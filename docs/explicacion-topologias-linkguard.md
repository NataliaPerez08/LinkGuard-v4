# Explicación de Topologías LinkGuard

## Cómo se comunica `mesh` con el orquestador

En `mesh`, los peers no dejan de hablar con el orquestador. Lo que cambia es el plano de datos, no el plano de control.

### Cómo se comunican con el orquestador

- Por `HTTP/XML-RPC` a `ORCH_URL`
- En este entorno típico: `http://101.44.24.91:8000/RPC2`
- Eso viaja por la red normal/pública, no por el enlace mesh peer-to-peer

### Flujo

1. El peer arranca y hace `peer.register`
2. Obtiene JWT y mantiene sesión con `auth.login` / `auth.refresh`
3. Pide configuración al orquestador
4. En `mesh`, el orquestador le devuelve la lista de otros peers vivos
5. El peer genera varios bloques `[Peer]` directos en `wg0.conf`
6. Luego sigue mandando `peer.heartbeat` al orquestador periódicamente

### Qué hace el orquestador en mesh

- Sigue siendo el control plane
- Lleva estado de peers, endpoints, heartbeats, topología
- Decide qué peers están vivos y cuáles deben aparecer en la config mesh
- No necesariamente transporta el tráfico de datos entre peers en `mesh`

### Qué tráfico va por dónde

- Tráfico de control:
  - peer -> orquestador por `ORCH_URL`
- Tráfico de datos:
  - peer <-> peer por WireGuard directo

### En el código

- `peer-install-v2/peer_register/auth.py`
  - login/refresh JWT contra el orquestador
- `peer-install-v2/peer_register/commands.py`
  - `peer.register` y `peer.heartbeat`
- `peer-install-v2/peer_register/config_gen.py`
  - genera bloques mesh directos
- `orchestrator-install-v2/orchestrator/endpoints_config.py`
  - calcula peers mesh y devuelve la config

### Resumen

- En `hub-spoke`: control y datos dependen del hub
- En `mesh`: el orquestador sigue controlando, pero los datos van directo peer-a-peer
- En `hub-mesh`: el orquestador sigue controlando y además decide quién va directo y quién cae a relay por HUB

## Diagrama simple

### Hub-Spoke

```text
                Control plane
      peer-a --------------> Orquestador
      peer-b --------------> Orquestador

                Data plane
      peer-a ====WG====> HUB/Orquestador <====WG==== peer-b
```

- El peer siempre habla con el orquestador por `ORCH_URL`
- El tráfico entre peers pasa por el HUB

### Mesh

```text
                Control plane
      peer-a --------------> Orquestador
      peer-b --------------> Orquestador

                Data plane
      peer-a <====WG directo====> peer-b
```

- El orquestador solo coordina
- Entrega endpoints, claves, peers vivos y versiones de config
- El tráfico real va directo peer-a-peer

### Hub-Mesh

```text
                Control plane
      peer-a --------------> Orquestador
      peer-b --------------> Orquestador

                Data plane
      si hay reachability:
          peer-a <====WG directo====> peer-b

      si no hay reachability:
          peer-a ====WG====> HUB/Orquestador <====WG==== peer-b
```

- El orquestador decide si un peer va:
  - `DIRECTO`
  - `RELAY` vía HUB

### En mesh, el orquestador sigue siendo necesario para

1. registrar peers
2. emitir/refrescar JWT
3. recibir heartbeats
4. devolver config
5. anunciar qué peers están vivos

Pero no lleva el tráfico de datos si los peers pueden hablarse directo.

## Diagrama con tus hosts reales

### Hub-Spoke

```text
Control plane (siempre)
46.250.168.185  --------\
122.8.179.57    --------->  101.44.24.91:8000  (orquestador)
46.250.162.141  --------/

Data plane
46.250.168.185 (10.20.30.4)  \
                               >====WG====> 101.44.24.91:51820 <====WG====< 122.8.179.57 (10.20.30.2)
46.250.162.141 (10.20.30.3)  /
```

- Todo el tráfico peer-a-peer pasa por el HUB
- El orquestador/HUB tiene doble rol:
  - control plane
  - relay de datos

### Mesh

```text
Control plane (siempre)
46.250.168.185  --------\
122.8.179.57    --------->  101.44.24.91:8000
46.250.162.141  --------/

Data plane
46.250.168.185 (10.20.30.4) <====WG directo====> 122.8.179.57 (10.20.30.2)
46.250.168.185 (10.20.30.4) <====WG directo====> 46.250.162.141 (10.20.30.3)
122.8.179.57   (10.20.30.2) <====WG directo====> 46.250.162.141 (10.20.30.3)
```

- El orquestador sigue gestionando:
  - registro
  - JWT
  - heartbeats
  - endpoints
  - lista de peers
- Pero el tráfico de datos ya no pasa por `101.44.24.91`

### Hub-Mesh

```text
Control plane (siempre)
46.250.168.185  --------\
122.8.179.57    --------->  101.44.24.91:8000
46.250.162.141  --------/

Data plane
si hay reachability:
46.250.168.185 (10.20.30.4) <====WG directo====> 122.8.179.57 (10.20.30.2)

si no hay reachability:
46.250.168.185 (10.20.30.4) ====WG====> 101.44.24.91:51820 <====WG==== 46.250.162.141 (10.20.30.3)
```

- El orquestador clasifica:
  - `DIRECTO`
  - `RELAY`
- Así algunos peers van directos y otros usan el HUB como fallback

### QEMU integrado al mismo orquestador

```text
Control plane
qemu-orq (10.20.30.5) ----\
qemu-pa  (10.20.30.6) -----+----> 101.44.24.91:8000
qemu-pb  (10.20.30.7) ----/
reales    (10.20.30.2/3/4)-/
```

- Los peers QEMU usan el mismo control plane real
- Por eso pueden coexistir con los peers reales en la misma red `10.20.30.0/24`

### Resumen corto

- `hub-spoke`: datos vía HUB
- `mesh`: datos directos entre peers
- `hub-mesh`: directos cuando se puede, HUB cuando no

## Tabla comparativa

| Topología | Control plane | Data plane | Dependencia del HUB | Comunicación con el orquestador |
|---|---|---|---|---|
| `hub-spoke` | Orquestador central | Todo el tráfico peer-a-peer pasa por el HUB | Alta | Siempre por `ORCH_URL`; además el HUB mueve datos |
| `mesh` | Orquestador central | Peer <-> peer directo | Baja para datos, alta para coordinación | Siempre por `ORCH_URL`; solo coordina |
| `hub-mesh` | Orquestador central | Directo si hay reachability, HUB si no | Media/alta | Siempre por `ORCH_URL`; además decide `DIRECTO` vs `RELAY` |

## Resumen final

| Topología | Registro/Auth | Heartbeats | Configuración | Tráfico entre peers |
|---|---|---|---|---|
| `hub-spoke` | Orquestador | Orquestador | Orquestador | Vía HUB |
| `mesh` | Orquestador | Orquestador | Orquestador | Directo |
| `hub-mesh` | Orquestador | Orquestador | Orquestador | Directo o vía HUB |
