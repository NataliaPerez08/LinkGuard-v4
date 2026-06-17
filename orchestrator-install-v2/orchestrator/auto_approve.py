"""
Logica de auto-aprobacion de peers.
Reglas, default network y aprobacion automatica.
"""

import json
import secrets
from typing import Dict, Any, Optional

from . import config, state, hub_client, network_alloc


def _ensure_default_network() -> str:
    net_id = config.DEFAULT_NET_ID
    with state.LOCK_NETWORKS:
        if net_id not in state.STATE["networks"]:
            state.STATE["networks"][net_id] = {
                "cidr": config.DEFAULT_NET_CIDR,
                "description": "Default auto-approve network",
                "user_id": "system",
                "tag": "",
                "created_ts": state.now_ts(),
            }
            state.persist()
            config.log(f"Red por defecto creada: {net_id} -> {config.DEFAULT_NET_CIDR}")
    return net_id


def try_auto_approve(public_key: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    if not config.AUTO_APPROVE_ENABLED or not config.AUTO_APPROVE_RULES:
        return None

    md = metadata or {}
    tag = md.get("tag") or md.get("auto_approve_tag") or ""
    cidr = config.AUTO_APPROVE_RULES.get(tag)
    if not cidr:
        config.log(f"Auto-approve: sin regla para tag='{tag}', ignorando")
        return None

    net_id = _ensure_default_network()
    peers_by_pubkey: Dict[str, Any] = {}
    with state.LOCK_PEERS:
        for pid, p in state.STATE["peers"].items():
            peers_by_pubkey[p.get("public_key", "")] = pid

    if str(public_key) in peers_by_pubkey:
        config.log(f"Auto-approve: peer ya existe (public_key={public_key[:16]}...), omitiendo")
        return None

    peer_id = md.get("peer_id") or ("p_" + secrets.token_hex(8))

    with state.LOCK_PEERS:
        all_existing_ips = [p["ip"] for p in state.STATE["peers"].values() if p.get("ip")]
    ip = network_alloc._allocate_ip_in_network(cidr, all_existing_ips)
    if not ip:
        config.log(f"Auto-approve: no hay IPs libres en {cidr}")
        return None

    peer = {
        "public_key": public_key,
        "ip": ip,
        "networks": [net_id],
        "user_id": "system",
        "metadata": md,
        "enabled": True,
        "created_ts": state.now_ts(),
        "keepalive": config.MESH_DEFAULT_KEEPALIVE,
    }

    with state.LOCK_PEERS:
        state.STATE["peers"][peer_id] = peer
        state.persist()

    state.add_event("peer_auto_approved", {"peer_id": peer_id, "ip": ip, "tag": tag})
    config.log(f"Peer auto-aprobado: {peer_id} -> {ip} (tag={tag})")
    hub_client._hub_apply_peer_allowed_ips(peer_id)

    return {"peer_id": peer_id, "ip": ip}
