# LinkGuard v4 — Implementación del agente peer (wg-auto-register)

## Arquitectura general

El agente peer es un **demonio Python** que se ejecuta en cada nodo participante de la red WireGuard. Se comunica con el orquestador central vía XML-RPC para registrarse, autenticarse, obtener configuración y reportar su estado periódicamente.

```
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
│              │                                                   │
│              ▼ XML-RPC                                           │
│         ORQUESTRADOR (puerto 8000 /RPC2)                        │
└──────────────────────────────────────────────────────────────────┘
```

---

## 1. Estructura de directorios

```
peer-install-v2/
├── wg-auto-register.py          # shim: from peer_register import main; main()
├── wg-auto-cli.py               # CLI local (/usr/local/bin/wg-auto-cli)
├── install.sh / uninstall.sh    # instalación cross-distro
├── peer.env.example             # template (chmod 600)
├── systemd/
│   └── wg-auto-register.service
└── peer_register/               # PAQUETE PRINCIPAL
    ├── __init__.py              # argparse dispatch (register/heartbeat/run/...)
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

---

## 2. Instalación cross-distro (`install.sh`)

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

---

## 3. Bootstrap y entrada (`peer_register/__init__.py`)

**`__init__.py:13-43`**: argparse con subcomandos:

| Subcomando | Handler | Descripción |
|-----------|---------|-------------|
| `register` | `commands.cmd_register` | Registro único |
| `heartbeat` | `commands.cmd_heartbeat` | Heartbeat único |
| `run` | `commands.cmd_run` | Loop demonio |
| `request-network` | `commands.cmd_request_network` | Solicitar red |
| `rotate-key` | `commands.cmd_rotate_key` | Rotar claves WG |

El systemd unit ejecuta `wg-auto-register run` (`systemd/wg-auto-register.service:10`).

---

## 4. Config (`peer_register/config.py`)

Auto-carga de `/etc/linkguard/peer.env` al importar el módulo (`config.py:10-23`). Solo setea keys que no están ya en `os.environ` (para que `Environment=` de systemd tenga prioridad).

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

---

## 5. RPC — comunicación con el orquestador

XML-RPC puro vía `xmlrpc.client.ServerProxy(cfg.ORCH_URL, allow_none=True)` (`utils.py:45-46`).

Patrón de invocación:

```python
from peer_register.utils import rpc
c = rpc()
resp = c.__getattr__("peer.heartbeat")(peer_id, status, token)
#     ^^^^^^^^^^^^^^^^  ^^^^^^^^^^^^^^^^
#     ServerProxy       methodName = "peer.heartbeat"
```

El uso de `__getattr__` es porque `getattr(c, "peer.heartbeat")` no funciona — el nombre del método contiene un punto y debe pasarse como string al methodName del XML-RPC.

### Métodos invocados por el peer

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

---

## 6. Registro (`commands.cmd_register`, `commands.py:21-44`)

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

---

## 7. Loop principal (`commands.cmd_run`, `commands.py:103-120`)

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

- **Fail-soft**: nunca sale. systemd `Restart=on-failure` como respaldo.
- El registro se intenta una vez al inicio; si falla, se reintenta implícitamente en cada heartbeat porque el orquestador acepta heartbeats de peers no registrados (los crea on-the-fly si `auto_approve` está habilitado).

---

## 8. Heartbeat (`commands.cmd_heartbeat`, `commands.py:47-100`)

1. **NAT detection** (cache 300s, `commands.py:53-60`): re-ejecuta `detect_nat_type()` solo si el caché expiró. Default: `symmetric`.
2. **Payload status** (`commands.py:62-67`):
   ```python
   status = {
       "ts": now.isoformat(),
       "wg": wg_show_output[:4000],   # snapshot del estado WG
       "endpoint": current_endpoint,
       "nat_type": st["nat_type"]
   }
   ```
3. **Envía heartbeat** → respuesta del orquestador incluye:
   - `desired_config_version` — para detectar cambios de configuración.
   - `mesh_peers_hash` / `hub_mesh_peers_hash` — para detectar cambios en la lista de peers mesh.
4. **Decisión de re-aplicar config**:
   - Si `desired_config_version != current` → re-aplica (`commands.py:81-83`).
   - Si `mesh_peers_hash` / `hub_mesh_peers_hash` cambió → re-aplica (`commands.py:85-90`).
5. **`probe_direct_peers()`**: solo en topología hub-mesh (`commands.py:97-100`).

---

## 9. Gestión de JWT (`peer_register/auth.py`)

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
- Scopes default: `peer:*,network:*,config:*,advertise:*,orch:read`.
- TTL default: 600 segundos.

---

## 10. Detección de NAT (`peer_register/nat.py:16-49`)

Heurística implementada:

| Condición | Resultado |
|-----------|-----------|
| Sin `PUBLIC_IP` | `symmetric` |
| `PUBLIC_IP` == IP local detectada | `none` (IP pública directa) |
| `WG_LISTEN_PORT` vacío o 0 | `symmetric` |
| Dos sockets UDP al mismo puerto hacia 8.8.8.8:53 y 1.1.1.1:53 muestran mismo puerto externo | `full-cone` |
| Caso contrario | `symmetric` |

El resultado se envía en cada heartbeat y se cachea 5 minutos en `wg-auto.json`.

---

## 11. Generación de configuración WireGuard (`config_gen.py`)

**`apply_config(peer_id)`** (`config_gen.py:121-139`) orquesta todo el proceso de fetch, render y aplicación.

### 11.1 Fetch (`_fetch_config`, `config_gen.py:17-20`)

```python
resp = c.config.get_peer_config(peer_id, token)
```

La respuesta del orquestador es un blob JSON con esta estructura:

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

### 11.2 Bloque `[Interface]` (`config_gen.py:23-29`)

```
[Interface]
Address = <ip>/32
PrivateKey = <de WG_PRIV_KEY_PATH>
MTU = 1420
ListenPort = <WG_LISTEN_PORT si está seteado y ≠ 0>
```

### 11.3 Bloque HUB `[Peer]` (`config_gen.py:32-41`)

- Hub-mesh: label `# relay de fallback`
- Hub-spoke/mesh: label `# bootstrap`
- Campos: `PublicKey`, `Endpoint`, `AllowedIPs`, `PersistentKeepalive=25`

### 11.4 Topología mesh (`_build_mesh_blocks`, `config_gen.py:44-67`)

Un bloque `[Peer]` por entrada en `mesh_peers[]`:

```
[Peer]
# <peer_id>
PublicKey = <pubkey>
AllowedIPs = <tunnel_ip>/32
Endpoint = <endpoint>   # ← incluido SIEMPRE si presente (fix AGENTS.md que resolvió mesh 0/7)
PersistentKeepalive = 25
```

- Peers `alive=False` también reciben bloque (solo se loggean como "aún sin heartbeat").

### 11.5 Topología hub-mesh (`_build_hub_mesh_blocks`, `config_gen.py:70-93`)

Dos secciones:
- **`hub_mesh_direct_peers`**: bloques completos con `Endpoint` y `/32`, etiquetados `# Directo: <pid>`.
- **`hub_mesh_relay_peers`**: solo comentarios `# Relay-via-HUB: <pid> (nat=..., sin bloque directo)` — el tráfico hacia estos peers va por el hub.

### 11.6 Persistencia de metadatos (`_save_state_metadata`, `config_gen.py:96-105`)

```python
st["topology"] = topology
st["mesh_peers_hash"] = meta.get("mesh_peers_hash", "")
st["hub_mesh_direct_candidates"] = direct_candidates  # para probe.py
state.save_state(st)  # chmod 0600
```

### 11.7 Hot-sync (`_sync_wg`, `config_gen.py:108-118`)

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

---

## 12. Probe de reachabilidad hub-mesh (`probe.py:15-63`)

Solo se activa en topología `hub-mesh`:

1. Lee `st["hub_mesh_direct_candidates"]` (lista de peers marcados como directos).
2. Parsea `wg show wg0 latest-handshakes` → obtiene timestamp del último handshake por public_key.
3. Para cada candidato: `alive = (0 < now - handshake <= 180)`.
4. Compara con `st["direct_handshake_map"]` previo.
5. **En transición** (cambió de vivo a muerto o viceversa) → llama `peer.report_reachability(peer_id, other_pid, alive, token)` para que el orquestador reclasifique.
6. Persiste el mapa actualizado.

---

## 13. Gestión de claves WireGuard (`keys.py`)

- `gen_keys_if_needed()` (`keys.py:13-21`): idempotente. Ejecuta `wg genkey` → archivo 0600, luego pipea a `wg pubkey` → archivo 0600. Skipea si ambos archivos ya existen.
- `rotate_keys()` (`keys.py:24-34`): regeneración incondicional, devuelve `(priv, pub)`.
- `load_public_key` / `load_private_key`: simplemente leen los archivos cacheados.

---

## 14. Estado persistente (`state.py`)

Archivo JSON en `/etc/wireguard/wg-auto.json` (chmod 600). Contenido:

```python
{
    "peer_id": "peer01",
    "config_version": 42,
    "topology": "mesh",
    "mesh_peers_hash": "sha256...",
    "hub_mesh_direct_candidates": [...],
    "direct_handshake_map": {...},
    "nat_type": "symmetric",
    "nat_type_detected_ts": 1234567890.0,
    "jwt": "eyJ...",
    "jwt_expires_at": 1234567890.0
}
```

Cada operación (register, heartbeat, apply_config) reload y re-save este archivo.

---

## 15. CLI local (`wg-auto-cli.py:275-333`)

CLI que se instala en `/usr/local/bin/wg-auto-cli`. Auto-carga `peer.env`, prefiere JWT sobre `ORCH_TOKEN` (`wg-auto-cli.py:50-54`).

### Subcomandos

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

### `mesh-status` (`wg-auto-cli.py:175-273`)

Diagnóstico puramente local que:
1. Parsea `wg0.conf` extrayendo bloques `[Peer]` y comentarios `# Directo:` / `# Relay-via-HUB:`.
2. Cruza con `wg show wg0 latest-handshakes`.
3. Renderiza tabla con columnas: `PEER`, `ENDPOINT`, `ALLOWED_IPS`, `HS`, `MODO` (DIRECTO/HUB-RELAY).

### RPC wrapper defensivo (`wg-auto-cli.py:64-76`)

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

## 16. Diagramas de flujo

### 16.1 Registro de un peer

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

### 16.2 Heartbeat (loop de 25s)

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

## 17. Patrones de diseño importantes

### Adapter pattern para XML-RPC legacy
Cada `_xml_*` wrapper en el orquestador (`orchestrator/__init__.py`) convierte la convención posicional (peers la usan así) en kwargs canónicos.

### Dotted XML-RPC dispatch via `__getattr__`
`utils.py:45-46` y todos los call sites: `c.__getattr__("peer.register")(...)` en lugar de `getattr(c, "peer.register")`, porque el name con puntos debe pasarse como string al ServerProxy.

### Config-version-driven reconciliation
Cada heartbeat devuelve `desired_config_version`. El peer solo re-fetchea y re-aplica configuración cuando hay drift.

### Topological hash heartbeat contract
Los heartbeats devuelven un SHA-256 hash del peer set. El peer diffea contra su último hash conocido para decidir si re-fetchear. Escala a 50+ peers sin traer listas completas en cada heartbeat.

### Hot-sync sobre cold restart
`_sync_wg` prefiere `wg-quick strip` + `wg syncconf` (sin teardown de interfaz), cayendo a `wg-quick up` solo cuando la interfaz no existe. Esencial para mantener túneles activos durante refrescos.

### Comentarios como metadata en `.conf`
`config_gen.py` escribe `# Directo: <pid>` y `# Relay-via-HUB: <pid>` en `wg0.conf`. El CLI `mesh-status` re-parsea estos comentarios para renderizar sus tablas, haciendo que el `.conf` sea tanto configuración WG como catálogo directo/relay del peer.

### JWT lifecycle con fallback
`ensure_jwt_session` intenta `auth.refresh` primero (renovación sin enviar el token maestro), y degrada a `auth.login` (con `ORCH_TOKEN`) solo si el refresh falla.

### Fail-soft daemon loop
El loop principal atrapa `Fault` separadamente de `Exception`, loggea ambos, y nunca sale. systemd `Restart=on-failure` como respaldo adicional.

---

## 18. Resumen de archivos clave

| Archivo | Líneas | Rol |
|---------|--------|-----|
| `peer-install-v2/wg-auto-register.py` | 17 | Shim → `peer_register.main()` |
| `peer-install-v2/wg-auto-cli.py` | ~330 | CLI local del peer |
| `peer-install-v2/peer_register/__init__.py` | 43 | argparse dispatch |
| `peer-install-v2/peer_register/config.py` | 43 | Carga de peer.env |
| `peer-install-v2/peer_register/utils.py` | ~50 | ServerProxy, helpers |
| `peer-install-v2/peer_register/identity.py` | ~47 | peer_id, endpoint, owner |
| `peer-install-v2/peer_register/keys.py` | 42 | wg genkey/pubkey |
| `peer-install-v2/peer_register/state.py` | 24 | wg-auto.json load/save |
| `peer-install-v2/peer_register/auth.py` | 52 | JWT login/refresh |
| `peer-install-v2/peer_register/nat.py` | 49 | Detección de tipo NAT |
| `peer-install-v2/peer_register/probe.py` | 63 | Reachability probe hub-mesh |
| `peer-install-v2/peer_register/config_gen.py` | 139 | Fetch + render + wg syncconf |
| `peer-install-v2/peer_register/commands.py` | 148 | register/heartbeat/run |
| `peer-install-v2/install.sh` | ~300 | Instalador cross-distro |
