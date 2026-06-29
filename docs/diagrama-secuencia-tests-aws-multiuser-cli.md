## Diagrama de secuencia: `tests-aws-multiuser-cli`

```mermaid
sequenceDiagram
    participant S as Script entrada
    participant RC as report_common.py
    participant CLI as orch-cli.py
    participant O as Orquestador
    participant C as Peers AWS
    participant T as VM/RPi via jump
    participant Q as Peers QEMU
    participant D as docs/reports

    S->>RC: run_report(topology, ...)
    RC->>O: leer /etc/linkguard/secrets
    O-->>RC: ADMIN_TOKEN
    RC->>CLI: user-create tenant-a
    CLI->>O: RPC user-create
    O-->>CLI: resultado
    CLI-->>RC: user_id / already exists

    RC->>CLI: issue-user-token tenant-a
    CLI->>O: RPC issue-user-token
    O-->>CLI: token tenant
    CLI-->>RC: token

    RC->>CLI: auth-login tenant-a token
    CLI->>O: RPC auth-login
    O-->>CLI: JWT tenant
    CLI-->>RC: jwt

    RC->>CLI: net-topology default
    CLI->>O: RPC net-topology
    O-->>CLI: topologia original
    CLI-->>RC: topologia original

    RC->>CLI: net-set-topology default topology
    CLI->>O: RPC net-set-topology
    O-->>CLI: ok
    CLI-->>RC: ok

    par Limpieza
        RC->>C: stop wg-auto-register + borrar wg0
        RC->>T: stop wg-auto-register + borrar wg0
        RC->>Q: stop wg-auto-register + borrar wg0
        RC->>CLI: peer-list / peer-unregister
        CLI->>O: RPC peer-list / peer-unregister
        O-->>CLI: peers / ok
        CLI-->>RC: resultado
        RC->>O: wg set wg-HUB peer remove
    end

    par Arranque
        RC->>C: actualizar peer.env + restart service
        RC->>T: actualizar peer.env + start service
        RC->>Q: actualizar peer.env + start service
    end

    loop Hasta registrar todos los peers
        RC->>CLI: peer-list
        CLI->>O: RPC peer-list
        O-->>CLI: inventario peers
        CLI-->>RC: peers con IP/endpoint
    end

    loop Hasta handshake completo
        RC->>O: wg show wg-HUB
        O-->>RC: estado handshakes
    end

    RC->>O: wg show + wg showconf
    RC->>C: wg show + wg showconf
    RC->>T: wg show + wg showconf
    RC->>Q: wg show + wg showconf

    RC->>C: ping a IPs tunel destino
    RC->>T: ping a IPs tunel destino
    RC->>Q: ping a IPs tunel destino

    alt iperf3 disponible en nube
        RC->>C: iperf3 server/client
        C-->>RC: throughput
    else fallback HTTP
        RC->>C: HTTP download test
        C-->>RC: throughput
    end

    RC->>CLI: net-set-topology default topologia_original
    CLI->>O: RPC net-set-topology
    O-->>CLI: ok
    CLI-->>RC: ok

    RC->>D: escribir HTML
    RC->>D: append JSONL historial
    RC-->>S: exit code 0
```

### Lectura rapida

- `report_common.py` actua como coordinador central de toda la corrida.
- `orch-cli.py` encapsula las llamadas RPC al orquestador para autenticacion, inventario y cambio de topologia.
- Las operaciones sobre peers se reparten en tres canales: AWS por llave SSH, terminales via jump host y QEMU por `sshpass`.
- El inventario devuelto por `peer-list` alimenta la matriz de pings porque aporta las IPs de tunel de cada peer.
- El reporte se genera al final, cuando ya se restauró la topologia original del orquestador.
