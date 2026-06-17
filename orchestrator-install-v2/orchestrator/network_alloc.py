"""
Helpers de asignacion de IPs dentro de redes WireGuard.
"""

import ipaddress
from typing import Optional, List

from . import config, state


def _allocate_ip_in_network(net_cidr: str, existing_ips: List[str]) -> Optional[str]:
    try:
        net = ipaddress.ip_network(net_cidr, strict=False)
    except Exception:
        return None
    used = set()
    for ip_str in existing_ips:
        try:
            used.add(ipaddress.ip_address(ip_str.split("/")[0]))
        except ValueError:
            pass
    # La primera IP util (.1) queda reservada para el HUB de WireGuard.
    for ip_int in range(int(net.network_address) + 2, int(net.broadcast_address)):
        ip = ipaddress.ip_address(ip_int)
        if ip not in used:
            return str(ip)
    return None


def _ensure_network_alloc_struct(n: dict) -> None:
    if "alloc" not in n or not isinstance(n["alloc"], dict):
        n["alloc"] = {"reserved": [], "assigned": {}}
    n["alloc"].setdefault("reserved", [])
    n["alloc"].setdefault("assigned", {})


def _network_release_ip(network_id: str, peer_id: str) -> None:
    with state.LOCK_NETWORKS:
        n = state.STATE["networks"].get(network_id)
        if not n:
            return
        _ensure_network_alloc_struct(n)
        released = n["alloc"]["assigned"].pop(peer_id, None)
        if released:
            state.STATE["networks"][network_id] = n
            config.log(f"IP {released} devuelta al pool de red '{network_id}'")


def _assign_ip_to_peer_in_network(peer_id: str, net_id: str) -> Optional[str]:
    with state.LOCK_NETWORKS:
        net = state.STATE["networks"].get(net_id)
        if not net:
            return None
        net_cidr = net.get("cidr", net.get("ip", ""))
    existing = []
    with state.LOCK_PEERS:
        for pid, p in state.STATE["peers"].items():
            if net_id in (p.get("networks") or []) and p.get("ip"):
                existing.append(p["ip"])
        peer = state.STATE["peers"].get(peer_id)
        if peer and peer.get("ip") and net_id in (peer.get("networks") or []):
            return peer["ip"]
    ip = _allocate_ip_in_network(net_cidr, existing)
    if ip:
        config.log(f"Asignada IP {ip} a peer {peer_id} en red {net_id}")
    return ip
