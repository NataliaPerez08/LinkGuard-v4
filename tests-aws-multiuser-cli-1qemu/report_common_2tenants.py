#!/usr/bin/env python3
"""Modulo comun para tests AWS Multiusuario CLI de LinkGuard v4 — VARIANTE DOS TENANTS.

Diferencia respecto a report_common.py:
  - Dos tenants: tenant-a (3 peers cloud AWS) y tenant-b (VM40 + RPi5 + QEMU)
  - Cada peer registra su ORCH_TOKEN y USER_ID del tenant correspondiente
  - Verifica conectividad cross-tenant en la misma red
  - El reporte HTML muestra a que tenant pertenece cada peer

Combina:
  - Infraestructura AWS (3 EC2 + 1 VM + 1 RPi5 + 1 QEMU)
  - Autenticacion multiusuario (admin + tenant-a + tenant-b) via orch-cli
  - Generacion de reportes HTML con matrices de conectividad cross-tenant
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SSH_KEY = os.environ.get("LINKGUARD_SSH_KEY", str(ROOT / "linkguard-key.pem"))

ORCH_HOST = os.environ.get("AWS_ORCH_HOST", "34.193.139.170")
ORCH_USER = os.environ.get("AWS_ORCH_USER", "admin")
REAL_ORCH_URL = os.environ.get("AWS_ORCH_URL", f"http://{ORCH_HOST}:8000/RPC2")
HUB_WG_IFACE = "wg-HUB"
SUDO_PASS = os.environ.get("LINKGUARD_SUDO_PASS", "")

TERMINAL_PASS = os.environ.get("LINKGUARD_TERMINAL_PASS", "atidesa15")
TERMINAL_JUMP = os.environ.get("LINKGUARD_TERMINAL_JUMP", "root@100.115.215.49")
JUMP_PASS = os.environ.get("LINKGUARD_JUMP_PASS", "atidesa15")
QEMU_PASS = os.environ.get("LINKGUARD_QEMU_PASS", "linkguard-test")

SSH_OPTS = ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null", "-o", "ConnectTimeout=15"]

# ── Peers reales + QEMU ──────────────────────────────────────────
REAL_PEERS = [
    {"peer_id": "peer-100-31-255-119", "host": "54.210.49.136", "user": "ubuntu", "label": "119 aws (54.210.49.136)", "tenant": "tenant-a"},
    {"peer_id": "peer-34-207-174-76", "host": "3.228.113.66", "user": "ec2-user", "label": "76 aws (3.228.113.66)", "tenant": "tenant-a"},
    {"peer_id": "peer-184-72-71-143", "host": "98.87.229.24", "user": "ec2-user", "label": "143 aws (98.87.229.24)", "tenant": "tenant-a"},
    {"peer_id": "peer-172-20-0-40", "host": "172.20.0.40", "user": "root", "pass": os.environ.get("LINKGUARD_VM40_PASS", "alpine123"), "service_mgr": "openrc", "label": "40 vm (172.20.0.40)", "is_terminal": True, "tenant": "tenant-b"},
    {"peer_id": "peer-172-20-0-7", "host": "172.20.0.7", "user": "natalia", "pass": os.environ.get("LINKGUARD_VM7_PASS", "atidesa15"), "service_mgr": "systemd", "label": "7 rpi5 (172.20.0.7)", "is_terminal": True, "is_rpi": True, "tenant": "tenant-b"},
]

QEMU_PEERS = [
    {"peer_id": "peer01", "role": "orq", "host": "192.168.100.10", "label": "peer01 (QEMU)", "service_mgr": "openrc", "tenant": "tenant-b"},
]

ALL_PEER_IDS = [p["peer_id"] for p in REAL_PEERS] + [p["peer_id"] for p in QEMU_PEERS]
ALL_PEER_LABELS = {p["peer_id"]: p["label"] for p in REAL_PEERS}
ALL_PEER_LABELS.update({p["peer_id"]: p["label"] for p in QEMU_PEERS})

# ── Mapa peer_id -> tenant ───────────────────────────────────────
PEER_TENANT_MAP: dict[str, str] = {}
for p in REAL_PEERS:
    PEER_TENANT_MAP[p["peer_id"]] = p["tenant"]
for p in QEMU_PEERS:
    PEER_TENANT_MAP[p["peer_id"]] = p["tenant"]

TENANTS = ["tenant-a", "tenant-b"]

_TOPOLOGY_DEFAULT = "hub-spoke"


@dataclass
class PingResult:
    ok: bool
    avg_ms: float | None
    loss_pct: float
    ttl: int | None
    raw: str


@dataclass
class ThroughputResult:
    peer_id: str
    mbps: float
    size_bytes: int
    time_sec: float
    ok: bool


def run(cmd: list[str], *, timeout: int = 120, check: bool = False, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, check=False, env=env)
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(cmd)}\n{result.stdout}\n{result.stderr}")
    return result


def _peer_user(host: str) -> str:
    for p in REAL_PEERS:
        if p["host"] == host:
            return p.get("user", "root")
    return "root"


def ssh_key_run(user: str, host: str, *remote_cmd: str, timeout: int = 120, check: bool = False) -> subprocess.CompletedProcess[str]:
    last = None
    for _ in range(3):
        last = run(["ssh", "-i", SSH_KEY, *SSH_OPTS, f"{user}@{host}", *remote_cmd], timeout=timeout, check=False)
        if last.returncode == 0:
            return last
        time.sleep(2)
    if check:
        raise RuntimeError(f"SSH failed on {host}\n{last.stdout if last else ''}\n{last.stderr if last else ''}")
    assert last is not None
    return last


def ssh_key_script(user: str, host: str, script: str, *, timeout: int = 120, check: bool = False) -> subprocess.CompletedProcess[str]:
    last = None
    for _ in range(3):
        last = subprocess.run(
            ["ssh", "-i", SSH_KEY, *SSH_OPTS, f"{user}@{host}", "sh"],
            input=script, text=True, capture_output=True, timeout=timeout, check=False,
        )
        if last.returncode == 0:
            return last
        time.sleep(2)
    if check:
        raise RuntimeError(f"Remote script failed on {host}\n{last.stdout if last else ''}\n{last.stderr if last else ''}")
    assert last is not None
    return last


def ssh_sudo_script(user: str, host: str, script: str, *, timeout: int = 120, check: bool = False) -> subprocess.CompletedProcess[str]:
    if SUDO_PASS:
        remote_cmd = "sudo -S -p '' sh"
        stdin_input = SUDO_PASS + "\n" + script
    else:
        remote_cmd = "sudo -n sh"
        stdin_input = script
    last = None
    for _ in range(3):
        last = subprocess.run(
            ["ssh", "-i", SSH_KEY, *SSH_OPTS, f"{user}@{host}", remote_cmd],
            input=stdin_input, text=True, capture_output=True, timeout=timeout, check=False,
        )
        if last.returncode == 0:
            return last
        time.sleep(2)
    if check:
        raise RuntimeError(f"Sudo script failed on {host}\n{last.stdout if last else ''}\n{last.stderr if last else ''}")
    assert last is not None
    return last


def ssh_cloud_run(host: str, *remote_cmd: str, timeout: int = 120, check: bool = False) -> subprocess.CompletedProcess[str]:
    return ssh_key_run(_peer_user(host), host, *remote_cmd, timeout=timeout, check=check)


def ssh_cloud_script(host: str, script: str, *, timeout: int = 120, check: bool = False) -> subprocess.CompletedProcess[str]:
    return ssh_key_script(_peer_user(host), host, script, timeout=timeout, check=check)


def ssh_cloud_sudo_script(host: str, script: str, *, timeout: int = 120, check: bool = False) -> subprocess.CompletedProcess[str]:
    return ssh_sudo_script(_peer_user(host), host, script, timeout=timeout, check=check)


def ssh_orch_run(*remote_cmd: str, timeout: int = 120, check: bool = False) -> subprocess.CompletedProcess[str]:
    return ssh_key_run(ORCH_USER, ORCH_HOST, *remote_cmd, timeout=timeout, check=check)


def ssh_orch_sudo_script(script: str, *, timeout: int = 120, check: bool = False) -> subprocess.CompletedProcess[str]:
    return ssh_sudo_script(ORCH_USER, ORCH_HOST, script, timeout=timeout, check=check)


def _terminal_pass(host: str) -> str:
    for p in REAL_PEERS:
        if p.get("is_terminal") and p["host"] == host:
            return p.get("pass", TERMINAL_PASS)
    return TERMINAL_PASS


def _terminal_user(host: str) -> str:
    for p in REAL_PEERS:
        if p.get("is_terminal") and p["host"] == host:
            return p.get("user", "root")
    return "root"


def _terminal_service_mgr(host: str) -> str:
    for p in REAL_PEERS:
        if p.get("is_terminal") and p["host"] == host:
            return p.get("service_mgr", "openrc")
    return "openrc"


def _terminal_ssh_cmd(host: str, remote_user: str = "") -> list[str]:
    target_pass = _terminal_pass(host)
    ruser = remote_user or _terminal_user(host)
    proxy = (
        f"sshpass -p {shlex.quote(JUMP_PASS)} ssh -o StrictHostKeyChecking=no "
        f"-o UserKnownHostsFile=/dev/null -o ConnectTimeout=15 -W %h:%p {TERMINAL_JUMP}"
    )
    return ["sshpass", "-p", target_pass, "ssh", *SSH_OPTS, "-o", f"ProxyCommand={proxy}", f"{ruser}@{host}"]


def ssh_terminal_run(host: str, *remote_cmd: str, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return run([*_terminal_ssh_cmd(host), *remote_cmd], timeout=timeout, check=False)


def ssh_terminal_script(host: str, script: str, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    last = None
    for _ in range(3):
        try:
            last = subprocess.run(
                [*_terminal_ssh_cmd(host), "sh"],
                input=script + "\nexit 0\n", text=True, capture_output=True, timeout=timeout, check=False,
            )
            if last.returncode == 0:
                return last
        except subprocess.TimeoutExpired:
            last = subprocess.CompletedProcess(args=[], returncode=-1, stdout="", stderr="timeout")
            continue
        time.sleep(3)
    assert last is not None
    return last


def ssh_terminal_sudo_script(host: str, script: str, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    if _terminal_user(host) == "root":
        return ssh_terminal_script(host, script, timeout=timeout)
    target_pass = _terminal_pass(host)
    last = None
    for _ in range(3):
        try:
            last = subprocess.run(
                [*_terminal_ssh_cmd(host), "sudo -S -p '' sh"],
                input=target_pass + "\n" + script + "\nexit 0\n", text=True, capture_output=True, timeout=timeout, check=False,
            )
            return last
        except subprocess.TimeoutExpired:
            last = subprocess.CompletedProcess(args=[], returncode=-1, stdout="", stderr="timeout")
            continue
        time.sleep(3)
    assert last is not None
    return last


def ssh_qemu_run(host: str, *remote_cmd: str, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return run(["sshpass", "-p", QEMU_PASS, "ssh", *SSH_OPTS, f"root@{host}", *remote_cmd], timeout=timeout, check=False)


def ssh_qemu_script(host: str, script: str, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["sshpass", "-p", QEMU_PASS, "ssh", *SSH_OPTS, f"root@{host}", "sh"],
        input=script, text=True, capture_output=True, timeout=timeout, check=False,
    )


# ── orch-cli wrapper ─────────────────────────────────────────────
ORCH_CLI = str(ROOT / "orchestrator-install-v2" / "orch-cli.py")

_admin_token = ""
# JWTs y tokens por tenant
_tenant_jwts: dict[str, str] = {}
_tenant_tokens: dict[str, str] = {}


def _parse_first_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if not text:
        return {}
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start >= 0:
                block = text[start:i+1]
                try:
                    return json.loads(block)
                except json.JSONDecodeError:
                    return {}
    return {}


def orch_cli(*args: str, admin_token: str = "", token: str = "", timeout: int = 120) -> dict[str, Any]:
    cmd = [sys.executable, ORCH_CLI, "--url", REAL_ORCH_URL]
    if admin_token:
        cmd += ["--admin-token", admin_token]
    elif token:
        cmd += ["--token", token]
    cmd += list(args)
    try:
        result = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return {"_error": f"timeout after {timeout}s", "_fault": True}
    if result.returncode != 0:
        return {"_error": (result.stderr or result.stdout or "").strip(), "_fault": True, "_raw": result.stdout or ""}
    return _parse_first_json(result.stdout or "")


def orch_cli_admin(*args: str) -> dict[str, Any]:
    return orch_cli(*args, admin_token=_admin_token)


def orch_cli_tenant(*args: str, tenant: str = "tenant-a") -> dict[str, Any]:
    jwt = _tenant_jwts.get(tenant, "")
    return orch_cli(*args, token=jwt)


def get_admin_token() -> str:
    candidates: list[subprocess.CompletedProcess[str]] = []
    if SUDO_PASS:
        candidates.append(ssh_orch_sudo_script("cat /etc/linkguard/secrets", timeout=60, check=False))
    else:
        candidates.append(ssh_orch_run("sudo", "-n", "cat", "/etc/linkguard/secrets", timeout=60, check=False))
        candidates.append(ssh_orch_run("cat", "/etc/linkguard/secrets", timeout=60, check=False))
    for r in candidates:
        if r.returncode == 0:
            for line in (r.stdout or "").splitlines():
                if line.startswith("ADMIN_TOKEN="):
                    return line.split("=", 1)[1].strip()
    raise RuntimeError(
        "No se pudo leer ADMIN_TOKEN de /etc/linkguard/secrets en el orquestador. "
        "Define LINKGUARD_SUDO_PASS si admin requiere password de sudo."
    )


def log(msg: str) -> None:
    print(f"[reporte-2tenants] {msg}", flush=True)


# ── Gestion de dos tenants ───────────────────────────────────────

def _tenant_token_for_peer(peer_id: str) -> str:
    tenant = PEER_TENANT_MAP.get(peer_id, "tenant-a")
    return _tenant_tokens.get(tenant, "")


def _tenant_jwt_for_peer(peer_id: str) -> str:
    tenant = PEER_TENANT_MAP.get(peer_id, "tenant-a")
    return _tenant_jwts.get(tenant, "")


def _tenant_for_peer(peer_id: str) -> str:
    return PEER_TENANT_MAP.get(peer_id, "tenant-a")


def ensure_tenant_user(tenant: str) -> str:
    """Crea (si no existe) un usuario tenant y obtiene su token + JWT."""
    global _tenant_tokens, _tenant_jwts
    r = orch_cli("user-create", tenant, admin_token=_admin_token)
    if "user_id" in r:
        log(f"Usuario {tenant} creado")
    elif "already exists" in str(r.get("_raw", "")):
        log(f"Usuario {tenant} ya existe")
    else:
        log(f"  WARN creando {tenant}: {r}")

    r = orch_cli("issue-user-token", tenant, admin_token=_admin_token)
    token = r.get("token", "")
    if not token:
        raise RuntimeError(f"No se pudo obtener token para {tenant}: {r}")
    _tenant_tokens[tenant] = token
    log(f"Token de {tenant}: {token[:16]}...")

    r = orch_cli("auth-login", tenant, token)
    jwt = r.get("jwt", "")
    if not jwt:
        raise RuntimeError(f"No se pudo obtener JWT para {tenant}: {r}")
    _tenant_jwts[tenant] = jwt
    log(f"JWT de {tenant}: {jwt[:20]}...")
    return jwt


def ensure_tenant_users() -> dict[str, str]:
    """Crea ambos tenants y devuelve el map {tenant: jwt}."""
    jwts = {}
    for tenant in TENANTS:
        log(f"\n--- Configurando tenant '{tenant}' ---")
        jwts[tenant] = ensure_tenant_user(tenant)
    return jwts


def peer_list() -> dict[str, Any]:
    return orch_cli_admin("peer-list").get("peers", {})


def get_current_topology() -> str:
    data = orch_cli_admin("net-topology", "default")
    return str(data.get("topology") or _TOPOLOGY_DEFAULT)


def set_topology(topology: str) -> None:
    orch_cli_admin("net-set-topology", "default", topology)


def peer_unregister(peer_id: str) -> bool:
    tenant = _tenant_for_peer(peer_id)
    jwt = _tenant_jwt_for_peer(peer_id)
    if jwt:
        try:
            r = orch_cli("peer-unregister", peer_id, token=jwt)
            if not r.get("_fault"):
                return True
            log(f"  WARN: No pude eliminar {peer_id} via {tenant} JWT, intentando admin...")
        except Exception:
            log(f"  WARN: No pude eliminar {peer_id} via {tenant} JWT, intentando admin...")
    try:
        r = orch_cli_admin("peer-unregister", peer_id)
        if not r.get("_fault"):
            return True
        log(f"  WARN: admin fallback tambien fallo: {r}")
        return False
    except Exception as exc2:
        log(f"  WARN: admin fallback tambien fallo: {exc2}")
        return False


def clean_cloud_peer(host: str) -> None:
    script = """set -e
systemctl stop wg-auto-register 2>/dev/null || true
rm -f /etc/wireguard/wg0.conf /etc/wireguard/wg0.key /etc/wireguard/wg0.pub /etc/linkguard/wg-auto.json /etc/wireguard/wg-auto.json
ip link delete wg0 2>/dev/null || true
"""
    ssh_cloud_sudo_script(host, script, timeout=60, check=False)


def clean_terminal_peer(host: str) -> None:
    if _terminal_service_mgr(host) == "systemd":
        stop_cmd = "systemctl stop wg-auto-register 2>/dev/null || true"
    else:
        stop_cmd = "rc-service wg-auto-register stop 2>/dev/null || true"
    script = f"""{stop_cmd}
killall -9 wg-auto-register.py 2>/dev/null || true
rm -f /etc/wireguard/wg0.conf /etc/wireguard/wg0.key /etc/wireguard/wg0.pub /etc/linkguard/wg-auto.json /etc/wireguard/wg-auto.json
ip link delete wg0 2>/dev/null || true
exit 0
"""
    ssh_terminal_sudo_script(host, script, timeout=90)


def clean_qemu_peer(host: str) -> None:
    script = """set -e
rc-service wg-auto-register stop 2>/dev/null || true
killall -9 wg-auto-register.py 2>/dev/null || true
rm -f /etc/wireguard/wg0.conf /etc/wireguard/wg0.key /etc/wireguard/wg0.pub /etc/linkguard/wg-auto.json
rm -f /etc/wireguard/wg-auto.json
ip link delete wg0 2>/dev/null || true
"""
    ssh_qemu_script(host, script, timeout=60)


def clean_orchestrator_peers() -> None:
    peers = peer_list()
    for pid in list(peers.keys()):
        peer_unregister(pid)
        log(f"  Eliminado {pid} del orquestador (tenant: {_tenant_for_peer(pid)})")
    time.sleep(2)


def hub_flush_peers() -> None:
    script = """set -e
WG_IFACE="wg-HUB"
wg show "$WG_IFACE" peers 2>/dev/null | while read -r pk; do
    [ -n "$pk" ] && wg set "$WG_IFACE" peer "$pk" remove
done
"""
    ssh_orch_sudo_script(script, timeout=60, check=False)
    log("  Peers eliminados del hub WG")


def clean_all_peers() -> None:
    log("Limpiando peers reales...")
    for p in REAL_PEERS:
        if p.get("is_terminal"):
            clean_terminal_peer(p["host"])
        else:
            clean_cloud_peer(p["host"])
        log(f"  {p['host']} limpiado (tenant: {p['tenant']})")
    log("Limpiando peers QEMU...")
    for p in QEMU_PEERS:
        clean_qemu_peer(p["host"])
        log(f"  {p['role']} limpiado (tenant: {p['tenant']})")
    log("Limpiando orquestador...")
    clean_orchestrator_peers()
    log("Limpiando WG hub...")
    hub_flush_peers()


def start_cloud_peer(host: str) -> None:
    ssh_cloud_sudo_script(host, "systemctl restart wg-auto-register", timeout=180, check=False)


def start_terminal_peer(host: str) -> None:
    if _terminal_service_mgr(host) == "systemd":
        stop_cmd = "systemctl stop wg-auto-register 2>/dev/null || true"
        start_cmd = "systemctl start wg-auto-register"
    else:
        stop_cmd = "rc-service wg-auto-register stop 2>/dev/null || true"
        start_cmd = "rc-service wg-auto-register start"
    script = f"""{stop_cmd}
killall -9 wg-auto-register.py 2>/dev/null || true
{start_cmd}
exit 0
"""
    ssh_terminal_sudo_script(host, script, timeout=180)


def start_qemu_peer(host: str) -> None:
    ssh_qemu_script(host, """set -e
rc-service wg-auto-register stop 2>/dev/null || true
killall -9 wg-auto-register.py 2>/dev/null || true
rc-service wg-auto-register start
""", timeout=180)


def _update_peer_env_token(host: str) -> None:
    """Escribe ORCH_TOKEN y USER_ID del tenant correspondiente en peer.env."""
    for p in REAL_PEERS:
        if p["host"] != host:
            continue
        peer_id = p["peer_id"]
        tenant = p["tenant"]
        token = _tenant_tokens.get(tenant, "")
        if not token:
            log(f"  WARN: sin token para {tenant}, peer {peer_id} no actualizara peer.env")
            return
        script = (
            f"sed -i 's|^ORCH_TOKEN=.*|ORCH_TOKEN={token}|' /etc/linkguard/peer.env; "
            f"sed -i 's|^USER_ID=.*|USER_ID={tenant}|' /etc/linkguard/peer.env; "
            f"sed -i 's|^PEER_ID=.*|PEER_ID={peer_id}|' /etc/linkguard/peer.env; "
            f"grep -q '^PEER_ID=' /etc/linkguard/peer.env || echo 'PEER_ID={peer_id}' >> /etc/linkguard/peer.env; "
            f"grep -q '^USER_ID=' /etc/linkguard/peer.env || echo 'USER_ID={tenant}' >> /etc/linkguard/peer.env"
        )
        if p.get("is_terminal"):
            ssh_terminal_sudo_script(host, script, timeout=30)
        else:
            ssh_cloud_sudo_script(host, script, timeout=30, check=False)
        return
    for p in QEMU_PEERS:
        if p["host"] != host:
            continue
        peer_id = p["peer_id"]
        tenant = p["tenant"]
        token = _tenant_tokens.get(tenant, "")
        if not token:
            log(f"  WARN: sin token para {tenant}, peer {peer_id} no actualizara peer.env")
            return
        script = (
            f"sed -i 's|^ORCH_TOKEN=.*|ORCH_TOKEN={token}|' /etc/linkguard/peer.env; "
            f"sed -i 's|^USER_ID=.*|USER_ID={tenant}|' /etc/linkguard/peer.env; "
            f"sed -i 's|^PEER_ID=.*|PEER_ID={peer_id}|' /etc/linkguard/peer.env; "
            f"grep -q '^PEER_ID=' /etc/linkguard/peer.env || echo 'PEER_ID={peer_id}' >> /etc/linkguard/peer.env; "
            f"grep -q '^USER_ID=' /etc/linkguard/peer.env || echo 'USER_ID={tenant}' >> /etc/linkguard/peer.env"
        )
        ssh_qemu_script(host, script, timeout=30)
        return


def start_all_peers() -> None:
    log("Iniciando peers reales...")
    for p in REAL_PEERS:
        _update_peer_env_token(p["host"])
        if p.get("is_terminal"):
            start_terminal_peer(p["host"])
        else:
            start_cloud_peer(p["host"])
        log(f"  {p['host']} iniciado (tenant: {p['tenant']})")
    log("Iniciando peers QEMU...")
    for p in QEMU_PEERS:
        _update_peer_env_token(p["host"])
        start_qemu_peer(p["host"])
        log(f"  {p['role']} iniciado (tenant: {p['tenant']})")


def wait_for_all_peers(timeout: int = 180) -> dict[str, Any]:
    deadline = time.time() + timeout
    last: dict[str, Any] = {}
    while time.time() < deadline:
        last = peer_list()
        found = [pid for pid in ALL_PEER_IDS if pid in last]
        if len(found) == len(ALL_PEER_IDS):
            log(f"Todos los {len(ALL_PEER_IDS)} peers registrados")
            return last
        log(f"  Esperando peers: {len(found)}/{len(ALL_PEER_IDS)} presentes: {found}")
        time.sleep(5)
    missing = sorted(set(ALL_PEER_IDS) - set(last))
    raise RuntimeError(f"No aparecieron todos los peers tras {timeout}s. Faltan: {missing}. Visibles: {list(last.keys())}")


def wait_for_handshakes(timeout: int = 120) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = ssh_orch_sudo_script(f"wg show {HUB_WG_IFACE}", timeout=60, check=False)
        lines = (result.stdout or "").splitlines()
        peers_with_hs = 0
        total_peers = 0
        for line in lines:
            if line.startswith("peer:"):
                total_peers += 1
            if re.search(r"latest handshake:\s+\d+", line):
                peers_with_hs += 1
        if total_peers >= len(ALL_PEER_IDS) and peers_with_hs == total_peers:
            log(f"Handshakes establecidos: {peers_with_hs}/{total_peers}")
            return
        log(f"  Esperando handshakes: {peers_with_hs}/{total_peers} peers")
        time.sleep(5)
    raise RuntimeError(f"No se establecieron handshakes tras {timeout}s")


def parse_ping_output(output: str) -> PingResult:
    ok = bool(re.search(r"(?<![0-9])0% packet loss", output))
    loss_m = re.search(r"(\d+)\s*% packet loss", output)
    loss_pct = float(loss_m.group(1)) if loss_m else (0.0 if ok else 100.0)
    ttl_m = re.search(r"ttl[=](\d+)", output)
    ttl = int(ttl_m.group(1)) if ttl_m else None
    patterns = [
        r"rtt min/avg/max(?:/mdev)? = ([0-9.]+)/([0-9.]+)/([0-9.]+)/?[0-9.]*",
        r"round-trip min/avg/max(?:/[a-z]+)? = ([0-9.]+)/([0-9.]+)/([0-9.]+)",
    ]
    avg = None
    for pat in patterns:
        m = re.search(pat, output)
        if m:
            avg = float(m.group(2))
            break
    return PingResult(ok=ok, avg_ms=avg, loss_pct=loss_pct, ttl=ttl, raw=output)


def ping_cloud(host: str, target: str, count: int = 5) -> PingResult:
    try:
        result = ssh_cloud_run(host, "ping", "-n", "-c", str(count), "-W", "2", target, timeout=60, check=False)
        return parse_ping_output((result.stdout or "") + (result.stderr or ""))
    except subprocess.TimeoutExpired:
        return PingResult(ok=False, avg_ms=None, loss_pct=100.0, ttl=None, raw="ssh timeout")
    except Exception as exc:
        return PingResult(ok=False, avg_ms=None, loss_pct=100.0, ttl=None, raw=str(exc))


def ping_qemu(host: str, target: str, count: int = 5) -> PingResult:
    try:
        result = ssh_qemu_run(host, "ping", "-n", "-c", str(count), "-W", "2", target, timeout=60)
        return parse_ping_output((result.stdout or "") + (result.stderr or ""))
    except subprocess.TimeoutExpired:
        return PingResult(ok=False, avg_ms=None, loss_pct=100.0, ttl=None, raw="ssh timeout")
    except Exception as exc:
        return PingResult(ok=False, avg_ms=None, loss_pct=100.0, ttl=None, raw=str(exc))


def ping_terminal(host: str, target: str, count: int = 5) -> PingResult:
    try:
        result = ssh_terminal_run(host, "ping", "-n", "-c", str(count), "-W", "2", target, timeout=60)
        return parse_ping_output((result.stdout or "") + (result.stderr or ""))
    except subprocess.TimeoutExpired:
        return PingResult(ok=False, avg_ms=None, loss_pct=100.0, ttl=None, raw="ssh timeout")
    except Exception as exc:
        return PingResult(ok=False, avg_ms=None, loss_pct=100.0, ttl=None, raw=str(exc))


def _has_iperf3(host: str, is_local: bool = False) -> bool:
    if is_local:
        r = subprocess.run(["which", "iperf3"], text=True, capture_output=True, timeout=15, check=False)
    else:
        r = ssh_cloud_run(host, "which", "iperf3", timeout=15, check=False)
    return r.returncode == 0 and "iperf3" in (r.stdout or "")


def _parse_iperf3_out(out: str, peer_id: str, duration: int) -> ThroughputResult:
    best_mbps = 0.0
    for line in out.splitlines():
        m = re.search(r"(\d+\.?\d*)\s+Mbits/sec", line)
        if m and "sender" in line:
            best_mbps = max(best_mbps, float(m.group(1)))
    if best_mbps == 0.0:
        for line in out.splitlines():
            m = re.search(r"(\d+\.?\d*)\s+Mbits/sec", line)
            if m:
                best_mbps = max(best_mbps, float(m.group(1)))
    if best_mbps > 0:
        return ThroughputResult(peer_id=peer_id, mbps=best_mbps, size_bytes=0, time_sec=duration, ok=True)
    log(f"  iperf3 parse error for {peer_id}: {out[:200]}")
    return ThroughputResult(peer_id=peer_id, mbps=0.0, size_bytes=0, time_sec=0, ok=False)


def measure_cloud_iperf3(server_host: str, server_ip: str, clients: list[tuple[str, str]], duration: int = 10) -> list[ThroughputResult]:
    port = "5201"
    results: list[ThroughputResult] = []
    server_script = f"""set -e
killall -9 iperf3 2>/dev/null || true
nohup iperf3 -s -B {server_ip} -p {port} >/tmp/iperf3-server.log 2>&1 &
echo $!
"""
    r = ssh_cloud_sudo_script(server_host, server_script, timeout=60, check=False)
    server_pid = (r.stdout or "").strip()
    time.sleep(2)
    try:
        for peer_id, host in clients:
            if not _has_iperf3(host):
                results.append(ThroughputResult(peer_id=peer_id, mbps=0.0, size_bytes=0, time_sec=0, ok=False))
                continue
            client_script = f"""set -e
output=$(iperf3 -c {server_ip} -p {port} -t {duration} -f m 2>&1)
echo "$output"
"""
            r = ssh_cloud_script(host, client_script, timeout=60, check=False)
            results.append(_parse_iperf3_out(r.stdout or "", peer_id, duration))
    finally:
        if server_pid:
            ssh_cloud_sudo_script(server_host, f"kill {server_pid} 2>/dev/null || true; killall -9 iperf3 2>/dev/null || true", timeout=30, check=False)
    return results


def measure_cloud_http(server_host: str, server_ip: str, clients: list[tuple[str, str]], file_size_mb: int = 8) -> list[ThroughputResult]:
    port = "8082"
    remote_file = f"/tmp/wg-perf-{file_size_mb}m.bin"
    pid_file = "/tmp/wg-http.pid"
    setup = f"""set -e
kill $(cat {pid_file}) 2>/dev/null || true
rm -f {pid_file} {remote_file}
dd if=/dev/zero of={remote_file} bs=1M count={file_size_mb} status=none
nohup python3 -m http.server {port} --bind {server_ip} --directory /tmp >/tmp/wg-http.log 2>&1 &
echo $! > {pid_file}
"""
    ssh_cloud_sudo_script(server_host, setup, timeout=180, check=True)
    time.sleep(2)
    results: list[ThroughputResult] = []
    try:
        for peer_id, host in clients:
            curl_cmd = f"""
curl -m 60 -s -o /dev/null -w '%{{http_code}} %{{size_download}} %{{time_total}} %{{speed_download}}' http://{server_ip}:{port}/{os.path.basename(remote_file)}
"""
            r = ssh_cloud_script(host, curl_cmd, timeout=180, check=False)
            out = (r.stdout or "").strip()
            parts = out.split()
            if len(parts) >= 4 and parts[0].isdigit():
                http_code = int(parts[0])
                size = int(parts[1])
                t = float(parts[2])
                speed = int(parts[3])
                mbps = round((speed * 8) / 1_000_000, 2) if speed > 0 else 0.0
                results.append(ThroughputResult(peer_id=peer_id, mbps=mbps, size_bytes=size, time_sec=t, ok=http_code == 200))
            else:
                results.append(ThroughputResult(peer_id=peer_id, mbps=0.0, size_bytes=0, time_sec=0, ok=False))
    finally:
        cleanup = f"kill $(cat {pid_file}) 2>/dev/null || true\nrm -f {pid_file} {remote_file}\n"
        ssh_cloud_sudo_script(server_host, cleanup, timeout=120, check=False)
    return results


@dataclass
class TopologyResult:
    topology: str
    peers: dict[str, Any]
    ping_results: dict[str, dict[str, PingResult]]
    throughput_results: dict[str, list[ThroughputResult]]
    wg_configs: dict[str, str]
    nat_diagnostics: dict[str, dict[str, Any]] | None = None


def capture_nat_diagnostics(peers: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Diagnostica NAT por peer combinando estado del orchestrator + wg show local.

    Para cada peer en ALL_PEER_IDS devuelve:
      - nat_type:  valor reportado al orquestador (none/full-cone/symmetric/...)
      - endpoint:  endpoint registrado (IP publica NAT : puerto observable)
      - tunnel_ip: IP dentro del tunel WireGuard
      - handshake_hub_s: segundos desde el ultimo handshake con el hub
      - handshakes_local: dict {pubkey16: hace_cuantos_seg} segun wg show del peer
      - is_nat: True si el peer esta detras de tipo NAT (no full-cone/none)
      - shares_nat_with: lista de peer_ids que comparten la misma IP publica NAT
    """
    diag: dict[str, dict[str, Any]] = {}

    # 1. nat_type + endpoint desde el estado del orquestador
    for pid in ALL_PEER_IDS:
        pinfo = peers.get(pid, {})
        nat_type = pinfo.get("nat_type") or ""
        endpoint = pinfo.get("endpoint") or ""
        tunnel_ip = pinfo.get("ip") or ""
        diag[pid] = {
            "nat_type": nat_type,
            "endpoint": endpoint,
            "tunnel_ip": tunnel_ip,
            "is_nat": bool(nat_type and nat_type not in ("none", "full-cone", "")),
            "shares_nat_with": [],
            "handshake_hub_s": None,
            "handshakes_local": {},
        }

    # 2. peers que comparten la misma IP publica NAT (hairpin / NAT bilateral)
    endpoints_by_ip: dict[str, list[str]] = {}
    for pid in ALL_PEER_IDS:
        ep = diag[pid]["endpoint"]
        if not ep:
            continue
        ep_ip = ep.rsplit(":", 1)[0] if ":" in ep else ep
        endpoints_by_ip.setdefault(ep_ip, []).append(pid)
    for pids in endpoints_by_ip.values():
        if len(pids) > 1:
            for pid in pids:
                diag[pid]["shares_nat_with"] = [other for other in pids if other != pid]

    # 3. handshake hub -> peer: parsear 'wg show wg-HUB latest-handshakes'
    try:
        pubkey_to_pid = {p.get("public_key", ""): pid for pid, p in peers.items() if pid in ALL_PEER_IDS}
        r = ssh_orch_sudo_script(f"wg show {HUB_WG_IFACE} latest-handshakes", timeout=30, check=False)
        now = int(time.time())
        for line in (r.stdout or "").splitlines():
            parts = line.split()
            if len(parts) == 2:
                pub, hs_ts = parts[0], parts[1]
                try:
                    hs = int(hs_ts)
                except ValueError:
                    continue
                pid = pubkey_to_pid.get(pub)
                if pid and pid in diag:
                    diag[pid]["handshake_hub_s"] = (now - hs) if hs > 0 else None
    except Exception:
        pass

    # 4. handshakes locales por peer: wg show wg0 latest-handshakes en cada peer
    for pid in ALL_PEER_IDS:
        local_hs: dict[str, int] = {}
        try:
            if pid in [p["peer_id"] for p in REAL_PEERS]:
                p = next(x for x in REAL_PEERS if x["peer_id"] == pid)
                if p.get("is_terminal"):
                    r = ssh_terminal_sudo_script(p["host"], "wg show wg0 latest-handshakes", timeout=20)
                else:
                    r = ssh_cloud_sudo_script(p["host"], "wg show wg0 latest-handshakes", timeout=20, check=False)
            else:
                p = next(x for x in QEMU_PEERS if x["peer_id"] == pid)
                r = ssh_qemu_script(p["host"], "wg show wg0 latest-handshakes", timeout=20)
            now = int(time.time())
            for line in (r.stdout or "").splitlines():
                parts = line.split()
                if len(parts) == 2:
                    try:
                        hs = int(parts[1])
                    except ValueError:
                        continue
                    local_hs[parts[0][:16] + "..."] = (now - hs) if hs > 0 else None
        except Exception:
            pass
        diag[pid]["handshakes_local"] = local_hs
    return diag


def capture_wg_configs() -> dict[str, str]:
    configs: dict[str, str] = {}
    try:
        r = ssh_orch_sudo_script(f"wg show {HUB_WG_IFACE}", timeout=30, check=False)
        configs["orquestador"] = r.stdout or "(no output)"
        r2 = ssh_orch_sudo_script(f"wg showconf {HUB_WG_IFACE}", timeout=30, check=False)
        configs["orquestador-conf"] = r2.stdout or "(no output)"
    except Exception as e:
        configs["orquestador"] = f"ERROR: {e}"
        configs["orquestador-conf"] = f"ERROR: {e}"
    for p in REAL_PEERS:
        try:
            if p.get("is_terminal"):
                r = ssh_terminal_sudo_script(p["host"], "wg show wg0", timeout=30)
                configs[p["peer_id"]] = r.stdout or "(no output)"
                r2 = ssh_terminal_sudo_script(p["host"], "wg showconf wg0", timeout=30)
                configs[f"{p['peer_id']}-conf"] = r2.stdout or "(no output)"
            else:
                r = ssh_cloud_sudo_script(p["host"], "wg show wg0", timeout=30, check=False)
                configs[p["peer_id"]] = r.stdout or "(no output)"
                r2 = ssh_cloud_sudo_script(p["host"], "wg showconf wg0", timeout=30, check=False)
                configs[f"{p['peer_id']}-conf"] = r2.stdout or "(no output)"
        except Exception as e:
            configs[p["peer_id"]] = f"ERROR: {e}"
            configs[f"{p['peer_id']}-conf"] = f"ERROR: {e}"
    for p in QEMU_PEERS:
        try:
            r = ssh_qemu_script(p["host"], "wg show wg0", timeout=30)
            configs[p["peer_id"]] = r.stdout or "(no output)"
            r2 = ssh_qemu_script(p["host"], "wg showconf wg0", timeout=30)
            configs[f"{p['peer_id']}-conf"] = r2.stdout or "(no output)"
        except Exception as e:
            configs[p["peer_id"]] = f"ERROR: {e}"
            configs[f"{p['peer_id']}-conf"] = f"ERROR: {e}"
    return configs


_FAST_MODE = False


def is_fast() -> bool:
    return _FAST_MODE


def run_topology_cycle(topology: str) -> TopologyResult:
    log(f"\n{'='*60}\n=== TOPOLOGIA: {topology} (2 tenants) ===\n{'='*60}")
    log("Fase 1: Limpieza completa...")
    clean_all_peers()
    log("Fase 2: Configurando topologia...")
    set_topology(topology)
    log(f"  Topologia {topology} configurada")
    log("Fase 3: Iniciando peers (con tokens por tenant)...")
    start_all_peers()
    log("Fase 4: Esperando registro...")
    peers = wait_for_all_peers()
    log("Fase 5: Esperando handshakes...")
    wait_for_handshakes(timeout=60 if is_fast() else 120)
    time.sleep(3 if is_fast() else 5)
    log("Fase 5b: Capturando configuracion WireGuard...")
    wg_configs = capture_wg_configs()
    log("Fase 5c: Diagnosticando NAT por peer...")
    nat_diagnostics = capture_nat_diagnostics(peers)
    for pid in ALL_PEER_IDS:
        d = nat_diagnostics.get(pid, {})
        hs_hub = d.get("handshake_hub_s")
        shares = d.get("shares_nat_with") or []
        log(f"  {pid}: nat_type={d.get('nat_type','') or '(none)'} endpoint={d.get('endpoint','') or '(none)'} hs_hub={hs_hub}s" + (f" comparten NAT con {shares}" if shares else ""))
    log("Fase 6: Ejecutando pruebas de ping (cross-tenant)...")
    ping_count = 2 if is_fast() else 5
    ip_map = {pid: p["ip"] for pid, p in peers.items() if pid in ALL_PEER_IDS}
    ping_results: dict[str, dict[str, PingResult]] = {}
    for src_id in ALL_PEER_IDS:
        if src_id not in ip_map:
            continue
        ping_results[src_id] = {}
        src_real = [p for p in REAL_PEERS if p["peer_id"] == src_id]
        src_qemu = [p for p in QEMU_PEERS if p["peer_id"] == src_id]
        for dst_id in ALL_PEER_IDS:
            if dst_id == src_id or dst_id not in ip_map:
                continue
            dst_ip = ip_map[dst_id]
            cross_tenant = _tenant_for_peer(src_id) != _tenant_for_peer(dst_id)
            label = f"{src_id[:12]}->{dst_id[:12]}" + (" [CROSS-TENANT]" if cross_tenant else "")
            log(f"  Ping {label}...")
            try:
                if src_real:
                    p = src_real[0]
                    if p.get("is_terminal"):
                        ping_results[src_id][dst_id] = ping_terminal(p["host"], dst_ip, count=ping_count)
                    else:
                        ping_results[src_id][dst_id] = ping_cloud(p["host"], dst_ip, count=ping_count)
                elif src_qemu:
                    ping_results[src_id][dst_id] = ping_qemu(src_qemu[0]["host"], dst_ip, count=ping_count)
            except Exception as exc:
                log(f"  ERROR en ping {label}: {exc}")
                ping_results[src_id][dst_id] = PingResult(ok=False, avg_ms=None, loss_pct=100.0, ttl=None, raw=str(exc))
        ok_count = sum(1 for r in ping_results[src_id].values() if r.ok)
        cross_count = sum(1 for dst_id in ping_results[src_id] if _tenant_for_peer(src_id) != _tenant_for_peer(dst_id))
        cross_ok = sum(1 for dst_id, r in ping_results[src_id].items() if r.ok and _tenant_for_peer(src_id) != _tenant_for_peer(dst_id))
        log(f"  Ping desde {src_id} (tenant: {_tenant_for_peer(src_id)}): {ok_count}/{len(ping_results[src_id])} OK, cross-tenant: {cross_ok}/{cross_count}")
    log("Fase 7: Midiendo throughput nube...")
    tp_results: dict[str, list[ThroughputResult]] = {}
    if len(ip_map) >= 3:
        server_id = REAL_PEERS[0]["peer_id"]
        server_ip = ip_map.get(server_id, "")
        normal_clients: list[tuple[str, str]] = []
        for p in REAL_PEERS[1:]:
            if p.get("is_terminal"):
                continue
            if p["peer_id"] != server_id:
                normal_clients.append((p["peer_id"], p["host"]))
        if server_ip and _has_iperf3(REAL_PEERS[0]["host"]):
            log("  Usando iperf3 para throughput nube")
            tp_results["real"] = measure_cloud_iperf3(REAL_PEERS[0]["host"], server_ip, normal_clients)
        elif server_ip:
            log("  iperf3 no disponible, usando HTTP fallback")
            tp_results["real"] = measure_cloud_http(REAL_PEERS[0]["host"], server_ip, normal_clients)
    log(f"Topologia {topology} completada")
    return TopologyResult(topology=topology, peers=peers, ping_results=ping_results, throughput_results=tp_results, wg_configs=wg_configs, nat_diagnostics=nat_diagnostics)


# ── HTML rendering con info de tenant ────────────────────────────

def _peer_type(peer_id: str) -> str:
    for p in REAL_PEERS:
        if p["peer_id"] == peer_id:
            if p.get("is_rpi"):
                return "RPi5"
            if p.get("is_terminal"):
                return "VM"
            return "NUBE"
    for p in QEMU_PEERS:
        if p["peer_id"] == peer_id:
            return "QEMU"
    return "NUBE"


def _peer_label(peer_id: str) -> str:
    return ALL_PEER_LABELS.get(peer_id, peer_id)


def _ping_icon(r: PingResult) -> str:
    if r.ok and r.avg_ms is not None and r.avg_ms < 50:
        return '<span class="ok">OK</span>'
    elif r.ok:
        return '<span class="warn">LENTO</span>'
    elif r.loss_pct >= 80:
        return '<span class="fail">FALLO</span>'
    else:
        return '<span class="partial">PARCIAL</span>'


def _rtt_cell(r: PingResult) -> str:
    if r.ok and r.avg_ms is not None:
        return f'{r.avg_ms:.1f} ms'
    return "—"


def _path_type(src_id: str, dst_id: str, topology: str = "") -> str:
    """Clasifica el camino teorico entre dos peers segun topologia y tipos.

    Importante: en mesh puro no hay relay del hub. Los pares cloud↔cloud con IP
    publica usan P2P directo; cualquier par que toca un peer detras de NAT
    simetrico es un intento P2P que tipicamente falla (los paquetes se descartan
    en el NAT). La etiqueta refleja eso para no inducir a creer que hay relay.
    """
    topology = topology or _TOPOLOGY_DEFAULT
    st = _peer_type(src_id)
    dt = _peer_type(dst_id)
    nat_types = {"VM", "RPi5", "QEMU"}
    if topology == "hub-spoke":
        return "Relay via hub"
    if topology == "mesh":
        if st == "NUBE" and dt == "NUBE":
            return "P2P"
        # En mesh puro no existe relay; cloud↔NAT y NAT↔NAT son intentos P2P
        # que suelen fallar por NAT simetrico / hairpin no soportado.
        if st in nat_types and dt in nat_types:
            return "Intento P2P (NAT sim.)"
        return "Intento P2P (destino NAT)"
    # hub-mesh: cloud↔cloud P2P directo, demas relayados por el hub
    if st == "NUBE" and dt == "NUBE":
        return "P2P"
    return "Relay via hub"


def _cross_tenant_label(src_id: str, dst_id: str) -> str:
    if _tenant_for_peer(src_id) != _tenant_for_peer(dst_id):
        return f'<span class="tag-cross">CROSS</span>'
    return f'<span class="tag-same">mismo</span>'


_NAT_TYPES = {"VM", "RPi5", "QEMU"}


def _nat_pair_label(src_id: str, dst_id: str) -> str:
    """Etiqueta el motivo teorico de fallo en pares que tocan peers NAT."""
    st = _peer_type(src_id)
    dt = _peer_type(dst_id)
    if st in _NAT_TYPES and dt in _NAT_TYPES:
        return '<span class="fail">NAT bilateral</span>'
    if st in _NAT_TYPES or dt in _NAT_TYPES:
        return '<span class="partial">1 peer NAT</span>'
    return '<span class="ok">sin NAT</span>'


def _ttl_summary(ping_results: dict[str, dict[str, PingResult]]) -> str:
    ttls = set()
    for src in ping_results.values():
        for r in src.values():
            if r.ttl:
                ttls.add(r.ttl)
    if not ttls:
        return "N/A"
    parts = []
    for t in sorted(ttls):
        if t == 64:
            parts.append(f"TTL={t} (directo)")
        elif t == 63:
            parts.append(f"TTL={t} (relay 1 hop)")
        else:
            parts.append(f"TTL={t} (relay {64-t} hops)")
    return ", ".join(parts)


def render_html(title: str, timestamp: str, results: list[TopologyResult]) -> str:
    peers_inventory: dict[str, Any] = {}
    for r in results:
        for pid, p in r.peers.items():
            if pid in ALL_PEER_IDS and pid not in peers_inventory:
                peers_inventory[pid] = p

    rows: list[str] = []
    rows.append("""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>""" + title + """</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: #0d1117; color: #c9d1d9; padding: 20px; }
  h1 { color: #58a6ff; font-size: 1.8em; margin-bottom: 5px; }
  h2 { color: #79c0ff; font-size: 1.4em; margin: 25px 0 15px; border-bottom: 1px solid #21262d; padding-bottom: 8px; }
  h3 { color: #a5d6ff; font-size: 1.1em; margin: 15px 0 10px; }
  h4 { color: #8b949e; font-size: 0.9em; margin: 10px 0 5px; }
  pre { background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 12px;
        font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
        font-size: 0.75em; overflow-x: auto; margin: 5px 0 15px; white-space: pre-wrap; }
  code { background: #21262d; padding: 1px 5px; border-radius: 3px; font-size: 0.9em; }
  table { border-collapse: collapse; width: 100%; margin: 10px 0 20px; font-size: 0.85em; }
  th, td { border: 1px solid #30363d; padding: 6px 10px; text-align: center; }
  th { background: #161b22; font-weight: 600; color: #79c0ff; }
  td { background: #0d1117; }
  .ok { color: #3fb950; font-weight: bold; }
  .warn { color: #d29922; font-weight: bold; }
  .fail { color: #f85149; font-weight: bold; }
  .partial { color: #d29922; font-weight: bold; }
  .tag-nube { background: #1f6feb33; color: #58a6ff; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }
  .tag-vm { background: #6e40c933; color: #d2a8ff; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }
  .tag-rpi { background: #da363333; color: #ff7b72; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }
  .tag-qemu { background: #23863633; color: #3fb950; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }
  .tag-tenant-a { background: #1f6feb33; color: #58a6ff; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }
  .tag-tenant-b { background: #6e40c933; color: #d2a8ff; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }
  .tag-cross { background: #d2992233; color: #d29922; padding: 2px 6px; border-radius: 4px; font-size: 0.75em; font-weight: bold; }
  .tag-same { background: #21262d; color: #8b949e; padding: 2px 6px; border-radius: 4px; font-size: 0.75em; }
  .nav { background: #161b22; padding: 12px 16px; border-radius: 8px; margin-bottom: 20px; }
  .nav a { color: #58a6ff; text-decoration: none; margin-right: 15px; }
  .nav a:hover { text-decoration: underline; }
  .section { background: #161b22; border-radius: 8px; padding: 16px; margin-bottom: 20px; border: 1px solid #30363d; }
  .summary-ok { color: #3fb950; }
  .summary-fail { color: #f85149; }
  .summary-partial { color: #d29922; }
  .legend { color: #8b949e; margin-top: 10px; font-size: 0.8em; }
</style>
</head>
<body>
<h1>""" + title + """</h1>
<p>Generado: <code>""" + timestamp + """</code> | Orquestador: <code>""" + ORCH_HOST + """</code> (usuario <code>""" + ORCH_USER + """</code>)</p>
<p>Peers: """ + str(len(REAL_PEERS)) + """ reales + """ + str(len(QEMU_PEERS)) + """ QEMU (total """ + str(len(ALL_PEER_IDS)) + """) | <strong>Dos tenants: tenant-a (3 cloud) + tenant-b (VM + RPi5 + QEMU)</strong></p>
""")

    # Inventario con columna tenant
    rows.append(f'<div class="section" id="inventario"><h2>Inventario de peers (2 tenants)</h2><table><tr><th>Peer</th><th>IP tunel</th><th>Endpoint</th><th>NAT</th><th>Tipo</th><th>Tenant</th></tr>')
    for pid in sorted(peers_inventory):
        p = peers_inventory[pid]
        ptype = _peer_type(pid)
        tag_cls = {"NUBE": "tag-nube", "QEMU": "tag-qemu", "VM": "tag-vm", "RPi5": "tag-rpi"}.get(ptype, "tag-nube")
        tag = f'<span class="{tag_cls}">{ptype}</span>'
        tenant = _tenant_for_peer(pid)
        tenant_tag = f'<span class="tag-{tenant}">{tenant}</span>'
        rows.append(f'<tr><td>{_peer_label(pid)}</td><td><code>{p.get("ip","")}</code></td><td><code>{p.get("endpoint","")}</code></td><td>{p.get("nat_type","")}</td><td>{tag}</td><td>{tenant_tag}</td></tr>')
    rows.append(f'</table><p class="legend">Hub: <code>{ORCH_HOST}:51820</code> — IP tunel: <code>10.20.30.1</code> | tenant-a: 3 peers cloud AWS | tenant-b: VM40 + RPi5 + QEMU</p></div>')

    for r in results:
        rows.append(f'<div class="section" id="topo-{r.topology}">')
        rows.append(f'<h2>Topologia: <code>{r.topology}</code> (2 tenants)</h2>')
        total_ok = sum(1 for src in r.ping_results.values() for d in src.values() if d.ok)
        total_pairs = sum(len(src) for src in r.ping_results.values())
        # Contar cross-tenant
        cross_ok = 0
        cross_total = 0
        same_ok = 0
        same_total = 0
        for src_id, dsts in r.ping_results.items():
            for dst_id, pr in dsts.items():
                if _tenant_for_peer(src_id) != _tenant_for_peer(dst_id):
                    cross_total += 1
                    if pr.ok:
                        cross_ok += 1
                else:
                    same_total += 1
                    if pr.ok:
                        same_ok += 1
        pct = f"{total_ok}/{total_pairs}" if total_pairs else "N/A"
        cls = "summary-ok" if total_pairs > 0 and total_ok == total_pairs else ("summary-partial" if total_ok > 0 else "summary-fail")
        rows.append(f'<p class="{cls}">Ping OK: {pct} — TTLs: {_ttl_summary(r.ping_results)}</p>')
        rows.append(f'<p class="legend">Cross-tenant: <span class="{"summary-ok" if cross_total > 0 and cross_ok == cross_total else "summary-partial"}">{cross_ok}/{cross_total} OK</span> | Mismo tenant: <span class="{"summary-ok" if same_total > 0 and same_ok == same_total else "summary-partial"}">{same_ok}/{same_total} OK</span></p>')
        rows.append(f'<h3>Matriz de conectividad</h3><table><tr><th>Origen \\ Destino</th>')
        all_ids = sorted(r.ping_results.keys())
        for dst_id in all_ids:
            ip = peers_inventory.get(dst_id, {}).get("ip", "")
            tenant_tag = f'<br><span class="tag-{_tenant_for_peer(dst_id)}">{_tenant_for_peer(dst_id)}</span>'
            rows.append(f'<th>{_peer_label(dst_id)}<br><small><code>{ip}</code></small>{tenant_tag}</th>')
        rows.append('</tr>')
        for src_id in all_ids:
            ip = peers_inventory.get(src_id, {}).get("ip", "")
            src_tenant = _tenant_for_peer(src_id)
            rows.append(f'<tr><td><b>{_peer_label(src_id)}</b><br><small><code>{ip}</code></small><br><span class="tag-{src_tenant}">{src_tenant}</span></td>')
            for dst_id in all_ids:
                if dst_id == src_id:
                    rows.append('<td>—</td>')
                    continue
                pr = r.ping_results.get(src_id, {}).get(dst_id)
                if pr is None:
                    rows.append('<td class="fail">—</td>')
                else:
                    icon = _ping_icon(pr)
                    rtt = _rtt_cell(pr)
                    cross = _cross_tenant_label(src_id, dst_id)
                    if pr.ok:
                        cls_cell = "ok"
                    elif pr.loss_pct >= 80:
                        cls_cell = "fail"
                    else:
                        cls_cell = "partial"
                    rows.append(f'<td class="{cls_cell}">{icon}<br><small>{rtt}</small><br>{cross}</td>')
            rows.append('</tr>')
        rows.append('</table>')
        rows.append('<h3>Detalle por par (con clasificacion cross-tenant y NAT)</h3><table><tr><th>Origen</th><th>Tenant</th><th>Destino</th><th>Tenant</th><th>Cross</th><th>Tipo</th><th>NAT</th><th>RTT (ms)</th><th>Perdida</th><th>TTL</th><th>Estado</th></tr>')
        for src_id in all_ids:
            for dst_id in all_ids:
                if dst_id == src_id:
                    continue
                pr = r.ping_results.get(src_id, {}).get(dst_id)
                if pr is None:
                    continue
                ptype = _path_type(src_id, dst_id, r.topology)
                nat_label = _nat_pair_label(src_id, dst_id)
                rtt = f'{pr.avg_ms:.1f}' if pr.avg_ms is not None else "—"
                loss = f'{pr.loss_pct:.0f}%'
                ttl = str(pr.ttl) if pr.ttl else "—"
                icon = _ping_icon(pr)
                ip_src = peers_inventory.get(src_id, {}).get("ip", "")
                ip_dst = peers_inventory.get(dst_id, {}).get("ip", "")
                src_t = _tenant_for_peer(src_id)
                dst_t = _tenant_for_peer(dst_id)
                cross = _cross_tenant_label(src_id, dst_id)
                rows.append(f'<tr><td>{_peer_label(src_id)}<br><small><code>{ip_src}</code></small></td><td><span class="tag-{src_t}">{src_t}</span></td><td>{_peer_label(dst_id)}<br><small><code>{ip_dst}</code></small></td><td><span class="tag-{dst_t}">{dst_t}</span></td><td>{cross}</td><td>{ptype}</td><td>{nat_label}</td><td>{rtt}</td><td>{loss}</td><td>{ttl}</td><td>{icon}</td></tr>')
        rows.append('</table>')
        tp = r.throughput_results
        if tp:
            rows.append('<h3>Throughput</h3><table><tr><th>Tipo</th><th>Cliente</th><th>Tenant</th><th>Velocidad</th><th>Tamanio</th><th>Estado</th></tr>')
            for tp_type, tp_items in tp.items():
                for item in tp_items:
                    cls = "ok" if item.ok else "fail"
                    speed = f'{item.mbps:.2f} Mbps' if item.ok else "—"
                    size = f'{item.size_bytes / 1024 / 1024:.0f} MB' if item.ok and item.size_bytes else "—"
                    icon = '<span class="ok">OK</span>' if item.ok else '<span class="fail">FALLO</span>'
                    tp_label = tp_type.upper() if tp_type != "real" else "NUBE"
                    item_tenant = _tenant_for_peer(item.peer_id)
                    rows.append(f'<tr><td><span class="tag-nube">{tp_label}</span></td><td>{item.peer_id}</td><td><span class="tag-{item_tenant}">{item_tenant}</span></td><td>{speed}</td><td>{size}</td><td>{icon}</td></tr>')
            rows.append('</table>')
        wg = r.wg_configs
        nd = r.nat_diagnostics
        if nd:
            rows.append('<h3>Diagnostico NAT</h3>')
            rows.append('<p class="legend">Diagnostico capturado en el momento de la medicion. Explica los fallos por NAT simetrico / hairpin / mapeo efimero.</p>')
            rows.append('<table><tr><th>Peer</th><th>Tipo</th><th>Tenant</th><th>Endpoint NAT</th><th>IP tunel</th><th>NAT type</th><th>Tras NAT</th><th>HS con hub</th><th>Comparte NAT con</th></tr>')
            for pid in ALL_PEER_IDS:
                d = nd.get(pid, {})
                ptype = _peer_type(pid)
                tag_cls = {"NUBE": "tag-nube", "QEMU": "tag-qemu", "VM": "tag-vm", "RPi5": "tag-rpi"}.get(ptype, "tag-nube")
                tenant = _tenant_for_peer(pid)
                is_nat = d.get("is_nat", False)
                nat_badge = '<span class="fail">SI</span>' if is_nat else '<span class="ok">no</span>'
                hs_hub = d.get("handshake_hub_s")
                hs_str = f'{hs_hub}s ago' if hs_hub is not None else "—"
                hs_cls = "ok" if (hs_hub is not None and hs_hub <= 180) else "fail"
                shares = d.get("shares_nat_with") or []
                shares_str = ", ".join(shares) if shares else "—"
                shares_str = f'<span class="fail">{shares_str}</span>' if shares else shares_str
                rows.append(f'<tr><td>{_peer_label(pid)}</td><td><span class="{tag_cls}">{ptype}</span></td><td><span class="tag-{tenant}">{tenant}</span></td><td><code>{d.get("endpoint","") or "—"}</code></td><td><code>{d.get("tunnel_ip","") or "—"}</code></td><td>{d.get("nat_type","") or "(none)"}</td><td>{nat_badge}</td><td class="{hs_cls}">{hs_str}</td><td>{shares_str}</td></tr>')
            rows.append('</table>')
            # Leyenda explicativa de fallos por patron NAT
            n_bilateral = sum(1 for pid in ALL_PEER_IDS if nd[pid].get("shares_nat_with"))
            n_nat = sum(1 for pid in ALL_PEER_IDS if nd[pid].get("is_nat"))
            rows.append(f'<p class="legend">Peers detras de NAT: {n_nat}/{len(ALL_PEER_IDS)} | Peers que comparten NAT (riesgo hairpin): {n_bilateral} | Hub relayRecommended para pares NAT↔NAT</p>')
        if wg:
            rows.append('<h3>Configuracion WireGuard capturada</h3>')
            rows.append('<h4>Orquestador (wg-HUB)</h4>')
            rows.append(f'<pre>{wg.get("orquestador", "N/A")}</pre>')
            rows.append('<h4>Orquestador config (wg-HUB)</h4>')
            rows.append(f'<pre>{wg.get("orquestador-conf", "N/A")}</pre>')
            for p in REAL_PEERS:
                pid = p["peer_id"]
                rows.append(f'<h4>{_peer_label(pid)} ({p["tenant"]}) — wg show</h4>')
                rows.append(f'<pre>{wg.get(pid, "N/A")}</pre>')
                rows.append(f'<h4>{_peer_label(pid)} ({p["tenant"]}) — wg showconf</h4>')
                rows.append(f'<pre>{wg.get(f"{pid}-conf", "N/A")}</pre>')
            for p in QEMU_PEERS:
                pid = p["peer_id"]
                rows.append(f'<h4>{_peer_label(pid)} ({p["tenant"]}) — wg show</h4>')
                rows.append(f'<pre>{wg.get(pid, "N/A")}</pre>')
                rows.append(f'<h4>{_peer_label(pid)} ({p["tenant"]}) — wg showconf</h4>')
                rows.append(f'<pre>{wg.get(f"{pid}-conf", "N/A")}</pre>')
        rows.append('</div>')
    rows.append('<div class="section" id="resumen"><h2>Resumen por topologia (2 tenants)</h2><table><tr><th>Topologia</th><th>Ping OK</th><th>Cross-tenant OK</th><th>Mismo tenant OK</th><th>RTT min</th><th>RTT prom</th><th>RTT max</th><th>Throughput</th></tr>')
    for r in results:
        all_avgs = [pr.avg_ms for src in r.ping_results.values() for pr in src.values() if pr.ok and pr.avg_ms is not None]
        min_rtt = f'{min(all_avgs):.1f}' if all_avgs else "—"
        avg_rtt = f'{sum(all_avgs) / len(all_avgs):.1f}' if all_avgs else "—"
        max_rtt = f'{max(all_avgs):.1f}' if all_avgs else "—"
        total_ok = sum(1 for src in r.ping_results.values() for pr in src.values() if pr.ok)
        total_pairs = sum(len(src) for src in r.ping_results.values())
        cross_ok = sum(1 for src_id, dsts in r.ping_results.items() for dst_id, pr in dsts.items() if pr.ok and _tenant_for_peer(src_id) != _tenant_for_peer(dst_id))
        cross_total = sum(1 for src_id, dsts in r.ping_results.items() for dst_id in dsts if _tenant_for_peer(src_id) != _tenant_for_peer(dst_id))
        same_ok = total_ok - cross_ok
        same_total = total_pairs - cross_total
        tp_strs = []
        for tp_type, tp_items in r.throughput_results.items():
            speeds = [i.mbps for i in tp_items if i.ok]
            if speeds:
                tp_strs.append(f'{"nube" if tp_type == "real" else tp_type}: {sum(speeds) / len(speeds):.1f} Mbps')
        tp_s = "; ".join(tp_strs) if tp_strs else "—"
        rows.append(f'<tr><td><code>{r.topology}</code></td><td><span class="{"summary-ok" if total_ok == total_pairs else "summary-partial"}">{total_ok}/{total_pairs}</span></td><td><span class="{"summary-ok" if cross_total > 0 and cross_ok == cross_total else "summary-partial"}">{cross_ok}/{cross_total}</span></td><td><span class="{"summary-ok" if same_total > 0 and same_ok == same_total else "summary-partial"}">{same_ok}/{same_total}</span></td><td>{min_rtt}</td><td>{avg_rtt}</td><td>{max_rtt}</td><td>{tp_s}</td></tr>')
    rows.append('</table></div>')
    rows.append('<div class="section" id="auth-info"><h2>Modo de autenticacion CLI Multiusuario — Dos Tenants</h2>')
    rows.append(f'<table><tr><th>Operacion</th><th>Usuario</th><th>Auth</th></tr>')
    rows.append(f'<tr><td>network.* (create/delete/topology)</td><td>admin</td><td><code>--admin-token</code></td></tr>')
    rows.append(f'<tr><td>peer.list (todos los peers)</td><td>admin</td><td><code>--admin-token</code></td></tr>')
    rows.append(f'<tr><td>peer.unregister (peers cloud)</td><td>tenant-a</td><td><code>--token</code> (JWT tenant-a)</td></tr>')
    rows.append(f'<tr><td>peer.unregister (VM/RPi5/QEMU)</td><td>tenant-b</td><td><code>--token</code> (JWT tenant-b)</td></tr>')
    rows.append(f'<tr><td>SSH nubes AWS</td><td>ubuntu / ec2-user</td><td>llave <code>linkguard-key.pem</code></td></tr>')
    rows.append(f'<tr><td>SSH orquestador</td><td>{ORCH_USER}</td><td>llave + <code>sudo</code></td></tr>')
    rows.append(f'<tr><td>SSH VM/RPi5</td><td>root / natalia</td><td>password via jump <code>{TERMINAL_JUMP}</code></td></tr>')
    rows.append(f'<tr><td>SSH QEMU</td><td>root</td><td>password <code>{QEMU_PASS}</code></td></tr>')
    rows.append(f'</table>')
    rows.append(f'<p class="legend">Tenants: <span class="tag-tenant-a">tenant-a</span> (3 peers cloud AWS) + <span class="tag-tenant-b">tenant-b</span> (VM40 + RPi5 + QEMU) | Cada peer.env con <code>USER_ID</code> + <code>ORCH_TOKEN</code> del tenant correspondiente</p>')
    rows.append('</div>')
    rows.append('</body></html>\n')
    return "\n".join(rows)


def write_jsonl_report(timestamp: str, results: list[TopologyResult]) -> None:
    jsonl_path = ROOT / "docs" / "reports" / "aws-multiuser-cli-1qemu-2tenants-historial.jsonl"
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    records = []
    for r in results:
        total_ok = sum(1 for src in r.ping_results.values() for pr in src.values() if pr.ok)
        total_pairs = sum(len(src) for src in r.ping_results.values())
        all_avgs = [pr.avg_ms for src in r.ping_results.values() for pr in src.values() if pr.ok and pr.avg_ms is not None]
        cross_ok = sum(1 for src_id, dsts in r.ping_results.items() for dst_id, pr in dsts.items() if pr.ok and _tenant_for_peer(src_id) != _tenant_for_peer(dst_id))
        cross_total = sum(1 for src_id, dsts in r.ping_results.items() for dst_id in dsts if _tenant_for_peer(src_id) != _tenant_for_peer(dst_id))
        tp_summary = {}
        for tp_type, tp_items in r.throughput_results.items():
            speeds = [i.mbps for i in tp_items if i.ok]
            if speeds:
                tp_summary[tp_type] = {"avg_mbps": round(sum(speeds) / len(speeds), 2), "samples": len(speeds)}
        record = {
            "timestamp": timestamp,
            "orchestrator": ORCH_HOST,
            "topology": r.topology,
            "tenants": TENANTS,
            "ping": {"ok": total_ok, "total": total_pairs, "cross_tenant_ok": cross_ok, "cross_tenant_total": cross_total, "min_rtt_ms": round(min(all_avgs), 2) if all_avgs else None, "avg_rtt_ms": round(sum(all_avgs) / len(all_avgs), 2) if all_avgs else None, "max_rtt_ms": round(max(all_avgs), 2) if all_avgs else None},
            "throughput": tp_summary,
            "peers": list(r.peers.keys()),
            "peer_tenants": {pid: _tenant_for_peer(pid) for pid in r.peers if pid in ALL_PEER_IDS},
            "nat_diagnostics": {
                pid: {
                    "nat_type": (r.nat_diagnostics or {}).get(pid, {}).get("nat_type", ""),
                    "is_nat": (r.nat_diagnostics or {}).get(pid, {}).get("is_nat", False),
                    "shares_nat_with": (r.nat_diagnostics or {}).get(pid, {}).get("shares_nat_with", []),
                    "handshake_hub_s": (r.nat_diagnostics or {}).get(pid, {}).get("handshake_hub_s"),
                }
                for pid in ALL_PEER_IDS if pid in (r.nat_diagnostics or {})
            } if r.nat_diagnostics else {},
        }
        records.append(record)
    with jsonl_path.open("a", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    log(f"Historial JSONL actualizado en {jsonl_path}")


def run_report(topology: str, *, title: str, report_subdir: str, file_prefix: str, default_topology: str = "hub-spoke", description: str = "") -> int:
    global _admin_token, _TOPOLOGY_DEFAULT, _FAST_MODE
    _TOPOLOGY_DEFAULT = default_topology

    parser = argparse.ArgumentParser(description=description or f"Genera reporte HTML para topologia {topology} con 2 tenants")
    parser.add_argument("--output", default="")
    parser.add_argument("--skip-throughput", action="store_true")
    parser.add_argument("--skip-clean", action="store_true")
    parser.add_argument("--fast", action="store_true", help="Pings rapidos (2 paquetes)")
    args = parser.parse_args()
    _FAST_MODE = args.fast

    if not Path(SSH_KEY).exists():
        print(f"ERROR: No se encontro la llave SSH {SSH_KEY}", file=sys.stderr)
        return 1

    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    ts_slug = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")
    if args.output:
        output_path = Path(args.output)
    else:
        date_dir = ts_slug[:4] + "-" + ts_slug[4:6] + "-" + ts_slug[6:8]
        output_path = ROOT / "docs" / "reports" / "aws-multiuser-cli-1qemu-2tenants" / report_subdir / date_dir / f"{file_prefix}-{ts_slug}.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    admin_token = get_admin_token()
    _admin_token = admin_token
    log(f"ADMIN_TOKEN obtenido: {admin_token[:16]}...")

    log(f"\n=== Configurando dos tenants: {', '.join(TENANTS)} ===")
    jwts = ensure_tenant_users()
    for t, jwt in jwts.items():
        log(f"  {t} JWT: {jwt[:20]}...")

    original_topology = get_current_topology()
    log(f"Topologia actual: {original_topology}")

    results: list[TopologyResult] = []

    try:
        result = run_topology_cycle(topology)
        results.append(result)

        log(f"\n{'='*60}\n=== GENERANDO REPORTE HTML (2 tenants) ===\n{'='*60}")
        set_topology(original_topology)
        html = render_html(title, timestamp, results)
        output_path.write_text(html)
        log(f"Reporte generado en {output_path}")
        write_jsonl_report(timestamp, results)
    except Exception as exc:
        log(f"ERROR: {exc}")
        import traceback
        traceback.print_exc()
        try:
            set_topology(original_topology)
        except Exception:
            pass
        return 1

    return 0
