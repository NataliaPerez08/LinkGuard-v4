# Documentación de Implementación — LinkGuard v4

## Visión General

LinkGuard es un gestor de redes overlay sobre WireGuard con arquitectura **orquestador-agente**. El orquestador actúa como plano de control (XML-RPC) y los peers ejecutan un agente que auto-registra y configura WireGuard dinámicamente. Soporta tres topologías: **hub-spoke**, **mesh** y **hub-mesh**.

```
┌─────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR                         │
│  (XML-RPC server :8000/RPC2)                            │
│  auth/state/endpoints/hub_client                        │
└────────┬────────────────────────────────────────┬───────┘
         │ HTTP/XML-RPC (JWT autenticado)          │ XML-RPC (token local)
         ▼                                          ▼
┌──────────────────┐                     ┌──────────────────┐
│   PEER AGENT     │   ...               │   HUB-AGENT      │
│  (wg-auto-reg.)  │                     │  (wg-HUB + ipt.) │
│  register/heart/ │                     │  apply/remove    │
│  config_gen/probe│                     │  peer en hub     │
└──────────────────┘                     └──────────────────┘
```

---

## 1. Orquestador (`orchestrator-install-v2/`)

### 1.1 `orchestrator/__init__.py` — Punto de entrada y servidor XML-RPC

- Clase `_Handler`: extiende `SimpleXMLRPCRequestHandler` para capturar `client_address` vía thread-local (útil para heartbeat remoto).
- Clase `_Server`: `ThreadingMixIn` + `SimpleXMLRPCServer` — servidor multi-hilo con reuso de puerto.
- Función `_register_xml_handlers()`: mapea ~30 nombres RPC (`peer.register`, `network.create`, etc.) a funciones `_xml_*` que traducen argumentos posicionales (convención XML-RPC) a diccionarios nombrados y delegan en los handlers modulares.
- Función `main()`: chequea dependencias, valida tokens, carga estado persistente, verifica conectividad con hub-agent, inicia loop de backups y arranca el servidor.

### 1.2 `orchestrator/config.py` — Configuración

Variables de entorno con defaults sensibles:
- `ORCH_BIND`/`ORCH_PORT`: bind del servidor (0.0.0.0:8000)
- `STATE_PATH`, `BACKUP_*`: persistencia
- `HUB_AGENT_URL`/`HUB_AGENT_TOKEN`: conexión al hub-agent local
- `JWT_SECRET_PATH`, `JWT_TTL_DEFAULT`: autenticación JWT
- `AUTO_APPROVE_*`: auto-asignación de peers a redes por defecto
- `DEFAULT_NET_*`: red por defecto (10.20.30.0/24)
- `HEARTBEAT_TTL_SEC`: tiempo sin heartbeat para marcar peer caído

### 1.3 `orchestrator/auth.py` — Autenticación JWT y multi-tenant

- `_read_jwt_secret()`: lee secret desde archivo con caché por hash (recarga en caliente si cambia).
- `_jwt_encode/decode()`: empaqueta/verifica JWTs con HS256, incluye claims `iss`, `aud`, `iat`, `exp`, `jti`.
- `_check_user_token()`: valida token de usuario contra almacén (SHA-256).
- `orch_check_admin_token()`: compara con `ADMIN_TOKEN` de entorno.
- `_issue_user_token()`: genera token de usuario para autenticación JWT posterior.
- `_is_revoked_jti()` / `revocar()`: blacklist de JTIs revocados.
- `_get_tenant_quota()`: control de límites por tenant (`max_peers`, `max_networks`).

### 1.4 `orchestrator/state.py` — Estado persistente

- Carga/guarda estado JSON en `STATE_PATH`.
- Almacena: peers registrados, redes, usuarios, topologías, eventos.
- `add_event()`: log de eventos en memoria + archivo JSONL.
- `start_backup_loop()`: thread daemon que respalda cada `BACKUP_INTERVAL_SEC`.

### 1.5 `orchestrator/hub_client.py` — Cliente hub-agent

- XML-RPC client hacia `hub-agent` (127.0.0.1:9000).
- `hub_ping()`: verifica conectividad.
- `hub_apply_peer()`: envía peer nuevo/actualizado al hub.
- `hub_remove_peer()`: elimina peer del hub.
- `_get_wg_endpoint()`: determina endpoint público del hub.

### 1.6 Endpoints — Handlers XML-RPC

Cada archivo implementa funciones `rpc_*` que reciben un `dict` y retornan `dict`:

| Archivo | Handlers |
|---|---|
| `endpoints_orch.py` | `health`, `metrics`, `events` |
| `endpoints_peers.py` | `peer_register`, `peer_heartbeat`, `peer_unregister`, `peer_request_network`, `peer_rotate_key`, `peer_report_reachability`, `peer_list`, `peer_get`, `peer_assign_network`, `peer_remove_from_network`, `peer_update_admin` |
| `endpoints_networks.py` | `network_create`, `network_delete`, `network_set_topology`, `network_get_topology`, `network_list`, `network_get` |
| `endpoints_config.py` | `config_get_peer_config`, `config_get_mesh_peers`, `_classify_peers_for_hub_mesh` (clasifica peers como DIRECT/RELAY) |
| `endpoints_users.py` | `user_create`, `user_list`, `user_delete` |
| `endpoints_auth.py` | `jwt_issue`, `jwt_verify`, `jwt_revoke` |
| `endpoints_advertised.py` | Manejo de IPs/endpoints publicitados |

### 1.7 `network_alloc.py` — Asignación de IPs

- `_allocate_ip_in_network()`: asigna siguiente IP disponible en el CIDR de la red.
- `_assign_ip_to_peer_in_network()`: asigna IP específica o auto-asigna.

### 1.8 `auto_approve.py` — Auto-aprobación

- Evalúa reglas de auto-approve al registrarse un peer.
- Si activado, asigna automáticamente el peer a la red por defecto.

### 1.9 `hub-agent.py` — Agente privilegiado (standalone 488 líneas)

Ejecuta como root, maneja WireGuard e iptables:

- `check_dependencies()`: verifica `wg`, `wg-quick`, `iptables`, `sysctl`.
- `validate_token_at_startup()`: rechaza tokens inseguros.
- `ensure_keys()`: genera par de claves WireGuard si no existe.
- `ensure_conf()`: crea `wg-HUB.conf` con `HUB_TUNNEL_IP` y `HUB_LISTEN_PORT`.
- `ensure_wg_up()`: levanta interfaz WireGuard.
- `ensure_nat_rules()`: configura MASQUERADE y FORWARD en iptables.
- `hub_apply_peer()` / `hub_remove_peer()`: agrega/elimina peers vía `wg set`.
- `hub_list_mesh_peers()`: lista peers en modo mesh/hub-mesh.
- `HUB_MESH_MODE`: enum `off` | `mesh` | `hub-mesh` que bifurca el comportamiento.
- Soporte TLS opcional (`HUB_AGENT_TLS`).

### 1.10 `orch-cli.py` — CLI Administrativo (327 líneas)

Cliente XML-RPC con argparse:
- Subcomandos: `health`, `metrics`, `events`, `peer-list`, `peer-get`, `peer-register`, `peer-unregister`, `net-create`, `net-list`, `net-set-topology`, `net-topology`, `mesh-peers`, `user-create`, `issue-user-token`, `auth-login`, etc.
- `--admin-token` y `--token` disponibles globalmente (heredados via `parents`).

---

## 2. Agente Peer (`peer-install-v2/`)

### 2.1 `peer_register/__init__.py` — Punto de entrada

Argparse con subcomandos:
- `register`: genera claves, registra peer en orquestador, aplica config WireGuard.
- `heartbeat`: envía heartbeat con tipo NAT, verifica cambios de config, sondea peers directos en hub-mesh.
- `run`: daemon que ejecuta register + heartbeat en loop.
- `request-network`: solicita asignación a una red específica.
- `rotate-key`: rota claves WireGuard.

### 2.2 `peer_register/config.py` — Configuración

Variables de entorno: `ORCH_URL`, `ORCH_TOKEN`, `WG_IFACE`, `WG_LISTEN_PORT`, `WG_HEARTBEAT_INTERVAL`, `JWT_*`, `SESSION_DIR`, `PEER_ID`, `HOST_ID`, etc.

### 2.3 `peer_register/auth.py` — Sesión JWT

- `ensure_jwt_session()`: login inicial o refresh de JWT.
- `orch_token_for_call()`: retorna token válido (JWT o token fijo).
- `_jwt_needs_refresh()`: determina si el JWT está por expirar.

### 2.4 `peer_register/commands.py` — Implementación de comandos CLI

- `cmd_register()`: genera claves (si no existen), determina peer_id y endpoint, llama a `peer.register` vía RPC, aplica configuración.
- `cmd_heartbeat()`: recopila estado (NAT type, versión config), envía heartbeat, si el orquestador responde con `needs_reconfig=True` re-aplica config, en hub-mesh ejecuta `probe_direct_peers()`.
- `cmd_run()`: loop principal: register si es necesario, luego heartbeat periódico.
- `cmd_request_network()`: envía solicitud RPC `peer.request_network`.
- `cmd_rotate_key()`: genera nueva clave pública y notifica al orquestador.

### 2.5 `peer_register/config_gen.py` — Generación de configuración WireGuard

Corazón de la topología:
- `apply_config()`: obtiene `peer_config` del orquestador, construye bloques `[Interface]` y `[Peer]`, escribe `wg0.conf`, sincroniza con `wg syncconf`.
- `_build_interface_block()`: configura `PrivateKey`, `Address`, `ListenPort`, `MTU`, `Table`, `PostUp/PostDown`.
- `_build_hub_block()`: configura peer del hub (`AllowedIPs` = `TUNNEL_CIDR` o `0.0.0.0/0` según topología).
- `_build_mesh_blocks()`: genera peers directos (mesh) con `Endpoint`, `AllowedIPs`, `PersistentKeepalive`.
- `_build_hub_mesh_blocks()`: peers directos + relay class, con `Endpoint` dinámico (directo si `alive`/`direct`, sino relay vía hub).

### 2.6 `peer_register/identity.py` — Identidad del peer

- `peer_id_default()`: genera ID por defecto (basado en hostname o MAC).
- `peer_endpoint_guess()`: determina endpoint público (IP pública + `WG_LISTEN_PORT`).
- `owner_default()`: propietario por defecto.

### 2.7 `peer_register/keys.py` — Gestión de claves

- `gen_keys_if_needed()`: genera par WireGuard si no existe.
- `rotate_keys()`: regenera clave privada, actualiza pública.
- `load_public_key()`: lee clave pública del archivo.

### 2.8 `peer_register/nat.py` — Detección de tipo NAT

- `detect_nat_type()`: heurística que clasifica como `none`, `full-cone` o `symmetric` basado en conectividad y comportamiento de puertos.

### 2.9 `peer_register/probe.py` — Sondeo directo (hub-mesh)

- `probe_direct_peers()`: monitorea handshakes WireGuard con `wg show`, clasifica peers como `alive`/`dead`, reporta alcanzabilidad al orquestador vía `peer.report_reachability`.

### 2.10 `peer_register/utils.py` — Utilidades

- Logger, subprocess runner con timeout, file I/O, cliente XML-RPC reutilizable.

### 2.11 `wg-auto-cli.py` — CLI local del peer (275 líneas)

Subcomandos: `status`, `mesh-status`, `unregister`, `rotate-key`, `orch-health`, `topology`, `add-to-network`.

---

## 3. Testbed QEMU (`testbed/`)

### 3.1 `scripts/launch-testbed.py` — Lanzador de VMs QEMU (325 líneas)

Orquesta 3 VMs Alpine Linux en bridges separados:
- **orq** (192.168.100.10): actúa como segundo orquestador peer
- **pa** (192.168.100.20): peer-a
- **pb** (192.168.100.30): peer-b

Funcionalidades:
- `setup_network(passwd)`: crea bridges (br0/br1/br2), taps, dnsmasq DHCP.
- `launch_vm(role, passwd)`: inicia QEMU con 3 NICs cada VM (una por bridge).
- `provision_vm(role)`: setup inicial: networking, paquetes, configuración peer.env.
- `configure_vm_as_real_peer(role)`: configura VM para registrarse con orquestador real.
- `integrate_with_real_orchestrator()`: flujo completo: crear usuarios/tokens, instalar agentes, registrar VMs.
- `teardown_network(passwd)`: limpia bridges y reglas iptables.

### 3.2 `scripts/create-base-image.py` — Imagen base Alpine
### 3.3 `scripts/setup-network.sh` — Script bash para bridges/taps
### 3.4 `tests/` — Tests de integración

- `test_wireguard_integration.py`: pruebas WireGuard entre VMs QEMU.
- `test_real_orchestrator_integration.py`: registro y ping contra orquestador real.

---

## 4. Suites de Test

### 4.1 `tests-linkguard-aws/report_common.py` — Biblioteca común (1361 líneas)

Base compartida para los generadores de reportes. Componentes:

- **Constantes**: `REAL_PEERS` (5 peers cloud/terminal), `QEMU_PEERS` (3 peers QEMU), `ORCH_HOST`, `SSH_KEY`.
- **Data classes**: `PingResult`, `ThroughputResult`, `TopologyResult`.
- **Helpers SSH**: `ssh_cloud_run/script`, `ssh_terminal_run/script`, `ssh_qemu_run/script`, `ssh_orch_run`, `ssh_real_script` — cada una con reintentos (3 intentos).
- **`clean_all_peers()`**: desregistra todos los peers y limpia hub.
- **`start_all_peers()`**: reinicia servicios peer en todas las máquinas.
- **`run_topology_cycle(topology)`**: ciclo completo: clean → set topology → register → wait → ping → throughput → capture WG configs.
- **`do_all_pings()`**: matriz de pings entre todos los peers.
- **`measure_all_throughput()`**: pruebas iperf3 y HTTP entre peers.
- **`render_html()`**: genera reporte HTML auto-contenido con matrices de ping, tablas de throughput, configs WireGuard.
- **`write_jsonl_report()`**: reporte en formato JSONL.

### 4.2 Generadores de Reporte por Topología

Cada suite sigue el mismo patrón con 3 scripts:

| Archivo | Propósito |
|---|---|
| `generate-report-hubspoke.py` | Prueba topología hub-spoke (8 peers) |
| `generate-report-hubmesh.py` | Prueba topología hub-mesh (modo fast) |
| `generate-report-mesh.py` | Prueba topología mesh (modo fast) |

Flujo típico: `clean_all_peers()` → `run_topology_cycle("hub-spoke")` → `render_html()` → subida a S3.

### 4.3 Suites Adicionales

| Suite | Variante |
|---|---|
| `tests-aws-multiuser-cli/` | Multi-tenant (admin + tenant-a) con orch-cli |
| `tests-cli-multiuser/` | CLI multi-tenant |
| `tests-cli-multiuser-altcidr/` | Multi-tenant con CIDR alternativo (10.99.88.0/24) |
| `tests-expanded/` | Suite expandida |
| `tests-parrot/` | Deprecado (reemplazado por QEMU) |

### 4.4 Scripts Independientes (`scripts/`)

Versiones standalone de los generadores de reporte (sin dependencia de `report_common.py`):
- `generate-report-hubspoke.py`, `generate-report-hubmesh.py`, `generate-report-mesh.py`
- `generate-report-html.py`: variante simplificada solo HTML
- `generate-performance-report.py`: genera reporte de rendimiento a `docs/`

---

## 5. Integración y Despliegue

### 5.1 Makefile — Automatización

| Target | Descripción |
|---|---|
| `test` | Tests unitarios del orquestador |
| `topology-test` | Tests unitarios de topologías |
| `topology-test-all` | Agrega tests de integración QEMU |
| `testbed-up` / `testbed-down` | Iniciar/detener testbed QEMU |
| `testbed-up-real` | Testbed integrado con orquestador real |
| `performance-report` | Generar reporte de rendimiento |
| `typecheck` | Mypy |
| `security` | Bandit |
| `uninstall` | Limpieza remota completa |

### 5.2 Systemd Services

- `orchestrator.service`: ejecuta `orchestrator.py`
- `hub-agent.service`: ejecuta `hub-agent.py`
- `wg-auto-register.service`: ejecuta `wg-auto-register.py run`

### 5.3 Arquitectura de Red

```
         ┌──────────┐
         │  HUB     │  (wg-HUB, 10.20.30.1/24)
         │ iptables │  MASQUERADE + FORWARD
         └────┬─────┘
              │ WireGuard tunnel (10.20.30.0/24)
    ┌─────────┼─────────┐
    │         │         │
  peer-1   peer-2   peer-3 ...
  (10.20.30.2) (10.20.30.3)
```

**Topologías:**
- **hub-spoke**: todo el tráfico via hub (AllowedIPs = 0.0.0.0/0 en peer → hub)
- **mesh**: peers se conectan directo (AllowedIPs = IP específica del peer)
- **hub-mesh**: híbrido — peers directos si alcanzables, sino relay via hub

---

---

## 6. Análisis Detallado de Componentes Clave

### 6.1 `orchestrator.py` — Wrapper y Punto de Entrada

**Archivo:** `orchestrator-install-v2/orchestrator.py` (9 líneas)

```python
from orchestrator import main
main()
```

**Propósito:** Es un *wrapper de compatibilidad*. El service systemd apunta a `ExecStart=/usr/bin/python3 /opt/linkguard-orchestrator/orchestrator.py`, y este wrapper simplemente importa y ejecuta `main()` desde el paquete `orchestrator/__init__.py`. Esto permite que el código real viva en un paquete Python estructurado mientras se mantiene compatibilidad con el path legacy del service unit.

**No tiene lógica propia** — es únicamente un puente entre systemd y el paquete modular.

---

### 6.2 Paquete `orchestrator/` — Plano de Control (Control Plane)

**Propósito:** Servidor XML-RPC que funciona como **plano de control** de la red overlay. Gestiona peers, redes, topologías, autenticación y persistencia. No maneja tráfico de datos — solo coordinación.

#### 6.2.1 Módulos y Librerías

| Módulo | Librerías externas | Rol |
|---|---|---|
| `__init__.py` | `defusedxml`, `xmlrpc.server`, `socketserver.ThreadingMixIn` | Servidor XML-RPC multi-hilo, registro de ~30 handlers RPC |
| `config.py` | `os`, `logging`, `ipaddress` | Variables de entorno, logging, chequeo de dependencias |
| `auth.py` | `PyJWT`, `hashlib`, `secrets`, `threading` | JWT HS256, tokens de usuario, admin auth, cuotas multi-tenant, blacklist de JTIs |
| `state.py` | `json`, `threading`, `shutil`, `time` | Estado persistente (JSON), backups periódicos, event logging |
| `hub_client.py` | `xmlrpc.client` | Cliente XML-RPC hacia hub-agent (localhost:9000) |
| `network_alloc.py` | `ipaddress` | Asignación de IPs dentro de CIDRs de red |
| `auto_approve.py` | — | Evaluación de reglas de auto-asignación a redes por defecto |
| `endpoints_orch.py`, `endpoints_peers.py`, `endpoints_networks.py`, `endpoints_users.py`, `endpoints_auth.py`, `endpoints_config.py`, `endpoints_advertised.py` | — | Handlers de cada método RPC, organizados por dominio |

#### 6.2.2 Service systemd

**Archivo:** `systemd/orchestrator.service`

```
[Unit]
After=network-online.target hub-agent.service
Requires=hub-agent.service    ← El orquestador requiere que hub-agent esté vivo
```

- **Type:** `simple` (no fork)
- **WorkingDirectory:** `/opt/linkguard-orchestrator`
- **ExecStart:** `python3 orchestrator.py`
- **Tokens** (ADMIN_TOKEN, ORCH_TOKEN, HUB_AGENT_TOKEN): inyectados como variables de entorno por `install.sh` con valores seguros generados via `openssl rand -hex 32`
- **Restart:** `on-failure` con 5s de espera
- **Quotas:** DEFAULT_MAX_PEERS=50, DEFAULT_MAX_NETWORKS=10
- **HA-04:** Reintentos al hub-agent: HUB_RETRY_COUNT=3, HUB_RETRY_DELAY=1.0

#### 6.2.3 Flujo del Control Plane

```
1. systemd arranca orchestrator.service
2. orchestrator.py → orchestrator.main()
3. main():
   a. check_dependencies() — verifica Python, módulos
   b. validate_tokens_at_startup() — rechaza tokens inseguros
   c. state.load_state() — carga estado persistente (peers, redes, usuarios)
   d. hub_ping() — verifica conectividad con hub-agent (127.0.0.1:9000)
   e. state.start_backup_loop() — thread daemon de backups cada 300s
   f. _register_xml_handlers() — mapea 30 funciones RPC
   g. server.serve_forever() — XML-RPC en 0.0.0.0:8000/RPC2

4. Por cada petición RPC entrante:
   a. _Handler.do_POST captura client_address en thread-local
   b. El wrapper _xml_* traduce args posicionales a dict
   c. _safe_call ejecuta el handler con manejo de Faults:
      - PermissionError → Fault 1 (403)
      - KeyError → Fault 1 (404)
      - ValueError → Fault 1 (400)
      - RuntimeError → Fault 1 (503)
   d. El handler retorna dict → serializado a XML-RPC
```

---

### 6.3 `hub-agent.py` — Plano de Datos (Data Plane)

**Archivo:** `orchestrator-install-v2/hub-agent.py` (488 líneas, archivo único sin paquete)

**Propósito:** Ejecuta como **root** y maneja todo lo que requiere privilegios: configuración WireGuard del hub, reglas iptables NAT, y enrutamiento. Es el **plano de datos** — el tráfico de red pasa por las interfaces que él configura.

#### 6.3.1 Librerías y Módulos

| Librería | Uso |
|---|---|
| `defusedxml.xmlrpc` | Monkey-patch de seguridad contra XML bombs |
| `ipaddress` | Validación y filtrado de CIDRs en `hub_list_mesh_peers` |
| `os` | Variables de entorno, rutas de archivos |
| `secrets` | Comparación segura de tokens (`compare_digest`) |
| `shutil` | `which()` para verificar dependencias |
| `ssl` | Soporte TLS opcional (HA-02) para el servidor XML-RPC |
| `subprocess` | Ejecución de `wg`, `wg-quick`, `iptables`, `sysctl` |
| `time` | Timestamps para handshake timeouts |
| `xmlrpc.server` | Servidor XML-RPC propio (independiente del orquestador) |

**No usa paquetes externos** — todo es stdlib + binarios del sistema (`wg`, `iptables`, `sysctl`).

#### 6.3.2 Service systemd

**Archivo:** `systemd/hub-agent.service`

```
[Unit]
After=network-online.target    ← No requiere el orquestador
```

- **ExecStart:** `python3 hub-agent.py`
- **ExecStop:** `hub-agent-cleanup.sh` (OPS-01 — limpia reglas iptables al detener)
- **HUB_AGENT_BIND:** `127.0.0.1` (HA-03 — no expuesto a la red)
- **HUB_AGENT_PORT:** `9000`
- **HUB_MESH_MODE:** `off` por defecto; `mesh` o `hub-mesh` según topología
- **TLS:** Opcional (`HUB_AGENT_TLS=0` por defecto)

#### 6.3.3 Arquitectura Interna

```
hub-agent.py
├── Configuración (líneas 36-101): vars de entorno con validación
├── check_dependencies() (119-136): verifica wg, wg-quick, iptables, sysctl
├── validate_token_at_startup() (141-149): rechaza tokens débiles
├── Bootstrap WireGuard (152-218)
│   ├── ensure_keys() — genera par de claves si no existe
│   ├── ensure_conf() — crea wg-HUB.conf
│   └── ensure_wg_up() — levanta interfaz con wg-quick
├── IPTABLES / SYSCTL (222-290)
│   ├── ensure_ip_forward() — net.ipv4.ip_forward=1
│   ├── ensure_forward_rule() — FORWARD wg↔wg ACCEPT
│   ├── ensure_nat_rules() — MASQUERADE + FORWARD wg↔eth0
│   └── cleanup_iptables_rules() — reverse de todo lo anterior
├── Endpoints XML-RPC (304-430)
│   ├── hub_health()          → "ok"
│   ├── hub_public_key()      → clave pública del hub
│   ├── hub_apply_peer()      → wg set <iface> peer <pub> allowed-ips <ips> [endpoint]
│   ├── hub_remove_peer()     → wg set <iface> peer <pub> remove
│   ├── hub_ensure_base_rules() → re-aplica bootstrap
│   ├── hub_show()            → wg show dump (full estado)
│   ├── hub_cleanup()         → llama cleanup_iptables_rules()
│   └── hub_list_mesh_peers() → parsea dump, filtra por CIDR, retorna alive/dead
└── Servidor (439-484)
    ├── bind: HUB_AGENT_BIND:HUB_AGENT_PORT (127.0.0.1:9000)
    ├── TLS opcional: SSLContext con TLS 1.2+ solamente
    └── 8 funciones RPC registradas
```

#### 6.3.4 hub_apply_peer — Comportamiento por Topología

```python
if HUB_MESH_MODE == "mesh":
    # En mesh: solo AllowedIPs /32 (IPs individuales de peers)
    # No se asigna ruta 0.0.0.0/0 — el tráfico no pasa por el hub
    allowed_ips = solo_ips_con_mascara_32

elif HUB_MESH_MODE == "hub-mesh":
    # En hub-mesh: peers directos + relay
    # El hub mantiene AllowedIPs completos + NAT para relay
    # HUB_MESH_RELAY=1 mantiene MASQUERADE activo

else:  # "off" (hub-spoke)
    # AllowedIPs completos (usualmente 0.0.0.0/0)
    # Todo el tráfico pasa por el hub
```

#### 6.3.5 Diferencia Control Plane vs Data Plane

| Aspecto | Orchestrator (control plane) | Hub-agent (data plane) |
|---|---|---|
| Puerto | 0.0.0.0:8000 (accesible desde red) | 127.0.0.1:9000 (solo local) |
| Autenticación | JWT + tokens de usuario + admin token | Token fijo compartido (HUB_AGENT_TOKEN) |
| Privilegios | No requiere root (pero corre como root) | **Requiere root** (wg, iptables) |
| Estado | Persistente en disco (JSON) | Sin estado — todo vía `wg show` |
| Lenguaje | Paquete modular (7 módulos) | Archivo único (488 líneas) |
| Dependencias | Python: PyJWT, defusedxml | Solo stdlib + binarios sistema |
| Rol | Coordinación, registro, topología | Configuración WireGuard + iptables |

---

### 6.4 `orch-cli.py` — Interfaz de Línea de Comandos

**Archivo:** `orchestrator-install-v2/orch-cli.py` (327 líneas)

**Propósito:** Cliente administrativo del orquestador vía XML-RPC. Permite administrar peers, redes, usuarios y topologías desde terminal.

#### 6.4.1 Librerías y Módulos

| Librería | Uso |
|---|---|
| `os` | Variables de entorno `ADMIN_TOKEN`, `JWT`, `ORCH_URL` |
| `json` | Formateo `pretty()` de respuestas RPC |
| `argparse` | Definición de ~25 subcomandos con argumentos |
| `xmlrpc.client.ServerProxy` | Cliente XML-RPC hacia `ORCH_URL` |

**No tiene dependencias externas** — todo stdlib.

#### 6.4.2 Estructura de Subcomandos

```
orch-cli [--url URL] [--admin-token TOKEN] [--token JWT] <comando> [args]

Comandos:
├── health, metrics, events          → monitoreo del orquestador
├── user-create, user-list,          → gestión de tenants (admin-only)
│   user-get, user-delete,
│   issue-user-token
├── auth-login, auth-refresh,        → autenticación JWT
│   auth-whoami
├── revoke                           → revocar JWT por jti
├── net-create, net-list, net-get,   → gestión de redes
│   net-delete, net-set-topology,
│   net-topology
├── mesh-peers, peer-reachability    → consulta topología mesh/hub-mesh
├── peer-list, peer-get,             → gestión de peers
│   peer-update-admin, peer-unregister
├── assign-network, remove-network   → membresía de red
```

#### 6.4.3 Mecanismo de Autenticación

- `--admin-token` (o `ADMIN_TOKEN` env): para operaciones administrativas (crear usuarios, redes, asignar peers)
- `--token` (o `JWT` env): JWT de tenant obtenido via `auth-login`
- Ambos disponibles en **todos** los subcomandos gracias al `parents=[shared]` de argparse

#### 6.4.4 Flujo de Llamada

```
1. argparse.parse_args()
2. ServerProxy(args.url) — conexión XML-RPC
3. Por comando:
   - Ejemplo: orch-cli peer-list --admin-token XXX
   → c.__getattr__("peer.list")(None, "XXX", None)
   → pretty(respuesta)
   
   - Ejemplo: orch-cli auth-login tenant-a mi-token
   → c.__getattr__("auth.login")("tenant-a", "tenant-a", "mi-token", ["*"], None)
   → imprime JWT + instrucción "export JWT=..."

4. Cada llamada RPC viaja a ORCH_URL/RPC2 como XML
5. Respuesta JSON formateada con pretty()
```

---

### 6.5 Scripts de Instalación

#### 6.5.1 `install.sh` — Instalador del Orquestador

**Archivo:** `orchestrator-install-v2/install.sh` (253 líneas)

**Propósito:** Instalación automatizada del orquestador, hub-agent y orch-cli en cualquier distro Linux con systemd.

**Fases:**

| Fase | Líneas | Descripción |
|---|---|---|
| **Preflight** | 6-9 | Verifica `root` |
| **Detección de SO** | 26-43 | Lee `/etc/os-release`, detecta `apt`/`dnf`/`yum`/`pacman`/`zypper`/`apk` |
| **Detección iptables** | 48-76 | Función `iptables_present()` + `install_iptables_if_missing()` — maneja `iptables` vs `iptables-nft` |
| **Instalación de dependencias** | 79-143 | `install_deps()`: por gestor de paquetes, instala `python3`, `wireguard-tools`, `defusedxml`, `pyjwt`, `iptables`, `openssl` |
| **Validación de archivos** | 150-161 | Verifica que existan: `orchestrator.py`, `hub-agent.py`, `orch-cli.py`, `systemd/*.service`, etc. |
| **Creación de directorios** | 169-175 | `/opt/linkguard-orchestrator`, `/etc/linkguard`, `/var/lib/wg-orchestrator/backups` |
| **Generación de tokens** | 178-200 | Solo en primera instalación: `openssl rand -hex 32` para ADMIN_TOKEN, ORCH_TOKEN, HUB_AGENT_TOKEN + JWT secret de 64 bytes |
| **Instalación de archivos** | 207-213 | Copia `orchestrator/` (paquete completo), `hub-agent.py`, `hub-agent-cleanup.sh`, `orch-cli.py` → `/usr/local/bin/orch-cli` |
| **Systemd units** | 216-229 | Hace `sed` sobre los templates para inyectar tokens, luego copia a `/etc/systemd/system/` |
| **Arranque** | 232-242 | `daemon-reload`, habilita e inicia servicios (hub-agent → orchestrator) |
| **Output** | 245-253 | Muestra rutas de tokens y estado de servicios |

**Mecanismo de seguridad:**
- Tokens generados con `openssl rand -hex 32` (256 bits)
- `SECRETS_FILE` con permisos `600` (solo root)
- `JWT_SECRET_FILE` con `openssl rand -hex 64` (512 bits), permisos `600`
- `systemd service files` con permisos `600`
- Los templates tienen `REPLACE_WITH_SECURE_TOKEN` — `install.sh` nunca deja valores inseguros

**Soporte multi-distro:**

| Gestor | Comando de instalación |
|---|---|
| `apt` (Debian/Ubuntu) | `apt-get install -y python3 python3-venv python3-pip python3-defusedxml python3-jwt wireguard-tools curl ca-certificates openssl` |
| `dnf` (Fedora/RHEL 8+) | `dnf -y install python3 python3-pip python3-defusedxml python3-pyjwt wireguard-tools curl ca-certificates openssl` |
| `yum` (RHEL 7) | Ídem dnf |
| `pacman` (Arch) | `pacman -Sy --noconfirm --needed python python-pip python-defusedxml python-pyjwt wireguard-tools curl ca-certificates openssl` + manejo especial iptables vs iptables-nft |
| `zypper` (openSUSE) | `zypper --non-interactive install -y python3 python3-pip python3-defusedxml python3-PyJWT wireguard-tools curl ca-certificates openssl` |
| `apk` (Alpine) | `apk add --no-cache python3 py3-pip py3-defusedxml py3-pyjwt wireguard-tools curl ca-certificates openssl` |

#### 6.5.2 `install.sh` — Instalador del Peer

**Archivo:** `peer-install-v2/install.sh` (292 líneas)

**Diferencias clave vs instalador del orquestador:**

- **Propósito:** Instala solo el agente peer (`wg-auto-register`) y CLI (`wg-auto-cli`).
- **No genera tokens** — el `ORCH_TOKEN` debe ser configurado manualmente en `/etc/linkguard/peer.env` (obtenido del admin del orquestador).
- **Soporta systemd y OpenRC** (Alpine usa OpenRC).
- **Valida ORCH_TOKEN** antes de arrancar el servicio — si está vacío o es `REPLACE_WITH_YOUR_TOKEN`, no inicia y advierte al usuario.
- **Crea wrapper** `/usr/local/bin/wg-auto-register` que ejecuta `python3 /opt/linkguard-peer/wg-auto-register.py $@`.
- **Sistema de detección de Python:** prueba `python3` primero, luego `python` (importante para Arch Linux donde el binario es `python`).
- **Manejo de lock de pacman:** detecta y remueve locks stale.
- **Service unit** generado inline con `EnvironmentFile=/etc/linkguard/peer.env`.

#### 6.5.3 `hub-agent-cleanup.sh` — Script de Limpieza

**Archivo:** `orchestrator-install-v2/hub-agent-cleanup.sh` (19 líneas)

**Propósito:** Elimina las reglas iptables creadas por hub-agent. Llamado por `ExecStop` del service systemd.

**Reglas que elimina:**
```bash
iptables -D FORWARD -i wg-HUB -o wg-HUB -j ACCEPT
iptables -D FORWARD -i wg-HUB -o eth0 -j ACCEPT
iptables -D FORWARD -i eth0 -o wg-HUB -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -t nat -D POSTROUTING -s 10.20.30.0/24 -o eth0 -j MASQUERADE
```

**Características:**
- Variables configurables via entorno: `HUB_WG_IFACE`, `HUB_NAT_OUT_IFACE`, `HUB_TUNNEL_CIDR`, `IPTABLES_BIN`
- `2>/dev/null || true` — ignora errores si la regla ya fue eliminada manualmente
- Corresponde 1:1 con las reglas creadas por `ensure_nat_rules()` + `ensure_forward_rule()` en `hub-agent.py`
- **OPS-01:** implementa la operación de limpieza para evitar acumulación de reglas en reinicios

---

### 6.6 Resumen de Services Systemd

| Service | Archivo | Ejecuta | Puerto | Depende de |
|---|---|---|---|---|
| `orchestrator.service` | `systemd/orchestrator.service` | `python3 orchestrator.py` | 0.0.0.0:8000 | `hub-agent.service` |
| `hub-agent.service` | `systemd/hub-agent.service` | `python3 hub-agent.py` | 127.0.0.1:9000 | `network-online.target` |
| `wg-auto-register.service` | Generado por `peer-install-v2/install.sh` | `wg-auto-register run` | — (cliente saliente) | `network-online.target` |

**Relación de arranque:**
```
network-online.target
  └── hub-agent.service (data plane, root)
        └── orchestrator.service (control plane, root)
              └── (peers se conectan vía HTTP XML-RPC)
```

El hub-agent arranca primero porque el orquestador requiere `hub_ping()` exitoso en `main()`. Los peers son independientes — se conectan al orquestador cuando están listos.

---

## 7. Seguridad

- **JWT HS256**: secret recargable en caliente, blacklist de JTIs revocados.
- **Tokens de usuario**: SHA-256, uno por tenant.
- **ADMIN_TOKEN**: requerido para operaciones administrativas.
- **Validación al arranque**: hub-agent rechaza tokens inseguros (`changeme`, vacío).
- **defusedxml**: monkey-patch contra XML bombs.
- **Multi-tenant**: cuotas de peers y redes por usuario.

---

## 7. Flujo de Operación Típico

```
1. Administrador crea usuario y genera token:
   orch-cli user-create tenant-a --admin-token XXX
   orch-cli issue-user-token tenant-a --admin-token XXX

2. Crea red con topología:
   orch-cli net-create red-principal 10.20.30.0/24
   orch-cli net-set-topology red-principal hub-spoke

3. En cada peer, instalar y ejecutar agente:
   wg-auto-register run

   El agente:
     a. Genera claves WireGuard
     b. Obtiene JWT (login con token de tenant)
     c. Se registra: peer.register(peer_id, public_key, endpoint)
     d. Obtiene config: config.get_peer_config(peer_id, jwt)
     e. Genera wg0.conf y aplica con wg syncconf
     f. Envía heartbeats periódicos con tipo NAT
     g. En hub-mesh: sondea peers directos y reporta reachability

4. Pruebas:
   pytest tests-linkguard-aws/generate-report-hubspoke.py
```
