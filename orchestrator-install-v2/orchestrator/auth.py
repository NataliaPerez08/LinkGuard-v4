"""
Autenticacion y autorizacion.
JWT, tokens de usuario, scopes, cuotas multi-tenant y helpers de auth.
"""

import hashlib
import secrets
import threading
from typing import Dict, Any, Optional, List, Tuple

import jwt as pyjwt

from . import config, state


# JWT secret recargable sin reinicio
_JWT_SECRET_HASH: Optional[str] = None
_JWT_SECRET_VALUE: Optional[str] = None
_JWT_SECRET_LOCK = threading.Lock()


def _read_jwt_secret() -> str:
    global _JWT_SECRET_HASH, _JWT_SECRET_VALUE
    try:
        with open(config.JWT_SECRET_PATH, "r") as f:
            s = f.read().strip()
        if not s:
            raise RuntimeError("JWT secret vacio")
        file_hash = hashlib.sha256(s.encode()).hexdigest()
        with _JWT_SECRET_LOCK:
            if file_hash != _JWT_SECRET_HASH:
                _JWT_SECRET_HASH = file_hash
                _JWT_SECRET_VALUE = s
                config.log("JWT secret recargado (hash cambio)")
            assert _JWT_SECRET_VALUE is not None
            return _JWT_SECRET_VALUE
    except FileNotFoundError:
        raise RuntimeError(
            f"JWT secret no existe: {config.JWT_SECRET_PATH}. "
            "Crea con: openssl rand -hex 32 > {config.JWT_SECRET_PATH} && chmod 600 {config.JWT_SECRET_PATH}"
        )
    except Exception as e:
        raise RuntimeError(f"No pude leer JWT secret: {e}")


def _jwt_encode(payload: Dict[str, Any], ttl_seconds: int) -> Tuple[str, int]:
    ttl = int(ttl_seconds) if ttl_seconds else config.JWT_TTL_DEFAULT
    if ttl <= 0:
        ttl = config.JWT_TTL_DEFAULT
    n = state.now_ts()
    exp = n + ttl
    full = dict(payload)
    full.update({
        "iss": config.JWT_ISSUER, "aud": config.JWT_AUDIENCE,
        "iat": n, "nbf": n, "exp": exp,
        "jti": secrets.token_hex(12),
    })
    token = pyjwt.encode(full, _read_jwt_secret(), algorithm="HS256")
    return token, exp


def _jwt_decode(token: str) -> Dict[str, Any]:
    return pyjwt.decode(
        token, _read_jwt_secret(), algorithms=["HS256"],
        audience=config.JWT_AUDIENCE, issuer=config.JWT_ISSUER,
        options={"require": ["exp", "iat", "nbf", "iss", "aud", "jti"]},
    )


def _is_probably_jwt(token: str) -> bool:
    return isinstance(token, str) and token.count(".") == 2 and len(token) > 30


# Revocacion JWT en archivo separado
_REVOKED_CACHE: Optional[Dict[str, Any]] = None


def _load_revoked() -> Dict[str, Any]:
    global _REVOKED_CACHE
    if _REVOKED_CACHE is not None:
        return _REVOKED_CACHE
    data = state.load_json(config.JWT_REVOKED_PATH)
    _REVOKED_CACHE = data if isinstance(data, dict) else {}
    return _REVOKED_CACHE


def _save_revoked(rev: Dict[str, Any]) -> None:
    global _REVOKED_CACHE
    state.save_json(config.JWT_REVOKED_PATH, rev)
    _REVOKED_CACHE = rev


def _is_revoked_jti(jti: str) -> bool:
    with state.LOCK_REVOKED:
        return jti in _load_revoked()


def _revoke_jti(jti: str, reason: str, exp: Optional[int] = None) -> None:
    with state.LOCK_REVOKED:
        rev = _load_revoked()
        rev[str(jti)] = {"ts": state.now_ts(), "reason": reason, "exp": exp or 0}
        now = state.now_ts()
        rev = {k: v for k, v in rev.items()
               if v.get("exp", 0) == 0 or v.get("exp", 0) > now}
        _save_revoked(rev)


def _auth_from_token(token: Optional[str]) -> Tuple[str, Optional[str], List[str], bool]:
    if token and _is_probably_jwt(token):
        payload = _jwt_decode(token)
        jti = str(payload.get("jti") or "")
        if jti and _is_revoked_jti(jti):
            raise PermissionError("jwt revoked")
        user_id = payload.get("user_id")
        scopes = payload.get("scopes") or []
        role = payload.get("role") or "user"
        if not isinstance(scopes, list):
            scopes = []
        return "jwt", user_id, [str(x) for x in scopes], (role == "admin")

    if token:
        return "legacy", None, [], False
    return "none", None, [], False


def _require_scope(scopes: List[str], needed: str) -> None:
    if needed in scopes:
        return
    prefix = needed.split(":", 1)[0] + ":*"
    if prefix in scopes or "*:*" in scopes or "*" in scopes:
        return
    raise PermissionError(f"missing scope: {needed}")


def orch_check_admin_token(token: Optional[str]) -> None:
    if not config.ADMIN_TOKEN:
        raise PermissionError("admin token not configured")
    if not token:
        raise PermissionError("admin token required")
    if token != config.ADMIN_TOKEN:
        raise PermissionError("invalid admin token")


# Tenant helpers
def _peer_owner_from_metadata(metadata: Optional[Dict[str, Any]]) -> str:
    if not metadata:
        return "default"
    owner = metadata.get("owner") or metadata.get("user_id") or metadata.get("tenant")
    return str(owner).strip() if owner else "default"


def _enforce_tenant_for_peer(user_id: str, peer_id: str) -> None:
    with state.LOCK_PEERS:
        p = state.STATE["peers"].get(peer_id)
    if not p:
        raise KeyError("peer not found")
    if str(p.get("user_id") or "default") != str(user_id):
        raise PermissionError("cross-tenant forbidden")


def _filter_events_for_tenant(user_id: str) -> List[Dict[str, Any]]:
    out = []
    with state.LOCK_EVENTS:
        events = list(state.STATE.get("events") or [])
    for ev in events:
        d = ev.get("detail") or {}
        pid = d.get("peer_id")
        nid = d.get("network_id")
        try:
            if pid:
                with state.LOCK_PEERS:
                    p = state.STATE["peers"].get(pid) or {}
                if str(p.get("user_id") or "default") != str(user_id):
                    continue
            if nid:
                with state.LOCK_NETWORKS:
                    n = state.STATE["networks"].get(nid) or {}
                if str(n.get("user_id") or "") != str(user_id):
                    continue
        except (KeyError, TypeError, AttributeError):
            continue
        out.append(ev)
    return out


# Users
def _user_exists(user_id: str) -> bool:
    with state.LOCK_USERS:
        return user_id in (state.STATE.get("users") or {})


def _get_user(user_id: str) -> Dict[str, Any]:
    with state.LOCK_USERS:
        u = (state.STATE.get("users") or {}).get(user_id)
    if not u:
        raise KeyError("user not found")
    return u


def _issue_user_token(user_id: str) -> str:
    tok = "u_" + secrets.token_hex(16)
    with state.LOCK_USERS:
        users = state.STATE.get("users") or {}
        u = users.get(user_id) or {"created_ts": state.now_ts(), "disabled": False}
        u["token"] = tok
        u.setdefault("created_ts", state.now_ts())
        users[user_id] = u
        state.STATE["users"] = users
    return tok


def _check_user_token(user_id: str, token: str) -> None:
    u = _get_user(user_id)
    if u.get("disabled"):
        raise PermissionError("user disabled")
    if str(u.get("token") or "") != str(token):
        raise PermissionError("invalid user token")


# Quotas
def _get_tenant_quota(user_id: str) -> Dict[str, int]:
    with state.LOCK_USERS:
        u = (state.STATE.get("users") or {}).get(user_id) or {}
    return {
        "max_peers": int(u.get("max_peers", config.DEFAULT_MAX_PEERS)),
        "max_networks": int(u.get("max_networks", config.DEFAULT_MAX_NETWORKS)),
    }


def _check_peer_quota(user_id: str) -> None:
    quota = _get_tenant_quota(user_id)
    with state.LOCK_PEERS:
        count = sum(1 for p in state.STATE["peers"].values()
                    if str(p.get("user_id") or "default") == str(user_id))
    if count >= quota["max_peers"]:
        raise PermissionError(f"Peer quota exceeded: {count}/{quota['max_peers']} for user '{user_id}'")


def _check_network_quota(user_id: str) -> None:
    quota = _get_tenant_quota(user_id)
    with state.LOCK_NETWORKS:
        count = sum(1 for n in state.STATE["networks"].values()
                    if str(n.get("user_id") or "") == str(user_id))
    if count >= quota["max_networks"]:
        raise PermissionError(f"Network quota exceeded: {count}/{quota['max_networks']} for user '{user_id}'")
