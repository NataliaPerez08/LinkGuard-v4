#!/bin/bash
# Lanza el testbed completo: 3 VMs QEMU + provisioning.
# Uso: bash launch-testbed.sh [up|down|ssh|test]
set -euo pipefail

BDIR="$(cd "$(dirname "$0")/.." && pwd)"
RAW="$BDIR/images/alpine-base.raw"
PID_DIR="$BDIR/pids"
SSH_KEY="$BDIR/ssh/id_ed25519"
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5"

ORQ_IP=192.168.100.10
PA_IP=192.168.100.20
PB_IP=192.168.100.30
PASS=linkguard-test

# --- funciones VM ---

qemu_base() {
    local name=$1 mac0=$2 mac1=$2 mac2=$4 tap0=$5 tap1=$6 tap2=$7
    local img=$8 pidfile=$9
    local mac_base="52:54:00:$(printf '%02x' $((0x${mac0//:/})))"
    cat <<CMD
qemu-system-x86_64 \
    -nographic -m 256M -smp 1 \
    -drive file=$img,format=raw,if=virtio \
    -netdev tap,id=net0,ifname=$tap0,script=no,downscript=no \
    -device virtio-net,netdev=net0,mac=$mac0 \
    -netdev tap,id=net1,ifname=$tap1,script=no,downscript=no \
    -device virtio-net,netdev=net1,mac=$mac1 \
    -netdev tap,id=net2,ifname=$tap2,script=no,downscript=no \
    -device virtio-net,netdev=net2,mac=$mac2 \
    -pidfile $pidfile
CMD
}

# MACs para cada VM (orq, pa, pb) x 3 interfaces
declare -A MACS
MACS[orq0]=52:54:00:01:00:10  MACS[orq1]=52:54:00:01:01:10  MACS[orq2]=52:54:00:01:02:10
MACS[pa0]=52:54:00:01:00:20   MACS[pa1]=52:54:00:01:01:20   MACS[pa2]=52:54:00:01:02:20
MACS[pb0]=52:54:00:01:00:30   MACS[pb1]=52:54:00:01:01:30   MACS[pb2]=52:54:00:01:02:30

up() {
    mkdir -p "$PID_DIR"
    # Clonar imagenes para cada VM
    for role in orq pa pb; do
        local img="$BDIR/images/$role.raw"
        if [ ! -f "$img" ]; then
            echo "Creando $img ..."
            cp "$RAW" "$img"
            qemu-img resize "$img" +1G 2>/dev/null || true
        fi
    done

    # Lanzar VMs
    echo "Lanzando orchestrator ..."
    $($(qemu_base orq \
        "${MACS[orq0]}" "${MACS[orq1]}" "${MACS[orq2]}" \
        tap0 tap1 tap2 \
        "$BDIR/images/orq.raw" "$PID_DIR/orq.pid") &>/tmp/orq.log &)

    echo "Lanzando peer-a ..."
    $($(qemu_base pa \
        "${MACS[pa0]}" "${MACS[pa1]}" "${MACS[pa2]}" \
        tap3 tap4 tap5 \
        "$BDIR/images/pa.raw" "$PID_DIR/pa.pid") &>/tmp/pa.log &)

    echo "Lanzando peer-b ..."
    $($(qemu_base pb \
        "${MACS[pb0]}" "${MACS[pb1]}" "${MACS[pb2]}" \
        tap6 tap7 tap8 \
        "$BDIR/images/pb.raw" "$PID_DIR/pb.pid") &>/tmp/pb.log &)

    echo "Esperando 30s para boot inicial ..."
    sleep 30

    # Provisionar cada VM
    for role in orq pa pb; do
        provision_$role
    done
    echo "Testbed listo"
}

down() {
    for role in orq pa pb; do
        local pidfile="$PID_DIR/$role.pid"
        if [ -f "$pidfile" ]; then
            kill "$(cat "$pidfile")" 2>/dev/null || true
            rm -f "$pidfile"
        fi
    done
    echo "Testbed detenido"
}

ssh_vm() {
    local ip=$1; shift
    sshpass -p "$PASS" ssh $SSH_OPTS "root@$ip" "$@"
}

wait_ssh() {
    local ip=$1
    for i in $(seq 1 30); do
        if sshpass -p "$PASS" ssh $SSH_OPTS "root@$ip" true 2>/dev/null; then
            return 0
        fi
        sleep 2
    done
    return 1
}

provision_orq() {
    local ip=$ORQ_IP
    echo "Esperando SSH en orchestrator ($ip) ..."
    wait_ssh $ip || { echo "ERROR: no SSH a $ip"; return 1; }
    # Configurar interfaces de red
    ssh_vm $ip "cat > /etc/network/interfaces << 'EOF'
auto lo
iface lo inet loopback
auto eth0
iface eth0 inet static
    address $ip/24
    gateway 192.168.100.1
auto eth1
iface eth1 inet static
    address 10.0.0.10/24
auto eth2
iface eth2 inet dhcp
EOF
rc-service networking restart"
    echo "orchestrator provisionado"
}

provision_pa() {
    local ip=$PA_IP
    echo "Esperando SSH en peer-a ($ip) ..."
    wait_ssh $ip || { echo "ERROR: no SSH a $ip"; return 1; }
    ssh_vm $ip "cat > /etc/network/interfaces << 'EOF'
auto lo
iface lo inet loopback
auto eth0
iface eth0 inet static
    address $ip/24
    gateway 192.168.100.1
auto eth1
iface eth1 inet static
    address 10.0.0.20/24
auto eth2
iface eth2 inet dhcp
EOF
rc-service networking restart"
    echo "peer-a provisionado"
}

provision_pb() {
    local ip=$PB_IP
    echo "Esperando SSH en peer-b ($ip) ..."
    wait_ssh $ip || { echo "ERROR: no SSH a $ip"; return 1; }
    ssh_vm $ip "cat > /etc/network/interfaces << 'EOF'
auto lo
iface lo inet loopback
auto eth0
iface eth0 inet static
    address $ip/24
    gateway 192.168.100.1
auto eth1
iface eth1 inet static
    address 10.0.0.30/24
auto eth2
iface eth2 inet dhcp
EOF
rc-service networking restart"
    echo "peer-b provisionado"
}

case "${1:-up}" in
    up) up ;;
    down) down ;;
    ssh) shift; ssh_vm "$@" ;;
    test) echo "TODO: run integration tests" ;;
    *) echo "Uso: $0 [up|down|ssh|test]"; exit 1 ;;
esac
