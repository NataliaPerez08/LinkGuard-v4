## Diagramas de `tests-aws-multiuser-cli`

Indice de acceso rapido a los diagramas del modulo.

Documento relacionado:

- [Indice general de documentacion](./README.md)

### Diagramas especificos

- [Diagrama de componentes](./diagrama-componentes-tests-aws-multiuser-cli.md)
- [Diagrama de flujo](./diagrama-flujo-tests-aws-multiuser-cli.md)
- [Diagrama de secuencia](./diagrama-secuencia-tests-aws-multiuser-cli.md)

### Diagrama general reutilizable

- [Caso general: sistema de pruebas de topologias y reportes](./diagrama-general-caso-pruebas-topologias.md)

### Documentos relacionados

- [Estilo de la API del orchestrator y del peer](./estilo-api-orchestrator-peer.md)

### Relacion entre archivos del modulo

- `generate-report-hubspoke.py` -> llama `run_report("hub-spoke", ...)`
- `generate-report-hubmesh.py` -> llama `run_report("hub-mesh", ...)`
- `generate-report-mesh.py` -> llama `run_report("mesh", ...)`
- `report_common.py` -> implementa inventario, SSH, CLI, ciclo de pruebas, render HTML y persistencia JSONL
