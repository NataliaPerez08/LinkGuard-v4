# Pruebas de Topologías LinkGuard

## Objetivo

Este documento describe cómo probar y desmontar las tres topologías soportadas por LinkGuard:

- `hub-spoke`
- `mesh`
- `hub-mesh`

Explicación conceptual y diagramas:

- `docs/explicacion-topologias-linkguard.md`

Los ejemplos asumen:

- orquestador instalado en `101.44.24.91`
- `orch-cli` disponible en el orquestador
- `wg-auto-cli` disponible en cada peer
- red de prueba `default` con CIDR `10.20.30.0/24`

## Pre-requisitos comunes

En el orquestador:

```bash
ssh root@101.44.24.91
source /etc/linkguard/secrets
orch-cli health
orch-cli peer-list --admin-token "$ADMIN_TOKEN"
orch-cli net-list --admin-token "$ADMIN_TOKEN"
```

En cada peer:

```bash
systemctl status wg-auto-register
wg-auto-cli orch-health
wg-auto-cli mesh-status
ip -4 addr show dev wg0
wg show wg0
```

Matriz de peers de ejemplo:

- `peer-a`: `46.250.168.185`
- `peer-b`: `122.8.179.57`
- `peer-c`: `46.250.162.141`

IPs de túnel esperadas en el ejemplo actual:

- `peer-a`: `10.20.30.4`
- `peer-b`: `10.20.30.2`
- `peer-c`: `10.20.30.3`

## Hub-Spoke

### Montaje

En el orquestador:

```bash
source /etc/linkguard/secrets
orch-cli net-set-topology default hub-spoke --admin-token "$ADMIN_TOKEN"
orch-cli net-topology default --admin-token "$ADMIN_TOKEN"
```

En cada peer, forzar recarga:

```bash
systemctl restart wg-auto-register
sleep 5
wg-auto-cli mesh-status
```

### Validación

Qué debes ver:

- `wg-auto-cli mesh-status` muestra solo el bloque del HUB.
- `orch-cli mesh-peers default --admin-token "$ADMIN_TOKEN"` debe fallar porque no es una red mesh.
- Los peers se alcanzan entre sí a través del HUB.

Pruebas sugeridas:

```bash
ping -c 3 10.20.30.2
ping -c 3 10.20.30.3
```

En el HUB:

```bash
wg show wg-HUB
```

Verifica que cada peer tenga su `allowed ips` en `/32`.

### Desmontaje

En cada peer:

```bash
systemctl stop wg-auto-register
wg-quick down wg0 || true
wg-auto-cli unregister
```

En el orquestador:

```bash
source /etc/linkguard/secrets
orch-cli peer-list --admin-token "$ADMIN_TOKEN"
```

## Mesh

### Montaje

En el orquestador:

```bash
source /etc/linkguard/secrets
orch-cli net-set-topology default mesh --admin-token "$ADMIN_TOKEN"
orch-cli net-topology default --admin-token "$ADMIN_TOKEN"
orch-cli mesh-peers default --admin-token "$ADMIN_TOKEN"
```

En cada peer:

```bash
systemctl restart wg-auto-register
sleep 5
wg-auto-cli mesh-status
```

### Validación

Qué debes ver:

- `wg-auto-cli mesh-status` muestra bloques `[Peer]` adicionales para peers vivos.
- `orch-cli mesh-peers default --admin-token "$ADMIN_TOKEN"` devuelve una lista.
- Si todos los peers son alcanzables, habrá handshakes directos peer-a/peer-b, peer-a/peer-c, peer-b/peer-c.

Pruebas sugeridas:

```bash
ping -c 3 10.20.30.4
ping -c 3 10.20.30.2
ping -c 3 10.20.30.3
wg-auto-cli mesh-status
```

### Desmontaje

Volver a la topología básica:

```bash
source /etc/linkguard/secrets
orch-cli net-set-topology default hub-spoke --admin-token "$ADMIN_TOKEN"
```

Si quieres desmontar por completo:

```bash
systemctl stop wg-auto-register
wg-quick down wg0 || true
wg-auto-cli unregister
```

## Hub-Mesh

### Montaje

En el orquestador:

```bash
source /etc/linkguard/secrets
orch-cli net-set-topology default hub-mesh --admin-token "$ADMIN_TOKEN"
orch-cli peer-reachability default --admin-token "$ADMIN_TOKEN"
```

En cada peer:

```bash
systemctl restart wg-auto-register
sleep 5
wg-auto-cli mesh-status
```

### Validación

Qué debes ver:

- `orch-cli peer-reachability default --admin-token "$ADMIN_TOKEN"` separa peers `DIRECTO` y `RELAY`.
- `wg-auto-cli mesh-status` muestra:
  - bloques directos para peers alcanzables
  - comentarios `Relay-via-HUB` para peers que usan relay
- el HUB sigue presente como relay de fallback.

Pruebas sugeridas:

```bash
orch-cli peer-reachability default --admin-token "$ADMIN_TOKEN"
orch-cli mesh-peers default --admin-token "$ADMIN_TOKEN"
wg-auto-cli mesh-status
ping -c 3 10.20.30.4
ping -c 3 10.20.30.2
ping -c 3 10.20.30.3
```

Si un peer queda detrás de NAT simétrico, el tráfico debe seguir funcionando, pero el detalle de reachability lo mostrará como `RELAY`.

### Desmontaje

Para volver a una topología sin enlaces directos:

```bash
source /etc/linkguard/secrets
orch-cli net-set-topology default hub-spoke --admin-token "$ADMIN_TOKEN"
```

Para desmontar completamente:

```bash
systemctl stop wg-auto-register
wg-quick down wg0 || true
wg-auto-cli unregister
```

## Limpieza completa del laboratorio

Si quieres dejar el entorno sin peers activos:

En cada peer:

```bash
systemctl stop wg-auto-register
wg-quick down wg0 || true
wg-auto-cli unregister
rm -f /etc/wireguard/wg0.conf /etc/wireguard/wg-auto.json
```

En el orquestador:

```bash
source /etc/linkguard/secrets
orch-cli peer-list --admin-token "$ADMIN_TOKEN"
orch-cli net-topology default --admin-token "$ADMIN_TOKEN"
wg show wg-HUB
```

Si también quieres borrar la red de pruebas:

```bash
orch-cli net-delete default --admin-token "$ADMIN_TOKEN"
```

Solo haz esto último si vas a recrear la red antes de volver a registrar peers.

## Suites automáticas relacionadas

Pruebas unitarias del orquestador:

```bash
pytest orchestrator-install-v2/tests/test_supported_topologies.py -q
```

Pruebas unitarias del peer:

```bash
pytest peer-install-v2/tests/test_supported_topologies.py -q
```

Pruebas de integración QEMU existentes:

```bash
pytest testbed/tests/test_wireguard_integration.py -q
```

Escenario mixto adicional `Arch + Alpine` detrás de NAT simétrico:

```bash
pytest peer-install-v2/tests/test_integration_mixed_nat_topologies.py -q
```

Ese escenario modela:

- VM `Arch Linux` anunciando `46.250.168.185:51820`
- VM `Alpine Linux` anunciando `122.8.179.57:51820`
- ambas detrás de NAT simétrico
- sin alcanzabilidad por red privada entre sí
- comparación del comportamiento en `hub-spoke`, `mesh` y `hub-mesh`

Para correr todo el paquete de pruebas de topologías, incluyendo la suite QEMU del testbed:

```bash
make topology-test-all
```

Para un flujo tipo CI que levante el testbed, ejecute todas las pruebas y lo desmonte al final:

```bash
make topology-test-ci
```

Nota:

- `topology-test-all` requiere que el laboratorio QEMU ya esté levantado y accesible.
- Si solo quieres las pruebas unitarias/simuladas, usa `make topology-test`.
- `topology-test-ci` automatiza `up -> tests -> down`.
- Si tu entorno necesita contraseña de sudo distinta, exporta `SUDO_PASS` antes de ejecutarlo.

## Integración del testbed QEMU con el orquestador real

El testbed ahora soporta un modo integrado para que las VMs `orq`, `pa` y `pb`
se registren como peers contra el mismo orquestador real que usa la infraestructura
en Huawei Cloud.

Variables esperadas:

```bash
export TESTBED_REAL_ORCH_HOST=101.44.24.91
export TESTBED_REAL_ORCH_USER=root
export TESTBED_REAL_ORCH_PASS='...'
```

Opcionalmente:

```bash
export TESTBED_REAL_ORCH_URL=http://101.44.24.91:8000/RPC2
```

Flujos disponibles:

```bash
# Levantar VMs y dejarlas integradas con el orquestador real
python3 testbed/scripts/launch-testbed.py up-real

# Si las VMs ya están levantadas, solo sincronizar la integración
python3 testbed/scripts/launch-testbed.py sync-real

# Entrar por SSH a una VM integrada
python3 testbed/scripts/launch-testbed.py ssh pa

# Apagar el laboratorio
python3 testbed/scripts/launch-testbed.py down
```

Atajos equivalentes con `make`:

```bash
make testbed-up-real TESTBED_REAL_ORCH_PASS='...'
make testbed-sync-real TESTBED_REAL_ORCH_PASS='...'
make testbed-down
make qemu-status-real TESTBED_REAL_ORCH_PASS='...'
```

Para validar automáticamente la integración real de extremo a extremo:

```bash
make topology-test-all-real TESTBED_REAL_ORCH_PASS='...'
```

Ese target hace:

- corre las pruebas unitarias/simuladas de topologías
- levanta el testbed integrado con el orquestador real
- valida que `qemu-orq`, `qemu-pa` y `qemu-pb` aparezcan en el orquestador real
- valida handshakes y ping entre `qemu-pa` y `qemu-pb`
- desmonta el laboratorio al final

Si solo quieres un resumen operativo del laboratorio integrado:

```bash
make qemu-status-real TESTBED_REAL_ORCH_PASS='...'
```

Ese comando muestra:

- estado de las VMs QEMU
- estado de `wg-auto-register` en `orq`, `pa` y `pb`
- `peer-list` del orquestador real
- `wg show wg-HUB` en el HUB real

## Reporte automático de rendimiento

Para regenerar `docs/reporte-rendimiento-conectividad.md` con una nueva corrida de métricas:

```bash
make performance-report TESTBED_REAL_ORCH_PASS='...'
```

Para forzar una corrida completa por topología incluyendo el bloque QEMU integrado:

```bash
make performance-report-all-real TESTBED_REAL_ORCH_PASS='...'
```

El generador:

- consulta el orquestador real
- mide pruebas separadas por `hub-spoke`, `mesh` y `hub-mesh`
- mide pings entre peers reales
- si el testbed está levantado o se fuerza `--ensure-qemu-real`, mide también QEMU integrado
- mide throughput HTTP sobre WireGuard entre peers reales y QEMU
- reescribe `docs/reporte-rendimiento-conectividad.md`

Además mantiene un historial acumulado en:

```text
docs/reporte-rendimiento-historial.md
```

Qué hace `up-real`:

- levanta las VMs del testbed
- provisiona red base dentro de cada VM
- crea o recicla usuarios/tokens en el orquestador real para:
  - `qemu-orq`
  - `qemu-pa`
  - `qemu-pb`
- instala `peer-install-v2` en las 3 VMs
- configura `peer.env` para que todas apunten a `101.44.24.91`

Comprobación rápida desde el orquestador real:

```bash
ssh root@101.44.24.91
source /etc/linkguard/secrets
orch-cli peer-list --admin-token "$ADMIN_TOKEN"
```

Deberías ver los peers `qemu-orq`, `qemu-pa` y `qemu-pb` además de los peers reales.
