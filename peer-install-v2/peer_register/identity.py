"""
Identidad del peer: hostname, IP local, endpoint, owner.
"""

import os
import socket
import subprocess

from . import config as cfg
from .utils import log


def peer_id_default() -> str:
    return os.getenv("PEER_ID") or socket.gethostname()


def _get_local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        pass
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        pass
    return ""


def peer_endpoint_guess() -> str:
    pub = os.getenv("PUBLIC_IP", "")
    port = os.getenv("WG_LISTEN_PORT", "")
    if not port:
        try:
            out = subprocess.check_output([cfg.WG_BIN, "show", cfg.WG_INTERFACE, "listen-port"], universal_newlines=True).strip()  # nosec B603
            port = out if out else "0"
        except Exception:
            port = "0"
    if pub:
        return f"{pub}:{port}"
    ip = _get_local_ip()
    return f"{ip}:{port}"


def owner_default() -> str:
    return (os.getenv("PEER_OWNER") or os.getenv("USER_ID") or "default").strip() or "default"
