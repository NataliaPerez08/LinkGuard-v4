"""
Endpoints RPC de gestion de usuarios/tenants.
"""

from typing import Any, Dict

from . import config, state, auth


def rpc_user_create(params: Dict[str, Any]) -> Dict[str, Any]:
    user_id = str(params.get("user_id") or "").strip()
    if not user_id:
        raise ValueError("user_id is required")
    if auth._user_exists(user_id):
        raise ValueError(f"user already exists: {user_id}")
    max_peers = int(params.get("max_peers", config.DEFAULT_MAX_PEERS))
    max_networks = int(params.get("max_networks", config.DEFAULT_MAX_NETWORKS))
    token = auth._issue_user_token(user_id)
    with state.LOCK_USERS:
        users = state.STATE["users"]
        users[user_id] = {
            "token": token,
            "disabled": False,
            "created_ts": state.now_ts(),
            "max_peers": max_peers,
            "max_networks": max_networks,
            "metadata": params.get("metadata", {}),
        }
        state.STATE["users"] = users
        state.persist()
    state.add_event("user_created", {"user_id": user_id})
    return {"user_id": user_id, "token": token}


def rpc_user_delete(params: Dict[str, Any]) -> Dict[str, Any]:
    user_id = str(params.get("user_id") or "")
    if not user_id:
        raise ValueError("user_id is required")
    if not auth._user_exists(user_id):
        raise KeyError("user not found")
    with state.LOCK_USERS:
        del state.STATE["users"][user_id]
        state.persist()
    state.add_event("user_deleted", {"user_id": user_id})
    return {"deleted": True}


def rpc_user_list(params: Dict[str, Any]) -> Dict[str, Any]:
    with state.LOCK_USERS:
        return {"users": dict(state.STATE.get("users", {}))}


def rpc_user_token_reset(params: Dict[str, Any]) -> Dict[str, Any]:
    user_id = str(params.get("user_id") or "")
    if not user_id:
        raise ValueError("user_id is required")
    if not auth._user_exists(user_id):
        raise KeyError("user not found")
    token = auth._issue_user_token(user_id)
    state.persist()
    return {"user_id": user_id, "token": token}


def rpc_user_disable(params: Dict[str, Any]) -> Dict[str, Any]:
    user_id = str(params.get("user_id") or "")
    if not user_id:
        raise ValueError("user_id is required")
    u = auth._get_user(user_id)
    u["disabled"] = True
    with state.LOCK_USERS:
        state.STATE["users"][user_id] = u
        state.persist()
    return {"disabled": True}
