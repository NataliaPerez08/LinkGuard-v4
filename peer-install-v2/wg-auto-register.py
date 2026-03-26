#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# wg-auto-register v4
# SEC-05:   Estado del peer guardado con permisos 600 (JWT no legible por otros usuarios)
# SEC-03:   ORCH_TOKEN requerido con mensaje de error claro
# MESH-F3a: apply_config genera N bloques [Peer] en redes mesh
# MESH-F3b: cmd_heartbeat detecta cambio de mesh_peers_hash y reaplica config
# MESH-F3c: cmd_heartbeat incluye endpoint detectado en el status
# HM-F4a:  apply_config genera .conf hub-mesh: HUB=/CIDR, directos=/32, relay sin bloque
# HM-F4b:  _detect_nat_type: heurística none|full-cone|symmetric
# HM-F4c:  _probe_direct_peers: monitor handshakes → peer.report_reachability
# HM-F4d:  cmd_heartbeat: incluye nat_type, llama _probe_direct_peers en hub-mesh

import os
import json
import time
import socket
import argparse
import subprocess
from xmlrpc.client import ServerProxy, Fault

# ── Auto-cargar /etc/linkguard/peer.env si existe y las vars no están en el entorno ──
# Esto permite ejecutar wg-auto-register manualmente (sin systemd) sin tener que
# exportar variables a mano.
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
                # Solo cargar si la variable NO está ya en el entorno (no sobreescribe exports)
                if _k and _v and _k not in os.environ:
                    os.environ[_k] = _v
    except PermissionError:
        pass  # Si no tenemos permiso de leer el archivo, el error saldrá luego al validar ORCH_TOKEN

ORCH_URL = os.getenv("ORCH_URL", "http://127.0.0.1:8000/RPC2")

# En modo "mixto":
# - ORCH_TOKEN: user token (emitido por orch.user-create / orch.issue-user-token) o bootstrap legacy
# - Se transforma a JWT vía auth.login() y desde ahí se usa JWT para todas las llamadas.
ORCH_TOKEN = os.getenv("ORCH_TOKEN", "")  # requerido si el orquestador exige auth

WG_INTERFACE = os.getenv("WG_INTERFACE", "wg0")
WG_BIN = os.getenv("WG_BIN", "/usr/bin/wg")
WG_QUICK = os.getenv("WG_QUICK", "/usr/bin/wg-quick")

WG_DIR = os.getenv("WG_DIR", "/etc/wireguard")
WG_CONF_PATH = os.getenv("WG_CONF_PATH", f"{WG_DIR}/{WG_INTERFACE}.conf")
WG_PRIV_KEY_PATH = os.getenv("WG_PRIV_KEY_PATH", f"{WG_DIR}/{WG_INTERFACE}.key")
WG_PUB_KEY_PATH = os.getenv("WG_PUB_KEY_PATH", f"{WG_DIR}/{WG_INTERFACE}.pub")

STATE_PATH = os.getenv("WG_AUTO_STATE", "/etc/wireguard/wg-auto.json")

DEFAULT_KEEPALIVE = int(os.getenv("WG_KEEPALIVE", "25"))
WG_HEARTBEAT_INTERVAL = int(os.getenv("WG_HEARTBEAT_INTERVAL", "25"))

# JWT session
JWT_SCOPES = [x.strip() for x in os.getenv("WG_JWT_SCOPES", "peer:* , network:* , config:* , advertise:* , orch:read").replace(" ", "").split(",") if x.strip()]
JWT_TTL = int(os.getenv("WG_JWT_TTL", "600"))  # seg


def log(msg: str):
    print(f"[wg-auto-register] {msg}", flush=True)


def run(cmd, check=True, capture=False) -> str:
    log(f"RUN: {' '.join(cmd)}")
    if capture:
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if check and r.returncode != 0:
            raise RuntimeError(r.stdout.strip())
        return r.stdout
    r = subprocess.run(cmd)
    if check and r.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    return ""


def ensure_dir():
    os.makedirs(WG_DIR, exist_ok=True)


def write_file(path: str, content: str, mode: int = 0o600):
    with open(path, "w") as f:
        f.write(content)
    os.chmod(path, mode)


def read_file(path: str) -> str:
    with open(path, "r") as f:
        return f.read().strip()


def gen_keys_if_needed():
    ensure_dir()
    if os.path.exists(WG_PRIV_KEY_PATH) and os.path.exists(WG_PUB_KEY_PATH):
        return
    priv = subprocess.check_output([WG_BIN, "genkey"], text=True).strip()
    write_file(WG_PRIV_KEY_PATH, priv + "\n", 0o600)
    pub = subprocess.check_output(["bash", "-lc", f"echo '{priv}' | {WG_BIN} pubkey"], text=True).strip()
    write_file(WG_PUB_KEY_PATH, pub + "\n", 0o600)
    log("Llaves del peer generadas")


def peer_id_default() -> str:
    return os.getenv("PEER_ID") or socket.gethostname()


def _get_local_ip() -> str:
    """Obtiene la IP local principal sin depender de 'hostname -I' (no disponible en todas las distros)."""
    # Método 1: conectar UDP a un destino externo (no envía paquetes reales)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        pass
    # Método 2: hostname → resolución DNS local
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
            out = subprocess.check_output([WG_BIN, "show", WG_INTERFACE, "listen-port"], text=True).strip()
            port = out if out else "0"
        except Exception:
            port = "0"
    if pub:
        return f"{pub}:{port}"
    ip = _get_local_ip()
    return f"{ip}:{port}"


def owner_default() -> str:
    # tenant/user_id del peer
    return (os.getenv("PEER_OWNER") or os.getenv("USER_ID") or "default").strip() or "default"


def rpc():
    return ServerProxy(ORCH_URL, allow_none=True)


def load_state() -> dict:
    try:
        return json.load(open(STATE_PATH))
    except Exception:
        return {}


def save_state(st: dict):
    ensure_dir()
    with open(STATE_PATH, "w") as f:
        json.dump(st, f, indent=2, sort_keys=True)
    # SEC-05: state file contains JWT; restrict permissions to owner only
    os.chmod(STATE_PATH, 0o600)


def _jwt_needs_refresh(st: dict) -> bool:
    exp = int(st.get("jwt_expires_at") or 0)
    if not exp:
        return True
    # refresh 60s before expiry
    return int(time.time()) >= (exp - 60)


def ensure_jwt_session(peer_id: str, st: dict) -> str:
    """
    Obtiene/renueva JWT para operar el orquestador.
    """
    if "jwt" in st and not _jwt_needs_refresh(st):
        return st["jwt"]

    if not ORCH_TOKEN:
        raise RuntimeError(
            "ORCH_TOKEN está vacío. Configura ORCH_TOKEN en /etc/linkguard/peer.env "
            "(obtén el token del admin del orchestrator con: orch-cli issue-user-token <user_id>)"
        )

    c = rpc()
    uid = owner_default()
    if "jwt" in st and _jwt_needs_refresh(st):
        try:
            resp = c.__getattr__("auth.refresh")(st["jwt"], JWT_TTL)
            st["jwt"] = resp["jwt"]
            st["jwt_expires_at"] = int(resp["expires_at"])
            save_state(st)
            return st["jwt"]
        except Exception as e:
            log(f"JWT refresh falló, re-login: {e}")

    resp = c.__getattr__("auth.login")(uid, peer_id, ORCH_TOKEN, JWT_SCOPES, JWT_TTL)
    st["jwt"] = resp["jwt"]
    st["jwt_expires_at"] = int(resp["expires_at"])
    save_state(st)
    return st["jwt"]


def orch_token_for_call(peer_id: str) -> str:
    st = load_state()
    return ensure_jwt_session(peer_id, st)


# HM-F4b: heurística para clasificar el tipo de NAT del peer
def _detect_nat_type() -> str:
    """
    Clasifica el NAT del host actual:
      none        — IP pública directa (sin NAT)
      full-cone   — NAT que mantiene el mismo puerto externo (hole-punch posible)
      symmetric   — NAT diferente por destino (hole-punch imposible, relay obligatorio)

    Se usa un valor conservador (symmetric) ante cualquier ambigüedad para evitar
    bloquear tráfico que dependería del relay del HUB.
    """
    import socket as _sock
    pub_env   = os.getenv("PUBLIC_IP", "").strip()
    listen_port = int(os.getenv("WG_LISTEN_PORT", "0") or "0")

    # Sin PUBLIC_IP configurado: conservador
    if not pub_env:
        return "symmetric"

    # Obtener IP local principal
    try:
        local_ip = _get_local_ip()
        if not local_ip:
            return "symmetric"
    except Exception:
        return "symmetric"

    # Si PUBLIC_IP == IP local: sin NAT
    if pub_env == local_ip:
        return "none"

    # Sin puerto de escucha: no podemos confirmar full-cone
    if listen_port == 0:
        return "symmetric"

    # Intentar determinar full-cone vs symmetric
    # (mismo puerto origen al conectar a dos destinos distintos → full-cone)
    try:
        s1 = _sock.socket(_sock.AF_INET, _sock.SOCK_DGRAM)
        s1.bind(("", listen_port))
        s1.connect(("8.8.8.8", 53))
        port1 = s1.getsockname()[1]
        s1.close()
        s2 = _sock.socket(_sock.AF_INET, _sock.SOCK_DGRAM)
        s2.bind(("", listen_port))
        s2.connect(("1.1.1.1", 53))
        port2 = s2.getsockname()[1]
        s2.close()
        return "full-cone" if port1 == port2 else "symmetric"
    except Exception:
        return "symmetric"


# HM-F4c: monitorea handshakes WireGuard y reporta cambios de alcanzabilidad al orchestrator
def _probe_direct_peers(peer_id: str, st: dict):
    """
    Compara handshakes activos ('wg show latest-handshakes') contra los peers directos
    configurados en el último apply_config de tipo hub-mesh.
    Por cada cambio (peer gana/pierde handshake directo) llama peer.report_reachability.
    """
    if st.get("topology") != "hub-mesh":
        return
    candidates = st.get("hub_mesh_direct_candidates") or []
    if not candidates:
        return

    try:
        out = subprocess.check_output(
            [WG_BIN, "show", WG_INTERFACE, "latest-handshakes"], text=True
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


def apply_config(peer_id: str):
    c = rpc()
    token = orch_token_for_call(peer_id)
    cfg = c.__getattr__("config.get_peer_config")(peer_id, token)

    addr      = cfg["interface"]["address"]
    mtu       = int(cfg["interface"].get("mtu", 1420))
    hub_pub   = cfg["peer"]["public_key"]
    hub_ep    = cfg["peer"]["endpoint"]
    hub_aips  = cfg["peer"]["allowed_ips"]
    keepalive = int(cfg["peer"].get("persistent_keepalive", DEFAULT_KEEPALIVE))
    topology  = cfg.get("meta", {}).get("topology", "hub-spoke")

    priv = read_file(WG_PRIV_KEY_PATH)

    # Bloque [Interface] — igual para todas las topologías
    conf = f"[Interface]\nAddress = {addr}\nPrivateKey = {priv}\nMTU = {mtu}\n"

    # Bloque HUB — siempre primero (bootstrap + relay en hub-mesh)
    conf += f"\n# HUB ({'relay de fallback' if topology == 'hub-mesh' else 'bootstrap'})\n"
    conf += f"[Peer]\nPublicKey = {hub_pub}\nEndpoint = {hub_ep}\n"
    conf += f"AllowedIPs = {hub_aips}\nPersistentKeepalive = {keepalive}\n"

    # ── mesh puro (v3) ──────────────────────────────────────────────
    mesh_peers = cfg.get("mesh_peers") or []
    if topology == "mesh" and mesh_peers:
        log(f"Topología mesh: generando {len(mesh_peers)} bloques [Peer] adicionales")
        for mp in mesh_peers:
            pid      = mp.get("peer_id", "?")
            mp_pub   = mp.get("public_key", "")
            mp_ep    = mp.get("endpoint")
            mp_ip    = mp.get("tunnel_ip", "")
            mp_alive = mp.get("alive", False)
            if not mp_pub or not mp_ip:
                continue
            conf += f"\n# Peer directo: {pid} (alive={mp_alive})\n"
            conf += f"[Peer]\nPublicKey = {mp_pub}\n"
            conf += f"AllowedIPs = {mp_ip}/32\n"
            if mp_ep and mp_alive:
                conf += f"Endpoint = {mp_ep}\n"
            conf += f"PersistentKeepalive = {keepalive}\n"

    # ── hub-mesh (v4) ───────────────────────────────────────────────
    elif topology == "hub-mesh":
        direct_peers = cfg.get("hub_mesh_direct_peers") or []
        relay_peers  = cfg.get("hub_mesh_relay_peers")  or []
        log(f"Topología hub-mesh: {len(direct_peers)} directos, {len(relay_peers)} via relay HUB")

        for mp in direct_peers:
            pid    = mp.get("peer_id", "?")
            mp_pub = mp.get("public_key", "")
            mp_ep  = mp.get("endpoint")
            mp_ip  = mp.get("tunnel_ip", "")
            if not mp_pub or not mp_ip:
                continue
            # /32 más específico que el /CIDR del HUB → prioridad de routing WireGuard
            conf += f"\n# Directo: {pid}\n"
            conf += f"[Peer]\nPublicKey = {mp_pub}\nEndpoint = {mp_ep}\n"
            conf += f"AllowedIPs = {mp_ip}/32\nPersistentKeepalive = {keepalive}\n"

        # Peers relay: sin bloque [Peer] propio → tráfico cae al /CIDR del HUB
        for mp in relay_peers:
            pid      = mp.get("peer_id", "?")
            nat_type = mp.get("nat_type", "?")
            conf += f"# Relay-via-HUB: {pid} (nat={nat_type}, sin bloque directo)\n"

    write_file(WG_CONF_PATH, conf, 0o600)

    # Persistir hash y metadata para detección de cambios en heartbeat
    st = load_state()
    st["topology"] = topology
    if topology == "hub-mesh":
        st["mesh_peers_hash"]           = cfg.get("meta", {}).get("hub_mesh_peers_hash", "")
        # Guardar candidatos directos para _probe_direct_peers
        st["hub_mesh_direct_candidates"] = cfg.get("hub_mesh_direct_peers") or []
    else:
        st["mesh_peers_hash"]           = cfg.get("meta", {}).get("mesh_peers_hash", "")
        st["hub_mesh_direct_candidates"] = []
    save_state(st)

    if subprocess.run(["/sbin/ip", "link", "show", WG_INTERFACE],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        run(["bash", "-lc", f"{WG_BIN} syncconf {WG_INTERFACE} <({WG_QUICK} strip {WG_INTERFACE})"], check=True)
    else:
        run([WG_QUICK, "up", WG_INTERFACE], check=True)


def cmd_register(_args):
    gen_keys_if_needed()
    peer_id = peer_id_default()
    pub = read_file(WG_PUB_KEY_PATH)

    tags = [x.strip() for x in (os.getenv("PEER_TAGS", "")).split(",") if x.strip()]
    metadata = {}
    metadata["owner"] = owner_default()

    endpoint = os.getenv("PEER_ENDPOINT", "") or peer_endpoint_guess()

    log(f"Conectando a orchestrator en {ORCH_URL}")
    c = rpc()

    token = orch_token_for_call(peer_id)
    resp = c.__getattr__("peer.register")(peer_id, pub, endpoint, tags, metadata, token)
    log(f"peer.register -> {resp}")

    st = load_state()
    st["peer_id"] = resp["peer_id"]
    st["config_version"] = resp.get("config_version", 1)
    save_state(st)

    apply_config(peer_id)
    run([WG_BIN, "show", WG_INTERFACE], check=False)


def cmd_heartbeat(_args):
    st = load_state()
    peer_id = st.get("peer_id") or peer_id_default()

    # F3: incluir el endpoint detectado para que el orchestrator lo propague a otros peers mesh
    detected_endpoint = os.getenv("PEER_ENDPOINT", "") or peer_endpoint_guess()

    # HM-F4d: detectar NAT type, cachearlo 5 min para no hacer el probe en cada heartbeat
    nat_cache_ts = int(st.get("nat_type_detected_ts", 0))
    if int(time.time()) - nat_cache_ts > 300:
        nat_type = _detect_nat_type()
        st["nat_type"] = nat_type
        st["nat_type_detected_ts"] = int(time.time())
        save_state(st)
    else:
        nat_type = st.get("nat_type", "symmetric")

    status = {
        "ts":       int(time.time()),
        "wg":       run([WG_BIN, "show", WG_INTERFACE], check=False, capture=True)[:4000],
        "endpoint": detected_endpoint,
        "nat_type": nat_type,   # HM-F4d
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
        log(f"Config version cambió {current_version} → {desired_version}, reaplicando...")
        need_reapply = True

    # F3 / HM-F4d: en redes mesh/hub-mesh, verificar si la lista de peers cambió
    if not need_reapply and topology in ("mesh", "hub-mesh"):
        new_mp_hash = resp.get("mesh_peers_hash", "") or resp.get("hub_mesh_peers_hash", "")
        if new_mp_hash and new_mp_hash != current_mp_hash:
            log(f"Lista de peers {topology} cambió (hash {current_mp_hash[:8]}→{new_mp_hash[:8]}), reaplicando...")
            need_reapply = True

    if need_reapply:
        apply_config(peer_id)
        st = load_state()  # apply_config puede haberlo actualizado
        st["config_version"] = desired_version
        save_state(st)

    # HM-F4d: probe de handshakes directos (solo hub-mesh, después de posible re-apply)
    if topology == "hub-mesh":
        st = load_state()
        _probe_direct_peers(peer_id, st)
        save_state(st)


def cmd_run(args):
    session = getattr(args, "session", "default") or "default"
    interval = int(getattr(args, "interval", WG_HEARTBEAT_INTERVAL))

    try:
        log(f"Modo run: ejecutando register (session={session})")
        cmd_register(args)
    except Exception as e:
        log(f"register falló (continuaremos reintentando): {e}")

    while True:
        try:
            cmd_heartbeat(args)
        except Fault as f:
            log(f"heartbeat Fault: {f}")
        except Exception as e:
            log(f"heartbeat error: {e}")

        time.sleep(interval)


def cmd_request_network(args):
    st = load_state()
    peer_id = st.get("peer_id") or peer_id_default()
    net = args.network_id
    c = rpc()
    token = ensure_jwt_session(peer_id, st)
    resp = c.__getattr__("peer.request_network")(peer_id, net, token)
    log(f"peer.request_network -> {resp}")
    if args.apply:
        apply_config(peer_id)
        run([WG_BIN, "show", WG_INTERFACE], check=False)


def cmd_rotate_key(_args):
    st = load_state()
    peer_id = st.get("peer_id") or peer_id_default()

    priv = subprocess.check_output([WG_BIN, "genkey"], text=True).strip()
    pub = subprocess.check_output(["bash", "-lc", f"echo '{priv}' | {WG_BIN} pubkey"], text=True).strip()
    write_file(WG_PRIV_KEY_PATH, priv + "\n", 0o600)
    write_file(WG_PUB_KEY_PATH, pub + "\n", 0o600)

    c = rpc()
    token = ensure_jwt_session(peer_id, st)
    resp = c.__getattr__("peer.rotate_key")(peer_id, pub, token)
    log(f"peer.rotate_key -> {resp}")

    apply_config(peer_id)
    run([WG_BIN, "show", WG_INTERFACE], check=False)


def main():
    ap = argparse.ArgumentParser(description="Peer auto-register + heartbeat + JWT session + multi-network")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_reg = sub.add_parser("register")
    p_reg.set_defaults(func=cmd_register)

    p_hb = sub.add_parser("heartbeat")
    p_hb.set_defaults(func=cmd_heartbeat)

    p_run = sub.add_parser("run", help="Daemon: register + heartbeat en loop")
    p_run.add_argument("--interval", type=int, default=WG_HEARTBEAT_INTERVAL, help="segundos entre heartbeats")
    p_run.add_argument("--session", default=os.getenv("WG_SESSION", "default"), help="session id (default)")
    p_run.set_defaults(func=cmd_run)

    p_req = sub.add_parser("request-network")
    p_req.add_argument("network_id")
    p_req.add_argument("--apply", action="store_true")
    p_req.set_defaults(func=cmd_request_network)

    p_rot = sub.add_parser("rotate-key")
    p_rot.set_defaults(func=cmd_rotate_key)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
