"""
Generacion y aplicacion de configuracion WireGuard.
Construye el .conf y sincroniza via wg syncconf.
"""

import os
import subprocess
import tempfile

from . import config as cfg
from .keys import load_private_key
from .auth import orch_token_for_call
from .state import load_state, save_state
from .utils import log, run, rpc, write_file


def _fetch_config(peer_id: str) -> dict:
    c = rpc()
    token = orch_token_for_call(peer_id)
    return c.__getattr__("config.get_peer_config")(peer_id, token)


def _build_interface_block(d: dict) -> str:
    addr = d["interface"]["address"]
    mtu  = int(d["interface"].get("mtu", 1420))
    priv = load_private_key()
    listen_port = (os.getenv("WG_LISTEN_PORT", "") or "").strip()
    listen = f"ListenPort = {listen_port}\n" if listen_port and listen_port != "0" else ""
    return f"[Interface]\nAddress = {addr}\nPrivateKey = {priv}\nMTU = {mtu}\n{listen}"


def _build_hub_block(d: dict) -> str:
    hub_pub   = d["peer"]["public_key"]
    hub_ep    = d["peer"]["endpoint"]
    hub_aips  = d["peer"]["allowed_ips"]
    keepalive = int(d["peer"].get("persistent_keepalive", cfg.DEFAULT_KEEPALIVE))
    topology  = d.get("meta", {}).get("topology", "hub-spoke")
    label     = "relay de fallback" if topology == "hub-mesh" else "bootstrap"
    return (f"\n# HUB ({label})\n"
            f"[Peer]\nPublicKey = {hub_pub}\nEndpoint = {hub_ep}\n"
            f"AllowedIPs = {hub_aips}\nPersistentKeepalive = {keepalive}\n")


def _build_mesh_blocks(d: dict) -> str:
    keepalive = int(d["peer"].get("persistent_keepalive", cfg.DEFAULT_KEEPALIVE))
    mesh_peers = d.get("mesh_peers") or []
    if not mesh_peers:
        return ""
    log(f"Topologia mesh: generando {len(mesh_peers)} bloques [Peer] adicionales")
    result = ""
    for mp in mesh_peers:
        pid      = mp.get("peer_id", "?")
        mp_pub   = mp.get("public_key", "")
        mp_ep    = mp.get("endpoint")
        mp_ip    = mp.get("tunnel_ip", "")
        mp_alive = mp.get("alive", False)
        if not mp_pub or not mp_ip:
            continue
        result += f"\n# Peer directo: {pid} (alive={mp_alive})\n"
        result += f"[Peer]\nPublicKey = {mp_pub}\n"
        result += f"AllowedIPs = {mp_ip}/32\n"
        if mp_ep and mp_alive:
            result += f"Endpoint = {mp_ep}\n"
        result += f"PersistentKeepalive = {keepalive}\n"
    return result


def _build_hub_mesh_blocks(d: dict) -> str:
    keepalive = int(d["peer"].get("persistent_keepalive", cfg.DEFAULT_KEEPALIVE))
    direct_peers = d.get("hub_mesh_direct_peers") or []
    relay_peers  = d.get("hub_mesh_relay_peers") or []
    log(f"Topologia hub-mesh: {len(direct_peers)} directos, {len(relay_peers)} via relay HUB")
    result = ""

    for mp in direct_peers:
        pid    = mp.get("peer_id", "?")
        mp_pub = mp.get("public_key", "")
        mp_ep  = mp.get("endpoint")
        mp_ip  = mp.get("tunnel_ip", "")
        if not mp_pub or not mp_ip:
            continue
        result += f"\n# Directo: {pid}\n"
        result += f"[Peer]\nPublicKey = {mp_pub}\nEndpoint = {mp_ep}\n"
        result += f"AllowedIPs = {mp_ip}/32\nPersistentKeepalive = {keepalive}\n"

    for mp in relay_peers:
        pid      = mp.get("peer_id", "?")
        nat_type = mp.get("nat_type", "?")
        result += f"# Relay-via-HUB: {pid} (nat={nat_type}, sin bloque directo)\n"

    return result


def _save_state_metadata(d: dict, topology: str) -> None:
    st = load_state()
    st["topology"] = topology
    if topology == "hub-mesh":
        st["mesh_peers_hash"]           = d.get("meta", {}).get("hub_mesh_peers_hash", "")
        st["hub_mesh_direct_candidates"] = d.get("hub_mesh_direct_peers") or []
    else:
        st["mesh_peers_hash"]           = d.get("meta", {}).get("mesh_peers_hash", "")
        st["hub_mesh_direct_candidates"] = []
    save_state(st)


def _sync_wg() -> None:
    if subprocess.run(["/sbin/ip", "link", "show", cfg.WG_INTERFACE],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        strip_out = subprocess.check_output([cfg.WG_QUICK, "strip", cfg.WG_INTERFACE], universal_newlines=True)  # nosec B603
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False)
        tmp.write(strip_out)
        tmp.close()
        subprocess.run([cfg.WG_BIN, "syncconf", cfg.WG_INTERFACE, tmp.name], check=True)  # nosec B603
        os.unlink(tmp.name)
    else:
        run([cfg.WG_QUICK, "up", cfg.WG_INTERFACE], check=True)


def apply_config(peer_id: str) -> int:
    cfg_resp = _fetch_config(peer_id)
    topology = cfg_resp.get("meta", {}).get("topology", "hub-spoke")

    conf  = _build_interface_block(cfg_resp)
    conf += _build_hub_block(cfg_resp)
    if topology == "mesh":
        conf += _build_mesh_blocks(cfg_resp)
    elif topology == "hub-mesh":
        conf += _build_hub_mesh_blocks(cfg_resp)

    write_file(cfg.WG_CONF_PATH, conf, 0o600)
    _save_state_metadata(cfg_resp, topology)

    st = load_state()
    desired_version = int(cfg_resp.get("meta", {}).get("config_version", st.get("config_version", 1)))

    _sync_wg()
    return desired_version
