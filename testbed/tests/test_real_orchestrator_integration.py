"""
Pruebas del testbed QEMU integrado con el orquestador real.

Requisitos:
  - TESTBED_REAL_ORCH_PASS definido
  - testbed levantado con: python3 testbed/scripts/launch-testbed.py up-real
"""

import os
import subprocess
import time
import xmlrpc.client


PASS = "linkguard-test"
SSH_OPTS = ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null", "-o", "ConnectTimeout=5"]
REAL_ORCH_URL = os.environ.get("TESTBED_REAL_ORCH_URL", "http://101.44.24.91:8000/RPC2")
_REAL_ORCH_HOST = REAL_ORCH_URL.split("://")[1].split(":")[0]
_REAL_WG_ENDPOINT = f"{_REAL_ORCH_HOST}:51820"

QEMU_PEERS = {
    "orq": {"host_ip": "192.168.100.10", "peer_id": "qemu-orq"},
    "pa": {"host_ip": "192.168.100.20", "peer_id": "qemu-pa"},
    "pb": {"host_ip": "192.168.100.30", "peer_id": "qemu-pb"},
}


def _ssh(host_ip, *cmd):
    return subprocess.run(
        ["sshpass", "-p", PASS, "ssh", *SSH_OPTS, f"root@{host_ip}", *cmd],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _rpc():
    return xmlrpc.client.ServerProxy(REAL_ORCH_URL, allow_none=True)


def _peer_list():
    return _rpc().__getattr__("peer.list")().get("peers", {})


def _wait_for_registered_qemu_peers(timeout=90):
    expected = {cfg["peer_id"] for cfg in QEMU_PEERS.values()}
    deadline = time.time() + timeout
    last = {}
    while time.time() < deadline:
        last = _peer_list()
        if expected.issubset(last.keys()):
            return last
        time.sleep(3)
    raise AssertionError(f"No aparecieron todos los peers QEMU en el orquestador real: {last}")


def _wait_for_handshake(host_ip: str, timeout=90):
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        r = _ssh(host_ip, "wg", "show", "wg0", "latest-handshakes")
        last = (r.stdout or "") + (r.stderr or "")
        if r.returncode == 0:
            for line in r.stdout.strip().splitlines():
                parts = line.split()
                if len(parts) == 2 and parts[1].isdigit() and int(parts[1]) > 0:
                    return r.stdout
        time.sleep(3)
    raise AssertionError(f"No hubo handshake WireGuard en {host_ip}:\n{last}")


def _wait_for_ping(src_host_ip: str, dst_tunnel_ip: str, timeout=90):
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        r = _ssh(src_host_ip, "ping", "-c", "2", "-W", "2", dst_tunnel_ip)
        last = (r.stdout or "") + (r.stderr or "")
        if r.returncode == 0:
            return last
        time.sleep(3)
    raise AssertionError(f"Ping {src_host_ip} -> {dst_tunnel_ip} falló:\n{last}")


def test_qemu_peers_registered_on_real_orchestrator():
    peers = _wait_for_registered_qemu_peers()
    for cfg in QEMU_PEERS.values():
        peer = peers[cfg["peer_id"]]
        assert peer["user_id"] == cfg["peer_id"]
        assert peer["endpoint"]
        assert peer["public_key"]
        assert "default" in (peer.get("networks") or [])
        assert "qemu" in (peer.get("tags") or [])


def test_qemu_peer_services_and_handshakes():
    _wait_for_registered_qemu_peers()
    for cfg in QEMU_PEERS.values():
        status = _ssh(cfg["host_ip"], "rc-service", "wg-auto-register", "status")
        assert status.returncode == 0, f"wg-auto-register no está sano en {cfg['host_ip']}:\n{status.stdout}\n{status.stderr}"
        wg_show = _ssh(cfg["host_ip"], "wg", "show", "wg0")
        assert wg_show.returncode == 0, f"wg0 no está levantado en {cfg['host_ip']}:\n{wg_show.stdout}\n{wg_show.stderr}"
        assert f"endpoint: {_REAL_WG_ENDPOINT}" in wg_show.stdout
        _wait_for_handshake(cfg["host_ip"])


def test_qemu_peers_can_ping_each_other_via_real_orchestrator():
    peers = _wait_for_registered_qemu_peers()
    pa = peers["qemu-pa"]["ip"]
    pb = peers["qemu-pb"]["ip"]
    _wait_for_ping(QEMU_PEERS["pa"]["host_ip"], pb)
    _wait_for_ping(QEMU_PEERS["pb"]["host_ip"], pa)
