#!/usr/bin/env bash
# ============================================================================
# uninstall-and-cleanup.sh — Desinstalación completa de LinkGuard
# ============================================================================
# Elimina TODOS los recursos de LinkGuard:
#   - Servicios systemd y procesos
#   - Reglas iptables (NAT + FORWARD)
#   - Interfaces de red (WireGuard, bridges, TAPs)
#   - Archivos de configuración, estado e instalación
#   - Opcionalmente en hosts remotos (orquestador + peers)
#
# Uso:
#   sudo bash scripts/uninstall-and-cleanup.sh [opciones]
#
# Opciones:
#   -y, --yes         No pedir confirmación (automático)
#   -n, --dry-run     Mostrar qué se haría sin ejecutarlo
#   --local-only      Limpiar solo el host local
#   --remote-only     Limpiar solo los hosts remotos
#   -h, --help        Mostrar ayuda
#
# Variables de entorno:
#   SUDO_PASS                Contraseña sudo local (si se requiere)
#   LINKGUARD_REMOTE_PASS    Contraseña SSH para hosts remotos
#   TESTBED_REAL_ORCH_PASS   Alternativa para LINKGUARD_REMOTE_PASS
# ============================================================================
set -euo pipefail

# ── Configuración ───────────────────────────────────────────────────────────

REMOTE_ORCH_HOST="${REMOTE_ORCH_HOST:-101.44.24.91}"
REMOTE_ORCH_USER="${REMOTE_ORCH_USER:-root}"
REMOTE_PEERS=(
    "46.250.168.185"
    "122.8.179.57"
    "46.250.162.141"
)
REMOTE_PEER_USER="${REMOTE_PEER_USER:-root}"
REMOTE_PASS="${LINKGUARD_REMOTE_PASS:-${TESTBED_REAL_ORCH_PASS:-}}"

# Redes del testbed QEMU
BR0=br0 BR1=br1 BR2=br2
BR0_NET="192.168.100.0/24"
BR1_NET="10.0.0.0/24"
BR2_NET="10.0.1.0/24"
TAPS=(tap{0..8})

# Redes del orquestador (hub-agent)
HUB_WG_IFACE="${HUB_WG_IFACE:-wg-HUB}"
PEER_WG_IFACE="${PEER_WG_IFACE:-wg0}"
HUB_TUNNEL_CIDR="${HUB_TUNNEL_CIDR:-10.20.30.0/24}"
HUB_NAT_IFACE="${HUB_NAT_IFACE:-}"

# Flags
FORCE=false
DRY_RUN=false
LOCAL_ONLY=false
REMOTE_ONLY=false

# ── Utilidades ──────────────────────────────────────────────────────────────

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*" >&2; }
info() { echo -e "${CYAN}[i]${NC} $*"; }

usage() {
    cat <<'EOF'
Uso: sudo bash scripts/uninstall-and-cleanup.sh [opciones]

Elimina todos los componentes de LinkGuard del sistema:
  - Servicios systemd y procesos QEMU/dnsmasq
  - Reglas iptables NAT y FORWARD
  - Interfaces WireGuard, bridges y TAPs
  - Archivos de instalación, configuración y estado
  - Opcionalmente en hosts remotos (orquestador + peers)

Opciones:
  -y, --yes         No pedir confirmación
  -n, --dry-run     Mostrar qué se haría sin ejecutarlo
  --local-only      Limpiar solo el host local
  --remote-only     Limpiar solo los hosts remotos
  -h, --help        Mostrar esta ayuda

Variables de entorno:
  SUDO_PASS                Contraseña sudo (si se requiere)
  LINKGUARD_REMOTE_PASS    Contraseña SSH para hosts remotos
  TESTBED_REAL_ORCH_PASS   Alternativa para LINKGUARD_REMOTE_PASS
EOF
    exit 0
}

out_iface() {
    ip route show default 2>/dev/null | awk '/default/ {print $5; exit}'
}

detect_nat_iface() {
    if [ -n "$HUB_NAT_IFACE" ]; then
        echo "$HUB_NAT_IFACE"
    else
        out_iface
    fi
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

sudo_dry_or_run() {
    local desc="$1"
    shift
    if [ "$DRY_RUN" = true ]; then
        info "[DRY-RUN] $desc"
        info "         sudo $*"
        return 0
    fi
    log "$desc"
    if [ -n "${SUDO_PASS:-}" ]; then
        echo "$SUDO_PASS" | sudo -S "$@" 2>/dev/null || true
    else
        sudo "$@" 2>/dev/null || true
    fi
}

remote_dry_or_run() {
    local host="$1"
    local desc="$2"
    shift 2
    local cmd_str="$*"
    if [ "$DRY_RUN" = true ]; then
        info "[DRY-RUN] [$host] $desc"
        info "         $cmd_str"
        return 0
    fi
    log "[$host] $desc"
    if [ -z "$REMOTE_PASS" ]; then
        warn "[$host] No hay REMOTE_PASS definido — saltando"
        return 1
    fi
    printf '%s\n' "$cmd_str" | sshpass -p "$REMOTE_PASS" ssh \
        -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10 \
        "${REMOTE_ORCH_USER}@${host}" sh 2>/dev/null || true
}

# ── Fase 1: Detener servicios locales ──────────────────────────────────────

stop_local_services() {
    info "=== Fase 1: Detener servicios locales ==="
    local services=()
    for svc in orchestrator.service hub-agent.service wg-auto-register.service; do
        if systemctl is-enabled "$svc" &>/dev/null 2>/dev/null || systemctl is-active "$svc" &>/dev/null 2>/dev/null; then
            services+=("$svc")
        fi
    done
    if [ ${#services[@]} -eq 0 ]; then
        info "No hay servicios systemd de LinkGuard activos"
    else
        for svc in "${services[@]}"; do
            sudo_dry_or_run "Deteniendo y deshabilitando $svc" \
                systemctl disable --now "$svc"
        done
    fi

    # OpenRC (Alpine/QEMU)
    if command -v rc-service &>/dev/null; then
        for svc in wg-auto-register; do
            if rc-service "$svc" status &>/dev/null 2>/dev/null; then
                sudo_dry_or_run "Deteniendo servicio OpenRC $svc" \
                    rc-service "$svc" stop
                sudo_dry_or_run "Eliminando servicio OpenRC $svc del runlevel" \
                    rc-update del "$svc" default
            fi
        done
    fi
}

kill_testbed_processes() {
    info "=== Matar procesos QEMU y dnsmasq ==="
    # Matar procesos QEMU por PID file
    local testbed_dir
    testbed_dir="$(dirname "$(dirname "$(readlink -f "$0")")")/testbed"
    local pid_dir="${testbed_dir}/pids"
    if [ -d "$pid_dir" ]; then
        for role in orq pa pb; do
            local pidfile="${pid_dir}/${role}.pid"
            if [ -f "$pidfile" ]; then
                local pid
                pid=$(cat "$pidfile" 2>/dev/null || true)
                if [ -n "$pid" ] && [ -d "/proc/${pid}" ]; then
                    sudo_dry_or_run "Matando QEMU $role (PID $pid)" \
                        kill "$pid"
                fi
                dry_or_run "Eliminando $pidfile" rm -f "$pidfile"
            fi
        done
    fi
    # Matar dnsmasq en br0
    if pgrep -f "dnsmasq.*br0" &>/dev/null; then
        sudo_dry_or_run "Matando dnsmasq en br0" \
            pkill -f "dnsmasq.*br0"
    fi
}

# ── Fase 2: Eliminar reglas iptables locales ───────────────────────────────

remove_local_iptables() {
    info "=== Fase 2: Eliminar reglas iptables ==="
    local nat_iface
    nat_iface="$(detect_nat_iface)"

    # Reglas del hub-agent
    info "Reglas del hub-agent..."
    if [ -n "$nat_iface" ]; then
        sudo_dry_or_run "nat/POSTROUTING: -s $HUB_TUNNEL_CIDR -o $nat_iface -j MASQUERADE" \
            iptables -t nat -D POSTROUTING -s "$HUB_TUNNEL_CIDR" -o "$nat_iface" -j MASQUERADE
        sudo_dry_or_run "FORWARD: -i $HUB_WG_IFACE -o $nat_iface -j ACCEPT" \
            iptables -D FORWARD -i "$HUB_WG_IFACE" -o "$nat_iface" -j ACCEPT
        sudo_dry_or_run "FORWARD: -i $nat_iface -o $HUB_WG_IFACE -m state --state RELATED,ESTABLISHED -j ACCEPT" \
            iptables -D FORWARD -i "$nat_iface" -o "$HUB_WG_IFACE" -m state --state RELATED,ESTABLISHED -j ACCEPT
    fi
    sudo_dry_or_run "FORWARD: -i $HUB_WG_IFACE -o $HUB_WG_IFACE -j ACCEPT" \
        iptables -D FORWARD -i "$HUB_WG_IFACE" -o "$HUB_WG_IFACE" -j ACCEPT

    # Reglas del testbed QEMU (bridges)
    info "Reglas del testbed QEMU..."
    if [ -n "$nat_iface" ]; then
        for net in "$BR0_NET" "$BR1_NET" "$BR2_NET"; do
            sudo_dry_or_run "nat/POSTROUTING: -s $net -o $nat_iface -j MASQUERADE" \
                iptables -t nat -D POSTROUTING -s "$net" -o "$nat_iface" -j MASQUERADE
        done
    fi
    for br in "$BR0" "$BR1" "$BR2"; do
        sudo_dry_or_run "FORWARD: -i $br -j ACCEPT" \
            iptables -D FORWARD -i "$br" -j ACCEPT
        sudo_dry_or_run "FORWARD: -o $br -j ACCEPT" \
            iptables -D FORWARD -o "$br" -j ACCEPT
    done

    # Limpieza adicional: buscar cualquier regla MASQUERADE residual de LinkGuard
    info "Reglas MASQUERADE residuales..."
    for net in "$HUB_TUNNEL_CIDR" "$BR0_NET" "$BR1_NET" "$BR2_NET"; do
        while iptables -t nat -C POSTROUTING -s "$net" -j MASQUERADE 2>/dev/null; do
            sudo_dry_or_run "nat/POSTROUTING (genérico): -s $net -j MASQUERADE" \
                iptables -t nat -D POSTROUTING -s "$net" -j MASQUERADE
        done
    done
}

# ── Fase 3: Eliminar interfaces de red locales ─────────────────────────────

remove_local_interfaces() {
    info "=== Fase 3: Eliminar interfaces de red ==="

    # WireGuard interfaces
    for wg_iface in "$HUB_WG_IFACE" "$PEER_WG_IFACE"; do
        if ip link show "$wg_iface" &>/dev/null 2>/dev/null; then
            sudo_dry_or_run "Bajando interfaz WireGuard $wg_iface (wg-quick)" \
                wg-quick down "$wg_iface"
            sudo_dry_or_run "Eliminando interfaz WireGuard $wg_iface" \
                ip link delete "$wg_iface"
        fi
    done

    # TAPs
    for tap in "${TAPS[@]}"; do
        if ip link show "$tap" &>/dev/null 2>/dev/null; then
            sudo_dry_or_run "Eliminando TAP $tap" \
                ip tuntap del "$tap" mode tap
        fi
    done

    # Bridges
    for br in "$BR0" "$BR1" "$BR2"; do
        if ip link show "$br" &>/dev/null 2>/dev/null; then
            sudo_dry_or_run "Bajando bridge $br" \
                ip link set "$br" down
            sudo_dry_or_run "Eliminando bridge $br" \
                ip link delete "$br"
        fi
    done
}

# ── Fase 4: Eliminar archivos locales ──────────────────────────────────────

remove_local_files() {
    info "=== Fase 4: Eliminar archivos de LinkGuard ==="
    local dirs_to_remove=(
        "/opt/linkguard-orchestrator"
        "/opt/linkguard-peer"
        "/etc/linkguard"
        "/var/lib/wg-orchestrator"
        "/var/lib/linkguard"
    )
    local files_to_remove=(
        "/etc/wireguard/${HUB_WG_IFACE}.conf"
        "/etc/wireguard/${HUB_WG_IFACE}.key"
        "/etc/wireguard/${HUB_WG_IFACE}.pub"
        "/etc/wireguard/${PEER_WG_IFACE}.conf"
        "/etc/wireguard/${PEER_WG_IFACE}.key"
        "/etc/wireguard/${PEER_WG_IFACE}.pub"
        "/etc/wireguard/wg-auto.json"
        "/usr/local/bin/orch-cli"
        "/usr/local/bin/wg-auto-register"
        "/usr/local/bin/wg-auto-cli"
    )
    local svc_files=(
        "/etc/systemd/system/orchestrator.service"
        "/etc/systemd/system/hub-agent.service"
        "/etc/systemd/system/wg-auto-register.service"
        "/etc/init.d/wg-auto-register"
    )

    for d in "${dirs_to_remove[@]}"; do
        if [ -e "$d" ]; then
            sudo_dry_or_run "Eliminando directorio $d" \
                rm -rf "$d"
        fi
    done
    for f in "${files_to_remove[@]}"; do
        if [ -e "$f" ]; then
            sudo_dry_or_run "Eliminando archivo $f" \
                rm -f "$f"
        fi
    done
    for f in "${svc_files[@]}"; do
        if [ -e "$f" ]; then
            sudo_dry_or_run "Eliminando unit file $f" \
                rm -f "$f"
        fi
    done

    # Recargar systemd daemon si se eliminaron units
    if [ "$DRY_RUN" = false ] && systemctl daemon-reload &>/dev/null 2>/dev/null; then
        log "systemd daemon recargado"
    fi
}

# ── Fase 5: Limpieza remota del orquestador ────────────────────────────────

cleanup_remote_orchestrator() {
    local host="$1"
    info "=== [REMOTO] Limpiando orquestador en $host ==="

    # Detectar interfaz NAT
    local nat_iface
    nat_iface="$(remote_dry_or_run "$host" "Detectando interfaz NAT" \
        "ip route show default 2>/dev/null | awk '/default/ {print \$5; exit}'" </dev/null 2>/dev/null || echo "")"

    if [ -z "$nat_iface" ]; then
        # Fallback: usar detección local si es dry-run, o eth0 por defecto
        if [ "$DRY_RUN" = true ]; then
            nat_iface="$(out_iface || echo 'eth0')"
        else
            nat_iface="eth0"
        fi
        warn "[$host] NAT iface no detectado, usando $nat_iface"
    fi

    remote_dry_or_run "$host" "Deteniendo orquestador.service" \
        "systemctl disable --now orchestrator.service 2>/dev/null || rc-service orchestrator stop 2>/dev/null || true"

    remote_dry_or_run "$host" "Deteniendo hub-agent.service" \
        "systemctl disable --now hub-agent.service 2>/dev/null || rc-service hub-agent stop 2>/dev/null || true"

    # Eliminar iptables del hub-agent
    remote_dry_or_run "$host" "Eliminando iptables FORWARD (wg-HUB)" \
        "iptables -D FORWARD -i ${HUB_WG_IFACE} -o ${HUB_WG_IFACE} -j ACCEPT 2>/dev/null || true; \
         iptables -D FORWARD -i ${HUB_WG_IFACE} -o ${nat_iface} -j ACCEPT 2>/dev/null || true; \
         iptables -D FORWARD -i ${nat_iface} -o ${HUB_WG_IFACE} -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || true"

    remote_dry_or_run "$host" "Eliminando iptables NAT (MASQUERADE)" \
        "iptables -t nat -D POSTROUTING -s ${HUB_TUNNEL_CIDR} -o ${nat_iface} -j MASQUERADE 2>/dev/null || true; \
         while iptables -t nat -C POSTROUTING -s ${HUB_TUNNEL_CIDR} -j MASQUERADE 2>/dev/null; do \
           iptables -t nat -D POSTROUTING -s ${HUB_TUNNEL_CIDR} -j MASQUERADE 2>/dev/null || break; \
         done"

    # Bajar y eliminar interfaz WireGuard
    remote_dry_or_run "$host" "Bajando y eliminando ${HUB_WG_IFACE}" \
        "wg-quick down ${HUB_WG_IFACE} 2>/dev/null || true; \
         ip link delete ${HUB_WG_IFACE} 2>/dev/null || true"

    # Eliminar archivos
    remote_dry_or_run "$host" "Eliminando archivos del orquestador" \
        "rm -rf /opt/linkguard-orchestrator /etc/linkguard /var/lib/wg-orchestrator \
                /etc/wireguard/${HUB_WG_IFACE}.conf /etc/wireguard/${HUB_WG_IFACE}.key \
                /etc/wireguard/${HUB_WG_IFACE}.pub \
                /usr/local/bin/orch-cli \
                /etc/systemd/system/orchestrator.service \
                /etc/systemd/system/hub-agent.service"

    remote_dry_or_run "$host" "Recargando systemd" \
        "systemctl daemon-reload 2>/dev/null || true"
}

# ── Fase 6: Limpieza remota de peers ──────────────────────────────────────

cleanup_remote_peer() {
    local host="$1"
    info "=== [REMOTO] Limpiando peer en $host ==="

    remote_dry_or_run "$host" "Deteniendo wg-auto-register" \
        "systemctl disable --now wg-auto-register.service 2>/dev/null || \
         rc-service wg-auto-register stop 2>/dev/null || true"

    remote_dry_or_run "$host" "Bajando y eliminando ${PEER_WG_IFACE}" \
        "wg-quick down ${PEER_WG_IFACE} 2>/dev/null || true; \
         ip link delete ${PEER_WG_IFACE} 2>/dev/null || true"

    remote_dry_or_run "$host" "Eliminando archivos del peer" \
        "rm -rf /opt/linkguard-peer /etc/linkguard /var/lib/linkguard \
                /etc/wireguard/${PEER_WG_IFACE}.conf /etc/wireguard/${PEER_WG_IFACE}.key \
                /etc/wireguard/${PEER_WG_IFACE}.pub /etc/wireguard/wg-auto.json \
                /usr/local/bin/wg-auto-register /usr/local/bin/wg-auto-cli \
                /etc/systemd/system/wg-auto-register.service"

    remote_dry_or_run "$host" "Recargando systemd" \
        "systemctl daemon-reload 2>/dev/null || true"
}

# ── Reporte final ──────────────────────────────────────────────────────────

print_summary() {
    local local_cleaned=false
    local remote_orch_cleaned=false
    local remote_peers_cleaned=0
    local dry=""
    [ "$DRY_RUN" = true ] && dry=" [DRY-RUN - no se ejecutó nada]"

    echo ""
    info "=============================================="
    info "  RESUMEN DE LIMPIEZA${dry}"
    info "=============================================="
    echo ""
    if [ "$REMOTE_ONLY" = false ]; then
        echo "  Local:              servicios, iptables, interfaces, archivos"
    fi
    if [ "$LOCAL_ONLY" = false ] && [ -n "$REMOTE_PASS" ]; then
        echo "  Orquestador remoto: $REMOTE_ORCH_HOST"
        echo "  Peers remotos:      ${REMOTE_PEERS[*]}"
    fi
    echo ""
    info "Para verificar:"
    info "  iptables -t nat -L POSTROUTING -n  | grep -E '(10\.20\.30|192\.168\.100|10\.0\.)'"
    info "  iptables -L FORWARD -n | grep -E '(wg-HUB|wg0|br0|br1|br2)'"
    info "  ip link show | grep -E '(wg-HUB|wg0|br[0-2]|tap[0-9])'"
    info "  ls /opt/linkguard-* /etc/linkguard /var/lib/wg-* 2>&1 || echo '(no existe)'"
    echo ""
}

# ── Main ────────────────────────────────────────────────────────────────────

main() {
    # Parsear argumentos
    while [ $# -gt 0 ]; do
        case "$1" in
            -h|--help) usage ;;
            -y|--yes) FORCE=true; shift ;;
            -n|--dry-run) DRY_RUN=true; shift ;;
            --local-only) LOCAL_ONLY=true; REMOTE_ONLY=false; shift ;;
            --remote-only) LOCAL_ONLY=false; REMOTE_ONLY=true; shift ;;
            *) warn "Opción desconocida: $1"; usage ;;
        esac
    done

    # Banner
    echo ""
    echo -e "${RED}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║       LINKGUARD — DESINSTALACIÓN COMPLETA          ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Verificar root
    if [ "$(id -u)" -ne 0 ] && [ "$DRY_RUN" = false ]; then
        err "Este script debe ejecutarse como root (o con sudo)"
        err "Ejecuta: sudo bash $0"
        exit 1
    fi

    # Resumen de lo que se va a hacer
    info "Esto ELIMINARÁ todos los componentes de LinkGuard:"
    echo ""
    if [ "$REMOTE_ONLY" = false ]; then
        echo "  • Servicios systemd locales (orchestrator, hub-agent, wg-auto-register)"
        echo "  • Procesos QEMU y dnsmasq del testbed"
        echo "  • Reglas iptables NAT y FORWARD"
        echo "  • Interfaces: $HUB_WG_IFACE, $PEER_WG_IFACE, $BR0, $BR1, $BR2, TAPs"
        echo "  • Archivos: /opt/linkguard-*, /etc/linkguard, /var/lib/wg-*, /etc/wireguard/*"
    fi
    if [ "$LOCAL_ONLY" = false ]; then
        if [ -z "$REMOTE_PASS" ]; then
            warn "LINKGUARD_REMOTE_PASS no definido — se saltará la limpieza remota"
        else
            echo "  • [$REMOTE_ORCH_HOST] Orquestador remoto (servicios, iptables, wg-HUB, archivos)"
            for peer in "${REMOTE_PEERS[@]}"; do
                echo "  • [$peer] Peer remoto (servicio, wg0, archivos)"
            done
        fi
    fi
    echo ""

    if ! confirm "¿Continuar con la desinstalación?"; then
        info "Cancelado."
        exit 0
    fi

    # ── Ejecutar fases ─────────────────────────────────────────────────────

    if [ "$REMOTE_ONLY" = false ]; then
        stop_local_services
        kill_testbed_processes
        remove_local_iptables
        remove_local_interfaces
        remove_local_files
    fi

    if [ "$LOCAL_ONLY" = false ] && [ -n "$REMOTE_PASS" ]; then
        cleanup_remote_orchestrator "$REMOTE_ORCH_HOST"
        for peer in "${REMOTE_PEERS[@]}"; do
            cleanup_remote_peer "$peer"
        done
    elif [ "$LOCAL_ONLY" = false ] && [ -z "$REMOTE_PASS" ]; then
        warn "Saltando limpieza remota — defina LINKGUARD_REMOTE_PASS o TESTBED_REAL_ORCH_PASS"
    fi

    print_summary
    log "Desinstalación completada."
}

main "$@"
