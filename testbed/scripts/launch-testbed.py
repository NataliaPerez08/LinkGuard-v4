#!/usr/bin/env python3
"""
Lanza el testbed QEMU completo: bridges, VMs, provisioning, tests.
Requiere: sudo para bridges/taps, dnsmasq, sshpass.

Modo integrado opcional con orquestador real:
  - export TESTBED_REAL_ORCH_HOST=101.44.24.91
  - export TESTBED_REAL_ORCH_PASS=... 
  - python3 launch-testbed.py up-real
"""
import json
import os, sys, subprocess, time, signal, atexit, tempfile, argparse
import xmlrpc.client

BDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW  = os.path.join(BDIR, "images", "alpine-base.raw")
PID_DIR = os.path.join(BDIR, "pids")
SSH_KEY = os.path.join(BDIR, "ssh", "id_ed25519")
PASS    = "linkguard-test"
SSH_OPTS = ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null", "-o", "ConnectTimeout=5"]
REAL_ORCH_HOST = os.environ.get("TESTBED_REAL_ORCH_HOST", "101.44.24.91")
REAL_ORCH_USER = os.environ.get("TESTBED_REAL_ORCH_USER", "root")
REAL_ORCH_PASS = os.environ.get("TESTBED_REAL_ORCH_PASS", "")
REAL_ORCH_URL = os.environ.get("TESTBED_REAL_ORCH_URL", f"http://{REAL_ORCH_HOST}:8000/RPC2")
REAL_ORCH_PORT = os.environ.get("TESTBED_REAL_ORCH_PORT", "51820")
REAL_PEER_IDS = {"orq": "qemu-orq", "pa": "qemu-pa", "pb": "qemu-pb"}
PEER_BUNDLE_DIR = os.path.abspath(os.path.join(BDIR, "..", "peer-install-v2"))
_REAL_ADMIN_TOKEN = None

VMS = {
    "orq": {"macs": ["52:54:00:01:00:10","52:54:00:01:01:10","52:54:00:01:02:10"],
            "taps": ["tap0","tap1","tap2"], "ip": "192.168.100.10",
            "data_ip": "10.0.0.10", "img": "orq.raw"},
    "pa":  {"macs": ["52:54:00:01:00:20","52:54:00:01:01:20","52:54:00:01:02:20"],
            "taps": ["tap3","tap4","tap5"], "ip": "192.168.100.20",
            "data_ip": "10.0.0.20", "img": "pa.raw"},
    "pb":  {"macs": ["52:54:00:01:00:30","52:54:00:01:01:30","52:54:00:01:02:30"],
            "taps": ["tap6","tap7","tap8"], "ip": "192.168.100.30",
            "data_ip": "10.0.0.30", "img": "pb.raw"},
}


def sudo(cmd, input_pass=None, **kw):
    """Ejecuta comando con sudo, opcionalmente pasando password via stdin."""
    full = ["sudo", "-S"] + cmd if input_pass else ["sudo"] + cmd
    if input_pass:
        kw.setdefault("input", input_pass + "\n")
        kw.setdefault("text", True)
    kw.setdefault("check", True)
    subprocess.run(full, **kw)


def run(cmd, **kw):
    kw.setdefault("text", True)
    return subprocess.run(cmd, check=False, **kw)


def setup_network(passwd):
    log("Creando bridges y taps...")
    sudo(["bash", os.path.join(BDIR, "scripts", "setup-network.sh"), "create"],
         input_pass=passwd)

    # DHCP en br0 via dnsmasq (background)
    run(["pkill", "-f", "dnsmasq.*br0"])
    dnsmasq_cmd = [
        "dnsmasq", "--interface=br0", "--bind-interfaces",
        "--dhcp-range=192.168.100.100,192.168.100.200,12h",
        "--dhcp-host=52:54:00:01:00:10,192.168.100.10",
        "--dhcp-host=52:54:00:01:00:20,192.168.100.20",
        "--dhcp-host=52:54:00:01:00:30,192.168.100.30",
        "--domain=linkguard.test", "--no-resolv",
    ]
    # Start dnsmasq as background process with sudo
    subprocess.Popen(
        ["sudo", "-S"] + dnsmasq_cmd,
        stdin=subprocess.PIPE, text=True
    ).communicate(input=passwd + "\n")
    time.sleep(2)
    log("DHCP en br0 listo")


def teardown_network(passwd):
    log("Destruyendo bridges y taps...")
    sudo(["pkill", "-f", "dnsmasq.*br0"], input_pass=passwd, check=False)
    sudo(["bash", os.path.join(BDIR, "scripts", "setup-network.sh"), "destroy"],
         input_pass=passwd)


def launch_vm(role, passwd):
    cfg = VMS[role]
    img_path = os.path.join(BDIR, "images", cfg["img"])
    pidfile = os.path.join(PID_DIR, f"{role}.pid")

    if not os.path.exists(img_path):
        log(f"Creando imagen {cfg['img']}...")
        run(["cp", RAW, img_path])
        # Resize si queremos mas espacio
        run(["qemu-img", "resize", img_path, "+1G"])

    cmd = [
        "qemu-system-x86_64", "-nographic", "-m", "256M", "-smp", "1",
        "-drive", f"file={img_path},format=raw,if=virtio",
    ]
    for i in range(3):
        cmd += [
            "-netdev", f"tap,id=net{i},ifname={cfg['taps'][i]},script=no,downscript=no",
            "-device", f"virtio-net,netdev=net{i},mac={cfg['macs'][i]}",
        ]
    cmd += ["-pidfile", pidfile]

    logpath = f"/tmp/lg-{role}.log"
    log(f"Lanzando {role} (log: {logpath})...")
    with open(logpath, "w") as lf:
        proc = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT,
                                preexec_fn=os.setsid)
    return proc


def wait_ssh(ip, timeout=120):
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = run(["sshpass", "-p", PASS, "ssh", *SSH_OPTS, f"root@{ip}", "true"],
                capture_output=True)
        if r.returncode == 0:
            return True
        time.sleep(3)
    return False


def ssh(ip, *cmd):
    return run(["sshpass", "-p", PASS, "ssh", *SSH_OPTS, f"root@{ip}"] + list(cmd))


def ssh_script(ip, script: str, timeout: int = 300, capture_output: bool = False):
    return subprocess.run(
        ["sshpass", "-p", PASS, "ssh", *SSH_OPTS, f"root@{ip}", "sh"],
        input=script,
        text=True,
        timeout=timeout,
        capture_output=capture_output,
        check=False,
    )


def scp(src, dest_ip, dest_path):
    return run(["sshpass", "-p", PASS, "scp", *SSH_OPTS, "-r", src, f"root@{dest_ip}:{dest_path}"])


def real_ssh(*cmd):
    if not REAL_ORCH_PASS:
        raise RuntimeError("Define TESTBED_REAL_ORCH_PASS para integrar el testbed con el orquestador real")
    return run(["sshpass", "-p", REAL_ORCH_PASS, "ssh", *SSH_OPTS, f"{REAL_ORCH_USER}@{REAL_ORCH_HOST}"] + list(cmd), capture_output=True)


def get_real_admin_token() -> str:
    global _REAL_ADMIN_TOKEN
    if _REAL_ADMIN_TOKEN:
        return _REAL_ADMIN_TOKEN
    r = real_ssh("cat", "/etc/linkguard/secrets")
    if r.returncode != 0 or not r.stdout.strip():
        raise RuntimeError(f"No pude leer ADMIN_TOKEN del orquestador real:\n{r.stderr}\n{r.stdout}")
    for line in r.stdout.splitlines():
        if line.startswith("ADMIN_TOKEN="):
            _REAL_ADMIN_TOKEN = line.split("=", 1)[1].strip()
            break
    if not _REAL_ADMIN_TOKEN:
        raise RuntimeError("No encontré ADMIN_TOKEN en /etc/linkguard/secrets del orquestador real")
    return _REAL_ADMIN_TOKEN


def ensure_real_peer_token(peer_id: str) -> str:
    admin_token = get_real_admin_token()
    client = xmlrpc.client.ServerProxy(REAL_ORCH_URL, allow_none=True)
    try:
        data = client.__getattr__("orch.user-create")(peer_id, 50, 10, {}, admin_token)
    except xmlrpc.client.Fault as exc:
        if "already exists" not in str(exc):
            raise RuntimeError(f"No pude crear usuario remoto {peer_id}: {exc}") from exc
        data = client.__getattr__("orch.issue-user-token")(peer_id, admin_token)
    return str(data["token"])


def configure_vm_as_real_peer(role: str) -> None:
    cfg = VMS[role]
    peer_id = REAL_PEER_IDS[role]
    token = ensure_real_peer_token(peer_id)
    peer_env = "\n".join([
        f"ORCH_URL={REAL_ORCH_URL}",
        f"ORCH_TOKEN={token}",
        f"PEER_ID={peer_id}",
        f"USER_ID={peer_id}",
        "WG_LISTEN_PORT=51820",
        "PEER_TAGS=qemu,lab",
        "WG_JWT_TTL=86400",
        "WG_KEEPALIVE=15",
        "",
    ])

    bundle_dest = "/root/peer-install-v2"
    log(f"Integrando {role} con orquestador real {REAL_ORCH_HOST} como {peer_id}...")
    scp(PEER_BUNDLE_DIR, cfg["ip"], "/root/")
    install_script = f"""set -e
install -d -m 0755 /etc/linkguard
cat > /etc/linkguard/peer.env <<'EOF'
{peer_env}EOF
if command -v apk >/dev/null 2>&1; then
    apk add --no-cache bash python3 curl ca-certificates wireguard-tools || true
fi
bash {bundle_dest}/install.sh
"""
    r = ssh_script(cfg["ip"], install_script, timeout=900, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(
            f"No pude instalar peer integrado en {role}: retorno {r.returncode}\n{r.stdout}\n{r.stderr}"
        )


def integrate_with_real_orchestrator() -> None:
    if not REAL_ORCH_PASS:
        raise RuntimeError("TESTBED_REAL_ORCH_PASS es obligatorio para up-real/sync-real")
    for role in ["orq", "pa", "pb"]:
        configure_vm_as_real_peer(role)
    log(f"VMs del testbed integradas con {REAL_ORCH_URL}")


def provision_vm(role):
    cfg = VMS[role]
    ip = cfg["ip"]
    log(f"Esperando SSH en {role} ({ip})...")
    if not wait_ssh(ip):
        log(f"ERROR: no SSH a {role}")
        return False

    # Configurar networking estatico via script embebido
    script = f"""cat > /etc/network/interfaces << 'NETEOF'
auto lo
iface lo inet loopback
auto eth0
iface eth0 inet static
    address {ip}/24
    gateway 192.168.100.1
auto eth1
iface eth1 inet static
    address {cfg['data_ip']}/24
auto eth2
iface eth2 inet dhcp
NETEOF
hostname {role}
echo "{role}" > /etc/hostname
rc-service networking restart
"""
    ssh_script(ip, script)
    log(f"{role} provisionado ({ip})")
    return True


def log(msg):
    print(f"[testbed] {msg}", flush=True)


# ---------- Main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", nargs="?", default="up",
                    choices=["up", "up-real", "sync-real", "down", "ssh", "status"])
    args, extra = ap.parse_known_args()

    # Read password from env or prompt
    passwd = os.environ.get("SUDO_PASS", "atidesa15")
    if args.action in ("up", "up-real"):
        setup_network(passwd)
        os.makedirs(PID_DIR, exist_ok=True)
        procs = {}
        for role in ["orq", "pa", "pb"]:
            p = launch_vm(role, passwd)
            procs[role] = p
        time.sleep(10)  # wait for initial boot
        ok = True
        for role in ["orq", "pa", "pb"]:
            ok = provision_vm(role) and ok
        if not ok:
            log("ERROR: provisioning incompleto; revisa los logs de QEMU y la imagen base")
            sys.exit(1)
        if args.action == "up-real":
            integrate_with_real_orchestrator()
        log("Testbed listo!")
        log("Usa: python3 launch-testbed.py ssh <role> <cmd>")
        log("Ej:  python3 launch-testbed.py ssh orq wg show")

    elif args.action == "sync-real":
        integrate_with_real_orchestrator()

    elif args.action == "down":
        teardown_network(passwd)
        for role in ["orq", "pa", "pb"]:
            pidfile = os.path.join(PID_DIR, f"{role}.pid")
            if os.path.exists(pidfile):
                pid = open(pidfile).read().strip()
                run(["kill", pid])
                os.remove(pidfile)
        log("Testbed detenido")

    elif args.action == "status":
        for role in ["orq", "pa", "pb"]:
            pidfile = os.path.join(PID_DIR, f"{role}.pid")
            if os.path.exists(pidfile):
                pid = open(pidfile).read().strip()
                alive = os.path.exists(f"/proc/{pid}")
                cfg = VMS[role]
                log(f"{role}: PID={pid} {'vivo' if alive else 'muerto'} IP={cfg['ip']}")
            else:
                log(f"{role}: detenido")

    elif args.action == "ssh":
        role = extra[0] if extra else "orq"
        cmd = extra[1:]
        ip = VMS[role]["ip"]
        if not cmd:
            cmd = ["sh", "-c", "hostname; ip addr show eth0 | grep inet; wg show"]
        r = ssh(ip, *cmd)
        sys.exit(r.returncode)


if __name__ == "__main__":
    main()
