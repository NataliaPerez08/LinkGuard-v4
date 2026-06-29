# Modelo de Seguridad y Autenticación

Este documento describe el modelo de seguridad de LinkGuard, incluyendo autenticación, autorización, gestión de secretos y aislamiento multi-tenant.

**Diagramas relacionados:**
- `multi-tenant-auth.png` — Flujo de autenticación multi-tenant
- `single-tenant-auth.png` — Flujo de autenticación single-tenant (un solo tenant)

---

## 1. Resumen del Modelo

LinkGuard implementa un modelo de seguridad basado en:

| Componente | Mecanismo | Propósito |
|------------|-----------|-----------|
| **ADMIN_TOKEN** | Token estático (hex 32 bytes) | Operaciones administrativas globales |
| **ORCH_TOKEN** | Token de usuario (prefijo `u_` + hex 16 bytes) | Autenticación inicial de tenants |
| **JWT** | JSON Web Token (HS256) | Sesiones de corta duración para peers |
| **HUB_AGENT_TOKEN** | Token estático (hex 32 bytes) | Comunicación orchestrator ↔ hub-agent |
| **JWT Secret** | Clave secreta (hex 64 bytes) | Firma y validación de JWTs |

---

## 2. Tokens Estáticos

### 2.1 ADMIN_TOKEN

**Propósito**: Autorizar operaciones administrativas globales.

**Generación** (`install.sh:178-189`):
```bash
if [[ ! -f "$SECRETS_FILE" ]]; then
  ADMIN_TOKEN=$(openssl rand -hex 32)
  ORCH_TOKEN=$(openssl rand -hex 32)
  HUB_AGENT_TOKEN=$(openssl rand -hex 32)
  cat > "$SECRETS_FILE" <<EOF
ADMIN_TOKEN=${ADMIN_TOKEN}
ORCH_TOKEN=${ORCH_TOKEN}
HUB_AGENT_TOKEN=${HUB_AGENT_TOKEN}
EOF
  chmod 600 "$SECRETS_FILE"
fi
```

**Almacenamiento**: `/etc/linkguard/secrets` (permisos 600, solo root)

**Validación** (`auth.py:135-141`):
```python
def orch_check_admin_token(token: Optional[str]) -> None:
    if not config.ADMIN_TOKEN:
        raise PermissionError("admin token not configured")
    if not token:
        raise PermissionError("admin token required")
    if token != config.ADMIN_TOKEN:
        raise PermissionError("invalid admin token")
```

**Operaciones que requieren ADMIN_TOKEN**:
- `orch.user-create` — Crear usuarios/tenants
- `orch.user-delete` — Eliminar usuarios
- `orch.issue-user-token` — Emitir tokens de usuario
- `network.create` — Crear redes
- `network.delete` — Eliminar redes
- `network.set_topology` — Cambiar topología
- `peer.update_admin` — Actualizar metadata de peers
- `peer.unregister` — Desregistrar peers (admin o propietario)
- `orch.revoke` — Revocar JWTs

**Uso desde CLI**:
```bash
source /etc/linkguard/secrets
orch-cli user-create tenant-a --admin-token "$ADMIN_TOKEN"
orch-cli peer-list --admin-token "$ADMIN_TOKEN"
```

### 2.2 ORCH_TOKEN (User Token)

**Propósito**: Token de larga duración para que un tenant obtenga JWTs.

**Formato**: `u_` + 16 bytes hex (ej: `u_abc123def456...`)

**Generación** (`auth.py:200-209`):
```python
def _issue_user_token(user_id: str) -> str:
    tok = "u_" + secrets.token_hex(16)
    with state.LOCK_USERS:
        users = state.STATE.get("users") or {}
        u = users.get(user_id) or {"created_ts": state.now_ts(), "disabled": False}
        u["token"] = tok
        users[user_id] = u
        state.STATE["users"] = users
    return tok
```

**Almacenamiento**: En `STATE["users"][user_id]["token"]` (persistido en `state.json`)

**Validación** (`auth.py:212-217`):
```python
def _check_user_token(user_id: str, token: str) -> None:
    u = _get_user(user_id)
    if u.get("disabled"):
        raise PermissionError("user disabled")
    if str(u.get("token") or "") != str(token):
        raise PermissionError("invalid user token")
```

**Uso**: El peer usa ORCH_TOKEN para hacer `auth.login` y obtener un JWT.

### 2.3 HUB_AGENT_TOKEN

**Propósito**: Autenticar comunicación entre orchestrator y hub-agent.

**Validación en hub-agent** (`hub-agent.py:296-298`):
```python
def check_token(token: str) -> None:
    if not secrets.compare_digest(token, HUB_AGENT_TOKEN):
        raise PermissionError("invalid token")
```

**Nota**: Usa `secrets.compare_digest` para prevenir timing attacks.

**Uso**: El orchestrator envía este token en cada llamada RPC al hub-agent.

---

## 3. JWT (JSON Web Tokens)

### 3.1 Estructura del JWT

**Payload** (`auth.py:46-59`):
```python
def _jwt_encode(payload: Dict[str, Any], ttl_seconds: int) -> Tuple[str, int]:
    ttl = int(ttl_seconds) if ttl_seconds else config.JWT_TTL_DEFAULT
    n = state.now_ts()
    exp = n + ttl
    full = dict(payload)
    full.update({
        "iss": config.JWT_ISSUER,        # "linkguard-orchestrator"
        "aud": config.JWT_AUDIENCE,      # "linkguard"
        "iat": n,                         # Issued at
        "nbf": n,                         # Not before
        "exp": exp,                       # Expiration
        "jti": secrets.token_hex(12),    # Unique ID (para revocación)
        # Campos personalizados:
        "user_id": "...",
        "peer_id": "...",
        "scopes": ["peer:*", "network:*", ...],
        "role": "user" | "admin",
    })
    token = pyjwt.encode(full, _read_jwt_secret(), algorithm="HS256")
    return token, exp
```

**Ejemplo de payload decodificado**:
```json
{
  "iss": "linkguard-orchestrator",
  "aud": "linkguard",
  "iat": 1703635200,
  "nbf": 1703635200,
  "exp": 1703635800,
  "jti": "a1b2c3d4e5f6",
  "user_id": "tenant-a",
  "peer_id": "peer_a1",
  "scopes": ["peer:*", "network:*", "config:*", "orch:read"],
  "role": "user"
}
```

### 3.2 JWT Secret

**Almacenamiento**: `/etc/linkguard/jwt_secret` (permisos 600)

**Generación** (`install.sh:196-200`):
```bash
if [[ ! -f "$JWT_SECRET_FILE" ]]; then
  openssl rand -hex 64 > "$JWT_SECRET_FILE"
  chmod 600 "$JWT_SECRET_FILE"
fi
```

**Recarga dinámica** (`auth.py:22-43`):
```python
def _read_jwt_secret() -> str:
    global _JWT_SECRET_HASH, _JWT_SECRET_VALUE
    with open(config.JWT_SECRET_PATH, "r") as f:
        s = f.read().strip()
    file_hash = hashlib.sha256(s.encode()).hexdigest()
    with _JWT_SECRET_LOCK:
        if file_hash != _JWT_SECRET_HASH:
            _JWT_SECRET_HASH = file_hash
            _JWT_SECRET_VALUE = s
            config.log("JWT secret recargado (hash cambio)")
        return _JWT_SECRET_VALUE
```

**Ventaja**: Se puede rotar el JWT secret sin reiniciar el orchestrator.

### 3.3 Validación de JWT

**Decodificación** (`auth.py:62-67`):
```python
def _jwt_decode(token: str) -> Dict[str, Any]:
    return pyjwt.decode(
        token, _read_jwt_secret(), algorithms=["HS256"],
        audience=config.JWT_AUDIENCE, issuer=config.JWT_ISSUER,
        options={"require": ["exp", "iat", "nbf", "iss", "aud", "jti"]},
    )
```

**Validaciones automáticas** (por PyJWT):
- Expiración (`exp`)
- Emisor (`iss`)
- Audiencia (`aud`)
- Firma HS256

**Extracción de autenticación** (`auth.py:108-123`):
```python
def _auth_from_token(token: Optional[str]) -> Tuple[str, Optional[str], List[str], bool]:
    if token and _is_probably_jwt(token):
        payload = _jwt_decode(token)
        jti = str(payload.get("jti") or "")
        if jti and _is_revoked_jti(jti):
            raise PermissionError("jwt revoked")
        user_id = payload.get("user_id")
        scopes = payload.get("scopes") or []
        role = payload.get("role") or "user"
        return "jwt", user_id, [str(x) for x in scopes], (role == "admin")
    
    if token:
        return "legacy", None, [], False
    return "none", None, [], False
```

### 3.4 Scopes

Los scopes controlan qué operaciones puede realizar un JWT.

**Formato**: `recurso:acción` o wildcards

**Scopes disponibles**:
| Scope | Descripción |
|-------|-------------|
| `peer:read` | Leer información de peers |
| `peer:write` | Registrar peers, heartbeats |
| `network:read` | Leer redes |
| `network:write` | Solicitar redes |
| `config:read` | Obtener configuración |
| `advertise:write` | Reportar reachability |
| `orch:read` | Leer health/metrics |
| `*` o `*:*` | Todos los permisos |
| `peer:*` | Todos los permisos de peers |

**Validación** (`auth.py:126-132`):
```python
def _require_scope(scopes: List[str], needed: str) -> None:
    if needed in scopes:
        return
    prefix = needed.split(":", 1)[0] + ":*"
    if prefix in scopes or "*:*" in scopes or "*" in scopes:
        return
    raise PermissionError(f"missing scope: {needed}")
```

**Scopes por defecto para peers** (`peer_register/config.py:42`):
```python
JWT_SCOPES = [x.strip() for x in os.getenv(
    "WG_JWT_SCOPES",
    "peer:*,network:*,config:*,advertise:*,orch:read"
).replace(" ", "").split(",") if x.strip()]
```

### 3.5 TTL y Refresh

**TTL por defecto**: 600 segundos (10 minutos)

**Refresh**: El peer refresca el JWT 60 segundos antes de que expire.

**Flujo** (`peer_register/auth.py:14-47`):
```python
def _jwt_needs_refresh(st: dict) -> bool:
    exp = int(st.get("jwt_expires_at") or 0)
    if not exp:
        return True
    return int(time.time()) >= (exp - 60)

def ensure_jwt_session(peer_id: str, st: dict) -> str:
    if "jwt" in st and not _jwt_needs_refresh(st):
        return st["jwt"]  # Usar JWT cacheado
    
    if "jwt" in st and _jwt_needs_refresh(st):
        try:
            resp = c.__getattr__("auth.refresh")(st["jwt"], cfg.JWT_TTL)
            st["jwt"] = resp["jwt"]
            st["jwt_expires_at"] = int(resp["expires_at"])
            save_state(st)
            return st["jwt"]
        except Exception:
            pass  # Fallback a login completo
    
    # Login completo con ORCH_TOKEN
    resp = c.__getattr__("auth.login")(uid, peer_id, cfg.ORCH_TOKEN, cfg.JWT_SCOPES, cfg.JWT_TTL)
    st["jwt"] = resp["jwt"]
    st["jwt_expires_at"] = int(resp["expires_at"])
    save_state(st)
    return st["jwt"]
```

### 3.6 Revocación de JWT

Los JWTs pueden ser revocados antes de su expiración.

**Almacenamiento**: `/var/lib/wg-orchestrator/jwt_revoked.json`

**Revocación** (`auth.py:98-105`):
```python
def _revoke_jti(jti: str, reason: str, exp: Optional[int] = None) -> None:
    with state.LOCK_REVOKED:
        rev = _load_revoked()
        rev[str(jti)] = {"ts": state.now_ts(), "reason": reason, "exp": exp or 0}
        # Limpieza de entradas expiradas
        now = state.now_ts()
        rev = {k: v for k, v in rev.items()
               if v.get("exp", 0) == 0 or v.get("exp", 0) > now}
        _save_revoked(rev)
```

**Uso desde CLI**:
```bash
# Revocar un JWT específico
orch-cli revoke <jti> --admin-token "$ADMIN_TOKEN"
```

**Verificación en cada request** (`auth.py:93-95`):
```python
def _is_revoked_jti(jti: str) -> bool:
    with state.LOCK_REVOKED:
        return jti in _load_revoked()
```

---

## 4. Flujo de Autenticación

### 4.1 Flujo Completo

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. ADMIN crea tenant                                                        │
│    orch-cli user-create tenant-a --admin-token $ADMIN_TOKEN                 │
│    → Retorna: {user_id: "tenant-a", token: "u_abc123..."}                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. ADMIN configura peer.env en el host del peer                             │
│    ORCH_TOKEN=u_abc123...                                                   │
│    USER_ID=tenant-a                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. PEER hace auth.login                                                     │
│    peer → orchestrator: auth.login(user_id, peer_id, ORCH_TOKEN, scopes)    │
│    orchestrator: _check_user_token(user_id, ORCH_TOKEN)                     │
│    → Retorna: {jwt: "eyJ...", expires_at: 1703635800}                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. PEER usa JWT para operaciones                                            │
│    peer → orchestrator: peer.register(..., jwt)                             │
│    orchestrator: _auth_from_token(jwt) → "jwt", user_id, scopes, is_admin   │
│    orchestrator: _require_scope(scopes, "peer:write")                       │
│    → Operación permitida                                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ 5. PEER refresca JWT antes de expirar                                       │
│    peer → orchestrator: auth.refresh(jwt, TTL)                              │
│    orchestrator: _jwt_decode(jwt) → validar exp, iss, aud                   │
│    → Retorna: {jwt: "eyJ...nuevo", expires_at: ...}                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Diagrama de Secuencia

```
Admin           Orchestrator              Peer
  │                  │                      │
  │ user-create      │                      │
  │─────────────────>│                      │
  │                  │                      │
  │ {user_id, token} │                      │
  │<─────────────────│                      │
  │                  │                      │
  │ Configura peer.env                      │
  │────────────────────────────────────────>│
  │                  │                      │
  │                  │     auth.login       │
  │                  │<─────────────────────│
  │                  │                      │
  │                  │     {jwt, exp}       │
  │                  │─────────────────────>│
  │                  │                      │
  │                  │  peer.register(jwt)  │
  │                  │<─────────────────────│
  │                  │                      │
  │                  │  {peer_id, wg_ip}    │
  │                  │─────────────────────>│
```

---

## 5. Aislamiento Multi-Tenant

### 5.1 Propiedad de Recursos

Cada peer y red tiene un `user_id` que identifica al tenant propietario.

**Peer** (`endpoints_peers.py`):
```python
peer = {
    "public_key": public_key,
    "ip": ip,
    "networks": [net_id],
    "user_id": user_id,  # ← Propietario
    ...
}
```

**Red** (`endpoints_networks.py`):
```python
network = {
    "cidr": cidr,
    "user_id": user_id,  # ← Propietario
    ...
}
```

### 5.2 Prevención de Cross-Tenant

**Validación** (`auth.py:152-158`):
```python
def _enforce_tenant_for_peer(user_id: str, peer_id: str) -> None:
    with state.LOCK_PEERS:
        p = state.STATE["peers"].get(peer_id)
    if not p:
        raise KeyError("peer not found")
    if str(p.get("user_id") or "default") != str(user_id):
        raise PermissionError("cross-tenant forbidden")
```

**Uso en endpoints**:
```python
# endpoints_config.py
def rpc_config_get_peer_config(params):
    auth_mode, uid, scopes, is_admin_jwt = auth._auth_from_token(token)
    if not is_admin_jwt:
        auth._enforce_tenant_for_peer(str(uid or ""), peer_id)
```

### 5.3 Filtrado de Eventos

Los eventos también se filtran por tenant (`auth.py:161-183`):
```python
def _filter_events_for_tenant(user_id: str) -> List[Dict[str, Any]]:
    out = []
    with state.LOCK_EVENTS:
        events = list(state.STATE.get("events") or [])
    for ev in events:
        d = ev.get("detail") or {}
        pid = d.get("peer_id")
        if pid:
            with state.LOCK_PEERS:
                p = state.STATE["peers"].get(pid) or {}
            if str(p.get("user_id") or "default") != str(user_id):
                continue  # Saltar eventos de otros tenants
        out.append(ev)
    return out
```

### 5.4 Admin Bypass

El admin (con ADMIN_TOKEN o JWT con `role: "admin"`) puede acceder a todos los recursos sin restricción de tenant.

```python
if is_admin_jwt:
    # Sin restricción de tenant
    pass
else:
    auth._enforce_tenant_for_peer(user_id, peer_id)
```

---

## 6. Quotas por Tenant

Cada tenant tiene límites configurables de peers y redes.

### 6.1 Configuración

**Por defecto** (`config.py:59-60`):
```python
DEFAULT_MAX_PEERS = int(os.getenv("DEFAULT_MAX_PEERS", "50"))
DEFAULT_MAX_NETWORKS = int(os.getenv("DEFAULT_MAX_NETWORKS", "10"))
```

**Por tenant** (en `STATE["users"]`):
```python
users[user_id] = {
    "token": token,
    "max_peers": 50,      # Límite de peers
    "max_networks": 10,   # Límite de redes
    ...
}
```

### 6.2 Validación

**Peer quota** (`auth.py:230-236`):
```python
def _check_peer_quota(user_id: str) -> None:
    quota = _get_tenant_quota(user_id)
    with state.LOCK_PEERS:
        count = sum(1 for p in state.STATE["peers"].values()
                    if str(p.get("user_id") or "default") == str(user_id))
    if count >= quota["max_peers"]:
        raise PermissionError(f"Peer quota exceeded: {count}/{quota['max_peers']} for user '{user_id}'")
```

**Network quota** (`auth.py:239-245`):
```python
def _check_network_quota(user_id: str) -> None:
    quota = _get_tenant_quota(user_id)
    with state.LOCK_NETWORKS:
        count = sum(1 for n in state.STATE["networks"].values()
                    if str(n.get("user_id") or "") == str(user_id))
    if count >= quota["max_networks"]:
        raise PermissionError(f"Network quota exceeded: {count}/{quota['max_networks']} for user '{user_id}'")
```

---

## 7. Archivos Sensibles y Permisos

### 7.1 Orchestrator

| Archivo | Permisos | Contenido |
|---------|----------|-----------|
| `/etc/linkguard/secrets` | 600 (root) | ADMIN_TOKEN, ORCH_TOKEN, HUB_AGENT_TOKEN |
| `/etc/linkguard/jwt_secret` | 600 (root) | Clave de firma JWT |
| `/var/lib/wg-orchestrator/state.json` | 644 | Estado (incluye user tokens) |
| `/var/lib/wg-orchestrator/jwt_revoked.json` | 644 | JWTs revocados |
| `/etc/wireguard/wg-HUB.key` | 600 (root) | Clave privada WireGuard del HUB |

### 7.2 Peer

| Archivo | Permisos | Contenido |
|---------|----------|-----------|
| `/etc/linkguard/peer.env` | 600 (root) | ORCH_TOKEN, configuración |
| `/etc/wireguard/wg-auto.json` | 600 (root) | JWT, peer_id, config_version |
| `/etc/wireguard/wg0.key` | 600 (root) | Clave privada WireGuard |
| `/etc/wireguard/wg0.conf` | 600 (root) | Configuración WireGuard (incluye claves) |

**SEC-05**: Estado del peer guardado con permisos 600 (`peer_register/state.py:24`):
```python
def save_state(st: dict) -> None:
    ensure_dir()
    with open(cfg.STATE_PATH, "w") as f:
        json.dump(st, f, indent=2, sort_keys=True)
    os.chmod(cfg.STATE_PATH, 0o600)  # JWT no legible por otros usuarios
```

---

## 8. Validaciones de Seguridad

### 8.1 Tokens Inseguros

**Validación al arranque** (`config.py:70, 85-110`):
```python
INSECURE_TOKENS = {"changeme", "changeme-super-secret", "secret", "password", "12345", ""}

def validate_tokens_at_startup() -> None:
    errors = []
    if not ADMIN_TOKEN:
        errors.append("ADMIN_TOKEN esta vacio")
    elif ADMIN_TOKEN.lower() in INSECURE_TOKENS:
        errors.append(f"ADMIN_TOKEN tiene un valor inseguro ('{ADMIN_TOKEN}')")
    
    if not HUB_AGENT_TOKEN:
        errors.append("HUB_AGENT_TOKEN esta vacio")
    elif HUB_AGENT_TOKEN.lower() in INSECURE_TOKENS:
        errors.append(f"HUB_AGENT_TOKEN tiene un valor inseguro")
    
    if errors:
        for e in errors:
            logger.critical("CONFIGURACION INSEGURA: %s", e)
        raise SystemExit("El orchestrator no puede arrancar con la configuracion actual.")
```

### 8.2 Hub-Agent

**SEC-01**: Validación de token al arranque (`hub-agent.py:139-149`):
```python
def validate_token_at_startup() -> None:
    if not HUB_AGENT_TOKEN:
        raise SystemExit("HUB_AGENT_TOKEN esta vacio")
    if HUB_AGENT_TOKEN.lower() in INSECURE_TOKENS:
        raise SystemExit(f"HUB_AGENT_TOKEN tiene un valor inseguro")
    log("Validación de token de arranque: OK")
```

### 8.3 Peer

**SEC-03**: ORCH_TOKEN requerido (`peer_register/auth.py:25-29`):
```python
if not cfg.ORCH_TOKEN:
    raise RuntimeError(
        "ORCH_TOKEN esta vacio. Configura ORCH_TOKEN en /etc/linkguard/peer.env "
        "(obten el token del admin del orchestrator con: orch-cli issue-user-token <user_id>)"
    )
```

---

## 9. Comparación con Enfoque Unix

| Principio Unix | Implementación LinkGuard |
|----------------|--------------------------|
| **Texto como interfaz** | Tokens en archivos de texto, JWTs en JSON |
| **Silencio es oro** | Logs estructurados, sin output innecesario |
| **Configuración por entorno** | Variables de entorno override archivos |
| **Separación mecanismo/política** | Tokens estáticos para admin, JWTs para sesiones |
| **Transparencia** | Secretos en archivos planos (no bases de datos opacas) |

**Desviaciones**:
- JWTs con scopes complejos (más enterprise que Unix)
- Estado global mutable en memoria (no stateless)
- XML-RPC en vez de pipes/sockets Unix

---

## 10. Checklist de Seguridad

### Instalación

- [ ] `/etc/linkguard/secrets` tiene permisos 600
- [ ] `/etc/linkguard/jwt_secret` tiene permisos 600
- [ ] ADMIN_TOKEN no está en INSECURE_TOKENS
- [ ] HUB_AGENT_TOKEN no está en INSECURE_TOKENS
- [ ] Orchestrator valida tokens al arranque

### Operación

- [ ] peer.env tiene permisos 600
- [ ] wg-auto.json tiene permisos 600
- [ ] Claves WireGuard tienen permisos 600
- [ ] JWTs se refrescan antes de expirar
- [ ] JWTs revocados se limpian periódicamente

### Multi-Tenant

- [ ] Cada peer tiene user_id asignado
- [ ] Cross-tenant forbidden se valida en cada request
- [ ] Eventos se filtran por tenant
- [ ] Admin bypass solo con ADMIN_TOKEN o JWT admin

---

## 11. Referencias

**Código**:
- `orchestrator-install-v2/orchestrator/auth.py` — Autenticación y autorización
- `orchestrator-install-v2/hub-agent.py` — Validación de HUB_AGENT_TOKEN
- `peer-install-v2/peer_register/auth.py` — Gestión de JWT en peer
- `peer-install-v2/peer_register/state.py` — Permisos de archivos

**Documentación**:
- `ciclo-vida.md` — Ciclo de vida completo
- `topologias-soportadas.md` — Topologías
- `multi-tenant-auth.puml` — Diagrama de autenticación multi-tenant
- `single-tenant-auth.puml` — Diagrama de autenticación single-tenant

**RFCs**:
- [RFC 7519 - JSON Web Token (JWT)](https://tools.ietf.org/html/rfc7519)
- [RFC 7518 - JSON Web Algorithms (JWA)](https://tools.ietf.org/html/rfc7518)
