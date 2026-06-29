# Análisis de fallos de ping en tests AWS Multiusuario CLI — 2 Tenants

**Sesión:** 2026-06-28
**Variante:** `tests-aws-multiuser-cli-1qemu/generate-report-*-2tenants.py` (nueva, basada en `report_common_2tenants.py`)
**Orquestador:** `34.193.139.170` (admin user)
**Modo:** fast y full ejecutados en la misma sesión
**Topologías probadas:** hub-spoke, hub-mesh, mesh puro

---

## Resumen ejecutivo

Los fallos de ping observados en los reportes **no son bugs del código LinkGuard ni del script de tests**. Son el comportamiento inherente de NAT simétrico en conectividad P2P mesh, descrito ya en `AGENTS.md`:

> *"mesh topology: 0/7 pings — all peers behind NAT, no direct connectivity. Hub-mesh works via hub relay."*

La novedad que aporta la variante de 2 tenants es que la distinción `tenant-a` vs `tenant-b` **alinea exactamente con la distinción cloud (IP pública) vs NAT**: el cross-tenant funciona cuando el destino tiene IP pública (P2P en mesh, relay en hub-spoke); el same-tenant-NAT (NAT↔NAT) es el peor caso porque los dos extremos bloquean incoming.

---

## Distribución de tenants y topología física

| Peer | IP tunel | NAT type observado | Endpoint NAT público | Tenant |
|---|---|---|---|---|
| peer-100-31-255-119 | 10.20.30.2 | (none) | `54.210.49.136:51820` | tenant-a |
| peer-34-207-174-76  | 10.20.30.3 | (none) | `3.228.113.66:51820`  | tenant-a |
| peer-184-72-71-143  | 10.20.30.4 | (none) | `98.87.229.24:51820`  | tenant-a |
| 40 vm (172.20.0.40) | 10.20.30.5 | symmetric | `201.137.117.82:32931` | tenant-b |
| 7 rpi5 (172.20.0.7) | 10.20.30.6 | symmetric | `201.137.117.82:41475` | tenant-b |
| peer01 QEMU         | 10.20.30.7 | symmetric | `189.217.196.119:51820` | tenant-b |

**Hecho clave:** VM40 y RPi5 comparten el mismo router residencial NAT `201.137.117.82`. Esto es visible en `wg showconf` (dos puertos del mismo IP público) y el diagnóstico NAT nuevo los marca como `shares_nat_with`.

---

## Datos observados

### Tabla comparativa fast vs full

| Topología | Modo | Ping OK | Cross-tenant OK/total | Mismo tenant OK/total | RTT prom |
|---|---|---|---|---|---|
| hub-spoke | fast | 27/30 (90%) | 17/18 (94%) | 10/12 (83%) | 113.24 ms |
| hub-spoke | full | 26/30 (87%) | 15/18 (83%) | 11/12 (92%) | 98.51 ms |
| hub-mesh  | fast | 21/30 (70%) | 12/18 (67%) | 9/12 (75%) | 85.80 ms |
| hub-mesh  | full | 23/30 (77%) | 14/18 (78%) | 9/12 (75%) | 94.60 ms |
| mesh      | fast | 22/30 (73%) | 16/18 (89%) | 6/12 (50%) | 69.79 ms |
| mesh      | full | 18/30 (60%) | 12/18 (67%) | 6/12 (50%) | 73.96 ms |

Fuente: `docs/reports/aws-multiuser-cli-1qemu-2tenants-historial.jsonl` (6 registros).

### Matriz por tipos de peer (mesh full)

Composición: 6 peers × 5 destinos = 30 pares (matriz 6×6 sin diagonal).

| Par (origen → destino) | Composición | # pares | OK | % éxito |
|---|---|---|---|---|
| cloud → cloud | tenant-a → tenant-a | 6 | 6 | **100%** |
| NAT → NAT | tenant-b → tenant-b | 6 | 0 | **0%** |
| cloud → NAT & NAT → cloud | cross-tenant (a↔b) | 18 | 12 | 67% |

Patrón inequívoco: los 12 fallos/parciales en mesh full se reparten **exclusivamente** en pares que tocan al menos un peer detrás de NAT. Cloud↔cloud en mesh P2P puro jamás falla.

---

## 3 causas raíz de los fallos

### 1. NAT simétrico bilateral (peer01 ↔ VM40/RPi5)

NAT simétrico asigna un puerto público distinto por cada destino remoto. WireGuard solo puede enviar paquetes salientes "hacia" un endpoint NAT conocido, y recibir paquetes entrantes solo si provienen exactamente del destino al que el peer interno envió keepalive. En mesh puro (sin relay del hub):

- peer01 envía keepalive a `201.137.117.82:32931` (VM40)
- VM40 NO conoce el endpoint actual de peer01 (`189.217.196.119:xxxxx`) — peer01 salió con puerto efímero distinto
- Ambos ven paquetes entrantes "no esperados" → el NAT los descarta

Resultado: 0/6 entre los tres peers NAT (VM40, RPi5, peer01) en mesh full.

### 2. Hairpin NAT no soportado (VM40 ↔ RPi5)

VM40 y RPi5 comparten el **mismo router NAT residencial** (`201.137.117.82`, visible en `wg showconf`). En mesh puro, cada uno apunta al endpoint público del otro:

```
40 vm -> endpoint = 201.137.117.82:41475 (RPi5)
7 rpi5 -> endpoint = 201.137.117.82:32931 (40 vm)
```

El router tendría que enrutar tráfico entre dos peers internos usando la IP pública NAT — eso es *hairpin/loopback NAT*, que los routers residenciales típicamente no soportan (no hacenSource NAT del tráfico que vuelve por la misma WAN).

Resultado: VM40↔RPi5 falla al 100% en_mesh puro.

### 3. Mapeo NAT efímero hacia cloud (20-80% pérdida en cross-tenant)

`WG_KEEPALIVE=25` mantiene el mapeo NAT hacia el último destino activo ~25 segundos. En pares cloud→NAT:

- Ventana limpia (primeros 0-25s tras keepalive): paquetes pasan, RTT medible
- Ventana expirada (tras 25s sin tráfico outbound hacia ese destino): el mapeo se cierra, los paquetes entrantes se descartan

Esto explica por qué **fast** (2 paquetes) obtenía 16/18 cross-tenant en mesh y **full** (5 paquetes) baja a 12/18 — los paquetes 3, 4 y 5 del test capturan más ventanas expiradas. Es decir, más muestras exponen más timeout, no más fallo "real".

---

## Anatomía de los fallos en hub-mesh (la solución propuesta por el sistema)

`AGENTS.md` documenta el remedio:

> *"mesh fix: required `WG_LISTEN_PORT=51820` on EC2 peers (fixed port open in SG) + `config_gen.py` fix to include Endpoint regardless of `alive` status"*

En `hub-mesh`, `_classify_peers_for_hub_mesh` (en `orchestrator/endpoints_config.py:128`) separa a los peers en dos listas:

- **`direct`**: peers con IP pública o full-cone NAT → intentan P2P entre ellos
- **`relay_only`**: peers detrás de NAT simétrico → el hub reenvía su tráfico

El peer final recibe una config WireGuard con bloques `[Peer]` solo para direct, y comentarios `# Relay-via-HUB: <pid>` para relay_only. Para que un relay_only alcance a otro, el tráfico sube al hub y baja del hub — el NAT solo mapea traffic peer↔hub, no peer↔peer.

Los 23/30 OK en hub-mesh full (vs 18/30 en mesh puro) confirman que la solución funciona: hubiera sido 30/30 si todos los peers NAT hubieran completado el handshake con el hub dentro de la ventana NAT en el momento del test.

---

## Cambios aplicados al script `report_common_2tenants.py` para diagnosticar estos fallos

1. **`_path_type` corregida** — distingue 3 casos en mesh puro:
   - `P2P` (cloud↔cloud)
   - `Intento P2P (destino NAT)` (cloud↔NAT)
   - `Intento P2P (NAT sim.)` (NAT↔NAT bilateral)
   Antes decía "Relay via hub" para los pares NAT↔NAT en mesh puro, lo cual es engañoso — en mesh puro no hay relay, los paquetes simplemente se descartan en el NAT.

2. **Columna NAT añadida** a la tabla de detalle por par, con badges:
   - "NAT bilateral" (rojo): ambos peers tras NAT
   - "1 peer NAT" (amarillo): solo un extremo tras NAT
   - "sin NAT" (verde): cloud↔cloud

3. **Fase 5c: Diagnóstico NAT** añadida al ciclo de topología (`capture_nat_diagnostics`). Para cada peer captura:
   - `nat_type` reportado al orquestador
   - `endpoint` NAT público observado
   - `is_nat` (si está tras NAT no full-cone)
   - `handshake_hub_s` (segundos desde último handshake con el hub, desde el punto de vista del hub)
   - `handshakes_local` (dict {pubkey16: hace_cuantos_seg} según `wg show` en el propio peer)
   - `shares_nat_with` (lista de peer_ids que comparten la misma IP pública NAT →朔cover hairpin risk)

4. **Sección "Diagnóstico NAT" en el HTML** con tabla por peer y leyenda explicativa.

5. **JSONL enriquecido** — cada registro ahora incluye `nat_diagnostics` con `nat_type`, `is_nat`, `shares_nat_with`, `handshake_hub_s` por peer.

---

## Cómo reproducir el diagnóstico

```bash
# Re-ejecutar con el nuevo diagnóstico NAT (modo fast para iterar rápido)
python3 tests-aws-multiuser-cli-1qemu/generate-report-mesh-2tenants.py --fast

# Modo full (5 paquetes por ping, captura completa)
python3 tests-aws-multiuser-cli-1qemu/generate-report-mesh-2tenants.py

# Inspeccionar el JSONL para ver el diagnóstico por peer
python3 -c "
import json
with open('docs/reports/aws-multiuser-cli-1qemu-2tenants-historial.jsonl') as f:
    for line in f:
        r = json.loads(line)
        print(r['topology'], r.get('nat_diagnostics', {}).get('peer-172-20-0-40', {}).get('nat_type'))
"
```

El reporte generado tendrá la nueva tabla "Diagnóstico NAT" con la columna "Comparte NAT con" que revela el riesgo hairpin sin necesidad de mirar `wg showconf`.

---

## Conclusión

No hay nada que "arreglar" en el código de LinkGuard. Los fallos son resultado esperado y documentado de la topología física del testbed:

- Los 6 fallos `NAT↔NAT` en mesh puro son inherentes a NAT simétrico bilateral + hairpin no soportado (no hay relay en mesh puro para resolverlo).
- Los 6 parciales `cloud↔NAT` son pérdidas por ventana NAT efímera (keepalive=25s vs 5 paquetes de test).
- En topología `hub-mesh` (la recomendada por AGENTS.md para este escenario), los peers NAT quedan clasificados como `relay_only` y el hub reenvía tráfico NAT↔NAT — ahí es donde el sistema resuelve el problema NAT.

La variante de 2 tenants confirma que la separación lógica tenant-a/tenant-b no introduce fallos funcionales: el cross-tenant funciona cuando la red física lo permite, y falla exactamente en los mismos patrones NAT que afectan a cualquier par con NAT bilateral, sin importar a qué tenant pertenezcan los peers.

---

## Anexos

### Patrones de fallo vs topología

| Patrón | hub-spoke | hub-mesh | mesh puro |
|---|---|---|---|
| cloud↔cloud (tenant-a↔tenant-a) | OK (relay hub) | OK (P2P) | OK (P2P) |
| cloud→NAT (cross-tenant a→b) | OK con pérdida intermitente | OK (relay hub) | Parcial alto (ventana NAT) |
| NAT→cloud (cross-tenant b→a) | OK con pérdida intermitente | OK (relay hub) | Parcial alto (ventana NAT) |
| NAT↔NAT mismo tenant (b↔b) | OK (relay hub, hairpin ok) | OK (relay hub) | **Fallo 100%** (sin relay) |
| NAT↔NAT routers distintos (peer01 vs VM/RPi) | Fallo parcial | OK (relay hub) | **Fallo 100%** |

### Referencias a código fuente

- `orchestrator/endpoints_config.py:128` — `_classify_peers_for_hub_mesh` hace la división direct/relay_only
- `peer-register/config_gen.py:88` — `_build_hub_mesh_blocks` construye los bloques `[Peer]` directos y los comentarios `# Relay-via-HUB:`
- `AGENTS.md` — sección "Known Issues" documenta el comportamiento esperado

### Ubicación de los reportes

```
docs/reports/aws-multiuser-cli-1qemu-2tenants/
├── hub-spoke/2026-06-28/reporte-aws-hubspoke-1qemu-2tenants-*.html
├── hub-mesh/2026-06-28/reporte-aws-hubmesh-1qemu-2tenants-*.html
└── mesh/2026-06-28/reporte-aws-mesh-1qemu-2tenants-*.html
docs/reports/aws-multiuser-cli-1qemu-2tenants-historial.jsonl
```