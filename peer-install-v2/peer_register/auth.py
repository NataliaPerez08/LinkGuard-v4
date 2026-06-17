"""
Manejo de sesion JWT con el orquestador.
Login, refresh, cache en state.
"""

import time

from . import config as cfg
from .state import load_state, save_state
from .identity import owner_default
from .utils import log, rpc


def _jwt_needs_refresh(st: dict) -> bool:
    exp = int(st.get("jwt_expires_at") or 0)
    if not exp:
        return True
    return int(time.time()) >= (exp - 60)


def ensure_jwt_session(peer_id: str, st: dict) -> str:
    if "jwt" in st and not _jwt_needs_refresh(st):
        return st["jwt"]

    if not cfg.ORCH_TOKEN:
        raise RuntimeError(
            "ORCH_TOKEN esta vacio. Configura ORCH_TOKEN en /etc/linkguard/peer.env "
            "(obten el token del admin del orchestrator con: orch-cli issue-user-token <user_id>)"
        )

    c = rpc()
    uid = owner_default()
    if "jwt" in st and _jwt_needs_refresh(st):
        try:
            resp = c.__getattr__("auth.refresh")(st["jwt"], cfg.JWT_TTL)
            st["jwt"] = resp["jwt"]
            st["jwt_expires_at"] = int(resp["expires_at"])
            save_state(st)
            return st["jwt"]
        except Exception as e:
            log(f"JWT refresh fallo, re-login: {e}")

    resp = c.__getattr__("auth.login")(uid, peer_id, cfg.ORCH_TOKEN, cfg.JWT_SCOPES, cfg.JWT_TTL)
    st["jwt"] = resp["jwt"]
    st["jwt_expires_at"] = int(resp["expires_at"])
    save_state(st)
    return st["jwt"]


def orch_token_for_call(peer_id: str) -> str:
    st = load_state()
    return ensure_jwt_session(peer_id, st)
