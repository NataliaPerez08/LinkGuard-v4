# Manejo de Sesiones en LinkGuard

Describe cómo se gestionan las sesiones (JWT) de peers y tenants contra el orchestrator: obtención, caché, refresh, revocación y almacenamiento de estado.

**Diagramas relacionados:**
- `sesion-jwt-peer.puml` — Sesión JWT del peer (login/refresh/cache)
- `multi-tenant-auth.puml` — Flujo de autenticación multi-tenant
- `single-tenant-auth.puml` — Flujo de autenticación single-tenant

---

## 1. Modelo de Sesión

LinkGuard usa **JWT (HS256)** como sesión de corta duración para peers y tenants. Los tokens estáticos (ADMIN_TOKEN, ORCH_TOKEN, HUB_AGENT_TOKEN) **no son sesiones**: son credenciales de larga duración.

| Componente | Mecanismo | Duración | Propósito |
|---|---|---|---|
| ORCH_TOKEN (`u_<hex16>`) | Token de usuario persistente | Larga | Obtener JWT vía `auth.login` |
| JWT | HS256, claims completos | 600 s (default) | Sesión para operaciones RPC |
| HUB_AGENT_TOKEN | Token estático | Larga | Comunicación orchestrator ↔ hub-agent (sin sesión) |
| ADMIN_TOKEN | Token estático | Larga | Operaciones de administración global |

**Flujo de obtención de sesión:**
1. El admin crea un tenant con `orch-cli user-create <tenant> --admin-token $ADMIN` → retorna `ORCH_TOKEN` (`u_...`).
2. El peer configura `ORCH_TOKEN` + `USER_ID` en `/etc/linkguard/peer.env`.
3. El peer hace `auth.login(user_id, peer_id, ORCH_TOKEN, scopes, TTL)` → recibe `{jwt, expires_at}`.
4. A partir de ahí, el peer envía el JWT en cada RPC. El ORCH_TOKEN solo se reutiliza si el refresh falla y hay que hacer login completo.

---

## 2. Estructura del JWT

Payload (`orchestrator/auth.py:46-59`):

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
  "scopes": ["peer:*", "network:*", "config:*", "advertise:*", "orch:read"],
  "role": "user"
}
```

Claims exigidos por `_jwt_decode` (`auth.py:62-67`):

- `iss`, `aud` — validados contra `config.JWT_ISSUER` / `config.JWT_AUDIENCE`.
- `iat`, `nbf`, `exp` — validación temporal por PyJWT.
- `jti` — identificador único para revocación.
- `user_id`, `peer_id`, `scopes`, `role` — campos personalizados.

El algoritmo es **HS256** con secreto en `/etc/linkguard/jwt_secret` (hex 64 bytes, permisos 600).

---

## 3. Obtención de JWT

### 3.1 `auth.login`

`peer_register/auth.py:43` → `orchestrator/endpoints_auth.py:_xml_auth_login:55`

```python
resp = c.__getattr__("auth.login")(
    uid, peer_id, cfg.ORCH_TOKEN, cfg.JWT_SCOPES, cfg.JWT_TTL
)
st["jwt"] = resp["jwt"]
st["jwt_expires_at"] = int(resp["expires_at"])
```

El orchestrator valida:

1. `_check_user_token(user_id, ORCH_TOKEN)` — verifica el token persistente en `STATE["users"][user_id]["token"]`.
2. `_jwt_encode(payload, ttl)` — firma y emite el JWT.

### 3.2 `auth.refresh`

`peer_register/auth.py:35` → `orchestrator/endpoints_auth.py:_xml_refresh:69`

```python
resp = c.__getattr__("auth.refresh")(st["jwt"], cfg.JWT_TTL)
```

- El orchestrator decodifica el JWT actual (`_jwt_decode`).
- Verifica que el `jti` no esté en `jwt_revoked.json`.
- Re-emite un JWT nuevo con el mismo `user_id`, `peer_id`, `scopes`, `role` pero nuevo `jti` y nuevo `exp`.
- **No requiere ORCH_TOKEN** — solo el JWT anterior (aunque esté a punto de expirar).

---

## 4. Gestión de Sesión en el Peer

### 4.1 `ensure_jwt_session`

Punto de entrada usado antes de cualquier RPC (`peer_register/auth.py:21-47`):

```python
def ensure_jwt_session(peer_id: str, st: dict) -> str:
    if "jwt" in st and not _jwt_needs_refresh(st):
        return st["jwt"]                       # usar JWT cacheado

    if "jwt" in st and _jwt_needs_refresh(st):
        try:
            resp = auth.refresh(st["jwt"], TTL)
            st["jwt"], st["jwt_expires_at"] = resp["jwt"], resp["expires_at"]
            save_state(st)
            return st["jwt"]
        except Exception:
            pass                                # fallback a login completo

    resp = auth.login(uid, peer_id, ORCH_TOKEN, scopes, TTL)
    st["jwt"], st["jwt_expires_at"] = resp["jwt"], resp["expires_at"]
    save_state(st)
    return st["jwt"]
```

**Prioridad**:
1. JWT cacheado válido (`exp > now + 60 s`) → se usa directo.
2. JWT existente próximo a expirar → `auth.refresh`.
3. Si el refresh falla (p.ej. JWT ya expirado o revocado) → `auth.login` con `ORCH_TOKEN`.
4. Si no hay JWT en estado → `auth.login`.

### 4.2 Umbral de refresh

`_jwt_needs_refresh` (`auth.py:14-18`):

```python
def _jwt_needs_refresh(st: dict) -> bool:
    exp = int(st.get("jwt_expires_at") or 0)
    if not exp:
        return True
    return int(time.time()) >= (exp - 60)
```

El peer refresca **60 s antes** de la expiración, evitando ventanas donde el JWT válido es insuficiente para un RPC en vuelo. Con TTL=600 s, el refresh ocurre en el segundo 540.

### 4.3 Estado persistente

El JWT se cachea en `/etc/wireguard/wg-auto.json` (permisos 600):

```json
{
  "peer_id": "peer_a1",
  "jwt": "eyJ...",
  "jwt_expires_at": 1703635800,
  "config_version": 3,
  "mesh_peers_hash": "sha256..."
}
```

Esto permite que el peer sobreviva reinicios sin reloguear de inmediato — si el JWT sigue válido al arrancar, lo reutiliza.

---

## 5. Validación en cada RPC

Cada vez que el orchestrator recibe una llamada con un token, pasa por `_auth_from_token` (`auth.py:108-123`):

```python
def _auth_from_token(token):
    if token and _is_probably_jwt(token):           # 2 puntos + len > 30
        payload = _jwt_decode(token)                 # valida firma, exp, iss, aud
        jti = payload.get("jti")
        if jti and _is_revoked_jti(jti):
            raise PermissionError("jwt revoked")
        return ("jwt", payload["user_id"], payload["scopes"],
                payload.get("role") == "admin")
    if token:
        return ("legacy", None, [], False)          # ADMIN_TOKEN o HUB_AGENT_TOKEN
    return ("none", None, [], False)
```

Pasos:
1. **Detección**: si el token tiene forma de JWT (2 puntos, longitud > 30) se procesa como tal; si no, se trata como token legacy (admin/hub).
2. **Decodificación**: `_jwt_decode` valida firma HS256, `iss`, `aud`, `exp`, `nbf`, `iat`, `jti` (todos obligatorios).
3. **Revocación**: consulta `jwt_revoked.json` por `jti`.
4. **Autorización**: `_require_scope(scopes, "peer:write")` por endpoint.

El coste por RPC incluye: decodificación HMAC + lookup en un dict de JTIs revocados. No hay I/O a disco salvo que la blacklist cambie.

---

## 6. Revocación

### 6.1 Almacenamiento

`/var/lib/wg-orchestrator/jwt_revoked.json` — dict `{jti: {ts, reason, exp}}`.

### 6.2 Mecanismo

`auth.py:98-105`:

```python
def _revoke_jti(jti, reason, exp=None):
    with state.LOCK_REVOKED:
        rev = _load_revoked()
        rev[jti] = {"ts": state.now_ts(), "reason": reason, "exp": exp or 0}
        now = state.now_ts()
        rev = {k: v for k, v in rev.items()
               if v.get("exp", 0) == 0 or v.get("exp", 0) > now}
        _save_revoked(rev)
```

- Añade el `jti` a la blacklist con timestamp y motivo.
- **Limpieza automática**: al escribir, poda los JTIs cuyo `exp` ya venció — la blacklist no crece indefinidamente porque los JWTs expirados son inválidos de todas formas.
- Verificación en cada request: `_is_revoked_jti` (`auth.py:93-95`) solo comprueba presencia del `jti` en el dict cargado en memoria.

### 6.3 Uso desde CLI

```bash
orch-cli revoke <jti> --admin-token "$ADMIN_TOKEN"
```

Requiere `ADMIN_TOKEN` (la revocación es operación de admin). Casos típicos:
- Compromiso de un peer → revocar su JWT activo antes de que expire.
- Logout administrativo de un tenant.
- Rotación: tras cambiar `jwt_secret`, los JTIs previos dejan de validar y no hace falta revocar manualmente.

---

## 7. Rotación del Secreto JWT

El secreto (`/etc/linkguard/jwt_secret`) es **recargable en caliente** sin reiniciar el orchestrator (`auth.py:22-43`):

```python
def _read_jwt_secret() -> str:
    global _JWT_SECRET_HASH, _JWT_SECRET_VALUE
    with open(config.JWT_SECRET_PATH) as f:
        s = f.read().strip()
    file_hash = hashlib.sha256(s.encode()).hexdigest()
    with _JWT_SECRET_LOCK:
        if file_hash != _JWT_SECRET_HASH:
            _JWT_SECRET_HASH, _JWT_SECRET_VALUE = file_hash, s
            config.log("JWT secret recargado (hash cambio)")
        return _JWT_SECRET_VALUE
```

**Comportamiento**:
- Cada llamada a `_jwt_decode` / `_jwt_encode` invoca `_read_jwt_secret`.
- Si el contenido del archivo cambió (sha256 distinto), se recarga el valor cacheado.
- **Efecto inmediato**: todos los JWTs firmados con el secreto anterior fallan `_jwt_decode` y los peers caen al fallback `auth.login` (que firma con el nuevo secreto).

Rotación operativa:
```bash
openssl rand -hex 64 > /etc/linkguard/jwt_secret
# En el siguiente RPC, el orchestrator recarga el secreto.
# Los peers fallan refresh, hacen auth.login y obtienen JWTs firmados con el nuevo secreto.
```

No requiere reiniciar el servicio ni coordinar con los peers — la rotación se propaga en el siguiente ciclo de heartbeat.

---

## 8. Scopes de Sesión

Los JWTs cargan `scopes` que el endpoint valida con `_require_scope`:

| Scope | Operaciones |
|---|---|
| `peer:read` | `peer.list`, `peer.get` |
| `peer:write` | `peer.register`, `peer.heartbeat`, `peer.unregister` |
| `network:read` | `network.list` |
| `network:write` | `peer.request_network` |
| `config:read` | `config.get_peer_config` |
| `advertise:write` | `peer.report_reachability` |
| `orch:read` | `orch.health`, `orch.metrics` |
| `peer:*` | todos los de peer |
| `*` / `*:*` | todos |

Default del peer (`WG_JWT_SCOPES`): `peer:*,network:*,config:*,advertise:*,orch:read`.

`_require_scope` (`auth.py:126-132`) admite wildcards:

```python
def _require_scope(scopes, needed):
    if needed in scopes:
        return
    prefix = needed.split(":", 1)[0] + ":*"
    if prefix in scopes or "*:*" in scopes or "*" in scopes:
        return
    raise PermissionError(f"missing scope: {needed}")
```

Los scopes **no se pueden ampliar** desde el peer: están firmados en el JWT y el orchestrator los diffean contra el campo `scopes` del payload al decodificar.

---

## 9. Sesión y Aislamiento Multi-Tenant

El JWTmaterial tambián transporta `user_id`, usado para aislar recursos:

- **`_enforce_tenant_for_peer(user_id, peer_id)`** (`auth.py:152-158`): comprueba que `STATE["peers"][peer_id]["user_id"] == user_id` del JWT; si no, lanza `cross-tenant forbidden` (403).
- **`_filter_events_for_tenant`** (`auth.py:161-183`): los eventos (`peer.register`, `peer.unregister`, `network.create`, etc.) solo se entregan a tenants propietarios del `peer_id` referenciado.
- **Admin bypass**: si `role == "admin"` en el JWT, o si se usa `ADMIN_TOKEN`, no se invoca `_enforce_tenant_for_peer`.

Por tanto, la sesión JWT no es solo una credencial de autenticación: **ataca el `user_id` a cada RPC**, simplificando la autorización por tenant.

---

## 10. Línea de Tiempo de una Sesión

```
t=0s    peer arranca, no hay JWT en wg-auto.json
        └─ auth.login(ORCH_TOKEN) → JWT exp=t+600s
t=25s   peer.heartbeat(JWT)         ─ OK
t=50s   peer.heartbeat(JWT)         ─ OK
...
t=540s  _jwt_needs_refresh → True   └─ auth.refresh(JWT) → nuevo JWT exp=t+1140s
t=565s  peer.heartbeat(JWT nuevo)   ─ OK
...
t=1080s refresh de nuevo            └─ auth.refresh ─ OK
...

Fallo:
t=610s  auth.refresh falla (orchestrator reiniciado con nuevo secret)
        └─ except → auth.login(ORCH_TOKEN) → JWT nuevo firmado con nuevo secret

Revocación:
admin: orch-cli revoke <jti> --admin-token $ADMIN
        └─ siguiente RPC con ese JWT → PermissionError("jwt revoked")
        └─ peer cae a except en ensure_jwt_session → auth.login → nuevo JWT
```

---

## 11. Resumen Operativo

| Parámetro | Default | Configurable en |
|---|---|---|
| `JWT_TTL` | 600 s (10 min) | `JWT_TTL_DEFAULT` env orchestrator, `WG_JWT_TTL` env peer |
| Refresh anticipado | 60 s antes de exp | hardcodeado `_jwt_needs_refresh` |
| Scopes peer | `peer:*,network:*,config:*,advertise:*,orch:read` | `WG_JWT_SCOPES` env peer |
| Secreto | `/etc/linkguard/jwt_secret` (hex 64) | `JWT_SECRET_PATH` env orchestrator |
| Revocación | `/var/lib/wg-orchestrator/jwt_revoked.json` | `JWTREVOKED_PATH` (implícito) |
| Estado peer | `/etc/wireguard/wg-auto.json` (0600) | `WG_STATE_PATH` env peer |

**Identidad de la sesión**: el par `(user_id, peer_id)` firmado en el JWT. `user_id` determina ownership y aislamiento; `peer_id` vincula la sesión al peer que la solicitó (algunos endpoints validan que el `peer_id` del JWT coincida con el `peer_id` del recurso accedido).

**No hay logout en el peer**: la sesión se mantiene indefinidamente mediante refresh. El logout real es la revocación del `jti` por un admin.

---

## 12. Referencias

**Código**:
- `orchestrator-install-v2/orchestrator/auth.py:46-123` — emisión, decodificación, validación de JWT.
- `orchestrator-install-v2/orchestrator/auth.py:22-43` — recarga en caliente del secreto.
- `orchestrator-install-v2/orchestrator/auth.py:98-105` — revocación.
- `orchestrator-install-v2/orchestrator/endpoints_auth.py:55,69` — endpoints `auth.login` y `auth.refresh`.
- `peer-install-v2/peer_register/auth.py:14-47` — `ensure_jwt_session`, `_jwt_needs_refresh`.
- `peer-install-v2/peer_register/state.py` — persistencia del JWT en `wg-auto.json` (0600).

**Diagramas**:
- `sesion-jwt-peer.puml` — flujo `ensure_jwt_session`.
- `multi-tenant-auth.puml` — provisioning de tenant + sesión con aislamiento.
- `single-tenant-auth.puml` — sesión con un único tenant.
- `config-version-bumps.puml` — integración con heartbeat y drift.

**RFCs**:
- [RFC 7519 - JSON Web Token (JWT)](https://tools.ietf.org/html/rfc7519)
- [RFC 7518 - JSON Web Algorithms (JWA)](https://tools.ietf.org/html/rfc7518)