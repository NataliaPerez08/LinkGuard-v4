# Testbed de integración con QEMU + Alpine Linux

## Arquitectura general

```
Host (Parrot OS, KVM habilitado)
├── bridge br0 (192.168.100.1/24)    ← red de control (SSH, RPC)
├── bridge br1 (172.16.0.1/24)       ← red "internet" (túneles WireGuard)
├── bridge br2 (10.0.0.1/24)         ← red NAT (peer detrás de NAT)
│
├── VM: orq  (orchestrator + hub-agent)
│   └── eth0: br0 (192.168.100.10)
│   └── eth1: br1 (172.16.0.10)
│
├── VM: peer-a
│   ├── eth0: br0 (192.168.100.20)
│   └── eth1: br1 (172.16.0.20)   ← IP "pública" para WireGuard
│
├── VM: peer-b (directo — escenario 1)
│   ├── eth0: br0 (192.168.100.30)
│   └── eth1: br1 (172.16.0.30)   ← IP "pública" para WireGuard
│
└── VM: peer-b (NAT — escenarios 2 y 3)
    ├── eth0: br0 (192.168.100.30)
    └── eth1: br2 (10.0.0.30)     ← IP privada, sin ruteo directo a br1
```

## Topologías por escenario

### Escenario 1 — Todos reachables

```
VMs activas: orq, peer-a, peer-b-directo

orq (172.16.0.10) ←→ peer-a (172.16.0.20)
orq (172.16.0.10) ←→ peer-b-directo (172.16.0.30)
peer-a (172.16.0.20) ←→ peer-b-directo (172.16.0.30)

Topología: hub-mesh
Esperado: peer-a y peer-b-directo clasificados como "direct".
          wg show latest-handshakes muestra handshake entre ellos.
```

### Escenario 2 — Un peer detrás de NAT

```
VMs activas: orq, peer-a, peer-b-nat

orq (172.16.0.10) ←→ peer-a (172.16.0.20)
orq (172.16.0.10) ←→ peer-b-nat (10.0.0.30)  [vía reenvío en host]
peer-a (172.16.0.20) -/-> peer-b-nat (10.0.0.30)  [sin ruta directa]

Simulación NAT:
  - Host hace SNAT: 10.0.0.30 → 172.16.0.200 (IP pública ficticia del peer-b)
  - peer-b-nat tiene nat_type = "symmetric"
  - orquestador clasifica peer-b-nat como relay_only
  - Tráfico peer-a → peer-b-nat viaja orq → NAT → peer-b-nat
```

### Escenario 3 — Solo orquestador reachable

```
VMs activas: orq, peer-a-nat, peer-b-nat

orq (172.16.0.10) ←→ peer-a-nat (10.0.0.20)  [vía reenvío]
orq (172.16.0.10) ←→ peer-b-nat (10.0.0.30)  [vía reenvío]
peer-a-nat -/-> peer-b-nat  [sin ruta]
peer-b-nat -/-> peer-a-nat  [sin ruta]

Simulación NAT:
  - peer-a-nat: SNAT 10.0.0.20 → 172.16.0.201
  - peer-b-nat: SNAT 10.0.0.30 → 172.16.0.200
  - Ambos clasificados como relay_only
  - Todo tráfico peer→peer viaja por el orquestador
```

## Provisionamiento de las imágenes Alpine

### 1. Creación de imagen base

```bash
# Descargar Alpine virt (8 MB)
wget https://dl-cdn.alpinelinux.org/alpine/v3.21/releases/x86_64/alpine-virt-3.21.3-x86_64.iso

# Crear disco
qemu-img create -f qcow2 alpine-base.qcow2 512M

# Instalación manual única (o con respuesta automática via setup-alpine)
qemu-system-x86_64 -machine accel=kvm -m 256M \
  -cdrom alpine-virt-3.21.3-x86_64.iso \
  -drive file=alpine-base.qcow2,format=qcow2,if=virtio \
  -netdev user,id=net0 -device virtio-net,netdev=net0
```

Dentro de la VM (instalación):
```bash
setup-alpine
  # keyboard: us, us
  # hostname: alpine-base
  # interfaces: eth0 (dhcp)
  # dns: 8.8.8.8
  # root password: linkguard-test
  # timezone: UTC
  # mirror: 1 (random)
  # openssh: openssh
  # disk: vda (sys mode)

# Después de reiniciar, instalar dependencias
apk add wireguard-tools openrc
rc-update add wg-quick default

# Apagar VM para crear clones
poweroff
```

### 2. Creación de imágenes por rol

```bash
# Clonar para cada VM
for vm in orq peer-a peer-b-directo peer-b-nat; do
  qemu-img create -f qcow2 -b alpine-base.qcow2 -F qcow2 "$vm.qcow2" 512M
done
```

### 3. Primer arranque y configuración por rol

Usar `-nic` para la red de control (SSH) y `-serial` para consola:

```bash
# Script de lanzamiento genérico
launch-vm() {
  local name=$1; shift
  local mac_ctrl=$1; shift  # MAC para br0 (control)
  local mac_data=$1; shift  # MAC para br1/br2 (datos)
  local data_bridge=$1       # br1 o br2

  qemu-system-x86_64 -machine accel=kvm -m 256M \
    -name "$name" \
    -drive file="${name}.qcow2",format=qcow2,if=virtio \
    -nic tap,ifname="tap-${name}-ctrl",script=no,downscript=no,model=virtio-net,mac="$mac_ctrl" \
    -nic tap,ifname="tap-${name}-data",script=no,downscript=no,model=virtio-net,mac="$mac_data" \
    -nographic \
    -pidfile "/tmp/qemu-${name}.pid" &
}

# Antes de lanzar, crear taps y bridges en el host
setup-host-networking() {
  # Bridge de control
  ip link add br0 type bridge
  ip addr add 192.168.100.1/24 dev br0
  ip link set br0 up

  # Bridge de datos
  ip link add br1 type bridge
  ip addr add 172.16.0.1/24 dev br1
  ip link set br1 up

  # Bridge NAT
  ip link add br2 type bridge
  ip addr add 10.0.0.1/24 dev br2
  ip link set br2 up

  # NAT para br2 (simula internet con NAT)
  iptables -t nat -A POSTROUTING -s 10.0.0.0/24 -j MASQUERADE
  iptables -A FORWARD -i br2 -j ACCEPT
}
```

### 4. Configuración dentro de cada VM (vía SSH o serial)

Usar `expect` o `sshpass` para automatizar:

```bash
cat > /etc/network/interfaces <<EOF
auto lo
iface lo inet loopback

auto eth0
iface eth0 inet static
  address 192.168.100.10
  netmask 255.255.255.0
  gateway 192.168.100.1

auto eth1
iface eth1 inet static
  address 172.16.0.10
  netmask 255.255.255.0
EOF

# Copiar LinkGuard al VM
# Opción 1: mount 9p (virtio-fs)
# Opción 2: rsync vía SSH desde el host
# Opción 3: wget desde un servidor HTTP en el host
```

## Flujo de provisioning automatizado

```bash
# 1. Encender VMs
for vm in orq peer-a peer-b-directo; do
  launch-vm "$vm" ...
done

# 2. Esperar a que arranquen (ping a IPs de control)
for ip in 192.168.100.10 192.168.100.20 192.168.100.30; do
  until ping -c1 "$ip" &>/dev/null; do sleep 1; done
done

# 3. Copiar software
for ip in 192.168.100.20 192.168.100.30; do
  rsync -r peer-install-v2/ root@$ip:/usr/local/linkguard-peer/
done
rsync -r orchestrator-install-v2/ root@192.168.100.10:/usr/local/linkguard-orch/

# 4. Instalar dependencias vía SSH
ssh root@192.168.100.10 "apk add wireguard-tools python3 py3-pip"
ssh root@192.168.100.10 "pip3 install pyjwt[crypto] defusedxml"

# 5. Configurar y arrancar servicio
ssh root@192.168.100.10 "ORCH_TOKEN=... ADMIN_TOKEN=... \
  python3 /usr/local/linkguard-orch/orchestrator.py &"

# 6. Ejecutar escenario de prueba
```

## Tests automatizados (pytest + SSH)

```python
# tests/test_qemu_reachability.py
import subprocess
import time

HOST = "root@192.168.100."
ORQ = f"{HOST}10"
PEER_A = f"{HOST}20"
PEER_B = f"{HOST}30"

def ssh(host, cmd):
    return subprocess.run(
        ["ssh", "-o", "StrictHostKeyChecking=no",
         "-o", "UserKnownHostsFile=/dev/null",
         host, cmd],
        capture_output=True, text=True, check=True
    ).stdout.strip()

class TestQemuReachability:

    def test_escenario_1_todos_directos(self):
        """Verificar handshake WireGuard entre peer-a y peer-b-directo."""
        # peer-a hace heartbeat
        ssh(PEER_A, "python3 /usr/local/linkguard-peer/wg-auto-register.py run --interval 10 &")

        # peer-b-directo hace heartbeat
        ssh(PEER_B, "python3 /usr/local/linkguard-peer/wg-auto-register.py run --interval 10 &")

        time.sleep(15)  # esperar heartbeats + wg syncconf

        # peer-a debe tener handshake con peer-b-directo
        hs = ssh(PEER_A, "wg show wg0 latest-handshakes")
        assert "pk-peer-b-directo" in hs
        ts = int(hs.split()[-1])
        assert ts > 0 and (time.time() - ts) < 180

        # peer-b-directo debe tener handshake con peer-a
        hs = ssh(PEER_B, "wg show wg0 latest-handshakes")
        assert "pk-peer-a" in hs

    def test_escenario_2_un_peer_detras_nat(self):
        """peer-a tiene handshake con orq y peer-b-nat (via relay)."""
        # Configurar peer-b-nat con public_ip falsa + nat_type symmetric
        ssh(PEER_B, """
cat > /etc/linkguard/peer.env <<EOF
PUBLIC_IP=172.16.0.200
WG_LISTEN_PORT=51820
ORCH_URL=http://192.168.100.10:8000/RPC2
EOF
""")
        ssh(PEER_B, "python3 /usr/local/linkguard-peer/wg-auto-register.py run --interval 10 &")
        time.sleep(15)

        hs_a = ssh(PEER_A, "wg show wg0 latest-handshakes")
        hs_b = ssh(PEER_B, "wg show wg0 latest-handshakes")

        # peer-a NO tiene handshake directo con peer-b-nat
        # (porque peer-b-nat está en relay_only)
        assert not any("pk-peer-b-nat" in line for line in hs_a.splitlines())

        # peer-b-nat tiene handshake con orq (vía relay)
        assert "pk-orq" in hs_b

    def test_escenario_3_solo_orquestador_reachable(self):
        """Ningún peer tiene handshake directo con otro peer."""
        # Configurar ambos peers con IPs privadas
        for vm in [PEER_A, PEER_B]:
            ssh(vm, "export PUBLIC_IP=10.0.0.X")
            ssh(vm, "export NAT_TYPE=symmetric")
            ssh(vm, "python3 ... run &")

        time.sleep(15)
        hs_a = ssh(PEER_A, "wg show wg0 latest-handshakes")
        hs_b = ssh(PEER_B, "wg show wg0 latest-handshakes")

        # Solo hay handshake con el orq, no entre peers
        assert "pk-orq" in hs_a
        assert "pk-orq" in hs_b
        assert not any("pk-peer" in line for line in hs_a.splitlines())
        assert not any("pk-peer" in line for line in hs_b.splitlines())
```

## Script orquestador de escenarios

```bash
#!/bin/bash
# run-scenario.sh — lanza VMs según el escenario

SCENARIO=${1:-1}

teardown() {
  for pid in /tmp/qemu-*.pid; do
    [ -f "$pid" ] && kill "$(cat "$pid")" 2>/dev/null
  done
  for tap in tap-*; do
    ip link del "$tap" 2>/dev/null
  done
}

setup_scenario_1() {
  launch-vm orq  52:54:00:01:01:10 br0 br1
  launch-vm peer-a 52:54:00:01:01:20 br0 br1
  launch-vm peer-b-directo 52:54:00:01:01:30 br0 br1
}

setup_scenario_2() {
  launch-vm orq  52:54:00:02:01:10 br0 br1
  launch-vm peer-a 52:54:00:02:01:20 br0 br1
  launch-vm peer-b-nat 52:54:00:02:01:30 br0 br2
  # Regla NAT en host
  iptables -t nat -A PREROUTING -i br1 -d 172.16.0.200 \
    -j DNAT --to-destination 10.0.0.30
}

setup_scenario_3() {
  launch-vm orq  52:54:00:03:01:10 br0 br1
  launch-vm peer-a-nat 52:54:00:03:01:20 br0 br2
  launch-vm peer-b-nat 52:54:00:03:01:30 br0 br2
}

case $SCENARIO in
  1) setup_scenario_1 ;;
  2) setup_scenario_2 ;;
  3) setup_scenario_3 ;;
esac

# Esperar a que estén listas
for ip in 192.168.100.10 192.168.100.20 192.168.100.30; do
  until ping -c1 -W1 "$ip" &>/dev/null; do sleep 1; done
done

# Provisionar
./provision.sh "$SCENARIO"

# Ejecutar tests
python3 -m pytest tests/test_qemu_reachability.py -v -k "escenario_$SCENARIO"
```

## Requisitos del host

| Componente | Mínimo | Recomendado |
|---|---|---|
| RAM (host) | 4 GB | 8 GB |
| Discos | 5 GB libres | 10 GB SSD |
| Kernel | Linux 5.6+ | Linux 6.x |
| Módulos | `wireguard`, `kvm`, `tap`, `bridge` | `tun`, `iptables`, `nf_nat` |
| Paquetes | `qemu-system-x86_64`, `qemu-img`, `bridge-utils` | + `iptables`, `sshpass`, `python3-pytest` |

## Limitaciones conocidas

1. **Rendimiento WireGuard**: QEMU-user con virtio-net tiene overhead. Los handshakes pueden tardar más que en bare-metal.
2. **Sincronización temporal**: VMs QEMU sin KVM TIME ajuste pueden derivar. Ajustar `-rtc base=localtime`.
3. **Detección de NAT real**: `detect_nat_type()` abre sockets UDP reales. En QEMU user-mode, los puertos externos son los del host. En tap, funcionan correctamente.
4. **Teardown**: Los taps pueden quedar huérfanos si el script se interrumpe. Usar `trap teardown EXIT` en el script principal.
