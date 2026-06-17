#!/usr/bin/env bash
# LinkGuard Peer installer - v2
# OPS-03: Verifica que ORCH_TOKEN esté configurado antes de instalar
set -euo pipefail

# If someone runs: sudo sh ./install.sh
if [[ -z "${BASH_VERSION:-}" ]]; then
  exec /usr/bin/env bash "$0" "$@"
fi

log(){ echo "[*] $*"; }
die(){ echo "[!] $*" >&2; exit 1; }
have(){ command -v "$1" >/dev/null 2>&1; }

SERVICE="wg-auto-register.service"
APP_DIR="/opt/linkguard-peer"
ENV_FILE="/etc/linkguard/peer.env"
BIN_DIR="/usr/local/bin"
WRAPPER="$BIN_DIR/wg-auto-register"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  die "Run as root (use sudo)."
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

log "Installing LinkGuard Peer + wg-auto-cli"

# --------------------------------------------------
# Detect package manager
# --------------------------------------------------
PKG_MGR="unknown"
if have apt-get;   then PKG_MGR="apt"
elif have dnf;     then PKG_MGR="dnf"
elif have yum;     then PKG_MGR="yum"
elif have pacman;  then PKG_MGR="pacman"
elif have zypper;  then PKG_MGR="zypper"
elif have apk;     then PKG_MGR="apk"
fi

log "Package manager: $PKG_MGR"

install_deps() {
  log "Installing dependencies..."

  if have python3 && have wg && have wg-quick; then
    log "Core runtime dependencies already present, skipping package installation."
    return 0
  fi

  case "$PKG_MGR" in
    apt)
      export DEBIAN_FRONTEND=noninteractive
      apt-get update -y
      apt-get install -y --no-install-recommends \
        python3 python3-pip \
        wireguard-tools curl ca-certificates
      ;;
    dnf)
      dnf -y makecache
      dnf -y install \
        python3 python3-pip \
        wireguard-tools curl ca-certificates
      ;;
    yum)
      yum -y makecache || true
      yum -y install \
        python3 python3-pip \
        wireguard-tools curl ca-certificates
      ;;
    pacman)
      # Handle pacman lock
      if [[ -f /var/lib/pacman/db.lck ]]; then
        if fuser /var/lib/pacman/db.lck >/dev/null 2>&1; then
          log "pacman database locked:"
          fuser -v /var/lib/pacman/db.lck || true
          die "Close other package managers and rerun."
        else
          log "Removing stale pacman lock."
          rm -f /var/lib/pacman/db.lck
        fi
      fi
      pacman -Sy --noconfirm --needed \
        python python-pip \
        wireguard-tools curl ca-certificates
      ;;
    zypper)
      zypper --non-interactive refresh
      zypper --non-interactive install -y \
        python3 python3-pip \
        wireguard-tools curl ca-certificates
      ;;
    apk)
      apk update
      apk add --no-cache \
        python3 \
        wireguard-tools bash
      ;;
    *)
      die "Unsupported system. Install manually: python3 + wireguard-tools + curl."
      ;;
  esac
}

# --------------------------------------------------
# Validate required files
# --------------------------------------------------
REQ_FILES=(
  "wg-auto-register.py"
  "wg-auto-cli.py"
  "peer.env.example"
  "peer_register/__init__.py"
)

for f in "${REQ_FILES[@]}"; do
  [[ -f "$SCRIPT_DIR/$f" ]] || die "Missing required file: $f"
done

install_deps

# --------------------------------------------------
# Ensure python exists
# --------------------------------------------------
PYTHON_BIN=""
if have python3; then
  PYTHON_BIN="python3"
elif have python; then
  PYTHON_BIN="python"
else
  die "Python not found after install."
fi

log "Python: $($PYTHON_BIN --version 2>/dev/null || true)"

# --------------------------------------------------
# Create directories
# --------------------------------------------------
log "Creating directories..."
install -d -m 0755 "$APP_DIR"
install -d -m 0755 /etc/linkguard
install -d -m 0755 /var/lib/linkguard
install -d -m 0755 "$BIN_DIR"

# --------------------------------------------------
# Install files
# --------------------------------------------------
log "Installing peer agent..."
install -m 0755 "$SCRIPT_DIR/wg-auto-register.py" "$APP_DIR/wg-auto-register.py"
cp -r "$SCRIPT_DIR/peer_register" "$APP_DIR/"
find "$APP_DIR/peer_register" -type f -exec chmod 0644 {} \;

log "Installing CLI..."
install -m 0755 "$SCRIPT_DIR/wg-auto-cli.py" "$BIN_DIR/wg-auto-cli"

# Compatibility wrapper (prevents legacy unit breakage)
# IMPORTANT: uses detected PYTHON_BIN (python3 or python), avoids Arch issues
cat >"$WRAPPER" <<WRAP
#!/usr/bin/env sh
exec /usr/bin/env $PYTHON_BIN $APP_DIR/wg-auto-register.py "\$@"
WRAP
chmod 0755 "$WRAPPER"

# --------------------------------------------------
# Environment file
# --------------------------------------------------
if [[ ! -f "$ENV_FILE" ]]; then
  log "Creating peer.env..."
  install -m 0600 "$SCRIPT_DIR/peer.env.example" "$ENV_FILE"
  echo "[!] IMPORTANTE: Edita $ENV_FILE y configura ORCH_TOKEN antes de iniciar el servicio."
  echo "    El token lo obtienes del admin del orchestrator con: orch-cli user-create <nombre>"
else
  log "peer.env already exists, skipping."
fi

# --------------------------------------------------
# Validate ORCH_TOKEN before starting
# --------------------------------------------------
# shellcheck disable=SC1090
source "$ENV_FILE" 2>/dev/null || true
if [[ -z "${ORCH_TOKEN:-}" ]] || [[ "${ORCH_TOKEN:-}" == "REPLACE_WITH_YOUR_TOKEN" ]]; then
  echo ""
  echo "[WARNING] ORCH_TOKEN no está configurado en $ENV_FILE."
  echo "          El peer NO se registrará hasta que configures el token."
  echo "          Edita $ENV_FILE y luego: systemctl restart wg-auto-register"
  echo ""
fi

# --------------------------------------------------
# Init system sanity
# --------------------------------------------------
INIT_SYSTEM=""
if have systemctl; then
  INIT_SYSTEM="systemd"
elif have rc-service && have rc-update; then
  INIT_SYSTEM="openrc"
else
  die "No supported init system found. Expected systemd or OpenRC."
fi

if [[ "$INIT_SYSTEM" == "systemd" ]]; then
  log "Fixing systemd unit (removing conflicts)..."

  # Stop service to prevent restart loop
  systemctl stop  "$SERVICE" 2>/dev/null || true
  systemctl disable "$SERVICE" 2>/dev/null || true

  # Remove vendor units and drop-in overrides
  rm -f  "/usr/lib/systemd/system/$SERVICE" 2>/dev/null || true
  rm -f  "/lib/systemd/system/$SERVICE"     2>/dev/null || true
  rm -rf "/etc/systemd/system/${SERVICE}.d" 2>/dev/null || true

  cat >"/etc/systemd/system/$SERVICE" <<UNIT
[Unit]
Description=WireGuard Peer Auto-Register & Heartbeat
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$APP_DIR
EnvironmentFile=$ENV_FILE
Environment=PYTHONUNBUFFERED=1
Environment=WG_INTERFACE=wg0
Environment=WG_DIR=/etc/wireguard
Environment=WG_CONF_PATH=/etc/wireguard/wg0.conf
Environment=WG_PRIV_KEY_PATH=/etc/wireguard/wg0.key
Environment=WG_PUB_KEY_PATH=/etc/wireguard/wg0.pub
Environment=WG_KEEPALIVE=25
Environment=WG_HEARTBEAT_INTERVAL=25
Environment=WG_AUTO_STATE=/etc/wireguard/wg-auto.json
ExecStart=$WRAPPER run
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
UNIT

  systemctl daemon-reload
  systemctl reset-failed "$SERVICE" 2>/dev/null || true

  log "Enabling service..."
  systemctl enable "$SERVICE"

  if [[ -n "${ORCH_TOKEN:-}" ]] && [[ "${ORCH_TOKEN:-}" != "REPLACE_WITH_YOUR_TOKEN" ]]; then
    log "Starting service..."
    systemctl start "$SERVICE"

    log "Effective unit configuration:"
    systemctl --no-pager show -p FragmentPath -p DropInPaths -p ExecStart "$SERVICE" || true

    log "Service status:"
    systemctl --no-pager --full status "$SERVICE" || true

    log "Peer installed and service started."
  else
    log "Peer installed. Configure ORCH_TOKEN in $ENV_FILE and then run: systemctl start $SERVICE"
  fi
else
  log "Configuring OpenRC service..."
  rc-service wg-auto-register stop 2>/dev/null || true

  cat >"/etc/init.d/wg-auto-register" <<'UNIT'
#!/sbin/openrc-run
description="WireGuard Peer Auto-Register & Heartbeat"
command="/usr/local/bin/wg-auto-register"
command_args="run"
command_background=true
pidfile="/run/wg-auto-register.pid"
name="wg-auto-register"

depend() {
  need net
}
UNIT
  chmod 0755 /etc/init.d/wg-auto-register

  rc-update add wg-auto-register default >/dev/null 2>&1 || true

  if [[ -n "${ORCH_TOKEN:-}" ]] && [[ "${ORCH_TOKEN:-}" != "REPLACE_WITH_YOUR_TOKEN" ]]; then
    log "Starting service..."
    rc-service wg-auto-register restart || rc-service wg-auto-register start
    rc-service wg-auto-register status || true
    log "Peer installed and service started."
  else
    log "Peer installed. Configure ORCH_TOKEN in $ENV_FILE and then run: rc-service wg-auto-register start"
  fi
fi
