# Topologías Soportadas — Documentación Técnica

## Resumen

LinkGuard soporta tres topologías de red WireGuard:

| Topología | Control Plane | Data Plane | Dependencia del HUB |
|-----------|---------------|------------|---------------------|
| `hub-spoke` | Orchestrator central | Todo el tráfico via HUB | Alta (relay obligatorio) |
| `mesh` | Orchestrator central | Peer-to-peer directo | Baja (solo coordinación) |
| `hub-mesh` | Orchestrator central | Directo si es posible, relay si no | Media (fallback) |

---

## 1. Hub-Spoke (Default)

### Descripción

Topología estrella donde todos los peers se conectan exclusivamente al HUB. El HUB actúa como relay para todo el tráfico entre peers.

### Arquitectura

```
┌─────────┐         ┌─────────────┐         ┌─────────┐
│ Peer A  │═════════│   HUB/wg-HUB│═════════│ Peer B  │
│ 10.20.30.2│       │ 10.20.30.1  │         │ 10.20.30.3│
└─────────┘         └─────────────┘         └─────────┘
                           │
                           │ (control plane)
                           ▼
                    ┌─────────────┐
                    │Orchestrator │
                    │  :8000/RPC2 │
                    └─────────────┘
```

### Flujo de Configuración

1. **Peer se registra**: `peer.register(peer_id, pub_key, endpoint)`
2. **Orchestrator asigna IP**: `10.20.30.X/32` en la red `default`
3. **Hub Agent aplica AllowedIPs**: `wg set wg-HUB peer <pub> allowed-ips <ip>/32`
4. **Peer solicita config**: `config.get_peer_config(peer_id, jwt)`
5. **Orchestrator devuelve**:
   ```json
   {
     "interface": {"address": "10.20.30.2/32", "mtu": 1420},
     "peer": {
       "public_key": "<HUB_PUB>",
       "endpoint": "101.44.24.91:51820",
       "allowed_ips": "10.20.30.0/24",
       "persistent_keepalive": 25
     },
     "meta": {"topology": "hub-spoke", "config_version": 1}
   }
   ```

### Configuración WireGuard Generada

```ini
[Interface]
Address = 10.20.30.2/32
PrivateKey = <PEER_PRIV>
MTU = 1420

# HUB (bootstrap)
[Peer]
PublicKey = <HUB_PUB>
Endpoint = 101.44.24.91:51820
AllowedIPs = 10.20.30.0/24
PersistentKeepalive = 25
```

### Características

- **Ventajas**: Simple, funciona con cualquier NAT, el HUB controla todo el tráfico
- **Desventajas**: Latencia adicional (2 saltos), el HUB es bottleneck y single point of failure
- **Uso recomendado**: Redes pequeñas, peers detrás de NAT simétrico, cuando se necesita inspección de tráfico

### Código Clave

- `orchestrator/endpoints_config.py:16-76` — `rpc_config_get_peer_config()`
- `peer_register/config_gen.py:32-41` — `_build_hub_block()`

---

## 2. Mesh (Full Mesh)

### Descripción

Todos los peers se conectan directamente entre sí. El HUB solo se usa para bootstrap inicial. No hay relay de tráfico.

### Arquitectura

```
┌─────────┐         ┌─────────┐
│ Peer A  │═════════│ Peer B  │
│.2       │         │.3       │
└────┬────┘         └────┬────┘
     │                   │
     │   ┌─────────┐     │
     └═══│ Peer C  │═════┘
         │.4       │
         └─────────┘
         
Control plane: todos → Orchestrator
Data plane: peer-to-peer directo
```

### Flujo de Configuración

1. **Peer se registra** igual que hub-spoke
2. **Orchestrator detecta topología**: `network.topology == "mesh"`
3. **Peer solicita config**: `config.get_peer_config(peer_id, jwt)`
4. **Orchestrator calcula peers vivos**: `_get_alive_mesh_peers()`
   - Itera sobre todos los peers en la red
   - Filtra por `last_heartbeat` dentro de `HEARTBEAT_TTL_SEC` (180s)
   - Ordena: vivos primero, luego por peer_id
   - Limita a `MESH_MAX_PEERS` (50)
5. **Devuelve**:
   ```json
   {
     "interface": {"address": "10.20.30.2/32", "mtu": 1420},
     "peer": {
       "public_key": "<HUB_PUB>",
       "endpoint": "101.44.24.91:51820",
       "allowed_ips": "10.20.30.0/24",
       "persistent_keepalive": 25
     },
     "mesh_peers": [
       {
         "peer_id": "peer_b",
         "public_key": "<B_PUB>",
         "endpoint": "122.8.179.57:51820",
         "tunnel_ip": "10.20.30.3",
         "alive": true,
         "last_seen_ts": 1703635200
       },
       {
         "peer_id": "peer_c",
         "public_key": "<C_PUB>",
         "endpoint": "46.250.162.141:51820",
         "tunnel_ip": "10.20.30.4",
         "alive": true,
         "last_seen_ts": 1703635195
       }
     ],
     "meta": {
       "topology": "mesh",
       "config_version": 2,
       "mesh_peers_hash": "abc123..."
     }
   }
   ```

### Configuración WireGuard Generada

```ini
[Interface]
Address = 10.20.30.2/32
PrivateKey = <PEER_PRIV>
MTU = 1420

# HUB (bootstrap)
[Peer]
PublicKey = <HUB_PUB>
Endpoint = 101.44.24.91:51820
AllowedIPs = 10.20.30.0/24
PersistentKeepalive = 25

# Peer directo: peer_b (alive=true)
[Peer]
PublicKey = <B_PUB>
Endpoint = 122.8.179.57:51820
AllowedIPs = 10.20.30.3/32
PersistentKeepalive = 25

# Peer directo: peer_c (alive=true)
[Peer]
PublicKey = <C_PUB>
Endpoint = 46.250.162.141:51820
AllowedIPs = 10.20.30.4/32
PersistentKeepalive = 25
```

### Características

- **Ventajas**: Baja latencia (1 salto), sin bottleneck, distribuido
- **Desventajas**: No funciona si ambos peers están detrás de NAT simétrico, O(n²) conexiones
- **Uso recomendado**: Peers con IP pública o NAT full-cone, redes pequeñas/medianas

### Limitaciones NAT

Si ambos peers están detrás de NAT simétrico:
- No pueden completar el handshake WireGuard
- El peer aparece como `alive=true` pero no hay handshake
- Solución: usar `hub-mesh` que detecta esto y usa relay

### Código Clave

- `orchestrator/endpoints_config.py:98-121` — `_get_alive_mesh_peers()`
- `peer_register/config_gen.py:44-67` — `_build_mesh_blocks()`

---

## 3. Hub-Mesh (Híbrida)

### Descripción

Topología híbrida que intenta conexión directa cuando es posible y usa el HUB como relay de fallback cuando hay NAT problemático.

### Arquitectura

```
┌─────────┐    directo    ┌─────────┐
│ Peer A  │═══════════════│ Peer B  │  (ambos con IP pública)
│.2       │               │.3       │
└────┬────┘               └────┬────┘
     │                         │
     │    ┌─────────────┐      │
     └═══►│   HUB/wg-HUB│◄═════┘  (Peer C detrás de NAT simétrico)
          │ 10.20.30.1  │
          └──────┬──────┘
                 │
          ┌──────┴──────┐
          │   Peer C    │  (relay only)
          │   .4        │
          └─────────────┘
```

### Flujo de Configuración

1. **Peer se registra** y reporta `nat_type` en heartbeat
2. **Peer solicita config**: `config.get_peer_config(peer_id, jwt)`
3. **Orchestrator clasifica peers**: `_classify_peers_for_hub_mesh()`
   - Para cada peer vivo en la red:
     - Si `requester_nat_type == "symmetric"` → todos van a `relay_only`
     - Si `target_nat_type == "symmetric"` → va a `relay_only`
     - Si `relay_mode == "force_relay"` → va a `relay_only`
     - Si `relay_mode == "force_direct"` → va a `direct`
     - Si `peer.report_reachability()` reportó `"hub-relay"` → va a `relay_only`
     - Si tiene endpoint público y NAT no simétrico → va a `direct`
4. **Devuelve**:
   ```json
   {
     "interface": {"address": "10.20.30.2/32", "mtu": 1420},
     "peer": {
       "public_key": "<HUB_PUB>",
       "endpoint": "101.44.24.91:51820",
       "allowed_ips": "10.20.30.0/24",
       "persistent_keepalive": 25
     },
     "hub_mesh_direct_peers": [
       {
         "peer_id": "peer_b",
         "public_key": "<B_PUB>",
         "endpoint": "122.8.179.57:51820",
         "tunnel_ip": "10.20.30.3",
         "nat_type": "none",
         "relay_mode": "auto",
         "alive": true
       }
     ],
     "hub_mesh_relay_peers": [
       {
         "peer_id": "peer_c",
         "public_key": "<C_PUB>",
         "endpoint": "46.250.162.141:51820",
         "tunnel_ip": "10.20.30.4",
         "nat_type": "symmetric",
         "relay_mode": "auto",
         "alive": true
       }
     ],
     "meta": {
       "topology": "hub-mesh",
       "config_version": 3,
       "hub_mesh_peers_hash": "def456..."
     }
   }
   ```

### Configuración WireGuard Generada

```ini
[Interface]
Address = 10.20.30.2/32
PrivateKey = <PEER_PRIV>
MTU = 1420

# HUB (relay de fallback)
[Peer]
PublicKey = <HUB_PUB>
Endpoint = 101.44.24.91:51820
AllowedIPs = 10.20.30.0/24
PersistentKeepalive = 25

# Directo: peer_b
[Peer]
PublicKey = <B_PUB>
Endpoint = 122.8.179.57:51820
AllowedIPs = 10.20.30.3/32
PersistentKeepalive = 25

# Relay-via-HUB: peer_c (nat=symmetric, sin bloque directo)
```

### Detección de NAT

El peer detecta su tipo de NAT y lo reporta en cada heartbeat:

```python
# peer_register/nat.py
def detect_nat_type() -> str:
    """
    Retorna:
    - "none": IP pública directa
    - "full-cone": NAT que permite inbound desde cualquier IP
    - "symmetric": NAT que cambia puerto por cada destino (no permite P2P)
    """
```

**Heurística**:
1. Compara `endpoint` auto-reportado con `remote_addr` visto por el orchestrator
2. Si coinciden → `none` o `full-cone`
3. Si no coinciden → `symmetric`

### Prueba de Reachability

En `hub-mesh`, el peer prueba activamente si puede alcanzar a otros peers:

```python
# peer_register/probe.py
def probe_direct_peers(peer_id: str, st: dict) -> None:
    """
    Para cada peer en hub_mesh_direct_candidates:
    - Intenta handshake WireGuard
    - Si falla después de N intentos → reporta peer.report_reachability(reachable=False)
    - Orchestrator mueve el peer a relay_only
    """
```

### Características

- **Ventajas**: Funciona con cualquier NAT, baja latencia cuando es posible, fallback automático
- **Desventajas**: Más complejo, overhead de probing, configuración dinámica
- **Uso recomendado**: Redes mixtas con peers detrás de diversos tipos de NAT

### Código Clave

- `orchestrator/endpoints_config.py:124-176` — `_classify_peers_for_hub_mesh()`
- `peer_register/config_gen.py:70-93` — `_build_hub_mesh_blocks()`
- `peer_register/probe.py` — `probe_direct_peers()`
- `peer_register/nat.py` — `detect_nat_type()`

---

## Configuración de Topología

### Cambiar Topología de una Red

```bash
# En el orchestrator
source /etc/linkguard/secrets

# Cambiar a mesh
orch-cli net-set-topology default mesh --admin-token "$ADMIN_TOKEN"

# Cambiar a hub-mesh
orch-cli net-set-topology default hub-mesh --admin-token "$ADMIN_TOKEN"

# Volver a hub-spoke
orch-cli net-set-topology default hub-spoke --admin-token "$ADMIN_TOKEN"

# Verificar
orch-cli net-topology default --admin-token "$ADMIN_TOKEN"
```

### Efecto en los Peers

1. Orchestrator incrementa `config_version`
2. Peers reciben `desired_config_version` en el próximo heartbeat
3. Peer detecta cambio: `desired != current`
4. Peer solicita nueva config: `config.get_peer_config()`
5. Peer regenera `wg0.conf` y aplica con `wg syncconf`

---

## Variables de Configuración

### Orchestrator

| Variable | Default | Descripción |
|----------|---------|-------------|
| `HEARTBEAT_TTL_SEC` | 180 | Tiempo para considerar un peer "vivo" |
| `MESH_MAX_PEERS` | 50 | Máximo de peers en config mesh |
| `MESH_DEFAULT_KEEPALIVE` | 25 | PersistentKeepalive para peers mesh |
| `WG_MTU` | 1420 | MTU de la interfaz WireGuard |

### Peer

| Variable | Default | Descripción |
|----------|---------|-------------|
| `WG_HEARTBEAT_INTERVAL` | 25 | Intervalo entre heartbeats |
| `WG_KEEPALIVE` | 25 | PersistentKeepalive |
| `WG_LISTEN_PORT` | (auto) | Puerto de escucha (si tiene IP pública) |

---

## Comparación Detallada

| Aspecto | Hub-Spoke | Mesh | Hub-Mesh |
|---------|-----------|------|----------|
| **Saltos de red** | 2 (peer→hub→peer) | 1 (peer→peer) | 1 o 2 |
| **Latencia** | Alta | Baja | Variable |
| **Throughput** | Limitado por HUB | Máximo | Variable |
| **NAT simétrico** | Funciona | No funciona | Funciona (relay) |
| **Configuración wg0.conf** | 1 bloque [Peer] | N bloques [Peer] | 1 + N_direct bloques |
| **Dependencia orchestrator** | Alta | Alta (control) | Alta (control + clasificación) |
| **Escalabilidad** | Buena (hub bottleneck) | Limitada (O(n²)) | Buena |
| **Single point of failure** | Sí (HUB) | No | Parcial (HUB como fallback) |

---

## Diagnóstico

### Ver Topología Actual

```bash
# En orchestrator
orch-cli net-topology default --admin-token "$ADMIN_TOKEN"

# En peer
wg-auto-cli mesh-status
```

### Ver Peers Mesh

```bash
# En orchestrator
orch-cli mesh-peers default --admin-token "$ADMIN_TOKEN"

# Ver reachability (hub-mesh)
orch-cli peer-reachability default --admin-token "$ADMIN_TOKEN"
```

### Verificar Handshakes

```bash
# En peer
wg show wg0 latest-handshakes

# En hub
wg show wg-HUB latest-handshakes
```

### Logs del Peer

```bash
journalctl -u wg-auto-register -f
```

Buscar:
- `Topologia mesh: generando N bloques [Peer] adicionales`
- `Topologia hub-mesh: X directos, Y via relay HUB`
- `Config version cambio X -> Y, reaplicando...`
- `Lista de peers mesh cambio (hash ...), reaplicando...`

---

## Referencias

- `docs/explicacion-topologias-linkguard.md` — Explicación conceptual
- `docs/topologias-linkguard.md` — Guía de pruebas
- `docs/arquitectura-linkguard.puml` — Diagrama de componentes
- `docs/topologias-flujo.puml` — Diagrama de flujos por topología
- `docs/secuencia-orchestrator-peer.puml` — Secuencia completa
