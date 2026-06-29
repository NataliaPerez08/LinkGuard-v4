# LinkGuard v4 — Análisis de la implementación del orquestador y el agente peer

## 1. Arquitectura general

LinkGuard v4 consta de **dos demonios XML-RPC cooperantes** que se ejecutan en el nodo hub (orquestador), más un **agente peer** desplegado en cada nodo participante. No usa base de datos externa — todo el estado se persiste en archivos JSON. La comunicación entre componentes usa XML-RPC sobre HTTP.

```
┌─────────────────────────────────────────────────────────────────┐
│                     NODO HUB (nube / VPS)                       │
│                                                                  │
│  ┌──────────────────────────┐     ┌──────────────────────────┐  │
│  │      ORCHESTRATOR        │     │       HUB-AGENT          │  │
│  │  (orchestrator/__init__.py) │     │  (hub-agent.py)          │  │
│  │  Puerto 8000 /RPC2       │────▶│  Puerto 9000 /RPC2       │  │
│  │  Bookkeeping, auth,      │     │  wg set, iptables,      │  │
│  │  topologías, IP alloc    │     │  dump de sesiones        │  │
│  └──────────┬───────────────┘     └──────────────────────────┘  │
│             │                        │                           │
│             │           ┌────────────┘                           │
│             ▼           ▼                                        │
│  ┌─────────────────────────────────────┐                         │
│  │   /var/lib/wg-orchestrator/        │                         │
│  │   state.json    (estado principal) │                         │
│  │   jwt_revoked.json (revocaciones)  │                         │
│  └─────────────────────────────────────┘                         │
└──────────────────────────────────────────────────────────────────┘
             │
             │ XML-RPC (puerto 8000)
             │
┌──────────────────────────────────────────────────────────────────┐
│                    PEER (nodo remoto)                            │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  wg-auto-register (peer_register/)                        │  │
│  │  Demonio que cada 25s:                                    │  │
│  │  1. Refresca JWT (auth.login / auth.refresh)              │  │
│  │  2. peer.heartbeat → con wg show + nat_type + endpoint    │  │
│  │  3. Detecta drift (config_version / mesh_peers_hash)      │  │
│  │  4. Reaplica config (wg syncconf sin teardown)            │  │
│  │  5. Si hub-mesh → probe de handshakes                     │  │
│  ├────────────────────────────────────────────────────────────┤  │
│  │  /etc/wireguard/wg0.conf   (generado por config_gen.py)    │  │
│  │  /etc/wireguard/wg-auto.json (estado local, chmod 600)    │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. Orquestador (`orchestrator-install-v2/`)

### 2.1 Estructura de directorios

```
orchestrator-install-v2/
├── orchestrator.py                  # shim: from orchestrator import main; main()
├── orch-cli.py                      # CLI admin/tenant (27 subcomandos)
├── hub-agent.py                     # data-plane WG, puerto 9000
├── install.sh / uninstall.sh        # instalación / desinstalación
├── systemd/
│   ├── orchestrator.service         # ExecStart=python3 orchestrator.py
│   │                                # Requires=hub-agent.service
│   └── hub-agent.service           # ExecStart=python3 hub-agent.py
├── tests/                           # pytest suite
└── orchestrator/                    # PAQUETE PRINCIPAL
    ├── __init__.py                  # Bootstrap, wrappers _xml_*, dispatch
    ├── config.py                    # Constantes, validación de tokens
    ├── state.py                     # JSON persistente, locks, backups
    ├── auth.py                      # JWT, multi-tenant, quotas, revocación
    ├── hub_client.py                # Cliente XML-RPC → hub-agent
    ├── network_alloc.py             # Pool de IPs dentro de CIDR
    ├── auto_approve.py              # Auto-registro por tags
    ├── endpoints_peers.py           # RPC: register, heartbeat, rotate_key...
    ├── endpoints_networks.py        # RPC: CRUD de redes, topología
    ├── endpoints_config.py          # RPC: generación de configs peer
    ├── endpoints_auth.py            # RPC: issue/verify/revoke JWT
    ├── endpoints_users.py           # RPC: CRUD de tenants
    ├── endpoints_advertised.py      # RPC: endpoints publicitados
    └── endpoints_orch.py            # RPC: health, events, metrics
```

### 2.2 Bootstrap y servidor XML-RPC (`orchestrator/__init__.py`)

El punto de entrada real es `orchestrator/__init__.py:380` (`main()`). El `orchestrator.py` raíz es un shim de 9 líneas que preserva la ruta del systemd `ExecStart`.

**`__init__.py:7-8`** — Se aplica `defusedxml.xmlrpc.monkey_patch()` para endurecer el parser XML-RPC contra ataques de expansión de entidades (`# nosec B411`).

**`__init__.py:23-31`** — `_Handler(SimpleXMLRPCRequestHandler)` pinnea la ruta a `/RPC2` y guarda `client_address` en thread-local (`_rpc_context`) para que los handlers conozcan la IP real del peer (crítico para NAT).

**`__init__.py:34-36`** — `_Server(ThreadingMixIn, SimpleXMLRPCServer)` con `daemon_threads=True`, `allow_reuse_address=True`.

**`__init__.py:39-49`** — `_safe_call()`: traductor uniforme de excepciones → `xmlrpc.client.Fault`:
| Excepción | Código Fault |
|-----------|-------------|
| `PermissionError` | 403 |
| `KeyError` | 404 |
| `ValueError` | 400 |
| `RuntimeError` | 503 |

Esto permite que los handlers lancen excepciones Python estándar en lugar de devolver diccionarios de error.

**`__init__.py:380-409`** — `main()`:
1. `config.check_dependencies()` y `config.validate_tokens_at_startup()` — rechaza tokens vacíos/inseguros.
2. `state.load_state()` y `state.start_backup_loop()` — hilo background que snapshotea cada `BACKUP_INTERVAL_SEC` (300s).
3. `hub_ping()` — verifica reachabilidad del hub-agent.
4. `server.serve_forever()` — en `KeyboardInterrupt` persiste estado y cierra socket.

**`__init__.py:341-377`** — `_register_xml_handlers()`: registra **31 métodos RPC**. Cada método legacy (convención posicional) se envuelve en un `_xml_*` que traduce argumentos posicionales a kwargs y delega en `endpoints_*.rpc_*`:

| Método RPC | Wrapper | Handler destino |
|-----------|---------|----------------|
| `peer.register` | `_xml_peer_register:243` | `endpoints_peers.rpc_peer_register` |
| `peer.heartbeat` | `_xml_peer_heartbeat:255` | `endpoints_peers.rpc_peer_heartbeat` |
| `peer.rotate_key` | `_xml_peer_rotate_key:267` | `endpoints_peers.rpc_peer_rotate_key` |
| `peer.unregister` | `_xml_peer_unregister:279` | `endpoints_peers.rpc_peer_unregister` |
| `config.get_peer_config` | `_xml_config_get:289` | `endpoints_config.rpc_config_get_peer_config` |
| `config.get_mesh_peers` | `_xml_mesh_peers:300` | `endpoints_config.rpc_config_get_mesh_peers` |
| `auth.login` | `_xml_auth_login:55` | `auth._jwt_encode` |
| `auth.refresh` | `_xml_refresh:69` | verifica JTI contra revocación, re-emite |
| `network.create` | `_xml_network_create:175` | `endpoints_networks.rpc_network_create` |
| `hub.*` | vía `hub_client.py` | hub-agent |

### 2.3 Hub-agent (`hub-agent.py`)

Demonio co-locado que **sí manipula WireGuard**. 488 líneas, sin dependencias externas (solo stdlib + `subprocess` para `wg`, `iptables`, `sysctl`).

**Arquitectura interna:**
- `hub-agent.py:44-45` — bindea `127.0.0.1:9000` (`XML_RPC_HOST`, `XML_RPC_PORT`).
- `hub-agent.py:83-92` — `HUB_MESH_MODE` (enum `off|mesh|hub-mesh`).
- `hub-agent.py:119-135` — `check_dependencies()`: verifica `wg`, `wg-quick`, `iptables`, `sysctl`.
- `hub-agent.py:141-149` — `validate_token_at_startup()`.
- `hub-agent.py:297` — autenticación: `secrets.compare_digest(token, HUB_AGENT_TOKEN)`.
- `hub-agent.py:379-429` — `hub_list_mesh_peers()`: parsea `wg show wg-HUB dump` y devuelve lista autoritativa `[(public_key, endpoint, allowed_ips, latest_handshake, alive), ...]`.
- `hub-agent.py:309-336` — `hub_apply_peer()`: en mesh puro filtra todo lo que no sea `/32` de `allowed_ips`; en hub-mesh loggea "relay activo"; luego ejecuta `wg set wg-HUB peer <pubkey> allowed-ips <csv> endpoint <ep>`.
- `hub-agent.py:474-481` — registro de métodos `hub.health, hub.public_key, hub.apply_peer, hub.remove_peer, hub.ensure_base_rules, hub.show, hub.cleanup, hub.list_mesh_peers`.

### 2.4 Registro y ciclo de vida de peers (`endpoints_peers.py`)

**`rpc_peer_create`** (`endpoints_peers.py:36-80`):
- Entrada admin/internal. Genera `peer_id` = `p_` + 8 hex aleatorios.
- Asigna IP de túnel via `network_alloc._allocate_ip_in_network`.
- Persiste peer dict con campos: `public_key, ip, networks, user_id, metadata, enabled, created_ts, keepalive` (líneas 56-65).
- Llama `hub_client._hub_apply_peer_allowed_ips(peer_id)`.
- Primero intenta `auto_approve.try_auto_approve` para peers con tags.

**`rpc_peer_register`** (`endpoints_peers.py:83-145`):
- Entrada tenant-facing. Requiere JWT con scope `peer:write` (`_require_peer_jwt`, líneas 18-29).
- Si peer_id existe → update (con check cross-tenant, líneas 102-103).
- Si no existe → deriva a `rpc_peer_create`.
- Devuelve `{peer_id, wg_ip, config_version}`.
- Siempre llama `state.bump_config_version_locked()`.

**`rpc_peer_heartbeat`** (`endpoints_peers.py:228-292`):
1. Actualiza `last_heartbeat` en estado.
2. Si el endpoint self-reportado es privado (`ipaddress.ip_address(ep.host).is_private`), lo sobreescribe con la IP pública real vista en el socket TCP (líneas 246-257 — del thread-local `_rpc_context.client_address`).
3. Consulta `hub.list_mesh_peers` via `_get_wg_endpoint` para obtener el puerto NAT-remapeado desde WG.
4. Devuelve `desired_config_version` + `mesh_peers_hash`/`hub_mesh_peers_hash` para que los peers diffeen.

**`rpc_peer_unregister`** (`endpoints_peers.py:424-457`):
- Remueve peer del hub (`hub_client.hub_remove_peer`).
- Libera IPs en todas sus redes (`network_alloc._network_release_ip`).
- Bump de config_version.

**`rpc_peer_rotate_key`** (`endpoints_peers.py:312-329`):
- Reemplaza `public_key` y bump de config_version.

### 2.5 Topologías (`endpoints_config.py`)

Las topologías son una propiedad por-red (`config.py:65`): `{"hub-spoke", "mesh", "hub-mesh"}`. Se asignan via `endpoints_networks.rpc_network_set_topology` (`endpoints_networks.py:67-78`).

#### Hub-Spoke
El caso por defecto. `rpc_config_get_peer_config` (`endpoints_config.py:16-76`) devuelve un solo bloque `[Peer]` apuntando a `config.HUB_ENDPOINT` con `allowed_ips = network["cidr"]`. Sin mesh peers.

#### Mesh
**`_get_alive_mesh_peers`** (`endpoints_config.py:98-121`):
1. Itera `network["alloc"]["assigned"]`.
2. Excluye al requester.
3. Marca cada peer `alive` si `last_heartbeat` está dentro de `HEARTBEAT_TTL_SEC` (180s, `config.py:38`).
4. Ordena alive-first.
5. Trunca en `MESH_MAX_PEERS` (50, `config.py:67`).
6. Output: `[{peer_id, public_key, endpoint, tunnel_ip, alive, last_seen_ts}, ...]`.
7. Se adjunta un SHA-256 hash de esta lista a la respuesta y al ack del heartbeat.

> **Nota importante**: El campo `endpoint` se incluye **siempre** (incluso si `alive=False`). Este es el fix documentado en AGENTS.md que resolvió el problema mesh `0/7` — sin esto, peers detrás de NAT no recibían `[Peer]` block.

#### Hub-Mesh (híbrido)
**`_classify_peers_for_hub_mesh`** (`endpoints_config.py:124-176`):

Clasifica cada peer vivo como `direct` o `relay_only`. La decisión (líneas 161-169) considera:

```python
is_direct = (
    relay_mode != "force_relay"
    AND endpoint present
    AND target nat_type != "symmetric"
    AND (relay_mode == "force_direct" OR not previously reported as hub-relay)
)
```

- Si el requester tiene `nat_type == "symmetric"` → fuerza todos a relay (líneas 158-160, porque peers con NAT simétrica no pueden completar P2P sin un bloque `[Peer]`).
- El `allowed_ips` del bloque hub se reescribe al `relay_cidr` (o al CIDR de red), para que el tráfico de relay pase por el hub.

### 2.6 Generación de configs peer (`endpoints_config.py:16-76`)

`rpc_config_get_peer_config` devuelve un blob JSON que el peer consume:

```json
{
  "interface": {
    "address": "<ip>/32",
    "mtu": 1420
  },
  "peer": {
    "public_key": "<hub_pubkey>",
    "endpoint": "<HUB_ENDPOINT>",
    "allowed_ips": "<relay_cidr o network_cidr>",
    "persistent_keepalive": 25
  },
  "meta": {
    "topology": "<hub-spoke|mesh|hub-mesh>",
    "config_version": 42,
    "mesh_peers_hash": "sha256...",
    "hub_mesh_peers_hash": "sha256..."
  },
  "mesh_peers": [...],
  "hub_mesh_direct_peers": [...],
  "hub_mesh_relay_peers": [...]
}
```

- La public key del hub se obtiene via `hub_client._hub_call_with_retry("hub.public_key", HUB_AGENT_TOKEN)` (`endpoints_config.py:49`).
- El `allowed_ips` inicial se selecciona como `hub_mesh_relay_fallback_cidr` si existe, sino `network["cidr"]` (`endpoints_config.py:51`).

### 2.7 Autenticación y autorización (`auth.py`)

Dos mecanismos complementarios:

#### Tokens compartidos (legacy)
- **`ADMIN_TOKEN`** (`config.py:31`): maestro para RPCs de admin, validado por `auth.orch_check_admin_token` (`auth.py:135-141`).
- **`HUB_AGENT_TOKEN`** (`config.py:27`): secreto orquestador↔hub-agent.
- **Tokens por tenant**: `auth._issue_user_token` (`auth.py:200-209`) genera `u_` + 16 hex bytes.

#### JWT (moderno)
- Algoritmo: HMAC-SHA256.
- Secreto: `/etc/linkguard/jwt_secret`.
- **Recargable en caliente** (`auth.py:22-43`): `_read_jwt_secret` cachea el secreto pero lo recarga cuando su SHA-256 cambia.
- Claims: `{iss, aud, iat, nbf, exp, jti}`. `_jwt_decode` (`auth.py:62-67`) exige TODOS los claims.
- **Revocación**: JTI-based, persistida en `/var/lib/wg-orchestrator/jwt_revoked.json` (`auth.py:74-105`). JTIs revocados más viejos que `exp` se podan al escribir.
- `_auth_from_token` (`auth.py:108-123`): reconoce JWTs (2 puntos + len > 30, línea 70-71), devuelve `(mode, user_id, scopes, is_admin_jwt)`.
- `_require_scope` (`auth.py:126-132`): soporta `scope`, `prefix:*`, `*:*`, `*`.

#### Aislamiento multi-tenant
- `_enforce_tenant_for_peer` (`auth.py:144-183`): lanza `PermissionError("cross-tenant forbidden")` si el `user_id` del JWT no coincide con `peer.user_id`.
- `_filter_events_for_tenant` (`auth.py:161-183`): filtra eventos por peer/network del tenant.
- **Cuotas** (`auth.py:220-244`): `_check_peer_quota` y `_check_network_quota` (defaults 50 peers / 10 redes por tenant, `config.py:59-60`).

### 2.8 Persistencia de estado (`state.py`)

No hay base de datos — todo es JSON en archivos.

- `STATE` es un dict a nivel de módulo (`state.py:58`). `DEFAULT_STATE` (`state.py:49-56`):
  ```python
  {version: 4, config_version: 1, users: {}, peers: {}, networks: {}, events: []}
  ```
- `STATE_PATH` = `/var/lib/wg-orchestrator/state.json` (`config.py:24`).
- **Jerarquía de locks** (`state.py:14-20`): `LOCK_USERS > LOCK_NETWORKS > LOCK_PEERS > LOCK_EVENTS > LOCK_STATE > LOCK_REVOKED`. El comentario "nunca invertir" documenta que el orden es obligatorio para prevenir deadlocks.
- `save_json` (`state.py:41-46`): escribe a `<path>.tmp` + `os.replace()` — operación atómica crash-safe.
- **Backup loop** (`state.py:79-108`): cada `BACKUP_INTERVAL_SEC` (300s) escribe snapshot a `BACKUP_DIR/state-<YYYYmmddTHHMMSS>.json`. Solo mantiene los últimos `BACKUP_MAX_KEEP` (10).
- **Eventos**: `add_event` (`state.py:70-76`) escribe a dos sinks: ring-buffer in-memory (cap `EVENTS_IN_STATE_MAX=200`, `config.py:55`) y archivo JSONL (`EVENTS_LOG_PATH`).
- **`bump_config_version_locked`** (`state.py:131-134`): incrementa la generación monótona que los peers usan para decidir si re-fetch config.

### 2.9 Asignación de IPs (`network_alloc.py`)

- `_allocate_ip_in_network` (`network_alloc.py:11-27`): enumera IPs en el CIDR desde `network_address + 2` (`.1` reservado para el hub WG), salteando las ya usadas. RuntimeError si se agota el subnet.
- `_ensure_network_alloc_struct` (`network_alloc.py:30-34`): construye lazy `n["alloc"] = {"reserved": [], "assigned": {peer_id: ip, ...}}`.
- `_assign_ip_to_peer_in_network` (`network_alloc.py:49-66`): short-circuit si el peer ya tiene IP en esa red.
- `_network_release_ip` (`network_alloc.py:37-46`): libera IP al unregister o remove-from-network.

### 2.10 Auto-approval (`auto_approve.py`)

Cuando `AUTO_APPROVE_ENABLED=1` (env en `config.py:40`), peers pueden auto-registrarse con un `metadata.tag` que matchee una regla en `AUTO_APPROVE_RULES` (`config.py:113-125`, formato `tag1:cidrA|tag2:cidrB`).

`try_auto_approve` (`auto_approve.py:29-77`):
1. Verifica tag contra reglas.
2. Rechaza re-aprobar una public_key existente.
3. Asigna IP en el CIDR de la regla.
4. Crea peer con `user_id="system"`.
5. Pushea allowed-ips al hub.

### 2.11 Comunicación orquestador↔hub-agent (`hub_client.py`)

- `_hub_call_with_retry` (`hub_client.py:19-31`): backoff exponencial `HUB_RETRY_DELAY * 2**attempt`, hasta `HUB_RETRY_COUNT=3`.
- `_hub_apply_peer_allowed_ips` (`hub_client.py:82-107`): construye `allowed_ips` CSV desde `_peer_all_allowed_ips` (`hub_client.py:49-54`, formato `{ip}/32`). Si el endpoint del peer es público (`_is_public_endpoint`, `hub_client.py:57-66` — chequea `ipaddress.ip_address(host).is_global`), consulta `hub.list_mesh_peers` para obtener el *WG-learned endpoint* y reescribe el puerto preservando el mapeo NAT.

### 2.12 CLI del orquestador (`orch-cli.py`)

- Parent parser compartido (`orch-cli.py:17-22`) con `--admin-token`/`--token` — este es el fix de argparse mencionado en AGENTS.md.
- 27 subcomandos, cada uno ejecuta `c.__getattr__("rpc.name")(...)`.
- Orden de resolución de token: `args.token or args.admin_token or env JWT`.
- Subcomandos notables:
  - `auth-login` (`orch-cli.py:137-143`): imprime `export JWT=...`.
  - `net-set-topology` (`orch-cli.py:226-239`): valida contra `["hub-spoke","mesh","hub-mesh"]`.
  - `mesh-peers` (`orch-cli.py:241-272`): renderiza `config.get_mesh_peers` como tabla.
  - `peer-reachability` (`orch-cli.py:275-298`): mismo RPC pero con columna `REACHABLE`.

---

## 3. Agente peer (`peer-install-v2/` — wg-auto-register v4)

### 3.1 Estructura de directorios

```
peer-install-v2/
├── wg-auto-register.py          # shim: from peer_register import main; main()
├── wg-auto-cli.py               # CLI local (/usr/local/bin/wg-auto-cli)
├── install.sh / uninstall.sh    # instalación cross-distro
├── peer.env.example             # template (chmod 600)
├── systemd/
│   └── wg-auto-register.service
└── peer_register/               # PAQUETE PRINCIPAL
    ├── __init__.py              # argparse dispatch
    ├── config.py                # carga peer.env al import
    ├── utils.py                 # log(), run(), rpc() ServerProxy
    ├── identity.py              # peer_id, endpoint guess, owner
    ├── keys.py                  # wg genkey/pubkey 0600
    ├── state.py                 # wg-auto.json load/save
    ├── auth.py                  # JWT session (login/refresh)
    ├── nat.py                   # detección NAT none/full-cone/symmetric
    ├── probe.py                 # handshake-based reachability probe
    ├── config_gen.py            # fetch + render .conf + wg syncconf
    └── commands.py              # cmd_register/heartbeat/run/...
```

### 3.2 Instalación cross-distro (`install.sh`)

- Detecta gestor de paquetes: `apt`/`dnf`/`yum`/`pacman`/`zypper`/`apk` (`install.sh:34-39`).
- Genera wrapper POSIX sh independiente del intérprete Python detectado (`install.sh:158-162`).
- Instala en:
  - `/opt/linkguard-peer/wg-auto-register.py` + `peer_register/`
  - `/usr/local/bin/wg-auto-register` (sh wrapper)
  - `/usr/local/bin/wg-auto-cli`
  - `/etc/linkguard/peer.env` (0600)
  - `/etc/wireguard/wg-auto.json`
- `install.sh:179-187` valida que `ORCH_TOKEN` no esté vacío ni sea el placeholder.
- Soporta systemd (unit regenerado, `install.sh:213-241`) y OpenRC (`install.sh:267-280`).

### 3.3 Bootstrap y entrada (`peer_register/__init__.py`)

**`__init__.py:13-43`**: argparse con subcomandos:
| Subcomando | Handler | Descripción |
|-----------|---------|-------------|
| `register` | `commands.cmd_register` | Registro único |
| `heartbeat` | `commands.cmd_heartbeat` | Heartbeat único |
| `run` | `commands.cmd_run` | Loop demonio |
| `request-network` | `commands.cmd_request_network` | Solicitar red |
| `rotate-key` | `commands.cmd_rotate_key` | Rotar claves WG |

El systemd unit ejecuta `wg-auto-register run` (`systemd/wg-auto-register.service:10`).

### 3.4 Config (`peer_register/config.py`)

Auto-carga de `/etc/linkguard/peer.env` al importar el módulo (`config.py:10-23`). Solo setea keys que no están ya en `os.environ` (para que `Environment=` de systemd tenga prioridad). Variables principales:

| Variable | Default | Propósito |
|----------|---------|-----------|
| `ORCH_URL` | `http://127.0.0.1:8000/RPC2` | Endpoint XML-RPC del orquestador |
| `ORCH_TOKEN` | (requerido) | Token de tenant para `auth.login` |
| `PEER_ID` | hostname | Identificador del peer |
| `USER_ID` / `PEER_OWNER` | `"default"` | Tenant owner para binding JWT |
| `PEER_TAGS` | `""` | Tags separados por coma |
| `PUBLIC_IP` | — | IP pública para detección NAT + endpoint |
| `PEER_ENDPOINT` | auto-detect | Override de endpoint |
| `WG_LISTEN_PORT` | `""` | Fuerza `ListenPort` en `[Interface]` |
| `WG_KEEPALIVE` | `25` | PersistentKeepalive |
| `WG_HEARTBEAT_INTERVAL` | `25` | Intervalo del loop de heartbeat |
| `WG_JWT_SCOPES` | `"peer:*,network:*,config:*,advertise:*,orch:read"` | Scopes del JWT |
| `WG_JWT_TTL` | `600` | TTL del JWT en segundos |

### 3.5 RPC — comunicación con el orquestador

XML-RPC puro vía `xmlrpc.client.ServerProxy(cfg.ORCH_URL, allow_none=True)` (`utils.py:45-46`).

Patrón de invocación (usado en todos los call sites):

```python
from peer_register.utils import rpc
c = rpc()
resp = c.__getattr__("peer.heartbeat")(peer_id, status, token)
#     ^^^^^^^^^^^^^^^^  ^^^^^^^^^^^^^^^^
#     ServerProxy       methodName = "peer.heartbeat"
```

El uso de `__getattr__` es porque `getattr(c, "peer.heartbeat")` no funciona — el nombre del método contiene un punto y debe pasarse como string al methodName del XML-RPC.

**Métodos invocados por el peer:**

| Método | Código | Propósito |
|--------|--------|-----------|
| `peer.register` | `commands.py:35` | Registrarse |
| `peer.heartbeat` | `commands.py:71` | Heartbeat |
| `peer.request_network` | `commands.py:129` | Solicitar red |
| `peer.rotate_key` | `commands.py:144` | Rotar clave pública |
| `peer.report_reachability` | `probe.py:55` | Reportar reachabilidad (hub-mesh) |
| `config.get_peer_config` | `config_gen.py:20` | Obtener configuración |
| `auth.login` | `auth.py:43` | Obtener JWT inicial |
| `auth.refresh` | `auth.py:35` | Refrescar JWT |

### 3.6 Registro (`commands.cmd_register`, `commands.py:21-44`)

```python
gen_keys_if_needed()               # keys.py:13 — idempotente
peer_id = peer_id_default()        # PEER_ID o hostname
pub     = load_public_key()        # keys.py:37
tags    = PEER_TAGS.split(',')     # opcional
endpoint = PEER_ENDPOINT or peer_endpoint_guess()  # identity.py:22-34
c = rpc()
token = orch_token_for_call(peer_id)  # auth.py:50-52
resp = c.peer.register(peer_id, pub, endpoint, tags, metadata, token)
st["peer_id"] = resp["peer_id"]
st["config_version"] = resp["config_version"]
apply_config(peer_id)
wg_show_output = run_wg_show()
```

### 3.7 Loop principal (`commands.cmd_run`, `commands.py:103-120`)

```
while True:
    try:
        if not registered:
            cmd_register(peer_id, force=True)
            registered = True
        cmd_heartbeat(peer_id)
    except Fault as e:
        log.error("Fault en heartbeat: %s", e)
    except Exception as e:
        log.exception("Error en heartbeat")
    time.sleep(interval)  # 25s por defecto
```

- Fail-soft: nunca sale. systemd `Restart=on-failure` como respaldo.
- El registro se intenta una vez al inicio; si falla, se reintenta implícitamente en cada heartbeat porque `heartbeat` también hace `register` si el peer no existe en el orquestador.

### 3.8 Heartbeat (`commands.cmd_heartbeat`, `commands.py:47-100`)

1. **NAT detection** (cache 300s, `commands.py:53-60`): re-ejecuta `detect_nat_type()` solo si el caché expiró. Default: `symmetric`.
2. **Payload status** (`commands.py:62-67`):
   ```python
   status = {
       "ts": now.isoformat(),
       "wg": wg_show_output[:4000],   # snapshot
       "endpoint": current_endpoint,
       "nat_type": st["nat_type"]
   }
   ```
3. **Envía heartbeat** → respuesta del orquestador incluye:
   - `desired_config_version` — para detectar cambios de configuración.
   - `mesh_peers_hash` / `hub_mesh_peers_hash` — para detectar cambios en la lista de peers mesh.
4. **Decisión de re-aplicar config**:
   - Si `desired_config_version != current` → re-aplica (`commands.py:81-83`).
   - Si `mesh_peers_hash` / `hub_mesh_peers_hash` cambió → re-aplica (`commands.py:85-90`, MESH-F3b).
5. **`probe_direct_peers()`**: solo en topología hub-mesh (`commands.py:97-100`).

### 3.9 Gestión de JWT (`peer_register/auth.py`)

**SEC-03** (`auth.py:25-29`): `ORCH_TOKEN` es obligatorio. Vacío → `RuntimeError` con mensaje claro apuntando a `orch-cli issue-user-token`.

**`ensure_jwt_session`** (`auth.py:21-47`):

```python
def ensure_jwt_session(peer_id, st):
    if "jwt" in st and not _jwt_needs_refresh(st):   # exp > now+60s
        return st["jwt"]
    try:
        resp = c.auth.refresh(st["jwt"], WG_JWT_TTL)  # intenta refresh primero
    except Exception:
        resp = c.auth.login(uid, peer_id, ORCH_TOKEN,  # fallback a login
                           WG_JWT_SCOPES, WG_JWT_TTL)
    st["jwt"] = resp["jwt"]
    st["jwt_expires_at"] = time.time() + resp["expires_in"]
    state.save_state(st)  # 0600
    return st["jwt"]
```

- `_jwt_needs_refresh` (`auth.py:14-18`): refresh 60s antes de expirar.
- El JWT se cachea en `wg-auto.json` con permiso 0600.

### 3.10 Detección de NAT (`peer_register/nat.py:16-49`)

Heurística implementada (HM-F4b):

| Condición | Resultado |
|-----------|-----------|
| Sin `PUBLIC_IP` | `symmetric` |
| `PUBLIC_IP` == IP local detectada | `none` (IP pública directa) |
| `WG_LISTEN_PORT` vacío o 0 | `symmetric` |
| Dos sockets UDP al mismo puerto hacia 8.8.8.8:53 y 1.1.1.1:53 muestran mismo puerto externo | `full-cone` |
| Caso contrario | `symmetric` |

El resultado se envía en cada heartbeat y se cachea 5 minutos en `wg-auto.json`.

### 3.11 Generación de configuración WireGuard (`config_gen.py`)

**`apply_config(peer_id)`** (`config_gen.py:121-139`) orquesta todo el proceso:

#### 3.11.1 Fetch (`_fetch_config`, `config_gen.py:17-20`)
```python
resp = c.config.get_peer_config(peer_id, token)
```

#### 3.11.2 Bloque `[Interface]` (`config_gen.py:23-29`)
```
[Interface]
Address = <ip>/32
PrivateKey = <de WG_PRIV_KEY_PATH>
MTU = 1420
ListenPort = <WG_LISTEN_PORT si está seteado y ≠ 0>
```

#### 3.11.3 Bloque HUB `[Peer]` (`config_gen.py:32-41`)
- Hub-mesh: label `# relay de fallback`
- Hub-spoke/mesh: label `# bootstrap`
- Campos: `PublicKey`, `Endpoint`, `AllowedIPs`, `PersistentKeepalive=25`

#### 3.11.4 Topología mesh (`_build_mesh_blocks`, `config_gen.py:44-67`)

Un bloque `[Peer]` por entrada en `mesh_peers[]`:

```
[Peer]
# <peer_id>
PublicKey = <pubkey>
AllowedIPs = <tunnel_ip>/32
Endpoint = <endpoint>   # ← incluido SIEMPRE si presente (fix AGENTS.md)
PersistentKeepalive = 25
```

- Peers `alive=False` también reciben bloque (solo se loggean como "aún sin heartbeat").

#### 3.11.5 Topología hub-mesh (`_build_hub_mesh_blocks`, `config_gen.py:70-93`)

Dos secciones:
- **`hub_mesh_direct_peers`**: bloques completos con `Endpoint` y `/32`, etiquetados `# Directo: <pid>`.
- **`hub_mesh_relay_peers`**: solo comentarios `# Relay-via-HUB: <pid> (nat=..., sin bloque directo)` — el tráfico hacia estos peers va por el hub.

#### 3.11.6 Persistencia de metadatos (`_save_state_metadata`, `config_gen.py:96-105`)

```python
st["topology"] = topology
st["mesh_peers_hash"] = meta.get("mesh_peers_hash", "")
st["hub_mesh_direct_candidates"] = direct_candidates  # para probe.py
state.save_state(st)  # chmod 0600
```

#### 3.11.7 Hot-sync (`_sync_wg`, `config_gen.py:108-118`)

```python
if "wg0" in ip_link_show:
    # Aplicación en caliente con wg-quick strip + wg syncconf
    wg_quick_strip_output = subprocess.run(["wg-quick", "strip", WG_CONF_PATH])
    write(tmpfile, wg_quick_strip_output)
    subprocess.run(["wg", "syncconf", WG_INTERFACE, tmpfile])
else:
    # Primera vez: wg-quick up
    subprocess.run(["wg-quick", "up", WG_INTERFACE])
```

- `wg syncconf` aplica delta sin teardown de la interfaz — crucial para mantener túneles activos durante refrescos de config.

### 3.12 Probe de reachabilidad hub-mesh (`probe.py:15-63`)

Solo se activa en topología `hub-mesh` (HM-F4c/d):

1. Lee `st["hub_mesh_direct_candidates"]` (lista de peers marcados como directos).
2. Parsea `wg show wg0 latest-handshakes` → obtiene timestamp del último handshake por public_key.
3. Para cada candidato: `alive = (0 < now - handshake <= 180)`.
4. Compara con `st["direct_handshake_map"]` previo.
5. **En transición** (cambió de vivo a muerto o viceversa) → llama `peer.report_reachability(peer_id, other_pid, alive, token)` para que el orquestador reclasifique.
6. Persiste el mapa actualizado.

### 3.13 Gestión de claves WireGuard (`keys.py`)

- `gen_keys_if_needed()` (`keys.py:13-21`): idempotente. Ejecuta `wg genkey` → archivo 0600, luego pipea a `wg pubkey` → archivo 0600. Skipea si ambos archivos ya existen.
- `rotate_keys()` (`keys.py:24-34`): regeneración incondicional, devuelve `(priv, pub)`.
- `load_public_key` / `load_private_key`: simplemente leen los archivos cacheados.

### 3.14 CLI local (`wg-auto-cli.py:275-333`)

CLI que se instala en `/usr/local/bin/wg-auto-cli`. Auto-carga `peer.env`, prefiere JWT sobre `ORCH_TOKEN` (`wg-auto-cli.py:50-54`).

Subcomandos:

| Subcomando | RPC / Acción |
|-----------|-------------|
| `unregister` | `peer.unregister(peer_id)` |
| `update <json>` | `peer.update(peer_id, fields)` |
| `list-networks` | `network.list(None, None, token)` |
| `add-to-network <nid> <role> <ip>` | `network.add_peer(...)` (admin-only) |
| `rm-from-network <nid>` | `network.remove_peer(...)` |
| `list-advertised` | `peer.list_advertised_networks(peer_id)` |
| `add-advertised <cidr> <nid> <mode>` | `peer.add_advertised_network(...)` |
| `rm-advertised <adv_id>` | `peer.remove_advertised_network(...)` |
| `topology <nid>` | `network.get_topology(nid, None, token)` |
| `status` | `peer.get_status(peer_id)` |
| `rotate-key` | ejecuta `wg-auto-register rotate-key` |
| `orch-health` | `orch.health()` |
| `mesh-status` | diagnóstico local parseando `.conf` + `wg show` |

**`mesh-status`** (`wg-auto-cli.py:175-273`): diagnóstico puramente local que:
1. Parsea `wg0.conf` extrayendo bloques `[Peer]` y comentarios `# Directo:` / `# Relay-via-HUB:`.
2. Cruza con `wg show wg0 latest-handshakes`.
3. Renderiza tabla con columnas: `PEER`, `ENDPOINT`, `ALLOWED_IPS`, `HS`, `MODO` (DIRECTO/HUB-RELAY).

### 3.15 RPC wrapper defensivo (`wg-auto-cli.py:64-76`)

```python
def rpc_call(method, *args):
    token = get_token()
    c = rpc()
    try:
        return c.__getattr__(method)(*args, token)
    except TypeError as e:
        # Fallback: algunos métodos no aceptan token
        return c.__getattr__(method)(*args)
```

---

## 4. Diagramas de flujo

### 4.1 Registro de un peer

```
PEER                                         ORQUESTRADOR                   HUB-AGENT
 │                                              │                              │
 ├─ auth.login(uid, peer_id, token) ──────────► │                              │
 │◄─ {jwt, expires_in} ──────────────────────── │                              │
 │                                              │                              │
 ├─ peer.register(peer_id, pub, ep, tags, md, jwt) ──►                        │
 │                                              ├─ auto_approve?               │
 │                                              ├─ network_alloc IP           │
 │                                              ├─ bump_config_version        │
 │                                              ├─ hub.apply_peer(pub, ip) ──►│
 │                                              │                         ──► wg set
 │◄─ {peer_id, wg_ip, config_version} ───────── │                              │
 │                                              │                              │
 ├─ config.get_peer_config(peer_id, jwt) ──────►│                              │
 │◄─ {interface, peer, meta, mesh_peers} ────── │                              │
 │                                              │                              │
 ├─ wg syncconf wg0 <nueva_config>             │                              │
 │✓ Interfaz wg0 activa                        │                              │
```

### 4.2 Heartbeat (loop de 25s)

```
PEER                                         ORQUESTRADOR                   HUB-AGENT
 │                                              │                              │
 ├─ detect_nat_type() → symmetric               │                              │
 ├─ wg show wg0 → {handshakes, transfer}        │                              │
 │                                              │                              │
 ├─ peer.heartbeat(pid, {wg, ep, nat}, jwt) ──► │                              │
 │                                              ├─ update last_heartbeat       │
 │                                              ├─ si ep privado: overwrite    │
 │                                              │  con client_address TCP      │
 │                                              ├─ consulta hub.list_mesh ────►│
 │◄─ {desired_cv, mesh_hash, hmb_hash} ──────── │◄─ WG endpoints ─────────────┤
 │                                              │                              │
 ├─ ¿cv != current? o ¿hash != stored?          │                              │
 │  └─ Sí → config.get_peer_config ───────────► │                              │
 │  └─ wg syncconf wg0                          │                              │
 │                                              │                              │
 ├─ ¿hub-mesh? → probe_direct_peers()           │                              │
 │  ├─ wg show wg0 latest-handshakes            │                              │
 │  ├─ ¿transición alive/muerto?                │                              │
 │  ├─ peer.report_reachability ───────────────►│                              │
 │  └─ actualiza direct_handshake_map           │                              │
```

---

## 5. Patrones de diseño importantes

### 5.1 Adapter pattern para XML-RPC legacy
Cada `_xml_*` wrapper en `orchestrator/__init__.py` convierte la convención posicional (peers legacy la usan así) en kwargs canónicos. Ejemplo: `_xml_user_create` (`__init__.py:106-131`) acepta tanto la forma CLI de 2 args como la forma test de 5 args.

### 5.2 Centralized exception-to-Fault mapping
`_safe_call` (`__init__.py:39-49`) significa que los handlers nunca devuelven códigos de error — lanzan excepciones Python que se traducen a Faults con códigos HTTP-style. Contrato uniforme para los peers.

### 5.3 Lock hierarchy
`state.py:14-20` documenta `USERS > NETWORKS > PEERS > EVENTS` como único orden legal de adquisición de locks. La mayoría de handlers adquiere solo un lock a la vez.

### 5.4 Persistencia atómica + backups asíncronos
`save_json` escribe temp + `os.replace` — crash-safe. Backup thread en daemon que poda copias viejas.

### 5.5 Hot-reloadable JWT secret
`_read_jwt_secret` (`auth.py:22-43`) relee `/etc/linkguard/jwt_secret` solo cuando su sha256 cambia.

### 5.6 Config-version-driven reconciliation
Toda mutación de peer llama `state.bump_config_version_locked()`. Heartbeats devuelven `desired_config_version`. Peers solo re-fetchean cuando hay drift.

### 5.7 Topological hash heartbeat contract
Ambos heartbeats (mesh y hub-mesh) devuelven un SHA-256 hash del peer set. Los peers diffen contra su último hash conocido para decidir si re-fetchear. Esto escala a 50+ peers sin traer listas completas en cada heartbeat.

### 5.8 Real-source-IP endpoint rewriting
`_Handler.do_POST` guarda `client_address` en thread-local; `rpc_peer_heartbeat` usa esta IP para sobreescribir endpoints privados con la IP pública real, y cruza contra `hub.list_mesh_peers` para estabilizar el puerto NAT-remapeado.

### 5.9 Dotted XML-RPC dispatch via `__getattr__`
`utils.py:45-46` y todos los call sites: `c.__getattr__("peer.register")(...)` en lugar de `getattr(c, "peer.register")`, porque el name con puntos debe pasarse como string al ServerProxy.

### 5.10 Hot-sync sobre cold restart
`_sync_wg` prefiere `wg-quick strip` + `wg syncconf` (sin teardown de interfaz), cayendo a `wg-quick up` solo cuando la interfaz no existe. Esencial para mantener túneles activos durante refrescos.

### 5.11 Comentarios como metadata en `.conf`
`config_gen.py` escribe `# Directo: <pid>` y `# Relay-via-HUB: <pid>` en `wg0.conf`. El CLI `mesh-status` re-parsea estos comentarios para renderizar sus tablas, haciendo que el `.conf` sea tanto configuración WG como catálogo directo/relay del peer.

---

## 6. Variables de entorno relevantes

### Orquestador (`orchestrator/__init__.py` / `config.py`)
| Variable | Default | Propósito |
|----------|---------|-----------|
| `LISTEN_IP` | `0.0.0.0` | IP de escucha del orquestador |
| `LISTEN_PORT` | `8000` | Puerto XML-RPC |
| `ADMIN_TOKEN` | (requerido) | Token maestro de admin |
| `HUB_AGENT_TOKEN` | (requerido) | Token para comunicación con hub-agent |
| `HUB_AGENT_URL` | `http://127.0.0.1:9000/RPC2` | URL del hub-agent |
| `JWTSECRET_FILE` | `/etc/linkguard/jwt_secret` | Archivo con secreto JWT |
| `HUB_ENDPOINT` | (requerido) | Endpoint público del hub WG |
| `STATE_PATH` | `/var/lib/wg-orchestrator/state.json` | Archivo de estado |
| `AUTO_APPROVE_ENABLED` | `0` | Habilitar auto-registro por tags |
| `AUTO_APPROVE_RULES` | — | Reglas `tag:cidr` separadas por `|` |
| `HUB_MESH_MODE` | `off` | Modo mesh del hub: `off|mesh|hub-mesh` |

### Peer (`peer_register/config.py`)
| Variable | Default | Propósito |
|----------|---------|-----------|
| `ORCH_URL` | `http://127.0.0.1:8000/RPC2` | URL del orquestador |
| `ORCH_TOKEN` | (requerido) | Token de tenant |
| `PEER_ID` | hostname | ID del peer |
| `USER_ID` | `"default"` | Tenant owner |
| `PUBLIC_IP` | — | IP pública del peer |
| `PEER_ENDPOINT` | auto-detect | Override de endpoint |
| `WG_LISTEN_PORT` | — | Puerto de escucha WG |
| `WG_HEARTBEAT_INTERVAL` | `25` | Intervalo de heartbeat |
| `WG_JWT_TTL` | `600` | TTL del JWT |
| `WG_KEEPALIVE` | `25` | PersistentKeepalive |

---

## 7. Resumen de archivos clave

| Archivo | Líneas | Rol |
|---------|--------|-----|
| `orchestrator-install-v2/orchestrator/__init__.py` | 413 | Bootstrap, dispatcher, 31 wrappers RPC |
| `orchestrator-install-v2/orchestrator/endpoints_peers.py` | 522 | Ciclo de vida de peers (register, heartbeat, rotate, unregister) |
| `orchestrator-install-v2/orchestrator/endpoints_config.py` | 200 | Generación de configs por topología |
| `orchestrator-install-v2/orchestrator/auth.py` | 245 | JWT, multi-tenant, quotas, revocación |
| `orchestrator-install-v2/orchestrator/state.py` | 134 | Persistencia JSON, locks, backups |
| `orchestrator-install-v2/hub-agent.py` | 488 | Data-plane WireGuard |
| `orchestrator-install-v2/orch-cli.py` | 327 | CLI del orquestador |
| `peer-install-v2/peer_register/commands.py` | 148 | Comandos del peer (register, heartbeat, run) |
| `peer-install-v2/peer_register/config_gen.py` | 139 | Generación y aplicación de config WG |
| `peer-install-v2/peer_register/auth.py` | 52 | JWT session login/refresh |
| `peer-install-v2/peer_register/nat.py` | 49 | Detección de tipo NAT |
| `peer-install-v2/peer_register/probe.py` | 63 | Reachability probe hub-mesh |
| `peer-install-v2/install.sh` | ~300 | Instalador cross-distro |
