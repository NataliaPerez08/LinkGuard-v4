"""
Comandos CLI: register, heartbeat, run, request-network, rotate-key.
"""

import os
import subprocess
import time
from xmlrpc.client import Fault

from . import config as cfg
from .keys import gen_keys_if_needed, load_public_key, rotate_keys
from .identity import peer_id_default, peer_endpoint_guess, owner_default
from .state import load_state, save_state
from .auth import orch_token_for_call, ensure_jwt_session
from .nat import detect_nat_type
from .probe import probe_direct_peers
from .config_gen import apply_config
from .utils import log, run, rpc


def cmd_register(_args) -> None:
    gen_keys_if_needed()
    peer_id = peer_id_default()
    pub = load_public_key()

    tags = [x.strip() for x in (os.getenv("PEER_TAGS", "")).split(",") if x.strip()]
    metadata = {"owner": owner_default()}

    endpoint = os.getenv("PEER_ENDPOINT", "") or peer_endpoint_guess()

    log(f"Conectando a orchestrator en {cfg.ORCH_URL}")
    c = rpc()

    token = orch_token_for_call(peer_id)
    resp = c.__getattr__("peer.register")(peer_id, pub, endpoint, tags, metadata, token)
    log(f"peer.register -> {resp}")

    st = load_state()
    st["peer_id"] = resp["peer_id"]
    st["config_version"] = resp.get("config_version", 1)
    save_state(st)

    apply_config(peer_id)
    run([cfg.WG_BIN, "show", cfg.WG_INTERFACE], check=False)


def cmd_heartbeat(_args) -> None:
    st = load_state()
    peer_id = st.get("peer_id") or peer_id_default()

    detected_endpoint = os.getenv("PEER_ENDPOINT", "") or peer_endpoint_guess()

    nat_cache_ts = int(st.get("nat_type_detected_ts", 0))
    if int(time.time()) - nat_cache_ts > 300:
        nat_type = detect_nat_type()
        st["nat_type"] = nat_type
        st["nat_type_detected_ts"] = int(time.time())
        save_state(st)
    else:
        nat_type = st.get("nat_type", "symmetric")

    status = {
        "ts":       int(time.time()),
        "wg":       run([cfg.WG_BIN, "show", cfg.WG_INTERFACE], check=False, capture=True)[:4000],
        "endpoint": detected_endpoint,
        "nat_type": nat_type,
    }

    c = rpc()
    token = ensure_jwt_session(peer_id, st)
    resp = c.__getattr__("peer.heartbeat")(peer_id, status, token)
    log(f"peer.heartbeat -> {resp}")

    desired_version = int(resp.get("desired_config_version", st.get("config_version", 1)))
    current_version = int(st.get("config_version", 1))
    current_mp_hash = st.get("mesh_peers_hash", "")
    topology        = st.get("topology", "hub-spoke")

    need_reapply = False

    if desired_version != current_version:
        log(f"Config version cambio {current_version} -> {desired_version}, reaplicando...")
        need_reapply = True

    if not need_reapply and topology in ("mesh", "hub-mesh"):
        new_mp_hash = resp.get("mesh_peers_hash", "") or resp.get("hub_mesh_peers_hash", "")
        if new_mp_hash and new_mp_hash != current_mp_hash:
            log(f"Lista de peers {topology} cambio (hash {current_mp_hash[:8]}->{new_mp_hash[:8]}), reaplicando...")
            need_reapply = True

    if need_reapply:
        apply_config(peer_id)
        st = load_state()
        st["config_version"] = desired_version
        save_state(st)

    if topology == "hub-mesh":
        st = load_state()
        probe_direct_peers(peer_id, st)
        save_state(st)


def cmd_run(args) -> None:
    interval = int(getattr(args, "interval", cfg.WG_HEARTBEAT_INTERVAL))

    try:
        log("Modo run: ejecutando register")
        cmd_register(args)
    except Exception as e:
        log(f"register fallo (continuaremos reintentando): {e}")

    while True:
        try:
            cmd_heartbeat(args)
        except Fault as f:
            log(f"heartbeat Fault: {f}")
        except Exception as e:
            log(f"heartbeat error: {e}")

        time.sleep(interval)


def cmd_request_network(args) -> None:
    st = load_state()
    peer_id = st.get("peer_id") or peer_id_default()
    net = args.network_id
    c = rpc()
    token = ensure_jwt_session(peer_id, st)
    resp = c.__getattr__("peer.request_network")(peer_id, net, token)
    log(f"peer.request_network -> {resp}")
    if args.apply:
        apply_config(peer_id)
        run([cfg.WG_BIN, "show", cfg.WG_INTERFACE], check=False)


def cmd_rotate_key(_args) -> None:
    st = load_state()
    peer_id = st.get("peer_id") or peer_id_default()

    priv, pub = rotate_keys()

    c = rpc()
    token = ensure_jwt_session(peer_id, st)
    resp = c.__getattr__("peer.rotate_key")(peer_id, pub, token)
    log(f"peer.rotate_key -> {resp}")

    apply_config(peer_id)
    run([cfg.WG_BIN, "show", cfg.WG_INTERFACE], check=False)
