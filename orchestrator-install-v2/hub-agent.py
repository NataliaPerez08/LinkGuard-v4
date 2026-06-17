#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LinkGuard / TLB-WG Hub Agent - v3

Cambios v1 → v2:
  SEC-01:  Validación de token al arranque; rechaza arrancar con 'changeme' o vacío
  HA-02:   Soporte opcional TLS en el servidor XML-RPC (HUB_AGENT_TLS=1)
  HA-03:   HUB_AGENT_BIND por defecto 127.0.0.1 (no expuesto a toda la red)
  OPS-01:  Script de cleanup de reglas iptables (hub_cleanup_rules) llamado en PreStop
  OPS-02:  Verificación de dependencias (wg, wg-quick, iptables, sysctl) al arranque

Cambios v2 → v3 (Hub-Mesh):
  HM-F5a:  HUB_MESH_MODE: bool → enum 'off'|'mesh'|'hub-mesh' (compat '0'/'1' mantenida)
  HM-F5b:  hub_apply_peer bifurca comportamiento por HUB_MESH_MODE enum
  HM-F5c:  ensure_base_rules_internal: log explícito cuando relay hub-mesh está activo
"""

import defusedxml.xmlrpc

defusedxml.xmlrpc.monkey_patch()

import ipaddress
import os
import secrets
import shutil
import ssl
import subprocess  # nosec B404
import time
from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler  # nosec B411

# =========================
# CONFIGURACIÓN
# =========================

HUB_WG_IFACE      = os.getenv("HUB_WG_IFACE", "wg-HUB")
WG_BIN            = os.getenv("WG_BIN", "/usr/bin/wg")
WG_QUICK          = os.getenv("WG_QUICK", "/usr/bin/wg-quick")
IPTABLES_BIN      = os.getenv("IPTABLES_BIN", "/sbin/iptables")
SYSCTL_BIN        = os.getenv("SYSCTL_BIN", "/sbin/sysctl")

# HA-03: bind por defecto a 127.0.0.1 (no 0.0.0.0)
HUB_AGENT_BIND    = os.getenv("HUB_AGENT_BIND", "127.0.0.1")
_HUB_AGENT_PORT_STR = os.getenv("HUB_AGENT_PORT", "9000")
try:
    HUB_AGENT_PORT = int(_HUB_AGENT_PORT_STR)
except ValueError:
    raise SystemExit(
        f"[hub-agent] ERROR: HUB_AGENT_PORT no es un entero válido: '{_HUB_AGENT_PORT_STR}'"
    )
if not (1 <= HUB_AGENT_PORT <= 65535):
    raise SystemExit(
        f"[hub-agent] ERROR: HUB_AGENT_PORT fuera de rango (1-65535): {HUB_AGENT_PORT}"
    )

# HA-02: TLS opcional
HUB_AGENT_TLS     = os.getenv("HUB_AGENT_TLS", "0") == "1"
HUB_AGENT_CERT    = os.getenv("HUB_AGENT_CERT", "/etc/linkguard/hub-agent.crt")
HUB_AGENT_KEY     = os.getenv("HUB_AGENT_KEY", "/etc/linkguard/hub-agent.key")

HUB_TUNNEL_IP     = os.getenv("HUB_TUNNEL_IP", "10.20.30.1/24")
_HUB_LISTEN_PORT_STR = os.getenv("HUB_LISTEN_PORT", "51820")
try:
    HUB_LISTEN_PORT = int(_HUB_LISTEN_PORT_STR)
except ValueError:
    raise SystemExit(
        f"[hub-agent] ERROR: HUB_LISTEN_PORT no es un entero válido: '{_HUB_LISTEN_PORT_STR}'"
    )
if not (1 <= HUB_LISTEN_PORT <= 65535):
    raise SystemExit(
        f"[hub-agent] ERROR: HUB_LISTEN_PORT fuera de rango (1-65535): {HUB_LISTEN_PORT}"
    )
WG_DIR            = os.getenv("WG_DIR", "/etc/wireguard")
HUB_CONF_PATH     = os.getenv("HUB_CONF_PATH", f"{WG_DIR}/{HUB_WG_IFACE}.conf")
HUB_PRIVKEY_PATH  = os.getenv("HUB_PRIVKEY_PATH", f"{WG_DIR}/{HUB_WG_IFACE}.key")
HUB_PUBKEY_PATH   = os.getenv("HUB_PUBKEY_PATH", f"{WG_DIR}/{HUB_WG_IFACE}.pub")

HUB_ENABLE_NAT    = os.getenv("HUB_ENABLE_NAT", "1") == "1"
HUB_NAT_OUT_IFACE = os.getenv("HUB_NAT_OUT_IFACE", "eth0")
TUNNEL_CIDR       = os.getenv("HUB_TUNNEL_CIDR", "10.20.30.0/24")

# HM-F5a: HUB_MESH_MODE extendido a enum 'off'|'mesh'|'hub-mesh'
# Compatibilidad v3: '0' → 'off', '1' → 'mesh'
_HUB_MESH_RAW = os.getenv("HUB_MESH_MODE", "off").strip().lower()
_HUB_MESH_COMPAT = {"0": "off", "1": "mesh"}
HUB_MESH_MODE = _HUB_MESH_COMPAT.get(_HUB_MESH_RAW, _HUB_MESH_RAW)
if HUB_MESH_MODE not in ("off", "mesh", "hub-mesh"):
    raise SystemExit(
        f"[hub-agent] ERROR: HUB_MESH_MODE inválido: '{HUB_MESH_MODE}'. "
        "Valores válidos: off | mesh | hub-mesh"
    )

# HUB_MESH_RELAY: en hub-mesh el HUB mantiene NAT/MASQUERADE para tráfico relay de peers
HUB_MESH_RELAY    = os.getenv("HUB_MESH_RELAY", "1") == "1"

# SEC-01: Token requerido; no puede ser vacío ni inseguro
HUB_AGENT_TOKEN   = os.getenv("HUB_AGENT_TOKEN", "")

# Valores inseguros que se rechazan al arrancar
INSECURE_TOKENS   = {"changeme", "changeme-super-secret", "secret", "password", "12345", ""}


def log(msg: str) -> None:
    print(f"[hub-agent] {msg}", flush=True)


def run(cmd: list, check: bool = True, capture: bool = False) -> str | subprocess.CompletedProcess:
    log("RUN: " + " ".join(cmd))
    if capture:
        result = subprocess.check_output(cmd, text=True)  # nosec B603
        return result
    return subprocess.run(cmd, check=check)  # nosec B603


# =========================
# OPS-02: Verificación de dependencias
# =========================
def check_dependencies() -> None:
    required = [
        (WG_BIN,       "wireguard-tools (wg)"),
        (WG_QUICK,     "wireguard-tools (wg-quick)"),
        (IPTABLES_BIN, "iptables"),
        (SYSCTL_BIN,   "sysctl (procps)"),
    ]
    missing = []
    for path, name in required:
        if not shutil.which(path) and not os.path.isfile(path):
            missing.append(f"{name} ({path})")
    if missing:
        raise SystemExit(
            f"[hub-agent] ERROR: Dependencias faltantes: {', '.join(missing)}.\n"
            "Instala los paquetes requeridos (wireguard-tools, iptables, procps) y reintenta."
        )
    log("Verificación de dependencias: OK")


# =========================
# SEC-01: Validación de token al arranque
# =========================
def validate_token_at_startup() -> None:
    if not HUB_AGENT_TOKEN or HUB_AGENT_TOKEN.lower() in INSECURE_TOKENS:
        raise SystemExit(
            f"[hub-agent] ERROR CRÍTICO: HUB_AGENT_TOKEN está vacío o tiene un valor inseguro "
            f"('{HUB_AGENT_TOKEN}'). \n"
            "Genera un token seguro con: openssl rand -hex 32\n"
            "El hub-agent no puede arrancar con configuración insegura."
        )
    log("Validación de token de arranque: OK")


# =========================
# BOOTSTRAP WIREGUARD HUB
# =========================
def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def file_exists(path: str) -> bool:
    try:
        return os.path.exists(path) and os.path.getsize(path) > 0
    except Exception:
        return False


def read_file(path: str) -> str:
    with open(path, "r") as f:
        return f.read().strip()


def write_file(path: str, content: str, mode: int = 0o600) -> None:
    with open(path, "w") as f:
        f.write(content.rstrip("\n") + "\n")
    os.chmod(path, mode)


def iface_exists() -> bool:
    try:
        out = run([WG_BIN, "show", HUB_WG_IFACE], capture=True)
        assert isinstance(out, str)
        return f"interface: {HUB_WG_IFACE}" in out
    except Exception:
        return False


def ensure_keys() -> None:
    ensure_dir(WG_DIR)
    if file_exists(HUB_PRIVKEY_PATH) and file_exists(HUB_PUBKEY_PATH):
        return
    log("Generando llaves del HUB (no existen todavía)")
    priv_raw = run([WG_BIN, "genkey"], capture=True)
    assert isinstance(priv_raw, str)
    priv = priv_raw.strip()
    pub  = subprocess.check_output([WG_BIN, "pubkey"], input=priv + "\n", text=True).strip()  # nosec B603
    write_file(HUB_PRIVKEY_PATH, priv, 0o600)
    write_file(HUB_PUBKEY_PATH,  pub,  0o644)


def ensure_conf() -> None:
    ensure_keys()
    if file_exists(HUB_CONF_PATH):
        return
    log(f"Creando configuración {HUB_CONF_PATH}")
    priv = read_file(HUB_PRIVKEY_PATH)
    conf = f"[Interface]\nAddress = {HUB_TUNNEL_IP}\nListenPort = {HUB_LISTEN_PORT}\nPrivateKey = {priv}\n"
    write_file(HUB_CONF_PATH, conf, 0o600)


def ensure_wg_up() -> None:
    ensure_conf()
    if iface_exists():
        log(f"Interfaz {HUB_WG_IFACE} ya está arriba")
        return
    log(f"Levantando interfaz {HUB_WG_IFACE} con wg-quick")
    run([WG_QUICK, "down", HUB_WG_IFACE], check=False)
    run([WG_QUICK, "up", HUB_WG_IFACE], check=True)
    if not iface_exists():
        raise RuntimeError(f"No se pudo levantar {HUB_WG_IFACE}")


# =========================
# IPTABLES / SYSCTL
# =========================
def ensure_ip_forward():
    run([SYSCTL_BIN, "-w", "net.ipv4.ip_forward=1"], check=True)


def _iptables_exists(args: list) -> bool:
    return subprocess.run([IPTABLES_BIN] + args, check=False,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0  # nosec B603


def ensure_forward_rule() -> None:
    fwd_args = ["-i", HUB_WG_IFACE, "-o", HUB_WG_IFACE, "-j", "ACCEPT"]
    if not _iptables_exists(["-C", "FORWARD"] + fwd_args):
        log("Añadiendo regla FORWARD wg-iface↔wg-iface")
        run([IPTABLES_BIN, "-I", "FORWARD", "1"] + fwd_args, check=True)
    else:
        log("Regla FORWARD wg-iface↔wg-iface ya existe")


def ensure_nat_rules() -> None:
    if not HUB_ENABLE_NAT:
        log("NAT desactivado (HUB_ENABLE_NAT != 1)")
        return
    log(f"Configurando NAT {TUNNEL_CIDR} → {HUB_NAT_OUT_IFACE}")
    rules = [
        (["-C", "FORWARD", "-i", HUB_WG_IFACE, "-o", HUB_NAT_OUT_IFACE, "-j", "ACCEPT"],
         ["-A", "FORWARD", "-i", HUB_WG_IFACE, "-o", HUB_NAT_OUT_IFACE, "-j", "ACCEPT"]),
        (["-C", "FORWARD", "-i", HUB_NAT_OUT_IFACE, "-o", HUB_WG_IFACE,
          "-m", "state", "--state", "RELATED,ESTABLISHED", "-j", "ACCEPT"],
         ["-A", "FORWARD", "-i", HUB_NAT_OUT_IFACE, "-o", HUB_WG_IFACE,
          "-m", "state", "--state", "RELATED,ESTABLISHED", "-j", "ACCEPT"]),
        (["-t", "nat", "-C", "POSTROUTING", "-s", TUNNEL_CIDR, "-o", HUB_NAT_OUT_IFACE, "-j", "MASQUERADE"],
         ["-t", "nat", "-A", "POSTROUTING", "-s", TUNNEL_CIDR, "-o", HUB_NAT_OUT_IFACE, "-j", "MASQUERADE"]),
    ]
    for check_args, insert_args in rules:
        if not _iptables_exists(check_args):
            run([IPTABLES_BIN] + insert_args, check=True)


# OPS-01: Limpieza de reglas iptables al detener el servicio
def cleanup_iptables_rules():
    """Elimina las reglas añadidas por hub-agent. Llamar en ExecStop/PreStop del servicio systemd."""
    log("Limpiando reglas iptables del hub-agent...")
    rules_to_delete = [
        ["-D", "FORWARD", "-i", HUB_WG_IFACE, "-o", HUB_WG_IFACE, "-j", "ACCEPT"],
        ["-D", "FORWARD", "-i", HUB_WG_IFACE, "-o", HUB_NAT_OUT_IFACE, "-j", "ACCEPT"],
        ["-D", "FORWARD", "-i", HUB_NAT_OUT_IFACE, "-o", HUB_WG_IFACE,
         "-m", "state", "--state", "RELATED,ESTABLISHED", "-j", "ACCEPT"],
        ["-t", "nat", "-D", "POSTROUTING", "-s", TUNNEL_CIDR, "-o", HUB_NAT_OUT_IFACE, "-j", "MASQUERADE"],
    ]
    for args in rules_to_delete:
        try:
            subprocess.run([IPTABLES_BIN] + args, check=False,  # nosec B603
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            log(f"WARNING: cleanup regla {args}: {e}")
    log("Limpieza de iptables completada.")


def ensure_base_rules_internal() -> None:
    ensure_wg_up()
    ensure_ip_forward()
    ensure_forward_rule()
    ensure_nat_rules()
    # HM-F5c: log explícito cuando el relay hub-mesh está activo
    if HUB_MESH_MODE == "hub-mesh":
        log("[HUB-MESH] Relay activo: regla FORWARD wg↔wg configurada.")
        log(f"[HUB-MESH] Peers detrás de NAT serán alcanzables vía relay ({TUNNEL_CIDR})")


# =========================
# AUTH
# =========================
def check_token(token: str) -> None:
    if not secrets.compare_digest(token, HUB_AGENT_TOKEN):
        raise PermissionError("invalid token")


# =========================
# XML-RPC ENDPOINTS
# =========================
def hub_health(token: str) -> str:
    check_token(token)
    return "ok"


def hub_apply_peer(token: str, public_key: str, allowed_ips: str, endpoint: str = "") -> bool:
    check_token(token)
    if not public_key or len(public_key) != 44:
        raise ValueError("invalid public_key")
    if not allowed_ips or not allowed_ips.strip():
        raise ValueError("invalid allowed_ips")
    ensure_wg_up()

    if HUB_MESH_MODE == "mesh":
        parts = [ip.strip() for ip in allowed_ips.split(",") if ip.strip()]
        mesh_parts = [ip for ip in parts if ip.endswith("/32")]
        if not mesh_parts:
            mesh_parts = parts
        allowed_ips = ",".join(mesh_parts)
        log(f"[MESH] peer {public_key[:16]}... → {allowed_ips}")

    elif HUB_MESH_MODE == "hub-mesh":
        log(f"[HUB-MESH] peer {public_key[:16]}... → {allowed_ips} (relay activo)")

    else:
        log(f"Aplicando peer en {HUB_WG_IFACE}: {public_key[:16]}... → {allowed_ips}")

    cmd = [WG_BIN, "set", HUB_WG_IFACE, "peer", public_key, "allowed-ips", allowed_ips]
    if endpoint:
        cmd.extend(["endpoint", endpoint])
        log(f"  endpoint → {endpoint}")
    run(cmd, check=True)
    return True


def hub_remove_peer(token: str, public_key: str) -> bool:
    check_token(token)
    if not public_key or len(public_key) != 44:
        raise ValueError("invalid public_key")
    ensure_wg_up()
    log(f"Eliminando peer de {HUB_WG_IFACE}: {public_key[:16]}...")
    run([WG_BIN, "set", HUB_WG_IFACE, "peer", public_key, "remove"], check=True)
    return True


def hub_ensure_base_rules(token: str) -> bool:
    check_token(token)
    ensure_base_rules_internal()
    return True


def hub_show(token: str) -> str:
    check_token(token)
    ensure_wg_up()
    result = run([WG_BIN, "show", HUB_WG_IFACE], capture=True)
    assert isinstance(result, str)
    return result


def hub_public_key(token: str) -> str:
    check_token(token)
    try:
        return subprocess.check_output([WG_BIN, "show", HUB_WG_IFACE, "public-key"], text=True).strip()  # nosec B603
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"wg show public-key failed: {e}") from e


# OPS-01: endpoint para llamar desde systemd ExecStop
def hub_cleanup(token: str) -> bool:
    check_token(token)
    cleanup_iptables_rules()
    return True


# F4: nuevo endpoint — lista peers con sesión WireGuard activa (útil para descubrimiento mesh)
def hub_list_mesh_peers(token: str, network_cidr: str = "") -> list:
    """
    RPC: hub.list_mesh_peers(token, network_cidr)
    Parsea 'wg show <iface> dump' y devuelve peers con handshake reciente.
    Permite que peers descubran la IP real de otros peers detrás de NAT con endpoint dinámico.
    """
    check_token(token)
    ensure_wg_up()
    try:
        # wg show dump: public_key preshared_key endpoint allowed_ips latest_handshake tx rx persistent_keepalive
        out = subprocess.check_output(  # nosec B603
            [WG_BIN, "show", HUB_WG_IFACE, "dump"], text=True
        ).strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"wg show dump failed: {e}") from e

    peers = []
    now_ts = int(time.time())
    for line in out.splitlines()[1:]:  # saltar línea de la interfaz
        parts = line.split("\t")
        if len(parts) < 8:
            continue
        pub_key, _, endpoint, allowed_ips_raw, latest_handshake_str, _, _, _ = parts[:8]
        try:
            latest_handshake = int(latest_handshake_str)
        except ValueError:
            latest_handshake = 0
        # Considerar activo si handshake en los últimos 3 min
        alive = latest_handshake > 0 and (now_ts - latest_handshake) <= 180

        # Filtrar por CIDR si se proporcionó
        if network_cidr:
            try:
                net = ipaddress.IPv4Network(network_cidr, strict=False)
                ips_in_net = [
                    a.split("/")[0] for a in allowed_ips_raw.split(",")
                    if ipaddress.IPv4Address(a.split("/")[0]) in net
                ]
                if not ips_in_net:
                    continue
            except ValueError:
                continue

        peers.append({
            "public_key":       pub_key,
            "endpoint":         endpoint if endpoint != "(none)" else None,
            "allowed_ips":      allowed_ips_raw,
            "latest_handshake": latest_handshake,
            "alive":            alive,
        })
    return peers


# =========================
# SERVIDOR
# =========================
class Handler(SimpleXMLRPCRequestHandler):
    rpc_paths = ("/RPC2",)


def main():
    check_dependencies()           # OPS-02
    validate_token_at_startup()    # SEC-01

    log(f"Arrancando hub-agent en {HUB_AGENT_BIND}:{HUB_AGENT_PORT}")
    log(f"Interfaz WG: {HUB_WG_IFACE} | Conf: {HUB_CONF_PATH}")
    log(f"NAT: {'activado' if HUB_ENABLE_NAT else 'desactivado'} → {HUB_NAT_OUT_IFACE}")
    log(f"Modo mesh: {HUB_MESH_MODE!r}")  # HM-F5a: muestra el enum ('off'|'mesh'|'hub-mesh')
    if HUB_AGENT_TLS:
        log(f"TLS habilitado: cert={HUB_AGENT_CERT} key={HUB_AGENT_KEY}")  # HA-02
    else:
        log("TLS desactivado (HUB_AGENT_TLS=0). Asegúrate de que solo sea accesible localmente.")

    ensure_base_rules_internal()

    server = SimpleXMLRPCServer(
        (HUB_AGENT_BIND, HUB_AGENT_PORT),
        requestHandler=Handler,
        allow_none=True,
        logRequests=False,
    )

    # HA-02: envolver con TLS si está habilitado
    if HUB_AGENT_TLS:
        if not os.path.isfile(HUB_AGENT_CERT) or not os.path.isfile(HUB_AGENT_KEY):
            raise SystemExit(
                f"[hub-agent] ERROR: TLS habilitado pero faltan certificados.\n"
                f"  Cert: {HUB_AGENT_CERT}\n  Key:  {HUB_AGENT_KEY}\n"
                "Genera con: openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes"
            )
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(HUB_AGENT_CERT, HUB_AGENT_KEY)
        ctx.options |= ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
        server.socket = ctx.wrap_socket(server.socket, server_side=True)

    server.register_function(hub_health,             "hub.health")
    server.register_function(hub_public_key,         "hub.public_key")
    server.register_function(hub_apply_peer,         "hub.apply_peer")
    server.register_function(hub_remove_peer,        "hub.remove_peer")
    server.register_function(hub_ensure_base_rules,  "hub.ensure_base_rules")
    server.register_function(hub_show,               "hub.show")
    server.register_function(hub_cleanup,            "hub.cleanup")      # OPS-01
    server.register_function(hub_list_mesh_peers,    "hub.list_mesh_peers")  # F4: mesh

    log("hub-agent listo")
    server.serve_forever()


if __name__ == "__main__":
    main()
