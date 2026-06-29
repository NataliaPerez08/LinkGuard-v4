#!/usr/bin/env python3
"""Recupera informacion de las maquinas de prueba (estilo fastfetch) y genera reporte.

Maquinas consultadas:
  - 3 nubes AWS (por llave SSH): 54.210.49.136, 3.228.113.66, 98.87.229.24
  - Orquestador/hub (llave, admin): 34.193.139.170
  - 3 QEMU Alpine VMs (local, sshpass): peer01/02/03 (192.168.100.10/20/30)
  - 1 VM + 1 RPi5 via jump 100.115.215.49: 172.20.0.40 (Alpine, root), 172.20.0.7 (RPi5, natalia)
  - Host local (donde se ejecuta el script)

Por cada maquina recopila: hostname, OS, kernel, arch, uptime, CPU (modelo/nucleos),
memoria, disco, load average, IP publica, interfaces de red, estado del servicio
wg-auto-register e interfaces WireGuard con conteo de peers.

Salida:
  - Tabla/bloques por consola (estilo fastfetch).
  - Reporte HTML en docs/reports/linkguard-aws/hostinfo/<ts>.html + latest.html.
  - Opcional JSON con --json.

Uso:
  python3 tests-linkguard-aws/collect-hostinfo.py
  python3 tests-linkguard-aws/collect-hostinfo.py --only peer-100-31-255-119
  python3 tests-linkguard-aws/collect-hostinfo.py --no-pubip --json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from report_common import (
    ROOT,
    REAL_PEERS,
    QEMU_PEERS,
    QEMU_PASS,
    ORCH_HOST,
    ORCH_USER,
    TERMINAL_JUMP,
    log,
    ssh_cloud_sudo_script,
    ssh_cloud_script,
    ssh_orch_sudo_script,
    ssh_key_script,
    ssh_qemu_script,
    ssh_terminal_script,
    ssh_terminal_sudo_script,
    _terminal_user,
    local_script,
)


def log(msg: str) -> None:
    print(f"[hostinfo] {msg}", flush=True, file=sys.stderr)

# Script POSIX que se ejecuta remotamente via `sh` (stdin). Devuelve KEY=VALUE.
# Funciona en Ubuntu/AmazonLinux/AlmaLinux/Debian y en Alpine (busybox sh).
INFO_SCRIPT = r"""
HN=$(hostname 2>/dev/null || cat /etc/hostname 2>/dev/null || echo unknown)
echo "HOSTNAME=$HN"
echo "KERNEL=$(uname -r 2>/dev/null)"
echo "ARCH=$(uname -m 2>/dev/null)"
if [ -f /etc/os-release ]; then
  . /etc/os-release
  echo "OS_NAME=${NAME:-unknown}"
  echo "OS_VERSION=${VERSION_ID:-}"
  echo "OS_PRETTY=${PRETTY_NAME:-${NAME:-unknown}}"
else
  echo "OS_NAME=unknown"
  echo "OS_VERSION="
  echo "OS_PRETTY=unknown"
fi
echo "UPTIME_SEC=$(cut -d. -f1 /proc/uptime 2>/dev/null || echo 0)"
CM=$(grep -m1 'model name' /proc/cpuinfo 2>/dev/null | cut -d: -f2 | sed 's/^ *//')
if [ -z "$CM" ]; then
  IMP=$(grep -m1 'CPU implementer' /proc/cpuinfo 2>/dev/null | cut -d: -f2 | sed 's/^ *//')
  PART=$(grep -m1 'CPU part' /proc/cpuinfo 2>/dev/null | cut -d: -f2 | sed 's/^ *//')
  if [ -n "$IMP" ] && [ -n "$PART" ]; then
    case "$IMP:$PART" in
      0x41:0xd03) CM="Cortex-A53" ;;
      0x41:0xd07) CM="Cortex-A57" ;;
      0x41:0xd08) CM="Cortex-A72" ;;
      0x41:0xd09) CM="Cortex-A73" ;;
      0x41:0xd0a) CM="Cortex-A75" ;;
      0x41:0xd0b) CM="Cortex-A76" ;;
      0x41:0xd0c) CM="Neoverse-N1" ;;
      0x41:0xd0d) CM="Cortex-A77" ;;
      0x41:0xd40) CM="Neoverse-V1" ;;
      0x41:0xd41) CM="Cortex-A78AE" ;;
      0x41:0xd44) CM="Cortex-X1" ;;
      0x41:0xd46) CM="Cortex-A510" ;;
      0x41:0xd47) CM="Cortex-A710" ;;
      0x41:0xd48) CM="Cortex-X2" ;;
      0x41:0xd49) CM="Neoverse-N2" ;;
      0x41:0xd4a) CM="Cortex-A715" ;;
      0x41:0xd4b) CM="Cortex-X3" ;;
      0x41:0xd4c) CM="Neoverse-V2" ;;
      0x41:0xd4d) CM="Cortex-A520" ;;
      0x41:0xd4e) CM="Cortex-A720" ;;
      0x41:0xd4f) CM="Cortex-X4" ;;
      0x42:0x000) CM="BCM2835" ;;
      0x42:0x001) CM="BCM2836" ;;
      0x42:0x020) CM="BCM2837" ;;
      0x42:0x021) CM="BCM2711" ;;
      0x42:0x022) CM="BCM2712" ;;
      *) CM="${IMP}:${PART}" ;;
    esac
  fi
fi
[ -z "$CM" ] && CM=$(grep -m1 'Hardware' /proc/cpuinfo 2>/dev/null | cut -d: -f2 | sed 's/^ *//')
[ -z "$CM" ] && CM=$(lscpu 2>/dev/null | sed -n 's/^Model name:\s*//p')
[ -z "$CM" ] && CM=unknown
echo "CPU_MODEL=$CM"
CC=$(nproc 2>/dev/null || grep -c '^processor' /proc/cpuinfo 2>/dev/null || echo 0)
echo "CPU_CORES=$CC"
MT=$(grep '^MemTotal:' /proc/meminfo 2>/dev/null | awk '{print $2}' || echo 0)
MA=$(grep '^MemAvailable:' /proc/meminfo 2>/dev/null | awk '{print $2}')
[ -z "$MA" ] && MA=$(grep '^MemFree:' /proc/meminfo 2>/dev/null | awk '{print $2}' || echo 0)
echo "MEM_TOTAL_KB=$MT"
echo "MEM_AVAIL_KB=$MA"
DFLINE=$(df -hP / 2>/dev/null | awk 'NR==2{print $2"|"$3"|"$4"|"$5}')
DT=$(echo "$DFLINE" | cut -d'|' -f1)
DU=$(echo "$DFLINE" | cut -d'|' -f2)
DA=$(echo "$DFLINE" | cut -d'|' -f3)
DP=$(echo "$DFLINE" | cut -d'|' -f4)
echo "DISK_TOTAL=$DT"
echo "DISK_USED=$DU"
echo "DISK_AVAIL=$DA"
echo "DISK_PCT=$DP"
echo "LOADAVG=$(cut -d' ' -f1-3 /proc/loadavg 2>/dev/null)"
PROCS=$(ls -d /proc/[0-9]* 2>/dev/null | wc -l)
echo "PROCS=$PROCS"
PUB=""
if command -v curl >/dev/null 2>&1; then
  PUB=$(curl -s -m 5 ifconfig.me 2>/dev/null)
elif command -v wget >/dev/null 2>&1; then
  PUB=$(wget -qO- -T 5 ifconfig.me 2>/dev/null)
fi
echo "PUB_IP=$PUB"
NET=$(ip -o addr show scope global 2>/dev/null | awk '{
  if ($3=="inet" || $3=="inet6") print $2"|"$3"|"$4
}' | sort -u | tr '\n' ';')
echo "NET_IFACES=$NET"
if command -v systemctl >/dev/null 2>&1; then
  WGS=$(systemctl is-active wg-auto-register 2>/dev/null || echo unknown)
elif command -v rc-service >/dev/null 2>&1; then
  WS=$(rc-service wg-auto-register status 2>&1)
  case "$WS" in *started*) WGS=active;; *stopped*) WGS=stopped;; *) WGS=unknown;; esac
else
  WGS=unknown
fi
echo "WG_SVC=$WGS"
WGI=$(wg show interfaces 2>/dev/null || echo '')
echo "WG_IFACES=$WGI"
WPC=$(wg show all dump 2>/dev/null | grep -c '^peer' 2>/dev/null || echo 0)
echo "WG_PEER_COUNT=$WPC"
"""

DEFAULT_TIMEOUT = 45


def build_machines() -> list[dict[str, str]]:
    machines: list[dict[str, str]] = []
    for p in REAL_PEERS:
        if p.get("is_terminal"):
            if p.get("is_rpi"):
                machines.append({"id": p["peer_id"], "label": p["label"], "host": p["host"], "role": "rpi", "kind": "terminal"})
            else:
                machines.append({"id": p["peer_id"], "label": p["label"], "host": p["host"], "role": "vm", "kind": "terminal"})
        else:
            machines.append({"id": p["peer_id"], "label": p["label"], "host": p["host"], "role": "nube", "kind": "cloud"})
    for p in QEMU_PEERS:
        machines.append({"id": p["peer_id"], "label": p["label"], "host": p["host"], "role": "qemu", "kind": "qemu"})
    machines.append({"id": "orquestador", "label": f"orq ({ORCH_HOST})", "host": ORCH_HOST, "role": "orquestador", "kind": "orch"})
    machines.append({"id": "local", "label": "host-local", "host": "(local)", "role": "local", "kind": "local"})
    return machines


def parse_info(out: str) -> dict[str, str]:
    info: dict[str, str] = {}
    for line in out.splitlines():
        m = re.match(r"^([A-Z_]+)=(.*)$", line)
        if m:
            info[m.group(1)] = m.group(2)
    return info


def _has_hostname(out: str) -> bool:
    return bool(re.search(r"^HOSTNAME=.+", out, re.MULTILINE))


def _local_plain_script(script: str, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["sh"], input=script, text=True, capture_output=True, timeout=timeout, check=False)


def collect_one(machine: dict[str, str], timeout: int, no_pubip: bool) -> dict[str, Any]:
    kind = machine["kind"]
    host = machine["host"]
    script = INFO_SCRIPT if not no_pubip else INFO_SCRIPT.replace("curl -s -m 5 ifconfig.me", "true").replace("wget -qO- -T 5 ifconfig.me", "true")

    def try_run(priv: bool) -> subprocess.CompletedProcess[str] | None:
        try:
            if kind == "cloud":
                if priv:
                    return ssh_cloud_sudo_script(host, script, timeout=timeout, check=False)
                return ssh_cloud_script(host, script, timeout=timeout, check=False)
            if kind == "qemu":
                return ssh_qemu_script(host, script, timeout=timeout)
            if kind == "orch":
                if priv:
                    return ssh_orch_sudo_script(script, timeout=timeout, check=False)
                return ssh_key_script(ORCH_USER, ORCH_HOST, script, timeout=timeout, check=False)
            if kind == "terminal":
                if priv:
                    return ssh_terminal_sudo_script(host, script, timeout=timeout)
                return ssh_terminal_script(host, script, timeout=timeout)
            if kind == "local":
                if priv:
                    return local_script(script, timeout=timeout)
                return _local_plain_script(script, timeout)
        except subprocess.TimeoutExpired:
            return None
        except Exception as exc:
            return subprocess.CompletedProcess(args=[], returncode=-1, stdout="", stderr=str(exc))
        return None

    result = try_run(priv=True)
    out = (result.stdout or "") if result else ""
    if not _has_hostname(out):
        result = try_run(priv=False)
        out = (result.stdout or "") if result else ""

    info = parse_info(out)
    if not info.get("HOSTNAME"):
        err = (result.stderr or "sin salida") if result else "timeout/error"
        info["HOSTNAME"] = "(inaccesible)"
        info["_error"] = err.strip()[:300]
    info["_id"] = machine["id"]
    info["_label"] = machine["label"]
    info["_host"] = host
    info["_role"] = machine["role"]
    info["_kind"] = kind
    return info


# ── Formateo ──

def fmt_uptime(sec: str | None) -> str:
    try:
        s = int(float(sec or 0))
    except (ValueError, TypeError):
        return "?"
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, _ = divmod(s, 60)
    if d:
        return f"{d}d {h}h"
    if h:
        return f"{h}h {m}m"
    return f"{m}m"


def fmt_mem(total_kb: str | None, avail_kb: str | None) -> str:
    try:
        t = int(total_kb or 0) / 1024 / 1024
        a = int(avail_kb or 0) / 1024 / 1024
        u = max(t - a, 0.0)
        return f"{u:.1f} / {t:.1f} GB"
    except (ValueError, TypeError):
        return "?"


def fmt_disk(info: dict[str, str]) -> str:
    t, u, p = info.get("DISK_TOTAL", "?"), info.get("DISK_USED", "?"), info.get("DISK_PCT", "?")
    return f"{u} / {t} ({p})"


def fmt_cpu(model: str | None, cores: str | None) -> str:
    m = (model or "?").strip()
    if len(m) > 42:
        m = m[:39] + "..."
    return f"{m} ({cores or '?'} nucleos)"


def fmt_net(raw: str | None) -> str:
    if not raw:
        return "(sin interfaces)"
    if "|" not in raw:
        return raw.rstrip(";").replace(";", ", ")
    parts = raw.rstrip(";").split(";")
    ifaces: dict[str, list[str]] = {}
    for p in parts:
        pieces = p.split("|")
        if len(pieces) == 3:
            iface, fam, addr = pieces
            tag = "v6" if fam == "inet6" else "v4"
            ifaces.setdefault(iface, []).append(f"{addr} ({tag})")
    if not ifaces:
        return raw.rstrip(";").replace(";", ", ")
    return "; ".join(f"{name}: {', '.join(ips)}" for name, ips in ifaces.items())


def fmt_wg(info: dict[str, str]) -> str:
    svc = info.get("WG_SVC", "unknown")
    ifaces = info.get("WG_IFACES", "") or "(ninguna)"
    peers = info.get("WG_PEER_COUNT", "0")
    return f"svc={svc}, ifaces={ifaces}, peers={peers}"


# ── Salida consola (estilo fastfetch) ──

ROLE_TAG = {"nube": "NUBE", "vm": "VM", "rpi": "RPi5", "qemu": "QEMU", "orquestador": "ORQ", "local": "LOCAL"}


def render_terminal(results: list[dict[str, str]]) -> None:
    print()
    print("\033[1;36m" + "LinkGuard v2 \u2014 Info de maquinas de prueba" + "\033[0m")
    print(f"\033[2mRecopilado: {datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')}\033[0m")
    print()
    for r in results:
        tag = ROLE_TAG.get(r["_role"], r["_role"])
        header = f" {r['_label']}  [{tag}] "
        if r.get("_error"):
            header_color = "\033[1;31m"
        elif r.get("WG_SVC") == "active":
            header_color = "\033[1;32m"
        else:
            header_color = "\033[1;33m"
        line = "\u2500" * max(8, 70 - len(header))
        print(header_color + "\u250c" + header + line + "\033[0m")
        if r.get("_error"):
            print(f"\u2502 \033[31mERROR: {r['_error']}\033[0m")
            print(f"\u2502 host: {r['_host']}")
            print("\u2514" + "\u2500" * 69)
            print()
            continue
        rows = [
            ("hostname", r.get("HOSTNAME", "?")),
            ("OS", f"{r.get('OS_PRETTY', '?')}  ({r.get('ARCH', '?')})"),
            ("kernel", r.get("KERNEL", "?")),
            ("uptime", fmt_uptime(r.get("UPTIME_SEC"))),
            ("CPU", fmt_cpu(r.get("CPU_MODEL"), r.get("CPU_CORES"))),
            ("Mem", fmt_mem(r.get("MEM_TOTAL_KB"), r.get("MEM_AVAIL_KB"))),
            ("Disk", fmt_disk(r)),
            ("Load", r.get("LOADAVG", "?")),
            ("Procs", r.get("PROCS", "?")),
            ("Pub IP", r.get("PUB_IP") or "(n/a)"),
            ("Net", fmt_net(r.get("NET_IFACES"))),
            ("WG", fmt_wg(r)),
        ]
        for k, v in rows:
            print(f"\u2502 \033[1;34m{k:<9}\033[0m {v}")
        print("\u2514" + "\u2500" * 69)
        print()


# ── Salida HTML ──

def _esc(s: Any) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_html(timestamp: str, results: list[dict[str, str]]) -> str:
    rows: list[str] = []
    rows.append("""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Info de maquinas \u2014 LinkGuard v2</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: #0d1117; color: #c9d1d9; padding: 20px; }
  h1 { color: #58a6ff; font-size: 1.8em; margin-bottom: 5px; }
  h2 { color: #79c0ff; font-size: 1.4em; margin: 25px 0 15px; border-bottom: 1px solid #21262d; padding-bottom: 8px; }
  h3 { color: #a5d6ff; font-size: 1.1em; margin: 15px 0 10px; }
  code { background: #21262d; padding: 1px 5px; border-radius: 3px; font-size: 0.9em; }
  table { border-collapse: collapse; width: 100%; margin: 10px 0 20px; font-size: 0.85em; }
  th, td { border: 1px solid #30363d; padding: 6px 10px; text-align: left; }
  th { background: #161b22; font-weight: 600; color: #79c0ff; }
  td { background: #0d1117; }
  .section { background: #161b22; border-radius: 8px; padding: 16px; margin-bottom: 20px; border: 1px solid #30363d; }
  .tag-nube { background: #1f6feb33; color: #58a6ff; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }
  .tag-qemu { background: #8b5cf633; color: #c4b5fd; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }
  .tag-vm { background: #6e40c933; color: #d2a8ff; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }
  .tag-rpi { background: #da363333; color: #ff7b72; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }
  .tag-orq { background: #23863633; color: #3fb950; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }
  .tag-local { background: #f0883e33; color: #f0883e; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; }
  .ok { color: #3fb950; font-weight: bold; }
  .fail { color: #f85149; font-weight: bold; }
  .warn { color: #d29922; font-weight: bold; }
  .legend { color: #8b949e; margin-top: 10px; font-size: 0.8em; }
  .card { background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 12px; margin-bottom: 15px; }
  .card h3 { margin-top: 0; }
  .kv { display: grid; grid-template-columns: 110px 1fr; gap: 4px 12px; font-size: 0.9em; }
  .kv .k { color: #79c0ff; font-weight: 600; }
  pre { background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 10px; font-size: 0.8em; overflow-x: auto; white-space: pre-wrap; }
</style>
</head>
<body>
<h1>Info de maquinas de prueba \u2014 LinkGuard v2</h1>
<p>Generado: <code>""" + timestamp + """</code></p>
    <p>Maquinas: """ + str(len(results)) + """ (3 nubes AWS + 3 QEMU + orquestador + 1 VM + 1 RPi5 via jump + host local)</p>
""")
    tag_cls = {"nube": "tag-nube", "vm": "tag-vm", "rpi": "tag-rpi", "qemu": "tag-qemu", "orquestador": "tag-orq", "local": "tag-local"}

    # Tabla resumen
    rows.append('<div class="section"><h2>Resumen</h2><table><tr><th>Maquina</th><th>Rol</th><th>Hostname</th><th>OS</th><th>Kernel</th><th>CPU</th><th>Mem</th><th>Disk</th><th>Uptime</th><th>WG svc</th><th>Pub IP</th></tr>')
    for r in results:
        cls = tag_cls.get(r["_role"], "tag-nube")
        wg_svc = r.get("WG_SVC", "unknown")
        wg_cls = "ok" if wg_svc == "active" else ("fail" if r.get("_error") else "warn")
        rows.append(f'<tr><td>{_esc(r["_label"])}</td><td><span class="{cls}">{_esc(ROLE_TAG.get(r["_role"], r["_role"]))}</span></td>'
                    f'<td>{_esc(r.get("HOSTNAME", "?"))}</td><td>{_esc(r.get("OS_PRETTY", "?"))}</td><td><code>{_esc(r.get("KERNEL", "?"))}</code></td>'
                    f'<td>{_esc(fmt_cpu(r.get("CPU_MODEL"), r.get("CPU_CORES")))}</td><td>{_esc(fmt_mem(r.get("MEM_TOTAL_KB"), r.get("MEM_AVAIL_KB")))}</td>'
                    f'<td>{_esc(fmt_disk(r))}</td><td>{_esc(fmt_uptime(r.get("UPTIME_SEC")))}</td>'
                    f'<td class="{wg_cls}">{_esc(wg_svc)}</td><td><code>{_esc(r.get("PUB_IP") or "(n/a)")}</code></td></tr>')
    rows.append('</table></div>')

    # Tarjetas detalladas
    rows.append('<div class="section"><h2>Detalle por maquina</h2>')
    for r in results:
        cls = tag_cls.get(r["_role"], "tag-nube")
        tag = f'<span class="{cls}">{_esc(ROLE_TAG.get(r["_role"], r["_role"]))}</span>'
        rows.append(f'<div class="card"><h3>{_esc(r["_label"])} {tag}</h3>')
        if r.get("_error"):
            rows.append(f'<p class="fail">ERROR de conexion: {_esc(r["_error"])}</p>')
            rows.append(f'<p>host: <code>{_esc(r["_host"])}</code></p></div>')
            continue
        kv = [
            ("hostname", r.get("HOSTNAME", "?")),
            ("OS", f"{r.get('OS_PRETTY', '?')} ({r.get('ARCH', '?')})"),
            ("kernel", r.get("KERNEL", "?")),
            ("uptime", fmt_uptime(r.get("UPTIME_SEC"))),
            ("CPU", fmt_cpu(r.get("CPU_MODEL"), r.get("CPU_CORES"))),
            ("Mem", fmt_mem(r.get("MEM_TOTAL_KB"), r.get("MEM_AVAIL_KB"))),
            ("Disk", fmt_disk(r)),
            ("Load", r.get("LOADAVG", "?")),
            ("Procs", r.get("PROCS", "?")),
            ("Pub IP", r.get("PUB_IP") or "(n/a)"),
            ("Net", fmt_net(r.get("NET_IFACES"))),
            ("WG svc", r.get("WG_SVC", "unknown")),
            ("WG ifaces", r.get("WG_IFACES") or "(ninguna)"),
            ("WG peers", r.get("WG_PEER_COUNT", "0")),
        ]
        rows.append('<div class="kv">')
        for k, v in kv:
            rows.append(f'<div class="k">{_esc(k)}</div><div>{_esc(v)}</div>')
        rows.append('</div></div>')
    rows.append('</div>')

    rows.append('<div class="section"><h2>Topologia de acceso</h2>')
    rows.append(f'<table><tr><th>Tipo</th><th>Maquina</th><th>Acceso</th></tr>')
    rows.append(f'<tr><td><span class="tag-nube">NUBE</span></td><td>54.210.49.136 / 3.228.113.66 / 98.87.229.24</td><td>llave SSH (ubuntu / ec2-user) + sudo</td></tr>')
    rows.append(f'<tr><td><span class="tag-orq">ORQ</span></td><td>{_esc(ORCH_HOST)}</td><td>llave SSH (admin) + sudo</td></tr>')
    rows.append(f'<tr><td><span class="tag-qemu">QEMU</span></td><td>peer-qemu01 / peer-qemu02 / peer-qemu03</td><td>sshpass local (root / <code>{_esc(QEMU_PASS)}</code>)</td></tr>')
    rows.append(f'<tr><td><span class="tag-vm">VM</span></td><td>172.20.0.40</td><td>password via jump <code>{_esc(TERMINAL_JUMP)}</code> (root)</td></tr>')
    rows.append(f'<tr><td><span class="tag-rpi">RPi5</span></td><td>172.20.0.7</td><td>password via jump <code>{_esc(TERMINAL_JUMP)}</code> (natalia)</td></tr>')
    rows.append(f'<tr><td><span class="tag-local">LOCAL</span></td><td>host-local</td><td>local (sudo)</td></tr>')
    rows.append('</table>')
    rows.append(f'<p class="legend">Sudo orquestador: {"LINKGUARD_SUDO_PASS" if os.environ.get("LINKGUARD_SUDO_PASS") else "no definido (sudo -n)"}</p>')
    rows.append('</div>')

    rows.append('</body></html>\n')
    return "\n".join(rows)


# ── Main ──

def main() -> int:
    parser = argparse.ArgumentParser(description="Recupera info de las maquinas de prueba (estilo fastfetch)")
    parser.add_argument("--only", default="", help="Solo consultar la maquina con este id (p.ej. peer-100-31-255-119)")
    parser.add_argument("--no-pubip", action="store_true", help="Saltar la consulta de IP publica (mas rapido)")
    parser.add_argument("--no-html", action="store_true", help="No generar reporte HTML")
    parser.add_argument("--json", action="store_true", help="Volcar resultados en JSON a stdout")
    parser.add_argument("--output", default="", help="Ruta del reporte HTML (default: docs/reports/linkguard-aws/hostinfo/)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Timeout por maquina en segundos")
    args = parser.parse_args()

    machines = build_machines()
    if args.only:
        machines = [m for m in machines if m["id"] == args.only]
        if not machines:
            print(f"ERROR: no existe maquina con id '{args.only}'", file=sys.stderr)
            return 1

    log(f"Consultando {len(machines)} maquinas (timeout {args.timeout}s, pubip={'no' if args.no_pubip else 'si'})...")

    results: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=len(machines)) as pool:
        futures = {pool.submit(collect_one, m, args.timeout, args.no_pubip): m for m in machines}
        for fut in as_completed(futures):
            m = futures[fut]
            try:
                res = fut.result()
            except Exception as exc:
                res = {"_id": m["id"], "_label": m["label"], "_host": m["host"], "_role": m["role"], "_kind": m["kind"],
                       "HOSTNAME": "(inaccesible)", "_error": str(exc)[:300]}
            results.append(res)
            status = "ERROR" if res.get("_error") else res.get("HOSTNAME", "?")
            log(f"  {m['label']}: {status}")

    results.sort(key=lambda r: [m["id"] for m in machines].index(r["_id"]) if r["_id"] in [m["id"] for m in machines] else 99)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        render_terminal(results)

    if not args.no_html:
        timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        ts_slug = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")
        if args.output:
            out_path = Path(args.output)
        else:
            date_dir = ts_slug[:4] + "-" + ts_slug[4:6] + "-" + ts_slug[6:8]
            out_path = ROOT / "docs" / "reports" / "linkguard-aws" / "hostinfo" / date_dir / f"hostinfo-{ts_slug}.html"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        html = render_html(timestamp, results)
        out_path.write_text(html)
        latest = out_path.parent / "latest.html"
        latest.write_text(html)
        log(f"Reporte HTML: {out_path}")
        log(f"Latest: {latest}")

    errors = sum(1 for r in results if r.get("_error"))
    if errors:
        log(f"{errors} maquina(s) inaccesibles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
