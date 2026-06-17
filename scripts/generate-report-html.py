#!/usr/bin/env python3
"""Genera reporte HTML completo con peers reales + QEMU, limpiando entre topologías."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import subprocess
import sys
import time
import xmlrpc.client
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TESTBED_SCRIPT = ROOT / "testbed" / "scripts" / "launch-testbed.py"
REPORT_PATH = ROOT / "docs" / "reporte-html-completo.html"

ORCH_HOST = os.environ.get("TESTBED_REAL_ORCH_HOST", "101.44.24.91")
ORCH_USER = os.environ.get("TESTBED_REAL_ORCH_USER", "root")
REMOTE_PASS = os.environ.get("LINKGUARD_REMOTE_PASS") or os.environ.get("TESTBED_REAL_ORCH_PASS", "")
REAL_ORCH_URL = os.environ.get("TESTBED_REAL_ORCH_URL", f"http://{ORCH_HOST}:8000/RPC2")
QEMU_PASS = "linkguard-test"
SSH_OPTS = ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null", "-o", "ConnectTimeout=5"]
TOPOLOGIES = ["hub-spoke", "mesh", "hub-mesh"]
HUB_WG_IFACE = "wg-HUB"
LOCAL_SUDO_PASS = os.environ.get("SUDO_PASS", "atidesa15")

REAL_PEERS = [
    {"peer_id": "peer-46-250-168-185", "host": "46.250.168.185", "label": "185 nube (46.250.168.185)"},
    {"peer_id": "peer-122-8-179-57", "host": "122.8.179.57", "label": "57 nube (122.8.179.57)"},
    {"peer_id": "peer-46-250-162-141", "host": "46.250.162.141", "label": "141 nube (46.250.162.141)"},
]

QEMU_PEERS = [
    {"peer_id": "qemu-orq", "role": "orq", "host": "192.168.100.10", "label": "qemu-orq"},
    {"peer_id": "qemu-pa", "role": "pa", "host": "192.168.100.20", "label": "qemu-pa"},
    {"peer_id": "qemu-pb", "role": "pb", "host": "192.168.100.30", "label": "qemu-pb"},
]

ALL_PEER_IDS = [p["peer_id"] for p in REAL_PEERS + QEMU_PEERS]
ALL_PEER_LABELS = {p["peer_id"]: p["label"] for p in REAL_PEERS + QEMU_PEERS}


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


def sshpass_run(password: str, host: str, *remote_cmd: str, timeout: int = 120, check: bool = False) -> subprocess.CompletedProcess[str]:
    return run(["sshpass", "-p", password, "ssh", *SSH_OPTS, host, *remote_cmd], timeout=timeout, check=check)


def ssh_real(host: str, *remote_cmd: str, timeout: int = 120, check: bool = False) -> subprocess.CompletedProcess[str]:
    if not REMOTE_PASS:
        raise RuntimeError("Define LINKGUARD_REMOTE_PASS o TESTBED_REAL_ORCH_PASS")
    last = None
    for _ in range(3):
        last = sshpass_run(REMOTE_PASS, f"root@{host}", *remote_cmd, timeout=timeout, check=False)
        if last.returncode == 0:
            return last
        time.sleep(2)
    if check:
        raise RuntimeError(f"SSH failed on {host}\n{last.stdout if last else ''}\n{last.stderr if last else ''}")
    assert last is not None
    return last


def ssh_real_script(host: str, script: str, *, timeout: int = 120, check: bool = False) -> subprocess.CompletedProcess[str]:
    if not REMOTE_PASS:
        raise RuntimeError("Define LINKGUARD_REMOTE_PASS o TESTBED_REAL_ORCH_PASS")
    last = None
    for _ in range(3):
        last = subprocess.run(
            ["sshpass", "-p", REMOTE_PASS, "ssh", *SSH_OPTS, f"root@{host}", "sh"],
            input=script, text=True, capture_output=True, timeout=timeout, check=False,
        )
        if last.returncode == 0:
            return last
        time.sleep(2)
    if check:
        raise RuntimeError(f"Remote script failed on {host}\n{last.stdout if last else ''}\n{last.stderr if last else ''}")
    assert last is not None
    return last


def qemu_cmd(*args: str, timeout: int = 120, check: bool = False) -> subprocess.CompletedProcess[str]:
    return run(["python3", str(TESTBED_SCRIPT), *args], timeout=timeout, check=check)


def qemu_ssh(role: str, *cmd: str, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return qemu_cmd("ssh", role, *cmd, timeout=timeout)


def qemu_ssh_script(role: str, script: str, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    host = [p["host"] for p in QEMU_PEERS if p["role"] == role][0]
    return subprocess.run(
        ["sshpass", "-p", QEMU_PASS, "ssh", *SSH_OPTS, f"root@{host}", "sh"],
        input=script, text=True, capture_output=True, timeout=timeout, check=False,
    )


def rpc() -> xmlrpc.client.ServerProxy:
    return xmlrpc.client.ServerProxy(REAL_ORCH_URL, allow_none=True)


def get_admin_token() -> str:
    result = ssh_real(ORCH_HOST, "cat", "/etc/linkguard/secrets", timeout=120, check=True)
    for line in result.stdout.splitlines():
        if line.startswith("ADMIN_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("No encontré ADMIN_TOKEN en /etc/linkguard/secrets")


def log(msg: str) -> None:
    print(f"[reporte] {msg}", flush=True)


# ── Peer listing ──

def peer_list() -> dict[str, Any]:
    return rpc().__getattr__("peer.list")().get("peers", {})


def get_current_topology() -> str:
    data = rpc().__getattr__("network.get_topology")("default")
    return str(data.get("topology") or "hub-spoke")


def set_topology(topology: str) -> None:
    rpc().__getattr__("network.set_topology")("default", topology)


# ── Cleanup ──

def peer_unregister(peer_id: str, admin_token: str) -> bool:
    try:
        return bool(rpc().__getattr__("peer.unregister")(peer_id, "", admin_token))
    except Exception as exc:
        log(f"  WARN: No pude eliminar {peer_id} del orquestador: {exc}")
        return False


def clean_real_peer(host: str) -> None:
    script = """set -e
systemctl stop wg-auto-register 2>/dev/null || true
rm -f /etc/wireguard/wg0.conf /etc/wireguard/wg0.key /etc/wireguard/wg0.pub /etc/linkguard/wg-auto.json /etc/wireguard/wg-auto.json
ip link delete wg0 2>/dev/null || true
"""
    ssh_real_script(host, script, timeout=60, check=False)


def clean_qemu_peer(role: str) -> None:
    script = """set -e
rc-service wg-auto-register stop 2>/dev/null || true
killall -9 wg-auto-register.py 2>/dev/null || true
rm -f /etc/wireguard/wg0.conf /etc/wireguard/wg0.key /etc/wireguard/wg0.pub /etc/linkguard/wg-auto.json
rm -f /etc/wireguard/wg-auto.json
ip link delete wg0 2>/dev/null || true
"""
    qemu_ssh_script(role, script, timeout=60)


def clean_orchestrator_peers(admin_token: str) -> None:
    peers = peer_list()
    for pid in list(peers.keys()):
        if pid.startswith("peer-") or pid.startswith("qemu-"):
            peer_unregister(pid, admin_token)
            log(f"  Eliminado {pid} del orquestador")
    time.sleep(2)


def hub_flush_peers(admin_token: str) -> None:
    script = """set -e
WG_IFACE="wg-HUB"
wg show "$WG_IFACE" peers 2>/dev/null | while read -r pk; do
    [ -n "$pk" ] && wg set "$WG_IFACE" peer "$pk" remove
done
"""
    ssh_real_script(ORCH_HOST, script, timeout=60, check=False)
    log("  Peers eliminados del hub WG")


def clean_all_peers(admin_token: str) -> None:
    log("Limpiando peers reales...")
    for p in REAL_PEERS:
        clean_real_peer(p["host"])
        log(f"  {p['host']} limpiado")
    log("Limpiando peers QEMU...")
    for p in QEMU_PEERS:
        clean_qemu_peer(p["role"])
        log(f"  {p['role']} limpiado")
    log("Limpiando orquestador...")
    clean_orchestrator_peers(admin_token)
    log("Limpiando WG hub...")
    hub_flush_peers(admin_token)


# ── Peer start ──

def start_real_peer(host: str) -> None:
    ssh_real(host, "systemctl", "restart", "wg-auto-register", timeout=180, check=False)


def start_qemu_peer(role: str) -> None:
    qemu_ssh_script(role, """set -e
rc-service wg-auto-register stop 2>/dev/null || true
killall -9 wg-auto-register.py 2>/dev/null || true
rc-service wg-auto-register start
""", timeout=180)


def start_all_peers() -> None:
    log("Iniciando peers reales...")
    for p in REAL_PEERS:
        start_real_peer(p["host"])
        log(f"  {p['host']} iniciado")
    log("Iniciando peers QEMU...")
    for p in QEMU_PEERS:
        start_qemu_peer(p["role"])
        log(f"  {p['role']} iniciado")


# ── Wait helpers ──

def wait_for_all_peers(timeout: int = 180) -> dict[str, Any]:
    deadline = time.time() + timeout
    last = {}
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
        result = ssh_real(ORCH_HOST, "wg", "show", HUB_WG_IFACE, timeout=60, check=False)
        lines = result.stdout.splitlines()
        peers_with_hs = 0
        total_peers = 0
        for line in lines:
            if line.startswith("peer:"):
                total_peers += 1
            # Match any "latest handshake" line (even 0 seconds ago counts as a handshake)
            if re.search(r"latest handshake:\s+\d+", line):
                peers_with_hs += 1
        if total_peers >= len(ALL_PEER_IDS) and peers_with_hs == total_peers:
            log(f"Handshakes establecidos: {peers_with_hs}/{total_peers}")
            return
        log(f"  Esperando handshakes: {peers_with_hs}/{total_peers} peers")
        time.sleep(5)
    raise RuntimeError(f"No se establecieron handshakes tras {timeout}s")


# ── Ping tests ──

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


def ping_real(host: str, target: str, count: int = 5) -> PingResult:
    result = ssh_real(host, "ping", "-n", "-c", str(count), "-W", "2", target, timeout=180, check=False)
    return parse_ping_output((result.stdout or "") + (result.stderr or ""))


def ping_qemu(role: str, target: str, count: int = 5) -> PingResult:
    result = qemu_cmd("ssh", role, "ping", "-n", "-c", str(count), "-W", "2", target, timeout=180, check=False)
    return parse_ping_output((result.stdout or "") + (result.stderr or ""))


# ── Throughput tests ──

def _has_iperf3(host: str, is_qemu: bool = False) -> bool:
    cmd = ["which", "iperf3"]
    if is_qemu:
        role = [p["role"] for p in QEMU_PEERS if p["host"] == host][0]
        r = qemu_ssh(role, *cmd, timeout=15)
    else:
        r = ssh_real(host, *cmd, timeout=15, check=False)
    return r.returncode == 0 and "iperf3" in (r.stdout or "")


def measure_real_iperf3(server_host: str, server_ip: str, clients: list[tuple[str, str]], duration: int = 10) -> list[ThroughputResult]:
    port = "5201"
    results = []
    # start server
    server_script = f"""set -e
killall -9 iperf3 2>/dev/null || true
nohup iperf3 -s -B {server_ip} -p {port} >/tmp/iperf3-server.log 2>&1 &
echo $!
"""
    r = ssh_real_script(server_host, server_script, timeout=60, check=False)
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
            r = ssh_real_script(host, client_script, timeout=60, check=False)
            out = r.stdout or ""
            # parse iperf3 output: [ ID] Interval ... Transfer ... Bandwidth
            m = re.search(r"\[\s*\d+\]\s+\d+\.\d+-\d+\.\d+\s+sec\s+[\d\.]+\s+\w+\s+([\d\.]+)\s+Mbits/sec", out)
            if m:
                mbps = float(m.group(1))
                results.append(ThroughputResult(peer_id=peer_id, mbps=mbps, size_bytes=0, time_sec=duration, ok=True))
            else:
                log(f"  iperf3 parse error for {peer_id}: {out[:200]}")
                results.append(ThroughputResult(peer_id=peer_id, mbps=0.0, size_bytes=0, time_sec=0, ok=False))
    finally:
        if server_pid:
            ssh_real_script(server_host, f"kill {server_pid} 2>/dev/null || true; killall -9 iperf3 2>/dev/null || true", timeout=30, check=False)
    return results


def measure_qemu_iperf3(server_role: str, server_ip: str, clients: list[tuple[str, str]], duration: int = 10) -> list[ThroughputResult]:
    port = "5201"
    results = []
    server_script = f"""set -e
killall -9 iperf3 2>/dev/null || true
nohup iperf3 -s -B {server_ip} -p {port} >/tmp/iperf3-server.log 2>&1 &
echo $!
"""
    r = qemu_ssh_script(server_role, server_script, timeout=60)
    server_pid = (r.stdout or "").strip()
    time.sleep(2)
    try:
        for peer_id, _ in clients:
            role_list = [p["role"] for p in QEMU_PEERS if p["peer_id"] == peer_id]
            if not role_list:
                results.append(ThroughputResult(peer_id=peer_id, mbps=0.0, size_bytes=0, time_sec=0, ok=False))
                continue
            role = role_list[0]
            client_script = f"""set -e
output=$(iperf3 -c {server_ip} -p {port} -t {duration} -f m 2>&1)
echo "$output"
"""
            r = qemu_ssh_script(role, client_script, timeout=60)
            out = r.stdout or ""
            m = re.search(r"\[\s*\d+\]\s+\d+\.\d+-\d+\.\d+\s+sec\s+[\d\.]+\s+\w+\s+([\d\.]+)\s+Mbits/sec", out)
            if m:
                mbps = float(m.group(1))
                results.append(ThroughputResult(peer_id=peer_id, mbps=mbps, size_bytes=0, time_sec=duration, ok=True))
            else:
                log(f"  QEMU iperf3 parse error for {peer_id}: {out[:200]}")
                results.append(ThroughputResult(peer_id=peer_id, mbps=0.0, size_bytes=0, time_sec=0, ok=False))
    finally:
        if server_pid:
            qemu_ssh_script(server_role, f"kill {server_pid} 2>/dev/null || true; killall -9 iperf3 2>/dev/null || true", timeout=30)
    return results


def measure_real_http(server_host: str, server_ip: str, clients: list[tuple[str, str]], file_size_mb: int = 8) -> list[ThroughputResult]:
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
    ssh_real_script(server_host, setup, timeout=180, check=True)
    time.sleep(2)
    results = []
    try:
        for peer_id, host in clients:
            curl_cmd = f"""
curl -m 60 -s -o /dev/null -w '%{{http_code}} %{{size_download}} %{{time_total}} %{{speed_download}}' http://{server_ip}:{port}/{os.path.basename(remote_file)}
"""
            r = ssh_real_script(host, curl_cmd, timeout=180, check=False)
            out = r.stdout.strip()
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
        ssh_real_script(server_host, cleanup, timeout=120, check=False)
    return results


def measure_qemu_http(server_role: str, server_ip: str, clients: list[tuple[str, str]], file_size_mb: int = 4) -> list[ThroughputResult]:
    port = "8083"
    remote_file = f"/tmp/wg-perf-{file_size_mb}m.bin"
    pid_file = "/tmp/wg-http.pid"
    setup = f"""set -e
kill $(cat {pid_file}) 2>/dev/null || true
rm -f {pid_file} {remote_file}
dd if=/dev/zero of={remote_file} bs=1M count={file_size_mb} status=none
nohup python3 -m http.server {port} --bind {server_ip} --directory /tmp >/tmp/wg-http.log 2>&1 &
echo $! > {pid_file}
"""
    qemu_ssh_script(server_role, setup, timeout=180)
    time.sleep(2)
    results = []
    try:
        for peer_id, host in clients:
            client_role_list = [p["role"] for p in QEMU_PEERS if p["peer_id"] == peer_id]
            if not client_role_list:
                results.append(ThroughputResult(peer_id=peer_id, mbps=0.0, size_bytes=0, time_sec=0, ok=False))
                continue
            role = client_role_list[0]
            py_script = f"""python3 - <<'PY'
import time, urllib.request
url = 'http://{server_ip}:{port}/{os.path.basename(remote_file)}'
t0 = time.time()
with urllib.request.urlopen(url, timeout=60) as r:
    data = r.read()
dt = time.time() - t0
speed = int(len(data) / dt) if dt else 0
print(speed)
PY
"""
            r = qemu_ssh_script(role, py_script, timeout=180)
            out = r.stdout.strip()
            if out.isdigit():
                speed = int(out)
                mbps = round((speed * 8) / 1_000_000, 2) if speed > 0 else 0.0
                results.append(ThroughputResult(peer_id=peer_id, mbps=mbps, size_bytes=file_size_mb * 1024 * 1024, time_sec=0, ok=True))
            else:
                log(f"  QEMU throughput error for {peer_id}: stdout={r.stdout!r} stderr={r.stderr!r}")
                results.append(ThroughputResult(peer_id=peer_id, mbps=0.0, size_bytes=0, time_sec=0, ok=False))
    finally:
        cleanup = f"kill $(cat {pid_file}) 2>/dev/null || true\nrm -f {pid_file} {remote_file}\n"
        qemu_ssh_script(server_role, cleanup, timeout=60)
    return results


# ── Topology cycle ──

@dataclass
class TopologyResult:
    topology: str
    peers: dict[str, Any]
    ping_results: dict[str, dict[str, PingResult]]
    throughput_results: dict[str, list[ThroughputResult]]
    wg_configs: dict[str, str]


def capture_wg_configs(peers: dict[str, Any]) -> dict[str, str]:
    configs: dict[str, str] = {}
    # Orchestrator
    try:
        r = ssh_real(ORCH_HOST, "wg", "show", HUB_WG_IFACE, timeout=30, check=False)
        configs["orquestador"] = r.stdout or "(no output)"
        r2 = ssh_real(ORCH_HOST, "wg", "showconf", HUB_WG_IFACE, timeout=30, check=False)
        configs["orquestador-conf"] = r2.stdout or "(no output)"
    except Exception as e:
        configs["orquestador"] = f"ERROR: {e}"
        configs["orquestador-conf"] = f"ERROR: {e}"
    # Real peers
    for p in REAL_PEERS:
        try:
            r = ssh_real(p["host"], "wg", "show", "wg0", timeout=30, check=False)
            configs[p["peer_id"]] = r.stdout or "(no output)"
            r2 = ssh_real(p["host"], "wg", "showconf", "wg0", timeout=30, check=False)
            configs[f"{p['peer_id']}-conf"] = r2.stdout or "(no output)"
        except Exception as e:
            configs[p["peer_id"]] = f"ERROR: {e}"
            configs[f"{p['peer_id']}-conf"] = f"ERROR: {e}"
    # QEMU peers
    for p in QEMU_PEERS:
        try:
            r = qemu_ssh(p["role"], "wg", "show", "wg0", timeout=30)
            configs[p["peer_id"]] = r.stdout or "(no output)"
            r2 = qemu_ssh(p["role"], "wg", "showconf", "wg0", timeout=30)
            configs[f"{p['peer_id']}-conf"] = r2.stdout or "(no output)"
        except Exception as e:
            configs[p["peer_id"]] = f"ERROR: {e}"
            configs[f"{p['peer_id']}-conf"] = f"ERROR: {e}"
    return configs


def run_topology_cycle(topology: str, admin_token: str) -> TopologyResult:
    log(f"\n{'='*60}\n=== TOPOLOGÍA: {topology} ===\n{'='*60}")
    log("Fase 1: Limpieza completa...")
    clean_all_peers(admin_token)
    log("Fase 2: Configurando topología...")
    set_topology(topology)
    log(f"  Topología {topology} configurada")
    log("Fase 3: Iniciando peers...")
    start_all_peers()
    log("Fase 4: Esperando registro...")
    peers = wait_for_all_peers()
    log("Fase 5: Esperando handshakes...")
    wait_for_handshakes()
    time.sleep(5)
    log("Fase 5b: Capturando configuración WireGuard...")
    wg_configs = capture_wg_configs(peers)
    log("Fase 6: Ejecutando pruebas de ping...")
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
            label = f"{src_id[:10]}→{dst_id[:10]}"
            log(f"  Ping {label}...")
            try:
                if src_real:
                    ping_results[src_id][dst_id] = ping_real(src_real[0]["host"], dst_ip)
                elif src_qemu:
                    ping_results[src_id][dst_id] = ping_qemu(src_qemu[0]["role"], dst_ip)
            except Exception as exc:
                log(f"  ERROR en ping {label}: {exc}")
                ping_results[src_id][dst_id] = PingResult(ok=False, avg_ms=None, loss_pct=100.0, ttl=None, raw=str(exc))
        log(f"  Ping desde {src_id}: {sum(1 for r in ping_results[src_id].values() if r.ok)}/{len(ping_results[src_id])} OK")
    log("Fase 7: Midiendo throughput real...")
    tp_results: dict[str, list[ThroughputResult]] = {}
    if len(ip_map) >= 3:
        server_id = REAL_PEERS[0]["peer_id"]
        server_ip = ip_map.get(server_id, "")
        clients = [(REAL_PEERS[1]["peer_id"], REAL_PEERS[1]["host"]), (REAL_PEERS[2]["peer_id"], REAL_PEERS[2]["host"])]
        if server_ip and _has_iperf3(REAL_PEERS[0]["host"]):
            log("  Usando iperf3 para throughput real")
            tp_results["real"] = measure_real_iperf3(REAL_PEERS[0]["host"], server_ip, clients)
        elif server_ip:
            log("  iperf3 no disponible, usando HTTP fallback")
            tp_results["real"] = measure_real_http(REAL_PEERS[0]["host"], server_ip, clients)
    log("Fase 8: Midiendo throughput QEMU...")
    qemu_ids = [p for p in ALL_PEER_IDS if p.startswith("qemu-")]
    qemu_ip_map = {pid: ip_map.get(pid) for pid in qemu_ids if pid in ip_map}
    if len(qemu_ip_map) >= 2:
        server_role = [p["role"] for p in QEMU_PEERS if p["peer_id"] == qemu_ids[0]][0]
        server_ip = qemu_ip_map.get(qemu_ids[0], "")
        if server_ip:
            clients = [(qemu_ids[1], qemu_ids[1])]
            if _has_iperf3(QEMU_PEERS[0]["host"], is_qemu=True):
                log("  Usando iperf3 para throughput QEMU")
                tp_results["qemu"] = measure_qemu_iperf3(server_role, server_ip, clients)
            else:
                log("  iperf3 no disponible en QEMU, usando HTTP fallback")
                tp_results["qemu"] = measure_qemu_http(server_role, server_ip, clients)
    log(f"Topología {topology} completada")
    return TopologyResult(topology=topology, peers=peers, ping_results=ping_results, throughput_results=tp_results, wg_configs=wg_configs)


# ── HTML Rendering ──

def _peer_type(peer_id: str) -> str:
    return "NUBE" if peer_id.startswith("peer-") else "QEMU"


def _peer_label(peer_id: str) -> str:
    return ALL_PEER_LABELS.get(peer_id, peer_id)


def _ping_icon(r: PingResult) -> str:
    if r.ok and r.avg_ms is not None and r.avg_ms < 50:
        return '<span class="ok">OK</span>'
    elif r.ok:
        return '<span class="warn">⚠️ LENTO</span>'
    return '<span class="fail">✗ FALLO</span>'


def _rtt_cell(r: PingResult) -> str:
    if r.ok and r.avg_ms is not None:
        return f'{r.avg_ms:.1f} ms'
    return "—"


def _path_type(src_id: str, dst_id: str) -> str:
    st = _peer_type(src_id)
    dt = _peer_type(dst_id)
    if st == dt and st == "NUBE":
        return "P2P"
    if st == dt and st == "QEMU":
        return "Relay vía hub"
    return "Relay vía hub"


def _ttl_summary(ping_results: dict[str, dict[str, PingResult]]) -> str:
    ttls = set()
    for src in ping_results.values():
        for r in src.values():
            if r.ttl:
                ttls.add(r.ttl)
    if not ttls:
        return "N/A"
    return ", ".join(f"TTL={t}" + (" (P2P)" if t <= 64 else " (relay)") for t in sorted(ttls))


def render_html(timestamp: str, results: list[TopologyResult]) -> str:
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
<title>Reporte Completo de Conectividad — LinkGuard v2</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: #0d1117; color: #c9d1d9; padding: 20px; }
  h1 { color: #58a6ff; font-size: 1.8em; margin-bottom: 5px; }
  h2 { color: #79c0ff; font-size: 1.4em; margin: 25px 0 15px; border-bottom: 1px solid #21262d; padding-bottom: 8px; }
  h3 { color: #c9d1d9; font-size: 1.1em; margin: 20px 0 10px; }
  .meta { color: #8b949e; font-size: 0.9em; margin-bottom: 20px; }
  table { border-collapse: collapse; width: 100%; margin: 10px 0 20px; font-size: 0.85em; }
  th, td { border: 1px solid #30363d; padding: 6px 10px; text-align: center; }
  th { background: #161b22; font-weight: 600; color: #79c0ff; }
  td { background: #0d1117; }
  .ok { color: #3fb950; font-weight: bold; }
  .warn { color: #d29922; font-weight: bold; }
  .fail { color: #f85149; font-weight: bold; }
  .tag-nube { background: #1f6feb33; color: #58a6ff; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }
  .tag-qemu { background: #23863633; color: #3fb950; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }
  .nav { background: #161b22; padding: 12px 16px; border-radius: 8px; margin-bottom: 20px; }
  .nav a { color: #58a6ff; text-decoration: none; margin-right: 15px; }
  .nav a:hover { text-decoration: underline; }
  .section { background: #161b22; border-radius: 8px; padding: 16px; margin-bottom: 20px; border: 1px solid #30363d; }
  .summary-ok { color: #3fb950; }
  .summary-fail { color: #f85149; }
  .summary-partial { color: #d29922; }
  ul { list-style: none; padding: 0; }
  li { padding: 4px 0; }
  .legend { font-size: 0.85em; color: #8b949e; margin-top: 10px; }
  pre { background: #161b22; padding: 12px; border-radius: 6px; overflow-x: auto; font-size: 0.85em; color: #c9d1d9; }
</style>
</head>
<body>
""")
    rows.append(f'<h1>🔗 Reporte Completo de Conectividad</h1>')
    rows.append(f'<p class="meta">Generado el {timestamp} — Orquestador: <code>{ORCH_HOST}</code> — LinkGuard v2</p>')
    rows.append(f'<div class="nav"><a href="#inventario">Inventario de peers</a>')
    for r in results:
        rows.append(f'<a href="#topo-{r.topology}">{r.topology}</a>')
    rows.append(f'<a href="#resumen">Resumen</a><a href="#comandos">Comandos</a></div>')
    rows.append(f'<div class="section" id="inventario"><h2>📋 Inventario de peers</h2><table><tr><th>Peer</th><th>IP túnel</th><th>Endpoint</th><th>NAT</th><th>Tipo</th></tr>')
    for pid in sorted(peers_inventory):
        p = peers_inventory[pid]
        ptype = _peer_type(pid)
        tag = f'<span class="tag-{"nube" if ptype == "NUBE" else "qemu"}">{ptype}</span>'
        rows.append(f'<tr><td>{_peer_label(pid)}</td><td><code>{p.get("ip","")}</code></td><td><code>{p.get("endpoint","")}</code></td><td>{p.get("nat_type","")}</td><td>{tag}</td></tr>')
    rows.append(f'</table><p class="legend">Hub: <code>{ORCH_HOST}:51820</code> — IP túnel: <code>10.20.30.1</code></p></div>')
    for r in results:
        rows.append(f'<div class="section" id="topo-{r.topology}">')
        rows.append(f'<h2>🌐 Topología: <code>{r.topology}</code></h2>')
        total_ok = sum(1 for src in r.ping_results.values() for d in src.values() if d.ok)
        total_pairs = sum(len(src) for src in r.ping_results.values())
        pct = f"{total_ok}/{total_pairs}" if total_pairs else "N/A"
        cls = "summary-ok" if total_pairs > 0 and total_ok == total_pairs else ("summary-partial" if total_ok > 0 else "summary-fail")
        rows.append(f'<p class="{cls}">Ping OK: {pct} — TTLs: {_ttl_summary(r.ping_results)}</p>')
        rows.append(f'<h3>Matriz de conectividad</h3><table><tr><th>Origen \\ Destino</th>')
        all_ids = sorted(r.ping_results.keys())
        for dst_id in all_ids:
            rows.append(f'<th>{_peer_label(dst_id)}</th>')
        rows.append('</tr>')
        for src_id in all_ids:
            rows.append(f'<tr><td><b>{_peer_label(src_id)}</b></td>')
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
                    cls_cell = "ok" if pr.ok else "fail"
                    rows.append(f'<td class="{cls_cell}">{icon}<br><small>{rtt}</small></td>')
            rows.append('</tr>')
        rows.append('</table>')
        rows.append('<h3>Detalle por par</h3><table><tr><th>Origen</th><th>Destino</th><th>Tipo</th><th>RTT (ms)</th><th>Pérdida</th><th>TTL</th><th>Estado</th></tr>')
        for src_id in all_ids:
            for dst_id in all_ids:
                if dst_id == src_id:
                    continue
                pr = r.ping_results.get(src_id, {}).get(dst_id)
                if pr is None:
                    continue
                ptype = _path_type(src_id, dst_id)
                rtt = f'{pr.avg_ms:.1f}' if pr.avg_ms is not None else "—"
                loss = f'{pr.loss_pct:.0f}%'
                ttl = str(pr.ttl) if pr.ttl else "—"
                icon = _ping_icon(pr)
                rows.append(f'<tr><td>{_peer_label(src_id)}</td><td>{_peer_label(dst_id)}</td><td>{ptype}</td><td>{rtt}</td><td>{loss}</td><td>{ttl}</td><td>{icon}</td></tr>')
        rows.append('</table>')
        tp = r.throughput_results
        if tp:
            rows.append('<h3>Throughput</h3><table><tr><th>Tipo</th><th>Cliente</th><th>Velocidad</th><th>Tamaño</th><th>Estado</th></tr>')
            for tp_type, tp_items in tp.items():
                for item in tp_items:
                    cls = "ok" if item.ok else "fail"
                    speed = f'{item.mbps:.2f} Mbps' if item.ok else "—"
                    size = f'{item.size_bytes / 1024 / 1024:.0f} MB' if item.ok else "—"
                    icon = '<span class="ok">OK</span>' if item.ok else '<span class="fail">FALLO</span>'
                    rows.append(f'<tr><td><span class="tag-{"nube" if tp_type == "real" else "qemu"}">{tp_type.upper() if tp_type != "real" else "NUBE"}</span></td><td>{item.peer_id}</td><td>{speed}</td><td>{size}</td><td>{icon}</td></tr>')
            rows.append('</table>')
        wg = r.wg_configs
        if wg:
            rows.append('<h3>🔒 Configuración WireGuard capturada</h3>')
            # Orchestrator
            rows.append('<h4>Orquestador (wg-HUB)</h4>')
            rows.append(f'<pre>{wg.get("orquestador", "N/A")}</pre>')
            rows.append('<h4>Orquestador config (wg-HUB)</h4>')
            rows.append(f'<pre>{wg.get("orquestador-conf", "N/A")}</pre>')
            # Real peers
            for p in REAL_PEERS:
                pid = p["peer_id"]
                rows.append(f'<h4>{_peer_label(pid)} — wg show</h4>')
                rows.append(f'<pre>{wg.get(pid, "N/A")}</pre>')
                rows.append(f'<h4>{_peer_label(pid)} — wg showconf</h4>')
                rows.append(f'<pre>{wg.get(f"{pid}-conf", "N/A")}</pre>')
            # QEMU peers
            for p in QEMU_PEERS:
                pid = p["peer_id"]
                rows.append(f'<h4>{_peer_label(pid)} — wg show</h4>')
                rows.append(f'<pre>{wg.get(pid, "N/A")}</pre>')
                rows.append(f'<h4>{_peer_label(pid)} — wg showconf</h4>')
                rows.append(f'<pre>{wg.get(f"{pid}-conf", "N/A")}</pre>')
        rows.append('</div>')
    rows.append('<div class="section" id="resumen"><h2>📊 Resumen por topología</h2><table><tr><th>Topología</th><th>Ping OK</th><th>RTT mínimo</th><th>RTT promedio</th><th>RTT máximo</th><th>Throughput</th></tr>')
    for r in results:
        all_avgs = [pr.avg_ms for src in r.ping_results.values() for pr in src.values() if pr.ok and pr.avg_ms is not None]
        min_rtt = f'{min(all_avgs):.1f}' if all_avgs else "—"
        avg_rtt = f'{sum(all_avgs) / len(all_avgs):.1f}' if all_avgs else "—"
        max_rtt = f'{max(all_avgs):.1f}' if all_avgs else "—"
        total_ok = sum(1 for src in r.ping_results.values() for pr in src.values() if pr.ok)
        total_pairs = sum(len(src) for src in r.ping_results.values())
        tp_strs = []
        for tp_type, tp_items in r.throughput_results.items():
            speeds = [i.mbps for i in tp_items if i.ok]
            if speeds:
                tp_strs.append(f'{"nube" if tp_type == "real" else tp_type}: {sum(speeds) / len(speeds):.1f} Mbps')
        tp_s = "; ".join(tp_strs) if tp_strs else "—"
        rows.append(f'<tr><td><code>{r.topology}</code></td><td><span class="{"summary-ok" if total_ok == total_pairs else "summary-partial"}">{total_ok}/{total_pairs}</span></td><td>{min_rtt}</td><td>{avg_rtt}</td><td>{max_rtt}</td><td>{tp_s}</td></tr>')
    rows.append('</table></div>')
    rows.append(f'<div class="section" id="comandos"><h2>🔧 Comandos útiles</h2><pre>make qemu-status-real TESTBED_REAL_ORCH_PASS=\'...\' ')
    rows.append(f'make performance-report-all-real TESTBED_REAL_ORCH_PASS=\'...\' ')
    rows.append(f'ping 10.20.30.1  # Hub')
    rows.append(f'ping 10.20.30.2  # 185 nube (46.250.168.185)')
    rows.append(f'ping 10.20.30.3  # 57 nube (122.8.179.57)')
    rows.append(f'ping 10.20.30.4  # 141 nube (46.250.162.141)')
    rows.append(f'ping 10.20.30.5  # qemu-orq')
    rows.append(f'ping 10.20.30.6  # qemu-pa')
    rows.append(f'ping 10.20.30.7  # qemu-pb</pre></div>')
    rows.append('<div class="section" id="diagnostico"><h2>🔍 Diagnóstico de fallas</h2>')
    # Dynamic diagnosis based on actual results
    diag_stats = {}
    for r in results:
        total_ok = sum(1 for src in r.ping_results.values() for pr in src.values() if pr.ok)
        total_pairs = sum(len(src) for src in r.ping_results.values())
        diag_stats[r.topology] = {"ok": total_ok, "total": total_pairs}
    rows.append('<p><b>Resultados de esta corrida:</b></p>')
    rows.append('<table><tr><th>Topología</th><th>Ping OK</th><th>Estado</th></tr>')
    for r in results:
        st = diag_stats[r.topology]
        cls = "summary-ok" if st["ok"] == st["total"] else "summary-partial"
        icon = "✅" if st["ok"] == st["total"] else "⚠️"
        rows.append(f'<tr><td><code>{r.topology}</code></td><td>{st["ok"]}/{st["total"]}</td><td class="{cls}">{icon}</td></tr>')
    rows.append('</table>')
    rows.append('<p><b>Patrón observado:</b> En topologías con P2P (mesh, hub-mesh), el peer <code>46.250.168.185</code> '
                'no puede alcanzar los peers QEMU (10.20.30.5–7), pero los QEMU sí llegan a 185. En hub-spoke no hay fallas porque todo '
                'el tráfico pasa por relay del hub.</p>')
    rows.append('<p><b>Causa raíz — NAT simétrico:</b> Los QEMU están detrás del host local (<code>189.217.195.93</code>) con NAT de puerto dinámico. '
                'El hub conoce el endpoint NAT del QEMU (<code>189.217.195.93:PUERTO_A</code>). Cuando 185 inicia handshake hacia ese endpoint, '
                'el NAT simétrico asigna un puerto diferente (<code>PUERTO_B</code>), el QEMU nunca recibe el paquete → 100% pérdida. '
                'Cuando el QEMU inicia hacia 185, el mapping funciona porque el NAT ya estableció <code>PUERTO_A</code> para esa conversación.</p>')
    rows.append('<p><b>Sugerencia:</b> Rutas explícitas vía hub desde 185 hacia los destinos QEMU en hub-mesh, o port forwarding '
                'UDP fijo en el host local hacia los puertos WireGuard de cada VM QEMU para eliminar la dependencia de NAT simétrico.</p>')
    rows.append('</div>')
    rows.append('</body></html>\n')
    return "\n".join(rows)


def write_jsonl_report(timestamp: str, results: list[TopologyResult]) -> None:
    jsonl_path = ROOT / "docs" / "reporte-rendimiento-historial.jsonl"
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    records = []
    for r in results:
        total_ok = sum(1 for src in r.ping_results.values() for pr in src.values() if pr.ok)
        total_pairs = sum(len(src) for src in r.ping_results.values())
        all_avgs = [pr.avg_ms for src in r.ping_results.values() for pr in src.values() if pr.ok and pr.avg_ms is not None]
        tp_summary = {}
        for tp_type, tp_items in r.throughput_results.items():
            speeds = [i.mbps for i in tp_items if i.ok]
            if speeds:
                tp_summary[tp_type] = {"avg_mbps": round(sum(speeds) / len(speeds), 2), "samples": len(speeds)}
        record = {
            "timestamp": timestamp,
            "topology": r.topology,
            "ping": {"ok": total_ok, "total": total_pairs, "min_rtt_ms": round(min(all_avgs), 2) if all_avgs else None, "avg_rtt_ms": round(sum(all_avgs) / len(all_avgs), 2) if all_avgs else None, "max_rtt_ms": round(max(all_avgs), 2) if all_avgs else None},
            "throughput": tp_summary,
            "peers": list(r.peers.keys()),
        }
        records.append(record)
    with jsonl_path.open("a", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    log(f"Historial JSONL actualizado en {jsonl_path}")


# ── QEMU Testbed ──

def qemu_up() -> bool:
    status = qemu_cmd("status", timeout=120, check=False)
    return all(f"{role}: PID=" in status.stdout and "vivo" in status.stdout for role in ("orq", "pa", "pb"))


def ensure_qemu_testbed() -> bool:
    if qemu_up():
        log("Testbed QEMU ya está levantado")
        return False
    log("Levantando testbed QEMU...")
    env = os.environ.copy()
    env.setdefault("TESTBED_REAL_ORCH_HOST", ORCH_HOST)
    env.setdefault("TESTBED_REAL_ORCH_USER", ORCH_USER)
    env.setdefault("TESTBED_REAL_ORCH_PASS", REMOTE_PASS)
    env.setdefault("TESTBED_REAL_ORCH_URL", REAL_ORCH_URL)
    qemu_cmd("up-real", timeout=1800, check=True, env=env)
    log("Testbed QEMU listo")
    return True


# ── Main ──

def main() -> int:
    parser = argparse.ArgumentParser(description="Genera reporte HTML completo con peers reales + QEMU")
    parser.add_argument("--output", default=str(REPORT_PATH))
    parser.add_argument("--skip-qemu", action="store_true")
    parser.add_argument("--skip-throughput", action="store_true")
    parser.add_argument("--skip-clean", action="store_true")
    args = parser.parse_args()

    if not REMOTE_PASS:
        print("ERROR: Define LINKGUARD_REMOTE_PASS o TESTBED_REAL_ORCH_PASS", file=sys.stderr)
        return 1

    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    ts_slug = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")
    if args.output == str(REPORT_PATH):
        output_path = ROOT / "docs" / f"reporte-html-{ts_slug}.html"
    else:
        output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    admin_token = get_admin_token()
    log(f"ADMIN_TOKEN obtenido: {admin_token[:16]}...")

    qemu_started = False
    if not args.skip_qemu:
        qemu_started = ensure_qemu_testbed()

    original_topology = get_current_topology()
    log(f"Topología actual: {original_topology}")

    results: list[TopologyResult] = []

    try:
        for topology in TOPOLOGIES:
            result = run_topology_cycle(topology, admin_token)
            results.append(result)

        log(f"\n{'='*60}\n=== GENERANDO REPORTE HTML ===\n{'='*60}")
        set_topology(original_topology)
        html = render_html(timestamp, results)
        output_path.write_text(html)
        log(f"Reporte generado en {output_path}")
        # Write JSONL history
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


if __name__ == "__main__":
    sys.exit(main())
