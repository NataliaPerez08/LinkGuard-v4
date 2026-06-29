## Diagrama general: sistema de pruebas de topologias y reportes

```mermaid
flowchart TD
    U[Usuario u operador] --> E[Entrypoint de ejecucion]

    subgraph Core[Motor de ejecucion]
        CFG[Configuracion\ncredenciales, inventario, topologia objetivo]
        AUTH[Sesion y autorizacion\ntoken, API key o credenciales]
        ORCH[Controlador de topologia]
        REM[Adaptadores remotos\nSSH, API, agente local]
        TEST[Motor de pruebas\nconectividad, handshake, throughput]
        OBS[Captura de estado\nconfigs, logs, metricas]
        RPT[Renderizador de reportes]
        HIS[Persistencia historica]
    end

    subgraph Infra[Infraestructura bajo prueba]
        HUB[Control plane u orquestador]
        P1[Grupo de peers tipo A]
        P2[Grupo de peers tipo B]
        P3[Grupo de peers tipo C]
    end

    subgraph Output[Salidas]
        HTML[Reporte visual]
        JSON[Resumen estructurado]
        LOG[Traza operativa]
    end

    E --> CFG
    CFG --> AUTH
    AUTH --> ORCH
    ORCH --> HUB

    CFG --> REM
    REM --> P1
    REM --> P2
    REM --> P3

    ORCH --> TEST
    REM --> TEST
    TEST --> OBS
    OBS --> RPT
    RPT --> HTML
    OBS --> JSON
    OBS --> HIS
    TEST --> LOG
```

### Lectura rapida

- Este diagrama abstrae el caso concreto y sirve para cualquier sistema que configure una topologia, ejecute pruebas distribuidas y genere reportes.
- Separa el problema en capas: entrada, ejecucion, infraestructura bajo prueba y salidas.
- El bloque `Adaptadores remotos` representa cualquier mecanismo de acceso a los nodos: SSH, agentes, RPC o APIs.
- `Captura de estado` y `Persistencia historica` quedan separados del renderizado para que el sistema pueda producir varios formatos de salida.
