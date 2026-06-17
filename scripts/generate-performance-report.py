#!/usr/bin/env python3
"""Genera el reporte de conectividad y rendimiento por topología soportada."""

from __future__ import annotations

import argparse
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


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "docs" / "reporte-rendimiento-conectividad.md"
HISTORY_PATH = ROOT / "docs" / "reporte-rendimiento-historial.md"
TESTBED_SCRIPT = ROOT / "testbed" / "scripts" / "launch-testbed.py"

ORCH_HOST = os.environ.get("TESTBED_REAL_ORCH_HOST", "101.44.24.91")
ORCH_USER = os.environ.get("TESTBED_REAL_ORCH_USER", "root")
REMOTE_PASS = os.environ.get("LINKGUARD_REMOTE_PASS") or os.environ.get("TESTBED_REAL_ORCH_PASS", "")
REAL_ORCH_URL = os.environ.get("TESTBED_REAL_ORCH_URL", f"http://{ORCH_HOST}:8000/RPC2")
QEMU_PASS = "linkguard-test"
SSH_OPTS = ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null", "-o", "ConnectTimeout=5"]
TOPOLOGIES = ["hub-spoke", "mesh", "hub-mesh"]

REAL_PEERS = {
    "peer-46-250-168-185": {"host": "46.250.168.185", "label": "peer-46-250-168-185"},
    "peer-122-8-179-57": {"host": "122.8.179.57", "label": "peer-122-8-179-57"},
    "peer-46-250-162-141": {"host": "46.250.162.141", "label": "peer-46-250-162-141"},
}

QEMU_PEERS = {
    "qemu-orq": {"role": "orq", "host": "192.168.100.10"},
    "qemu-pa": {"role": "pa", "host": "192.168.100.20"},
    "qemu-pb": {"role": "pb", "host": "192.168.100.30"},
}


@dataclass
class PingResult:
    ok: bool
    avg_ms: float | None
    raw: str


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
            input=script,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        if last.returncode == 0:
            return last
        time.sleep(2)
    if check:
        raise RuntimeError(f"Remote script failed ({last.returncode if last else 'n/a'}) on {host}\n{last.stdout if last else ''}\n{last.stderr if last else ''}")
    assert last is not None
    return last


def ssh_qemu(host: str, *remote_cmd: str, timeout: int = 120, check: bool = False) -> subprocess.CompletedProcess[str]:
    return sshpass_run(QEMU_PASS, f"root@{host}", *remote_cmd, timeout=timeout, check=check)


def ssh_qemu_script(host: str, script: str, *, timeout: int = 120, check: bool = False) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["sshpass", "-p", QEMU_PASS, "ssh", *SSH_OPTS, f"root@{host}", "sh"],
        input=script,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"Remote QEMU script failed ({result.returncode}) on {host}\n{result.stdout}\n{result.stderr}")
    return result


def qemu_cmd(*args: str, timeout: int = 120, check: bool = False, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return run(["python3", str(TESTBED_SCRIPT), *args], timeout=timeout, check=check, env=env)


def rpc() -> xmlrpc.client.ServerProxy:
    return xmlrpc.client.ServerProxy(REAL_ORCH_URL, allow_none=True)


def get_admin_token() -> str:
    result = ssh_real(ORCH_HOST, "cat", "/etc/linkguard/secrets", timeout=120, check=True)
    for line in result.stdout.splitlines():
        if line.startswith("ADMIN_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("No encontré ADMIN_TOKEN en /etc/linkguard/secrets")


def get_orchestrator_snapshot(admin_token: str) -> dict:
    client = rpc()
    health = client.__getattr__("orch.health")()
    peers = client.__getattr__("peer.list")().get("peers", {})
    return {"health": health, "peers": peers}


def get_current_topology() -> str:
    data = rpc().__getattr__("network.get_topology")("default")
    return str(data.get("topology") or "hub-spoke")


def set_topology(topology: str) -> None:
    rpc().__getattr__("network.set_topology")("default", topology)


def parse_ping_output(output: str) -> PingResult:
    ok = bool(re.search(r"(?<![0-9])0% packet loss", output))
    patterns = [
        r"rtt min/avg/max(?:/mdev)? = ([0-9.]+)/([0-9.]+)/([0-9.]+)/[0-9.]+",
        r"round-trip min/avg/max(?:/[a-z]+)? = ([0-9.]+)/([0-9.]+)/([0-9.]+)",
        r"min/avg/max(?:/[a-z]+)? = ([0-9.]+)/([0-9.]+)/([0-9.]+)",
    ]
    match = None
    for pattern in patterns:
        match = re.search(pattern, output)
        if match:
            break
    avg = float(match.group(2)) if match else None
    if avg is None:
        samples = [float(x) for x in re.findall(r"time\s*=\s*([0-9.]+)\s*ms", output)]
        if samples:
            avg = sum(samples) / len(samples)
    if avg is None:
        samples = [float(x) for x in re.findall(r"time[=<]\s*([0-9.]+)\s*ms?", output)]
        if samples:
            avg = sum(samples) / len(samples)
    return PingResult(ok=ok, avg_ms=avg, raw=output)


def ping_real(host: str, target: str, count: int = 5) -> PingResult:
    result = ssh_real(host, "ping", "-n", "-c", str(count), "-W", "2", target, timeout=180, check=False)
    parsed = parse_ping_output((result.stdout or "") + (result.stderr or ""))
    if parsed.ok and parsed.avg_ms is None:
        retry = ssh_real(host, "ping", "-n", "-c", str(count), "-W", "2", target, timeout=180, check=False)
        parsed = parse_ping_output((retry.stdout or "") + (retry.stderr or ""))
    return parsed


def ping_qemu(role: str, target: str, count: int = 10) -> PingResult:
    base_args = ["ssh", role, "ping", "-n", "-c", str(count), "-W", "5", target]
    result = qemu_cmd(*base_args, timeout=180, check=False)
    parsed = parse_ping_output((result.stdout or "") + (result.stderr or ""))
    if parsed.ok and parsed.avg_ms is None:
        retry = qemu_cmd(*base_args, timeout=180, check=False)
        parsed = parse_ping_output((retry.stdout or "") + (retry.stderr or ""))
    if parsed.ok and parsed.avg_ms is None:
        heavy_args = ["ssh", role, "ping", "-n", "-c", "20", "-W", "10", target]
        heavy = qemu_cmd(*heavy_args, timeout=300, check=False)
        parsed = parse_ping_output((heavy.stdout or "") + (heavy.stderr or ""))
    return parsed


def qemu_up() -> bool:
    status = qemu_cmd("status", timeout=120, check=False)
    return all(f"{role}: PID=" in status.stdout and "vivo" in status.stdout for role in ("orq", "pa", "pb"))


def ensure_qemu_integrated() -> bool:
    if qemu_up():
        return False
    env = os.environ.copy()
    env.setdefault("TESTBED_REAL_ORCH_HOST", ORCH_HOST)
    env.setdefault("TESTBED_REAL_ORCH_USER", ORCH_USER)
    env.setdefault("TESTBED_REAL_ORCH_PASS", REMOTE_PASS)
    env.setdefault("TESTBED_REAL_ORCH_URL", REAL_ORCH_URL)
    qemu_cmd("up-real", timeout=1800, check=True, env=env)
    return True


def restart_real_peers() -> None:
    for cfg in REAL_PEERS.values():
        ssh_real(cfg["host"], "systemctl", "restart", "wg-auto-register", timeout=180, check=False)


def restart_qemu_peers() -> None:
    for cfg in QEMU_PEERS.values():
        qemu_cmd("ssh", cfg["role"], "rc-service", "wg-auto-register", "restart", timeout=180, check=False)


def wait_for_stabilization(seconds: int = 12) -> None:
    time.sleep(seconds)


def measure_http_throughput_generic(script_runner, server_host: str, server_ip: str, client_hosts: list[tuple[str, str]], *, file_size_mb: int, port: str, client_builder) -> list[dict]:
    remote_file = f"/tmp/wg-perf-{file_size_mb}m.bin"
    remote_pid = "/tmp/wg-http.pid"
    setup = f"""
kill $(cat {remote_pid}) 2>/dev/null || true
rm -f {remote_pid} {remote_file}
dd if=/dev/zero of={remote_file} bs=1M count={file_size_mb} status=none
nohup python3 -m http.server {port} --bind {server_ip} --directory /tmp >/tmp/wg-http.log 2>&1 &
echo $! > {remote_pid}
"""
    script_runner(server_host, setup, timeout=180, check=True)
    time.sleep(2)
    results = []
    try:
        for peer_id, host in client_hosts:
            out = ""
            last_error = None
            for _ in range(3):
                try:
                    out = script_runner(host, client_builder(peer_id, server_ip, port, Path(remote_file).name), timeout=180, check=True).stdout.strip()
                    last_error = None
                    break
                except Exception as exc:
                    last_error = exc
                    time.sleep(2)
            if last_error is not None:
                raise last_error
            parts = out.split()
            if len(parts) < 5:
                raise RuntimeError(f"Salida inesperada de descarga en {host}: {out!r}")
            speed = int(float(parts[4]))
            results.append({
                "peer_id": parts[0],
                "http": int(parts[1]),
                "size_download": int(parts[2]),
                "time_total": float(parts[3]),
                "speed_download": speed,
                "mbps": round((speed * 8) / 1_000_000, 2),
            })
    finally:
        cleanup = f"kill $(cat {remote_pid}) 2>/dev/null || true\nrm -f {remote_pid} {remote_file}\n"
        script_runner(server_host, cleanup, timeout=120, check=False)
    return results


def measure_real_throughput(server_host: str, server_ip: str, client_hosts: list[tuple[str, str]]) -> list[dict]:
    def curl_builder(peer_id: str, server_ip: str, port: str, filename: str) -> str:
        return f"""
curl -m 60 -s -o /dev/null \
  -w '{peer_id} %{{http_code}} %{{size_download}} %{{time_total}} %{{speed_download}}\\n' \
  http://{server_ip}:{port}/{filename}
"""

    return measure_http_throughput_generic(ssh_real_script, server_host, server_ip, client_hosts, file_size_mb=8, port="8082", client_builder=curl_builder)


def measure_qemu_throughput(server_host: str, server_ip: str, client_hosts: list[tuple[str, str]]) -> list[dict]:
    def py_builder(peer_id: str, server_ip: str, port: str, filename: str) -> str:
        return f"""
python3 - <<'PY'
import time, urllib.request
peer_id = {peer_id!r}
url = 'http://{server_ip}:{port}/{filename}'
t0 = time.time()
with urllib.request.urlopen(url, timeout=60) as r:
    data = r.read()
dt = time.time() - t0
speed = int(len(data) / dt) if dt else 0
print(peer_id, getattr(r, 'status', 200), len(data), f"{{dt:.6f}}", speed)
PY
"""

    return measure_http_throughput_generic(ssh_qemu_script, server_host, server_ip, client_hosts, file_size_mb=4, port="8083", client_builder=py_builder)


def collect_topology_result(topology: str, real_ip_map: dict[str, str], qemu_present: bool, admin_token: str) -> dict:
    set_topology(topology)
    restart_real_peers()
    if qemu_present:
        restart_qemu_peers()
    wait_for_stabilization()
    snapshot = get_orchestrator_snapshot(admin_token)
    result: dict[str, object] = {"topology": topology, "real_pings": [], "real_throughput": [], "qemu_pings": [], "qemu_throughput": [], "mesh_view": None}

    real_pairs = [
        ("peer-46-250-168-185", "peer-122-8-179-57"),
        ("peer-46-250-168-185", "peer-46-250-162-141"),
        ("peer-122-8-179-57", "peer-46-250-162-141"),
    ]
    for src_id, dst_id in real_pairs:
        ping = ping_real(REAL_PEERS[src_id]["host"], real_ip_map[dst_id])
        result["real_pings"].append({"src": real_ip_map[src_id], "dst": real_ip_map[dst_id], "ok": ping.ok, "avg_ms": ping.avg_ms})

    result["real_throughput"] = measure_real_throughput(
        REAL_PEERS["peer-46-250-168-185"]["host"],
        real_ip_map["peer-46-250-168-185"],
        [("peer-122-8-179-57", REAL_PEERS["peer-122-8-179-57"]["host"]), ("peer-46-250-162-141", REAL_PEERS["peer-46-250-162-141"]["host"])],
    )

    if topology in ("mesh", "hub-mesh"):
        try:
            result["mesh_view"] = rpc().__getattr__("config.get_mesh_peers")("admin-query", "default")
        except Exception as exc:
            result["mesh_view"] = {"error": str(exc)}

    if qemu_present and all(peer_id in snapshot["peers"] for peer_id in QEMU_PEERS):
        qemu_ip_map = {peer_id: snapshot["peers"][peer_id]["ip"] for peer_id in QEMU_PEERS}
        qemu_pairs = [("pa", "qemu-pa", "qemu-pb"), ("pb", "qemu-pb", "qemu-pa")]
        for role, src_id, dst_id in qemu_pairs:
            ping = ping_qemu(role, qemu_ip_map[dst_id])
            result["qemu_pings"].append({"src": src_id, "dst": dst_id, "ok": ping.ok, "avg_ms": ping.avg_ms})
        result["qemu_throughput"] = measure_qemu_throughput(
            QEMU_PEERS["qemu-pa"]["host"],
            qemu_ip_map["qemu-pa"],
            [("qemu-pb", QEMU_PEERS["qemu-pb"]["host"])],
        )
    return result


def render_table(lines: list[str], headers: list[str], rows: list[list[str]]) -> None:
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")


def render_report(timestamp: str, snapshot: dict, topology_results: list[dict], qemu_present: bool, restored_topology: str) -> str:
    lines: list[str] = []
    lines.append("# Reporte de Rendimiento y Conectividad")
    lines.append("")
    lines.append(f"Fecha de ejecución: `{timestamp}`")
    lines.append("")
    lines.append("## Alcance")
    lines.append("")
    lines.append("- infraestructura real conectada al orquestador `101.44.24.91`")
    lines.append("- laboratorio QEMU integrado contra el mismo orquestador real" if qemu_present else "- laboratorio QEMU no medido en esta ejecución")
    lines.append("")
    lines.append("## Estado del orquestador")
    lines.append("")
    lines.append(f"- `orch.health`: `{snapshot['health'].get('status')}`")
    lines.append(f"- `hub_reachable`: `{snapshot['health'].get('hub_reachable')}`")
    lines.append(f"- `peers_count`: `{snapshot['health'].get('peers_count')}`")
    lines.append(f"- topología restaurada al final: `{restored_topology}`")
    lines.append("")
    for topo in topology_results:
        lines.append(f"## Topología `{topo['topology']}`")
        lines.append("")
        lines.append("### Conectividad real")
        lines.append("")
        render_table(lines, ["Origen", "Destino", "Éxito", "RTT promedio"], [
            [f"`{row['src']}`", f"`{row['dst']}`", f"`{'sí' if row['ok'] else 'no'}`", f"`{row['avg_ms']:.3f} ms`" if row['avg_ms'] is not None else "`n/d`"]
            for row in topo['real_pings']
        ])
        lines.append("")
        lines.append("### Throughput real")
        lines.append("")
        render_table(lines, ["Cliente", "HTTP", "Tamaño", "Tiempo", "speed_download", "Aprox. Mbps"], [
            [f"`{row['peer_id']}`", f"`{row['http']}`", f"`{row['size_download']}`", f"`{row['time_total']:.3f} s`", f"`{row['speed_download']}`", f"`{row['mbps']:.2f}`"]
            for row in topo['real_throughput']
        ])
        lines.append("")
        if qemu_present and topo['qemu_pings']:
            lines.append("### Conectividad QEMU integrada")
            lines.append("")
            render_table(lines, ["Origen", "Destino", "Éxito", "RTT promedio"], [
                [f"`{row['src']}`", f"`{row['dst']}`", f"`{'sí' if row['ok'] else 'no'}`", f"`{row['avg_ms']:.3f} ms`" if row['avg_ms'] is not None else "`n/d`"]
                for row in topo['qemu_pings']
            ])
            lines.append("")
            lines.append("### Throughput QEMU integrado")
            lines.append("")
            render_table(lines, ["Cliente", "HTTP", "Tamaño", "Tiempo", "speed_download", "Aprox. Mbps"], [
                [f"`{row['peer_id']}`", f"`{row['http']}`", f"`{row['size_download']}`", f"`{row['time_total']:.3f} s`", f"`{row['speed_download']}`", f"`{row['mbps']:.2f}`"]
                for row in topo['qemu_throughput']
            ])
            lines.append("")
        if topo['mesh_view'] is not None:
            lines.append("### Vista del orquestador")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(topo['mesh_view'], indent=2, sort_keys=True))
            lines.append("```")
            lines.append("")
    lines.append("## Peers visibles en el orquestador")
    lines.append("")
    for peer_id in sorted(snapshot['peers'].keys()):
        peer = snapshot['peers'][peer_id]
        lines.append(f"- `{peer_id}` -> `{peer.get('ip')}` endpoint `{peer.get('endpoint')}`")
    lines.append("")
    lines.append("## Comandos útiles")
    lines.append("")
    lines.append("```bash")
    lines.append("make qemu-status-real TESTBED_REAL_ORCH_PASS='...' ")
    lines.append("make performance-report-all-real TESTBED_REAL_ORCH_PASS='...' ")
    lines.append("make testbed-down")
    lines.append("```")
    lines.append("")
    return "\n".join(lines) + "\n"


def build_history_entry(timestamp: str, snapshot: dict, topology_results: list[dict], qemu_present: bool, report_path: Path) -> str:
    lines: list[str] = []
    lines.append(f"## {timestamp}")
    lines.append("")
    lines.append(f"- reporte actual: `{report_path.as_posix()}`")
    lines.append(f"- estado del orquestador: `{snapshot['health'].get('status')}`")
    lines.append(f"- peers visibles: `{snapshot['health'].get('peers_count')}`")
    lines.append(f"- qemu incluido: `{'sí' if qemu_present else 'no'}`")
    lines.append("")
    for topo in topology_results:
        real_ok = sum(1 for row in topo["real_pings"] if row["ok"])
        real_avg = [row["avg_ms"] for row in topo["real_pings"] if row["avg_ms"] is not None]
        real_avg_s = f"{sum(real_avg) / len(real_avg):.3f} ms" if real_avg else "n/d"
        real_tp = [row["mbps"] for row in topo["real_throughput"]]
        real_tp_s = f"{sum(real_tp) / len(real_tp):.2f} Mbps" if real_tp else "n/d"

        lines.append(f"### {topo['topology']}")
        lines.append("")
        lines.append(f"- conectividad real OK: `{real_ok}/{len(topo['real_pings'])}`")
        lines.append(f"- RTT real promedio agregado: `{real_avg_s}`")
        lines.append(f"- throughput real promedio agregado: `{real_tp_s}`")
        if qemu_present and topo["qemu_pings"]:
            qemu_ok = sum(1 for row in topo["qemu_pings"] if row["ok"])
            qemu_avg = [row["avg_ms"] for row in topo["qemu_pings"] if row["avg_ms"] is not None]
            qemu_avg_s = f"{sum(qemu_avg) / len(qemu_avg):.3f} ms" if qemu_avg else "n/d"
            qemu_tp = [row["mbps"] for row in topo["qemu_throughput"]]
            qemu_tp_s = f"{sum(qemu_tp) / len(qemu_tp):.2f} Mbps" if qemu_tp else "n/d"
            lines.append(f"- conectividad QEMU OK: `{qemu_ok}/{len(topo['qemu_pings'])}`")
            lines.append(f"- RTT QEMU promedio agregado: `{qemu_avg_s}`")
            lines.append(f"- throughput QEMU promedio agregado: `{qemu_tp_s}`")
        if topo.get("mesh_view") is not None:
            lines.append("- incluye vista del orquestador para topología con peers mesh")
        lines.append("")
    payload = {
        "timestamp": timestamp,
        "report_path": str(report_path),
        "qemu_included": qemu_present,
        "health": snapshot["health"],
        "peers": snapshot["peers"],
        "topology_results": topology_results,
    }
    lines.append("### JSON crudo")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(payload, indent=2, sort_keys=True))
    lines.append("```")
    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def append_history(timestamp: str, snapshot: dict, topology_results: list[dict], qemu_present: bool, history_path: Path, report_path: Path) -> None:
    if history_path.exists():
        current = history_path.read_text()
    else:
        current = "# Historial de Rendimiento y Conectividad\n\n"
    entry = build_history_entry(timestamp, snapshot, topology_results, qemu_present, report_path)
    history_path.write_text(current + entry)


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera el reporte de conectividad y rendimiento")
    parser.add_argument("--output", default=str(REPORT_PATH))
    parser.add_argument("--history-output", default=str(HISTORY_PATH))
    parser.add_argument("--skip-qemu", action="store_true")
    parser.add_argument("--skip-throughput", action="store_true")
    parser.add_argument("--ensure-qemu-real", action="store_true")
    parser.add_argument("--teardown-qemu", action="store_true")
    args = parser.parse_args()

    report_output = Path(args.output)
    history_output = Path(args.history_output)
    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    admin_token = get_admin_token()
    qemu_started = False
    report = ""
    original_topology = get_current_topology()

    try:
        if args.ensure_qemu_real and not args.skip_qemu:
            qemu_started = ensure_qemu_integrated()

        snapshot = get_orchestrator_snapshot(admin_token)
        real_ip_map = {peer_id: snapshot['peers'][peer_id]['ip'] for peer_id in REAL_PEERS if peer_id in snapshot['peers']}
        if len(real_ip_map) != len(REAL_PEERS):
            missing = sorted(set(REAL_PEERS) - set(real_ip_map))
            raise RuntimeError(f"Faltan peers reales en el orquestador: {missing}")

        qemu_present = (not args.skip_qemu) and qemu_up() and all(peer_id in snapshot['peers'] for peer_id in QEMU_PEERS)

        topology_results = []
        for topology in TOPOLOGIES:
            topology_results.append(collect_topology_result(topology, real_ip_map, qemu_present, admin_token))

        set_topology(original_topology)
        restart_real_peers()
        if qemu_present:
            restart_qemu_peers()
        wait_for_stabilization(8)
        snapshot = get_orchestrator_snapshot(admin_token)
        report = render_report(timestamp, snapshot, topology_results, qemu_present, original_topology)
    finally:
        try:
            set_topology(original_topology)
        except Exception:
            pass
        if args.teardown_qemu and qemu_started:
            qemu_cmd("down", timeout=300, check=False)

    report_output.write_text(report)
    append_history(timestamp, snapshot, topology_results, qemu_present, history_output, report_output)
    print(f"Reporte generado en {report_output}")
    print(f"Historial actualizado en {history_output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
