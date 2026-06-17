#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import argparse
from xmlrpc.client import ServerProxy

def client(url: str):
    return ServerProxy(url, allow_none=True)

def pretty(x):
    print(json.dumps(x, indent=2, sort_keys=True))

def main():
    # Parser compartido: --admin-token y --token disponibles en TODOS los subcomandos
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--admin-token", default=os.getenv("ADMIN_TOKEN", ""),
                        help="ADMIN_TOKEN (required for admin-only ops)")
    shared.add_argument("--token", default=os.getenv("JWT", ""),
                        help="JWT de tenant (obtener con: orch-cli auth-login)")

    ap = argparse.ArgumentParser(description="Orchestrator Admin CLI (admin-only ops + tenant ops)",
                                 parents=[shared])
    ap.add_argument("--url", default=os.getenv("ORCH_URL", "http://127.0.0.1:8000/RPC2"))

    sub = ap.add_subparsers(dest="cmd", required=True)

    # core
    sub.add_parser("health", parents=[shared])
    sub.add_parser("metrics", parents=[shared])
    sub.add_parser("events", parents=[shared])

    # users (admin-only)
    p_uc = sub.add_parser("user-create", parents=[shared])
    p_uc.add_argument("user_id")

    sub.add_parser("user-list", parents=[shared])

    p_ug = sub.add_parser("user-get", parents=[shared])
    p_ug.add_argument("user_id")

    p_ud = sub.add_parser("user-delete", parents=[shared])
    p_ud.add_argument("user_id")
    p_ud.add_argument("--purge", action="store_true")

    p_uit = sub.add_parser("issue-user-token", parents=[shared])
    p_uit.add_argument("user_id")

    # auth
    p_al = sub.add_parser("auth-login", help="Obtener JWT con user_id + user_token", parents=[shared])
    p_al.add_argument("user_id")
    p_al.add_argument("user_token")
    p_al.add_argument("--scopes", default="*", help="Scopes separados por coma (default: *)")
    p_al.add_argument("--ttl", type=int, default=None, help="TTL en segundos (default: server default)")

    p_ar = sub.add_parser("auth-refresh", help="Renovar JWT existente antes de que expire", parents=[shared])
    p_ar.add_argument("jwt_token", nargs="?", default=None,
                      help="JWT a renovar (default: $JWT)")
    p_ar.add_argument("--ttl", type=int, default=None, help="TTL en segundos (default: server default)")

    sub.add_parser("auth-whoami", help="Decodificar el JWT actual y mostrar su payload", parents=[shared])

    # revoke
    p_rev = sub.add_parser("revoke", parents=[shared])
    p_rev.add_argument("jti")

    # networks (admin-only create/delete; list/get/topology readable with tenant JWT in other clients)
    p_nc = sub.add_parser("net-create", parents=[shared])
    p_nc.add_argument("network_id")
    p_nc.add_argument("tunnel_cidr")
    p_nc.add_argument("--topology", default="hub-spoke")
    p_nc.add_argument("--hub-peer-id", default="HUB")
    p_nc.add_argument("--user-id", default=None)

    p_nl = sub.add_parser("net-list", parents=[shared])
    p_nl.add_argument("--user-id", default=None)

    p_ng = sub.add_parser("net-get", parents=[shared])
    p_ng.add_argument("network_id")

    p_nt = sub.add_parser("net-topology", parents=[shared])
    p_nt.add_argument("network_id")

    p_nd = sub.add_parser("net-delete", parents=[shared])
    p_nd.add_argument("network_id")
    p_nd.add_argument("--purge", action="store_true")

    # F5: cambiar topología de una red existente (admin-only)
    p_nst = sub.add_parser("net-set-topology", parents=[shared],
                            help="Cambia la topología de una red ('hub-spoke', 'mesh' o 'hub-mesh')")
    p_nst.add_argument("network_id")
    p_nst.add_argument("topology", choices=["hub-spoke", "mesh", "hub-mesh"])  # HM-F5d

    # F5: listar peers mesh activos en una red
    p_mp = sub.add_parser("mesh-peers",
                           help="Lista peers activos en una red mesh", parents=[shared])
    p_mp.add_argument("network_id")
    p_mp.add_argument("--peer-id", default=None,
                      help="peer_id del solicitante (para excluirlo de la lista)")

    # HM-F5e: nuevo subcomando — tabla de clasificación direct/relay en redes hub-mesh
    p_pr = sub.add_parser("peer-reachability",
                           help="Muestra clasificación directo/relay de peers en una red hub-mesh", parents=[shared])
    p_pr.add_argument("network_id")
    p_pr.add_argument("--peer-id", default=None,
                      help="peer_id del solicitante (default: 'admin-query')")

    # peers
    p_pl = sub.add_parser("peer-list", parents=[shared])
    p_pl.add_argument("--user-id", default=None)

    p_pg = sub.add_parser("peer-get", parents=[shared])
    p_pg.add_argument("peer_id")

    p_pu = sub.add_parser("peer-update-admin", parents=[shared])
    p_pu.add_argument("peer_id")
    p_pu.add_argument("fields_json")

    p_pdel = sub.add_parser("peer-unregister", parents=[shared])
    p_pdel.add_argument("peer_id")

    # assign/remove network membership (admin-only)
    p_an = sub.add_parser("assign-network", parents=[shared])
    p_an.add_argument("peer_id")
    p_an.add_argument("network_id")
    p_an.add_argument("ip")
    p_an.add_argument("--role", default=None)

    p_rn = sub.add_parser("remove-network", parents=[shared])
    p_rn.add_argument("peer_id")
    p_rn.add_argument("network_id")

    args = ap.parse_args()
    c = client(args.url)

    if args.cmd == "auth-login":
        scopes = [s.strip() for s in args.scopes.split(",")]
        result = c.__getattr__("auth.login")(args.user_id, args.user_id, args.user_token, scopes, args.ttl)
        pretty(result)
        print(f"\n  Exporta el JWT para usarlo en otros comandos:")
        print(f"  export JWT={result['jwt']}\n")
        return

    if args.cmd == "auth-refresh":
        jwt_token = args.jwt_token or os.getenv("JWT", "")
        if not jwt_token:
            print("ERROR: proporciona el JWT como argumento o en la variable $JWT")
            return
        result = c.__getattr__("auth.refresh")(jwt_token, args.ttl)
        pretty(result)
        print(f"\n  Actualiza la variable de entorno:")
        print(f"  export JWT={result['jwt']}\n")
        return

    if args.cmd == "auth-whoami":
        jwt_token = args.token or os.getenv("JWT", "")
        if not jwt_token:
            print("ERROR: proporciona el JWT con --token o en la variable $JWT")
            return
        pretty(c.__getattr__("auth.whoami")(jwt_token))
        return

    if args.cmd == "health":
        pretty(c.__getattr__("orch.health")(args.token or None))
        return

    if args.cmd == "metrics":
        # admin token -> global
        tok = args.admin_token or args.token or None
        pretty(c.__getattr__("orch.metrics")(tok))
        return

    if args.cmd == "events":
        tok = args.admin_token or args.token or None
        pretty(c.__getattr__("orch.events")(tok))
        return

    # users
    if args.cmd == "user-create":
        pretty(c.__getattr__("orch.user-create")(args.user_id, args.admin_token))
        return

    if args.cmd == "user-list":
        pretty(c.__getattr__("orch.user-list")(args.admin_token))
        return

    if args.cmd == "user-get":
        pretty(c.__getattr__("orch.user-get")(args.user_id, args.admin_token))
        return

    if args.cmd == "user-delete":
        pretty(c.__getattr__("orch.user-delete")(args.user_id, bool(args.purge), args.admin_token))
        return

    if args.cmd == "issue-user-token":
        pretty(c.__getattr__("orch.issue-user-token")(args.user_id, args.admin_token))
        return

    if args.cmd == "revoke":
        pretty(c.__getattr__("orch.revoke")(args.jti, args.admin_token))
        return

    # networks
    if args.cmd == "net-create":
        pretty(c.__getattr__("network.create")(args.network_id, args.tunnel_cidr, args.topology, args.hub_peer_id, args.user_id, args.admin_token))
        return

    if args.cmd == "net-list":
        pretty(c.__getattr__("network.list")(args.user_id, args.admin_token, args.token or None))
        return

    if args.cmd == "net-get":
        pretty(c.__getattr__("network.get")(args.network_id, args.admin_token, args.token or None))
        return

    if args.cmd == "net-topology":
        pretty(c.__getattr__("network.get_topology")(args.network_id, args.admin_token, args.token or None))
        return

    if args.cmd == "net-delete":
        pretty(c.__getattr__("network.delete")(args.network_id, bool(args.purge), args.admin_token))
        return

    # F5: mesh
    if args.cmd == "net-set-topology":
        result = c.__getattr__("network.set_topology")(args.network_id, args.topology, args.admin_token)
        pretty(result)
        if result.get("changed"):
            if args.topology == "hub-mesh":
                print(f"\n  ✓ hub-mesh activo en '{args.network_id}'.")
                print("    Peers directamente alcanzables → conexión P2P.")
                print("    Peers detrás de NAT simétrico → relay automático vía HUB.")
            else:
                print(f"\n  ✓ Topología cambiada a '{args.topology}'. "
                      "Los peers actualizarán su config en el próximo heartbeat.")
        else:
            print(f"\n  — La red ya tenía topología '{args.topology}', sin cambios.")
        return

    if args.cmd == "mesh-peers":
        peer_id = getattr(args, "peer_id", None) or "admin-query"
        data = c.__getattr__("config.get_mesh_peers")(peer_id, args.network_id,
                                                       args.admin_token or args.token or None)
        # Soportar respuesta lista (mesh puro) o dict (hub-mesh)
        if isinstance(data, list):
            peers = data
            fmt = "  {:<20} {:<20} {:<45} {:<6}"
            print(fmt.format("PEER ID", "TUNNEL IP", "ENDPOINT", "ALIVE"))
            print("  " + "-" * 93)
            for p in peers:
                print(fmt.format(
                    p.get("peer_id", "")[:19],
                    p.get("tunnel_ip", "")[:19],
                    (p.get("endpoint") or "(sin endpoint)")[:44],
                    "✓" if p.get("alive") else "✗",
                ))
        else:
            # hub-mesh: dict con direct / relay_only
            direct     = data.get("direct") or []
            relay_only = data.get("relay_only") or []
            relay_cidr = data.get("relay_cidr", "")
            fmt = "  {:<20} {:<14} {:<45} {:<8}"
            print(fmt.format("PEER ID", "TUNNEL IP", "ENDPOINT", "MODO"))
            print("  " + "-" * 90)
            for p in direct:
                print(fmt.format(p.get("peer_id","")[:19], p.get("tunnel_ip","")[:13],
                                 (p.get("endpoint") or "")[:44], "DIRECTO"))
            for p in relay_only:
                print(fmt.format(p.get("peer_id","")[:19], p.get("tunnel_ip","")[:13],
                                 f"(relay via {relay_cidr})"[:44], "RELAY"))
        return

    # HM-F5e: peer-reachability
    if args.cmd == "peer-reachability":
        peer_id = getattr(args, "peer_id", None) or "admin-query"
        data = c.__getattr__("config.get_mesh_peers")(peer_id, args.network_id,
                                                       args.admin_token or args.token or None)
        if isinstance(data, list):
            print(f"  La red '{args.network_id}' es mesh puro, no hub-mesh.")
            print("  Usa 'mesh-peers' para ver peers de redes mesh puro.")
            return
        direct     = data.get("direct")     or []
        relay_only = data.get("relay_only") or []
        relay_cidr = data.get("relay_cidr", "")
        fmt = "  {:<20} {:<14} {:<12} {:<13} {:<10}"
        print(f"\n  Red: {args.network_id}  |  Relay CIDR: {relay_cidr}")
        print(fmt.format("PEER ID", "TUNNEL IP", "NAT TYPE", "RELAY MODE", "ESTADO"))
        print("  " + "-" * 72)
        for p in direct:
            print(fmt.format(p.get("peer_id","")[:19], p.get("tunnel_ip","")[:13],
                             (p.get("nat_type") or "?")[:11],
                             (p.get("relay_mode") or "auto")[:12], "DIRECTO"))
        for p in relay_only:
            print(fmt.format(p.get("peer_id","")[:19], p.get("tunnel_ip","")[:13],
                             (p.get("nat_type") or "?")[:11],
                             (p.get("relay_mode") or "auto")[:12], "RELAY"))
        return

    # peers
    if args.cmd == "peer-list":
        pretty(c.__getattr__("peer.list")(args.user_id, args.admin_token, args.token or None))
        return

    if args.cmd == "peer-get":
        pretty(c.__getattr__("peer.get")(args.peer_id, args.admin_token, args.token or None))
        return

    if args.cmd == "peer-update-admin":
        fields = json.loads(args.fields_json)
        pretty(c.__getattr__("peer.update_admin")(args.peer_id, fields, args.admin_token))
        return

    if args.cmd == "peer-unregister":
        pretty(c.__getattr__("peer.unregister")(args.peer_id, args.token or None))
        return

    if args.cmd == "assign-network":
        pretty(c.__getattr__("peer.assign_network")(args.peer_id, args.network_id, args.ip, args.role, args.admin_token, args.token or None))
        return

    if args.cmd == "remove-network":
        pretty(c.__getattr__("peer.remove_from_network")(args.peer_id, args.network_id, args.admin_token))
        return

if __name__ == "__main__":
    main()
