#!/usr/bin/env bash
# LinkGuard Orchestrator + Hub Agent + orch-cli installer - releasev4
# Based on ChatGPT v3 structure; corrected paths/files for releasev4
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "[!] Run as root (use sudo)."
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

log()  { echo "[*] $*"; }
warn() { echo "[!] $*" >&2; }
die()  { echo "[!] $*" >&2; exit 1; }

# ---- Paths (releasev4) ----
INSTALL_DIR="/opt/linkguard-orchestrator"
STATE_DIR="/var/lib/wg-orchestrator"
BACKUP_DIR="${STATE_DIR}/backups"
SECRETS_FILE="/etc/linkguard/secrets"
JWT_SECRET_FILE="/etc/linkguard/jwt_secret"

# ---- Detect distro / package manager ----
OS_ID="unknown"
OS_LIKE=""
if [[ -r /etc/os-release ]]; then
  . /etc/os-release
  OS_ID="${ID:-unknown}"
  OS_LIKE="${ID_LIKE:-}"
fi

have() { command -v "$1" >/dev/null 2>&1; }

PKG_MGR="unknown"
if   have apt-get; then PKG_MGR="apt"
elif have dnf;     then PKG_MGR="dnf"
elif have yum;     then PKG_MGR="yum"
elif have pacman;  then PKG_MGR="pacman"
elif have zypper;  then PKG_MGR="zypper"
elif have apk;     then PKG_MGR="apk"
fi

log "Detected OS: id=${OS_ID} like=${OS_LIKE} pkgmgr=${PKG_MGR}"

# ---- iptables safety helpers ----
iptables_present() {
  have iptables && return 0
  case "$PKG_MGR" in
    apt|dnf|yum|zypper) rpm -q iptables >/dev/null 2>&1 || dpkg -s iptables >/dev/null 2>&1 ;;
    apk)    apk info -e iptables >/dev/null 2>&1 ;;
    pacman)
      pacman -Q iptables     >/dev/null 2>&1 && return 0
      pacman -Q iptables-nft >/dev/null 2>&1 && return 0
      return 1 ;;
    *) return 1 ;;
  esac
}

install_iptables_if_missing() {
  if iptables_present; then
    warn "iptables already present; keeping current variant (will not replace)."
    return 0
  fi
  warn "iptables not found; installing a compatible package..."
  case "$PKG_MGR" in
    apt)    apt-get install -y --no-install-recommends iptables ;;
    dnf)    dnf -y install iptables ;;
    yum)    yum -y install iptables ;;
    zypper) zypper --non-interactive install -y iptables ;;
    apk)    apk add --no-cache iptables ;;
    pacman) pacman -Sy --noconfirm --needed iptables-nft ;;
    *)      die "Cannot auto-install iptables on this system. Install it manually." ;;
  esac
}

# ---- Install system dependencies ----
install_deps() {
  log "Installing system dependencies..."
  case "$PKG_MGR" in
    apt)
      export DEBIAN_FRONTEND=noninteractive
      apt-get update -y
      apt-get install -y --no-install-recommends \
        python3 python3-venv python3-pip python3-defusedxml python3-jwt \
        wireguard-tools curl ca-certificates openssl
      install_iptables_if_missing
      ;;
    dnf)
      dnf -y makecache
      dnf -y install python3 python3-pip python3-defusedxml python3-pyjwt wireguard-tools curl ca-certificates openssl
      install_iptables_if_missing
      ;;
    yum)
      yum -y makecache || true
      yum -y install python3 python3-pip python3-defusedxml python3-pyjwt wireguard-tools curl ca-certificates openssl
      install_iptables_if_missing
      ;;
    pacman)
      deps=(python python-pip python-defusedxml python-pyjwt wireguard-tools curl ca-certificates openssl)

      ipt="no"; iptnft="no"
      pacman -Q iptables     >/dev/null 2>&1 && ipt="yes"
      pacman -Q iptables-nft >/dev/null 2>&1 && iptnft="yes"

      if [[ "$ipt" == "yes" && "$iptnft" == "yes" ]]; then
        warn "Both iptables and iptables-nft detected simultaneously — leaving untouched."
      elif [[ "$ipt" == "yes" ]]; then
        warn "iptables already installed; keeping legacy variant."
        deps+=(iptables)
      elif [[ "$iptnft" == "yes" ]]; then
        warn "iptables-nft already installed; keeping nft variant."
        deps+=(iptables-nft)
      else
        warn "No iptables found; installing iptables-nft (Arch default)."
        deps+=(iptables-nft)
      fi

      pacman -Sy --noconfirm --needed "${deps[@]}"

      # Ensure python3 symlink exists (Arch uses 'python')
      if ! have python3 && have python; then
        ln -sf "$(command -v python)" /usr/local/bin/python3
        log "Created python3 -> python symlink"
      fi
      ;;
    zypper)
      zypper --non-interactive refresh
      zypper --non-interactive install -y \
        python3 python3-pip python3-defusedxml python3-PyJWT wireguard-tools curl ca-certificates openssl
      install_iptables_if_missing
      ;;
    apk)
      apk update
      apk add --no-cache python3 py3-pip py3-defusedxml py3-pyjwt wireguard-tools curl ca-certificates openssl
      install_iptables_if_missing
      ;;
    *)
      die "Unsupported system. Install manually: python3 pip defusedxml pyjwt wireguard-tools iptables curl ca-certificates openssl"
      ;;
  esac
}

# ---- Preflight checks ----
if ! have systemctl; then
  die "systemctl not found. This installer requires a systemd-based distro."
fi

req_files=(
  "orchestrator.py"
  "orchestrator/__init__.py"
  "hub-agent.py"
  "hub-agent-cleanup.sh"
  "orch-cli.py"
  "systemd/orchestrator.service"
  "systemd/hub-agent.service"
)
for f in "${req_files[@]}"; do
  [[ -f "$SCRIPT_DIR/$f" ]] || die "Missing required file: $f (expected at $SCRIPT_DIR/$f)"
done

install_deps

have python3 || die "python3 not found after dependency install."
log "Python: $(python3 --version 2>/dev/null || true) @ $(command -v python3)"
have openssl  || die "openssl not found after dependency install."

# ---- Create directories ----
log "Creating directories..."
install -d -m 0755 "$INSTALL_DIR"
install -d -m 0755 /usr/local/bin
install -d -m 0750 /etc/linkguard
install -d -m 0755 "$STATE_DIR"
install -d -m 0755 "$BACKUP_DIR"

# ---- Generate tokens (only on first install) ----
if [[ ! -f "$SECRETS_FILE" ]]; then
  log "Generating secure tokens (first install)..."
  ADMIN_TOKEN=$(openssl rand -hex 32)
  ORCH_TOKEN=$(openssl rand -hex 32)
  HUB_AGENT_TOKEN=$(openssl rand -hex 32)
  cat > "$SECRETS_FILE" <<EOF
# Auto-generated by install.sh — root-only
ADMIN_TOKEN=${ADMIN_TOKEN}
ORCH_TOKEN=${ORCH_TOKEN}
HUB_AGENT_TOKEN=${HUB_AGENT_TOKEN}
EOF
  chmod 600 "$SECRETS_FILE"
  log "Tokens saved to $SECRETS_FILE"
else
  log "Existing tokens found in $SECRETS_FILE — reusing."
fi

# ---- Generate JWT secret (only on first install) ----
if [[ ! -f "$JWT_SECRET_FILE" ]]; then
  openssl rand -hex 64 > "$JWT_SECRET_FILE"
  chmod 600 "$JWT_SECRET_FILE"
  log "JWT secret generated at $JWT_SECRET_FILE"
fi

# ---- Load tokens into env ----
# shellcheck disable=SC1090
source "$SECRETS_FILE"

# ---- Install application files ----
log "Installing application files..."
install -m 0644 "$SCRIPT_DIR/orchestrator.py"    "$INSTALL_DIR/orchestrator.py"
cp -r "$SCRIPT_DIR/orchestrator"                 "$INSTALL_DIR/orchestrator"
find "$INSTALL_DIR/orchestrator" -type f -exec chmod 0644 {} \;
install -m 0644 "$SCRIPT_DIR/hub-agent.py"        "$INSTALL_DIR/hub-agent.py"
install -m 0755 "$SCRIPT_DIR/hub-agent-cleanup.sh" "$INSTALL_DIR/hub-agent-cleanup.sh"
install -m 0755 "$SCRIPT_DIR/orch-cli.py"          /usr/local/bin/orch-cli

# ---- Patch and install systemd units ----
log "Installing systemd units..."

sed \
  -e "s|^Environment=ADMIN_TOKEN=.*|Environment=ADMIN_TOKEN=${ADMIN_TOKEN}|" \
  -e "s|^Environment=ORCH_TOKEN=.*|Environment=ORCH_TOKEN=${ORCH_TOKEN}|" \
  -e "s|^Environment=HUB_AGENT_TOKEN=.*|Environment=HUB_AGENT_TOKEN=${HUB_AGENT_TOKEN}|" \
  "$SCRIPT_DIR/systemd/orchestrator.service" > /etc/systemd/system/orchestrator.service

sed \
  -e "s|^Environment=HUB_AGENT_TOKEN=.*|Environment=HUB_AGENT_TOKEN=${HUB_AGENT_TOKEN}|" \
  "$SCRIPT_DIR/systemd/hub-agent.service" > /etc/systemd/system/hub-agent.service

chmod 600 /etc/systemd/system/orchestrator.service
chmod 600 /etc/systemd/system/hub-agent.service

# ---- Enable and start services ----
log "Reloading systemd..."
systemctl daemon-reexec
systemctl daemon-reload

log "Stopping existing services (if running)..."
systemctl stop hub-agent.service orchestrator.service 2>/dev/null || true

log "Enabling and starting services..."
systemctl enable orchestrator.service hub-agent.service
systemctl restart hub-agent.service
systemctl restart orchestrator.service

log "Done."
echo ""
log "Tokens:     $SECRETS_FILE  (root-only)"
log "JWT secret: $JWT_SECRET_FILE  (root-only)"
echo ""
log "Service status:"
systemctl --no-pager --full status orchestrator.service hub-agent.service || true
echo ""
log "Recent logs (hub-agent):"
journalctl -u hub-agent.service -n 30 --no-pager || true
