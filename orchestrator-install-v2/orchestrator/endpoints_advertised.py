"""
Endpoints RPC para peers con IPs publicas anunciadas (advertised).
"""

from typing import Any, Dict

from . import config, state


def rpc_advertised_ips(params: Dict[str, Any]) -> Dict[str, Any]:
    net_id = str(params.get("network_id") or config.DEFAULT_NET_ID)
    advertised = {}
    with state.LOCK_PEERS:
        for pid, p in state.STATE["peers"].items():
            ip = p.get("ip")
            pubkey = p.get("public_key", "")
            hostname = (p.get("metadata") or {}).get("hostname", "")
            if net_id in (p.get("networks") or []):
                if p.get("enabled", True) and ip:
                    ts = p.get("last_heartbeat", 0)
                    advertised[pid] = {"ip": ip, "public_key": pubkey, "hostname": hostname, "last_seen": ts}
    return {"network_id": net_id, "peers": advertised, "count": len(advertised)}


def rpc_advertised_endpoint(params: Dict[str, Any]) -> Dict[str, Any]:
    peer_id = str(params.get("peer_id") or "")
    endpoint = str(params.get("endpoint") or "")
    if not peer_id or not endpoint:
        raise ValueError("peer_id and endpoint are required")
    with state.LOCK_PEERS:
        if peer_id not in state.STATE["peers"]:
            raise KeyError("peer not found")
        state.STATE["peers"][peer_id].setdefault("metadata", {})
        state.STATE["peers"][peer_id]["metadata"]["advertised_endpoint"] = endpoint
        state.persist()
    return {"recorded": True}


def rpc_advertised_unset(params: Dict[str, Any]) -> Dict[str, Any]:
    peer_id = str(params.get("peer_id") or "")
    if not peer_id:
        raise ValueError("peer_id is required")
    with state.LOCK_PEERS:
        if peer_id not in state.STATE["peers"]:
            raise KeyError("peer not found")
        state.STATE["peers"][peer_id].setdefault("metadata", {}).pop("advertised_endpoint", None)
        state.persist()
    return {"unset": True}
