# New session - 2026-06-23T20:59:01.701Z

**Session ID:** ses_109b87f3affeEc4BHi8sLoNZj5
**Created:** 6/23/2026, 2:59:01 PM
**Updated:** 6/23/2026, 3:11:04 PM

---

## User

Describe the implementation of the project

---

## Assistant (Build · Qwen3.7 Plus · 132.6s)

_Thinking:_

The user wants me to describe the implementation of the project. Let me explore the codebase structure to understand what this project is about.


**Tool: read**

**Input:**
```json
{
  "filePath": "/home/natalia/Documents/Releasev4"
}
```

**Output:**
```
<path>/home/natalia/Documents/Releasev4</path>
<type>directory</type>
<entries>
.bandit
.git/
.github/
.gitignore
.mypy_cache/
.pytest_cache/
acceso.txt
AGENTS.md
Archivador.zip
docs.zip
docs/
howtotest
linkguard-key.pem
Makefile
orchestrator-install-v2/
peer-install-v2/
scripts/
session-parrot-test.md
testbed/
tests-cli-multiuser-altcidr/
tests-cli-multiuser/
tests-cli/
tests-expanded/
tests-linkguard-aws/
tests-parrot/

(25 entries)
</entries>
```

**Tool: glob**

**Input:**
```json
{
  "path": "/home/natalia/Documents/Releasev4",
  "pattern": "**/*.md"
}
```

**Output:**
```
/home/natalia/Documents/Releasev4/AGENTS.md
/home/natalia/Documents/Releasev4/session-parrot-test.md
/home/natalia/Documents/Releasev4/docs/reporte-rendimiento-conectividad.md
/home/natalia/Documents/Releasev4/docs/topologias-linkguard.md
/home/natalia/Documents/Releasev4/docs/integracion-qemu.md
/home/natalia/Documents/Releasev4/docs/explicacion-topologias-linkguard.md
/home/natalia/Documents/Releasev4/docs/reporte-rendimiento-historial.md
/home/natalia/Documents/Releasev4/peer-install-v2/README.md
/home/natalia/Documents/Releasev4/orchestrator-install-v2/README.md
```

**Tool: glob**

**Input:**
```json
{
  "path": "/home/natalia/Documents/Releasev4",
  "pattern": "**/*.py"
}
```

**Output:**
```
/home/natalia/Documents/Releasev4/tests-linkguard-aws/collect-hostinfo.py
/home/natalia/Documents/Releasev4/tests-linkguard-aws/generate-report-hubmesh.py
/home/natalia/Documents/Releasev4/tests-linkguard-aws/generate-report-hubspoke.py
/home/natalia/Documents/Releasev4/tests-linkguard-aws/generate-report-mesh.py
/home/natalia/Documents/Releasev4/tests-linkguard-aws/report_common.py
/home/natalia/Documents/Releasev4/tests-parrot/generate-report-mesh.py
/home/natalia/Documents/Releasev4/tests-parrot/generate-report-hubmesh.py
/home/natalia/Documents/Releasev4/tests-parrot/generate-report-hubspoke.py
/home/natalia/Documents/Releasev4/tests-cli-multiuser-altcidr/generate-report-mesh.py
/home/natalia/Documents/Releasev4/tests-cli-multiuser-altcidr/generate-report-hubmesh.py
/home/natalia/Documents/Releasev4/tests-cli-multiuser-altcidr/generate-report-hubspoke.py
/home/natalia/Documents/Releasev4/tests-cli-multiuser/generate-report-mesh.py
/home/natalia/Documents/Releasev4/tests-cli-multiuser/generate-report-hubspoke.py
/home/natalia/Documents/Releasev4/tests-cli-multiuser/generate-report-hubmesh.py
/home/natalia/Documents/Releasev4/tests-cli/generate-report-mesh.py
/home/natalia/Documents/Releasev4/tests-cli/generate-report-hubmesh.py
/home/natalia/Documents/Releasev4/tests-cli/generate-report-hubspoke.py
/home/natalia/Documents/Releasev4/tests-expanded/generate-report-mesh.py
/home/natalia/Documents/Releasev4/tests-expanded/generate-report-hubmesh.py
/home/natalia/Documents/Releasev4/tests-expanded/generate-report-hubspoke.py
/home/natalia/Documents/Releasev4/scripts/generate-report-mesh.py
/home/natalia/Documents/Releasev4/scripts/generate-report-hubmesh.py
/home/natalia/Documents/Releasev4/scripts/generate-report-hubspoke.py
/home/natalia/Documents/Releasev4/scripts/generate-report-html.py
/home/natalia/Documents/Releasev4/scripts/generate-performance-report.py
/home/natalia/Documents/Releasev4/testbed/tests-alt-cidr/generate-report-mesh.py
/home/natalia/Documents/Releasev4/testbed/tests-alt-cidr/generate-report-hubmesh.py
/home/natalia/Documents/Releasev4/testbed/tests-alt-cidr/generate-report-hubspoke.py
/home/natalia/Documents/Releasev4/testbed/tests/test_real_orchestrator_integration.py
/home/natalia/Documents/Releasev4/testbed/tests/test_wireguard_integration.py
/home/natalia/Documents/Releasev4/testbed/scripts/launch-testbed.py
/home/natalia/Documents/Releasev4/testbed/scripts/create-base-image.py
/home/natalia/Documents/Releasev4/orchestrator-install-v2/hub-agent.py
/home/natalia/Documents/Releasev4/orchestrator-install-v2/orch-cli.py
/home/natalia/Documents/Releasev4/peer-install-v2/wg-auto-register.py
/home/natalia/Documents/Releasev4/peer-install-v2/tests/test_config_gen.py
/home/natalia/Documents/Releasev4/peer-install-v2/wg-auto-cli.py
/home/natalia/Documents/Releasev4/peer-install-v2/tests/test_nat.py
/home/natalia/Documents/Releasev4/peer-install-v2/tests/test_utils.py
/home/natalia/Documents/Releasev4/peer-install-v2/tests/test_integration_mixed_nat_topologies.py
/home/natalia/Documents/Releasev4/peer-install-v2/tests/test_keys.py
/home/natalia/Documents/Releasev4/peer-install-v2/tests/conftest.py
/home/natalia/Documents/Releasev4/peer-install-v2/tests/test_identity.py
/home/natalia/Documents/Releasev4/peer-install-v2/tests/test_supported_topologies.py
/home/natalia/Documents/Releasev4/peer-install-v2/tests/test_peer_config.py
/home/natalia/Documents/Releasev4/peer-install-v2/tests/test_peer_auth.py
/home/natalia/Documents/Releasev4/peer-install-v2/tests/test_integration_reachability.py
/home/natalia/Documents/Releasev4/peer-install-v2/tests/test_probe.py
/home/natalia/Documents/Releasev4/peer-install-v2/tests/test_peer_state.py
/home/natalia/Documents/Releasev4/orchestrator-install-v2/tests/test_supported_topologies.py
/home/natalia/Documents/Releasev4/orchestrator-install-v2/tests/test_peer_compat.py
/home/natalia/Documents/Releasev4/orchestrator-install-v2/tests/integration_orchestrator.py
/home/natalia/Documents/Releasev4/orchestrator-install-v2/tests/test_hub_client.py
/home/natalia/Documents/Releasev4/orchestrator-install-v2/tests/test_endpoints.py
/home/natalia/Documents/Releasev4/orchestrator-install-v2/tests/test_auto_approve.py
/home/natalia/Documents/Releasev4/orchestrator-install-v2/tests/test_network_alloc.py
/home/natalia/Documents/Releasev4/orchestrator-install-v2/tests/test_auth.py
/home/natalia/Documents/Releasev4/orchestrator-install-v2/tests/test_state.py
/home/natalia/Documents/Releasev4/orchestrator-install-v2/tests/test_config.py
/home/natalia/Documents/Releasev4/orchestrator-install-v2/tests/conftest.py
/home/natalia/Documents/Releasev4/orchestrator-install-v2/orchestrator.py
/home/natalia/Documents/Releasev4/peer-install-v2/peer_register/state.py
/home/natalia/Documents/Releasev4/peer-install-v2/peer_register/probe.py
/home/natalia/Documents/Releasev4/peer-install-v2/peer_register/keys.py
/home/natalia/Documents/Releasev4/peer-install-v2/peer_register/identity.py
/home/natalia/Documents/Releasev4/peer-install-v2/peer_register/utils.py
/home/natalia/Documents/Releasev4/peer-install-v2/peer_register/config.py
/home/natalia/Documents/Releasev4/peer-install-v2/peer_register/nat.py
/home/natalia/Documents/Releasev4/peer-install-v2/peer_register/auth.py
/home/natalia/Documents/Releasev4/peer-install-v2/peer_register/config_gen.py
/home/natalia/Documents/Releasev4/peer-install-v2/peer_register/commands.py
/home/natalia/Documents/Releasev4/peer-install-v2/peer_register/__init__.py
/home/natalia/Documents/Releasev4/orchestrator-install-v2/orchestrator/hub_client.py
/home/natalia/Documents/Releasev4/orchestrator-install-v2/orchestrator/auth.py
/home/natalia/Documents/Releasev4/orchestrator-install-v2/orchestrator/state.py
/home/natalia/Documents/Releasev4/orchestrator-install-v2/orchestrator/config.py
/home/natalia/Documents/Releasev4/orchestrator-install-v2/orchestrator/endpoints_auth.py
/home/natalia/Documents/Releasev4/orchestrator-install-v2/orchestrator/auto_approve.py
/home/natalia/Documents/Releasev4/orchestrator-install-v2/orchestrator/network_alloc.py
/home/natalia/Documents/Releasev4/orchestrator-install-v2/orchestrator/endpoints_users.py
/home/natalia/Documents/Releasev4/orchestrator-install-v2/orchestrator/endpoints_orch.py
/home/natalia/Documents/Releasev4/orchestrator-install-v2/orchestrator/endpoints_peers.py
/home/natalia/Documents/Releasev4/orchestrator-install-v2/orchestrator/endpoints_config.py
/home/natalia/Documents/Releasev4/orchestrator-install-v2/orchestrator/endpoints_networks.py
/home/natalia/Documents/Releasev4/orchestrator-install-v2/orchestrator/endpoints_advertised.py
/home/natalia/Documents/Releasev4/orchestrator-install-v2/orchestrator/__init__.py
```

---

## Assistant (Build · Qwen3.7 Plus · 9.0s)

_Thinking:_

Let me explore the key files to understand the project architecture and implementation.


**Tool: read**

**Input:**
```json
{
  "filePath": "/home/natalia/Documents/Releasev4/orchestrator-install-v2/orchestrator.py",
  "limit": 80
}
```

**Output:**
```
<path>/home/natalia/Documents/Releasev4/orchestrator-install-v2/orchestrator.py</path>
<type>file</type>
<content>
1: #!/usr/bin/env python3
2: """
3: LinkGuard Orchestrator v4 - Wrapper de compatibilidad.
4: Conserva compatibilidad con: ExecStart=python3 /opt/linkguard-orchestrator/orchestrator.py
5: """
6: 
7: from orchestrator import main
8: 
9: main()

(End of file - total 9 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/natalia/Documents/Releasev4/peer-install-v2/wg-auto-register.py",
  "limit": 80
}
```

**Output:**
```
<path>/home/natalia/Documents/Releasev4/peer-install-v2/wg-auto-register.py</path>
<type>file</type>
<content>
1: #!/usr/bin/env python3
2: # -*- coding: utf-8 -*-
3: # wg-auto-register v4 — wrapper para peer_register/
4: # SEC-05:   Estado del peer guardado con permisos 600 (JWT no legible por otros usuarios)
5: # SEC-03:   ORCH_TOKEN requerido con mensaje de error claro
6: # MESH-F3a: apply_config genera N bloques [Peer] en redes mesh
7: # MESH-F3b: cmd_heartbeat detecta cambio de mesh_peers_hash y reaplica config
8: # MESH-F3c: cmd_heartbeat incluye endpoint detectado en el status
9: # HM-F4a:  apply_config genera .conf hub-mesh: HUB=/CIDR, directos=/32, relay sin bloque
10: # HM-F4b:  detect_nat_type: heuristica none|full-cone|symmetric
11: # HM-F4c:  probe_direct_peers: monitor handshakes -> peer.report_reachability
12: # HM-F4d:  cmd_heartbeat: incluye nat_type, llama probe_direct_peers en hub-mesh
13: 
14: from peer_register import main as _main
15: 
16: if __name__ == "__main__":
17:     _main()

(End of file - total 17 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/natalia/Documents/Releasev4/orchestrator-install-v2/README.md"
}
```

**Output:**
```
<path>/home/natalia/Documents/Releasev4/orchestrator-install-v2/README.md</path>
<type>file</type>
<content>
1: 
2: # LinkGuard Orchestrator – Installation Bundle (v2)
3: 
4: Installs:
5: - orchestrator (control plane)
6: - hub-agent (WireGuard privileged helper)
7: - orch-cli (administrator CLI)
8: 
9: ## Install
10: ```bash
11: unzip orchestrator-install-v2.zip
12: cd orchestrator-install-v2
13: sudo bash install.sh
14: ```
15: 
16: ## Verify
17: ```bash
18: systemctl status orchestrator
19: systemctl status hub-agent
20: orch-cli health
21: ```

(End of file - total 21 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/natalia/Documents/Releasev4/peer-install-v2/README.md"
}
```

**Output:**
```
<path>/home/natalia/Documents/Releasev4/peer-install-v2/README.md</path>
<type>file</type>
<content>
1: 
2: # LinkGuard Peer – Installation Bundle (v2)
3: 
4: Installs:
5: - wg-auto-register (peer agent)
6: - wg-auto-cli (local peer CLI)
7: - orch-cli (read-only orchestration CLI)
8: 
9: ## Install
10: ```bash
11: unzip peer-install-v2.zip
12: cd peer-install-v2
13: sudo bash install.sh
14: ```
15: 
16: ## Verify
17: ```bash
18: systemctl status wg-auto-register
19: wg-auto-cli status
20: orch-cli health
21: ```
22: 
23: 
24: https://linkguard-release.s3.us-east-2.amazonaws.com/Releasev4.zip

(End of file - total 24 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/natalia/Documents/Releasev4/docs/topologias-linkguard.md"
}
```

**Output:**
```
<path>/home/natalia/Documents/Releasev4/docs/topologias-linkguard.md</path>
<type>file</type>
<content>
1: # Pruebas de Topologías LinkGuard
2: 
3: ## Objetivo
4: 
5: Este documento describe cómo probar y desmontar las tres topologías soportadas por LinkGuard:
6: 
7: - `hub-spoke`
8: - `mesh`
9: - `hub-mesh`
10: 
11: Explicación conceptual y diagramas:
12: 
13: - `docs/explicacion-topologias-linkguard.md`
14: 
15: Los ejemplos asumen:
16: 
17: - orquestador instalado en `101.44.24.91`
18: - `orch-cli` disponible en el orquestador
19: - `wg-auto-cli` disponible en cada peer
20: - red de prueba `default` con CIDR `10.20.30.0/24`
21: 
22: ## Pre-requisitos comunes
23: 
24: En el orquestador:
25: 
26: ```bash
27: ssh root@101.44.24.91
28: source /etc/linkguard/secrets
29: orch-cli health
30: orch-cli peer-list --admin-token "$ADMIN_TOKEN"
31: orch-cli net-list --admin-token "$ADMIN_TOKEN"
32: ```
33: 
34: En cada peer:
35: 
36: ```bash
37: systemctl status wg-auto-register
38: wg-auto-cli orch-health
39: wg-auto-cli mesh-status
40: ip -4 addr show dev wg0
41: wg show wg0
42: ```
43: 
44: Matriz de peers de ejemplo:
45: 
46: - `peer-a`: `46.250.168.185`
47: - `peer-b`: `122.8.179.57`
48: - `peer-c`: `46.250.162.141`
49: 
50: IPs de túnel esperadas en el ejemplo actual:
51: 
52: - `peer-a`: `10.20.30.4`
53: - `peer-b`: `10.20.30.2`
54: - `peer-c`: `10.20.30.3`
55: 
56: ## Hub-Spoke
57: 
58: ### Montaje
59: 
60: En el orquestador:
61: 
62: ```bash
63: source /etc/linkguard/secrets
64: orch-cli net-set-topology default hub-spoke --admin-token "$ADMIN_TOKEN"
65: orch-cli net-topology default --admin-token "$ADMIN_TOKEN"
66: ```
67: 
68: En cada peer, forzar recarga:
69: 
70: ```bash
71: systemctl restart wg-auto-register
72: sleep 5
73: wg-auto-cli mesh-status
74: ```
75: 
76: ### Validación
77: 
78: Qué debes ver:
79: 
80: - `wg-auto-cli mesh-status` muestra solo el bloque del HUB.
81: - `orch-cli mesh-peers default --admin-token "$ADMIN_TOKEN"` debe fallar porque no es una red mesh.
82: - Los peers se alcanzan entre sí a través del HUB.
83: 
84: Pruebas sugeridas:
85: 
86: ```bash
87: ping -c 3 10.20.30.2
88: ping -c 3 10.20.30.3
89: ```
90: 
91: En el HUB:
92: 
93: ```bash
94: wg show wg-HUB
95: ```
96: 
97: Verifica que cada peer tenga su `allowed ips` en `/32`.
98: 
99: ### Desmontaje
100: 
101: En cada peer:
102: 
103: ```bash
104: systemctl stop wg-auto-register
105: wg-quick down wg0 || true
106: wg-auto-cli unregister
107: ```
108: 
109: En el orquestador:
110: 
111: ```bash
112: source /etc/linkguard/secrets
113: orch-cli peer-list --admin-token "$ADMIN_TOKEN"
114: ```
115: 
116: ## Mesh
117: 
118: ### Montaje
119: 
120: En el orquestador:
121: 
122: ```bash
123: source /etc/linkguard/secrets
124: orch-cli net-set-topology default mesh --admin-token "$ADMIN_TOKEN"
125: orch-cli net-topology default --admin-token "$ADMIN_TOKEN"
126: orch-cli mesh-peers default --admin-token "$ADMIN_TOKEN"
127: ```
128: 
129: En cada peer:
130: 
131: ```bash
132: systemctl restart wg-auto-register
133: sleep 5
134: wg-auto-cli mesh-status
135: ```
136: 
137: ### Validación
138: 
139: Qué debes ver:
140: 
141: - `wg-auto-cli mesh-status` muestra bloques `[Peer]` adicionales para peers vivos.
142: - `orch-cli mesh-peers default --admin-token "$ADMIN_TOKEN"` devuelve una lista.
143: - Si todos los peers son alcanzables, habrá handshakes directos peer-a/peer-b, peer-a/peer-c, peer-b/peer-c.
144: 
145: Pruebas sugeridas:
146: 
147: ```bash
148: ping -c 3 10.20.30.4
149: ping -c 3 10.20.30.2
150: ping -c 3 10.20.30.3
151: wg-auto-cli mesh-status
152: ```
153: 
154: ### Desmontaje
155: 
156: Volver a la topología básica:
157: 
158: ```bash
159: source /etc/linkguard/secrets
160: orch-cli net-set-topology default hub-spoke --admin-token "$ADMIN_TOKEN"
161: ```
162: 
163: Si quieres desmontar por completo:
164: 
165: ```bash
166: systemctl stop wg-auto-register
167: wg-quick down wg0 || true
168: wg-auto-cli unregister
169: ```
170: 
171: ## Hub-Mesh
172: 
173: ### Montaje
174: 
175: En el orquestador:
176: 
177: ```bash
178: source /etc/linkguard/secrets
179: orch-cli net-set-topology default hub-mesh --admin-token "$ADMIN_TOKEN"
180: orch-cli peer-reachability default --admin-token "$ADMIN_TOKEN"
181: ```
182: 
183: En cada peer:
184: 
185: ```bash
186: systemctl restart wg-auto-register
187: sleep 5
188: wg-auto-cli mesh-status
189: ```
190: 
191: ### Validación
192: 
193: Qué debes ver:
194: 
195: - `orch-cli peer-reachability default --admin-token "$ADMIN_TOKEN"` separa peers `DIRECTO` y `RELAY`.
196: - `wg-auto-cli mesh-status` muestra:
197:   - bloques directos para peers alcanzables
198:   - comentarios `Relay-via-HUB` para peers que usan relay
199: - el HUB sigue presente como relay de fallback.
200: 
201: Pruebas sugeridas:
202: 
203: ```bash
204: orch-cli peer-reachability default --admin-token "$ADMIN_TOKEN"
205: orch-cli mesh-peers default --admin-token "$ADMIN_TOKEN"
206: wg-auto-cli mesh-status
207: ping -c 3 10.20.30.4
208: ping -c 3 10.20.30.2
209: ping -c 3 10.20.30.3
210: ```
211: 
212: Si un peer queda detrás de NAT simétrico, el tráfico debe seguir funcionando, pero el detalle de reachability lo mostrará como `RELAY`.
213: 
214: ### Desmontaje
215: 
216: Para volver a una topología sin enlaces directos:
217: 
218: ```bash
219: source /etc/linkguard/secrets
220: orch-cli net-set-topology default hub-spoke --admin-token "$ADMIN_TOKEN"
221: ```
222: 
223: Para desmontar completamente:
224: 
225: ```bash
226: systemctl stop wg-auto-register
227: wg-quick down wg0 || true
228: wg-auto-cli unregister
229: ```
230: 
231: ## Limpieza completa del laboratorio
232: 
233: Si quieres dejar el entorno sin peers activos:
234: 
235: En cada peer:
236: 
237: ```bash
238: systemctl stop wg-auto-register
239: wg-quick down wg0 || true
240: wg-auto-cli unregister
241: rm -f /etc/wireguard/wg0.conf /etc/wireguard/wg-auto.json
242: ```
243: 
244: En el orquestador:
245: 
246: ```bash
247: source /etc/linkguard/secrets
248: orch-cli peer-list --admin-token "$ADMIN_TOKEN"
249: orch-cli net-topology default --admin-token "$ADMIN_TOKEN"
250: wg show wg-HUB
251: ```
252: 
253: Si también quieres borrar la red de pruebas:
254: 
255: ```bash
256: orch-cli net-delete default --admin-token "$ADMIN_TOKEN"
257: ```
258: 
259: Solo haz esto último si vas a recrear la red antes de volver a registrar peers.
260: 
261: ## Suites automáticas relacionadas
262: 
263: Pruebas unitarias del orquestador:
264: 
265: ```bash
266: pytest orchestrator-install-v2/tests/test_supported_topologies.py -q
267: ```
268: 
269: Pruebas unitarias del peer:
270: 
271: ```bash
272: pytest peer-install-v2/tests/test_supported_topologies.py -q
273: ```
274: 
275: Pruebas de integración QEMU existentes:
276: 
277: ```bash
278: pytest testbed/tests/test_wireguard_integration.py -q
279: ```
280: 
281: Escenario mixto adicional `Arch + Alpine` detrás de NAT simétrico:
282: 
283: ```bash
284: pytest peer-install-v2/tests/test_integration_mixed_nat_topologies.py -q
285: ```
286: 
287: Ese escenario modela:
288: 
289: - VM `Arch Linux` anunciando `46.250.168.185:51820`
290: - VM `Alpine Linux` anunciando `122.8.179.57:51820`
291: - ambas detrás de NAT simétrico
292: - sin alcanzabilidad por red privada entre sí
293: - comparación del comportamiento en `hub-spoke`, `mesh` y `hub-mesh`
294: 
295: Para correr todo el paquete de pruebas de topologías, incluyendo la suite QEMU del testbed:
296: 
297: ```bash
298: make topology-test-all
299: ```
300: 
301: Para un flujo tipo CI que levante el testbed, ejecute todas las pruebas y lo desmonte al final:
302: 
303: ```bash
304: make topology-test-ci
305: ```
306: 
307: Nota:
308: 
309: - `topology-test-all` requiere que el laboratorio QEMU ya esté levantado y accesible.
310: - Si solo quieres las pruebas unitarias/simuladas, usa `make topology-test`.
311: - `topology-test-ci` automatiza `up -> tests -> down`.
312: - Si tu entorno necesita contraseña de sudo distinta, exporta `SUDO_PASS` antes de ejecutarlo.
313: 
314: ## Integración del testbed QEMU con el orquestador real
315: 
316: El testbed ahora soporta un modo integrado para que las VMs `orq`, `pa` y `pb`
317: se registren como peers contra el mismo orquestador real que usa la infraestructura
318: en Huawei Cloud.
319: 
320: Variables esperadas:
321: 
322: ```bash
323: export TESTBED_REAL_ORCH_HOST=101.44.24.91
324: export TESTBED_REAL_ORCH_USER=root
325: export TESTBED_REAL_ORCH_PASS='...'
326: ```
327: 
328: Opcionalmente:
329: 
330: ```bash
331: export TESTBED_REAL_ORCH_URL=http://101.44.24.91:8000/RPC2
332: ```
333: 
334: Flujos disponibles:
335: 
336: ```bash
337: # Levantar VMs y dejarlas integradas con el orquestador real
338: python3 testbed/scripts/launch-testbed.py up-real
339: 
340: # Si las VMs ya están levantadas, solo sincronizar la integración
341: python3 testbed/scripts/launch-testbed.py sync-real
342: 
343: # Entrar por SSH a una VM integrada
344: python3 testbed/scripts/launch-testbed.py ssh pa
345: 
346: # Apagar el laboratorio
347: python3 testbed/scripts/launch-testbed.py down
348: ```
349: 
350: Atajos equivalentes con `make`:
351: 
352: ```bash
353: make testbed-up-real TESTBED_REAL_ORCH_PASS='...'
354: make testbed-sync-real TESTBED_REAL_ORCH_PASS='...'
355: make testbed-down
356: make qemu-status-real TESTBED_REAL_ORCH_PASS='...'
357: ```
358: 
359: Para validar automáticamente la integración real de extremo a extremo:
360: 
361: ```bash
362: make topology-test-all-real TESTBED_REAL_ORCH_PASS='...'
363: ```
364: 
365: Ese target hace:
366: 
367: - corre las pruebas unitarias/simuladas de topologías
368: - levanta el testbed integrado con el orquestador real
369: - valida que `qemu-orq`, `qemu-pa` y `qemu-pb` aparezcan en el orquestador real
370: - valida handshakes y ping entre `qemu-pa` y `qemu-pb`
371: - desmonta el laboratorio al final
372: 
373: Si solo quieres un resumen operativo del laboratorio integrado:
374: 
375: ```bash
376: make qemu-status-real TESTBED_REAL_ORCH_PASS='...'
377: ```
378: 
379: Ese comando muestra:
380: 
381: - estado de las VMs QEMU
382: - estado de `wg-auto-register` en `orq`, `pa` y `pb`
383: - `peer-list` del orquestador real
384: - `wg show wg-HUB` en el HUB real
385: 
386: ## Reporte automático de rendimiento
387: 
388: Para regenerar `docs/reporte-rendimiento-conectividad.md` con una nueva corrida de métricas:
389: 
390: ```bash
391: make performance-report TESTBED_REAL_ORCH_PASS='...'
392: ```
393: 
394: Para forzar una corrida completa por topología incluyendo el bloque QEMU integrado:
395: 
396: ```bash
397: make performance-report-all-real TESTBED_REAL_ORCH_PASS='...'
398: ```
399: 
400: El generador:
401: 
402: - consulta el orquestador real
403: - mide pruebas separadas por `hub-spoke`, `mesh` y `hub-mesh`
404: - mide pings entre peers reales
405: - si el testbed está levantado o se fuerza `--ensure-qemu-real`, mide también QEMU integrado
406: - mide throughput HTTP sobre WireGuard entre peers reales y QEMU
407: - reescribe `docs/reporte-rendimiento-conectividad.md`
408: 
409: Además mantiene un historial acumulado en:
410: 
411: ```text
412: docs/reporte-rendimiento-historial.md
413: ```
414: 
415: Qué hace `up-real`:
416: 
417: - levanta las VMs del testbed
418: - provisiona red base dentro de cada VM
419: - crea o recicla usuarios/tokens en el orquestador real para:
420:   - `qemu-orq`
421:   - `qemu-pa`
422:   - `qemu-pb`
423: - instala `peer-install-v2` en las 3 VMs
424: - configura `peer.env` para que todas apunten a `101.44.24.91`
425: 
426: Comprobación rápida desde el orquestador real:
427: 
428: ```bash
429: ssh root@101.44.24.91
430: source /etc/linkguard/secrets
431: orch-cli peer-list --admin-token "$ADMIN_TOKEN"
432: ```
433: 
434: Deberías ver los peers `qemu-orq`, `qemu-pa` y `qemu-pb` además de los peers reales.

(End of file - total 434 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/natalia/Documents/Releasev4/orchestrator-install-v2/orchestrator/__init__.py"
}
```

**Output:**
```
<path>/home/natalia/Documents/Releasev4/orchestrator-install-v2/orchestrator/__init__.py</path>
<type>file</type>
<content>
1: """
2: LinkGuard Orchestrator v4 - Paquete modular.
3: Punto de entrada unico: main()
4: Servidor XML-RPC en /RPC2, compatible con orch-cli.py y hub-agent.py.
5: """
6: 
7: import defusedxml.xmlrpc
8: defusedxml.xmlrpc.monkey_patch()  # nosec B411
9: 
10: import threading
11: from typing import Any, Dict
12: from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler  # nosec B411
13: from socketserver import ThreadingMixIn
14: from xmlrpc.client import Fault  # nosec B411
15: 
16: from . import config, state, auth
17: 
18: 
19: # Thread-local storage for HTTP request context
20: _rpc_context = threading.local()
21: 
22: 
23: class _Handler(SimpleXMLRPCRequestHandler):
24:     rpc_paths = ("/RPC2",)
25: 
26:     def do_POST(self):
27:         _rpc_context.client_address = self.client_address
28:         try:
29:             return super().do_POST()
30:         finally:
31:             _rpc_context.client_address = None
32: 
33: 
34: class _Server(ThreadingMixIn, SimpleXMLRPCServer):
35:     daemon_threads = True
36:     allow_reuse_address = True
37: 
38: 
39: def _safe_call(handler, params: dict) -> Any:
40:     try:
41:         return handler(params)
42:     except PermissionError as e:
43:         raise Fault(1, f"403: {e}")
44:     except KeyError as e:
45:         raise Fault(1, f"404: {e}")
46:     except ValueError as e:
47:         raise Fault(1, f"400: {e}")
48:     except RuntimeError as e:
49:         raise Fault(1, f"503: {e}")
50: 
51: 
52: # Cada wrapper XML-RPC recibe *args posicionales segun el contrato original
53: # y construye un dict para el handler modular.
54: 
55: def _xml_login(*args) -> dict:
56:     user_id, peer_id, user_token = args[0], args[1] if len(args) > 1 else None, args[2] if len(args) > 2 else ""
57:     scopes = args[3] if len(args) > 3 else ["*"]
58:     ttl = args[4] if len(args) > 4 else config.JWT_TTL_DEFAULT
59:     if not user_id or not user_token:
60:         raise ValueError("user_id and user_token required")
61:     auth._check_user_token(user_id, user_token)
62:     token, exp = auth._jwt_encode({
63:         "user_id": user_id, "peer_id": peer_id,
64:         "scopes": scopes, "role": "user",
65:     }, ttl)
66:     return {"jwt": token, "expires_at": exp}
67: 
68: 
69: def _xml_refresh(*args) -> dict:
70:     jwt_token = args[0] if args else ""
71:     ttl = args[1] if len(args) > 1 else config.JWT_TTL_DEFAULT
72:     payload = auth._jwt_decode(jwt_token)
73:     jti = str(payload.get("jti") or "")
74:     if jti and auth._is_revoked_jti(jti):
75:         raise PermissionError("jwt revoked")
76:     token, exp = auth._jwt_encode({
77:         "role": payload.get("role", "user"), "user_id": payload.get("user_id"),
78:         "peer_id": payload.get("peer_id"), "scopes": payload.get("scopes") or [],
79:     }, ttl)
80:     return {"jwt": token, "expires_at": exp}
81: 
82: 
83: def _xml_whoami(*args) -> dict:
84:     p = auth._jwt_decode(args[0] if args else "")
85:     for k in ("iat", "nbf", "exp"):
86:         p.pop(k, None)
87:     return p
88: 
89: 
90: def _xml_health(*args) -> dict:
91:     from .endpoints_orch import rpc_health
92:     return _safe_call(rpc_health, {})
93: 
94: 
95: def _xml_metrics(*args) -> dict:
96:     from .endpoints_orch import rpc_metrics
97:     token = args[0] if args else None
98:     return _safe_call(rpc_metrics, {"token": token})
99: 
100: 
101: def _xml_events(*args) -> dict:
102:     from .endpoints_orch import rpc_events
103:     return _safe_call(rpc_events, {})
104: 
105: 
106: def _xml_user_create(*args) -> dict:
107:     # CLI convention: (user_id, admin_token) — 2 args
108:     # Test convention: (user_id, max_peers, max_networks, metadata, admin_token) — 5 args
109:     if len(args) >= 5:
110:         admin_token = args[4]
111:         max_peers = args[1]
112:         max_networks = args[2]
113:         metadata = args[3]
114:     elif len(args) >= 2:
115:         admin_token = args[1]
116:         max_peers = config.DEFAULT_MAX_PEERS
117:         max_networks = config.DEFAULT_MAX_NETWORKS
118:         metadata = {}
119:     else:
120:         admin_token = None
121:         max_peers = config.DEFAULT_MAX_PEERS
122:         max_networks = config.DEFAULT_MAX_NETWORKS
123:         metadata = {}
124:     auth.orch_check_admin_token(admin_token)
125:     from .endpoints_users import rpc_user_create
126:     return _safe_call(rpc_user_create, {
127:         "user_id": args[0] if args else "",
128:         "max_peers": max_peers,
129:         "max_networks": max_networks,
130:         "metadata": metadata,
131:     })
132: 
133: 
134: def _xml_user_list(*args) -> dict:
135:     auth.orch_check_admin_token(args[0] if args else None)
136:     from .endpoints_users import rpc_user_list
137:     return _safe_call(rpc_user_list, {})
138: 
139: 
140: def _xml_user_get(*args) -> dict:
141:     auth.orch_check_admin_token(args[1] if len(args) > 1 else None)
142:     user_id = args[0] if args else ""
143:     if not user_id:
144:         raise ValueError("user_id required")
145:     u = auth._get_user(user_id)
146:     return {"user_id": user_id, **u}
147: 
148: 
149: def _xml_user_delete(*args) -> dict:
150:     auth.orch_check_admin_token(args[1] if len(args) > 1 else None)
151:     from .endpoints_users import rpc_user_delete
152:     return _safe_call(rpc_user_delete, {"user_id": args[0] if args else ""})
153: 
154: 
155: def _xml_issue_user_token(*args) -> dict:
156:     auth.orch_check_admin_token(args[1] if len(args) > 1 else None)
157:     user_id = args[0] if args else ""
158:     if not user_id:
159:         raise ValueError("user_id required")
160:     tok = auth._issue_user_token(user_id)
161:     state.persist()
162:     state.add_event("user.issue_token", {"user_id": user_id})
163:     return {"user_id": user_id, "token": tok}
164: 
165: 
166: def _xml_revoke(*args) -> dict:
167:     auth.orch_check_admin_token(args[2] if len(args) > 2 else None)
168:     from .endpoints_auth import rpc_jwt_revoke
169:     return _safe_call(rpc_jwt_revoke, {
170:         "token": args[0] if args else "",
171:         "reason": args[1] if len(args) > 1 else "manual revocation",
172:     })
173: 
174: 
175: def _xml_network_create(*args) -> dict:
176:     admin_token = args[5] if len(args) > 5 else None
177:     if admin_token:
178:         auth.orch_check_admin_token(admin_token)
179:     from .endpoints_networks import rpc_network_create
180:     return _safe_call(rpc_network_create, {
181:         "net_id": args[0] if args else "",
182:         "cidr": args[1] if len(args) > 1 else "",
183:         "description": args[2] if len(args) > 2 else "",
184:         "tag": args[3] if len(args) > 3 else "",
185:         "user_id": args[4] if len(args) > 4 else "admin",
186:     })
187: 
188: 
189: def _xml_network_list(*args) -> dict:
190:     from .endpoints_networks import rpc_network_list
191:     return _safe_call(rpc_network_list, {})
192: 
193: 
194: def _xml_network_get(*args) -> dict:
195:     from .endpoints_networks import rpc_network_get
196:     return _safe_call(rpc_network_get, {"network_id": args[0] if args else ""})
197: 
198: 
199: def _xml_network_get_topology(*args) -> dict:
200:     from .endpoints_networks import rpc_network_get_topology
201:     return _safe_call(rpc_network_get_topology, {
202:         "network_id": args[0] if args else "",
203:         "admin_token": args[1] if len(args) > 1 else None,
204:         "token": args[2] if len(args) > 2 else None,
205:     })
206: 
207: 
208: def _xml_network_delete(*args) -> dict:
209:     from .endpoints_networks import rpc_network_delete
210:     return _safe_call(rpc_network_delete, {"network_id": args[0] if args else ""})
211: 
212: 
213: def _xml_network_set_topology(*args) -> dict:
214:     from .endpoints_networks import rpc_network_set_topology
215:     return _safe_call(rpc_network_set_topology, {
216:         "network_id": args[0] if args else "",
217:         "topology": args[1] if len(args) > 1 else "hub-spoke",
218:     })
219: 
220: 
221: def _xml_config_get_mesh_peers(*args) -> Any:
222:     from .endpoints_config import rpc_config_get_mesh_peers
223:     return _safe_call(rpc_config_get_mesh_peers, {
224:         "peer_id": args[0] if args else "",
225:         "network_id": args[1] if len(args) > 1 else "",
226:         "token": args[2] if len(args) > 2 else None,
227:     })
228: 
229: 
230: def _xml_config_get_peer_config(*args) -> Any:
231:     from .endpoints_config import rpc_config_get_peer_config
232:     return _safe_call(rpc_config_get_peer_config, {
233:         "peer_id": args[0] if args else "",
234:         "token": args[1] if len(args) > 1 else None,
235:     })
236: 
237: 
238: def _xml_peer_list(*args) -> dict:
239:     from .endpoints_peers import rpc_peer_list
240:     return _safe_call(rpc_peer_list, {})
241: 
242: 
243: def _xml_peer_register(*args) -> dict:
244:     from .endpoints_peers import rpc_peer_register
245:     return _safe_call(rpc_peer_register, {
246:         "peer_id": args[0] if args else "",
247:         "public_key": args[1] if len(args) > 1 else "",
248:         "endpoint": args[2] if len(args) > 2 else "",
249:         "tags": args[3] if len(args) > 3 else [],
250:         "metadata": args[4] if len(args) > 4 else {},
251:         "token": args[5] if len(args) > 5 else None,
252:     })
253: 
254: 
255: def _xml_peer_heartbeat(*args) -> dict:
256:     from .endpoints_peers import rpc_peer_heartbeat
257:     client_addr = getattr(_rpc_context, "client_address", None)
258:     remote_addr = client_addr[0] if client_addr else None
259:     return _safe_call(rpc_peer_heartbeat, {
260:         "peer_id": args[0] if args else "",
261:         "status": args[1] if len(args) > 1 else {},
262:         "token": args[2] if len(args) > 2 else None,
263:         "remote_addr": remote_addr,
264:     })
265: 
266: 
267: def _xml_peer_request_network(*args) -> dict:
268:     from .endpoints_peers import rpc_peer_request_network
269:     return _safe_call(rpc_peer_request_network, {
270:         "peer_id": args[0] if args else "",
271:         "network_id": args[1] if len(args) > 1 else "",
272:         "token": args[2] if len(args) > 2 else None,
273:     })
274: 
275: 
276: def _xml_peer_rotate_key(*args) -> dict:
277:     from .endpoints_peers import rpc_peer_rotate_key
278:     return _safe_call(rpc_peer_rotate_key, {
279:         "peer_id": args[0] if args else "",
280:         "public_key": args[1] if len(args) > 1 else "",
281:         "token": args[2] if len(args) > 2 else None,
282:     })
283: 
284: 
285: def _xml_peer_report_reachability(*args) -> dict:
286:     from .endpoints_peers import rpc_peer_report_reachability
287:     return _safe_call(rpc_peer_report_reachability, {
288:         "peer_id": args[0] if args else "",
289:         "target_peer_id": args[1] if len(args) > 1 else "",
290:         "reachable": args[2] if len(args) > 2 else False,
291:         "token": args[3] if len(args) > 3 else None,
292:     })
293: 
294: 
295: def _xml_peer_get(*args) -> dict:
296:     from .endpoints_peers import rpc_peer_get
297:     return _safe_call(rpc_peer_get, {"peer_id": args[0] if args else ""})
298: 
299: 
300: def _xml_peer_update_admin(*args) -> bool:
301:     auth.orch_check_admin_token(args[2] if len(args) > 2 else None)
302:     from .endpoints_peers import rpc_peer_update_admin
303:     return _safe_call(rpc_peer_update_admin, {
304:         "peer_id": args[0] if args else "",
305:         "fields": args[1] if len(args) > 1 else {},
306:     })
307: 
308: 
309: def _xml_peer_unregister(*args) -> bool:
310:     admin_token = args[2] if len(args) > 2 else None
311:     if admin_token:
312:         auth.orch_check_admin_token(admin_token)
313:     from .endpoints_peers import rpc_peer_unregister
314:     return _safe_call(rpc_peer_unregister, {
315:         "peer_id": args[0] if args else "",
316:         "token": args[1] if len(args) > 1 else None,
317:         "admin_token": admin_token or None,
318:     })
319: 
320: 
321: def _xml_peer_assign_network(*args) -> bool:
322:     auth.orch_check_admin_token(args[4] if len(args) > 4 else None)
323:     from .endpoints_peers import rpc_peer_assign_network
324:     return _safe_call(rpc_peer_assign_network, {
325:         "peer_id": args[0] if args else "",
326:         "network_id": args[1] if len(args) > 1 else "",
327:         "ip": args[2] if len(args) > 2 else "",
328:         "role": args[3] if len(args) > 3 else None,
329:     })
330: 
331: 
332: def _xml_peer_remove_from_network(*args) -> bool:
333:     auth.orch_check_admin_token(args[2] if len(args) > 2 else None)
334:     from .endpoints_peers import rpc_peer_remove_from_network
335:     return _safe_call(rpc_peer_remove_from_network, {
336:         "peer_id": args[0] if args else "",
337:         "network_id": args[1] if len(args) > 1 else "",
338:     })
339: 
340: 
341: def _register_xml_handlers(server) -> None:
342:     mapping: list[tuple[str, Any]] = [
343:         ("auth.login", _xml_login),
344:         ("auth.refresh", _xml_refresh),
345:         ("auth.whoami", _xml_whoami),
346:         ("orch.health", _xml_health),
347:         ("orch.metrics", _xml_metrics),
348:         ("orch.events", _xml_events),
349:         ("orch.user-create", _xml_user_create),
350:         ("orch.user-list", _xml_user_list),
351:         ("orch.user-get", _xml_user_get),
352:         ("orch.user-delete", _xml_user_delete),
353:         ("orch.issue-user-token", _xml_issue_user_token),
354:         ("orch.revoke", _xml_revoke),
355:         ("network.create", _xml_network_create),
356:         ("network.list", _xml_network_list),
357:         ("network.get", _xml_network_get),
358:         ("network.get_topology", _xml_network_get_topology),
359:         ("network.delete", _xml_network_delete),
360:         ("network.set_topology", _xml_network_set_topology),
361:         ("config.get_mesh_peers", _xml_config_get_mesh_peers),
362:         ("config.get_peer_config", _xml_config_get_peer_config),
363:         ("peer.list", _xml_peer_list),
364:         ("peer.register", _xml_peer_register),
365:         ("peer.get", _xml_peer_get),
366:         ("peer.heartbeat", _xml_peer_heartbeat),
367:         ("peer.request_network", _xml_peer_request_network),
368:         ("peer.rotate_key", _xml_peer_rotate_key),
369:         ("peer.report_reachability", _xml_peer_report_reachability),
370:         ("peer.update_admin", _xml_peer_update_admin),
371:         ("peer.unregister", _xml_peer_unregister),
372:         ("peer.assign_network", _xml_peer_assign_network),
373:         ("peer.remove_from_network", _xml_peer_remove_from_network),
374:     ]
375:     for name, fn in mapping:
376:         server.register_function(fn, name)
377:     config.log(f"Registrados {len(mapping)} handlers XML-RPC")
378: 
379: 
380: def main() -> None:
381:     config.check_dependencies()
382:     config.validate_tokens_at_startup()
383: 
384:     state.load_state()
385: 
386:     from .hub_client import hub_ping
387:     if hub_ping():
388:         config.log("Conexion con hub-agent: OK")
389:     else:
390:         config.log("ADVERTENCIA: hub-agent no responde")
391: 
392:     state.start_backup_loop()
393: 
394:     server = _Server(
395:         (config.ORCH_BIND, config.ORCH_PORT),
396:         requestHandler=_Handler,
397:         allow_none=True, logRequests=False,
398:     )
399:     _register_xml_handlers(server)
400: 
401:     config.log(f"Orchestrator listo en {config.ORCH_BIND}:{config.ORCH_PORT}/RPC2")
402:     config.log(f"Auto-approve: {'ACTIVADO' if config.AUTO_APPROVE_ENABLED else 'DESACTIVADO'}")
403: 
404:     try:
405:         server.serve_forever()
406:     except KeyboardInterrupt:
407:         config.log("Apagando...")
408:         state.persist()
409:         server.server_close()
410: 
411: 
412: if __name__ == "__main__":
413:     main()

(End of file - total 413 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/natalia/Documents/Releasev4/peer-install-v2/peer_register/__init__.py"
}
```

**Output:**
```
<path>/home/natalia/Documents/Releasev4/peer-install-v2/peer_register/__init__.py</path>
<type>file</type>
<content>
1: """
2: LinkGuard Peer Auto-Register v4 - Paquete modular.
3: Punto de entrada: main()
4: """
5: 
6: import argparse
7: import os
8: 
9: from . import config as cfg
10: from .commands import cmd_register, cmd_heartbeat, cmd_run, cmd_request_network, cmd_rotate_key
11: 
12: 
13: def main() -> None:
14:     ap = argparse.ArgumentParser(description="Peer auto-register + heartbeat + JWT session + multi-network")
15:     sub = ap.add_subparsers(dest="cmd")
16: 
17:     p_reg = sub.add_parser("register")
18:     p_reg.set_defaults(func=cmd_register)
19: 
20:     p_hb = sub.add_parser("heartbeat")
21:     p_hb.set_defaults(func=cmd_heartbeat)
22: 
23:     p_run = sub.add_parser("run", help="Daemon: register + heartbeat en loop")
24:     p_run.add_argument("--interval", type=int, default=cfg.WG_HEARTBEAT_INTERVAL, help="segundos entre heartbeats")
25:     p_run.add_argument("--session", default=os.getenv("WG_SESSION", "default"), help="session id (default)")
26:     p_run.set_defaults(func=cmd_run)
27: 
28:     p_req = sub.add_parser("request-network")
29:     p_req.add_argument("network_id")
30:     p_req.add_argument("--apply", action="store_true")
31:     p_req.set_defaults(func=cmd_request_network)
32: 
33:     p_rot = sub.add_parser("rotate-key")
34:     p_rot.set_defaults(func=cmd_rotate_key)
35: 
36:     args = ap.parse_args()
37:     if not getattr(args, "cmd", None):
38:         ap.error("the following arguments are required: cmd")
39:     args.func(args)
40: 
41: 
42: if __name__ == "__main__":
43:     main()

(End of file - total 43 lines)
</content>
```

---

## Assistant (Build · Qwen3.7 Plus · 11.5s)

_Thinking:_

Let me read more key files to understand the full architecture.


**Tool: read**

**Input:**
```json
{
  "filePath": "/home/natalia/Documents/Releasev4/orchestrator-install-v2/hub-agent.py",
  "limit": 100
}
```

**Output:**
```
<path>/home/natalia/Documents/Releasev4/orchestrator-install-v2/hub-agent.py</path>
<type>file</type>
<content>
1: #!/usr/bin/env python3
2: # -*- coding: utf-8 -*-
3: 
4: """
5: LinkGuard / TLB-WG Hub Agent - v3
6: 
7: Cambios v1 → v2:
8:   SEC-01:  Validación de token al arranque; rechaza arrancar con 'changeme' o vacío
9:   HA-02:   Soporte opcional TLS en el servidor XML-RPC (HUB_AGENT_TLS=1)
10:   HA-03:   HUB_AGENT_BIND por defecto 127.0.0.1 (no expuesto a toda la red)
11:   OPS-01:  Script de cleanup de reglas iptables (hub_cleanup_rules) llamado en PreStop
12:   OPS-02:  Verificación de dependencias (wg, wg-quick, iptables, sysctl) al arranque
13: 
14: Cambios v2 → v3 (Hub-Mesh):
15:   HM-F5a:  HUB_MESH_MODE: bool → enum 'off'|'mesh'|'hub-mesh' (compat '0'/'1' mantenida)
16:   HM-F5b:  hub_apply_peer bifurca comportamiento por HUB_MESH_MODE enum
17:   HM-F5c:  ensure_base_rules_internal: log explícito cuando relay hub-mesh está activo
18: """
19: 
20: import defusedxml.xmlrpc
21: 
22: defusedxml.xmlrpc.monkey_patch()
23: 
24: import ipaddress
25: import os
26: import secrets
27: import shutil
28: import ssl
29: import subprocess  # nosec B404
30: import time
31: from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler  # nosec B411
32: 
33: # =========================
34: # CONFIGURACIÓN
35: # =========================
36: 
37: HUB_WG_IFACE      = os.getenv("HUB_WG_IFACE", "wg-HUB")
38: WG_BIN            = os.getenv("WG_BIN", "/usr/bin/wg")
39: WG_QUICK          = os.getenv("WG_QUICK", "/usr/bin/wg-quick")
40: IPTABLES_BIN      = os.getenv("IPTABLES_BIN", "/sbin/iptables")
41: SYSCTL_BIN        = os.getenv("SYSCTL_BIN", "/sbin/sysctl")
42: 
43: # HA-03: bind por defecto a 127.0.0.1 (no 0.0.0.0)
44: HUB_AGENT_BIND    = os.getenv("HUB_AGENT_BIND", "127.0.0.1")
45: _HUB_AGENT_PORT_STR = os.getenv("HUB_AGENT_PORT", "9000")
46: try:
47:     HUB_AGENT_PORT = int(_HUB_AGENT_PORT_STR)
48: except ValueError:
49:     raise SystemExit(
50:         f"[hub-agent] ERROR: HUB_AGENT_PORT no es un entero válido: '{_HUB_AGENT_PORT_STR}'"
51:     )
52: if not (1 <= HUB_AGENT_PORT <= 65535):
53:     raise SystemExit(
54:         f"[hub-agent] ERROR: HUB_AGENT_PORT fuera de rango (1-65535): {HUB_AGENT_PORT}"
55:     )
56: 
57: # HA-02: TLS opcional
58: HUB_AGENT_TLS     = os.getenv("HUB_AGENT_TLS", "0") == "1"
59: HUB_AGENT_CERT    = os.getenv("HUB_AGENT_CERT", "/etc/linkguard/hub-agent.crt")
60: HUB_AGENT_KEY     = os.getenv("HUB_AGENT_KEY", "/etc/linkguard/hub-agent.key")
61: 
62: HUB_TUNNEL_IP     = os.getenv("HUB_TUNNEL_IP", "10.20.30.1/24")
63: _HUB_LISTEN_PORT_STR = os.getenv("HUB_LISTEN_PORT", "51820")
64: try:
65:     HUB_LISTEN_PORT = int(_HUB_LISTEN_PORT_STR)
66: except ValueError:
67:     raise SystemExit(
68:         f"[hub-agent] ERROR: HUB_LISTEN_PORT no es un entero válido: '{_HUB_LISTEN_PORT_STR}'"
69:     )
70: if not (1 <= HUB_LISTEN_PORT <= 65535):
71:     raise SystemExit(
72:         f"[hub-agent] ERROR: HUB_LISTEN_PORT fuera de rango (1-65535): {HUB_LISTEN_PORT}"
73:     )
74: WG_DIR            = os.getenv("WG_DIR", "/etc/wireguard")
75: HUB_CONF_PATH     = os.getenv("HUB_CONF_PATH", f"{WG_DIR}/{HUB_WG_IFACE}.conf")
76: HUB_PRIVKEY_PATH  = os.getenv("HUB_PRIVKEY_PATH", f"{WG_DIR}/{HUB_WG_IFACE}.key")
77: HUB_PUBKEY_PATH   = os.getenv("HUB_PUBKEY_PATH", f"{WG_DIR}/{HUB_WG_IFACE}.pub")
78: 
79: HUB_ENABLE_NAT    = os.getenv("HUB_ENABLE_NAT", "1") == "1"
80: HUB_NAT_OUT_IFACE = os.getenv("HUB_NAT_OUT_IFACE", "eth0")
81: TUNNEL_CIDR       = os.getenv("HUB_TUNNEL_CIDR", "10.20.30.0/24")
82: 
83: # HM-F5a: HUB_MESH_MODE extendido a enum 'off'|'mesh'|'hub-mesh'
84: # Compatibilidad v3: '0' → 'off', '1' → 'mesh'
85: _HUB_MESH_RAW = os.getenv("HUB_MESH_MODE", "off").strip().lower()
86: _HUB_MESH_COMPAT = {"0": "off", "1": "mesh"}
87: HUB_MESH_MODE = _HUB_MESH_COMPAT.get(_HUB_MESH_RAW, _HUB_MESH_RAW)
88: if HUB_MESH_MODE not in ("off", "mesh", "hub-mesh"):
89:     raise SystemExit(
90:         f"[hub-agent] ERROR: HUB_MESH_MODE inválido: '{HUB_MESH_MODE}'. "
91:         "Valores válidos: off | mesh | hub-mesh"
92:     )
93: 
94: # HUB_MESH_RELAY: en hub-mesh el HUB mantiene NAT/MASQUERADE para tráfico relay de peers
95: HUB_MESH_RELAY    = os.getenv("HUB_MESH_RELAY", "1") == "1"
96: 
97: # SEC-01: Token requerido; no puede ser vacío ni inseguro
98: HUB_AGENT_TOKEN   = os.getenv("HUB_AGENT_TOKEN", "")
99: 
100: # Valores inseguros que se rechazan al arrancar

(Showing lines 1-100 of 488. Use offset=101 to continue.)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/natalia/Documents/Releasev4/peer-install-v2/peer_register/commands.py",
  "limit": 120
}
```

**Output:**
```
<path>/home/natalia/Documents/Releasev4/peer-install-v2/peer_register/commands.py</path>
<type>file</type>
<content>
1: """
2: Comandos CLI: register, heartbeat, run, request-network, rotate-key.
3: """
4: 
5: import os
6: import subprocess
7: import time
8: from xmlrpc.client import Fault
9: 
10: from . import config as cfg
11: from .keys import gen_keys_if_needed, load_public_key, rotate_keys
12: from .identity import peer_id_default, peer_endpoint_guess, owner_default
13: from .state import load_state, save_state
14: from .auth import orch_token_for_call, ensure_jwt_session
15: from .nat import detect_nat_type
16: from .probe import probe_direct_peers
17: from .config_gen import apply_config
18: from .utils import log, run, rpc
19: 
20: 
21: def cmd_register(_args) -> None:
22:     gen_keys_if_needed()
23:     peer_id = peer_id_default()
24:     pub = load_public_key()
25: 
26:     tags = [x.strip() for x in (os.getenv("PEER_TAGS", "")).split(",") if x.strip()]
27:     metadata = {"owner": owner_default()}
28: 
29:     endpoint = os.getenv("PEER_ENDPOINT", "") or peer_endpoint_guess()
30: 
31:     log(f"Conectando a orchestrator en {cfg.ORCH_URL}")
32:     c = rpc()
33: 
34:     token = orch_token_for_call(peer_id)
35:     resp = c.__getattr__("peer.register")(peer_id, pub, endpoint, tags, metadata, token)
36:     log(f"peer.register -> {resp}")
37: 
38:     st = load_state()
39:     st["peer_id"] = resp["peer_id"]
40:     st["config_version"] = resp.get("config_version", 1)
41:     save_state(st)
42: 
43:     apply_config(peer_id)
44:     run([cfg.WG_BIN, "show", cfg.WG_INTERFACE], check=False)
45: 
46: 
47: def cmd_heartbeat(_args) -> None:
48:     st = load_state()
49:     peer_id = st.get("peer_id") or peer_id_default()
50: 
51:     detected_endpoint = os.getenv("PEER_ENDPOINT", "") or peer_endpoint_guess()
52: 
53:     nat_cache_ts = int(st.get("nat_type_detected_ts", 0))
54:     if int(time.time()) - nat_cache_ts > 300:
55:         nat_type = detect_nat_type()
56:         st["nat_type"] = nat_type
57:         st["nat_type_detected_ts"] = int(time.time())
58:         save_state(st)
59:     else:
60:         nat_type = st.get("nat_type", "symmetric")
61: 
62:     status = {
63:         "ts":       int(time.time()),
64:         "wg":       run([cfg.WG_BIN, "show", cfg.WG_INTERFACE], check=False, capture=True)[:4000],
65:         "endpoint": detected_endpoint,
66:         "nat_type": nat_type,
67:     }
68: 
69:     c = rpc()
70:     token = ensure_jwt_session(peer_id, st)
71:     resp = c.__getattr__("peer.heartbeat")(peer_id, status, token)
72:     log(f"peer.heartbeat -> {resp}")
73: 
74:     desired_version = int(resp.get("desired_config_version", st.get("config_version", 1)))
75:     current_version = int(st.get("config_version", 1))
76:     current_mp_hash = st.get("mesh_peers_hash", "")
77:     topology        = st.get("topology", "hub-spoke")
78: 
79:     need_reapply = False
80: 
81:     if desired_version != current_version:
82:         log(f"Config version cambio {current_version} -> {desired_version}, reaplicando...")
83:         need_reapply = True
84: 
85:     if not need_reapply and topology in ("mesh", "hub-mesh"):
86:         new_mp_hash = resp.get("mesh_peers_hash", "") or resp.get("hub_mesh_peers_hash", "")
87:         if new_mp_hash and new_mp_hash != current_mp_hash:
88:             log(f"Lista de peers {topology} cambio (hash {current_mp_hash[:8]}->{new_mp_hash[:8]}), reaplicando...")
89:             need_reapply = True
90: 
91:     if need_reapply:
92:         apply_config(peer_id)
93:         st = load_state()
94:         st["config_version"] = desired_version
95:         save_state(st)
96: 
97:     if topology == "hub-mesh":
98:         st = load_state()
99:         probe_direct_peers(peer_id, st)
100:         save_state(st)
101: 
102: 
103: def cmd_run(args) -> None:
104:     interval = int(getattr(args, "interval", cfg.WG_HEARTBEAT_INTERVAL))
105: 
106:     try:
107:         log("Modo run: ejecutando register")
108:         cmd_register(args)
109:     except Exception as e:
110:         log(f"register fallo (continuaremos reintentando): {e}")
111: 
112:     while True:
113:         try:
114:             cmd_heartbeat(args)
115:         except Fault as f:
116:             log(f"heartbeat Fault: {f}")
117:         except Exception as e:
118:             log(f"heartbeat error: {e}")
119: 
120:         time.sleep(interval)

(Showing lines 1-120 of 148. Use offset=121 to continue.)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/natalia/Documents/Releasev4/peer-install-v2/peer_register/config_gen.py",
  "limit": 120
}
```

**Output:**
```
<path>/home/natalia/Documents/Releasev4/peer-install-v2/peer_register/config_gen.py</path>
<type>file</type>
<content>
1: """
2: Generacion y aplicacion de configuracion WireGuard.
3: Construye el .conf y sincroniza via wg syncconf.
4: """
5: 
6: import os
7: import subprocess
8: import tempfile
9: 
10: from . import config as cfg
11: from .keys import load_private_key
12: from .auth import orch_token_for_call
13: from .state import load_state, save_state
14: from .utils import log, run, rpc, write_file
15: 
16: 
17: def _fetch_config(peer_id: str) -> dict:
18:     c = rpc()
19:     token = orch_token_for_call(peer_id)
20:     return c.__getattr__("config.get_peer_config")(peer_id, token)
21: 
22: 
23: def _build_interface_block(d: dict) -> str:
24:     addr = d["interface"]["address"]
25:     mtu  = int(d["interface"].get("mtu", 1420))
26:     priv = load_private_key()
27:     listen_port = (os.getenv("WG_LISTEN_PORT", "") or "").strip()
28:     listen = f"ListenPort = {listen_port}\n" if listen_port and listen_port != "0" else ""
29:     return f"[Interface]\nAddress = {addr}\nPrivateKey = {priv}\nMTU = {mtu}\n{listen}"
30: 
31: 
32: def _build_hub_block(d: dict) -> str:
33:     hub_pub   = d["peer"]["public_key"]
34:     hub_ep    = d["peer"]["endpoint"]
35:     hub_aips  = d["peer"]["allowed_ips"]
36:     keepalive = int(d["peer"].get("persistent_keepalive", cfg.DEFAULT_KEEPALIVE))
37:     topology  = d.get("meta", {}).get("topology", "hub-spoke")
38:     label     = "relay de fallback" if topology == "hub-mesh" else "bootstrap"
39:     return (f"\n# HUB ({label})\n"
40:             f"[Peer]\nPublicKey = {hub_pub}\nEndpoint = {hub_ep}\n"
41:             f"AllowedIPs = {hub_aips}\nPersistentKeepalive = {keepalive}\n")
42: 
43: 
44: def _build_mesh_blocks(d: dict) -> str:
45:     keepalive = int(d["peer"].get("persistent_keepalive", cfg.DEFAULT_KEEPALIVE))
46:     mesh_peers = d.get("mesh_peers") or []
47:     if not mesh_peers:
48:         return ""
49:     log(f"Topologia mesh: generando {len(mesh_peers)} bloques [Peer] adicionales")
50:     result = ""
51:     for mp in mesh_peers:
52:         pid      = mp.get("peer_id", "?")
53:         mp_pub   = mp.get("public_key", "")
54:         mp_ep    = mp.get("endpoint")
55:         mp_ip    = mp.get("tunnel_ip", "")
56:         mp_alive = mp.get("alive", False)
57:         if not mp_pub or not mp_ip:
58:             continue
59:         result += f"\n# Peer directo: {pid} (alive={mp_alive})\n"
60:         result += f"[Peer]\nPublicKey = {mp_pub}\n"
61:         result += f"AllowedIPs = {mp_ip}/32\n"
62:         if mp_ep:
63:             result += f"Endpoint = {mp_ep}\n"
64:         result += f"PersistentKeepalive = {keepalive}\n"
65:         if not mp_alive:
66:             log(f"  {pid}: endpoint conocido pero peer no responde heartbeat aun (alive={mp_alive})")
67:     return result
68: 
69: 
70: def _build_hub_mesh_blocks(d: dict) -> str:
71:     keepalive = int(d["peer"].get("persistent_keepalive", cfg.DEFAULT_KEEPALIVE))
72:     direct_peers = d.get("hub_mesh_direct_peers") or []
73:     relay_peers  = d.get("hub_mesh_relay_peers") or []
74:     log(f"Topologia hub-mesh: {len(direct_peers)} directos, {len(relay_peers)} via relay HUB")
75:     result = ""
76: 
77:     for mp in direct_peers:
78:         pid    = mp.get("peer_id", "?")
79:         mp_pub = mp.get("public_key", "")
80:         mp_ep  = mp.get("endpoint")
81:         mp_ip  = mp.get("tunnel_ip", "")
82:         if not mp_pub or not mp_ip:
83:             continue
84:         result += f"\n# Directo: {pid}\n"
85:         result += f"[Peer]\nPublicKey = {mp_pub}\nEndpoint = {mp_ep}\n"
86:         result += f"AllowedIPs = {mp_ip}/32\nPersistentKeepalive = {keepalive}\n"
87: 
88:     for mp in relay_peers:
89:         pid      = mp.get("peer_id", "?")
90:         nat_type = mp.get("nat_type", "?")
91:         result += f"# Relay-via-HUB: {pid} (nat={nat_type}, sin bloque directo)\n"
92: 
93:     return result
94: 
95: 
96: def _save_state_metadata(d: dict, topology: str) -> None:
97:     st = load_state()
98:     st["topology"] = topology
99:     if topology == "hub-mesh":
100:         st["mesh_peers_hash"]           = d.get("meta", {}).get("hub_mesh_peers_hash", "")
101:         st["hub_mesh_direct_candidates"] = d.get("hub_mesh_direct_peers") or []
102:     else:
103:         st["mesh_peers_hash"]           = d.get("meta", {}).get("mesh_peers_hash", "")
104:         st["hub_mesh_direct_candidates"] = []
105:     save_state(st)
106: 
107: 
108: def _sync_wg() -> None:
109:     if subprocess.run(["/sbin/ip", "link", "show", cfg.WG_INTERFACE],
110:                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
111:         strip_out = subprocess.check_output([cfg.WG_QUICK, "strip", cfg.WG_INTERFACE], universal_newlines=True)  # nosec B603
112:         tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False)
113:         tmp.write(strip_out)
114:         tmp.close()
115:         subprocess.run([cfg.WG_BIN, "syncconf", cfg.WG_INTERFACE, tmp.name], check=True)  # nosec B603
116:         os.unlink(tmp.name)
117:     else:
118:         run([cfg.WG_QUICK, "up", cfg.WG_INTERFACE], check=True)
119: 
120: 

(Showing lines 1-120 of 139. Use offset=121 to continue.)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/natalia/Documents/Releasev4/orchestrator-install-v2/orchestrator/endpoints_peers.py",
  "limit": 120
}
```

**Output:**
```
<path>/home/natalia/Documents/Releasev4/orchestrator-install-v2/orchestrator/endpoints_peers.py</path>
<type>file</type>
<content>
1: """
2: Endpoints RPC de gestion de peers WireGuard.
3: """
4: 
5: import json
6: import secrets
7: from typing import Any, Dict
8: 
9: from . import config, state, auth, hub_client, network_alloc, auto_approve
10: 
11: 
12: def _extract_owner_id(params: Dict[str, Any]) -> str:
13:     user_id = params.get("user_id") or params.get("owner") or params.get("tenant") or "default"
14:     return str(user_id)
15: 
16: 
17: def _require_peer_jwt(token: Any, peer_id: str, needed_scope: str) -> str:
18:     auth_mode, uid, scopes, is_admin_jwt = auth._auth_from_token(token)
19:     if auth_mode != "jwt":
20:         raise PermissionError("authentication required: provide a valid JWT")
21:     auth._require_scope(scopes, needed_scope)
22:     user_id = str(uid or "")
23:     if not is_admin_jwt and peer_id:
24:         with state.LOCK_PEERS:
25:             peer = state.STATE["peers"].get(peer_id)
26:         if peer and str(peer.get("user_id") or "default") != user_id:
27:             raise PermissionError("cross-tenant forbidden")
28:     return user_id
29: 
30: 
31: def _mesh_hash(payload: Any) -> str:
32:     return secrets.token_hex(0) or json.dumps(payload, sort_keys=True)
33: 
34: 
35: def rpc_peer_create(params: Dict[str, Any]) -> Dict[str, Any]:
36:     public_key = str(params.get("public_key") or "")
37:     if not public_key:
38:         raise ValueError("public_key is required")
39:     user_id = _extract_owner_id(params)
40: 
41:     if user_id != "admin":
42:         auth._check_peer_quota(user_id)
43: 
44:     try_auto = auto_approve.try_auto_approve(public_key, params.get("metadata"))
45:     if try_auto:
46:         return try_auto
47: 
48:     peer_id = params.get("peer_id") or ("p_" + secrets.token_hex(8))
49:     net_id = str(params.get("network") or "") or config.DEFAULT_NET_ID
50: 
51:     ip = network_alloc._assign_ip_to_peer_in_network(peer_id, net_id)
52:     if not ip:
53:         raise RuntimeError(f"No hay IP disponible en {net_id}")
54: 
55:     peer = {
56:         "public_key": public_key,
57:         "ip": ip,
58:         "networks": [net_id],
59:         "user_id": user_id,
60:         "metadata": params.get("metadata", {}),
61:         "enabled": True,
62:         "created_ts": state.now_ts(),
63:         "keepalive": int(params.get("keepalive", config.MESH_DEFAULT_KEEPALIVE)),
64:     }
65: 
66:     with state.LOCK_NETWORKS:
67:         net = state.STATE["networks"].get(net_id)
68:         if net:
69:             network_alloc._ensure_network_alloc_struct(net)
70:             net["alloc"]["assigned"][peer_id] = ip
71:             state.STATE["networks"][net_id] = net
72: 
73:     with state.LOCK_PEERS:
74:         state.STATE["peers"][peer_id] = peer
75:         state.persist()
76:     state.add_event("peer_created", {"peer_id": peer_id, "public_key": public_key[:16], "user_id": user_id})
77:     config.log(f"Peer creado: {peer_id}")
78:     hub_client._hub_apply_peer_allowed_ips(peer_id)
79:     return {"peer_id": peer_id, "ip": ip, "network": net_id}
80: 
81: 
82: def rpc_peer_register(params: Dict[str, Any]) -> Dict[str, Any]:
83:     token = params.get("token")
84:     peer_id = str(params.get("peer_id") or "")
85:     public_key = str(params.get("public_key") or "")
86:     endpoint = str(params.get("endpoint") or "")
87:     tags = params.get("tags") or []
88:     metadata = params.get("metadata") or {}
89:     if not peer_id:
90:         raise ValueError("peer_id is required")
91:     if not public_key:
92:         raise ValueError("public_key is required")
93:     user_id = _require_peer_jwt(token, "", "peer:write")
94:     metadata = dict(metadata) if isinstance(metadata, dict) else {}
95:     metadata.setdefault("owner", user_id)
96: 
97:     with state.LOCK_PEERS:
98:         peer = state.STATE["peers"].get(peer_id)
99: 
100:     if peer:
101:         if str(peer.get("user_id") or "default") != user_id:
102:             raise PermissionError("cross-tenant forbidden")
103:         with state.LOCK_PEERS:
104:             peer = state.STATE["peers"][peer_id]
105:             peer["public_key"] = public_key
106:             peer["enabled"] = True
107:             peer["metadata"] = metadata
108:             if endpoint:
109:                 peer["endpoint"] = endpoint
110:             if tags:
111:                 peer["tags"] = tags
112:             state.STATE["peers"][peer_id] = peer
113:         state.bump_config_version_locked()
114:         state.persist()
115:         hub_client._hub_apply_peer_allowed_ips(peer_id)
116:         state.add_event("peer.register", {"peer_id": peer_id, "user_id": user_id, "existing": True})
117:         return {
118:             "peer_id": peer_id,
119:             "wg_ip": f"{peer.get('ip')}/32",
120:             "config_version": int(state.STATE.get("config_version", 1)),

(Showing lines 1-120 of 519. Use offset=121 to continue.)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/natalia/Documents/Releasev4/orchestrator-install-v2/orchestrator/endpoints_config.py",
  "limit": 120
}
```

**Output:**
```
<path>/home/natalia/Documents/Releasev4/orchestrator-install-v2/orchestrator/endpoints_config.py</path>
<type>file</type>
<content>
1: """
2: Endpoints RPC de configuracion y mantenimiento.
3: """
4: 
5: import hashlib
6: import json
7: from typing import Any, Dict
8: 
9: from . import config, state
10: 
11: 
12: def rpc_config_get(params: Dict[str, Any]) -> Dict[str, Any]:
13:     return {"config_version": state.STATE.get("config_version"), "state_version": state.STATE.get("version")}
14: 
15: 
16: def rpc_config_get_peer_config(params: Dict[str, Any]) -> Dict[str, Any]:
17:     from . import auth as auth_mod, hub_client
18: 
19:     peer_id = str(params.get("peer_id") or "")
20:     token = params.get("token")
21:     auth_mode, uid, scopes, is_admin_jwt = auth_mod._auth_from_token(token)
22:     if auth_mode != "jwt":
23:         raise PermissionError("authentication required: provide a valid JWT")
24:     auth_mod._require_scope(scopes, "config:read")
25:     if not is_admin_jwt:
26:         auth_mod._enforce_tenant_for_peer(str(uid or ""), peer_id)
27: 
28:     with state.LOCK_PEERS:
29:         peer = state.STATE["peers"].get(peer_id)
30:     if not peer:
31:         raise KeyError("peer not found")
32:     network_ids = list(peer.get("networks") or [])
33:     if not network_ids:
34:         raise RuntimeError("peer has no assigned network")
35:     network_id = network_ids[0]
36:     with state.LOCK_NETWORKS:
37:         network = state.STATE["networks"].get(network_id)
38:     if not network:
39:         raise KeyError("network not found")
40: 
41:     topology = str(network.get("topology") or "hub-spoke")
42:     keepalive = int(peer.get("keepalive") or config.MESH_DEFAULT_KEEPALIVE)
43:     response = {
44:         "interface": {
45:             "address": f"{peer.get('ip')}/32",
46:             "mtu": config.WG_MTU,
47:         },
48:         "peer": {
49:             "public_key": hub_client._hub_call_with_retry("hub.public_key", config.HUB_AGENT_TOKEN),
50:             "endpoint": config.HUB_ENDPOINT,
51:             "allowed_ips": network.get("hub_mesh_relay_fallback_cidr") or network.get("cidr"),
52:             "persistent_keepalive": keepalive,
53:         },
54:         "meta": {
55:             "topology": topology,
56:             "config_version": int(state.STATE.get("config_version", 1)),
57:             "requester_nat_type": peer.get("nat_type", "unknown") if topology == "hub-mesh" else None,
58:         },
59:     }
60: 
61:     if topology == "mesh":
62:         mesh_peers = _get_alive_mesh_peers(peer_id, network_id)
63:         response["mesh_peers"] = mesh_peers
64:         response["meta"]["mesh_peers_hash"] = hashlib.sha256(
65:             json.dumps(mesh_peers, sort_keys=True).encode()
66:         ).hexdigest()
67:     elif topology == "hub-mesh":
68:         classified = _classify_peers_for_hub_mesh(peer_id, network_id)
69:         response["hub_mesh_direct_peers"] = classified["direct"]
70:         response["hub_mesh_relay_peers"] = classified["relay_only"]
71:         response["peer"]["allowed_ips"] = classified.get("relay_cidr") or network.get("cidr")
72:         response["meta"]["hub_mesh_peers_hash"] = hashlib.sha256(
73:             json.dumps(classified, sort_keys=True).encode()
74:         ).hexdigest()
75: 
76:     return response
77: 
78: 
79: def rpc_config_reload(params: Dict[str, Any]) -> Dict[str, Any]:
80:     from importlib import reload
81:     reload(config)
82:     config.log("Recarga de configuracion solicitada via RPC")
83:     return {"reloaded": True}
84: 
85: 
86: def rpc_state_reset(params: Dict[str, Any]) -> Dict[str, Any]:
87:     confirm = str(params.get("confirm", ""))
88:     if confirm != "RESET":
89:         raise ValueError("must pass confirm=RESET")
90:     from .state import DEFAULT_STATE, load_state, persist
91:     with state.LOCK_STATE:
92:         state.STATE.update(json.loads(json.dumps(DEFAULT_STATE)))
93:         persist()
94:     state.add_event("state_reset", {"trigger": "rpc_state_reset"})
95:     return {"reset": True}
96: 
97: 
98: def _get_alive_mesh_peers(requester_peer_id: str, network_id: str) -> list:
99:     now = state.now_ts()
100:     with state.LOCK_NETWORKS:
101:         n = state.STATE["networks"].get(network_id)
102:     if not n:
103:         return []
104:     assigned = (n.get("alloc") or {}).get("assigned") or {}
105:     result = []
106:     with state.LOCK_PEERS:
107:         for pid, tunnel_ip in assigned.items():
108:             if pid == requester_peer_id:
109:                 continue
110:             p = state.STATE["peers"].get(pid)
111:             if not p:
112:                 continue
113:             last_hb = int(p.get("last_heartbeat") or 0)
114:             alive = last_hb > 0 and (now - last_hb) <= config.HEARTBEAT_TTL_SEC
115:             result.append({
116:                 "peer_id": pid, "public_key": p.get("public_key") or "",
117:                 "endpoint": p.get("endpoint"), "tunnel_ip": tunnel_ip,
118:                 "alive": alive, "last_seen_ts": last_hb,
119:             })
120:     result.sort(key=lambda x: (not x["alive"], x["peer_id"]))

(Showing lines 1-120 of 200. Use offset=121 to continue.)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/natalia/Documents/Releasev4/orchestrator-install-v2/orchestrator/network_alloc.py",
  "limit": 80
}
```

**Output:**
```
<path>/home/natalia/Documents/Releasev4/orchestrator-install-v2/orchestrator/network_alloc.py</path>
<type>file</type>
<content>
1: """
2: Helpers de asignacion de IPs dentro de redes WireGuard.
3: """
4: 
5: import ipaddress
6: from typing import Optional, List
7: 
8: from . import config, state
9: 
10: 
11: def _allocate_ip_in_network(net_cidr: str, existing_ips: List[str]) -> Optional[str]:
12:     try:
13:         net = ipaddress.ip_network(net_cidr, strict=False)
14:     except Exception:
15:         return None
16:     used = set()
17:     for ip_str in existing_ips:
18:         try:
19:             used.add(ipaddress.ip_address(ip_str.split("/")[0]))
20:         except ValueError:
21:             pass
22:     # La primera IP util (.1) queda reservada para el HUB de WireGuard.
23:     for ip_int in range(int(net.network_address) + 2, int(net.broadcast_address)):
24:         ip = ipaddress.ip_address(ip_int)
25:         if ip not in used:
26:             return str(ip)
27:     return None
28: 
29: 
30: def _ensure_network_alloc_struct(n: dict) -> None:
31:     if "alloc" not in n or not isinstance(n["alloc"], dict):
32:         n["alloc"] = {"reserved": [], "assigned": {}}
33:     n["alloc"].setdefault("reserved", [])
34:     n["alloc"].setdefault("assigned", {})
35: 
36: 
37: def _network_release_ip(network_id: str, peer_id: str) -> None:
38:     with state.LOCK_NETWORKS:
39:         n = state.STATE["networks"].get(network_id)
40:         if not n:
41:             return
42:         _ensure_network_alloc_struct(n)
43:         released = n["alloc"]["assigned"].pop(peer_id, None)
44:         if released:
45:             state.STATE["networks"][network_id] = n
46:             config.log(f"IP {released} devuelta al pool de red '{network_id}'")
47: 
48: 
49: def _assign_ip_to_peer_in_network(peer_id: str, net_id: str) -> Optional[str]:
50:     with state.LOCK_NETWORKS:
51:         net = state.STATE["networks"].get(net_id)
52:         if not net:
53:             return None
54:         net_cidr = net.get("cidr", net.get("ip", ""))
55:     existing = []
56:     with state.LOCK_PEERS:
57:         for pid, p in state.STATE["peers"].items():
58:             if net_id in (p.get("networks") or []) and p.get("ip"):
59:                 existing.append(p["ip"])
60:         peer = state.STATE["peers"].get(peer_id)
61:         if peer and peer.get("ip") and net_id in (peer.get("networks") or []):
62:             return peer["ip"]
63:     ip = _allocate_ip_in_network(net_cidr, existing)
64:     if ip:
65:         config.log(f"Asignada IP {ip} a peer {peer_id} en red {net_id}")
66:     return ip

(End of file - total 66 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/natalia/Documents/Releasev4/orchestrator-install-v2/orchestrator/state.py",
  "limit": 100
}
```

**Output:**
```
<path>/home/natalia/Documents/Releasev4/orchestrator-install-v2/orchestrator/state.py</path>
<type>file</type>
<content>
1: """
2: Estado persistente del Orchestrator.
3: STATE, locks, persistencia, backup automatico y eventos.
4: """
5: 
6: import json
7: import os
8: import time
9: import threading
10: 
11: from . import config
12: 
13: 
14: # Locks granulares — orden: USERS > NETWORKS > PEERS > EVENTS (nunca invertir)
15: LOCK_PEERS = threading.RLock()
16: LOCK_NETWORKS = threading.RLock()
17: LOCK_USERS = threading.RLock()
18: LOCK_EVENTS = threading.RLock()
19: LOCK_STATE = threading.RLock()
20: LOCK_REVOKED = threading.RLock()
21: 
22: 
23: def now_ts() -> int:
24:     return int(time.time())
25: 
26: 
27: def ensure_dir(path: str) -> None:
28:     d = os.path.dirname(path)
29:     if d:
30:         os.makedirs(d, exist_ok=True)
31: 
32: 
33: def load_json(path: str) -> dict:
34:     try:
35:         with open(path, "r") as f:
36:             return json.load(f)
37:     except Exception:
38:         return {}
39: 
40: 
41: def save_json(path: str, data: dict) -> None:
42:     ensure_dir(path)
43:     tmp = path + ".tmp"
44:     with open(tmp, "w") as f:
45:         json.dump(data, f, indent=2, sort_keys=True)
46:     os.replace(tmp, path)
47: 
48: 
49: DEFAULT_STATE = {
50:     "version": 4,
51:     "config_version": 1,
52:     "users": {},
53:     "peers": {},
54:     "networks": {},
55:     "events": [],
56: }
57: 
58: STATE: dict = {}
59: 
60: 
61: def _append_event_to_log(ev: dict) -> None:
62:     try:
63:         ensure_dir(config.EVENTS_LOG_PATH)
64:         with open(config.EVENTS_LOG_PATH, "a") as f:
65:             f.write(json.dumps(ev, sort_keys=True) + "\n")
66:     except Exception as e:
67:         config.log(f"WARNING: No pude escribir evento en log: {e}")
68: 
69: 
70: def add_event(kind: str, detail: dict) -> None:
71:     ev = {"ts": now_ts(), "kind": kind, "detail": detail}
72:     _append_event_to_log(ev)
73:     with LOCK_EVENTS:
74:         STATE["events"].append(ev)
75:         if len(STATE["events"]) > config.EVENTS_IN_STATE_MAX:
76:             STATE["events"] = STATE["events"][-config.EVENTS_IN_STATE_MAX:]
77: 
78: 
79: def _do_backup() -> None:
80:     if not config.BACKUP_ENABLED:
81:         return
82:     try:
83:         os.makedirs(config.BACKUP_DIR, exist_ok=True)
84:         ts = time.strftime("%Y%m%dT%H%M%S")
85:         backup_path = os.path.join(config.BACKUP_DIR, f"state-{ts}.json")
86:         with LOCK_STATE:
87:             save_json(backup_path, STATE)
88:         backups = sorted([f for f in os.listdir(config.BACKUP_DIR)
89:                           if f.startswith("state-") and f.endswith(".json")])
90:         for old in backups[:-config.BACKUP_MAX_KEEP]:
91:             try:
92:                 os.remove(os.path.join(config.BACKUP_DIR, old))
93:             except OSError:
94:                 pass
95:         config.log(f"Backup guardado: {backup_path}")
96:     except Exception as e:
97:         config.log(f"WARNING: Backup fallo: {e}")
98: 
99: 
100: def _backup_loop() -> None:

(Showing lines 1-100 of 134. Use offset=101 to continue.)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/natalia/Documents/Releasev4/orchestrator-install-v2/orchestrator/auth.py",
  "limit": 100
}
```

**Output:**
```
<path>/home/natalia/Documents/Releasev4/orchestrator-install-v2/orchestrator/auth.py</path>
<type>file</type>
<content>
1: """
2: Autenticacion y autorizacion.
3: JWT, tokens de usuario, scopes, cuotas multi-tenant y helpers de auth.
4: """
5: 
6: import hashlib
7: import secrets
8: import threading
9: from typing import Dict, Any, Optional, List, Tuple
10: 
11: import jwt as pyjwt
12: 
13: from . import config, state
14: 
15: 
16: # JWT secret recargable sin reinicio
17: _JWT_SECRET_HASH: Optional[str] = None
18: _JWT_SECRET_VALUE: Optional[str] = None
19: _JWT_SECRET_LOCK = threading.Lock()
20: 
21: 
22: def _read_jwt_secret() -> str:
23:     global _JWT_SECRET_HASH, _JWT_SECRET_VALUE
24:     try:
25:         with open(config.JWT_SECRET_PATH, "r") as f:
26:             s = f.read().strip()
27:         if not s:
28:             raise RuntimeError("JWT secret vacio")
29:         file_hash = hashlib.sha256(s.encode()).hexdigest()
30:         with _JWT_SECRET_LOCK:
31:             if file_hash != _JWT_SECRET_HASH:
32:                 _JWT_SECRET_HASH = file_hash
33:                 _JWT_SECRET_VALUE = s
34:                 config.log("JWT secret recargado (hash cambio)")
35:             assert _JWT_SECRET_VALUE is not None
36:             return _JWT_SECRET_VALUE
37:     except FileNotFoundError:
38:         raise RuntimeError(
39:             f"JWT secret no existe: {config.JWT_SECRET_PATH}. "
40:             "Crea con: openssl rand -hex 32 > {config.JWT_SECRET_PATH} && chmod 600 {config.JWT_SECRET_PATH}"
41:         )
42:     except Exception as e:
43:         raise RuntimeError(f"No pude leer JWT secret: {e}")
44: 
45: 
46: def _jwt_encode(payload: Dict[str, Any], ttl_seconds: int) -> Tuple[str, int]:
47:     ttl = int(ttl_seconds) if ttl_seconds else config.JWT_TTL_DEFAULT
48:     if ttl <= 0:
49:         ttl = config.JWT_TTL_DEFAULT
50:     n = state.now_ts()
51:     exp = n + ttl
52:     full = dict(payload)
53:     full.update({
54:         "iss": config.JWT_ISSUER, "aud": config.JWT_AUDIENCE,
55:         "iat": n, "nbf": n, "exp": exp,
56:         "jti": secrets.token_hex(12),
57:     })
58:     token = pyjwt.encode(full, _read_jwt_secret(), algorithm="HS256")
59:     return token, exp
60: 
61: 
62: def _jwt_decode(token: str) -> Dict[str, Any]:
63:     return pyjwt.decode(
64:         token, _read_jwt_secret(), algorithms=["HS256"],
65:         audience=config.JWT_AUDIENCE, issuer=config.JWT_ISSUER,
66:         options={"require": ["exp", "iat", "nbf", "iss", "aud", "jti"]},
67:     )
68: 
69: 
70: def _is_probably_jwt(token: str) -> bool:
71:     return isinstance(token, str) and token.count(".") == 2 and len(token) > 30
72: 
73: 
74: # Revocacion JWT en archivo separado
75: _REVOKED_CACHE: Optional[Dict[str, Any]] = None
76: 
77: 
78: def _load_revoked() -> Dict[str, Any]:
79:     global _REVOKED_CACHE
80:     if _REVOKED_CACHE is not None:
81:         return _REVOKED_CACHE
82:     data = state.load_json(config.JWT_REVOKED_PATH)
83:     _REVOKED_CACHE = data if isinstance(data, dict) else {}
84:     return _REVOKED_CACHE
85: 
86: 
87: def _save_revoked(rev: Dict[str, Any]) -> None:
88:     global _REVOKED_CACHE
89:     state.save_json(config.JWT_REVOKED_PATH, rev)
90:     _REVOKED_CACHE = rev
91: 
92: 
93: def _is_revoked_jti(jti: str) -> bool:
94:     with state.LOCK_REVOKED:
95:         return jti in _load_revoked()
96: 
97: 
98: def _revoke_jti(jti: str, reason: str, exp: Optional[int] = None) -> None:
99:     with state.LOCK_REVOKED:
100:         rev = _load_revoked()

(Showing lines 1-100 of 245. Use offset=101 to continue.)
</content>
```

---

## Assistant (Build · Qwen3.7 Plus · 544.0s)

_Thinking:_

Let me also look at some remaining key files to get a complete picture.

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/natalia/Documents/Releasev4/orchestrator-install-v2/orchestrator/hub_client.py",
  "limit": 80
}
```

**Output:**
```
<path>/home/natalia/Documents/Releasev4/orchestrator-install-v2/orchestrator/hub_client.py</path>
<type>file</type>
<content>
1: """
2: Cliente RPC hacia hub-agent via XML-RPC.
3: Llamadas al hub-agent en /RPC2 y helpers de allowed IPs.
4: """
5: 
6: import ipaddress
7: import time
8: import xmlrpc.client  # nosec B411
9: from typing import Optional, Dict, Any, List
10: from xmlrpc.client import ServerProxy  # nosec B411
11: 
12: from . import config, state
13: 
14: 
15: def get_hub_client() -> ServerProxy:
16:     return ServerProxy(config.HUB_AGENT_URL, allow_none=True)
17: 
18: 
19: def _hub_call_with_retry(method: str, *args) -> Any:
20:     last_exc = None
21:     for attempt in range(config.HUB_RETRY_COUNT):
22:         try:
23:             c = get_hub_client()
24:             return getattr(c, method)(*args)
25:         except Exception as e:
26:             last_exc = e
27:             if attempt < config.HUB_RETRY_COUNT - 1:
28:                 delay = config.HUB_RETRY_DELAY * (2 ** attempt)
29:                 config.log(f"hub-agent '{method}' fallo (intento {attempt+1}/{config.HUB_RETRY_COUNT}): {e}. Reintentando en {delay:.1f}s...")
30:                 time.sleep(delay)
31:     raise RuntimeError(f"hub-agent '{method}' fallo tras {config.HUB_RETRY_COUNT} intentos: {last_exc}")
32: 
33: 
34: def hub_apply_peer(pub: str, allowed_ips_csv: str, endpoint: str = "") -> bool:
35:     return bool(_hub_call_with_retry("hub.apply_peer", config.HUB_AGENT_TOKEN, pub, allowed_ips_csv, endpoint))
36: 
37: 
38: def hub_remove_peer(pub: str) -> bool:
39:     return bool(_hub_call_with_retry("hub.remove_peer", config.HUB_AGENT_TOKEN, pub))
40: 
41: 
42: def hub_ping() -> bool:
43:     try:
44:         return _hub_call_with_retry("hub.health", config.HUB_AGENT_TOKEN) in {"ok", "pong"}
45:     except Exception:
46:         return False
47: 
48: 
49: def _peer_all_allowed_ips(peer: Dict[str, Any]) -> List[str]:
50:     ips = []
51:     peer_ip = str(peer.get("ip") or "").strip()
52:     if peer_ip:
53:         ips.append(config.WG_PEER_ALLOWED_FMT.replace("{ip}", peer_ip.split("/")[0]))
54:     return ips
55: 
56: 
57: def _is_public_endpoint(ep: str) -> bool:
58:     if not ep:
59:         return False
60:     host = ep.rsplit(":", 1)[0].strip("[]")
61:     try:
62:         ip = ipaddress.ip_address(host)
63:         return ip.is_global
64:     except ValueError:
65:         return True
66: 
67: 
68: def _get_wg_endpoint(pub_key: str) -> str:
69:     """Retrieve the real WG-learned endpoint (with correct NAT port) from the hub's WireGuard interface."""
70:     try:
71:         peers = _hub_call_with_retry("hub.list_mesh_peers", config.HUB_AGENT_TOKEN, "")
72:     except Exception:
73:         return ""
74:     for p in peers:
75:         if p.get("public_key") == pub_key:
76:             ep = p.get("endpoint")
77:             if ep:
78:                 return ep
79:     return ""
80: 

(Showing lines 1-80 of 107. Use offset=81 to continue.)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/natalia/Documents/Releasev4/peer-install-v2/peer_register/nat.py",
  "limit": 80
}
```

**Output:**
```
<path>/home/natalia/Documents/Releasev4/peer-install-v2/peer_register/nat.py</path>
<type>file</type>
<content>
1: """
2: Deteccion heuristica del tipo de NAT del peer.
3: 
4: Clasificaciones:
5:   none        - IP publica directa (sin NAT)
6:   full-cone   - mismo puerto externo se mantiene (hole-punch posible)
7:   symmetric   - puerto diferente por destino (relay obligatorio)
8: """
9: 
10: import os
11: import socket
12: 
13: from .identity import _get_local_ip
14: 
15: 
16: def detect_nat_type() -> str:
17:     pub_env = os.getenv("PUBLIC_IP", "").strip()
18:     listen_port = int(os.getenv("WG_LISTEN_PORT", "0") or "0")
19: 
20:     if not pub_env:
21:         return "symmetric"
22: 
23:     try:
24:         local_ip = _get_local_ip()
25:         if not local_ip:
26:             return "symmetric"
27:     except Exception:
28:         return "symmetric"
29: 
30:     if pub_env == local_ip:
31:         return "none"
32: 
33:     if listen_port == 0:
34:         return "symmetric"
35: 
36:     try:
37:         s1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
38:         s1.bind(("", listen_port))
39:         s1.connect(("8.8.8.8", 53))
40:         port1 = s1.getsockname()[1]
41:         s1.close()
42:         s2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
43:         s2.bind(("", listen_port))
44:         s2.connect(("1.1.1.1", 53))
45:         port2 = s2.getsockname()[1]
46:         s2.close()
47:         return "full-cone" if port1 == port2 else "symmetric"
48:     except Exception:
49:         return "symmetric"

(End of file - total 49 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/natalia/Documents/Releasev4/peer-install-v2/peer_register/probe.py",
  "limit": 80
}
```

**Output:**
```
<path>/home/natalia/Documents/Releasev4/peer-install-v2/peer_register/probe.py</path>
<type>file</type>
<content>
1: """
2: Monitoreo de handshakes WireGuard para peers directos (hub-mesh).
3: Reporta cambios de alcanzabilidad al orquestador.
4: """
5: 
6: import subprocess
7: import time
8: 
9: from . import config as cfg
10: from .state import save_state
11: from .auth import ensure_jwt_session
12: from .utils import log, rpc
13: 
14: 
15: def probe_direct_peers(peer_id: str, st: dict) -> None:
16:     if st.get("topology") != "hub-mesh":
17:         return
18:     candidates = st.get("hub_mesh_direct_candidates") or []
19:     if not candidates:
20:         return
21: 
22:     try:
23:         out = subprocess.check_output(
24:             [cfg.WG_BIN, "show", cfg.WG_INTERFACE, "latest-handshakes"], universal_newlines=True  # nosec B603
25:         )
26:     except Exception:
27:         return
28: 
29:     now = int(time.time())
30:     handshakes: dict = {}
31:     for line in out.strip().splitlines():
32:         parts = line.split()
33:         if len(parts) == 2:
34:             try:
35:                 handshakes[parts[0]] = int(parts[1])
36:             except ValueError:
37:                 pass
38: 
39:     prev = st.get("direct_handshake_map") or {}
40:     c = rpc()
41:     token = ensure_jwt_session(peer_id, st)
42:     changed = False
43: 
44:     for mp in candidates:
45:         pub = mp.get("public_key", "")
46:         pid = mp.get("peer_id", "")
47:         if not pub or not pid:
48:             continue
49:         hs = handshakes.get(pub, 0)
50:         alive_now = hs > 0 and (now - hs) <= 180
51:         was_alive = bool(prev.get(pub, False))
52: 
53:         if alive_now != was_alive:
54:             try:
55:                 c.__getattr__("peer.report_reachability")(peer_id, pid, alive_now, token)
56:                 log(f"Reachability {pid}: {'directo' if alive_now else 'relay'}")
57:             except Exception as e:
58:                 log(f"report_reachability error ({pid}): {e}")
59:         prev[pub] = alive_now
60:         changed = True
61: 
62:     if changed:
63:         st["direct_handshake_map"] = prev

(End of file - total 63 lines)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/natalia/Documents/Releasev4/orchestrator-install-v2/orch-cli.py",
  "limit": 80
}
```

**Output:**
```
<path>/home/natalia/Documents/Releasev4/orchestrator-install-v2/orch-cli.py</path>
<type>file</type>
<content>
1: #!/usr/bin/env python3
2: # -*- coding: utf-8 -*-
3: 
4: import os
5: import json
6: import argparse
7: from xmlrpc.client import ServerProxy
8: 
9: def client(url: str):
10:     return ServerProxy(url, allow_none=True)
11: 
12: def pretty(x):
13:     print(json.dumps(x, indent=2, sort_keys=True))
14: 
15: def main():
16:     # Parser compartido: --admin-token y --token disponibles en TODOS los subcomandos
17:     shared = argparse.ArgumentParser(add_help=False)
18:     shared.add_argument("--admin-token", default=os.getenv("ADMIN_TOKEN", ""),
19:                         help="ADMIN_TOKEN (required for admin-only ops)")
20:     shared.add_argument("--token", default=os.getenv("JWT", ""),
21:                         help="JWT de tenant (obtener con: orch-cli auth-login)")
22: 
23:     ap = argparse.ArgumentParser(description="Orchestrator Admin CLI (admin-only ops + tenant ops)",
24:                                  parents=[shared])
25:     ap.add_argument("--url", default=os.getenv("ORCH_URL", "http://127.0.0.1:8000/RPC2"))
26: 
27:     sub = ap.add_subparsers(dest="cmd", required=True)
28: 
29:     # core
30:     sub.add_parser("health")
31:     sub.add_parser("metrics")
32:     sub.add_parser("events")
33: 
34:     # users (admin-only)
35:     p_uc = sub.add_parser("user-create")
36:     p_uc.add_argument("user_id")
37: 
38:     sub.add_parser("user-list")
39: 
40:     p_ug = sub.add_parser("user-get")
41:     p_ug.add_argument("user_id")
42: 
43:     p_ud = sub.add_parser("user-delete")
44:     p_ud.add_argument("user_id")
45:     p_ud.add_argument("--purge", action="store_true")
46: 
47:     p_uit = sub.add_parser("issue-user-token")
48:     p_uit.add_argument("user_id")
49: 
50:     # auth
51:     p_al = sub.add_parser("auth-login", help="Obtener JWT con user_id + user_token")
52:     p_al.add_argument("user_id")
53:     p_al.add_argument("user_token")
54:     p_al.add_argument("--scopes", default="*", help="Scopes separados por coma (default: *)")
55:     p_al.add_argument("--ttl", type=int, default=None, help="TTL en segundos (default: server default)")
56: 
57:     p_ar = sub.add_parser("auth-refresh", help="Renovar JWT existente antes de que expire")
58:     p_ar.add_argument("jwt_token", nargs="?", default=None,
59:                       help="JWT a renovar (default: $JWT)")
60:     p_ar.add_argument("--ttl", type=int, default=None, help="TTL en segundos (default: server default)")
61: 
62:     sub.add_parser("auth-whoami", help="Decodificar el JWT actual y mostrar su payload")
63: 
64:     # revoke
65:     p_rev = sub.add_parser("revoke")
66:     p_rev.add_argument("jti")
67: 
68:     # networks (admin-only create/delete; list/get/topology readable with tenant JWT in other clients)
69:     p_nc = sub.add_parser("net-create")
70:     p_nc.add_argument("network_id")
71:     p_nc.add_argument("tunnel_cidr")
72:     p_nc.add_argument("--topology", default="hub-spoke")
73:     p_nc.add_argument("--hub-peer-id", default="HUB")
74:     p_nc.add_argument("--user-id", default=None)
75: 
76:     p_nl = sub.add_parser("net-list")
77:     p_nl.add_argument("--user-id", default=None)
78: 
79:     p_ng = sub.add_parser("net-get")
80:     p_ng.add_argument("network_id")

(Showing lines 1-80 of 327. Use offset=81 to continue.)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/natalia/Documents/Releasev4/peer-install-v2/wg-auto-cli.py",
  "limit": 80
}
```

**Output:**
```
<path>/home/natalia/Documents/Releasev4/peer-install-v2/wg-auto-cli.py</path>
<type>file</type>
<content>
1: #!/usr/bin/env python3
2: # -*- coding: utf-8 -*-
3: 
4: import argparse
5: import json
6: import os
7: import socket
8: import subprocess
9: import sys
10: from xmlrpc.client import ServerProxy
11: 
12: # ── Auto-cargar /etc/linkguard/peer.env si existe ──────────────────────────
13: _PEER_ENV_PATH = os.getenv("PEER_ENV_PATH", "/etc/linkguard/peer.env")
14: if os.path.isfile(_PEER_ENV_PATH):
15:     try:
16:         with open(_PEER_ENV_PATH) as _f:
17:             for _line in _f:
18:                 _line = _line.strip()
19:                 if not _line or _line.startswith("#") or "=" not in _line:
20:                     continue
21:                 _k, _, _v = _line.partition("=")
22:                 _k = _k.strip(); _v = _v.strip()
23:                 if _k and _v and _k not in os.environ:
24:                     os.environ[_k] = _v
25:     except PermissionError:
26:         pass
27: 
28: ORCH_URL = os.getenv("ORCH_URL", "http://127.0.0.1:8000/RPC2")
29: STATE_PATH = os.getenv("WG_AUTO_STATE", "/etc/wireguard/wg-auto.json")
30: ORCH_TOKEN = os.getenv("ORCH_TOKEN", "")
31: 
32: def log(msg: str) -> None:
33:     print(f"[wg-auto-cli] {msg}", flush=True)
34: 
35: def load_state() -> dict:
36:     if not os.path.exists(STATE_PATH):
37:         return {}
38:     try:
39:         with open(STATE_PATH, "r") as f:
40:             return json.load(f)
41:     except Exception:
42:         return {}
43: 
44: def get_peer_id() -> str:
45:     state = load_state()
46:     if "peer_id" in state:
47:         return state["peer_id"]
48:     return os.getenv("PEER_ID", socket.gethostname())
49: 
50: def get_auth_token() -> str:
51:     st = load_state()
52:     if st.get("jwt"):
53:         return st["jwt"]
54:     return ORCH_TOKEN
55: 
56: def get_client(url: str = "") -> ServerProxy:
57:     url = url or ORCH_URL
58:     log(f"Conectando a orchestrator en {url}")
59:     return ServerProxy(url, allow_none=True)
60: 
61: def print_json(obj) -> None:
62:     print(json.dumps(obj, indent=2, sort_keys=True))
63: 
64: def rpc_call(c, method: str, *args):
65:     """
66:     Intenta invocar con token al final.
67:     Si el método no acepta token, reintenta sin él.
68:     """
69:     tok = get_auth_token()
70:     fn = c.__getattr__(method)
71:     if tok:
72:         try:
73:             return fn(*args, tok)
74:         except TypeError:
75:             return fn(*args)
76:     return fn(*args)
77: 
78: # ============================================================
79: # WRAPPERS peer.local.* (usando JWT si existe)
80: # ============================================================

(Showing lines 1-80 of 336. Use offset=81 to continue.)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/natalia/Documents/Releasev4/testbed/scripts/launch-testbed.py",
  "limit": 80
}
```

**Output:**
```
<path>/home/natalia/Documents/Releasev4/testbed/scripts/launch-testbed.py</path>
<type>file</type>
<content>
1: #!/usr/bin/env python3
2: """
3: Lanza el testbed QEMU completo: bridges, VMs, provisioning, tests.
4: Requiere: sudo para bridges/taps, dnsmasq, sshpass.
5: 
6: Modo integrado opcional con orquestador real:
7:   - export TESTBED_REAL_ORCH_HOST=101.44.24.91
8:   - export TESTBED_REAL_ORCH_PASS=... 
9:   - python3 launch-testbed.py up-real
10: """
11: import json
12: import os, sys, subprocess, time, signal, atexit, tempfile, argparse
13: import xmlrpc.client
14: 
15: BDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
16: RAW  = os.path.join(BDIR, "images", "alpine-base.raw")
17: PID_DIR = os.path.join(BDIR, "pids")
18: SSH_KEY = os.path.join(BDIR, "ssh", "id_ed25519")
19: PASS    = "linkguard-test"
20: SSH_OPTS = ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null", "-o", "ConnectTimeout=5"]
21: REAL_ORCH_HOST = os.environ.get("TESTBED_REAL_ORCH_HOST", "101.44.24.91")
22: REAL_ORCH_USER = os.environ.get("TESTBED_REAL_ORCH_USER", "root")
23: REAL_ORCH_PASS = os.environ.get("TESTBED_REAL_ORCH_PASS", "")
24: REAL_ORCH_URL = os.environ.get("TESTBED_REAL_ORCH_URL", f"http://{REAL_ORCH_HOST}:8000/RPC2")
25: REAL_ORCH_PORT = os.environ.get("TESTBED_REAL_ORCH_PORT", "51820")
26: REAL_PEER_IDS = {"orq": "qemu-orq", "pa": "qemu-pa", "pb": "qemu-pb"}
27: PEER_BUNDLE_DIR = os.path.abspath(os.path.join(BDIR, "..", "peer-install-v2"))
28: _REAL_ADMIN_TOKEN = None
29: 
30: VMS = {
31:     "orq": {"macs": ["52:54:00:01:00:10","52:54:00:01:01:10","52:54:00:01:02:10"],
32:             "taps": ["tap0","tap1","tap2"], "ip": "192.168.100.10",
33:             "data_ip": "10.0.0.10", "img": "orq.raw"},
34:     "pa":  {"macs": ["52:54:00:01:00:20","52:54:00:01:01:20","52:54:00:01:02:20"],
35:             "taps": ["tap3","tap4","tap5"], "ip": "192.168.100.20",
36:             "data_ip": "10.0.0.20", "img": "pa.raw"},
37:     "pb":  {"macs": ["52:54:00:01:00:30","52:54:00:01:01:30","52:54:00:01:02:30"],
38:             "taps": ["tap6","tap7","tap8"], "ip": "192.168.100.30",
39:             "data_ip": "10.0.0.30", "img": "pb.raw"},
40: }
41: 
42: 
43: def sudo(cmd, input_pass=None, **kw):
44:     """Ejecuta comando con sudo, opcionalmente pasando password via stdin."""
45:     full = ["sudo", "-S"] + cmd if input_pass else ["sudo"] + cmd
46:     if input_pass:
47:         kw.setdefault("input", input_pass + "\n")
48:         kw.setdefault("text", True)
49:     kw.setdefault("check", True)
50:     subprocess.run(full, **kw)
51: 
52: 
53: def run(cmd, **kw):
54:     kw.setdefault("text", True)
55:     return subprocess.run(cmd, check=False, **kw)
56: 
57: 
58: def setup_network(passwd):
59:     log("Creando bridges y taps...")
60:     sudo(["bash", os.path.join(BDIR, "scripts", "setup-network.sh"), "create"],
61:          input_pass=passwd)
62: 
63:     # DHCP en br0 via dnsmasq (background)
64:     run(["pkill", "-f", "dnsmasq.*br0"])
65:     dnsmasq_cmd = [
66:         "dnsmasq", "--interface=br0", "--bind-interfaces",
67:         "--dhcp-range=192.168.100.100,192.168.100.200,12h",
68:         "--dhcp-host=52:54:00:01:00:10,192.168.100.10",
69:         "--dhcp-host=52:54:00:01:00:20,192.168.100.20",
70:         "--dhcp-host=52:54:00:01:00:30,192.168.100.30",
71:         "--domain=linkguard.test", "--no-resolv",
72:     ]
73:     # Start dnsmasq as background process with sudo
74:     subprocess.Popen(
75:         ["sudo", "-S"] + dnsmasq_cmd,
76:         stdin=subprocess.PIPE, text=True
77:     ).communicate(input=passwd + "\n")
78:     time.sleep(2)
79:     log("DHCP en br0 listo")
80: 

(Showing lines 1-80 of 325. Use offset=81 to continue.)
</content>
```

**Tool: read**

**Input:**
```json
{
  "filePath": "/home/natalia/Documents/Releasev4/Makefile",
  "limit": 80
}
```

**Output:**
```
<path>/home/natalia/Documents/Releasev4/Makefile</path>
<type>file</type>
<content>
1: .PHONY: test typecheck lint security syntax-check peer-test topology-test topology-test-all topology-test-ci topology-test-all-real testbed-up testbed-down testbed-up-real testbed-sync-real qemu-status-real performance-report performance-report-all-real uninstall uninstall-local
2: 
3: test:
4: 	python3 -m pytest orchestrator-install-v2/tests/ -v --tb=short
5: 
6: topology-test:
7: 	python3 -m pytest orchestrator-install-v2/tests/test_supported_topologies.py -v --tb=short
8: 	python3 -m pytest peer-install-v2/tests/test_supported_topologies.py -v --tb=short
9: 	python3 -m pytest peer-install-v2/tests/test_integration_mixed_nat_topologies.py -v --tb=short
10: 
11: topology-test-all: topology-test
12: 	python3 -m pytest testbed/tests/test_wireguard_integration.py -v --tb=short
13: 
14: topology-test-ci:
15: 	bash -lc 'set -e; status=0; python3 testbed/scripts/launch-testbed.py up || status=$$?; if [ $$status -eq 0 ]; then $(MAKE) topology-test-all || status=$$?; fi; python3 testbed/scripts/launch-testbed.py down || true; exit $$status'
16: 
17: topology-test-all-real:
18: 	@test -n "$(TESTBED_REAL_ORCH_PASS)" || (echo "TESTBED_REAL_ORCH_PASS is required" >&2; exit 1)
19: 	bash -lc 'set -e; status=0; $(MAKE) topology-test || status=$$?; if [ $$status -eq 0 ]; then $(MAKE) testbed-up-real TESTBED_REAL_ORCH_HOST="$(if $(TESTBED_REAL_ORCH_HOST),$(TESTBED_REAL_ORCH_HOST),101.44.24.91)" TESTBED_REAL_ORCH_USER="$(if $(TESTBED_REAL_ORCH_USER),$(TESTBED_REAL_ORCH_USER),root)" TESTBED_REAL_ORCH_PASS="$(TESTBED_REAL_ORCH_PASS)" TESTBED_REAL_ORCH_URL="$(if $(TESTBED_REAL_ORCH_URL),$(TESTBED_REAL_ORCH_URL),http://$(if $(TESTBED_REAL_ORCH_HOST),$(TESTBED_REAL_ORCH_HOST),101.44.24.91):8000/RPC2)" || status=$$?; fi; if [ $$status -eq 0 ]; then TESTBED_REAL_ORCH_URL="$(if $(TESTBED_REAL_ORCH_URL),$(TESTBED_REAL_ORCH_URL),http://$(if $(TESTBED_REAL_ORCH_HOST),$(TESTBED_REAL_ORCH_HOST),101.44.24.91):8000/RPC2)" python3 -m pytest testbed/tests/test_real_orchestrator_integration.py -v --tb=short || status=$$?; fi; $(MAKE) testbed-down || true; exit $$status'
20: 
21: testbed-up:
22: 	python3 testbed/scripts/launch-testbed.py up
23: 
24: testbed-down:
25: 	python3 testbed/scripts/launch-testbed.py down
26: 
27: testbed-up-real:
28: 	@test -n "$(TESTBED_REAL_ORCH_PASS)" || (echo "TESTBED_REAL_ORCH_PASS is required" >&2; exit 1)
29: 	TESTBED_REAL_ORCH_HOST="$(if $(TESTBED_REAL_ORCH_HOST),$(TESTBED_REAL_ORCH_HOST),101.44.24.91)" \
30: 	TESTBED_REAL_ORCH_USER="$(if $(TESTBED_REAL_ORCH_USER),$(TESTBED_REAL_ORCH_USER),root)" \
31: 	TESTBED_REAL_ORCH_PASS="$(TESTBED_REAL_ORCH_PASS)" \
32: 	TESTBED_REAL_ORCH_URL="$(if $(TESTBED_REAL_ORCH_URL),$(TESTBED_REAL_ORCH_URL),http://$(if $(TESTBED_REAL_ORCH_HOST),$(TESTBED_REAL_ORCH_HOST),101.44.24.91):8000/RPC2)" \
33: 	python3 testbed/scripts/launch-testbed.py up-real
34: 
35: testbed-sync-real:
36: 	@test -n "$(TESTBED_REAL_ORCH_PASS)" || (echo "TESTBED_REAL_ORCH_PASS is required" >&2; exit 1)
37: 	TESTBED_REAL_ORCH_HOST="$(if $(TESTBED_REAL_ORCH_HOST),$(TESTBED_REAL_ORCH_HOST),101.44.24.91)" \
38: 	TESTBED_REAL_ORCH_USER="$(if $(TESTBED_REAL_ORCH_USER),$(TESTBED_REAL_ORCH_USER),root)" \
39: 	TESTBED_REAL_ORCH_PASS="$(TESTBED_REAL_ORCH_PASS)" \
40: 	TESTBED_REAL_ORCH_URL="$(if $(TESTBED_REAL_ORCH_URL),$(TESTBED_REAL_ORCH_URL),http://$(if $(TESTBED_REAL_ORCH_HOST),$(TESTBED_REAL_ORCH_HOST),101.44.24.91):8000/RPC2)" \
41: 	python3 testbed/scripts/launch-testbed.py sync-real
42: 
43: qemu-status-real:
44: 	@test -n "$(TESTBED_REAL_ORCH_PASS)" || (echo "TESTBED_REAL_ORCH_PASS is required" >&2; exit 1)
45: 	python3 testbed/scripts/launch-testbed.py status
46: 	python3 testbed/scripts/launch-testbed.py ssh orq rc-service wg-auto-register status || true
47: 	python3 testbed/scripts/launch-testbed.py ssh pa rc-service wg-auto-register status || true
48: 	python3 testbed/scripts/launch-testbed.py ssh pb rc-service wg-auto-register status || true
49: 	sshpass -p "$(TESTBED_REAL_ORCH_PASS)" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null $(if $(TESTBED_REAL_ORCH_USER),$(TESTBED_REAL_ORCH_USER),root)@$(if $(TESTBED_REAL_ORCH_HOST),$(TESTBED_REAL_ORCH_HOST),101.44.24.91) 'source /etc/linkguard/secrets && orch-cli peer-list --admin-token "$$ADMIN_TOKEN" && wg show wg-HUB'
50: 
51: performance-report:
52: 	@test -n "$(LINKGUARD_REMOTE_PASS)$(TESTBED_REAL_ORCH_PASS)" || (echo "LINKGUARD_REMOTE_PASS or TESTBED_REAL_ORCH_PASS is required" >&2; exit 1)
53: 	LINKGUARD_REMOTE_PASS="$(if $(LINKGUARD_REMOTE_PASS),$(LINKGUARD_REMOTE_PASS),$(TESTBED_REAL_ORCH_PASS))" \
54: 	TESTBED_REAL_ORCH_HOST="$(if $(TESTBED_REAL_ORCH_HOST),$(TESTBED_REAL_ORCH_HOST),101.44.24.91)" \
55: 	TESTBED_REAL_ORCH_USER="$(if $(TESTBED_REAL_ORCH_USER),$(TESTBED_REAL_ORCH_USER),root)" \
56: 	python3 scripts/generate-performance-report.py
57: 
58: performance-report-all-real:
59: 	@test -n "$(LINKGUARD_REMOTE_PASS)$(TESTBED_REAL_ORCH_PASS)" || (echo "LINKGUARD_REMOTE_PASS or TESTBED_REAL_ORCH_PASS is required" >&2; exit 1)
60: 	LINKGUARD_REMOTE_PASS="$(if $(LINKGUARD_REMOTE_PASS),$(LINKGUARD_REMOTE_PASS),$(TESTBED_REAL_ORCH_PASS))" \
61: 	TESTBED_REAL_ORCH_HOST="$(if $(TESTBED_REAL_ORCH_HOST),$(TESTBED_REAL_ORCH_HOST),101.44.24.91)" \
62: 	TESTBED_REAL_ORCH_USER="$(if $(TESTBED_REAL_ORCH_USER),$(TESTBED_REAL_ORCH_USER),root)" \
63: 	TESTBED_REAL_ORCH_PASS="$(if $(TESTBED_REAL_ORCH_PASS),$(TESTBED_REAL_ORCH_PASS),$(LINKGUARD_REMOTE_PASS))" \
64: 	TESTBED_REAL_ORCH_URL="$(if $(TESTBED_REAL_ORCH_URL),$(TESTBED_REAL_ORCH_URL),http://$(if $(TESTBED_REAL_ORCH_HOST),$(TESTBED_REAL_ORCH_HOST),101.44.24.91):8000/RPC2)" \
65: 	python3 scripts/generate-performance-report.py --ensure-qemu-real --teardown-qemu
66: 
67: typecheck:
68: 	python3 -m mypy orchestrator-install-v2/orchestrator/ orchestrator-install-v2/hub-agent.py --ignore-missing-imports --allow-untyped-decorators
69: 	python3 -m mypy peer-install-v2/peer_register/ --ignore-missing-imports --allow-untyped-decorators
70: 
71: security:
72: 	python3 -m bandit -r orchestrator-install-v2/orchestrator/ orchestrator-install-v2/hub-agent.py peer-install-v2/peer_register/ -c .bandit
73: 
74: syntax-check:
75: 	python3 -m py_compile orchestrator-install-v2/orchestrator/__init__.py
76: 	python3 -m py_compile orchestrator-install-v2/orchestrator.py
77: 	python3 -m py_compile orchestrator-install-v2/hub-agent.py
78: 	python3 -m py_compile peer-install-v2/wg-auto-register.py
79: 	python3 -m py_compile peer-install-v2/peer_register/__init__.py
80: 	python3 -m py_compile scripts/generate-performance-report.py

(Showing lines 1-80 of 114. Use offset=81 to continue.)
</content>
```

---

## Assistant (Build · Qwen3.7 Plus · 26.0s)

_Thinking:_

Now I have a comprehensive understanding of the project. Let me synthesize this into a clear description.

## LinkGuard v4 — Implementation Overview

**LinkGuard** is a WireGuard VPN orchestration platform that automates peer registration, key management, IP allocation, and dynamic topology configuration across three network topologies: **hub-spoke**, **mesh**, and **hub-mesh**.

### Architecture (3 components)

**1. Orchestrator** (`orchestrator-install-v2/`)
- **`orchestrator/`** — Modular Python package exposing ~30 XML-RPC methods on `/RPC2` (threaded `SimpleXMLRPCServer`). Key modules:
  - `endpoints_peers.py` — peer registration, heartbeat, key rotation, reachability reporting, multi-tenant isolation
  - `endpoints_config.py` — generates per-peer WireGuard configs with topology-aware mesh/relay peer lists
  - `endpoints_networks.py` — network CRUD, topology switching
  - `endpoints_users.py` — multi-tenant user management with quotas
  - `auth.py` — JWT (HS256) issuance/refresh/revocation, scope-based authorization, tenant isolation
  - `state.py` — thread-safe in-memory state with JSON persistence, automatic backups, event log
  - `network_alloc.py` — CIDR-based IP allocation (`.1` reserved for hub)
  - `hub_client.py` — XML-RPC client to hub-agent with retry/backoff
  - `auto_approve.py` — pre-approved peer auto-registration
- **`hub-agent.py`** — Privileged daemon on the hub server managing the `wg-HUB` WireGuard interface. Handles `wg set` peer additions/removals, iptables NAT/MASQUERADE rules, and supports `off|mesh|hub-mesh` modes. Binds to `127.0.0.1:9000` with optional TLS.
- **`orch-cli.py`** — Admin CLI wrapping all XML-RPC calls with `--admin-token`/`--token` auth.

**2. Peer Agent** (`peer-install-v2/`)
- **`peer_register/`** — Modular package:
  - `commands.py` — `register`, `heartbeat`, `run` (daemon loop), `request-network`, `rotate-key`
  - `config_gen.py` — Builds WireGuard `.conf` files per topology: hub block + mesh peer blocks (with `/32` allowed IPs for direct peers, relay comments for unreachable peers in hub-mesh). Uses `wg syncconf` for hot-reload.
  - `nat.py` — Heuristic NAT detection (`none`/`full-cone`/`symmetric`) via UDP port comparison to two external IPs
  - `probe.py` — Monitors WireGuard latest-handshakes to detect direct connectivity changes and reports reachability to orchestrator
  - `auth.py` — JWT session management (login, refresh, token selection)
  - `keys.py` — WireGuard key generation/rotation
  - `identity.py` — Peer ID and endpoint auto-detection
  - `state.py` — Local state persistence (`/etc/wireguard/wg-auto.json`)
- **`wg-auto-cli.py`** — Local peer CLI for status, mesh-status, unregister, etc.

**3. Testbed** (`testbed/`)
- **`launch-testbed.py`** — Spins up 3 QEMU Alpine VMs (`orq`, `pa`, `pb`) on Linux bridges (`br0`/`br1`/`br2`) with TAP interfaces, DHCP via dnsmasq. Supports integration with the real orchestrator (`up-real`, `sync-real`).
- Integration tests for WireGuard and real orchestrator connectivity.

### Topology Logic

| Topology | Peer config | Hub role |
|---|---|---|
| **hub-spoke** | Single `[Peer]` block (the hub), all traffic via hub | Relay all peer-to-peer |
| **mesh** | N `[Peer]` blocks for all alive peers (direct `/32`) | Bootstrap only |
| **hub-mesh** | Direct `[Peer]` blocks for reachable peers + relay comments for NAT-blocked peers | Fallback relay for symmetric-NAT peers |

### Key Design Decisions
- **XML-RPC** for all control-plane communication (orchestrator ↔ hub-agent, orchestrator ↔ peers)
- **JWT auth** with scopes (`peer:write`, `config:read`, etc.), tenant isolation, and revocation
- **Config versioning** — peers detect version changes via heartbeat and hot-reload WireGuard config
- **Mesh peer hash** — SHA-256 hash of peer list lets peers detect membership changes without full config pulls
- **NAT-aware** — hub-mesh classifies peers as `DIRECT` or `RELAY` based on reported `nat_type` and reachability probes
- **Security** — `defusedxml` for XML-RPC, token validation at startup, state files with `600` permissions, no secrets in code

### Testing & CI
- Unit tests under each package's `tests/` directory (pytest)
- `make topology-test` — unit + simulated NAT topology tests
- `make topology-test-ci` — full CI: QEMU up → tests → QEMU down
- `make typecheck` (mypy), `make security` (bandit), `make lint`
- Performance report generation with real orchestrator + QEMU peers

---

