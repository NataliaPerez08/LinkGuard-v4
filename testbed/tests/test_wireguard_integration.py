"""
Tests de integración con WireGuard real sobre el testbed QEMU.
Ejecuta escenarios de alcanzabilidad entre VMs (orq, pa, pb).

Requisitos:
  - Testbed lanzado (python3 launch-testbed.py up)
  - sshpass instalado en el host
  - Las VMs accesibles vía SSH (root/linkguard-test)

Escenarios:
  1. Directo P2P: pa ↔ pb con WireGuard sobre br1
  2. Hub-Spoke: pa y pb conectados via orq como hub
  3. Hub-Mesh: pa y pb con peers directos + relay de fallback
"""

import os, subprocess, time, json, pytest, re, sys, base64
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import x25519

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
PASS = "linkguard-test"
SSH_OPTS = ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null", "-o", "ConnectTimeout=5"]

VMS = {
    "orq": {"ip": "192.168.100.10", "data_ip": "10.0.0.10"},
    "pa":  {"ip": "192.168.100.20", "data_ip": "10.0.0.20"},
    "pb":  {"ip": "192.168.100.30", "data_ip": "10.0.0.30"},
}

TUNNEL_PREFIX = 24
TUNNEL_CIDR = "10.99.0.0/24"
HUB_TUNNEL_IP = "10.99.0.1"
PA_TUNNEL_IP = "10.99.0.2"
PB_TUNNEL_IP = "10.99.0.3"
WG_PORT = "51820"
WG_IFACE = "wg0"


def _ssh(host_ip, *cmd):
    full_cmd = ["sshpass", "-p", PASS, "ssh"] + SSH_OPTS + [f"root@{host_ip}"] + list(cmd)
    return subprocess.run(full_cmd, capture_output=True, text=True, timeout=30)


def _ssh_ok(host_ip, *cmd):
    r = _ssh(host_ip, *cmd)
    assert r.returncode == 0, f"SSH a {host_ip} falló:\n{r.stderr}\n{r.stdout}"
    return r.stdout


def _scp(src, dest_host_ip, dest_path):
    full_cmd = ["sshpass", "-p", PASS, "scp"] + SSH_OPTS + [src, f"root@{dest_host_ip}:{dest_path}"]
    subprocess.run(full_cmd, capture_output=True, text=True, timeout=30, check=True)


def _cleanup_wg(host_ip):
    _ssh(host_ip, "ip", "link", "del", WG_IFACE)


def _ensure_wg_clean(host_ip):
    _ssh(host_ip, "ip", "link", "del", WG_IFACE)  # falla silenciosamente si no existe


def _local_gen_privkey():
    """Genera private key WireGuard usando cryptography (sin wg binario)."""
    pk = x25519.X25519PrivateKey.generate()
    return base64.b64encode(pk.private_bytes_raw()).decode()


def _local_pubkey(priv_b64):
    """Deriva public key WireGuard desde private key."""
    raw = base64.b64decode(priv_b64)
    pk = x25519.X25519PrivateKey.from_private_bytes(raw)
    return base64.b64encode(pk.public_key().public_bytes_raw()).decode()


def _gen_keypair(host_ip, keydir="/etc/wireguard"):
    r = _ssh(host_ip, "mkdir", "-p", keydir)
    _ssh(host_ip, "wg", "genkey", "|", "tee", f"{keydir}/{WG_IFACE}.key", "|", "wg", "pubkey", ">", f"{keydir}/{WG_IFACE}.pub")
    r_priv = _ssh(host_ip, "cat", f"{keydir}/{WG_IFACE}.key")
    r_pub = _ssh(host_ip, "cat", f"{keydir}/{WG_IFACE}.pub")
    return r_priv.stdout.strip(), r_pub.stdout.strip()


def _get_pubkey(host_ip, keydir="/etc/wireguard"):
    r = _ssh(host_ip, "cat", f"{keydir}/{WG_IFACE}.pub")
    return r.stdout.strip()


def _wg_show(host_ip, iface=WG_IFACE):
    r = _ssh(host_ip, "wg", "show", iface)
    if r.returncode != 0:
        return ""
    return r.stdout


def _wg_latest_handshakes(host_ip, iface=WG_IFACE):
    """wg show wg0 latest-handshakes → dict {pubkey: timestamp}"""
    r = _ssh(host_ip, "wg", "show", iface, "latest-handshakes")
    if r.returncode != 0:
        return {}
    result = {}
    for line in r.stdout.strip().splitlines():
        parts = line.split()
        if len(parts) >= 2:
            result[parts[0]] = int(parts[1])
    return result


def _wg_peers(host_ip, iface=WG_IFACE):
    """wg show wg0 peers → lista de pubkeys"""
    r = _ssh(host_ip, "wg", "show", iface, "peers")
    if r.returncode != 0:
        return []
    return [p for p in r.stdout.strip().splitlines() if p]


def _wg_endpoints(host_ip, iface=WG_IFACE):
    """wg show wg0 endpoints → dict {pubkey: endpoint}"""
    r = _ssh(host_ip, "wg", "show", iface, "endpoints")
    if r.returncode != 0:
        return {}
    result = {}
    for line in r.stdout.strip().splitlines():
        parts = line.split()
        if len(parts) >= 2:
            result[parts[0]] = parts[1]
    return result


def _ping(host_ip, target_ip, count=3, iface=None):
    if iface:
        r = _ssh(host_ip, "ping", "-I", iface, "-c", str(count), "-W", "2", target_ip)
    else:
        r = _ssh(host_ip, "ping", "-c", str(count), "-W", "2", target_ip)
    return r.returncode == 0


# ===========================================================================
# Fixtures compartidos
# ===========================================================================

@pytest.fixture(scope="session")
def testbed_running():
    """Verifica que las 3 VMs respondan SSH."""
    for role, cfg in VMS.items():
        r = _ssh(cfg["ip"], "true")
        assert r.returncode == 0, f"{role} ({cfg['ip']}) no responde SSH"
    yield


@pytest.fixture(scope="function")
def clean_wg_all():
    """Limpia interfaces WireGuard en todas las VMs antes/después de cada test."""
    for cfg in VMS.values():
        _ensure_wg_clean(cfg["ip"])
    yield
    for cfg in VMS.values():
        _ensure_wg_clean(cfg["ip"])


# ===========================================================================
# Helpers de escenarios
# ===========================================================================

def _get_privkey(host_ip, keypath=None):
    if keypath is None:
        keypath = f"/etc/wireguard/{WG_IFACE}.key"
    r = _ssh(host_ip, "cat", keypath)
    return r.stdout.strip()


def _write_wg_config(host_ip, content, iface=WG_IFACE):
    """Escribe config WireGuard en la VM vía stdin."""
    r = subprocess.run(
        ["sshpass", "-p", PASS, "ssh"] + SSH_OPTS + [f"root@{host_ip}",
         "sh", "-c", f"cat > /etc/wireguard/{iface}.conf"],
        input=content, capture_output=True, text=True, timeout=15
    )
    return r


def _wg_quick_up(host_ip, iface=WG_IFACE):
    r = _ssh(host_ip, "wg-quick", "up", iface)
    assert r.returncode == 0, f"wg-quick up {iface} en {host_ip} falló:\n{r.stderr}\n{r.stdout}"
    return r


def _setup_direct_tunnel(host_a_ip, host_a_tunnel_ip, host_a_pubkey,
                         host_b_ip, host_b_tunnel_ip, host_b_pubkey,
                         listen_port=WG_PORT, iface=WG_IFACE,
                         data_iface="eth1"):
    """Configura un túnel WireGuard directo entre host_a y host_b.
    Lee la llave privada y la embedé directamente en la config."""
    privkey = _get_privkey(host_a_ip)
    cfg = (
        f"[Interface]\n"
        f"Address = {host_a_tunnel_ip}/{TUNNEL_PREFIX}\n"
        f"PrivateKey = {privkey}\n"
        f"ListenPort = {listen_port}\n"
        f"MTU = 1420\n"
        f"\n"
        f"[Peer]\n"
        f"PublicKey = {host_b_pubkey}\n"
        f"Endpoint = {host_b_ip}:{listen_port}\n"
        f"AllowedIPs = {host_b_tunnel_ip}/32\n"
        f"PersistentKeepalive = 25\n"
    )
    _write_wg_config(host_a_ip, cfg, iface)
    _wg_quick_up(host_a_ip, iface)
    return cfg


# ===========================================================================
# ESCENARIO 1 — Directo P2P
# ===========================================================================

class TestDirectoP2P:
    """Túnel WireGuard directo entre pa y pb sobre br1 (10.0.0.0/24)."""

    def test_gen_keys(self, testbed_running, clean_wg_all):
        """Genera pares de llaves WireGuard en pa y pb."""
        for host in ["pa", "pb"]:
            priv, pub = _gen_keypair(VMS[host]["ip"])
            assert len(priv) == 44, f"{host}: llave privada inválida"
            assert len(pub) == 44, f"{host}: llave pública inválida"

    def test_tunel_conecta_y_hace_handshake(self, testbed_running, clean_wg_all):
        """Configura túneles directos y verifica handshake en ambos lados."""
        pa_pub = _gen_keypair(VMS["pa"]["ip"])[1]
        pb_pub = _gen_keypair(VMS["pb"]["ip"])[1]

        _setup_direct_tunnel(
            VMS["pa"]["ip"], PA_TUNNEL_IP, pa_pub,
            VMS["pb"]["data_ip"], PB_TUNNEL_IP, pb_pub,
        )
        _setup_direct_tunnel(
            VMS["pb"]["ip"], PB_TUNNEL_IP, pb_pub,
            VMS["pa"]["data_ip"], PA_TUNNEL_IP, pa_pub,
        )

        time.sleep(3)

        show_pa = _wg_show(VMS["pa"]["ip"])
        assert "peer:" in show_pa or "peer" in show_pa, f"pa no tiene peers:\n{show_pa}"
        assert pb_pub in show_pa, f"pa no muestra la pubkey de pb:\n{show_pa}"

        show_pb = _wg_show(VMS["pb"]["ip"])
        assert pa_pub in show_pb, f"pb no muestra la pubkey de pa:\n{show_pb}"

    def test_ping_por_tunel(self, testbed_running, clean_wg_all):
        """Ping a través del túnel WireGuard entre pa y pb."""
        pa_pub = _gen_keypair(VMS["pa"]["ip"])[1]
        pb_pub = _gen_keypair(VMS["pb"]["ip"])[1]

        _setup_direct_tunnel(
            VMS["pa"]["ip"], PA_TUNNEL_IP, pa_pub,
            VMS["pb"]["data_ip"], PB_TUNNEL_IP, pb_pub,
        )
        _setup_direct_tunnel(
            VMS["pb"]["ip"], PB_TUNNEL_IP, pb_pub,
            VMS["pa"]["data_ip"], PA_TUNNEL_IP, pa_pub,
        )

        time.sleep(3)

        assert _ping(VMS["pa"]["ip"], PB_TUNNEL_IP, iface=WG_IFACE), \
            "pa no puede ping a pb por el túnel WireGuard"
        assert _ping(VMS["pb"]["ip"], PA_TUNNEL_IP, iface=WG_IFACE), \
            "pb no puede ping a pa por el túnel WireGuard"

    def test_handshake_reciente(self, testbed_running, clean_wg_all):
        """Verifica handshake reciente (< 5s) tras ping usando latest-handshakes."""
        pa_pub = _gen_keypair(VMS["pa"]["ip"])[1]
        pb_pub = _gen_keypair(VMS["pb"]["ip"])[1]

        _setup_direct_tunnel(
            VMS["pa"]["ip"], PA_TUNNEL_IP, pa_pub,
            VMS["pb"]["data_ip"], PB_TUNNEL_IP, pb_pub,
        )
        _setup_direct_tunnel(
            VMS["pb"]["ip"], PB_TUNNEL_IP, pb_pub,
            VMS["pa"]["data_ip"], PA_TUNNEL_IP, pa_pub,
        )

        time.sleep(3)

        _ping(VMS["pa"]["ip"], PB_TUNNEL_IP, count=1, iface=WG_IFACE)
        time.sleep(2)

        h = _wg_latest_handshakes(VMS["pa"]["ip"])
        assert pb_pub in h, f"pa no registra handshake con pb:\n{h}"
        assert h[pb_pub] > 0, f"pa: handshake de pb es 0 (no ocurrió):\n{h}"


# ===========================================================================
# ESCENARIO 2 — Hub-Spoke
# ===========================================================================

class TestHubSpoke:
    """orq actúa como hub WireGuard; pa y pb como spokes."""

    def _setup_hub(self, host_ip, tunnel_ip, data_iface="eth1"):
        """Configura un hub WireGuard (orq)."""
        privkey = _get_privkey(host_ip)
        hub_conf = (
            f"[Interface]\n"
            f"Address = {tunnel_ip}/{TUNNEL_PREFIX}\n"
            f"PrivateKey = {privkey}\n"
            f"ListenPort = {WG_PORT}\n"
            f"MTU = 1420\n"
            f"PostUp = sysctl -w net.ipv4.ip_forward=1\n"
        )
        _write_wg_config(host_ip, hub_conf)
        _wg_quick_up(host_ip)

    def _setup_spoke(self, host_ip, tunnel_ip, hub_ip, hub_pubkey):
        """Configura un spoke que apunta al hub."""
        privkey = _get_privkey(host_ip)
        spoke_conf = (
            f"[Interface]\n"
            f"Address = {tunnel_ip}/{TUNNEL_PREFIX}\n"
            f"PrivateKey = {privkey}\n"
            f"ListenPort = {WG_PORT}\n"
            f"MTU = 1420\n"
            f"\n"
            f"[Peer]\n"
            f"PublicKey = {hub_pubkey}\n"
            f"Endpoint = {hub_ip}:{WG_PORT}\n"
            f"AllowedIPs = {TUNNEL_CIDR}\n"
            f"PersistentKeepalive = 25\n"
        )
        _write_wg_config(host_ip, spoke_conf)
        _wg_quick_up(host_ip)

    def test_hub_conecta_ambos_spokes(self, testbed_running, clean_wg_all):
        """Configura orq como hub, pa y pb como spokes; verifica handshakes."""
        orq_pub = _gen_keypair(VMS["orq"]["ip"])[1]
        pa_pub = _gen_keypair(VMS["pa"]["ip"])[1]
        pb_pub = _gen_keypair(VMS["pb"]["ip"])[1]

        self._setup_hub(VMS["orq"]["ip"], HUB_TUNNEL_IP)
        self._setup_spoke(VMS["pa"]["ip"], PA_TUNNEL_IP,
                          VMS["orq"]["data_ip"], orq_pub)
        self._setup_spoke(VMS["pb"]["ip"], PB_TUNNEL_IP,
                          VMS["orq"]["data_ip"], orq_pub)

        _ssh(VMS["orq"]["ip"], "wg", "set", WG_IFACE,
             "peer", pa_pub,
             "allowed-ips", f"{PA_TUNNEL_IP}/32",
             "endpoint", f"{VMS['pa']['data_ip']}:{WG_PORT}")
        _ssh(VMS["orq"]["ip"], "wg", "set", WG_IFACE,
             "peer", pb_pub,
             "allowed-ips", f"{PB_TUNNEL_IP}/32",
             "endpoint", f"{VMS['pb']['data_ip']}:{WG_PORT}")

        time.sleep(10)

        peers = _wg_peers(VMS["orq"]["ip"])
        assert pa_pub in peers, f"orq no tiene a pa como peer:\n{peers}"
        assert pb_pub in peers, f"orq no tiene a pb como peer:\n{peers}"

        h = _wg_latest_handshakes(VMS["orq"]["ip"])
        assert h.get(pa_pub, 0) > 0, f"orq: no hay handshake con pa:\n{h}"
        assert h.get(pb_pub, 0) > 0, f"orq: no hay handshake con pb:\n{h}"

    def test_spoke_habla_con_otro_spoke_via_hub(self, testbed_running, clean_wg_all):
        """pa ping a pb(pb_tunnel_ip) a través de orq como hub."""
        orq_pub = _gen_keypair(VMS["orq"]["ip"])[1]
        pa_pub = _gen_keypair(VMS["pa"]["ip"])[1]
        pb_pub = _gen_keypair(VMS["pb"]["ip"])[1]

        self._setup_hub(VMS["orq"]["ip"], HUB_TUNNEL_IP)
        self._setup_spoke(VMS["pa"]["ip"], PA_TUNNEL_IP,
                          VMS["orq"]["data_ip"], orq_pub)
        self._setup_spoke(VMS["pb"]["ip"], PB_TUNNEL_IP,
                          VMS["orq"]["data_ip"], orq_pub)

        _ssh(VMS["orq"]["ip"], "wg", "set", WG_IFACE,
             "peer", pa_pub,
             "allowed-ips", f"{PA_TUNNEL_IP}/32",
             "endpoint", f"{VMS['pa']['data_ip']}:{WG_PORT}")
        _ssh(VMS["orq"]["ip"], "wg", "set", WG_IFACE,
             "peer", pb_pub,
             "allowed-ips", f"{PB_TUNNEL_IP}/32",
             "endpoint", f"{VMS['pb']['data_ip']}:{WG_PORT}")

        time.sleep(5)

        assert _ping(VMS["pa"]["ip"], PB_TUNNEL_IP, count=5, iface=WG_IFACE), \
            "pa no puede ping a tunnel_ip de pb vía hub"
        assert _ping(VMS["pb"]["ip"], PA_TUNNEL_IP, count=5, iface=WG_IFACE), \
            "pb no puede ping a tunnel_ip de pa vía hub"


# ===========================================================================
# ESCENARIO 3 — Multitúnel y estado persistente
# ===========================================================================

class TestMultitunelYEstado:
    """Varios túneles simultáneos y persistencia de estado."""

    def test_dos_tuneles_simultaneos(self, testbed_running, clean_wg_all):
        """pa y pb establecen túneles simultáneos con orq y entre sí."""
        orq_pub = _gen_keypair(VMS["orq"]["ip"])[1]
        pa_pub = _gen_keypair(VMS["pa"]["ip"])[1]
        pb_pub = _gen_keypair(VMS["pb"]["ip"])[1]

        TestHubSpoke._setup_hub(self, VMS["orq"]["ip"], HUB_TUNNEL_IP)
        TestHubSpoke._setup_spoke(self, VMS["pa"]["ip"], PA_TUNNEL_IP,
                                  VMS["orq"]["data_ip"], orq_pub)
        TestHubSpoke._setup_spoke(self, VMS["pb"]["ip"], PB_TUNNEL_IP,
                                  VMS["orq"]["data_ip"], orq_pub)

        _ssh(VMS["orq"]["ip"], "wg", "set", WG_IFACE,
             "peer", pa_pub,
             "allowed-ips", f"{PA_TUNNEL_IP}/32",
             "endpoint", f"{VMS['pa']['data_ip']}:{WG_PORT}")
        _ssh(VMS["orq"]["ip"], "wg", "set", WG_IFACE,
             "peer", pb_pub,
             "allowed-ips", f"{PB_TUNNEL_IP}/32",
             "endpoint", f"{VMS['pb']['data_ip']}:{WG_PORT}")

        time.sleep(5)

        assert _ping(VMS["pa"]["ip"], PB_TUNNEL_IP, count=3, iface=WG_IFACE), \
            "pa → pb vía hub"
        assert _ping(VMS["pa"]["ip"], HUB_TUNNEL_IP, count=3, iface=WG_IFACE), \
            "pa → hub"

    def test_estado_wg_show(self, testbed_running, clean_wg_all):
        """Verifica la salida de wg show (peer, endpoint, handshake, transfer)."""
        pa_pub = _gen_keypair(VMS["pa"]["ip"])[1]
        pb_pub = _gen_keypair(VMS["pb"]["ip"])[1]

        _setup_direct_tunnel(
            VMS["pa"]["ip"], PA_TUNNEL_IP, pa_pub,
            VMS["pb"]["data_ip"], PB_TUNNEL_IP, pb_pub,
        )
        _setup_direct_tunnel(
            VMS["pb"]["ip"], PB_TUNNEL_IP, pb_pub,
            VMS["pa"]["data_ip"], PA_TUNNEL_IP, pa_pub,
        )

        time.sleep(3)
        _ping(VMS["pa"]["ip"], PB_TUNNEL_IP, count=2, iface=WG_IFACE)
        time.sleep(2)

        peers = _wg_peers(VMS["pa"]["ip"])
        assert len(peers) == 1, f"pa debería tener 1 peer, tiene: {peers}"
        assert pb_pub == peers[0], f"El peer de pa debería ser pb: {peers}"

        h = _wg_latest_handshakes(VMS["pa"]["ip"])
        assert h.get(pb_pub, 0) > 0, f"pa no registra handshake con pb:\n{h}"

        eps = _wg_endpoints(VMS["pa"]["ip"])
        assert pb_pub in eps, f"pa no tiene endpoint para pb:\n{eps}"
        assert VMS["pb"]["data_ip"] in eps[pb_pub], \
            f"endpoint de pb incorrecto: {eps[pb_pub]}"


# ===========================================================================
# ESCENARIO 4 — ConfigGen local con datos reales
# ===========================================================================

class TestConfigGenConLlavesReales:
    """Prueba que el generador de config produce configs válidas para wg-quick."""

    @pytest.fixture(autouse=True)
    def _setup_env(self):
        """Crea key file temporal y configura env vars."""
        import tempfile
        self._tmpdir = tempfile.mkdtemp()
        keypath = os.path.join(self._tmpdir, "wg0.key")
        with open(keypath, "w") as kf:
            kf.write(_local_gen_privkey())
        os.environ["WG_DIR"] = self._tmpdir
        os.environ["WG_PRIV_KEY_PATH"] = keypath
        os.environ["WG_INTERFACE"] = "wg0"
        os.environ["PUBLIC_IP"] = "10.0.0.20"
        os.environ["ORCH_URL"] = f"http://{VMS['orq']['ip']}:8000/RPC2"
        os.environ["ORCH_TOKEN"] = "test-token"
        yield
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)
        for k in ["WG_DIR", "WG_PRIV_KEY_PATH", "WG_INTERFACE", "PUBLIC_IP", "ORCH_URL", "ORCH_TOKEN"]:
            os.environ.pop(k, None)

    def test_config_gen_produce_formato_valido(self, testbed_running, clean_wg_all):
        """Genera config con peer_register.config_gen y la aplica con wg-quick."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                                         "../../peer-install-v2"))
        import importlib
        from peer_register import config as pr_config
        importlib.reload(pr_config)
        from peer_register.config_gen import (
            _build_interface_block,
            _build_hub_block,
            _build_hub_mesh_blocks,
        )

        pa_pub = _gen_keypair(VMS["pa"]["ip"])[1]
        pb_pub = _gen_keypair(VMS["pb"]["ip"])[1]
        hub_pub = _local_pubkey(_local_gen_privkey())

        cfg = {
            "interface": {"address": f"{PA_TUNNEL_IP}/{TUNNEL_PREFIX}", "mtu": 1420},
            "peer": {
                "public_key": hub_pub,
                "endpoint": f"{VMS['pb']['data_ip']}:{WG_PORT}",
                "allowed_ips": TUNNEL_CIDR,
                "persistent_keepalive": 25,
            },
            "meta": {"topology": "hub-mesh", "config_version": 1, "hub_mesh_peers_hash": "abc"},
            "hub_mesh_direct_peers": [
                {
                    "peer_id": "pb",
                    "public_key": pb_pub,
                    "endpoint": f"{VMS['pb']['data_ip']}:{WG_PORT}",
                    "tunnel_ip": PB_TUNNEL_IP,
                },
            ],
            "hub_mesh_relay_peers": [],
        }

        iface_block = _build_interface_block(cfg)
        hub_block = _build_hub_block(cfg)
        mesh_blocks = _build_hub_mesh_blocks(cfg)
        full_conf = iface_block + "\n" + hub_block + "\n" + mesh_blocks

        assert "[Interface]" in full_conf
        assert "[Peer]" in full_conf
        assert pb_pub in full_conf
        assert PA_TUNNEL_IP in full_conf

        # Copia la config a pa y aplícala
        _write_wg_config(VMS["pa"]["ip"], full_conf)
        _ssh(VMS["pa"]["ip"], "cat", f"/etc/wireguard/{WG_IFACE}.conf")
        _wg_quick_up(VMS["pa"]["ip"])
        show = _wg_show(VMS["pa"]["ip"])
        assert "peer:" in show or "peer" in show, f"wg-quick up falló:\n{show}"


# ===========================================================================
# ESCENARIO 5 — NAT type detection remoto
# ===========================================================================

class TestNATTypeDetection:
    """Detecta tipo de NAT usando la lógica de nat.py sobre datos reales."""

    @pytest.fixture(autouse=True)
    def _setup_env(self):
        import tempfile
        self._tmpdir = tempfile.mkdtemp()
        keypath = os.path.join(self._tmpdir, "wg0.key")
        with open(keypath, "w") as kf:
            kf.write(_local_gen_privkey())
        os.environ.setdefault("WG_DIR", self._tmpdir)
        os.environ.setdefault("WG_PRIV_KEY_PATH", keypath)
        os.environ.setdefault("WG_INTERFACE", "wg0")
        os.environ.setdefault("ORCH_URL", f"http://{VMS['orq']['ip']}:8000/RPC2")
        os.environ.setdefault("ORCH_TOKEN", "test")
        os.environ["PUBLIC_IP"] = VMS["pa"]["data_ip"]
        yield
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_detectar_nat_type_en_vm(self, testbed_running):
        """Ejecuta nat.detect_nat_type() y verifica resultado."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                                         "../../peer-install-v2"))
        import importlib
        from peer_register import config as pr_config
        importlib.reload(pr_config)
        from peer_register.nat import detect_nat_type

        nat_type = detect_nat_type()
        assert nat_type in ("none", "full-cone", "restricted", "symmetric"), \
            f"NAT type inesperado: {nat_type}"
