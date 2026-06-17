#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import socket
import subprocess
import sys
from xmlrpc.client import ServerProxy

# ── Auto-cargar /etc/linkguard/peer.env si existe ──────────────────────────
_PEER_ENV_PATH = os.getenv("PEER_ENV_PATH", "/etc/linkguard/peer.env")
if os.path.isfile(_PEER_ENV_PATH):
    try:
        with open(_PEER_ENV_PATH) as _f:
            for _line in _f:
                _line = _line.strip()
                if not _line or _line.startswith("#") or "=" not in _line:
                    continue
                _k, _, _v = _line.partition("=")
                _k = _k.strip(); _v = _v.strip()
                if _k and _v and _k not in os.environ:
                    os.environ[_k] = _v
    except PermissionError:
        pass

ORCH_URL = os.getenv("ORCH_URL", "http://127.0.0.1:8000/RPC2")
STATE_PATH = os.getenv("WG_AUTO_STATE", "/etc/wireguard/wg-auto.json")
ORCH_TOKEN = os.getenv("ORCH_TOKEN", "")

def log(msg: str) -> None:
    print(f"[wg-auto-cli] {msg}", flush=True)

def load_state() -> dict:
    if not os.path.exists(STATE_PATH):
        return {}
    try:
        with open(STATE_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def get_peer_id() -> str:
    state = load_state()
    if "peer_id" in state:
        return state["peer_id"]
    return os.getenv("PEER_ID", socket.gethostname())

def get_auth_token() -> str:
    st = load_state()
    if st.get("jwt"):
        return st["jwt"]
    return ORCH_TOKEN

def get_client(url: str = "") -> ServerProxy:
    url = url or ORCH_URL
    log(f"Conectando a orchestrator en {url}")
    return ServerProxy(url, allow_none=True)

def print_json(obj) -> None:
    print(json.dumps(obj, indent=2, sort_keys=True))

def rpc_call(c, method: str, *args):
    """
    Intenta invocar con token al final.
    Si el método no acepta token, reintenta sin él.
    """
    tok = get_auth_token()
    fn = c.__getattr__(method)
    if tok:
        try:
            return fn(*args, tok)
        except TypeError:
            return fn(*args)
    return fn(*args)

# ============================================================
# WRAPPERS peer.local.* (usando JWT si existe)
# ============================================================

def cmd_local_unregister(args):
    peer_id = get_peer_id()
    c = get_client(args.url)
    log(f"Desregistrando peer_id={peer_id}")
    resp = rpc_call(c, "peer.unregister", peer_id)
    print(resp)

def cmd_local_update(args):
    peer_id = get_peer_id()
    c = get_client(args.url)
    try:
        fields = json.loads(args.fields)
    except Exception as e:
        log(f"ERROR: fields no es JSON válido: {e}")
        sys.exit(1)
    log(f"Actualizando peer_id={peer_id} con fields={fields}")
    resp = rpc_call(c, "peer.update", peer_id, fields)
    print(resp)

def cmd_local_list_networks(args):
    c = get_client(args.url)
    # En modo JWT: network.list(uid, admin_token, token) pero podemos omitir uid/admin_token
    try:
        resp = c.__getattr__("network.list")(None, None, get_auth_token())
    except TypeError:
        resp = rpc_call(c, "network.list")
    print_json(resp)

def cmd_local_add_to_network(args):
    peer_id = get_peer_id()
    c = get_client(args.url)
    log(f"NOTA: add_to_network es admin-only en modo multi-tenant (usa orch-cli / admin token)")
    # Mantengo compat por si el orquestador no está en modo admin-only
    resp = rpc_call(c, "network.add_peer", args.network_id, peer_id, args.role, args.tunnel_ip)
    print(resp)

def cmd_local_remove_from_network(args):
    peer_id = get_peer_id()
    c = get_client(args.url)
    log(f"NOTA: rm-from-network es admin-only en modo multi-tenant (usa orch-cli / admin token)")
    resp = rpc_call(c, "network.remove_peer", args.network_id, peer_id)
    print(resp)

def cmd_local_list_advertised(args):
    peer_id = get_peer_id()
    c = get_client(args.url)
    resp = rpc_call(c, "peer.list_advertised_networks", peer_id)
    print_json(resp)

def cmd_local_add_advertised(args):
    peer_id = get_peer_id()
    c = get_client(args.url)
    log(f"Añadiendo LAN anunciada {args.cidr} en network_id={args.network_id} mode={args.mode} para {peer_id}")
    resp = rpc_call(c, "peer.add_advertised_network", peer_id, args.cidr, args.network_id, args.mode)
    print(resp)

def cmd_local_remove_advertised(args):
    peer_id = get_peer_id()
    c = get_client(args.url)
    adv_id = int(args.adv_id)
    log(f"Eliminando LAN anunciada índice={adv_id} para {peer_id}")
    resp = rpc_call(c, "peer.remove_advertised_network", peer_id, adv_id)
    print(resp)

def cmd_local_topology(args):
    c = get_client(args.url)
    try:
        resp = c.__getattr__("network.get_topology")(args.network_id, None, get_auth_token())
    except TypeError:
        resp = rpc_call(c, "network.get_topology", args.network_id)
    print_json(resp)

def cmd_local_status(args):
    peer_id = get_peer_id()
    c = get_client(args.url)
    resp = rpc_call(c, "peer.get_status", peer_id)
    print_json(resp)

def cmd_local_rotate_key(args):
    cmd = ["wg-auto-register", "rotate-key"]
    if os.geteuid() != 0:
        log("Advertencia: lo normal es ejecutar esto con sudo.")
    log("Delegando a: " + " ".join(cmd))
    rc = subprocess.call(cmd)
    sys.exit(rc)

def cmd_local_orch_health(args):
    c = get_client(args.url)
    resp = rpc_call(c, "orch.health")
    print(resp)


# F5: muestra el estado de los peers mesh configurados localmente
def cmd_local_mesh_status(args):
    """
    Lee el .conf de WireGuard del peer y 'wg show' para mostrar:
    - Peers configurados (bloques [Peer] en el .conf)
    - Estado de handshake activo por peer (vía 'wg show')
    - En hub-mesh: columna MODO (DIRECTO / HUB-RELAY)
    """
    import re, subprocess as sp

    conf_path = os.getenv("WG_CONF_PATH", f"{os.getenv('WG_DIR','/etc/wireguard')}/{os.getenv('WG_INTERFACE','wg0')}.conf")
    iface     = os.getenv("WG_INTERFACE", "wg0")
    state     = load_state()

    topology = state.get("topology", "hub-spoke")
    print(f"[mesh-status]  Topología: {topology}")
    print(f"[mesh-status]  Config:    {conf_path}")
    if topology == "hub-mesh":
        nat_type = state.get("nat_type", "?")
        print(f"[mesh-status]  NAT type:  {nat_type}")
    print()

    # Parsear bloques [Peer] del .conf
    peers_in_conf: list = []
    # Conjunto de peer_ids que tienen bloque directo (para hub-mesh)
    direct_peer_ids: set = set()
    # IPs que reciben route relay (no tienen bloque [Peer] propio)
    relay_comments: list = []
    try:
        txt = open(conf_path).read()
        # Capturar comentarios de tipo "# Relay-via-HUB: <pid>"
        for m in re.finditer(r"#\s*Relay-via-HUB:\s*(\S+)", txt):
            relay_comments.append(m.group(1))
        blocks = re.split(r"\[Peer\]", txt)[1:]
        for b in blocks:
            pub     = re.search(r"PublicKey\s*=\s*(\S+)", b)
            ep      = re.search(r"Endpoint\s*=\s*(\S+)", b)
            aips    = re.search(r"AllowedIPs\s*=\s*(.+)", b)
            comment = re.search(r"#\s*(.+)", b)
            label_raw = comment.group(1).strip() if comment else ""
            is_direct = "Directo:" in label_raw
            if is_direct:
                direct_peer_ids.add(label_raw.replace("Directo:", "").strip())
            peers_in_conf.append({
                "public_key":  pub.group(1) if pub else "?",
                "endpoint":    ep.group(1) if ep else None,
                "allowed_ips": aips.group(1).strip() if aips else "",
                "label":       label_raw,
                "is_direct":   is_direct,
            })
    except FileNotFoundError:
        print(f"  No se encontró el archivo de configuración: {conf_path}")

    # Obtener handshakes activos de 'wg show'
    handshakes: dict = {}
    try:
        out = sp.check_output(["wg", "show", iface, "latest-handshakes"], universal_newlines=True)
        for line in out.strip().splitlines():
            parts = line.split()
            if len(parts) == 2:
                try:
                    handshakes[parts[0]] = int(parts[1])
                except ValueError:
                    pass
    except Exception:
        pass

    now = int(__import__("time").time())

    # HM-F5f: en hub-mesh mostrar columna MODO
    if topology == "hub-mesh":
        fmt = "  {:<22} {:<38} {:<9} {:<7} {:<10}"
        print(fmt.format("LABEL", "ALLOWED IPS", "HANDSHAKE", "ACTIVO", "MODO"))
        print("  " + "-" * 90)
        for p in peers_in_conf:
            pub   = p["public_key"]
            hs    = handshakes.get(pub, 0)
            ago   = f"{now - hs}s" if hs else "nunca"
            alive = "✓" if hs and (now - hs) <= 180 else "✗"
            label = (p["label"] or pub[:16] + "...")[:21]
            modo  = "DIRECTO" if p.get("is_direct") else "HUB-RELAY"
            print(fmt.format(label, p["allowed_ips"][:37], ago, alive, modo))
        # Peers relay sin bloque (solo comentarios en el .conf)
        if relay_comments:
            print()
            print("  Peers sin bloque [Peer] (tráfico vía relay HUB):")
            for pid in relay_comments:
                print(f"    • {pid}")
    else:
        # mesh puro o hub-spoke: tabla original sin columna MODO
        fmt = "  {:<20} {:<45} {:<8} {:<8}"
        print(fmt.format("LABEL / PUBKEY (16)", "ALLOWED IPS", "HANDSHAKE", "ACTIVO"))
        print("  " + "-" * 85)
        for p in peers_in_conf:
            pub   = p["public_key"]
            hs    = handshakes.get(pub, 0)
            ago   = f"{now - hs}s" if hs else "nunca"
            alive = "✓" if hs and (now - hs) <= 180 else "✗"
            label = (p["label"] or pub[:16] + "...")[:19]
            print(fmt.format(label, p["allowed_ips"][:44], ago, alive))

def main():
    parser = argparse.ArgumentParser(description="CLI local para un peer WireGuard gestionado por wg-auto-register")
    parser.add_argument("--url", default=ORCH_URL, help=f"URL del orchestrator (default: {ORCH_URL})")

    subparsers = parser.add_subparsers(dest="command", required=True)

    p_unreg = subparsers.add_parser("unregister", help="peer.local.unregister() → peer.unregister(peer_id)")
    p_unreg.set_defaults(func=cmd_local_unregister)

    p_upd = subparsers.add_parser("update", help='peer.local.update(fields JSON) → peer.update(peer_id, fields)')
    p_upd.add_argument("fields", help='JSON con campos a actualizar')
    p_upd.set_defaults(func=cmd_local_update)

    p_lnets = subparsers.add_parser("list-networks", help="peer.local.list_networks() → network.list()")
    p_lnets.set_defaults(func=cmd_local_list_networks)

    p_addnet = subparsers.add_parser("add-to-network", help="peer.local.add_to_network(network_id, role, tunnel_ip)")
    p_addnet.add_argument("network_id")
    p_addnet.add_argument("role")
    p_addnet.add_argument("tunnel_ip")
    p_addnet.set_defaults(func=cmd_local_add_to_network)

    p_rmnet = subparsers.add_parser("rm-from-network", help="peer.local.remove_from_network(network_id)")
    p_rmnet.add_argument("network_id")
    p_rmnet.set_defaults(func=cmd_local_remove_from_network)

    p_ladv = subparsers.add_parser("list-advertised", help="peer.local.list_advertised()")
    p_ladv.set_defaults(func=cmd_local_list_advertised)

    p_addadv = subparsers.add_parser("add-advertised", help="peer.local.add_advertised(cidr, network_id, mode)")
    p_addadv.add_argument("cidr")
    p_addadv.add_argument("network_id")
    p_addadv.add_argument("mode")
    p_addadv.set_defaults(func=cmd_local_add_advertised)

    p_rmadv = subparsers.add_parser("rm-advertised", help="peer.local.remove_advertised(adv_id)")
    p_rmadv.add_argument("adv_id")
    p_rmadv.set_defaults(func=cmd_local_remove_advertised)

    p_topo = subparsers.add_parser("topology", help="peer.local.topology(network_id)")
    p_topo.add_argument("network_id")
    p_topo.set_defaults(func=cmd_local_topology)

    p_status = subparsers.add_parser("status", help="peer.local.status() → peer.get_status(peer_id)")
    p_status.set_defaults(func=cmd_local_status)

    p_rot = subparsers.add_parser("rotate-key", help="peer.local.rotate_key()")
    p_rot.set_defaults(func=cmd_local_rotate_key)

    p_h = subparsers.add_parser("orch-health", help="peer.local.orch_health() → orch.health()")
    p_h.set_defaults(func=cmd_local_orch_health)

    # F5: estado de peers mesh configurados localmente
    p_ms = subparsers.add_parser("mesh-status",
                                  help="Muestra peers mesh en el .conf local y su estado de handshake")
    p_ms.set_defaults(func=cmd_local_mesh_status)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
