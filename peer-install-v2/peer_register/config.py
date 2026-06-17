"""
Configuracion del peer auto-register.
Variables de entorno, paths, peer.env auto-loading.
"""

import os
import sys

_PEER_ENV_PATH = os.getenv("PEER_ENV_PATH", "/etc/linkguard/peer.env")
if os.path.isfile(_PEER_ENV_PATH):
    try:
        with open(_PEER_ENV_PATH) as _f:
            for _line in _f:
                _line = _line.strip()
                if not _line or _line.startswith("#") or "=" not in _line:
                    continue
                _k, _, _v = _line.partition("=")
                _k = _k.strip()
                _v = _v.strip()
                if _k and _v and _k not in os.environ:
                    os.environ[_k] = _v
    except PermissionError:
        pass

ORCH_URL         = os.getenv("ORCH_URL", "http://127.0.0.1:8000/RPC2")
ORCH_TOKEN       = os.getenv("ORCH_TOKEN", "")

WG_INTERFACE     = os.getenv("WG_INTERFACE", "wg0")
WG_BIN           = os.getenv("WG_BIN", "/usr/bin/wg")
WG_QUICK         = os.getenv("WG_QUICK", "/usr/bin/wg-quick")

WG_DIR           = os.getenv("WG_DIR", "/etc/wireguard")
WG_CONF_PATH     = os.getenv("WG_CONF_PATH", f"{WG_DIR}/{WG_INTERFACE}.conf")
WG_PRIV_KEY_PATH = os.getenv("WG_PRIV_KEY_PATH", f"{WG_DIR}/{WG_INTERFACE}.key")
WG_PUB_KEY_PATH  = os.getenv("WG_PUB_KEY_PATH", f"{WG_DIR}/{WG_INTERFACE}.pub")

STATE_PATH       = os.getenv("WG_AUTO_STATE", "/etc/wireguard/wg-auto.json")

DEFAULT_KEEPALIVE       = int(os.getenv("WG_KEEPALIVE", "25"))
WG_HEARTBEAT_INTERVAL   = int(os.getenv("WG_HEARTBEAT_INTERVAL", "25"))

JWT_SCOPES = [x.strip() for x in os.getenv("WG_JWT_SCOPES", "peer:*,network:*,config:*,advertise:*,orch:read").replace(" ", "").split(",") if x.strip()]
JWT_TTL    = int(os.getenv("WG_JWT_TTL", "600"))
