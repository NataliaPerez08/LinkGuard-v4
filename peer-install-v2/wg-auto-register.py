#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# wg-auto-register v4 — wrapper para peer_register/
# SEC-05:   Estado del peer guardado con permisos 600 (JWT no legible por otros usuarios)
# SEC-03:   ORCH_TOKEN requerido con mensaje de error claro
# MESH-F3a: apply_config genera N bloques [Peer] en redes mesh
# MESH-F3b: cmd_heartbeat detecta cambio de mesh_peers_hash y reaplica config
# MESH-F3c: cmd_heartbeat incluye endpoint detectado en el status
# HM-F4a:  apply_config genera .conf hub-mesh: HUB=/CIDR, directos=/32, relay sin bloque
# HM-F4b:  detect_nat_type: heuristica none|full-cone|symmetric
# HM-F4c:  probe_direct_peers: monitor handshakes -> peer.report_reachability
# HM-F4d:  cmd_heartbeat: incluye nat_type, llama probe_direct_peers en hub-mesh

from peer_register import main as _main

if __name__ == "__main__":
    _main()
