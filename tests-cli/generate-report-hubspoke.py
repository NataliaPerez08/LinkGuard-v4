#!/usr/bin/env python3
"""Genera reporte HTML para topologia hub-spoke via CLI (orch-cli.py)."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TESTBED_SCRIPT = ROOT / "testbed" / "scripts" / "launch-testbed.py"
REPORT_PATH = ROOT / "docs" / "reports" / "cli" / "hub-spoke" / "latest.html"

ORCH_HOST = os.environ.get("TESTBED_REAL_ORCH_HOST", "101.44.24.91")
ORCH_USER = os.environ.get("TESTBED_REAL_ORCH_USER", "root")
REMOTE_PASS = os.environ.get("LINKGUARD_REMOTE_PASS") or os.environ.get("TESTBED_REAL_ORCH_PASS", "")
REAL_ORCH_URL = os.environ.get("TESTBED_REAL_ORCH_URL", f"http://{ORCH_HOST}:8000/RPC2")
QEMU_PASS = "linkguard-test"
TERMINAL_PASS = "alpine123"
TERMINAL_JUMP = "root@100.115.215.49"
TERMINAL_HOST = "172.20.0.40"
SSH_OPTS = ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null", "-o", "ConnectTimeout=5"]
TOPOLOGIES = ["hub-spoke"]
HUB_WG_IFACE = "wg-HUB"

REAL_PEERS = [
    {"peer_id": "peer-46-250-168-185", "host": "46.250.168.185", "label": "185 nube (46.250.168.185)"},
    {"peer_id": "peer-122-8-179-57", "host": "122.8.179.57", "label": "57 nube (122.8.179.57)"},
    {"peer_id": "peer-46-250-162-141", "host": "46.250.162.141", "label": "141 nube (46.250.162.141)"},
    {"peer_id": "peer-172-20-0-40", "host": TERMINAL_HOST, "label": "40 vm (172.20.0.40)", "is_terminal": True},
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


def ssh_terminal(*remote_cmd: str, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return run(["sshpass", "-p", TERMINAL_PASS, "ssh", *SSH_OPTS, "-J", TERMINAL_JUMP, f"root@{TERMINAL_HOST}", *remote_cmd], timeout=timeout, check=False)


def ssh_terminal_script(script: str, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["sshpass", "-p", TERMINAL_PASS, "ssh", *SSH_OPTS, "-J", TERMINAL_JUMP, f"root@{TERMINAL_HOST}", "sh"],
        input=script, text=True, capture_output=True, timeout=timeout, check=False,
    )


def qemu_cmd(*args: str, timeout: int = 120, check: bool = False, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return run(["python3", str(TESTBED_SCRIPT), *args], timeout=timeout, check=check, env=env)


def qemu_ssh(role: str, *cmd: str, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return qemu_cmd("ssh", role, *cmd, timeout=timeout)


def qemu_ssh_script(role: str, script: str, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    host = [p["host"] for p in QEMU_PEERS if p["role"] == role][0]
    return subprocess.run(
        ["sshpass", "-p", QEMU_PASS, "ssh", *SSH_OPTS, f"root@{host}", "sh"],
        input=script, text=True, capture_output=True, timeout=timeout, check=False,
    )
ORCH_CLI = str(ROOT / "orchestrator-install-v2" / "orch-cli.py")

# ── ORCH CLI wrapper ──

_admin_token = ""  # seteado en main()

def orch_cli(*args: str, admin_token: str = "", timeout: int = 120) -> dict[str, Any]:
    """Ejecuta orch-cli.py localmente apuntando al orquestador remoto via --url."""
    token = admin_token or _admin_token
    cmd = ["python3", ORCH_CLI, "--url", REAL_ORCH_URL]
    cmd.extend(args)
    if token:
        cmd.extend(["--admin-token", token])
    result = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, check=False)
    out = (result.stdout or "").strip()
    if not out:
        return {}
    try:
        return json.loads(out) if isinstance(json.loads(out), dict) else {}
    except json.JSONDecodeError:
        return {"_raw": out}




def get_admin_token() -> str:
    result = ssh_real(ORCH_HOST, "cat", "/etc/linkguard/secrets", timeout=120, check=True)
    for line in result.stdout.splitlines():
        if line.startswith("ADMIN_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("No encontre ADMIN_TOKEN en /etc/linkguard/secrets")


def log(msg: str) -> None:
    print(f"[reporte] {msg}", flush=True)


# ── Peer listing ──

def peer_list() -> dict[str, Any]:
    return orch_cli("peer-list").get("peers", {})


def get_current_topology() -> str:
    data = orch_cli("net-topology", "default")
    return str(data.get("topology") or "hub-spoke")


def set_topology(topology: str) -> None:
    orch_cli("net-set-topology", "default", topology)


# ── Cleanup ──

def peer_unregister(peer_id: str, admin_token: str) -> bool:
    """peer.unregister via CLI (--admin-token)."""
    try:
        r = orch_cli("peer-unregister", peer_id, admin_token=admin_token)
        return bool(r.get("_raw") or r)
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


def clean_terminal_peer() -> None:
    script = """set -e
rc-service wg-auto-register stop 2>/dev/null || true
killall -9 wg-auto-register.py 2>/dev/null || true
rm -f /etc/wireguard/wg0.conf /etc/wireguard/wg0.key /etc/wireguard/wg0.pub /etc/linkguard/wg-auto.json /etc/wireguard/wg-auto.json
ip link delete wg0 2>/dev/null || true
"""
    ssh_terminal_script(script, timeout=60)


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
        if p.get("is_terminal"):
            clean_terminal_peer()
        else:
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


def start_terminal_peer() -> None:
    ssh_terminal_script("""set -e
rc-service wg-auto-register stop 2>/dev/null || true
killall -9 wg-auto-register.py 2>/dev/null || true
rc-service wg-auto-register start
""", timeout=180)


def start_qemu_peer(role: str) -> None:
    qemu_ssh_script(role, """set -e
rc-service wg-auto-register stop 2>/dev/null || true
killall -9 wg-auto-register.py 2>/dev/null || true
rc-service wg-auto-register start
""", timeout=180)


def start_all_peers() -> None:
    log("Iniciando peers reales...")
    for p in REAL_PEERS:
        if p.get("is_terminal"):
            start_terminal_peer()
        else:
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


def ping_terminal(target: str, count: int = 5) -> PingResult:
    result = ssh_terminal("ping", "-n", "-c", str(count), "-W", "2", target, timeout=180)
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
                results.append(ThroughputResult(peer_id=peer_id, mbps=best_mbps, size_bytes=0, time_sec=duration, ok=True))
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
                results.append(ThroughputResult(peer_id=peer_id, mbps=best_mbps, size_bytes=0, time_sec=duration, ok=True))
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
                log(f"  QEMU throughput error for {peer_id}: stdout={out!r} stderr={r.stderr!r}")
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
    try:
        r = ssh_real(ORCH_HOST, "wg", "show", HUB_WG_IFACE, timeout=30, check=False)
        configs["orquestador"] = r.stdout or "(no output)"
        r2 = ssh_real(ORCH_HOST, "wg", "showconf", HUB_WG_IFACE, timeout=30, check=False)
        configs["orquestador-conf"] = r2.stdout or "(no output)"
    except Exception as e:
        configs["orquestador"] = f"ERROR: {e}"
        configs["orquestador-conf"] = f"ERROR: {e}"
    for p in REAL_PEERS:
        try:
            if p.get("is_terminal"):
                r = ssh_terminal("wg", "show", "wg0", timeout=30)
                configs[p["peer_id"]] = r.stdout or "(no output)"
                r2 = ssh_terminal("wg", "showconf", "wg0", timeout=30)
                configs[f"{p['peer_id']}-conf"] = r2.stdout or "(no output)"
            else:
                r = ssh_real(p["host"], "wg", "show", "wg0", timeout=30, check=False)
                configs[p["peer_id"]] = r.stdout or "(no output)"
                r2 = ssh_real(p["host"], "wg", "showconf", "wg0", timeout=30, check=False)
                configs[f"{p['peer_id']}-conf"] = r2.stdout or "(no output)"
        except Exception as e:
            configs[p["peer_id"]] = f"ERROR: {e}"
            configs[f"{p['peer_id']}-conf"] = f"ERROR: {e}"
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
    log(f"\n{'='*60}\n=== TOPOLOGIA: {topology} ===\n{'='*60}")
    log("Fase 1: Limpieza completa...")
    clean_all_peers(admin_token)
    log("Fase 2: Configurando topologia...")
    set_topology(topology)
    log(f"  Topologia {topology} configurada")
    log("Fase 3: Iniciando peers...")
    start_all_peers()
    log("Fase 4: Esperando registro...")
    peers = wait_for_all_peers()
    log("Fase 5: Esperando handshakes...")
    wait_for_handshakes()
    time.sleep(5)
    log("Fase 5b: Capturando configuracion WireGuard...")
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
            label = f"{src_id[:10]}->{dst_id[:10]}"
            log(f"  Ping {label}...")
            try:
                if src_real:
                    p = src_real[0]
                    if p.get("is_terminal"):
                        ping_results[src_id][dst_id] = ping_terminal(dst_ip)
                    else:
                        ping_results[src_id][dst_id] = ping_real(p["host"], dst_ip)
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
        # Exclude terminal peer from iperf3 (needs internet)
        normal_clients = []
        for p in REAL_PEERS[1:]:
            if p.get("is_terminal"):
                continue
            if p["peer_id"] != server_id:
                normal_clients.append((p["peer_id"], p["host"]))
        if server_ip and _has_iperf3(REAL_PEERS[0]["host"]):
            log("  Usando iperf3 para throughput real")
            tp_results["real"] = measure_real_iperf3(REAL_PEERS[0]["host"], server_ip, normal_clients)
        elif server_ip:
            log("  iperf3 no disponible, usando HTTP fallback")
            tp_results["real"] = measure_real_http(REAL_PEERS[0]["host"], server_ip, normal_clients)
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
    log(f"Topologia {topology} completada")
    return TopologyResult(topology=topology, peers=peers, ping_results=ping_results, throughput_results=tp_results, wg_configs=wg_configs)


# ── HTML Rendering ──

def _peer_type(peer_id: str) -> str:
    if peer_id == "peer-172-20-0-40":
        return "VM"
    return "NUBE" if peer_id.startswith("peer-") else "QEMU"


def _peer_label(peer_id: str) -> str:
    return ALL_PEER_LABELS.get(peer_id, peer_id)


def _ping_icon(r: PingResult) -> str:
    if r.ok and r.avg_ms is not None and r.avg_ms < 50:
        return '<span class="ok">OK</span>'
    elif r.ok:
        return '<span class="warn">\u26a0 LENTO</span>'
    elif r.loss_pct >= 80:
        return '<span class="fail">\u2717 FALLO</span>'
    else:
        return '<span class="partial">\u26a0 PARCIAL</span>'


def _rtt_cell(r: PingResult) -> str:
    if r.ok and r.avg_ms is not None:
        return f'{r.avg_ms:.1f} ms'
    return "\u2014"


def _path_type(src_id: str, dst_id: str) -> str:
    st = _peer_type(src_id)
    dt = _peer_type(dst_id)
    if st == dt and st == "NUBE":
        return "P2P"
    if st == dt and st == "QEMU":
        return "Relay via hub"
    if st == "VM" or dt == "VM":
        return "Relay via hub"
    return "Relay via hub"


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
<title>Reporte Hub-Spoke vía CLI \u2014 LinkGuard v2</title>
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
  .tag-qemu { background: #23863633; color: #3fb950; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }
  .tag-vm { background: #6e40c933; color: #d2a8ff; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }
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
<h1>Reporte Hub-Spoke vía CLI \u2014 LinkGuard v2</h1>
<p>Generado: <code>""" + timestamp + """</code> | Orquestador: <code>""" + ORCH_HOST + """</code></p>
<p>Peers: """ + str(len(REAL_PEERS)) + """ nube/vm + """ + str(len(QEMU_PEERS)) + """ QEMU (total """ + str(len(ALL_PEER_IDS)) + """)</p>
""")

    rows.append(f'<div class="section" id="inventario"><h2>Inventario de peers</h2><table><tr><th>Peer</th><th>IP tunel</th><th>Endpoint</th><th>NAT</th><th>Tipo</th></tr>')
    for pid in sorted(peers_inventory):
        p = peers_inventory[pid]
        ptype = _peer_type(pid)
        tag_cls = {"NUBE": "tag-nube", "QEMU": "tag-qemu", "VM": "tag-vm"}.get(ptype, "tag-nube")
        tag = f'<span class="{tag_cls}">{ptype}</span>'
        rows.append(f'<tr><td>{_peer_label(pid)}</td><td><code>{p.get("ip","")}</code></td><td><code>{p.get("endpoint","")}</code></td><td>{p.get("nat_type","")}</td><td>{tag}</td></tr>')
    rows.append(f'</table><p class="legend">Hub: <code>{ORCH_HOST}:51820</code> \u2014 IP tunel: <code>10.20.30.1</code></p></div>')
    for r in results:
        rows.append(f'<div class="section" id="topo-{r.topology}">')
        rows.append(f'<h2>Topologia: <code>{r.topology}</code></h2>')
        total_ok = sum(1 for src in r.ping_results.values() for d in src.values() if d.ok)
        total_pairs = sum(len(src) for src in r.ping_results.values())
        pct = f"{total_ok}/{total_pairs}" if total_pairs else "N/A"
        cls = "summary-ok" if total_pairs > 0 and total_ok == total_pairs else ("summary-partial" if total_ok > 0 else "summary-fail")
        rows.append(f'<p class="{cls}">Ping OK: {pct} \u2014 TTLs: {_ttl_summary(r.ping_results)}</p>')
        rows.append(f'<h3>Matriz de conectividad</h3><table><tr><th>Origen \\ Destino</th>')
        all_ids = sorted(r.ping_results.keys())
        for dst_id in all_ids:
            ip = peers_inventory.get(dst_id, {}).get("ip", "")
            rows.append(f'<th>{_peer_label(dst_id)}<br><small><code>{ip}</code></small></th>')
        rows.append('</tr>')
        for src_id in all_ids:
            ip = peers_inventory.get(src_id, {}).get("ip", "")
            rows.append(f'<tr><td><b>{_peer_label(src_id)}</b><br><small><code>{ip}</code></small></td>')
            for dst_id in all_ids:
                if dst_id == src_id:
                    rows.append('<td>\u2014</td>')
                    continue
                pr = r.ping_results.get(src_id, {}).get(dst_id)
                if pr is None:
                    rows.append('<td class="fail">\u2014</td>')
                else:
                    icon = _ping_icon(pr)
                    rtt = _rtt_cell(pr)
                    if pr.ok:
                        cls_cell = "ok"
                    elif pr.loss_pct >= 80:
                        cls_cell = "fail"
                    else:
                        cls_cell = "partial"
                    rows.append(f'<td class="{cls_cell}">{icon}<br><small>{rtt}</small></td>')
            rows.append('</tr>')
        rows.append('</table>')
        rows.append('<h3>Detalle por par</h3><table><tr><th>Origen</th><th>Destino</th><th>Tipo</th><th>RTT (ms)</th><th>Perdida</th><th>TTL</th><th>Estado</th></tr>')
        for src_id in all_ids:
            for dst_id in all_ids:
                if dst_id == src_id:
                    continue
                pr = r.ping_results.get(src_id, {}).get(dst_id)
                if pr is None:
                    continue
                ptype = _path_type(src_id, dst_id)
                rtt = f'{pr.avg_ms:.1f}' if pr.avg_ms is not None else "\u2014"
                loss = f'{pr.loss_pct:.0f}%'
                ttl = str(pr.ttl) if pr.ttl else "\u2014"
                icon = _ping_icon(pr)
                ip_src = peers_inventory.get(src_id, {}).get("ip", "")
                ip_dst = peers_inventory.get(dst_id, {}).get("ip", "")
                rows.append(f'<tr><td>{_peer_label(src_id)}<br><small><code>{ip_src}</code></small></td><td>{_peer_label(dst_id)}<br><small><code>{ip_dst}</code></small></td><td>{ptype}</td><td>{rtt}</td><td>{loss}</td><td>{ttl}</td><td>{icon}</td></tr>')
        rows.append('</table>')
        tp = r.throughput_results
        if tp:
            rows.append('<h3>Throughput</h3><table><tr><th>Tipo</th><th>Cliente</th><th>Velocidad</th><th>Tamanio</th><th>Estado</th></tr>')
            for tp_type, tp_items in tp.items():
                for item in tp_items:
                    cls = "ok" if item.ok else "fail"
                    speed = f'{item.mbps:.2f} Mbps' if item.ok else "\u2014"
                    size = f'{item.size_bytes / 1024 / 1024:.0f} MB' if item.ok else "\u2014"
                    icon = '<span class="ok">OK</span>' if item.ok else '<span class="fail">FALLO</span>'
                    tp_label = tp_type.upper() if tp_type != "real" else "NUBE"
                    rows.append(f'<tr><td><span class="tag-nube">{tp_label}</span></td><td>{item.peer_id}</td><td>{speed}</td><td>{size}</td><td>{icon}</td></tr>')
            rows.append('</table>')
        wg = r.wg_configs
        if wg:
            rows.append('<h3>Configuracion WireGuard capturada</h3>')
            rows.append('<h4>Orquestador (wg-HUB)</h4>')
            rows.append(f'<pre>{wg.get("orquestador", "N/A")}</pre>')
            rows.append('<h4>Orquestador config (wg-HUB)</h4>')
            rows.append(f'<pre>{wg.get("orquestador-conf", "N/A")}</pre>')
            for p in REAL_PEERS:
                pid = p["peer_id"]
                rows.append(f'<h4>{_peer_label(pid)} \u2014 wg show</h4>')
                rows.append(f'<pre>{wg.get(pid, "N/A")}</pre>')
                rows.append(f'<h4>{_peer_label(pid)} \u2014 wg showconf</h4>')
                rows.append(f'<pre>{wg.get(f"{pid}-conf", "N/A")}</pre>')
            for p in QEMU_PEERS:
                pid = p["peer_id"]
                rows.append(f'<h4>{_peer_label(pid)} \u2014 wg show</h4>')
                rows.append(f'<pre>{wg.get(pid, "N/A")}</pre>')
                rows.append(f'<h4>{_peer_label(pid)} \u2014 wg showconf</h4>')
                rows.append(f'<pre>{wg.get(f"{pid}-conf", "N/A")}</pre>')
        rows.append('</div>')
    rows.append('<div class="section" id="resumen"><h2>Resumen por topologia</h2><table><tr><th>Topologia</th><th>Ping OK</th><th>RTT minimo</th><th>RTT promedio</th><th>RTT maximo</th><th>Throughput</th></tr>')
    for r in results:
        all_avgs = [pr.avg_ms for src in r.ping_results.values() for pr in src.values() if pr.ok and pr.avg_ms is not None]
        min_rtt = f'{min(all_avgs):.1f}' if all_avgs else "\u2014"
        avg_rtt = f'{sum(all_avgs) / len(all_avgs):.1f}' if all_avgs else "\u2014"
        max_rtt = f'{max(all_avgs):.1f}' if all_avgs else "\u2014"
        total_ok = sum(1 for src in r.ping_results.values() for pr in src.values() if pr.ok)
        total_pairs = sum(len(src) for src in r.ping_results.values())
        tp_strs = []
        for tp_type, tp_items in r.throughput_results.items():
            speeds = [i.mbps for i in tp_items if i.ok]
            if speeds:
                tp_strs.append(f'{"nube" if tp_type == "real" else tp_type}: {sum(speeds) / len(speeds):.1f} Mbps')
        tp_s = "; ".join(tp_strs) if tp_strs else "\u2014"
        rows.append(f'<tr><td><code>{r.topology}</code></td><td><span class="{"summary-ok" if total_ok == total_pairs else "summary-partial"}">{total_ok}/{total_pairs}</span></td><td>{min_rtt}</td><td>{avg_rtt}</td><td>{max_rtt}</td><td>{tp_s}</td></tr>')
    rows.append('</table></div>')
    rows.append('<div class="section" id="diagnostico"><h2>Diagnostico de fallas</h2>')
    diag_stats = {}
    for r in results:
        total_ok = sum(1 for src in r.ping_results.values() for pr in src.values() if pr.ok)
        total_pairs = sum(len(src) for src in r.ping_results.values())
        diag_stats[r.topology] = {"ok": total_ok, "total": total_pairs}
    rows.append('<p><b>Resultados de esta corrida:</b></p>')
    rows.append('<table><tr><th>Topologia</th><th>Ping OK</th><th>Estado</th></tr>')
    for r in results:
        st = diag_stats[r.topology]
        cls = "summary-ok" if st["ok"] == st["total"] else "summary-partial"
        icon = "\u2705" if st["ok"] == st["total"] else "\u26a0\ufe0f"
        rows.append(f'<tr><td><code>{r.topology}</code></td><td>{st["ok"]}/{st["total"]}</td><td class="{cls}">{icon}</td></tr>')
    rows.append('</table>')
    rows.append('<p><b>Diagnostico por topologia:</b></p>')
    for r in results:
        all_entries = [(s, d, p) for s in r.ping_results for d, p in r.ping_results[s].items()]
        partial = [(s, d, p) for s, d, p in all_entries if not p.ok and p.loss_pct < 80]
        failed = [(s, d, p) for s, d, p in all_entries if not p.ok and p.loss_pct >= 80]
        ok_count = sum(1 for _, _, p in all_entries if p.ok)
        rows.append(f'<p><b>{r.topology}:</b> {ok_count} rutas OK, {len(partial)} con perdida parcial (&lt;80%), {len(failed)} con perdida &ge;80%.</p>')
        if partial:
            src_loss: dict[str, list[tuple[str, float]]] = {}
            for s, d, p in partial:
                src_loss.setdefault(s, []).append((d, p.loss_pct))
            worst_src = max(src_loss, key=lambda s: len(src_loss[s]))
            rows.append(f'<p>Perdida parcial en {len(partial)} pares, origen mas afectado: <code>{worst_src}</code>. Causa probable: congestion del hub como relay bajo trafico concurrente de todos los peers, o buffers de kernel WireGuard saturados por multiplexacion de handshakes.</p>')
        if failed:
            dst_qemu = [d for s, d, p in failed if d.startswith('qemu-')]
            dst_terminal = [d for s, d, p in failed if d == 'peer-172-20-0-40' or s == 'peer-172-20-0-40']
            if dst_terminal:
                rows.append('<p><b>Nueva terminal (172.20.0.40):</b> Esta VM esta detras de un jump-host y podria no tener conectividad directa al orquestador (101.44.24.91). Verificar ruta de red y NAT en el jump-host 100.115.215.49.</p>')
            if dst_qemu:
                rows.append('<p><b>Fallos hacia QEMU \u2014 NAT simetrico:</b> Los QEMU estan detras del host local con NAT de puerto dinamico. El hub conoce el endpoint NAT del QEMU (<code>HOST:PUERTO_A</code>). Al iniciar handshake hacia ese endpoint, el NAT simetrico asigna un puerto diferente (<code>PUERTO_B</code>) y el QEMU nunca recibe el paquete \u2192 100% perdida.</p>')
        if not partial and not failed:
            rows.append('<p>Todos los pares con 0% perdida. Conectividad completa en esta topologia.</p>')
    rows.append('<p><b>Sugerencia:</b> Rutas explicitas via hub desde nubes hacia los destinos QEMU, o port forwarding UDP fijo en el host local hacia los puertos WireGuard de cada VM QEMU para eliminar la dependencia de NAT simetrico.</p>')
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
        log("Testbed QEMU ya esta levantado")
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
    parser = argparse.ArgumentParser(description="Genera reporte HTML para topologia hub-spoke (4 nubes/vm + 3 QEMU)")
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
        date_dir = ts_slug[:4] + "-" + ts_slug[4:6] + "-" + ts_slug[6:8]
        output_path = ROOT / "docs" / "reports" / "cli" / "hub-spoke" / date_dir / f"reporte-hubspoke-{ts_slug}.html"
    else:
        output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    admin_token = get_admin_token()
    global _admin_token
    _admin_token = admin_token
    log(f"ADMIN_TOKEN obtenido: {admin_token[:16]}...")

    qemu_started = False
    if not args.skip_qemu:
        qemu_started = ensure_qemu_testbed()

    original_topology = get_current_topology()
    log(f"Topologia actual: {original_topology}")

    results: list[TopologyResult] = []

    try:
        result = run_topology_cycle("hub-spoke", admin_token)
        results.append(result)

        log(f"\n{'='*60}\n=== GENERANDO REPORTE HTML ===\n{'='*60}")
        set_topology(original_topology)
        html = render_html(timestamp, results)
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


if __name__ == "__main__":
    sys.exit(main())
