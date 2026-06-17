#!/bin/bash
# Crea bridges y tap interfaces para el testbed QEMU.
# Uso: sudo bash setup-network.sh [create|destroy]
set -euo pipefail

BR0=br0 BR1=br1 BR2=br2
BR0_IP=192.168.100.1 BR1_IP=10.0.0.1 BR2_IP=10.0.1.1
BR0_NET=192.168.100.0/24
BR1_NET=10.0.0.0/24
BR2_NET=10.0.1.0/24
TAP_ORQ=(tap0 tap1 tap2)
TAP_PA=(tap3 tap4 tap5)
TAP_PB=(tap6 tap7 tap8)

out_iface() {
    ip route show default | awk '/default/ {print $5; exit}'
}

create() {
    OUT_IF="$(out_iface)"
    [ -n "$OUT_IF" ] || { echo "No pude detectar la interfaz de salida" >&2; exit 1; }

    # Bridges
    for br in $BR0 $BR1 $BR2; do
        ip link show $br 2>/dev/null || ip link add $br type bridge
    done
    ip addr add $BR0_IP/24 dev $BR0 2>/dev/null || true
    ip addr add $BR1_IP/24 dev $BR1 2>/dev/null || true
    ip addr add $BR2_IP/24 dev $BR2 2>/dev/null || true
    ip link set $BR0 up; ip link set $BR1 up; ip link set $BR2 up

    # TAPs orchestrator -> br0, br1, br2
    for tap in "${TAP_ORQ[@]}"; do
        ip tuntap add $tap mode tap user $SUDO_USER 2>/dev/null || true
        ip link set $tap up
    done
    ip link set tap0 master $BR0
    ip link set tap1 master $BR1
    ip link set tap2 master $BR2

    # TAPs peer-a -> br0, br1, br2
    for tap in "${TAP_PA[@]}"; do
        ip tuntap add $tap mode tap user $SUDO_USER 2>/dev/null || true
        ip link set $tap up
    done
    ip link set tap3 master $BR0
    ip link set tap4 master $BR1
    ip link set tap5 master $BR2

    # TAPs peer-b -> br0, br1, br2
    for tap in "${TAP_PB[@]}"; do
        ip tuntap add $tap mode tap user $SUDO_USER 2>/dev/null || true
        ip link set $tap up
    done
    ip link set tap6 master $BR0
    ip link set tap7 master $BR1
    ip link set tap8 master $BR2

    # NAT saliente para que las VMs puedan alcanzar la red real desde el host.
    for net in $BR0_NET $BR1_NET $BR2_NET; do
        iptables -t nat -C POSTROUTING -s $net -o $OUT_IF -j MASQUERADE 2>/dev/null || \
            iptables -t nat -A POSTROUTING -s $net -o $OUT_IF -j MASQUERADE
    done

    # Forwarding
    sysctl -w net.ipv4.ip_forward=1 >/dev/null
    for br in $BR0 $BR1 $BR2; do
        iptables -C FORWARD -i $br -j ACCEPT 2>/dev/null || \
            iptables -A FORWARD -i $br -j ACCEPT
        iptables -C FORWARD -o $br -j ACCEPT 2>/dev/null || \
            iptables -A FORWARD -o $br -j ACCEPT
    done

    echo "OK: bridges and taps created"
    for b in $BR0 $BR1 $BR2; do
        ip addr show $b 2>/dev/null | grep inet
    done
}

destroy() {
    OUT_IF="$(out_iface)"

    # TAPs
    for tap in tap{0..8}; do
        ip tuntap del $tap mode tap 2>/dev/null || true
    done
    # Bridges
    for br in $BR0 $BR1 $BR2; do
        ip link set $br down 2>/dev/null || true
        ip link delete $br 2>/dev/null || true
    done
    # NAT y forwarding
    if [ -n "$OUT_IF" ]; then
        for net in $BR0_NET $BR1_NET $BR2_NET; do
            iptables -t nat -D POSTROUTING -s $net -o $OUT_IF -j MASQUERADE 2>/dev/null || true
        done
    fi
    for br in $BR0 $BR1 $BR2; do
        iptables -D FORWARD -i $br -j ACCEPT 2>/dev/null || true
        iptables -D FORWARD -o $br -j ACCEPT 2>/dev/null || true
    done
    echo "OK: bridges and taps destroyed"
}

case "${1:-create}" in
    create) create ;;
    destroy) destroy ;;
    *) echo "Uso: $0 [create|destroy]"; exit 1 ;;
esac
