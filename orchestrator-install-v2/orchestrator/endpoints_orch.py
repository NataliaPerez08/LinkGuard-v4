"""
Endpoints RPC del orchestrator (estado, health, etc).
"""

from typing import Any, Dict

from . import config, state


def rpc_health(params: Dict[str, Any]) -> Dict[str, Any]:
    from .hub_client import hub_ping
    return {
        "status": "healthy",
        "peers_count": len(state.STATE.get("peers", {})),
        "networks_count": len(state.STATE.get("networks", {})),
        "hub_reachable": hub_ping(),
        "config_version": state.STATE.get("config_version"),
    }


def rpc_state_dump(params: Dict[str, Any]) -> Dict[str, Any]:
    with state.LOCK_STATE:
        return {"state": dict(state.STATE)}


def rpc_state_persist(params: Dict[str, Any]) -> Dict[str, Any]:
    state.persist()
    return {"persisted": True}


def rpc_events(params: Dict[str, Any]) -> Dict[str, Any]:
    return {"events": state.STATE.get("events", [])}


def rpc_metrics(params: Dict[str, Any]) -> Dict[str, Any]:
    from . import auth as auth_mod
    token = params.get("token")
    auth_mode, uid, scopes, is_admin_jwt = auth_mod._auth_from_token(token) if token else ("none", None, [], False)
    now = state.now_ts()
    with state.LOCK_PEERS:
        total = len(state.STATE["peers"])
        alive = sum(1 for p in state.STATE["peers"].values()
                    if p.get("last_heartbeat") and (now - int(p["last_heartbeat"])) <= config.HEARTBEAT_TTL_SEC)
    base = {
        "ts": now, "config_version": state.STATE.get("config_version", 1),
        "hub_agent_url": config.HUB_AGENT_URL, "hub_endpoint": config.HUB_ENDPOINT,
        "auto_approve_enabled": config.AUTO_APPROVE_ENABLED,
        "auto_approve_rules": config.AUTO_APPROVE_RULES,
    }
    if (auth_mode == "legacy" and token == config.ADMIN_TOKEN) or is_admin_jwt:
        with state.LOCK_USERS:
            users_total = len(state.STATE.get("users") or {})
        with state.LOCK_NETWORKS:
            networks_total = len(state.STATE.get("networks") or {})
        base.update({"peers_total": total, "peers_alive": alive, "peers_stale": total - alive,
                     "users_total": users_total, "networks_total": networks_total})
        return base
    if auth_mode == "jwt":
        auth_mod._require_scope(scopes, "orch:read")
        uid_s = str(uid or "")
        with state.LOCK_PEERS:
            peers_t = [p for p in state.STATE["peers"].values()
                       if str(p.get("user_id") or "default") == uid_s]
            alive_t = sum(1 for p in peers_t
                          if p.get("last_heartbeat") and
                          (now - int(p["last_heartbeat"])) <= config.HEARTBEAT_TTL_SEC)
        base.update({"user_id": uid_s, "peers_total": len(peers_t),
                     "peers_alive": alive_t, "peers_stale": len(peers_t) - alive_t})
        return base
    raise PermissionError("authentication required: provide a valid JWT")
