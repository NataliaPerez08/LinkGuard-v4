#!/usr/bin/env bash
# ============================================================================
# deploy.sh — Despliega orquestador + peers en las maquinas de prueba
# ============================================================================
# 1. Instala el orquestador en 34.193.139.170 (admin, llave + sudo)
# 2. Obtiene el ADMIN_TOKEN del orquestador
# 3. Crea un usuario tenant y obtiene su token
# 4. Instala peers en 3 nubes AWS + 2 VMs via jump
# 5. Configura peer.env con ORCH_URL y ORCH_TOKEN en cada peer
#
# Uso:
#   bash tests-linkguard-aws/deploy.sh [--orch-only] [--peers-only] [--skip-orch] [--skip-peers]
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
SSH_KEY="${LINKGUARD_SSH_KEY:-${REPO_DIR}/linkguard-key.pem}"
SUDO_PASS="${LINKGUARD_SUDO_PASS:-}"
VM40_PASS="${LINKGUARD_VM40_PASS:-alpine123}"
VM7_PASS="${LINKGUARD_VM7_PASS:-atidesa15}"
JUMP_PASS="${LINKGUARD_JUMP_PASS:-atidesa15}"
JUMP_HOST="root@100.115.215.49"

ORCH_HOST="34.193.139.170"
ORCH_USER="admin"
ORCH_URL="http://${ORCH_HOST}:8000/RPC2"

SSH_OPTS=(-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=15)

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[ERR]${NC} $*" >&2; }
info() { echo -e "${CYAN}[i]${NC} $*"; }

SKIP_ORCH=false
SKIP_PEERS=false
ORCH_ONLY=false
PEERS_ONLY=false

while [ $# -gt 0 ]; do
    case "$1" in
        --skip-orch) SKIP_ORCH=true; shift ;;
        --skip-peers) SKIP_PEERS=true; shift ;;
        --orch-only) SKIP_ORCH=false; SKIP_PEERS=true; ORCH_ONLY=true; shift ;;
        --peers-only) SKIP_ORCH=true; SKIP_PEERS=false; PEERS_ONLY=true; shift ;;
        -h|--help) sed -n '3,18p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'; exit 0 ;;
        *) warn "Opcion desconocida: $1"; shift ;;
    esac
done

# ── Helpers SSH ──

sudo_cmd() {
    if [ -n "$SUDO_PASS" ]; then
        echo "sudo -S -p ''"
    else
        echo "sudo -n"
    fi
}

scp_key() {
    local user="$1" host="$2" src="$3" dest="$4"
    scp -i "$SSH_KEY" "${SSH_OPTS[@]}" -r "$src" "${user}@${host}:${dest}" 2>/dev/null
}

ssh_key_sudo() {
    local user="$1" host="$2" script="$3"
    local remote_cmd
    local stdin_input
    if [ -n "$SUDO_PASS" ]; then
        remote_cmd="sudo -S -p '' bash"
        stdin_input="${SUDO_PASS}"$'\n'"${script}"
    else
        remote_cmd="sudo -n bash"
        stdin_input="$script"
    fi
    printf '%s' "$stdin_input" | ssh -i "$SSH_KEY" "${SSH_OPTS[@]}" "${user}@${host}" "$remote_cmd" 2>&1
}

ssh_key_run() {
    local user="$1" host="$2"; shift 2
    ssh -i "$SSH_KEY" "${SSH_OPTS[@]}" "${user}@${host}" "$@" 2>&1
}

remote_jump_root_scp() {
    local host="$1" pass="$2" src="$3" dest="$4"
    local proxy="sshpass -p ${JUMP_PASS} ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=15 -W %h:%p ${JUMP_HOST}"
    sshpass -p "$pass" scp "${SSH_OPTS[@]}" -o "ProxyCommand=${proxy}" -r "$src" "root@${host}:${dest}" 2>/dev/null
}

remote_jump_root_run() {
    local host="$1" pass="$2"; shift 2
    local proxy="sshpass -p ${JUMP_PASS} ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=15 -W %h:%p ${JUMP_HOST}"
    sshpass -p "$pass" ssh "${SSH_OPTS[@]}" -o "ProxyCommand=${proxy}" "root@${host}" "$@" 2>&1
}

remote_jump_sudo_scp() {
    local host="$1" user="$2" pass="$3" src="$4" dest="$5"
    local proxy="sshpass -p ${JUMP_PASS} ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=15 -W %h:%p ${JUMP_HOST}"
    sshpass -p "$pass" scp "${SSH_OPTS[@]}" -o "ProxyCommand=${proxy}" -r "$src" "${user}@${host}:${dest}" 2>/dev/null
}

remote_jump_sudo_run() {
    local host="$1" user="$2" pass="$3"; shift 3
    local proxy="sshpass -p ${JUMP_PASS} ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=15 -W %h:%p ${JUMP_HOST}"
    local script="$*"
    printf '%s\n%s' "$pass" "$script" | sshpass -p "$pass" ssh "${SSH_OPTS[@]}" -o "ProxyCommand=${proxy}" "${user}@${host}" "sudo -S -p '' bash" 2>&1
}

# ── 1. Instalar orquestador ──

deploy_orchestrator() {
    info "=== Instalando orquestador en ${ORCH_HOST} (${ORCH_USER}, llave+sudo) ==="
    if [ ! -f "$SSH_KEY" ]; then
        err "No se encontro la llave SSH: $SSH_KEY"
        return 1
    fi

    info "Copiando orchestrator-install-v2 al orquestador..."
    scp_key "$ORCH_USER" "$ORCH_HOST" "${REPO_DIR}/orchestrator-install-v2" "/tmp/" || {
        err "Fallo el scp del orquestador"
        return 1
    }

    info "Ejecutando install.sh con sudo..."
    local install_script="cd /tmp/orchestrator-install-v2 && bash install.sh"
    local out
    out=$(ssh_key_sudo "$ORCH_USER" "$ORCH_HOST" "$install_script" 2>&1) || true
    echo "$out" | tail -20

    # Verificar servicios
    info "Verificando servicios..."
    ssh_key_run "$ORCH_USER" "$ORCH_HOST" "sudo systemctl is-active orchestrator hub-agent" 2>&1 || true

    log "Orquestador instalado en ${ORCH_HOST}"
}

# ── 2. Obtener ADMIN_TOKEN ──

get_admin_token() {
    info "Obteniendo ADMIN_TOKEN del orquestador..."
    local token=""
    if [ -n "$SUDO_PASS" ]; then
        token=$(printf '%s\n' "$SUDO_PASS" | ssh -i "$SSH_KEY" "${SSH_OPTS[@]}" "${ORCH_USER}@${ORCH_HOST}" "sudo -S -p '' cat /etc/linkguard/secrets" 2>/dev/null | grep '^ADMIN_TOKEN=' | cut -d= -f2 | tr -d '[:space:]')
    else
        token=$(ssh -i "$SSH_KEY" "${SSH_OPTS[@]}" "${ORCH_USER}@${ORCH_HOST}" "sudo -n cat /etc/linkguard/secrets" 2>/dev/null | grep '^ADMIN_TOKEN=' | cut -d= -f2 | tr -d '[:space:]')
    fi
    if [ -z "$token" ]; then
        err "No pude obtener ADMIN_TOKEN"
        return 1
    fi
    echo "$token"
    return 0
}

# ── 3. Crear usuario tenant y obtener token ──

get_tenant_token() {
    local admin_token="$1"
    info "Creando usuario tenant 'tenant-a' y obteniendo token..."
    local orch_cli="${REPO_DIR}/orchestrator-install-v2/orch-cli.py"

    # Crear usuario (ignorar si ya existe)
    python3 "$orch_cli" --url "$ORCH_URL" --admin-token "$admin_token" user-create tenant-a 2>/dev/null || true

    # Obtener token
    local token
    token=$(python3 "$orch_cli" --url "$ORCH_URL" --admin-token "$admin_token" issue-user-token tenant-a 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null || echo "")
    if [ -z "$token" ]; then
        err "No pude obtener token para tenant-a"
        return 1
    fi
    echo "$token"
    return 0
}

# ── 4. Instalar peer en nube (llave + sudo) ──

deploy_cloud_peer() {
    local id="$1" host="$2" user="$3" peer_token="$4"
    info "=== Instalando peer en nube ${id} (${user}@${host}) ==="

    info "  Copiando peer-install-v2..."
    scp_key "$user" "$host" "${REPO_DIR}/peer-install-v2" "/tmp/" || {
        err "  Fallo el scp a ${host}"
        return 1
    }

    info "  Ejecutando install.sh + configurando peer.env..."
    local script="cd /tmp/peer-install-v2 && bash install.sh 2>&1
install -d -m 0755 /etc/linkguard
cat > /etc/linkguard/peer.env <<'ENVEOF'
ORCH_URL=${ORCH_URL}
ORCH_TOKEN=${peer_token}
PEER_ID=
USER_ID=tenant-a
WG_INTERFACE=wg0
WG_DIR=/etc/wireguard
WG_CONF_PATH=/etc/wireguard/wg0.conf
WG_PRIV_KEY_PATH=/etc/wireguard/wg0.key
WG_PUB_KEY_PATH=/etc/wireguard/wg0.pub
WG_KEEPALIVE=25
WG_HEARTBEAT_INTERVAL=25
WG_AUTO_STATE=/etc/wireguard/wg-auto.json
ENVEOF
chmod 600 /etc/linkguard/peer.env
echo PEER_INSTALLED"
    local out
    out=$(ssh_key_sudo "$user" "$host" "$script" 2>&1) || true
    echo "$out" | tail -5

    log "  Nube ${id} (${host}) peer instalado"
}

# ── 5. Instalar peer en VM via jump ──

deploy_vm40_peer() {
    local peer_token="$1"
    info "=== Instalando peer en VM 172.20.0.40 (root, openrc, via jump) ==="

    info "  Copiando peer-install-v2 via jump..."
    remote_jump_root_scp "172.20.0.40" "$VM40_PASS" "${REPO_DIR}/peer-install-v2" "/root/" || {
        err "  Fallo el scp a 172.20.0.40"
        return 1
    }

    info "  Ejecutando install.sh + configurando peer.env..."
    local script="cd /root/peer-install-v2 && bash install.sh 2>&1
install -d -m 0755 /etc/linkguard
cat > /etc/linkguard/peer.env <<'ENVEOF'
ORCH_URL=${ORCH_URL}
ORCH_TOKEN=${peer_token}
PEER_ID=
USER_ID=tenant-a
WG_INTERFACE=wg0
WG_DIR=/etc/wireguard
WG_CONF_PATH=/etc/wireguard/wg0.conf
WG_PRIV_KEY_PATH=/etc/wireguard/wg0.key
WG_PUB_KEY_PATH=/etc/wireguard/wg0.pub
WG_KEEPALIVE=25
WG_HEARTBEAT_INTERVAL=25
WG_AUTO_STATE=/etc/wireguard/wg-auto.json
ENVEOF
chmod 600 /etc/linkguard/peer.env
echo PEER_INSTALLED"
    local out
    out=$(remote_jump_root_run "172.20.0.40" "$VM40_PASS" "$script" 2>&1) || true
    echo "$out" | tail -5

    log "  VM 172.20.0.40 peer instalado"
}

deploy_vm7_peer() {
    local peer_token="$1"
    info "=== Instalando peer en VM 172.20.0.7 (natalia, systemd+sudo, via jump) ==="

    info "  Copiando peer-install-v2 via jump..."
    remote_jump_sudo_scp "172.20.0.7" "natalia" "$VM7_PASS" "${REPO_DIR}/peer-install-v2" "/tmp/" || {
        err "  Fallo el scp a 172.20.0.7"
        return 1
    }

    info "  Ejecutando install.sh + configurando peer.env (sudo)..."
    local script="cd /tmp/peer-install-v2 && bash install.sh 2>&1
install -d -m 0755 /etc/linkguard
cat > /etc/linkguard/peer.env <<'ENVEOF'
ORCH_URL=${ORCH_URL}
ORCH_TOKEN=${peer_token}
PEER_ID=
USER_ID=tenant-a
WG_INTERFACE=wg0
WG_DIR=/etc/wireguard
WG_CONF_PATH=/etc/wireguard/wg0.conf
WG_PRIV_KEY_PATH=/etc/wireguard/wg0.key
WG_PUB_KEY_PATH=/etc/wireguard/wg0.pub
WG_KEEPALIVE=25
WG_HEARTBEAT_INTERVAL=25
WG_AUTO_STATE=/etc/wireguard/wg-auto.json
ENVEOF
chmod 600 /etc/linkguard/peer.env
echo PEER_INSTALLED"
    local out
    out=$(remote_jump_sudo_run "172.20.0.7" "natalia" "$VM7_PASS" "$script" 2>&1) || true
    echo "$out" | tail -5

    log "  VM 172.20.0.7 peer instalado"
}

# ── Main ──

main() {
    echo ""
    echo -e "${CYAN}======================================================${NC}"
    echo -e "${CYAN}  LINKGUARD — DESPLIEGUE (orquestador + peers)${NC}"
    echo -e "${CYAN}======================================================${NC}"
    echo ""

    if [ ! -f "$SSH_KEY" ]; then
        err "No se encontro la llave SSH: $SSH_KEY"
        exit 1
    fi

    local admin_token=""
    local peer_token=""

    if [ "$SKIP_ORCH" = false ]; then
        deploy_orchestrator
        admin_token=$(get_admin_token)
        info "ADMIN_TOKEN: ${admin_token:0:16}..."
    fi

    if [ "$SKIP_PEERS" = false ]; then
        if [ -z "$admin_token" ]; then
            info "Obteniendo ADMIN_TOKEN (no se instalo orquestador en esta corrida)..."
            admin_token=$(get_admin_token)
        fi
        peer_token=$(get_tenant_token "$admin_token")
        info "Peer token (tenant-a): ${peer_token:0:16}..."

        deploy_cloud_peer 119 54.210.49.136 ubuntu "$peer_token"
        deploy_cloud_peer 76  3.228.113.66  ec2-user "$peer_token"
        deploy_cloud_peer 143 98.87.229.24 ec2-user "$peer_token"
        deploy_vm40_peer "$peer_token"
        deploy_vm7_peer "$peer_token"
    fi

    echo ""
    log "Despliegue completado."
    if [ -n "$peer_token" ]; then
        info "Token de peers: ${peer_token:0:16}... (guardado en /etc/linkguard/peer.env de cada peer)"
    fi
}

main "$@"
