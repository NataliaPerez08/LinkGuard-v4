#!/usr/bin/env bash
# hub-agent-cleanup.sh
# Llamado por ExecStop del servicio hub-agent para limpiar reglas iptables.
# OPS-01: Elimina las reglas añadidas por hub-agent al arranque.

WG_IFACE="${HUB_WG_IFACE:-wg-HUB}"
NAT_IFACE="${HUB_NAT_OUT_IFACE:-eth0}"
TUNNEL_CIDR="${HUB_TUNNEL_CIDR:-10.20.30.0/24}"
IPTABLES="${IPTABLES_BIN:-/sbin/iptables}"

echo "[hub-agent-cleanup] Limpiando reglas iptables (iface=${WG_IFACE}, nat=${NAT_IFACE})..."

# Eliminar reglas silenciosamente (ignora error si ya no existen)
$IPTABLES -D FORWARD -i "$WG_IFACE" -o "$WG_IFACE" -j ACCEPT 2>/dev/null || true
$IPTABLES -D FORWARD -i "$WG_IFACE" -o "$NAT_IFACE" -j ACCEPT 2>/dev/null || true
$IPTABLES -D FORWARD -i "$NAT_IFACE" -o "$WG_IFACE" -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || true
$IPTABLES -t nat -D POSTROUTING -s "$TUNNEL_CIDR" -o "$NAT_IFACE" -j MASQUERADE 2>/dev/null || true

echo "[hub-agent-cleanup] Limpieza completada."
