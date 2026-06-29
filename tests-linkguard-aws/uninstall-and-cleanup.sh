#!/usr/bin/env bash
# ============================================================================
# uninstall-and-cleanup.sh — Limpieza de WireGuard + estado de LinkGuard
# ============================================================================
# Alcance: SOLO WireGuard + estado (no desinstala binarios ni units).
#
# Elimina por host:
#   - Servicio wg-auto-register (systemd u openrc)
#   - Interfaces WireGuard (wg0 / wg-HUB)
#   - Reglas iptables (MASQUERADE 10.20.30.0/24, FORWARD wg-*)
#   - Archivos de estado: /etc/wireguard/wg0.* wg-HUB.* /etc/linkguard/wg-auto.json
#     /etc/wireguard/wg-auto.json
#
# Maquinas:
#   Local:    parrot (systemd)
#   Orquest:  34.193.139.170  (admin, llave + sudo)
#   Nubes:    54.210.49.136 (ubuntu), 3.228.113.66 (ec2-user),
#             98.87.229.24 (ec2-user)  — llave + sudo
#   VMs:      172.20.0.40 (root, alpine123, openrc)
#             172.20.0.7  (natalia, atidesa15, systemd, sudo)
#             via jump root@100.115.215.49 (atidesa15)
#
# Uso:
#   sudo bash tests-linkguard-aws/uninstall-and-cleanup.sh [opciones]
#
# Opciones:
#   -y, --yes         No pedir confirmacion
#   -n, --dry-run     Mostrar que se haria sin ejecutarlo
#   --local-only      Limpiar solo parrot local
#   --remote-only     Limpiar solo hosts remotos
#   --only ID         Limpiar solo una maquina (orq|119|76|143|40|7|parrot)
#   -h, --help        Mostrar esta ayuda
#
# Variables de entorno:
#   LINKGUARD_SSH_KEY      Llave SSH (default: linkguard-key.pem en el repo)
#   LINKGUARD_SUDO_PASS    Password sudo para nubes/orquestador (si no hay NOPASSWD)
#   LINKGUARD_VM40_PASS    Password SSH 172.20.0.40 (default: alpine123)
#   LINKGUARD_VM7_PASS     Password SSH 172.20.0.7 (default: atidesa15)
#   LINKGUARD_JUMP_PASS    Password SSH jump host (default: atidesa15)
# ============================================================================
set -euo pipefail

# ── Configuracion ───────────────────────────────────────────────────────────

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

HUB_WG_IFACE="wg-HUB"
PEER_WG_IFACE="wg0"
HUB_TUNNEL_CIDR="10.20.30.0/24"

SSH_OPTS=(-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=15)

# Flags
FORCE=false
DRY_RUN=false
LOCAL_ONLY=false
REMOTE_ONLY=false
ONLY_ID=""

# ── Utilidades ──────────────────────────────────────────────────────────────

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'

log()  { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[ERR]${NC} $*" >&2; }
info() { echo -e "${CYAN}[i]${NC} $*"; }

usage() {
    sed -n '3,33p' "${BASH_SOURCE[0]}" | sed 's/^# \?//' >&2
    exit 0
}

confirm() {
    if [ "$FORCE" = true ]; then return 0; fi
    local msg="${1:-¿Continuar?}"
    echo -en "${YELLOW}${msg}${NC} [s/N] "
    read -r r
    case "$r" in [sSyY]) return 0 ;; *) return 1 ;; esac
}

dry_or_run() {
    local desc="$1"; shift
    if [ "$DRY_RUN" = true ]; then
        info "[DRY-RUN] $desc"
        info "          $*"
        return 0
    fi
    log "$desc"
    "$@" 2>/dev/null || true
}

sudo_dry_or_run() {
    local desc="$1"; shift
    if [ "$DRY_RUN" = true ]; then
        info "[DRY-RUN] $desc"
        info "          sudo $*"
        return 0
    fi
    log "$desc"
    if [ -n "$SUDO_PASS" ]; then
        printf '%s\n' "$SUDO_PASS" | sudo -S "$@" 2>/dev/null || true
    else
        sudo "$@" 2>/dev/null || true
    fi
}

# ── Helpers SSH remotos ─────────────────────────────────────────────────────

# Nubes + orquestador: llave SSH + sudo
remote_key() {
    local user="$1" host="$2" script="$3"
    local remote_cmd
    if [ -n "$SUDO_PASS" ]; then
        remote_cmd="sudo -S -p '' sh"
        local stdin_input="${SUDO_PASS}"$'\n'"${script}"
    else
        remote_cmd="sudo -n sh"
        local stdin_input="$script"
    fi
    if [ "$DRY_RUN" = true ]; then
        info "[DRY-RUN] [${user}@${host}] sudo sh <<'EOF'"
        info "$script"
        info "EOF"
        return 0
    fi
    printf '%s' "$stdin_input" | ssh -i "$SSH_KEY" "${SSH_OPTS[@]}" "${user}@${host}" "$remote_cmd" 2>/dev/null || true
}

# VM via jump, root directo (172.20.0.40)
remote_jump_root() {
    local host="$1" pass="$2" script="$3"
    local proxy="sshpass -p ${JUMP_PASS} ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=15 -W %h:%p ${JUMP_HOST}"
    if [ "$DRY_RUN" = true ]; then
        info "[DRY-RUN] [root@${host} via jump] sh <<'EOF'"
        info "$script"
        info "EOF"
        return 0
    fi
    printf '%s' "$script" | sshpass -p "$pass" ssh "${SSH_OPTS[@]}" -o "ProxyCommand=${proxy}" "root@${host}" sh 2>/dev/null || true
}

# VM via jump, usuario no-root + sudo (172.20.0.7)
remote_jump_sudo() {
    local host="$1" user="$2" pass="$3" script="$4"
    local proxy="sshpass -p ${JUMP_PASS} ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=15 -W %h:%p ${JUMP_HOST}"
    if [ "$DRY_RUN" = true ]; then
        info "[DRY-RUN] [${user}@${host} via jump] sudo -S sh <<'EOF'"
        info "$script"
        info "EOF"
        return 0
    fi
    printf '%s\n%s' "$pass" "$script" | sshpass -p "$pass" ssh "${SSH_OPTS[@]}" -o "ProxyCommand=${proxy}" "${user}@${host}" "sudo -S -p '' sh" 2>/dev/null || true
}

# ── Scripts de limpieza (POSIX sh) ──────────────────────────────────────────

# Script para peers (nubes + VMs): wg0 + wg-auto-register + estado
CLEAN_PEER_SCRIPT=$(cat <<'SCRIPT'
set -e
# Detener servicio
if command -v systemctl >/dev/null 2>&1; then
    systemctl stop wg-auto-register 2>/dev/null || true
elif command -v rc-service >/dev/null 2>&1; then
    rc-service wg-auto-register stop 2>/dev/null || true
fi
killall -9 wg-auto-register.py 2>/dev/null || true
# Bajar interfaz WireGuard
ip link delete wg0 2>/dev/null || true
# Eliminar archivos de estado
rm -f /etc/wireguard/wg0.conf /etc/wireguard/wg0.key /etc/wireguard/wg0.pub
rm -f /etc/linkguard/wg-auto.json /etc/wireguard/wg-auto.json
# iptables: reglas FORWARD de wg0
iptables -D FORWARD -i wg0 -j ACCEPT 2>/dev/null || true
iptables -D FORWARD -o wg0 -j ACCEPT 2>/dev/null || true
echo "PEER_CLEANED"
SCRIPT
)

# Script para orquestador/hub: wg-HUB + hub-agent + orchestrator + estado + iptables hub
CLEAN_ORCH_SCRIPT=$(cat <<'SCRIPT'
set -e
# Detener servicios del orquestador
systemctl stop hub-agent 2>/dev/null || true
systemctl stop orchestrator 2>/dev/null || true
# Detener wg-auto-register si corre en el hub
systemctl stop wg-auto-register 2>/dev/null || true
# Bajar interfaz WireGuard del hub
wg-quick down wg-HUB 2>/dev/null || true
ip link delete wg-HUB 2>/dev/null || true
# Eliminar archivos de estado del hub
rm -f /etc/wireguard/wg-HUB.conf /etc/wireguard/wg-HUB.key /etc/wireguard/wg-HUB.pub
rm -f /etc/linkguard/wg-auto.json /etc/wireguard/wg-auto.json
# iptables: reglas del hub
NAT_IFACE=$(ip route show default 2>/dev/null | awk '/default/ {print $5; exit}')
[ -z "$NAT_IFACE" ] && NAT_IFACE=eth0
iptables -t nat -D POSTROUTING -s 10.20.30.0/24 -o "$NAT_IFACE" -j MASQUERADE 2>/dev/null || true
iptables -D FORWARD -i wg-HUB -o wg-HUB -j ACCEPT 2>/dev/null || true
iptables -D FORWARD -i wg-HUB -o "$NAT_IFACE" -j ACCEPT 2>/dev/null || true
iptables -D FORWARD -i "$NAT_IFACE" -o wg-HUB -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || true
# Reglas MASQUERADE residuales
while iptables -t nat -C POSTROUTING -s 10.20.30.0/24 -j MASQUERADE 2>/dev/null; do
    iptables -t nat -D POSTROUTING -s 10.20.30.0/24 -j MASQUERADE 2>/dev/null || break
done
echo "ORCH_CLEANED"
SCRIPT
)

# ── Limpieza local (parrot) ─────────────────────────────────────────────────

clean_local() {
    info "=== Limpiando parrot (local) ==="
    # Detener servicio
    dry_or_run "Deteniendo wg-auto-register" systemctl stop wg-auto-register
    # Bajar interfaz
    sudo_dry_or_run "Eliminando wg0" ip link delete wg0
    # Archivos de estado
    for f in /etc/wireguard/wg0.conf /etc/wireguard/wg0.key /etc/wireguard/wg0.pub \
             /etc/linkguard/wg-auto.json /etc/wireguard/wg-auto.json; do
        if [ -e "$f" ]; then
            sudo_dry_or_run "Eliminando $f" rm -f "$f"
        fi
    done
    # iptables locales
    local nat_iface
    nat_iface=$(ip route show default 2>/dev/null | awk '/default/ {print $5; exit}')
    if [ -n "$nat_iface" ]; then
        sudo_dry_or_run "iptables NAT MASQUERADE 10.20.30.0/24" \
            iptables -t nat -D POSTROUTING -s "$HUB_TUNNEL_CIDR" -o "$nat_iface" -j MASQUERADE
    fi
    sudo_dry_or_run "iptables FORWARD wg-HUB" \
        iptables -D FORWARD -i wg-HUB -o wg-HUB -j ACCEPT
    sudo_dry_or_run "iptables FORWARD wg0" \
        iptables -D FORWARD -i wg0 -j ACCEPT
    sudo_dry_or_run "iptables FORWARD wg0 (out)" \
        iptables -D FORWARD -o wg0 -j ACCEPT
    # MASQUERADE residual
    while sudo iptables -t nat -C POSTROUTING -s "$HUB_TUNNEL_CIDR" -j MASQUERADE 2>/dev/null; do
        sudo_dry_or_run "iptables MASQUERADE residual" \
            iptables -t nat -D POSTROUTING -s "$HUB_TUNNEL_CIDR" -j MASQUERADE
    done
    log "parrot limpiado"
}

# ── Limpieza remota ─────────────────────────────────────────────────────────

clean_orchestrator() {
    info "=== [REMOTO] Orquestador ${ORCH_HOST} (admin, llave+sudo) ==="
    if [ ! -f "$SSH_KEY" ]; then
        err "No se encontro la llave SSH: $SSH_KEY"
        return 1
    fi
    remote_key "$ORCH_USER" "$ORCH_HOST" "$CLEAN_ORCH_SCRIPT"
    log "Orquestador ${ORCH_HOST} limpiado"
}

clean_cloud() {
    local id="$1" host="$2" user="$3"
    info "=== [REMOTO] Nube ${id} (${user}@${host}, llave+sudo) ==="
    if [ ! -f "$SSH_KEY" ]; then
        err "No se encontro la llave SSH: $SSH_KEY"
        return 1
    fi
    remote_key "$user" "$host" "$CLEAN_PEER_SCRIPT"
    log "Nube ${id} (${host}) limpiada"
}

clean_vm40() {
    info "=== [REMOTO] VM 172.20.0.40 (root, openrc, via jump) ==="
    remote_jump_root "172.20.0.40" "$VM40_PASS" "$CLEAN_PEER_SCRIPT"
    log "VM 172.20.0.40 limpiada"
}

clean_vm7() {
    info "=== [REMOTO] VM 172.20.0.7 (natalia, systemd+sudo, via jump) ==="
    remote_jump_sudo "172.20.0.7" "natalia" "$VM7_PASS" "$CLEAN_PEER_SCRIPT"
    log "VM 172.20.0.7 limpiada"
}

# ── Resumen ─────────────────────────────────────────────────────────────────

print_summary() {
    local dry=""
    [ "$DRY_RUN" = true ] && dry=" [DRY-RUN - no se ejecuto nada]"
    echo ""
    info "=============================================="
    info "  RESUMEN DE LIMPIEZA${dry}"
    info "=============================================="
    echo ""
    if [ "$REMOTE_ONLY" = false ]; then
        echo "  Local (parrot):     wg0, wg-auto-register, iptables, estado"
    fi
    if [ "$LOCAL_ONLY" = false ]; then
        echo "  Orquestador:        ${ORCH_HOST} (admin, llave+sudo)"
        echo "  Nube 119:           54.210.49.136 (ubuntu)"
        echo "  Nube 76:            3.228.113.66 (ec2-user)"
        echo "  Nube 143:           98.87.229.24 (ec2-user)"
        echo "  VM 40:              172.20.0.40 (root, via jump)"
        echo "  VM 7:               172.20.0.7 (natalia, via jump)"
    fi
    echo ""
    info "Alcance: solo WireGuard + estado (binarios NO eliminados)"
    info "Para verificar:"
    info "  ip link show | grep -E '(wg-HUB|wg0)'  (debe estar vacio)"
    info "  iptables -t nat -L POSTROUTING -n | grep 10.20.30  (debe estar vacio)"
    info "  ls /etc/wireguard/wg0.* /etc/linkguard/wg-auto.json 2>&1  (no existe)"
    echo ""
}

# ── Main ────────────────────────────────────────────────────────────────────

main() {
    while [ $# -gt 0 ]; do
        case "$1" in
            -h|--help) usage ;;
            -y|--yes) FORCE=true; shift ;;
            -n|--dry-run) DRY_RUN=true; shift ;;
            --local-only) LOCAL_ONLY=true; REMOTE_ONLY=false; shift ;;
            --remote-only) LOCAL_ONLY=false; REMOTE_ONLY=true; shift ;;
            --only) ONLY_ID="$2"; shift 2 ;;
            *) warn "Opcion desconocida: $1"; usage ;;
        esac
    done

    echo ""
    echo -e "${RED}======================================================${NC}"
    echo -e "${RED}  LINKGUARD — LIMPIEZA WG + ESTADO (AWS + VMs + parrot)${NC}"
    echo -e "${RED}======================================================${NC}"
    echo ""
    info "Alcance: solo WireGuard + estado (NO elimina binarios ni units)"
    echo ""

    # Verificar root para limpieza local
    if [ "$REMOTE_ONLY" = false ] && [ "$(id -u)" -ne 0 ] && [ "$DRY_RUN" = false ]; then
        err "Para limpieza local ejecuta con sudo: sudo bash $0"
        err "O usa --remote-only"
        exit 1
    fi

    # Calcular flags de que limpiar
    local do_local=true do_orch=true do_119=true do_76=true do_143=true do_40=true do_7=true
    if [ -n "$ONLY_ID" ]; then
        do_local=false; do_orch=false; do_119=false; do_76=false; do_143=false; do_40=false; do_7=false
        case "$ONLY_ID" in
            parrot|local) do_local=true ;;
            orq|orch)     do_orch=true ;;
            119)          do_119=true ;;
            76)           do_76=true ;;
            143)          do_143=true ;;
            40)           do_40=true ;;
            7)            do_7=true ;;
            *) err "ID desconocido: $ONLY_ID (validos: parrot|orq|119|76|143|40|7)"; exit 1 ;;
        esac
    fi

    # Listar que se va a limpiar
    info "Se limpiaran:"
    if [ "$REMOTE_ONLY" = false ] && [ "$do_local" = true ]; then
        echo "  - parrot (local): wg0, wg-auto-register, iptables, estado"
    fi
    if [ "$LOCAL_ONLY" = false ]; then
        if [ "$do_orch" = true ]; then echo "  - Orquestador ${ORCH_HOST}: wg-HUB, hub-agent, orchestrator, iptables, estado"; fi
        if [ "$do_119" = true ];  then echo "  - Nube 54.210.49.136 (ubuntu): wg0, wg-auto-register, estado"; fi
        if [ "$do_76"  = true ];  then echo "  - Nube 3.228.113.66 (ec2-user): wg0, wg-auto-register, estado"; fi
        if [ "$do_143" = true ];  then echo "  - Nube 98.87.229.24 (ec2-user): wg0, wg-auto-register, estado"; fi
        if [ "$do_40"  = true ];  then echo "  - VM 172.20.0.40 (root, openrc, via jump): wg0, wg-auto-register, estado"; fi
        if [ "$do_7"   = true ];  then echo "  - VM 172.20.0.7 (natalia, systemd, via jump): wg0, wg-auto-register, estado"; fi
    fi
    echo ""

    if ! confirm "¿Continuar con la limpieza?"; then
        info "Cancelado."
        exit 0
    fi

    # Ejecutar segun flags

    if [ "$REMOTE_ONLY" = false ] && [ "$do_local" = true ]; then
        clean_local
    fi

    if [ "$LOCAL_ONLY" = false ]; then
        if [ "$do_orch" = true ]; then clean_orchestrator; fi
        if [ "$do_119" = true ]; then clean_cloud 119 54.210.49.136 ubuntu; fi
        if [ "$do_76"  = true ]; then clean_cloud 76  3.228.113.66  ec2-user; fi
        if [ "$do_143" = true ]; then clean_cloud 143 98.87.229.24 ec2-user; fi
        if [ "$do_40"  = true ]; then clean_vm40; fi
        if [ "$do_7"   = true ]; then clean_vm7; fi
    fi

    print_summary
    log "Limpieza completada."
}

main "$@"
