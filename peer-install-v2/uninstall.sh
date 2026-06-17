#!/usr/bin/env bash
# ============================================================================
# uninstall.sh — Desinstalación completa del peer LinkGuard (wg-auto-register)
# ============================================================================
# Elimina todos los componentes del peer:
#   - Servicio: wg-auto-register (systemd y/o OpenRC)
#   - Interfaz WireGuard wg0
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

WG_IFACE="${WG_IFACE:-wg0}"
WG_DIR="${WG_DIR:-/etc/wireguard}"

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

Elimina todos los componentes del peer LinkGuard:
  - Servicio: wg-auto-register (systemd y/o OpenRC)
  - Interfaz WireGuard wg0
  - Archivos: /opt/linkguard-peer/, /etc/linkguard/peer.env, /var/lib/linkguard/

Opciones:
  -y, --yes         No pedir confirmación
  -n, --dry-run     Mostrar qué se haría sin ejecutarlo
  -h, --help        Mostrar esta ayuda

Variables de entorno:
  WG_IFACE    Nombre de la interfaz WireGuard (default: wg0)
  WG_DIR      Directorio de config WireGuard (default: /etc/wireguard)
USAGEEOF
    exit 0
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

# ── Fase 1: Detener servicio ───────────────────────────────────────────────

stop_service() {
    info "=== Fase 1: Detener servicio wg-auto-register ==="

    # systemd
    if systemctl is-enabled wg-auto-register.service &>/dev/null 2>/dev/null || \
       systemctl is-active wg-auto-register.service &>/dev/null 2>/dev/null; then
        sudo_dry_or_run "Deteniendo y deshabilitando wg-auto-register.service" \
            systemctl disable --now wg-auto-register.service
    fi

    # OpenRC
    if command -v rc-service &>/dev/null; then
        if rc-service wg-auto-register status &>/dev/null 2>/dev/null; then
            sudo_dry_or_run "Deteniendo wg-auto-register (OpenRC)" \
                rc-service wg-auto-register stop
        fi
        if rc-update show 2>/dev/null | grep -q wg-auto-register; then
            sudo_dry_or_run "Eliminando wg-auto-register del runlevel default (OpenRC)" \
                rc-update del wg-auto-register default
        fi
    fi
}

# ── Fase 2: Eliminar interfaz WireGuard ────────────────────────────────────

remove_wg_interface() {
    info "=== Fase 2: Eliminar interfaz WireGuard ==="
    if ip link show "$WG_IFACE" &>/dev/null 2>/dev/null; then
        sudo_dry_or_run "Bajando $WG_IFACE" \
            ip link set "$WG_IFACE" down 2>/dev/null || true
        sudo_dry_or_run "Eliminando interfaz $WG_IFACE" \
            ip link delete "$WG_IFACE"
    fi
}

# ── Fase 3: Eliminar archivos ──────────────────────────────────────────────

remove_files() {
    info "=== Fase 3: Eliminar archivos ==="
    local dirs=(
        "/opt/linkguard-peer"
        "/var/lib/linkguard"
    )
    local files=(
        "/usr/local/bin/wg-auto-cli"
        "/usr/local/bin/wg-auto-register"
        "${WG_DIR}/${WG_IFACE}.conf"
        "${WG_DIR}/${WG_IFACE}.key"
        "${WG_DIR}/${WG_IFACE}.pub"
        "${WG_DIR}/${WG_IFACE}.json"
        "/etc/linkguard/peer.env"
        "/etc/systemd/system/wg-auto-register.service"
        "/etc/init.d/wg-auto-register"
    )
    local del_dirs=(
        "/etc/systemd/system/wg-auto-register.service.d"
        "/usr/lib/systemd/system/wg-auto-register.service"
        "/lib/systemd/system/wg-auto-register.service"
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
    for d in "${del_dirs[@]}"; do
        if [ -e "$d" ]; then
            sudo_dry_or_run "Eliminando $d" rm -rf "$d"
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

# ── Fase 4: (Opcional) Limpiar dependencias instaladas por install.sh ──────

remove_deps() {
    info "=== Fase 4: Dependencias (opcional) ==="
    info "El install.sh instaló: python3, python3-pip, wireguard-tools, curl, ca-certificates"
    info "NO se eliminarán automáticamente para evitar afectar otros servicios."
    info "Si desea removerlas manualmente:"
    info "  apt purge -y python3-pip wireguard-tools  # (Debian/Ubuntu)"
    info "  apk del py3-pip wireguard-tools           # (Alpine)"
}

# ── Reporte final ──────────────────────────────────────────────────────────

print_summary() {
    local dry=""
    [ "$DRY_RUN" = true ] && dry=" [DRY-RUN — no se ejecutó nada]"
    echo ""
    info "=============================================="
    info "  PEER LINKGUARD DESINSTALADO${dry}"
    info "=============================================="
    echo ""
    info "Para verificar:"
    info "  systemctl status wg-auto-register.service 2>&1 | head -3 || echo '(eliminado)'"
    info "  ip link show $WG_IFACE 2>&1 || echo '(eliminado)'"
    info "  ls /opt/linkguard-peer 2>&1 || echo '(eliminado)'"
    info "  wg-auto-cli --help 2>&1 || echo '(eliminado)'"
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
    echo -e "${RED}║   LINKGUARD — DESINSTALAR PEER (wg-auto-register)   ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════════════╝${NC}"
    echo ""

    if [ "$(id -u)" -ne 0 ] && [ "$DRY_RUN" = false ]; then
        err "Debe ejecutarse como root (o con sudo)"
        err "Ejecute: sudo bash $0"
        exit 1
    fi

    echo "Se ELIMINARÁN los siguientes componentes del peer:"
    echo ""
    echo "  • Servicio: wg-auto-register (systemd + OpenRC)"
    echo "  • Interfaz WireGuard: $WG_IFACE"
    echo "  • Directorios: /opt/linkguard-peer/, /etc/linkguard/, /var/lib/linkguard/"
    echo "  • Archivos: wg-auto-cli, wg-auto-register, peer.env, claves WireGuard"
    echo ""

    if ! confirm "¿Desinstalar el peer LinkGuard?"; then
        info "Cancelado."
        exit 0
    fi

    stop_service
    remove_wg_interface
    remove_files
    remove_deps
    print_summary
    log "Desinstalación del peer completada."
}

main "$@"
