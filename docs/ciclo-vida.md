# Ciclo de Vida: Orchestrator y Peer

Este documento describe el ciclo de vida completo de los componentes principales de LinkGuard.

**Diagramas relacionados:**
- `ciclo-vida-orchestrator.png` — Estados del orchestrator
- `ciclo-vida-peer.png` — Estados del peer
- `secuencia-orchestrator-peer.png` — Interacción completa
- `flujo-rpc-orchestrator.png` — Flujo interno de un RPC

---

## 1. Ciclo de Vida del Orchestrator

### 1.1 Arranque

El orchestrator arranca como servicio systemd (`orchestrator.service`).

```bash
systemctl start orchestrator
```

**Secuencia de inicialización** (`orchestrator/__init__.py:380-413`):

```python
def main() -> None:
    config.check_dependencies()              # 1. Verificar python3
    config.validate_tokens_at_startup()      # 2. Validar ADMIN_TOKEN, HUB_AGENT_TOKEN, HUB_ENDPOINT
    
    state.load_state()                       # 3. Cargar state.json desde disco
    
    from .hub_client import hub_ping
    if hub_ping():                           # 4. Verificar conexión con hub-agent
        config.log("Conexion con hub-agent: OK")
    else:
        config.log("ADVERTENCIA: hub-agent no responde")
    
    state.start_backup_loop()                # 5. Iniciar thread de backup cada 300s
    
    server = _Server(...)                    # 6. Crear servidor XML-RPC
    _register_xml_handlers(server)           # 7. Registrar 31 handlers RPC
    
    config.log(f"Orchestrator listo en {config.ORCH_BIND}:{config.ORCH_PORT}/RPC2")
    server.serve_forever()                   # 8. Servir peticiones
```

**Validaciones críticas:**
- `ADMIN_TOKEN` no vacío ni inseguro (`changeme`, `password`, etc.)
- `HUB_AGENT_TOKEN` no vacío ni inseguro
- `HUB_ENDPOINT` con formato `IP:PUERTO` (ej: `101.44.24.91:51820`)

Si alguna validación falla, el orchestrator termina con código de error.

### 1.2 Estado de Operación

Una vez arrancado, el orchestrator mantiene:

**Estado en memoria:**
```python
# orchestrator/state.py
STATE = {
    "version": 4,
    "config_version": 1,
    "users": {},      # {user_id: {token, max_peers, max_networks, ...}}
    "peers": {},      # {peer_id: {public_key, ip, endpoint, last_heartbeat, ...}}
    "networks": {},   # {net_id: {cidr, topology, alloc, ...}}
    "events": [],     # Lista de eventos recientes
}
```

**Locks granulares** (orden estricto para evitar deadlocks):
```python
LOCK_USERS      # Para operaciones sobre usuarios
LOCK_NETWORKS   # Para operaciones sobre redes
LOCK_PEERS      # Para operaciones sobre peers
LOCK_EVENTS     # Para append de eventos
LOCK_STATE      # Para operaciones globales de estado
```

**Hilos activos:**
1. **Main thread**: Servidor XML-RPC atendiendo peticiones en `:8000/RPC2`
2. **Backup thread**: Cada `BACKUP_INTERVAL_SEC` (300s) hace backup de `state.json`

**31 handlers XML-RPC registrados:**
- `auth.*` — login, refresh, whoami
- `orch.*` — health, metrics, events, user-create, user-list, etc.
- `peer.*` — register, heartbeat, get, list, rotate_key, etc.
- `network.*` — create, list, get, set_topology, etc.
- `config.*` — get_peer_config, get_mesh_peers

### 1.3 Procesamiento de un RPC

Cada petición XML-RPC sigue este flujo (`__init__.py:39-50`):

```
Cliente → POST /RPC2
    ↓
_xml_<cmd> wrapper
    ↓
_safe_call(handler, params)
    ↓
auth: orch_check_admin_token() o _auth_from_token(jwt)
    ↓
handler: endpoints_*.rpc_*(params)
    ↓
state: LOCK_*, mutate STATE, persist()
    ↓
hub_client: _hub_apply_peer_allowed_ips() (si aplica)
    ↓
Response XML-RPC
```

**Ejemplo: peer.register**
```python
def _xml_peer_register(*args) -> dict:
    from .endpoints_peers import rpc_peer_register
    return _safe_call(rpc_peer_register, {
        "peer_id": args[0],
        "public_key": args[1],
        "endpoint": args[2],
        "tags": args[3],
        "metadata": args[4],
        "token": args[5],
    })
```

### 1.4 Persistencia de Estado

**Escritura atómica** (`state.py:41-46`):
```python
def save_json(path: str, data: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    os.replace(tmp, path)  # Atómico en POSIX
```

**Backup automático** (`state.py`):
- Cada 300s copia `state.json` a `backups/state.json.<timestamp>`
- Mantiene máximo `BACKUP_MAX_KEEP` (10) backups

### 1.5 Apagado

```bash
systemctl stop orchestrator
```

**Secuencia de apagado** (`__init__.py:404-409`):
```python
try:
    server.serve_forever()
except KeyboardInterrupt:
    config.log("Apagando...")
    state.persist()              # 1. Guardar estado actual
    server.server_close()        # 2. Cerrar socket
```

El servicio systemd también puede configurarse con `PreStop` para limpieza adicional.

---

## 2. Ciclo de Vida del Peer

El peer corre como servicio systemd (`wg-auto-register.service`) en cada host.

### 2.1 Instalación

```bash
# En el peer host
cd peer-install-v2
sudo bash install.sh
```

**Qué hace install.sh:**
1. Instala dependencias (python3, wireguard-tools, etc.)
2. Crea `/etc/linkguard/peer.env` con configuración
3. Instala `wg-auto-register` en `/usr/local/bin/`
4. Configura servicio systemd

**peer.env** (configuración del peer):
```bash
ORCH_URL=http://101.44.24.91:8000/RPC2
ORCH_TOKEN=u_abc123...  # Token del tenant (obtenido con orch-cli issue-user-token)
WG_INTERFACE=wg0
WG_HEARTBEAT_INTERVAL=25
```

### 2.2 Registro Inicial

```bash
wg-auto-register register
```

**Secuencia** (`peer_register/commands.py:21-44`):

```python
def cmd_register(_args) -> None:
    gen_keys_if_needed()                    # 1. Generar claves WireGuard si no existen
    peer_id = peer_id_default()             # 2. Determinar peer_id (hostname o env)
    pub = load_public_key()                 # 3. Leer clave pública
    
    endpoint = os.getenv("PEER_ENDPOINT", "") or peer_endpoint_guess()
    
    c = rpc()
    token = orch_token_for_call(peer_id)    # 4. Obtener JWT (auth.login)
    resp = c.__getattr__("peer.register")(  # 5. Llamar peer.register
        peer_id, pub, endpoint, tags, metadata, token
    )
    
    st = load_state()
    st["peer_id"] = resp["peer_id"]         # 6. Guardar peer_id en state
    st["config_version"] = resp.get("config_version", 1)
    save_state(st)
    
    apply_config(peer_id)                   # 7. Aplicar configuración WireGuard
    run([cfg.WG_BIN, "show", cfg.WG_INTERFACE], check=False)
```

**Qué pasa en el orchestrator:**
1. Valida JWT del tenant
2. Si peer ya existe → actualiza clave pública y endpoint
3. Si peer no existe → crea nuevo peer, asigna IP, notifica al hub-agent
4. Incrementa `config_version`
5. Retorna `{peer_id, wg_ip, config_version}`

**Configuración WireGuard generada** (`/etc/wireguard/wg0.conf`):
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

**Aplicación de config** (`config_gen.py:108-118`):
```python
def _sync_wg() -> None:
    if interface_exists(WG_INTERFACE):
        # Interface ya existe, usar syncconf (hot-reload)
        strip_out = subprocess.check_output([WG_QUICK, "strip", WG_INTERFACE])
        tmp = tempfile.NamedTemporaryFile(...)
        tmp.write(strip_out)
        subprocess.run([WG_BIN, "syncconf", WG_INTERFACE, tmp.name], check=True)
    else:
        # Interface no existe, crear desde cero
        run([WG_QUICK, "up", WG_INTERFACE], check=True)
```

### 2.3 Daemon Loop (cmd_run)

```bash
wg-auto-register run --interval 25
```

**Bucle principal** (`commands.py:103-120`):

```python
def cmd_run(args) -> None:
    interval = int(getattr(args, "interval", cfg.WG_HEARTBEAT_INTERVAL))
    
    try:
        log("Modo run: ejecutando register")
        cmd_register(args)                  # 1. Registro inicial
    except Exception as e:
        log(f"register fallo (continuaremos reintentando): {e}")
    
    while True:                             # 2. Loop infinito
        try:
            cmd_heartbeat(args)             # 3. Heartbeat cada intervalo
        except Fault as f:
            log(f"heartbeat Fault: {f}")
        except Exception as e:
            log(f"heartbeat error: {e}")
        
        time.sleep(interval)                # 4. Dormir 25s
```

### 2.4 Heartbeat

Cada 25 segundos, el peer envía un heartbeat al orchestrator.

**Secuencia** (`commands.py:47-100`):

```python
def cmd_heartbeat(_args) -> None:
    st = load_state()
    peer_id = st.get("peer_id") or peer_id_default()
    
    detected_endpoint = os.getenv("PEER_ENDPOINT", "") or peer_endpoint_guess()
    
    # 1. Detectar tipo de NAT (cacheado 300s)
    nat_cache_ts = int(st.get("nat_type_detected_ts", 0))
    if int(time.time()) - nat_cache_ts > 300:
        nat_type = detect_nat_type()        # none | full-cone | symmetric
        st["nat_type"] = nat_type
        st["nat_type_detected_ts"] = int(time.time())
        save_state(st)
    else:
        nat_type = st.get("nat_type", "symmetric")
    
    # 2. Construir status
    status = {
        "ts":       int(time.time()),
        "wg":       run([cfg.WG_BIN, "show", cfg.WG_INTERFACE], capture=True)[:4000],
        "endpoint": detected_endpoint,
        "nat_type": nat_type,
    }
    
    # 3. Enviar heartbeat
    c = rpc()
    token = ensure_jwt_session(peer_id, st)  # 4. JWT refresh si necesario
    resp = c.__getattr__("peer.heartbeat")(peer_id, status, token)
    
    # 5. Evaluar si reaplicar config
    desired_version = int(resp.get("desired_config_version", st.get("config_version", 1)))
    current_version = int(st.get("config_version", 1))
    
    need_reapply = False
    
    if desired_version != current_version:
        log(f"Config version cambio {current_version} -> {desired_version}, reaplicando...")
        need_reapply = True
    
    topology = st.get("topology", "hub-spoke")
    
    if not need_reapply and topology in ("mesh", "hub-mesh"):
        new_mp_hash = resp.get("mesh_peers_hash", "") or resp.get("hub_mesh_peers_hash", "")
        if new_mp_hash and new_mp_hash != current_mp_hash:
            log(f"Lista de peers {topology} cambio, reaplicando...")
            need_reapply = True
    
    if need_reapply:
        apply_config(peer_id)                # 6. Regenerar wg0.conf y syncconf
        st = load_state()
        st["config_version"] = desired_version
        save_state(st)
    
    # 7. En hub-mesh, probar reachability directa
    if topology == "hub-mesh":
        st = load_state()
        probe_direct_peers(peer_id, st)
        save_state(st)
```

**Qué hace el orchestrator al recibir heartbeat:**
1. Actualiza `last_heartbeat = now`
2. Actualiza `endpoint` (con override de `remote_addr` si el auto-reportado es privado)
3. Actualiza `nat_type`
4. Si endpoint cambió → notifica al hub-agent
5. Retorna `{desired_config_version, mesh_peers_hash}`

### 2.5 Sesión JWT

El peer usa JWT para autenticarse con el orchestrator.

**Flujo** (`peer_register/auth.py:21-47`):

```python
def ensure_jwt_session(peer_id: str, st: dict) -> str:
    if "jwt" in st and not _jwt_needs_refresh(st):
        return st["jwt"]                     # 1. Usar JWT cacheado
    
    if not cfg.ORCH_TOKEN:
        raise RuntimeError("ORCH_TOKEN esta vacio")
    
    c = rpc()
    uid = owner_default()
    
    if "jwt" in st and _jwt_needs_refresh(st):
        try:
            resp = c.__getattr__("auth.refresh")(st["jwt"], cfg.JWT_TTL)
            st["jwt"] = resp["jwt"]          # 2. Refresh JWT
            st["jwt_expires_at"] = int(resp["expires_at"])
            save_state(st)
            return st["jwt"]
        except Exception as e:
            log(f"JWT refresh fallo, re-login: {e}")
    
    # 3. Login completo
    resp = c.__getattr__("auth.login")(uid, peer_id, cfg.ORCH_TOKEN, cfg.JWT_SCOPES, cfg.JWT_TTL)
    st["jwt"] = resp["jwt"]
    st["jwt_expires_at"] = int(resp["expires_at"])
    save_state(st)
    return st["jwt"]

def _jwt_needs_refresh(st: dict) -> bool:
    exp = int(st.get("jwt_expires_at") or 0)
    if not exp:
        return True
    return int(time.time()) >= (exp - 60)    # Refresh 60s antes de expirar
```

**JWT_TTL**: 600s (10 minutos) por defecto

### 2.6 Rotación de Clave

```bash
wg-auto-register rotate-key
```

**Secuencia** (`commands.py:136-148`):

```python
def cmd_rotate_key(_args) -> None:
    st = load_state()
    peer_id = st.get("peer_id") or peer_id_default()
    
    priv, pub = rotate_keys()                # 1. Generar nuevas claves
    
    c = rpc()
    token = ensure_jwt_session(peer_id, st)
    resp = c.__getattr__("peer.rotate_key")(peer_id, pub, token)
    
    apply_config(peer_id)                    # 2. Aplicar config con nueva clave
    run([cfg.WG_BIN, "show", cfg.WG_INTERFACE], check=False)
```

**Qué hace el orchestrator:**
1. Actualiza `public_key` del peer
2. Incrementa `config_version`
3. Notifica al hub-agent para actualizar `allowed-ips`

### 2.7 Solicitar Red Adicional

```bash
wg-auto-register request-network <network_id> --apply
```

**Secuencia** (`commands.py:123-133`):

```python
def cmd_request_network(args) -> None:
    st = load_state()
    peer_id = st.get("peer_id") or peer_id_default()
    net = args.network_id
    
    c = rpc()
    token = ensure_jwt_session(peer_id, st)
    resp = c.__getattr__("peer.request_network")(peer_id, net, token)
    
    if args.apply:
        apply_config(peer_id)                # Regenerar config con nueva red
        run([cfg.WG_BIN, "show", cfg.WG_INTERFACE], check=False)
```

### 2.8 Desregistro

```bash
wg-auto-register unregister
```

**Qué hace:**
1. Llama `peer.unregister(peer_id, jwt)` al orchestrator
2. Orchestrator elimina peer de `STATE["peers"]`
3. Notifica al hub-agent para remover `allowed-ips`
4. Peer puede opcionalmente eliminar archivos locales:
   ```bash
   rm -f /etc/wireguard/wg0.conf /etc/wireguard/wg-auto.json
   ```

### 2.9 Apagado

```bash
systemctl stop wg-auto-register
```

El daemon termina, pero la interfaz `wg0` permanece activa con la última configuración.

Para apagar completamente:
```bash
systemctl stop wg-auto-register
wg-quick down wg0
```

---

## 3. Interacción Orchestrator ↔ Peer

### 3.1 Secuencia Completa de Registro

```
Peer                                    Orchestrator                         Hub Agent
 │                                         │                                    │
 │  1. gen_keys_if_needed()                │                                    │
 │                                         │                                    │
 │  2. auth.login(user_id, peer_id, token) │                                    │
 │────────────────────────────────────────>│                                    │
 │                                         │  validar user_token                │
 │                                         │  generar JWT                       │
 │  {jwt, expires_at}                      │                                    │
 │<────────────────────────────────────────│                                    │
 │                                         │                                    │
 │  3. peer.register(peer_id, pub, ep)     │                                    │
 │────────────────────────────────────────>│                                    │
 │                                         │  4. validar JWT                    │
 │                                         │  5. ¿peer existe?                  │
 │                                         │     Sí: actualizar pub_key         │
 │                                         │     No: crear peer, asignar IP     │
 │                                         │  6. bump_config_version            │
 │                                         │  7. persist STATE                  │
 │                                         │                                    │
 │                                         │  8. _hub_apply_peer_allowed_ips    │
 │                                         │───────────────────────────────────>│
 │                                         │                                    │  9. wg set wg-HUB
 │                                         │                                    │     peer <pub>
 │                                         │                                    │     allowed-ips <ip>/32
 │                                         │  ok                                │
 │                                         │<───────────────────────────────────│
 │                                         │                                    │
 │  {peer_id, wg_ip, config_version}       │                                    │
 │<────────────────────────────────────────│                                    │
 │                                         │                                    │
 │  10. apply_config()                     │                                    │
 │      fetch config.get_peer_config       │                                    │
 │      generar wg0.conf                   │                                    │
 │      wg syncconf wg0                    │                                    │
```

### 3.2 Secuencia de Heartbeat

```
Peer                                    Orchestrator                         Hub Agent
 │                                         │                                    │
 │  1. ensure_jwt_session()                │                                    │
 │     (refresh si expira en <60s)         │                                    │
 │                                         │                                    │
 │  2. detect_nat_type()                   │                                    │
 │     (cacheado 300s)                     │                                    │
 │                                         │                                    │
 │  3. peer.heartbeat(peer_id, status)     │                                    │
 │────────────────────────────────────────>│                                    │
 │                                         │  4. validar JWT                    │
 │                                         │  5. last_heartbeat = now           │
 │                                         │  6. endpoint = remote_addr_override│
 │                                         │  7. nat_type = status.nat_type     │
 │                                         │  8. persist STATE                  │
 │                                         │                                    │
 │                                         │  9. ¿endpoint cambió?              │
 │                                         │     Sí: _hub_apply_peer_allowed_ips│
 │                                         │───────────────────────────────────>│
 │                                         │                                    │  10. wg set wg-HUB
 │                                         │                                    │      endpoint <new_ep>
 │                                         │  ok                                │
 │                                         │<───────────────────────────────────│
 │                                         │                                    │
 │  {desired_config_version, mesh_hash}    │                                    │
 │<────────────────────────────────────────│                                    │
 │                                         │                                    │
 │  11. ¿desired != current?               │                                    │
 │      Sí: apply_config()                 │                                    │
 │                                         │                                    │
 │  12. ¿topology == "hub-mesh"?           │                                    │
 │      Sí: probe_direct_peers()           │                                    │
 │          peer.report_reachability()     │                                    │
```

### 3.3 Eventos que Incrementan config_version

Cuando `config_version` cambia, todos los peers reaplican su configuración en el próximo heartbeat.

**Eventos:**
- `peer.register` (re-entry con nueva clave pública)
- `peer.rotate_key`
- `peer.update_admin` (cambio de metadata por admin)
- `peer.set_networks` (asignación de redes)
- `network.set_topology` (cambio de topología)
- `network.create` (cuando se asigna un peer)

---

## 4. Estados del Peer (Vista del Orchestrator)

El orchestrator mantiene el estado de cada peer en `STATE["peers"]`:

```python
{
    "peer_id": "peer_a",
    "public_key": "abc123...",
    "ip": "10.20.30.2",
    "networks": ["default"],
    "user_id": "tenant-a",
    "endpoint": "46.250.168.185:51820",
    "nat_type": "none",
    "last_heartbeat": 1703635200,
    "enabled": True,
    "metadata": {"owner": "admin"},
    "created_ts": 1703630000,
    "keepalive": 25,
    "status": {...},  # Último status reportado
    "reachability_map": {},  # Para hub-mesh
}
```

**Estados posibles:**

| Estado | Condición | Descripción |
|--------|-----------|-------------|
| **Creado** | Recién registrado | Peer existe pero no ha hecho heartbeat |
| **Activo** | `enabled=True` | Peer habilitado para comunicarse |
| **Vivo** | `last_heartbeat` dentro de 180s | Peer responde heartbeats |
| **Stale** | `last_heartbeat` > 180s | Peer no responde, marcado como `alive=False` en mesh |
| **Deshabilitado** | `enabled=False` | Peer bloqueado por admin |
| **Eliminado** | Removido de STATE | Peer desregistrado |

**Transiciones:**
```
[*] → Creado (peer.register)
Creado → Activo (primer heartbeat)
Activo → Vivo (heartbeat dentro de TTL)
Vivo → Vivo (heartbeat continuo)
Vivo → Stale (sin heartbeat > 180s)
Stale → Vivo (heartbeat llega tarde)
Stale → Eliminado (nunca vuelve)
Activo → Deshabilitado (rpc_peer_disable)
Deshabilitado → Activo (rpc_peer_enable)
Vivo → Rotado (peer.rotate_key)
Rotado → Vivo (config_version bumped)
Activo → Eliminado (peer.unregister)
```

---

## 5. Diagnóstico

### 5.1 Estado del Orchestrator

```bash
# En orchestrator host
systemctl status orchestrator
journalctl -u orchestrator -f

# Verificar salud
orch-cli health

# Ver peers
orch-cli peer-list --admin-token "$ADMIN_TOKEN"

# Ver eventos recientes
orch-cli events --admin-token "$ADMIN_TOKEN"
```

### 5.2 Estado del Peer

```bash
# En peer host
systemctl status wg-auto-register
journalctl -u wg-auto-register -f

# Ver estado de malla
wg-auto-cli mesh-status

# Ver interfaz WireGuard
wg show wg0
ip -4 addr show dev wg0

# Ver configuración
cat /etc/wireguard/wg0.conf

# Ver estado local
cat /etc/wireguard/wg-auto.json | jq
```

### 5.3 Logs Clave

**Orchestrator:**
```
[orchestrator] 2024-01-15T10:23:45 INFO Peer creado: peer_a
[orchestrator] 2024-01-15T10:23:45 INFO peer.register: peer_a user=tenant-a existing=False
[orchestrator] 2024-01-15T10:24:10 INFO peer.heartbeat: peer_a ts=1703635450
```

**Peer:**
```
[peer] 2024-01-15T10:23:45 INFO Conectando a orchestrator en http://101.44.24.91:8000/RPC2
[peer] 2024-01-15T10:23:45 INFO peer.register -> {'peer_id': 'peer_a', 'wg_ip': '10.20.30.2/32', 'config_version': 1}
[peer] 2024-01-15T10:24:10 INFO peer.heartbeat -> {'heartbeat_ack': True, 'desired_config_version': 1}
[peer] 2024-01-15T10:25:00 INFO Config version cambio 1 -> 2, reaplicando...
[peer] 2024-01-15T10:25:00 INFO Topologia mesh: generando 3 bloques [Peer] adicionales
```

---

## 6. Referencias

**Diagramas:**
- `ciclo-vida-orchestrator.png`
- `ciclo-vida-peer.png`
- `secuencia-orchestrator-peer.png`
- `flujo-rpc-orchestrator.png`
- `sesion-jwt-peer.png`
- `estados-peer-orchestrator.png`
- `config-version-bumps.png`

**Código:**
- `orchestrator-install-v2/orchestrator/__init__.py` — Main loop y handlers RPC
- `orchestrator-install-v2/orchestrator/state.py` — Persistencia de estado
- `orchestrator-install-v2/orchestrator/endpoints_peers.py` — Lógica de peers
- `peer-install-v2/peer_register/commands.py` — Comandos CLI del peer
- `peer-install-v2/peer_register/auth.py` — Gestión de JWT
- `peer-install-v2/peer_register/config_gen.py` — Generación de wg0.conf

**Documentación relacionada:**
- `topologias-soportadas.md` — Topologías hub-spoke, mesh, hub-mesh
- `explicacion-topologias-linkguard.md` — Explicación conceptual
- `topologias-linkguard.md` — Guía de pruebas
