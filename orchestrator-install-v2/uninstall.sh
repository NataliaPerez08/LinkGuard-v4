#!/usr/bin/env bash
# ============================================================================
# uninstall.sh — Desinstalación completa del orquestador LinkGuard
# ============================================================================
# Elimina todos los componentes del orquestador:
#   - Servicios: orchestrator.service, hub-agent.service
#   - Reglas iptables NAT y FORWARD del hub-agent
#   - Interfaz WireGuard wg-HUB
#   - Archivos de instalación, configuración y estado
#
# Uso:
#   sudo bash uninstall.sh [opciones]
#
# Opciones:
#   -y, --yes         No pedir confirmación (automático)
#   -n, --dry-run     Mostrar qué se haría sin ejecutarlo
#   -h, --help        Mostrar ayuda
# ============================================================================
set -euo pipefail

# ── Configuración ───────────────────────────────────────────────────────────

HUB_WG_IFACE="${HUB_WG_IFACE:-wg-HUB}"
HUB_TUNNEL_CIDR="${HUB_TUNNEL_CIDR:-10.20.30.0/24}"
HUB_NAT_IFACE="${HUB_NAT_IFACE:-}"
HUB_LISTEN_PORT="${HUB_LISTEN_PORT:-51820}"

FORCE=false
DRY_RUN=false

# ── Utilidades ──────────────────────────────────────────────────────────────

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*" >&2; }
info() { echo -e "${CYAN}[i]${NC} $*"; }

usage() {
    cat <<'USAGEEOF'
Uso: sudo bash uninstall.sh [opciones]

Elimina todos los componentes del orquestador LinkGuard:
  - Servicios: orchestrator.service, hub-agent.service
  - Reglas iptables (NAT + FORWARD) del hub-agent
  - Interfaz WireGuard wg-HUB
  - Archivos: /opt/linkguard-orchestrator/, /etc/linkguard/, /var/lib/wg-orchestrator/

Opciones:
  -y, --yes         No pedir confirmación
  -n, --dry-run     Mostrar qué se haría sin ejecutarlo
  -h, --help        Mostrar esta ayuda

Variables de entorno:
  HUB_WG_IFACE      Nombre de la interfaz WireGuard (default: wg-HUB)
  HUB_TUNNEL_CIDR   CIDR de la red del túnel (default: 10.20.30.0/24)
  HUB_NAT_IFACE     Interfaz de salida para NAT (default: autodetectada)
USAGEEOF
    exit 0
}

out_iface() {
    ip route show default 2>/dev/null | awk '/default/ {print $5; exit}'
}

confirm() {
    if [ "$FORCE" = true ]; then
        return 0
    fi
    local msg="${1:-¿Continuar?}"
    echo -en "${YELLOW}${msg}${NC} [s/N] "
    read -r r
    case "$r" in
        [sSyY]) return 0 ;;
        *) return 1 ;;
    esac
}

sudo_dry_or_run() {
    local desc="$1"
    shift
    if [ "$DRY_RUN" = true ]; then
        info "[DRY-RUN] $desc"
        info "         sudo $*"
        return 0
    fi
    log "$desc"
    sudo "$@" 2>/dev/null || true
}

dry_or_run() {
    local desc="$1"
    shift
    if [ "$DRY_RUN" = true ]; then
        info "[DRY-RUN] $desc"
        info "         $*"
        return 0
    fi
    log "$desc"
    "$@" 2>/dev/null || true
}

# ── Fase 1: Detener servicios ──────────────────────────────────────────────

stop_services() {
    info "=== Fase 1: Detener servicios ==="
    for svc in orchestrator.service hub-agent.service; do
        if systemctl is-enabled "$svc" &>/dev/null 2>/dev/null || systemctl is-active "$svc" &>/dev/null 2>/dev/null; then
            sudo_dry_or_run "Deteniendo y deshabilitando $svc" \
                systemctl disable --now "$svc"
        fi
    done
}

# ── Fase 2: Eliminar reglas iptables ───────────────────────────────────────

remove_iptables() {
    info "=== Fase 2: Eliminar reglas iptables ==="

    local nat_iface="${HUB_NAT_IFACE:-$(out_iface)}"
    if [ -z "$nat_iface" ]; then
        nat_iface="eth0"
        warn "No se detectó interfaz NAT, usando eth0"
    fi

    # Reglas FORWARD del hub-agent
    sudo_dry_or_run "FORWARD: -i $HUB_WG_IFACE -o $HUB_WG_IFACE -j ACCEPT" \
        iptables -D FORWARD -i "$HUB_WG_IFACE" -o "$HUB_WG_IFACE" -j ACCEPT

    sudo_dry_or_run "FORWARD: -i $HUB_WG_IFACE -o $nat_iface -j ACCEPT" \
        iptables -D FORWARD -i "$HUB_WG_IFACE" -o "$nat_iface" -j ACCEPT

    sudo_dry_or_run "FORWARD: -i $nat_iface -o $HUB_WG_IFACE -m state --state RELATED,ESTABLISHED -j ACCEPT" \
        iptables -D FORWARD -i "$nat_iface" -o "$HUB_WG_IFACE" -m state --state RELATED,ESTABLISHED -j ACCEPT

    # Regla NAT MASQUERADE del hub-agent
    sudo_dry_or_run "nat/POSTROUTING: -s $HUB_TUNNEL_CIDR -o $nat_iface -j MASQUERADE" \
        iptables -t nat -D POSTROUTING -s "$HUB_TUNNEL_CIDR" -o "$nat_iface" -j MASQUERADE

    # Limpieza residual: reglas MASQUERADE genéricas sin -o
    while iptables -t nat -C POSTROUTING -s "$HUB_TUNNEL_CIDR" -j MASQUERADE 2>/dev/null; do
        sudo_dry_or_run "nat/POSTROUTING (residual): -s $HUB_TUNNEL_CIDR -j MASQUERADE" \
            iptables -t nat -D POSTROUTING -s "$HUB_TUNNEL_CIDR" -j MASQUERADE
    done
}

# ── Fase 3: Eliminar interfaz WireGuard ────────────────────────────────────

remove_wg_interface() {
    info "=== Fase 3: Eliminar interfaz WireGuard ==="
    if ip link show "$HUB_WG_IFACE" &>/dev/null 2>/dev/null; then
        sudo_dry_or_run "Bajando $HUB_WG_IFACE (wg-quick down)" \
            wg-quick down "$HUB_WG_IFACE"
        sudo_dry_or_run "Eliminando interfaz $HUB_WG_IFACE" \
            ip link delete "$HUB_WG_IFACE"
    fi
}

# ── Fase 4: Eliminar archivos ──────────────────────────────────────────────

remove_files() {
    info "=== Fase 4: Eliminar archivos ==="
    local dirs=(
        "/opt/linkguard-orchestrator"
        "/var/lib/wg-orchestrator"
    )
    local files=(
        "/etc/linkguard/secrets"
        "/etc/linkguard/jwt_secret"
        "/usr/local/bin/orch-cli"
        "/etc/wireguard/${HUB_WG_IFACE}.conf"
        "/etc/wireguard/${HUB_WG_IFACE}.key"
        "/etc/wireguard/${HUB_WG_IFACE}.pub"
        "/etc/systemd/system/orchestrator.service"
        "/etc/systemd/system/hub-agent.service"
    )

    for d in "${dirs[@]}"; do
        if [ -e "$d" ]; then
            sudo_dry_or_run "Eliminando directorio $d" rm -rf "$d"
        fi
    done
    for f in "${files[@]}"; do
        if [ -e "$f" ]; then
            sudo_dry_or_run "Eliminando archivo $f" rm -f "$f"
        fi
    done

    # Eliminar /etc/linkguard solo si está vacío
    if [ -d "/etc/linkguard" ] && [ -z "$(ls -A /etc/linkguard 2>/dev/null)" ]; then
        sudo_dry_or_run "Eliminando /etc/linkguard (vacío)" rmdir "/etc/linkguard"
    fi

    if [ "$DRY_RUN" = false ]; then
        systemctl daemon-reload 2>/dev/null || true
        log "systemd daemon recargado"
    fi
}

# ── Reporte final ──────────────────────────────────────────────────────────

print_summary() {
    local dry=""
    [ "$DRY_RUN" = true ] && dry=" [DRY-RUN — no se ejecutó nada]"
    echo ""
    info "=============================================="
    info "  ORQUESTADOR DESINSTALADO${dry}"
    info "=============================================="
    echo ""
    info "Para verificar:"
    info "  systemctl status orchestrator.service hub-agent.service 2>&1 | head -5"
    info "  iptables -t nat -L POSTROUTING -n | grep '$HUB_TUNNEL_CIDR' || echo '(limpio)'"
    info "  ip link show $HUB_WG_IFACE 2>&1 || echo '(eliminado)'"
    info "  ls /opt/linkguard-orchestrator 2>&1 || echo '(eliminado)'"
    echo ""
}

# ── Main ────────────────────────────────────────────────────────────────────

main() {
    while [ $# -gt 0 ]; do
        case "$1" in
            -h|--help) usage ;;
            -y|--yes) FORCE=true; shift ;;
            -n|--dry-run) DRY_RUN=true; shift ;;
            *) warn "Opción desconocida: $1"; usage ;;
        esac
    done

    echo ""
    echo -e "${RED}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║   LINKGUARD — DESINSTALAR ORQUESTADOR              ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════════════╝${NC}"
    echo ""

    if [ "$(id -u)" -ne 0 ] && [ "$DRY_RUN" = false ]; then
        err "Debe ejecutarse como root (o con sudo)"
        err "Ejecute: sudo bash $0"
        exit 1
    fi

    echo "Se ELIMINARÁN los siguientes componentes del orquestador:"
    echo ""
    echo "  • Servicios: orchestrator.service, hub-agent.service"
    echo "  • Reglas iptables (FORWARD + NAT MASQUERADE)"
    echo "  • Interfaz WireGuard: $HUB_WG_IFACE"
    echo "  • Directorios: /opt/linkguard-orchestrator/, /etc/linkguard/, /var/lib/wg-orchestrator/"
    echo "  • Archivos: claves WireGuard, secrets, systemd units, orch-cli"
    echo ""

    if ! confirm "¿Desinstalar el orquestador LinkGuard?"; then
        info "Cancelado."
        exit 0
    fi

    stop_services
    remove_iptables
    remove_wg_interface
    remove_files
    print_summary
    log "Desinstalación del orquestador completada."
}

main "$@"
