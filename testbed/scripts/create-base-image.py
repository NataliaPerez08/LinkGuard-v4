#!/usr/bin/env python3
"""
Crea imagen base Alpine Linux para testbed.
Usa QEMU + Alpine Virt ISO + pexpect para automatizar instalacion.
"""
import os, sys, subprocess, argparse, time, shutil, textwrap

BDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ISO = os.path.join(BDIR, "images", "alpine-virt-3.21.3-x86_64.iso")


def log(msg):
    print(f"[install] {msg}", flush=True)


def run(cmd, **kw):
    kw.setdefault("capture_output", False)
    kw.setdefault("text", True)
    return subprocess.run(cmd, check=True, **kw)


def create_via_qemu(raw_path: str):
    """Crea imagen usando QEMU + ISO + pexpect."""
    import pexpect

    log(f"Creando disco raw: {raw_path}")
    run(["qemu-img", "create", "-f", "raw", raw_path, "2G"])

    qemu_cmd = [
        "qemu-system-x86_64", "-nographic",
        "-m", "256M",
        "-smp", "1",
        "-drive", f"file={raw_path},format=raw,if=virtio",
        "-cdrom", ISO,
        "-boot", "d",
        "-device", "virtio-net,netdev=net0",
        "-netdev", "user,id=net0",
    ]
    log("Iniciando QEMU...")
    child = pexpect.spawn(" ".join(qemu_cmd), timeout=120,
                          encoding="utf-8", codec_errors="replace")
    child.logfile = sys.stdout

    try:
        # Esperar login prompt de la ISO live
        child.expect("localhost login:", timeout=60)
        child.sendline("root")
        child.expect("localhost:~#", timeout=10)

        # Crear answer file linea por linea via heredoc
        # Nota: INTERFACESOPTS usa \n literal (backslash-n) que setup-alpine
        # interpreta como separador de lineas en /etc/network/interfaces
        log("Creando answer file para setup-alpine...")
        child.sendline("cat > /tmp/answers.txt << 'ANSWERS'")
        time.sleep(0.3)
        lines = [
            'KEYMAPOPTS="us us"',
            'HOSTNAMEOPTS="-n linkguard-base"',
            'INTERFACESOPTS="auto lo\\niface lo inet loopback\\nauto eth0\\niface eth0 inet dhcp"',
            'TIMEZONEOPTS="-z UTC"',
            'PROXYOPTS="none"',
            'APKREPOSOPTS="-1"',
            'SSHDOPTS="-c openssh"',
            'NTPOPTS="-c chrony"',
            'DISKOPTS="-m sys /dev/vda"',
            'ROOTPWD="linkguard-test"',
            'USEROPTS="no"',
        ]
        for line in lines:
            child.sendline(line)
            time.sleep(0.1)
        child.sendline("ANSWERS")
        child.expect("localhost:~#", timeout=10)

        log("Ejecutando setup-alpine -f /tmp/answers.txt ...")
        password = "linkguard-test"
        child.sendline("setup-alpine -f /tmp/answers.txt")
        time.sleep(1)

        while True:
            idx = child.expect_exact(
                [
                    "New password:",
                    "Retype password:",
                    "Bad password: too weak",
                    "Installation is complete",
                    "run: reboot",
                    "localhost:~#",
                    "(y/n) [n]",
                ],
                timeout=240,
            )
            if idx == 0:
                child.sendline(password)
            elif idx == 1:
                child.sendline(password)
            elif idx == 2:
                child.sendline(password)
            elif idx == 6:
                child.sendline("y")
            elif idx in (3, 4, 5):
                log("setup-alpine completado")
                break

        log("Apagando...")
        child.sendline("poweroff")
        child.expect(pexpect.EOF, timeout=30)
        child.close()

        # Fase 2: Instalar paquetes adicionales
        log("Fase 2: Instalando paquetes adicionales (wireguard-tools, python3, ethtool, iptables)...")
        qemu_boot_cmd = [
            "qemu-system-x86_64", "-nographic",
            "-m", "256M",
            "-smp", "1",
            "-drive", f"file={raw_path},format=raw,if=virtio",
            "-boot", "c",
            "-device", "virtio-net,netdev=net0",
            "-netdev", "user,id=net0",
        ]
        child = pexpect.spawn(" ".join(qemu_boot_cmd), timeout=120,
                              encoding="utf-8", codec_errors="replace")
        child.logfile = sys.stdout
        child.expect_exact("login:", timeout=60)
        child.sendline("root")
        child.expect_exact("Password:", timeout=20)
        child.sendline("linkguard-test")
        child.expect_exact("linkguard-base:~#", timeout=20)
        child.sendline(
            "sed -i '/^#*PermitRootLogin/d' /etc/ssh/sshd_config "
            "&& echo 'PermitRootLogin yes' >> /etc/ssh/sshd_config "
            "&& rc-update add sshd default "
            "&& rc-update add networking default "
            "&& rc-service sshd restart"
        )
        child.expect_exact("linkguard-base:~#", timeout=10)
        child.sendline("apk update && apk add wireguard-tools python3 ethtool iptables")
        child.expect_exact("linkguard-base:~#", timeout=120)
        child.sendline("poweroff")
        child.expect(pexpect.EOF, timeout=30)
        child.close()

    except Exception as e:
        log(f"ERROR: {e}")
        try:
            child.close()
        except Exception:
            pass
        return False

    log(f"Imagen creada: {raw_path}")
    return True


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--output",
                    default=os.path.join(BDIR, "images", "alpine-base.raw"))
    args = ap.parse_args()

    # Verificar que existe la ISO
    if not os.path.exists(ISO):
        log(f"ISO no encontrada: {ISO}")
        log("Descargala con: scripts/download-iso.sh")
        sys.exit(1)

    ok = create_via_qemu(args.output)
    sys.exit(0 if ok else 1)
