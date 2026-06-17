"""
Monitoreo de handshakes WireGuard para peers directos (hub-mesh).
Reporta cambios de alcanzabilidad al orquestador.
"""

import subprocess
import time

from . import config as cfg
from .state import save_state
from .auth import ensure_jwt_session
from .utils import log, rpc


def probe_direct_peers(peer_id: str, st: dict) -> None:
    if st.get("topology") != "hub-mesh":
        return
    candidates = st.get("hub_mesh_direct_candidates") or []
    if not candidates:
        return

    try:
        out = subprocess.check_output(
            [cfg.WG_BIN, "show", cfg.WG_INTERFACE, "latest-handshakes"], universal_newlines=True  # nosec B603
        )
    except Exception:
        return

    now = int(time.time())
    handshakes: dict = {}
    for line in out.strip().splitlines():
        parts = line.split()
        if len(parts) == 2:
            try:
                handshakes[parts[0]] = int(parts[1])
            except ValueError:
                pass

    prev = st.get("direct_handshake_map") or {}
    c = rpc()
    token = ensure_jwt_session(peer_id, st)
    changed = False

    for mp in candidates:
        pub = mp.get("public_key", "")
        pid = mp.get("peer_id", "")
        if not pub or not pid:
            continue
        hs = handshakes.get(pub, 0)
        alive_now = hs > 0 and (now - hs) <= 180
        was_alive = bool(prev.get(pub, False))

        if alive_now != was_alive:
            try:
                c.__getattr__("peer.report_reachability")(peer_id, pid, alive_now, token)
                log(f"Reachability {pid}: {'directo' if alive_now else 'relay'}")
            except Exception as e:
                log(f"report_reachability error ({pid}): {e}")
        prev[pub] = alive_now
        changed = True

    if changed:
        st["direct_handshake_map"] = prev
