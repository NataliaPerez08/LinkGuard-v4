## Estilo de la API del orchestrator y del peer

Documento relacionado:

- [Indice general de documentacion](./README.md)
- [Indice de diagramas de `tests-aws-multiuser-cli`](./diagramas-tests-aws-multiuser-cli.md)

### Descripcion

El `orchestrator` y el `peer` no siguen el mismo rol, asi que su estilo de API tambien es distinto.

#### Orchestrator

- Es una API RPC remota sobre XML-RPC/HTTP.
- Esta organizada por dominios con namespaces:
  - `orch.*`
  - `auth.*`
  - `network.*`
  - `peer.*`
  - `config.*`
- Su estilo semantico es action-oriented y de orquestacion, no REST.
- La autenticacion va dentro de los argumentos RPC, no por headers HTTP:
  - `ADMIN_TOKEN` para admin
  - `JWT` para tenant o peer
- Es una API de grano grueso: cada llamada representa una operacion completa de negocio, no una manipulacion fina de recursos HTTP.

Resumen del orchestrator:

- RPC
- Namespaced
- Imperativa
- Orientada a workflows de administracion y red
- No REST

#### Peer

Aqui hay una diferencia importante: en este repo el peer no expone un servidor HTTP o XML-RPC propio. El peer es sobre todo un agente cliente que consume la API del orchestrator.

Su estilo es:

- Agent-style o client-side RPC
- Se registra, hace heartbeat, pide configuracion, rota claves y solicita red
- Usa el mismo backend RPC del orchestrator, pero desde una logica de ciclo de vida del nodo
- La autenticacion del peer es stateful:
  - arranca con `ORCH_TOKEN`
  - hace `auth.login`
  - guarda `JWT` y `expires_at`
  - luego usa `auth.refresh`
- El intercambio con el orchestrator mezcla dos patrones:
  - push de estado: `peer.heartbeat(peer_id, status, token)`
  - pull de configuracion: `config.get_peer_config(peer_id, token)`
- El payload del peer es rico en estado operativo, no solo CRUD:
  - estado WG
  - endpoint detectado
  - tipo de NAT
  - version de configuracion
  - hash de peers mesh

#### Interfaz local del peer

Ademas del agente, el peer tiene una CLI local `wg-auto-cli.py`, que actua como una fachada local contextual sobre la API remota.

- El usuario invoca comandos locales tipo:
  - `status`
  - `update`
  - `topology`
  - `unregister`
- La CLI resuelve automaticamente `peer_id` y token local, y luego llama al orchestrator.

Lectura rapida:

- El orchestrator tiene estilo de API RPC de control.
- El peer tiene estilo de agente cliente stateful.
- Ambos no son REST, y estan orientados a comandos y workflows.
- La diferencia principal es que el orchestrator sirve operaciones y el peer ejecuta y sincroniza estado.

### Tabla comparativa

| Aspecto | Orchestrator | Peer |
|---|---|---|
| Rol | Servidor de control y orquestacion | Agente cliente que se registra, reporta estado y aplica config |
| Transporte | XML-RPC sobre HTTP | XML-RPC sobre HTTP hacia el orchestrator |
| Endpoint base | `http://host:8000/RPC2` | `ORCH_URL`, normalmente `.../RPC2` |
| Estilo | RPC remota orientada a comandos | Cliente stateful orientado a ciclo de vida del nodo |
| Modelo semantico | Operaciones de negocio y administracion | Sincronizacion operativa del peer |
| Organizacion | Namespaces: `orch.*`, `auth.*`, `network.*`, `peer.*`, `config.*` | Consume sobre todo `auth.*`, `peer.*`, `config.*`, `network.*` |
| Autenticacion | `ADMIN_TOKEN` o `JWT` pasados como argumentos RPC | Empieza con `ORCH_TOKEN`, obtiene `JWT`, lo refresca y lo guarda en estado |
| Estado | Centralizado en el orchestrator | Local y persistente en `state`, ademas del estado central |
| Patron principal | Llamadas coarse-grained de orquestacion | `register -> heartbeat -> fetch config -> apply config` |
| Patron de datos | Respuestas estructuradas tipo dict/list | Push de estado + pull de configuracion |
| Interfaz humana | `orch-cli.py` como fachada CLI | `wg-auto-cli.py` como fachada local contextual |
| Naturaleza | API de control | Agente de convergencia/configuracion |

Ejemplos tipicos del orchestrator:

- `auth.login`
- `orch.user-create`
- `network.set_topology`
- `peer.unregister`
- `config.get_mesh_peers`

Ejemplos tipicos del peer:

- `peer.register`
- `peer.heartbeat`
- `config.get_peer_config`
- `peer.request_network`
- `peer.rotate_key`

Lectura rapida:

- El orchestrator tiene estilo de API RPC de control.
- El peer tiene estilo de agente cliente stateful.
- El peer no expone aqui una API remota propia; expone una CLI local que traduce acciones del nodo a llamadas RPC al orchestrator.
