"""
Endpoints RPC de gestion de redes.
"""

import secrets
from typing import Any, Dict

from . import config, state, auth


def _extract_owner_id(params: Dict[str, Any]) -> str:
    return str(params.get("user_id") or params.get("owner") or params.get("tenant") or "default")


def rpc_network_create(params: Dict[str, Any]) -> Dict[str, Any]:
    net_id = str(params.get("net_id") or params.get("network_id") or ("n_" + secrets.token_hex(8)))
    cidr = str(params.get("cidr") or "")
    if not cidr:
        raise ValueError("cidr is required")
    user_id = _extract_owner_id(params)
    if user_id != "admin":
        auth._check_network_quota(user_id)
    with state.LOCK_NETWORKS:
        if net_id in state.STATE["networks"]:
            raise ValueError(f"network already exists: {net_id}")
        state.STATE["networks"][net_id] = {
            "cidr": cidr,
            "description": str(params.get("description", "")),
            "user_id": user_id,
            "tag": str(params.get("tag", "")),
            "created_ts": state.now_ts(),
        }
        state.persist()
    state.add_event("network_created", {"network_id": net_id, "cidr": cidr})
    return {"network_id": net_id, "cidr": cidr}


def rpc_network_delete(params: Dict[str, Any]) -> Dict[str, Any]:
    net_id = str(params.get("net_id") or params.get("network_id") or "")
    if not net_id:
        raise ValueError("network_id is required")
    with state.LOCK_NETWORKS:
        if net_id not in state.STATE["networks"]:
            raise KeyError("network not found")
        del state.STATE["networks"][net_id]
        state.persist()
    state.add_event("network_deleted", {"network_id": net_id})
    return {"deleted": True}


def rpc_network_list(params: Dict[str, Any]) -> Dict[str, Any]:
    with state.LOCK_NETWORKS:
        return {"networks": dict(state.STATE["networks"])}


def rpc_network_get(params: Dict[str, Any]) -> Dict[str, Any]:
    net_id = str(params.get("net_id") or params.get("network_id") or "")
    if not net_id:
        raise ValueError("network_id is required")
    with state.LOCK_NETWORKS:
        net = state.STATE["networks"].get(net_id)
    if not net:
        raise KeyError("network not found")
    return {"network": net}


def rpc_network_set_topology(params: Dict[str, Any]) -> Dict[str, Any]:
    net_id = str(params.get("net_id") or params.get("network_id") or "")
    topology = str(params.get("topology", "hub-spoke"))
    if topology not in config.VALID_TOPOLOGIES:
        raise ValueError(f"invalid topology: {topology}")
    with state.LOCK_NETWORKS:
        if net_id not in state.STATE["networks"]:
            raise KeyError("network not found")
        state.STATE["networks"][net_id]["topology"] = topology
        state.persist()
    state.add_event("network_topology_changed", {"network_id": net_id, "topology": topology})
    return {"topology": topology}


def rpc_network_peers(params: Dict[str, Any]) -> Dict[str, Any]:
    net_id = str(params.get("net_id") or params.get("network_id") or "")
    if not net_id:
        raise ValueError("network_id is required")
    result = {}
    with state.LOCK_PEERS:
        for pid, p in state.STATE["peers"].items():
            if net_id in (p.get("networks") or []):
                result[pid] = p
    return {"peers": result, "count": len(result)}


def rpc_network_get_topology(params: Dict[str, Any]) -> Dict[str, Any]:
    net_id = str(params.get("network_id") or "")
    if not net_id:
        raise ValueError("network_id is required")
    with state.LOCK_NETWORKS:
        n = state.STATE["networks"].get(net_id)
    if not n:
        raise KeyError("network not found")
    assigned = (n.get("alloc") or {}).get("assigned") or {}
    peers_info = {}
    with state.LOCK_PEERS:
        for pid, ip_s in assigned.items():
            p = state.STATE["peers"].get(pid) or {}
            peers_info[pid] = {
                "tunnel_ip": ip_s, "endpoint": p.get("endpoint"),
                "tags": p.get("tags", []), "user_id": p.get("user_id"),
            }
    return {"network_id": net_id, **n, "peers": peers_info}
