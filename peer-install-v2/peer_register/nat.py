"""
Deteccion heuristica del tipo de NAT del peer.

Clasificaciones:
  none        - IP publica directa (sin NAT)
  full-cone   - mismo puerto externo se mantiene (hole-punch posible)
  symmetric   - puerto diferente por destino (relay obligatorio)
"""

import os
import socket

from .identity import _get_local_ip


def detect_nat_type() -> str:
    pub_env = os.getenv("PUBLIC_IP", "").strip()
    listen_port = int(os.getenv("WG_LISTEN_PORT", "0") or "0")

    if not pub_env:
        return "symmetric"

    try:
        local_ip = _get_local_ip()
        if not local_ip:
            return "symmetric"
    except Exception:
        return "symmetric"

    if pub_env == local_ip:
        return "none"

    if listen_port == 0:
        return "symmetric"

    try:
        s1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s1.bind(("", listen_port))
        s1.connect(("8.8.8.8", 53))
        port1 = s1.getsockname()[1]
        s1.close()
        s2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s2.bind(("", listen_port))
        s2.connect(("1.1.1.1", 53))
        port2 = s2.getsockname()[1]
        s2.close()
        return "full-cone" if port1 == port2 else "symmetric"
    except Exception:
        return "symmetric"
