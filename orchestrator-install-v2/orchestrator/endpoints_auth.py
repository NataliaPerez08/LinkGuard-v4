"""
Endpoints RPC de autenticacion/tokens.
"""

from typing import Any, Dict, Optional

from . import config, state, auth


def rpc_jwt_issue(params: Dict[str, Any]) -> Dict[str, Any]:
    user_id = str(params.get("user_id") or "")
    if not user_id:
        raise ValueError("user_id is required")
    ttl = int(params.get("ttl") or config.JWT_TTL_DEFAULT)
    payload = {"user_id": user_id, "scopes": params.get("scopes", []), "role": params.get("role", "user")}
    token, exp = auth._jwt_encode(payload, ttl)
    return {"token": token, "expires_at": exp, "user_id": user_id}


def rpc_jwt_verify(params: Dict[str, Any]) -> Dict[str, Any]:
    token = str(params.get("token") or "")
    if not token:
        raise ValueError("token is required")
    payload = auth._jwt_decode(token)
    jti = payload.get("jti", "")
    if jti and auth._is_revoked_jti(jti):
        raise PermissionError("jwt revoked")
    return {"valid": True, "payload": payload}


def rpc_jwt_revoke(params: Dict[str, Any]) -> Dict[str, Any]:
    token = str(params.get("token") or "")
    if not token:
        raise ValueError("token is required")
    payload = auth._jwt_decode(token)
    jti = payload.get("jti", "")
    exp = payload.get("exp", 0)
    reason = str(params.get("reason") or "manual revocation")
    if jti:
        auth._revoke_jti(jti, reason, exp)
    state.add_event("jwt_revoked", {"jti": jti, "reason": reason})
    return {"revoked": True}
