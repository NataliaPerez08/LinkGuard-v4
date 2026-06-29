# Plano de Control y Plano de Datos por Topología

Comparativa de los dos planos en las tres topologías soportadas por LinkGuard: **hub-spoke**, **mesh** y **hub-mesh**. Los diagramas asociados están en `plano-control-datos-{hub-spoke,mesh,hub-mesh}.puml`.

---

## 1. Hub-Spoke

### Plano de control (XML-RPC `:8000`)
- Cada peer hace `peer.register` al arrancar y `peer.heartbeat` cada 25 s.
- El orquestador asigna la IP `10.20.30.x/32`, devuelve `desired_config_version` y la config WireGuard con **un único bloque `[Peer]`** apuntando al HUB.
- No hay detección de NAT ni `probe_direct_peers`; la topología es estática: todos hablan al hub.

### Plano de datos (WireGuard `:51820`)
- Cada peer levanta `wg0` con un peer único: el HUB (`10.20.30.1`).
- El tráfico peer→peer siempre hace **2 saltos**: `Peer A → HUB → Peer B`.
- Sin P2P directo, sin mesh. El HUB es bottleneck y single point of failure; latencia = 2 × RTT peer-HUB.

---

## 2. Mesh

### Plano de control
- `peer.register` + `peer.heartbeat` como en las demás, pero el orquestador devuelve **`mesh_peers_hash`** (SHA-256 de la lista de peers vivos).
- El peer diff-ea el hash: si cambió, re-aplica config con **un bloque `[Peer]` por cada otro peer vivo** (todos con `Endpoint=`).
- No hay clasificación NAT; el orquestador asume que todos pueden alcanzarse.

### Plano de datos
- Topología full-mesh: N peers → N×(N-1)/2 túneles WireGuard directos.
- Cada paquete peer→peer es **1 salto** (P2P cifrado directo, sin relay).
- Latencia mínima, sin bottleneck.
- **Limitación real**: si dos peers están detrás de NAT simétrico (caso visto: terminal peers vía jump, QEMU tras NAT del host), el handshake WG directo nunca completa → 0/7 pings en malla pura. El plano de datos no tiene fallback.

---

## 3. Hub-Mesh (híbrido)

### Plano de control
- `peer.heartbeat` incluye `nat_type` (`none` / `full-cone` / `symmetric`), detectado con `detect_nat_type()` (caché 300 s).
- El orquestador ejecuta `_classify_peers_for_hub_mesh`: para cada par decide `direct` (ambos alcanzables + `nat_type != symmetric`) o `relay_only`.
- Devuelve `hub_mesh_peers_hash`; el peer re-aplica config con:
  - Bloques `[Peer]` normales para peers `direct`.
  - Comentarios `# Relay-via-HUB: <pid>` para peers `relay_only` (no hay `[Peer]` directo, el tráfico sube al hub).
- Tras reconfigurar, el peer ejecuta `probe_direct_peers()` (vía `wg show`) y reporta transiciones alive↔dead con `peer.report_reachability(peer_id, target, reachable)` para que el orquestador reclasifique.

### Plano de datos
- Dos modos coexisten en el mismo `wg0`:
  - **Directo** entre peers con IP pública (p.ej. EC2↔EC2): 1 salto, baja latencia, como mesh.
  - **Relay** cuando uno de los dos es `relay_only` (NAT simétrico): `Peer A → HUB → Peer C`, 2 saltos, como hub-spoke.
- El HUB sigue activo como fallback pero solo transporta lo que el plano de control marcó como `relay_only` — no es bottleneck para el tráfico EC2↔EC2.
- Resuelve el fallo de mesh pura: los peers NAT no intentan handshake directo imposible, van por hub y completan connectivity.

---

## 4. Cuadro comparativo

| Aspecto | hub-spoke | mesh | hub-mesh |
|---|---|---|---|
| Saltos peer→peer | 2 (vía HUB) | 1 (directo) | 1 o 2 según clasificación |
| Hash de drift en heartbeat | — | `mesh_peers_hash` | `hub_mesh_peers_hash` |
| NAT detection | no | no | sí (`nat_type`) |
| `probe_direct_peers` | no | no | sí |
| `peer.report_reachability` | no | no | sí |
| Bloques `[Peer]` por peer | 1 (HUB) | N-1 (todos) | direct + `# Relay-via-HUB` |
| Bottleneck HUB | siempre | nunca | solo relay |
| Funciona con NAT simétrico | sí (todo vía HUB) | **no** (0/7) | sí (relay_only) |

---

## 5. Referencias de código

| Símbolo | Ubicación |
|---|---|
| `peer.register` / `peer.heartbeat` | `orchestrator/endpoints_peers.py` |
| `_classify_peers_for_hub_mesh` | `orchestrator/endpoints_config.py:128` |
| `mesh_peers_hash` / `hub_mesh_peers_hash` | `orchestrator/state.py` |
| `detect_nat_type()` | `peer-install-v2/peer_register/commands.py:53-60` |
| `probe_direct_peers()` | `peer-install-v2/peer_register/commands.py:97-100` |
| `peer.report_reachability` | `peer-install-v2/peer_register/probe.py:55` |
| Drift por hash en heartbeat | `ciclo-vida.md:333` |

**Diagramas relacionados:**
- `plano-control-datos-general.puml` — vista conjunta
- `plano-control-datos-hub-spoke.puml`
- `plano-control-datos-mesh.puml`
- `plano-control-datos-hub-mesh.puml`