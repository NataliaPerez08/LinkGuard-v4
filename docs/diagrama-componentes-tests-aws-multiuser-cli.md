## Diagrama de componentes: `tests-aws-multiuser-cli`

```mermaid
flowchart TD
    subgraph Entrypoints[Entrypoints]
        HS[generate-report-hubspoke.py]
        HM[generate-report-hubmesh.py]
        MS[generate-report-mesh.py]
    end

    subgraph Core[Core comun: report_common.py]
        RR[run_report]
        AUTH[Autenticacion multiusuario\nget_admin_token + ensure_tenant_user]
        TOPO[Control de topologia\nget_current_topology + set_topology]
        CYCLE[run_topology_cycle]
        CLEAN[Limpieza y reinicio de peers\nclean_* + start_* + wait_*]
        TESTS[Pruebas de red\nping_* + throughput]
        WG[Captura WireGuard\ncapture_wg_configs]
        HTML[render_html]
        JSONL[write_jsonl_report]
    end

    subgraph Access[Capa de acceso remoto]
        CLI[orchestrator-install-v2/orch-cli.py]
        SSHC[SSH cloud/orchestrator\nssh_key_* + ssh_cloud_* + ssh_orch_*]
        SSHT[SSH terminal via jump\nssh_terminal_*]
        SSHQ[SSH QEMU\nssh_qemu_*]
    end

    subgraph Inventory[Inventario de peers]
        REAL[REAL_PEERS\n3 AWS + 1 VM + 1 RPi5]
        QEMU[QEMU_PEERS\npeer01 + peer02 + peer03]
    end

    subgraph Infra[Infraestructura externa]
        ORCH[Orquestador LinkGuard]
        CLOUD[Peers nube]
        TERM[VM y RPi5 via jump host]
        VMS[VMs QEMU]
    end

    subgraph Output[Salidas]
        HTMLFILE[Reporte HTML\ndocs/reports/aws-multiuser-cli/...]
        JSONLFILE[Historial JSONL\ndocs/reports/aws-multiuser-cli-historial.jsonl]
    end

    HS --> RR
    HM --> RR
    MS --> RR

    RR --> AUTH
    RR --> TOPO
    RR --> CYCLE
    RR --> HTML
    RR --> JSONL

    AUTH --> CLI
    TOPO --> CLI
    CYCLE --> CLEAN
    CYCLE --> TESTS
    CYCLE --> WG

    CLEAN --> SSHC
    CLEAN --> SSHT
    CLEAN --> SSHQ
    TESTS --> SSHC
    TESTS --> SSHT
    TESTS --> SSHQ
    WG --> SSHC
    WG --> SSHT
    WG --> SSHQ

    CLI --> ORCH
    SSHC --> ORCH
    SSHC --> CLOUD
    SSHT --> TERM
    SSHQ --> VMS

    REAL --> CYCLE
    QEMU --> CYCLE
    REAL --> TESTS
    QEMU --> TESTS

    HTML --> HTMLFILE
    JSONL --> JSONLFILE
```

### Lectura rapida

- Los tres scripts de entrada solo cambian la topologia objetivo: `hub-spoke`, `hub-mesh` o `mesh`.
- `report_common.py` concentra casi toda la logica del sistema.
- La autenticacion multiusuario pasa por `orch-cli.py`: obtiene `ADMIN_TOKEN`, crea/asegura `tenant-a`, emite token y hace `auth-login` para conseguir el JWT del tenant.
- La ejecucion principal hace un ciclo por topologia: limpiar, configurar, arrancar peers, esperar registro/handshake, medir conectividad y generar reporte.
- Hay tres canales de acceso remoto distintos porque el testbed mezcla AWS, terminales detras de jump host y VMs QEMU.
- Las salidas finales son un HTML por corrida y un JSONL historico con resumenes.
