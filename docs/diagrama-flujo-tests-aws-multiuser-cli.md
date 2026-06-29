## Diagrama de flujo: `tests-aws-multiuser-cli`

```mermaid
flowchart TD
    A[Script de entrada\nhub-spoke | hub-mesh | mesh] --> B[run_report topologia]
    B --> C[Parsear argumentos CLI]
    C --> D[Verificar llave SSH]
    D --> E[Obtener ADMIN_TOKEN\ndesde orquestador]
    E --> F[Asegurar tenant-a\ncrear token + login JWT]
    F --> G[Leer topologia original]
    G --> H[run_topology_cycle]

    subgraph Cycle[Ciclo por topologia]
        H --> H1[Limpieza completa\npeers + orquestador + hub WG]
        H1 --> H2[Configurar topologia en orquestador]
        H2 --> H3[Actualizar peer.env e iniciar peers]
        H3 --> H4[Esperar registro de todos los peers]
        H4 --> H5[Esperar handshakes WireGuard]
        H5 --> H6[Capturar wg show y wg showconf]
        H6 --> H7[Ejecutar matriz de pings]
        H7 --> H8[Medir throughput nube\niperf3 o fallback HTTP]
        H8 --> H9[Construir TopologyResult]
    end

    H9 --> I[Restaurar topologia original]
    I --> J[render_html]
    J --> K[Escribir reporte HTML]
    K --> L[Append historial JSONL]
    L --> M[Fin OK]

    H --> X[Excepcion]
    E --> X
    F --> X
    G --> X
    X --> Y[Intentar restaurar topologia original]
    Y --> Z[Fin con error]
```

### Lectura rapida

- El entrypoint solo selecciona la topologia y delega todo a `run_report(...)`.
- `run_report(...)` prepara autenticacion y contexto global antes de lanzar el ciclo de pruebas.
- `run_topology_cycle(...)` ejecuta las fases operativas: limpieza, configuracion, arranque, espera, medicion y captura de estado.
- Al terminar, siempre intenta volver a la topologia original del orquestador antes de escribir salidas.
- Si ocurre un error, tambien intenta restaurar la topologia antes de devolver codigo de salida `1`.
