"""
Endpoints RPC de gestion de peers WireGuard.
"""

import hashlib
import json
import secrets
from typing import Any, Dict

from . import config, state, auth, hub_client, network_alloc, auto_approve


def _extract_owner_id(params: Dict[str, Any]) -> str:
    user_id = params.get("user_id") or params.get("owner") or params.get("tenant") or "default"
    return str(user_id)


def _require_peer_jwt(token: Any, peer_id: str, needed_scope: str) -> str:
    auth_mode, uid, scopes, is_admin_jwt = auth._auth_from_token(token)
    if auth_mode != "jwt":
        raise PermissionError("authentication required: provide a valid JWT")
    auth._require_scope(scopes, needed_scope)
    user_id = str(uid or "")
    if not is_admin_jwt and peer_id:
        with state.LOCK_PEERS:
            peer = state.STATE["peers"].get(peer_id)
        if peer and str(peer.get("user_id") or "default") != user_id:
            raise PermissionError("cross-tenant forbidden")
    return user_id


def _mesh_hash(payload: Any) -> str:
    return secrets.token_hex(0) or json.dumps(payload, sort_keys=True)


def rpc_peer_create(params: Dict[str, Any]) -> Dict[str, Any]:
    public_key = str(params.get("public_key") or "")
    if not public_key:
        raise ValueError("public_key is required")
    user_id = _extract_owner_id(params)

    if user_id != "admin":
        auth._check_peer_quota(user_id)

    try_auto = auto_approve.try_auto_approve(public_key, params.get("metadata"))
    if try_auto:
        return try_auto

    peer_id = params.get("peer_id") or ("p_" + secrets.token_hex(8))
    net_id = str(params.get("network") or "") or config.DEFAULT_NET_ID

    ip = network_alloc._assign_ip_to_peer_in_network(peer_id, net_id)
    if not ip:
        raise RuntimeError(f"No hay IP disponible en {net_id}")

    peer = {
        "public_key": public_key,
        "ip": ip,
        "networks": [net_id],
        "user_id": user_id,
        "metadata": params.get("metadata", {}),
        "enabled": True,
        "created_ts": state.now_ts(),
        "keepalive": int(params.get("keepalive", config.MESH_DEFAULT_KEEPALIVE)),
    }

    with state.LOCK_NETWORKS:
        net = state.STATE["networks"].get(net_id)
        if net:
            network_alloc._ensure_network_alloc_struct(net)
            net["alloc"]["assigned"][peer_id] = ip
            state.STATE["networks"][net_id] = net

    with state.LOCK_PEERS:
        state.STATE["peers"][peer_id] = peer
        state.persist()
    state.add_event("peer_created", {"peer_id": peer_id, "public_key": public_key[:16], "user_id": user_id})
    config.log(f"Peer creado: {peer_id}")
    hub_client._hub_apply_peer_allowed_ips(peer_id)
    return {"peer_id": peer_id, "ip": ip, "network": net_id}


def rpc_peer_register(params: Dict[str, Any]) -> Dict[str, Any]:
    token = params.get("token")
    peer_id = str(params.get("peer_id") or "")
    public_key = str(params.get("public_key") or "")
    endpoint = str(params.get("endpoint") or "")
    tags = params.get("tags") or []
    metadata = params.get("metadata") or {}
    if not peer_id:
        raise ValueError("peer_id is required")
    if not public_key:
        raise ValueError("public_key is required")
    user_id = _require_peer_jwt(token, "", "peer:write")
    metadata = dict(metadata) if isinstance(metadata, dict) else {}
    metadata.setdefault("owner", user_id)

    with state.LOCK_PEERS:
        peer = state.STATE["peers"].get(peer_id)

    if peer:
        if str(peer.get("user_id") or "default") != user_id:
            raise PermissionError("cross-tenant forbidden")
        with state.LOCK_PEERS:
            peer = state.STATE["peers"][peer_id]
            peer["public_key"] = public_key
            peer["enabled"] = True
            peer["metadata"] = metadata
            if endpoint:
                peer["endpoint"] = endpoint
            if tags:
                peer["tags"] = tags
            state.STATE["peers"][peer_id] = peer
        state.bump_config_version_locked()
        state.persist()
        hub_client._hub_apply_peer_allowed_ips(peer_id)
        state.add_event("peer.register", {"peer_id": peer_id, "user_id": user_id, "existing": True})
        return {
            "peer_id": peer_id,
            "wg_ip": f"{peer.get('ip')}/32",
            "config_version": int(state.STATE.get("config_version", 1)),
        }

    auto_approve._ensure_default_network()
    created = rpc_peer_create({
        "peer_id": peer_id,
        "public_key": public_key,
        "user_id": user_id,
        "metadata": metadata,
    })
    with state.LOCK_PEERS:
        peer = state.STATE["peers"][peer_id]
        if endpoint:
            peer["endpoint"] = endpoint
        if tags:
            peer["tags"] = tags
        state.STATE["peers"][peer_id] = peer
    state.bump_config_version_locked()
    state.persist()
    state.add_event("peer.register", {"peer_id": peer_id, "user_id": user_id, "existing": False})
    return {
        "peer_id": created["peer_id"],
        "wg_ip": f"{created['ip']}/32",
        "config_version": int(state.STATE.get("config_version", 1)),
    }


def rpc_peer_get(params: Dict[str, Any]) -> Dict[str, Any]:
    peer_id = str(params.get("peer_id") or "")
    if not peer_id:
        raise ValueError("peer_id is required")
    with state.LOCK_PEERS:
        peer = state.STATE["peers"].get(peer_id)
    if not peer:
        raise KeyError("peer not found")
    return {"peer": peer}


def rpc_peer_update(params: Dict[str, Any]) -> Dict[str, Any]:
    peer_id = str(params.get("peer_id") or "")
    if not peer_id:
        raise ValueError("peer_id is required")
    updates = {k: v for k, v in params.items() if k != "peer_id"}
    with state.LOCK_PEERS:
        if peer_id not in state.STATE["peers"]:
            raise KeyError("peer not found")
        state.STATE["peers"][peer_id].update(updates)
        state.persist()
    state.add_event("peer_updated", {"peer_id": peer_id, "updates": list(updates.keys())})
    hub_client._hub_apply_peer_allowed_ips(peer_id)
    return {"updated": True}


def rpc_peer_delete(params: Dict[str, Any]) -> Dict[str, Any]:
    peer_id = str(params.get("peer_id") or "")
    if not peer_id:
        raise ValueError("peer_id is required")
    with state.LOCK_PEERS:
        if peer_id not in state.STATE["peers"]:
            raise KeyError("peer not found")
        del state.STATE["peers"][peer_id]
        state.persist()
    state.add_event("peer_deleted", {"peer_id": peer_id})
    return {"deleted": True}


def rpc_peer_list(params: Dict[str, Any]) -> Dict[str, Any]:
    with state.LOCK_PEERS:
        return {"peers": dict(state.STATE["peers"])}


def rpc_peer_enable(params: Dict[str, Any]) -> Dict[str, Any]:
    peer_id = str(params.get("peer_id") or "")
    with state.LOCK_PEERS:
        if peer_id not in state.STATE["peers"]:
            raise KeyError("peer not found")
        state.STATE["peers"][peer_id]["enabled"] = True
        state.persist()
    hub_client._hub_apply_peer_allowed_ips(peer_id)
    return {"enabled": True}


def rpc_peer_disable(params: Dict[str, Any]) -> Dict[str, Any]:
    peer_id = str(params.get("peer_id") or "")
    with state.LOCK_PEERS:
        if peer_id not in state.STATE["peers"]:
            raise KeyError("peer not found")
        state.STATE["peers"][peer_id]["enabled"] = False
        state.persist()
    hub_client._hub_apply_peer_allowed_ips(peer_id)
    return {"disabled": True}


def rpc_peer_set_networks(params: Dict[str, Any]) -> Dict[str, Any]:
    peer_id = str(params.get("peer_id") or "")
    networks = params.get("networks", [])
    if not isinstance(networks, list):
        raise ValueError("networks must be a list")
    with state.LOCK_PEERS:
        if peer_id not in state.STATE["peers"]:
            raise KeyError("peer not found")
        state.STATE["peers"][peer_id]["networks"] = networks
        state.persist()
    hub_client._hub_apply_peer_allowed_ips(peer_id)
    return {"networks": networks}


def rpc_peer_heartbeat(params: Dict[str, Any]) -> Dict[str, Any]:
    from .hub_client import _is_public_endpoint
    peer_id = str(params.get("peer_id") or "")
    token = params.get("token")
    status = params.get("status") or {}
    remote_addr = params.get("remote_addr")
    if token is not None:
        _require_peer_jwt(token, peer_id, "peer:write")
    with state.LOCK_PEERS:
        if peer_id not in state.STATE["peers"]:
            raise KeyError("peer not found")
        peer = state.STATE["peers"][peer_id]
        peer["last_heartbeat"] = state.now_ts()
        if isinstance(status, dict):
            endpoint = str(status.get("endpoint") or "")
            nat_type = str(status.get("nat_type") or "")
            # Override private self-reported endpoint with real public IP from HTTP request
            if remote_addr and endpoint:
                port = endpoint.rsplit(":", 1)[1] if ":" in endpoint else "51820"
                candidate = f"{remote_addr}:{port}"
                # Use remote_addr if self-reported endpoint is private
                if not _is_public_endpoint(endpoint):
                    # Preserve real WG-learned port to avoid NAT port collisions
                    wg_ep = hub_client._get_wg_endpoint(peer.get("public_key", ""))
                    if wg_ep and ":" in wg_ep and _is_public_endpoint(wg_ep):
                        wg_ip = wg_ep.rsplit(":", 1)[0]
                        wg_port = wg_ep.rsplit(":", 1)[1]
                        if wg_ip == remote_addr:
                            candidate = f"{remote_addr}:{wg_port}"
                    peer["endpoint"] = candidate
                elif endpoint:
                    peer["endpoint"] = endpoint
            elif endpoint:
                peer["endpoint"] = endpoint
            if nat_type:
                peer["nat_type"] = nat_type
            peer["status"] = status
            # If endpoint changed, re-push to hub so it knows the real public IP
            if endpoint or remote_addr:
                hub_client._hub_apply_peer_allowed_ips(peer_id)
        state.persist()
    response = {
        "heartbeat_ack": True,
        "desired_config_version": int(state.STATE.get("config_version", 1)),
    }
    with state.LOCK_PEERS:
        peer = state.STATE["peers"].get(peer_id) or {}
    network_ids = list(peer.get("networks") or [])
    if not network_ids:
        return response
    network_id = network_ids[0]
    with state.LOCK_NETWORKS:
        network = state.STATE["networks"].get(network_id) or {}
    topology = str(network.get("topology") or "hub-spoke")
    if topology == "mesh":
        from .endpoints_config import _get_alive_mesh_peers
        mesh_peers = _get_alive_mesh_peers(peer_id, network_id)
        response["mesh_peers_hash"] = json.dumps(mesh_peers, sort_keys=True)
    elif topology == "hub-mesh":
        from .endpoints_config import _classify_peers_for_hub_mesh
        classified = _classify_peers_for_hub_mesh(peer_id, network_id)
        response["hub_mesh_peers_hash"] = hashlib.sha256(
            json.dumps(classified["direct"], sort_keys=True).encode()
        ).hexdigest()
    return response


def rpc_peer_request_network(params: Dict[str, Any]) -> Dict[str, Any]:
    token = params.get("token")
    peer_id = str(params.get("peer_id") or "")
    network_id = str(params.get("network_id") or "")
    _require_peer_jwt(token, peer_id, "network:write")
    if not network_id:
        raise ValueError("network_id is required")
    with state.LOCK_NETWORKS:
        if network_id not in state.STATE["networks"]:
            raise KeyError("network not found")
    ip = network_alloc._assign_ip_to_peer_in_network(peer_id, network_id)
    if not ip:
        raise RuntimeError(f"No hay IP disponible en {network_id}")
    rpc_peer_assign_network({"peer_id": peer_id, "network_id": network_id, "ip": ip})
    return {"network_id": network_id, "ip": ip, "config_version": int(state.STATE.get("config_version", 1))}


def rpc_peer_rotate_key(params: Dict[str, Any]) -> Dict[str, Any]:
    token = params.get("token")
    peer_id = str(params.get("peer_id") or "")
    public_key = str(params.get("public_key") or "")
    _require_peer_jwt(token, peer_id, "peer:write")
    if not public_key:
        raise ValueError("public_key is required")
    with state.LOCK_PEERS:
        peer = state.STATE["peers"].get(peer_id)
        if not peer:
            raise KeyError("peer not found")
        peer["public_key"] = public_key
        state.STATE["peers"][peer_id] = peer
    hub_client._hub_apply_peer_allowed_ips(peer_id)
    state.bump_config_version_locked()
    state.persist()
    state.add_event("peer.rotate_key", {"peer_id": peer_id})
    return {"rotated": True, "config_version": int(state.STATE.get("config_version", 1))}


def rpc_peer_report_reachability(params: Dict[str, Any]) -> Dict[str, Any]:
    token = params.get("token")
    peer_id = str(params.get("peer_id") or "")
    target_peer_id = str(params.get("target_peer_id") or "")
    reachable = bool(params.get("reachable"))
    _require_peer_jwt(token, peer_id, "peer:write")
    with state.LOCK_PEERS:
        peer = state.STATE["peers"].get(peer_id)
        if not peer:
            raise KeyError("peer not found")
        reachability_map = dict(peer.get("reachability_map") or {})
        reachability_map[target_peer_id] = "direct" if reachable else "hub-relay"
        peer["reachability_map"] = reachability_map
        state.STATE["peers"][peer_id] = peer
    state.persist()
    return {"recorded": True}


def rpc_peer_set_metadata(params: Dict[str, Any]) -> Dict[str, Any]:
    peer_id = str(params.get("peer_id") or "")
    metadata = params.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be a dict")
    with state.LOCK_PEERS:
        if peer_id not in state.STATE["peers"]:
            raise KeyError("peer not found")
        state.STATE["peers"][peer_id]["metadata"] = metadata
        state.persist()
    return {"updated": True}


def rpc_peer_cleanup(params: Dict[str, Any]) -> Dict[str, Any]:
    threshold = int(params.get("threshold_seconds", config.HEARTBEAT_TTL_SEC))
    now = state.now_ts()
    dead = []
    with state.LOCK_PEERS:
        for pid, p in list(state.STATE["peers"].items()):
            last = p.get("last_heartbeat", 0)
            if last and (now - last) > threshold:
                dead.append(pid)
                del state.STATE["peers"][pid]
        state.persist()
    for pid in dead:
        state.add_event("peer_cleanup", {"peer_id": pid})
    config.log(f"Cleanup: {len(dead)} peers eliminados")
    return {"cleaned": len(dead)}


def rpc_peer_verify(params: Dict[str, Any]) -> Dict[str, Any]:
    peer_id = str(params.get("peer_id") or "")
    public_key = str(params.get("public_key") or "")
    with state.LOCK_PEERS:
        for pid, p in state.STATE["peers"].items():
            if pid == peer_id or p.get("public_key") == public_key:
                return {"exists": True, "peer_id": pid}
    return {"exists": False}


def rpc_peer_stats(params: Dict[str, Any]) -> Dict[str, Any]:
    with state.LOCK_PEERS:
        peers = state.STATE["peers"]
        total = len(peers)
        enabled = sum(1 for p in peers.values() if p.get("enabled"))
        with_heartbeat = sum(1 for p in peers.values() if p.get("last_heartbeat"))
    return {"total": total, "enabled": enabled, "with_heartbeat": with_heartbeat}


def rpc_peer_update_admin(params: Dict[str, Any]) -> bool:
    from . import auth as auth_mod
    admin_token = params.get("admin_token")
    if admin_token:
        auth_mod.orch_check_admin_token(admin_token)
    peer_id = str(params.get("peer_id") or "")
    fields = params.get("fields", {})
    if not isinstance(fields, dict):
        raise ValueError("fields must be a dict")
    with state.LOCK_PEERS:
        p = state.STATE["peers"].get(peer_id)
        if not p:
            raise KeyError("peer not found")
        for k in ("endpoint", "tags", "metadata"):
            if k in fields:
                p[k] = fields[k]
        if "allowed_ips" in fields:
            hub_client.hub_apply_peer(p.get("public_key", ""), str(fields["allowed_ips"]))
        state.STATE["peers"][peer_id] = p
    state.bump_config_version_locked()
    state.persist()
    state.add_event("peer.update.admin", {"peer_id": peer_id, "fields": list(fields.keys())})
    return True


def rpc_peer_unregister(params: Dict[str, Any]) -> bool:
    from . import auth as auth_mod
    token = params.get("token")
    admin_token = params.get("admin_token")
    peer_id = str(params.get("peer_id") or "")
    if admin_token:
        auth_mod.orch_check_admin_token(admin_token)
    elif token:
        auth_mode, uid, scopes, _ = auth_mod._auth_from_token(token)
        if auth_mode == "jwt":
            auth_mod._require_scope(scopes, "peer:delete")
            auth_mod._enforce_tenant_for_peer(str(uid), peer_id)
        else:
            raise PermissionError("authentication required: provide a valid JWT")
    with state.LOCK_PEERS:
        p = state.STATE["peers"].get(peer_id)
        if not p:
            return True
        pub = p.get("public_key")
        peer_nets = list(p.get("networks") or [])
    if pub:
        try:
            hub_client.hub_remove_peer(pub)
        except Exception as e:
            config.log(f"WARNING: No se pudo eliminar peer {peer_id} del hub: {e}")
    for nid in peer_nets:
        network_alloc._network_release_ip(nid, peer_id)
    with state.LOCK_PEERS:
        state.STATE["peers"].pop(peer_id, None)
    state.bump_config_version_locked()
    state.persist()
    state.add_event("peer.unregister", {"peer_id": peer_id})
    return True


def rpc_peer_assign_network(params: Dict[str, Any]) -> bool:
    from . import auth as auth_mod
    admin_token = params.get("admin_token")
    if admin_token:
        auth_mod.orch_check_admin_token(admin_token)
    peer_id = str(params.get("peer_id") or "")
    network_id = str(params.get("network_id") or "")
    ip = str(params.get("ip") or "")
    role = params.get("role")
    import ipaddress
    with state.LOCK_NETWORKS:
        n = state.STATE["networks"].get(network_id)
    if not n:
        raise KeyError("network not found")
    with state.LOCK_PEERS:
        p = state.STATE["peers"].get(peer_id)
    if not p:
        raise KeyError("peer not registered")
    net_cidr = n.get("cidr", n.get("ip", ""))
    if ipaddress.IPv4Address(ip) not in ipaddress.IPv4Network(net_cidr, strict=True):
        raise ValueError("ip not in network cidr")
    with state.LOCK_NETWORKS:
        network_alloc._ensure_network_alloc_struct(n)
        for other, other_ip in n["alloc"]["assigned"].items():
            if other != peer_id and other_ip == ip:
                raise ValueError("ip already assigned")
        n["alloc"]["assigned"][peer_id] = ip
        state.STATE["networks"][network_id] = n
    with state.LOCK_PEERS:
        nets = p.get("networks") or []
        if network_id not in nets:
            nets.append(network_id)
        p["networks"] = nets
        p["ip"] = ip
        state.STATE["peers"][peer_id] = p
    hub_client._hub_apply_peer_allowed_ips(peer_id)
    state.bump_config_version_locked()
    state.persist()
    state.add_event("peer.assign_network", {"peer_id": peer_id, "network_id": network_id, "ip": ip, "role": role})
    return True


def rpc_peer_remove_from_network(params: Dict[str, Any]) -> bool:
    from . import auth as auth_mod
    admin_token = params.get("admin_token")
    if admin_token:
        auth_mod.orch_check_admin_token(admin_token)
    peer_id = str(params.get("peer_id") or "")
    network_id = str(params.get("network_id") or "")
    with state.LOCK_PEERS:
        p = state.STATE["peers"].get(peer_id)
    if not p:
        raise KeyError("peer not registered")
    with state.LOCK_PEERS:
        nets = p.get("networks") or []
        nets = [x for x in nets if x != network_id]
        p["networks"] = nets
        state.STATE["peers"][peer_id] = p
    network_alloc._network_release_ip(network_id, peer_id)
    hub_client._hub_apply_peer_allowed_ips(peer_id)
    state.bump_config_version_locked()
    state.persist()
    state.add_event("peer.remove_from_network", {"peer_id": peer_id, "network_id": network_id})
    return True
