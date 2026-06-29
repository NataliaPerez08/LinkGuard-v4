"""
Endpoints RPC de configuracion y mantenimiento.
"""

import hashlib
import json
from typing import Any, Dict

from . import config, state


def rpc_config_get(params: Dict[str, Any]) -> Dict[str, Any]:
    return {"config_version": state.STATE.get("config_version"), "state_version": state.STATE.get("version")}


def rpc_config_get_peer_config(params: Dict[str, Any]) -> Dict[str, Any]:
    from . import auth as auth_mod, hub_client

    peer_id = str(params.get("peer_id") or "")
    token = params.get("token")
    auth_mode, uid, scopes, is_admin_jwt = auth_mod._auth_from_token(token)
    if auth_mode != "jwt":
        raise PermissionError("authentication required: provide a valid JWT")
    auth_mod._require_scope(scopes, "config:read")
    if not is_admin_jwt:
        auth_mod._enforce_tenant_for_peer(str(uid or ""), peer_id)

    with state.LOCK_PEERS:
        peer = state.STATE["peers"].get(peer_id)
    if not peer:
        raise KeyError("peer not found")
    network_ids = list(peer.get("networks") or [])
    if not network_ids:
        raise RuntimeError("peer has no assigned network")
    network_id = network_ids[0]
    with state.LOCK_NETWORKS:
        network = state.STATE["networks"].get(network_id)
    if not network:
        raise KeyError("network not found")

    topology = str(network.get("topology") or "hub-spoke")
    keepalive = int(peer.get("keepalive") or config.MESH_DEFAULT_KEEPALIVE)
    response = {
        "interface": {
            "address": f"{peer.get('ip')}/32",
            "mtu": config.WG_MTU,
        },
        "peer": {
            "public_key": hub_client._hub_call_with_retry("hub.public_key", config.HUB_AGENT_TOKEN),
            "endpoint": config.HUB_ENDPOINT,
            "allowed_ips": network.get("hub_mesh_relay_fallback_cidr") or network.get("cidr"),
            "persistent_keepalive": keepalive,
        },
        "meta": {
            "topology": topology,
            "config_version": int(state.STATE.get("config_version", 1)),
            "requester_nat_type": peer.get("nat_type", "unknown") if topology == "hub-mesh" else None,
        },
    }

    if topology == "mesh":
        mesh_peers = _get_alive_mesh_peers(peer_id, network_id)
        response["mesh_peers"] = mesh_peers
        response["meta"]["mesh_peers_hash"] = hashlib.sha256(
            json.dumps(mesh_peers, sort_keys=True).encode()
        ).hexdigest()
    elif topology == "hub-mesh":
        classified = _classify_peers_for_hub_mesh(peer_id, network_id)
        response["hub_mesh_direct_peers"] = classified["direct"]
        response["hub_mesh_relay_peers"] = classified["relay_only"]
        response["peer"]["allowed_ips"] = classified.get("relay_cidr") or network.get("cidr")
        response["meta"]["hub_mesh_peers_hash"] = hashlib.sha256(
            json.dumps(classified["direct"], sort_keys=True).encode()
        ).hexdigest()

    return response


def rpc_config_reload(params: Dict[str, Any]) -> Dict[str, Any]:
    from importlib import reload
    reload(config)
    config.log("Recarga de configuracion solicitada via RPC")
    return {"reloaded": True}


def rpc_state_reset(params: Dict[str, Any]) -> Dict[str, Any]:
    confirm = str(params.get("confirm", ""))
    if confirm != "RESET":
        raise ValueError("must pass confirm=RESET")
    from .state import DEFAULT_STATE, load_state, persist
    with state.LOCK_STATE:
        state.STATE.update(json.loads(json.dumps(DEFAULT_STATE)))
        persist()
    state.add_event("state_reset", {"trigger": "rpc_state_reset"})
    return {"reset": True}


def _get_alive_mesh_peers(requester_peer_id: str, network_id: str) -> list:
    now = state.now_ts()
    with state.LOCK_NETWORKS:
        n = state.STATE["networks"].get(network_id)
    if not n:
        return []
    assigned = (n.get("alloc") or {}).get("assigned") or {}
    result = []
    with state.LOCK_PEERS:
        for pid, tunnel_ip in assigned.items():
            if pid == requester_peer_id:
                continue
            p = state.STATE["peers"].get(pid)
            if not p:
                continue
            last_hb = int(p.get("last_heartbeat") or 0)
            alive = last_hb > 0 and (now - last_hb) <= config.HEARTBEAT_TTL_SEC
            result.append({
                "peer_id": pid, "public_key": p.get("public_key") or "",
                "endpoint": p.get("endpoint"), "tunnel_ip": tunnel_ip,
                "alive": alive, "last_seen_ts": last_hb,
            })
    result.sort(key=lambda x: (not x["alive"], x["peer_id"]))
    return result[:config.MESH_MAX_PEERS]


def _classify_peers_for_hub_mesh(requester_peer_id: str, network_id: str) -> dict:
    now = state.now_ts()
    with state.LOCK_NETWORKS:
        n = state.STATE["networks"].get(network_id)
    if not n:
        return {"direct": [], "relay_only": [], "relay_cidr": "0.0.0.0/0"}
    assigned = (n.get("alloc") or {}).get("assigned") or {}
    relay_cidr = n.get("hub_mesh_relay_fallback_cidr") or n.get("cidr", "0.0.0.0/0")
    direct = []
    relay_only = []
    with state.LOCK_PEERS:
        requester = state.STATE["peers"].get(requester_peer_id) or {}
        req_rm = requester.get("reachability_map") or {}
        requester_nat_type = requester.get("nat_type", "")
        for pid, tunnel_ip in assigned.items():
            if pid == requester_peer_id:
                continue
            p = state.STATE["peers"].get(pid)
            if not p:
                continue
            last_hb = int(p.get("last_heartbeat") or 0)
            alive = last_hb > 0 and (now - last_hb) <= config.HEARTBEAT_TTL_SEC
            if not alive:
                continue
            nat_type = p.get("nat_type")
            relay_mode = p.get("relay_mode", "auto")
            endpoint = p.get("endpoint")
            req_reported_relay = req_rm.get(pid) == "hub-relay"
            rec = {
                "peer_id": pid, "public_key": p.get("public_key") or "",
                "endpoint": endpoint, "tunnel_ip": tunnel_ip,
                "nat_type": nat_type, "relay_mode": relay_mode,
                "alive": True, "last_seen_ts": last_hb,
            }
            # FIX: symmetric NAT requester cannot complete P2P handshakes
            # because target peers won't have a [Peer] block for them.
            # Force all peers to relay-only for symmetric NAT requesters.
            if requester_nat_type == "symmetric":
                is_direct = False
            else:
                is_direct = (
                    relay_mode != "force_relay"
                    and bool(endpoint)
                    and nat_type != "symmetric"
                    and (relay_mode == "force_direct" or not req_reported_relay)
                )
            if is_direct:
                direct.append(rec)
            else:
                relay_only.append(rec)
    direct.sort(key=lambda x: x["peer_id"])
    relay_only.sort(key=lambda x: x["peer_id"])
    return {"direct": direct, "relay_only": relay_only, "relay_cidr": relay_cidr}


def rpc_config_get_mesh_peers(params: Dict[str, Any]) -> Any:
    from . import auth as auth_mod
    peer_id = str(params.get("peer_id") or "")
    network_id = str(params.get("network_id") or "")
    token = params.get("token")
    if token:
        auth_mode, uid, scopes, is_admin_jwt = auth_mod._auth_from_token(token)
        if auth_mode == "jwt":
            auth_mod._require_scope(scopes, "config:read")
            auth_mod._enforce_tenant_for_peer(str(uid), peer_id)
        else:
            raise PermissionError("authentication required: provide a valid JWT")
    with state.LOCK_NETWORKS:
        n = state.STATE["networks"].get(network_id)
    if not n:
        raise KeyError("network not found")
    topo = n.get("topology", "hub-spoke")
    if topo not in ("mesh", "hub-mesh"):
        raise ValueError(f"La red '{network_id}' tiene topologia '{topo}', no 'mesh' ni 'hub-mesh'")
    if topo == "hub-mesh":
        return _classify_peers_for_hub_mesh(peer_id, network_id)
    return _get_alive_mesh_peers(peer_id, network_id)
