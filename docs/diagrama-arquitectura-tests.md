# Diagrama de arquitectura de todos los tests

Vista física y lógica del testbed de `tests-linkguard-aws`: orquestador/hub, 5 peers reales (3 AWS + VM40 + RPi5) y 3 VMs QEMU, con las tres topologías probadas (`hub-spoke`, `hub-mesh`, `mesh`) y el flujo de ejecución.

---

## 1. Infraestructura física del testbed

```mermaid
flowchart TD
    OP[Operador<br/>laptop local]

    subgraph AWS[AWS - Internet publico]
        ORCH["Orquestador / HUB<br/>34.193.139.170 (admin)<br/>wg-HUB :51820<br/>IP tunel 10.20.30.1<br/>API XML-RPC :8000/RPC2"]
        EC2A["peer-100-31-255-119<br/>54.210.49.136 (ubuntu)<br/>ecs-linkguard-0003"]
        EC2B["peer-34-207-174-76<br/>3.228.113.66 (ec2-user)<br/>ecs-linkguard-0002"]
        EC2C["peer-184-72-71-143<br/>98.87.229.24 (ec2-user)<br/>ecs-linkguard-0001"]
    end

    subgraph JUMP[Red local detras de jump host]
        JH["Jump host<br/>100.115.215.49 (root)<br/>acceso WAN"]
        VM40["peer-172-20-0-40<br/>VM Alpine 172.20.0.40 (root)<br/>openrc"]
        RPI5["peer-172-20-0-7<br/>RPi5 172.20.0.7 (natalia)<br/>systemd"]
    end

    subgraph QEMU[Host local - VMs QEMU sobre bridges]
        BR0["br0 192.168.100.0/24<br/>+ dnsmasq DHCP"]
        P01["peer01 / orq<br/>192.168.100.10<br/>Alpine openrc"]
        P02["peer02 / pa<br/>192.168.100.20<br/>Alpine openrc"]
        P03["peer03 / pb<br/>192.168.100.30<br/>Alpine openrc"]
    end

    OP -->|"ssh -i linkguard-key.pem"| ORCH
    OP -->|"ssh -i linkguard-key.pem"| EC2A
    OP -->|"ssh -i linkguard-key.pem"| EC2B
    OP -->|"ssh -i linkguard-key.pem"| EC2C
    OP -->|"sshpass + ProxyCommand"| JH
    JH -->|"sshpass (atidesa15)"| VM40
    JH -->|"sshpass (atidesa15)"| RPI5
    OP -->|"sshpass (linkguard-test)"| P01
    OP -->|"sshpass (linkguard-test)"| P02
    OP -->|"sshpass (linkguard-test)"| P03
    BR0 --- P01
    BR0 --- P02
    BR0 --- P03

    ORCH -. "WG :51820 (NAT traversal)" .- EC2A
    ORCH -. "WG :51820 (NAT traversal)" .- EC2B
    ORCH -. "WG :51820 (NAT traversal)" .- EC2C
    ORCH -. "WG via jump/NAT" .- JH
    JH -. "WG" .- VM40
    JH -. "WG" .- RPI5
    ORCH -. "WG via NAT simetrico host" .- P01
    ORCH -. "WG via NAT simetrico host" .- P02
    ORCH -. "WG via NAT simetrico host" .- P03
```

**Leyenda de acceso:**
- Líneas sólidas = SSH de control desde el operador.
- Líneas discontinuas = túneles WireGuard que se establecen durante el ciclo de pruebas.
- 3 canales SSH distintos: llave PEM (AWS/orq), `sshpass` + `ProxyCommand` via jump (VM40/RPi5), `sshpass` directo (QEMU).

---

## 2. Topologia hub-spoke

Todo el tráfico entre peers pasa por el hub. Sin P2P.

```mermaid
flowchart TB
    HUB(("HUB<br/>34.193.139.170<br/>10.20.30.1"))

    EC2A["peer-100<br/>10.20.30.x"]
    EC2B["peer-34<br/>10.20.30.x"]
    EC2C["peer-184<br/>10.20.30.x"]
    VM40["peer-172-20-0-40<br/>10.20.30.x"]
    RPI5["peer-172-20-0-7<br/>10.20.30.x"]
    P01["peer01 QEMU<br/>10.20.30.x"]
    P02["peer02 QEMU<br/>10.20.30.x"]
    P03["peer03 QEMU<br/>10.20.30.x"]

    EC2A -->|"relay via hub"| HUB
    EC2B -->|"relay via hub"| HUB
    EC2C -->|"relay via hub"| HUB
    VM40 -->|"relay via hub"| HUB
    RPI5 -->|"relay via hub"| HUB
    P01 -->|"relay via hub"| HUB
    P02 -->|"relay via hub"| HUB
    P03 -->|"relay via hub"| HUB

    HUB --> EC2A
    HUB --> EC2B
    HUB --> EC2C
    HUB --> VM40
    HUB --> RPI5
    HUB --> P01
    HUB --> P02
    HUB --> P03
```

- Resultado esperado: 8 peers, todos reachables a traves del hub.
- Estado actual (AGENTS.md): completado, 8 peers OK.

---

## 3. Topologia hub-mesh

Peers de nube (AWS) con P2P directo entre ellos; el resto relay via hub.

```mermaid
flowchart TB
    HUB(("HUB<br/>10.20.30.1"))

    subgraph NUBE[P2P mesh entre nubes]
        EC2A["peer-100<br/>AWS"]
        EC2B["peer-34<br/>AWS"]
        EC2C["peer-184<br/>AWS"]
        EC2A <--> EC2B
        EC2A <--> EC2C
        EC2B <--> EC2C
    end

    VM40["peer-172-20-0-40<br/>VM via jump"]
    RPI5["peer-172-20-0-7<br/>RPi5 via jump"]
    P01["peer01 QEMU"]
    P02["peer02 QEMU"]
    P03["peer03 QEMU"]

    EC2A <--> HUB
    EC2B <--> HUB
    EC2C <--> HUB
    HUB <--> VM40
    HUB <--> RPI5
    HUB <--> P01
    HUB <--> P02
    HUB <--> P03

    VM40 -. "relay" .- EC2A
    RPI5 -. "relay" .- EC2A
    P01 -. "relay" .- EC2A
```

- Nube-a-nube: P2P directo (TTL=64, menor RTT).
- NAT peers (VM40/RPi5/QEMU): relay via hub (TTL=63).
- Estado actual (AGENTS.md): completado en fast mode; terminales 1-3/7 pings (NAT esperado).

---

## 4. Topologia mesh

P2P directo entre todos los peers con endpoint publico. Sin relay central (excepto peers tras NAT).

```mermaid
flowchart TB
    subgraph NUBE[P2P directo - puerto 51820 abierto en SG]
        EC2A["peer-100<br/>54.210.49.136:51820"]
        EC2B["peer-34<br/>3.228.113.66:51820"]
        EC2C["peer-184<br/>98.87.229.24:51820"]
        EC2A <--> EC2B
        EC2A <--> EC2C
        EC2B <--> EC2C
    end

    HUB(("HUB<br/>relay de respaldo"))

    VM40["peer-172-20-0-40<br/>NAT via jump"]
    RPI5["peer-172-20-0-7<br/>NAT via jump"]
    P01["peer01 QEMU<br/>NAT simetrico host"]
    P02["peer02 QEMU<br/>NAT simetrico host"]
    P03["peer03 QEMU<br/>NAT simetrico host"]

    HUB <--> EC2A
    HUB <--> EC2B
    HUB <--> EC2C

    VM40 -. "sin endpoint directo<br/>(NAT)" .- EC2A
    RPI5 -. "sin endpoint directo<br/>(NAT)" .- EC2A
    P01 -. "sin endpoint directo<br/>(NAT simetrico)" .- EC2A
    P02 -. "sin endpoint directo" .- EC2B
    P03 -. "sin endpoint directo" .- EC2C
```

- EC2-to-EC2: 6-7/7 OK (P2P real con `WG_LISTEN_PORT=51820`).
- NAT peers (jump/QEMU): 3/7 OK — sin endpoint publico, no hay conectividad directa.
- Estado actual (AGENTS.md): completado en fast mode; issue conocido documentado.

---

## 5. Componentes de codigo

```mermaid
flowchart LR
    subgraph Entry[Entrypoints]
        HS[generate-report-hubspoke.py]
        HM[generate-report-hubmesh.py]
        MS[generate-report-mesh.py]
    end

    subgraph Common[report_common.py]
        RR[run_report]
        AUTH[Auth multiusuario<br/>ADMIN_TOKEN + tenant-a JWT]
        CYCLE[run_topology_cycle]
        CLEAN[clean_all_peers<br/>start_all_peers]
        TESTS[ping_* + throughput<br/>iperf3 / HTTP fallback]
        WG[capture_wg_configs]
        HTML[render_html]
        JSONL[write_jsonl_report]
    end

    subgraph Access[Acceso remoto]
        CLI[orch-cli.py<br/>argparse fixed]
        SSHK[SSH llave PEM<br/>nubes + orq]
        SSHT[sshpass + ProxyCommand<br/>VM40 / RPi5 via jump]
        SSHQ[sshpass directo<br/>QEMU]
    end

    subgraph Testbed[Testbed launcher]
        LT[launch-testbed.py<br/>bridges br0 + dnsmasq + 3 VMs]
    end

    HS --> RR
    HM --> RR
    MS --> RR
    RR --> AUTH --> CLI
    RR --> CYCLE
    CYCLE --> CLEAN
    CYCLE --> TESTS
    CYCLE --> WG
    CLEAN --> SSHK
    CLEAN --> SSHT
    CLEAN --> SSHQ
    TESTS --> SSHK
    TESTS --> SSHT
    TESTS --> SSHQ
    WG --> SSHK
    WG --> SSHT
    WG --> SSHQ
    CLI -->|"XML-RPC :8000"| ORCH[Orquestador]
    RR --> HTML --> REPF[docs/reports/.../reporte-*.html]
    RR --> JSONL --> HISF[docs/reporte-rendimiento-historial.jsonl]
    LT -. "arranca/keepalive" .- SSHQ
```

---

## 6. Flujo del ciclo por topologia

```mermaid
flowchart TD
    S[Entry: hub-spoke | hub-mesh | mesh] --> A[get_admin_token desde orq]
    A --> B[ensure_tenant_user: crear tenant-a + login JWT]
    B --> C[Leer topologia original]
    C --> D[set_topology objetivo en orq]
    D --> E[F1 clean_all_peers<br/>peers + orq + hub wg-HUB]
    E --> F[F2 set_topology]
    F --> G[F3 start_all_peers<br/>update peer.env + restart service]
    G --> H[F4 wait_for_all_peers<br/>8/8 registrados]
    H --> I[F5 wait_for_handshakes<br/>wg show wg-HUB]
    I --> J[F5b capture_wg_configs<br/>wg show + showconf por peer]
    J --> K[F6 matriz de pings NxN<br/>8x7 = 56 pares]
    K --> L[F7 throughput nube<br/>iperf3 o HTTP fallback]
    L --> M[F9 check_wan_access<br/>VM40 + RPi5]
    M --> N[Restaurar topologia original]
    N --> O[render_html]
    O --> P[write_jsonl_report]
    P --> Q[Fin OK]
```

- `--fast`: pings de 2 paquetes, timeout 60s (iteracion rapida).
- Sin `--fast`: 5 paquetes, timeout 120s (medicion realista).

---

## 7. Inventario consolidado

| Peer ID | Host | Tipo | Acceso | NAT | Service mgr |
|---|---|---|---|---|---|
| peer-100-31-255-119 | 54.210.49.136 | AWS Ubuntu | llave PEM | ninguno | systemd |
| peer-34-207-174-76 | 3.228.113.66 | AWS Amazon Linux | llave PEM | ninguno | systemd |
| peer-184-72-71-143 | 98.87.229.24 | AWS Amazon Linux | llave PEM | ninguno | systemd |
| peer-172-20-0-40 | 172.20.0.40 | VM Alpine | sshpass via jump 100.115.215.49 | jump host | openrc |
| peer-172-20-0-7 | 172.20.0.7 | RPi5 | sshpass via jump 100.115.215.49 | jump host | systemd |
| peer01 (orq) | 192.168.100.10 | QEMU Alpine | sshpass directo (br0) | simetrico host | openrc |
| peer02 (pa) | 192.168.100.20 | QEMU Alpine | sshpass directo (br0) | simetrico host | openrc |
| peer03 (pb) | 192.168.100.30 | QEMU Alpine | sshpass directo (br0) | simetrico host | openrc |

**Total:** 5 reales + 3 QEMU = 8 peers bajo tenant-a. Orquestador/hub en `34.193.139.170`.

---

## Lectura rapida

- **3 entrypoints** (`generate-report-{hubspoke,hubmesh,mesh}.py`) solo cambian la topologia objetivo; toda la logica vive en `report_common.py`.
- **3 canales SSH** distintos por tipo de peer: PEM (AWS/orq), `sshpass + ProxyCommand` (VM40/RPi5 via jump), `sshpass` directo (QEMU).
- **3 topologias**: hub-spoke (todo relay), hub-mesh (P2P solo entre nubes), mesh (P2P entre endpoints publicos; NAT peers sin directo).
- **8 peers** bajo tenant `tenant-a`, orquestador/hub unico en `34.193.139.170:51820`.
- Salidas: HTML por corrida en `docs/reports/linkguard-aws/<topo>/<fecha>/` + historial JSONL en `docs/reporte-rendimiento-historial.jsonl`.
