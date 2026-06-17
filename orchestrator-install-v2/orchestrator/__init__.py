"""
LinkGuard Orchestrator v4 - Paquete modular.
Punto de entrada unico: main()
Servidor XML-RPC en /RPC2, compatible con orch-cli.py y hub-agent.py.
"""

import defusedxml.xmlrpc
defusedxml.xmlrpc.monkey_patch()  # nosec B411

import threading
from typing import Any, Dict
from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler  # nosec B411
from socketserver import ThreadingMixIn
from xmlrpc.client import Fault  # nosec B411

from . import config, state, auth


# Thread-local storage for HTTP request context
_rpc_context = threading.local()


class _Handler(SimpleXMLRPCRequestHandler):
    rpc_paths = ("/RPC2",)

    def do_POST(self):
        _rpc_context.client_address = self.client_address
        try:
            return super().do_POST()
        finally:
            _rpc_context.client_address = None


class _Server(ThreadingMixIn, SimpleXMLRPCServer):
    daemon_threads = True
    allow_reuse_address = True


def _safe_call(handler, params: dict) -> Any:
    try:
        return handler(params)
    except PermissionError as e:
        raise Fault(1, f"403: {e}")
    except KeyError as e:
        raise Fault(1, f"404: {e}")
    except ValueError as e:
        raise Fault(1, f"400: {e}")
    except RuntimeError as e:
        raise Fault(1, f"503: {e}")


# Cada wrapper XML-RPC recibe *args posicionales segun el contrato original
# y construye un dict para el handler modular.

def _xml_login(*args) -> dict:
    user_id, peer_id, user_token = args[0], args[1] if len(args) > 1 else None, args[2] if len(args) > 2 else ""
    scopes = args[3] if len(args) > 3 else ["*"]
    ttl = args[4] if len(args) > 4 else config.JWT_TTL_DEFAULT
    if not user_id or not user_token:
        raise ValueError("user_id and user_token required")
    auth._check_user_token(user_id, user_token)
    token, exp = auth._jwt_encode({
        "user_id": user_id, "peer_id": peer_id,
        "scopes": scopes, "role": "user",
    }, ttl)
    return {"jwt": token, "expires_at": exp}


def _xml_refresh(*args) -> dict:
    jwt_token = args[0] if args else ""
    ttl = args[1] if len(args) > 1 else config.JWT_TTL_DEFAULT
    payload = auth._jwt_decode(jwt_token)
    jti = str(payload.get("jti") or "")
    if jti and auth._is_revoked_jti(jti):
        raise PermissionError("jwt revoked")
    token, exp = auth._jwt_encode({
        "role": payload.get("role", "user"), "user_id": payload.get("user_id"),
        "peer_id": payload.get("peer_id"), "scopes": payload.get("scopes") or [],
    }, ttl)
    return {"jwt": token, "expires_at": exp}


def _xml_whoami(*args) -> dict:
    p = auth._jwt_decode(args[0] if args else "")
    for k in ("iat", "nbf", "exp"):
        p.pop(k, None)
    return p


def _xml_health(*args) -> dict:
    from .endpoints_orch import rpc_health
    return _safe_call(rpc_health, {})


def _xml_metrics(*args) -> dict:
    from .endpoints_orch import rpc_metrics
    token = args[0] if args else None
    return _safe_call(rpc_metrics, {"token": token})


def _xml_events(*args) -> dict:
    from .endpoints_orch import rpc_events
    return _safe_call(rpc_events, {})


def _xml_user_create(*args) -> dict:
    # CLI convention: (user_id, admin_token) — 2 args
    # Test convention: (user_id, max_peers, max_networks, metadata, admin_token) — 5 args
    if len(args) >= 5:
        admin_token = args[4]
        max_peers = args[1]
        max_networks = args[2]
        metadata = args[3]
    elif len(args) >= 2:
        admin_token = args[1]
        max_peers = config.DEFAULT_MAX_PEERS
        max_networks = config.DEFAULT_MAX_NETWORKS
        metadata = {}
    else:
        admin_token = None
        max_peers = config.DEFAULT_MAX_PEERS
        max_networks = config.DEFAULT_MAX_NETWORKS
        metadata = {}
    auth.orch_check_admin_token(admin_token)
    from .endpoints_users import rpc_user_create
    return _safe_call(rpc_user_create, {
        "user_id": args[0] if args else "",
        "max_peers": max_peers,
        "max_networks": max_networks,
        "metadata": metadata,
    })


def _xml_user_list(*args) -> dict:
    auth.orch_check_admin_token(args[0] if args else None)
    from .endpoints_users import rpc_user_list
    return _safe_call(rpc_user_list, {})


def _xml_user_get(*args) -> dict:
    auth.orch_check_admin_token(args[1] if len(args) > 1 else None)
    user_id = args[0] if args else ""
    if not user_id:
        raise ValueError("user_id required")
    u = auth._get_user(user_id)
    return {"user_id": user_id, **u}


def _xml_user_delete(*args) -> dict:
    auth.orch_check_admin_token(args[1] if len(args) > 1 else None)
    from .endpoints_users import rpc_user_delete
    return _safe_call(rpc_user_delete, {"user_id": args[0] if args else ""})


def _xml_issue_user_token(*args) -> dict:
    auth.orch_check_admin_token(args[1] if len(args) > 1 else None)
    user_id = args[0] if args else ""
    if not user_id:
        raise ValueError("user_id required")
    tok = auth._issue_user_token(user_id)
    state.persist()
    state.add_event("user.issue_token", {"user_id": user_id})
    return {"user_id": user_id, "token": tok}


def _xml_revoke(*args) -> dict:
    auth.orch_check_admin_token(args[2] if len(args) > 2 else None)
    from .endpoints_auth import rpc_jwt_revoke
    return _safe_call(rpc_jwt_revoke, {
        "token": args[0] if args else "",
        "reason": args[1] if len(args) > 1 else "manual revocation",
    })


def _xml_network_create(*args) -> dict:
    admin_token = args[5] if len(args) > 5 else None
    if admin_token:
        auth.orch_check_admin_token(admin_token)
    from .endpoints_networks import rpc_network_create
    return _safe_call(rpc_network_create, {
        "net_id": args[0] if args else "",
        "cidr": args[1] if len(args) > 1 else "",
        "description": args[2] if len(args) > 2 else "",
        "tag": args[3] if len(args) > 3 else "",
        "user_id": args[4] if len(args) > 4 else "admin",
    })


def _xml_network_list(*args) -> dict:
    from .endpoints_networks import rpc_network_list
    return _safe_call(rpc_network_list, {})


def _xml_network_get(*args) -> dict:
    from .endpoints_networks import rpc_network_get
    return _safe_call(rpc_network_get, {"network_id": args[0] if args else ""})


def _xml_network_get_topology(*args) -> dict:
    from .endpoints_networks import rpc_network_get_topology
    return _safe_call(rpc_network_get_topology, {
        "network_id": args[0] if args else "",
        "admin_token": args[1] if len(args) > 1 else None,
        "token": args[2] if len(args) > 2 else None,
    })


def _xml_network_delete(*args) -> dict:
    from .endpoints_networks import rpc_network_delete
    return _safe_call(rpc_network_delete, {"network_id": args[0] if args else ""})


def _xml_network_set_topology(*args) -> dict:
    from .endpoints_networks import rpc_network_set_topology
    return _safe_call(rpc_network_set_topology, {
        "network_id": args[0] if args else "",
        "topology": args[1] if len(args) > 1 else "hub-spoke",
    })


def _xml_config_get_mesh_peers(*args) -> Any:
    from .endpoints_config import rpc_config_get_mesh_peers
    return _safe_call(rpc_config_get_mesh_peers, {
        "peer_id": args[0] if args else "",
        "network_id": args[1] if len(args) > 1 else "",
        "token": args[2] if len(args) > 2 else None,
    })


def _xml_config_get_peer_config(*args) -> Any:
    from .endpoints_config import rpc_config_get_peer_config
    return _safe_call(rpc_config_get_peer_config, {
        "peer_id": args[0] if args else "",
        "token": args[1] if len(args) > 1 else None,
    })


def _xml_peer_list(*args) -> dict:
    from .endpoints_peers import rpc_peer_list
    return _safe_call(rpc_peer_list, {})


def _xml_peer_register(*args) -> dict:
    from .endpoints_peers import rpc_peer_register
    return _safe_call(rpc_peer_register, {
        "peer_id": args[0] if args else "",
        "public_key": args[1] if len(args) > 1 else "",
        "endpoint": args[2] if len(args) > 2 else "",
        "tags": args[3] if len(args) > 3 else [],
        "metadata": args[4] if len(args) > 4 else {},
        "token": args[5] if len(args) > 5 else None,
    })


def _xml_peer_heartbeat(*args) -> dict:
    from .endpoints_peers import rpc_peer_heartbeat
    client_addr = getattr(_rpc_context, "client_address", None)
    remote_addr = client_addr[0] if client_addr else None
    return _safe_call(rpc_peer_heartbeat, {
        "peer_id": args[0] if args else "",
        "status": args[1] if len(args) > 1 else {},
        "token": args[2] if len(args) > 2 else None,
        "remote_addr": remote_addr,
    })


def _xml_peer_request_network(*args) -> dict:
    from .endpoints_peers import rpc_peer_request_network
    return _safe_call(rpc_peer_request_network, {
        "peer_id": args[0] if args else "",
        "network_id": args[1] if len(args) > 1 else "",
        "token": args[2] if len(args) > 2 else None,
    })


def _xml_peer_rotate_key(*args) -> dict:
    from .endpoints_peers import rpc_peer_rotate_key
    return _safe_call(rpc_peer_rotate_key, {
        "peer_id": args[0] if args else "",
        "public_key": args[1] if len(args) > 1 else "",
        "token": args[2] if len(args) > 2 else None,
    })


def _xml_peer_report_reachability(*args) -> dict:
    from .endpoints_peers import rpc_peer_report_reachability
    return _safe_call(rpc_peer_report_reachability, {
        "peer_id": args[0] if args else "",
        "target_peer_id": args[1] if len(args) > 1 else "",
        "reachable": args[2] if len(args) > 2 else False,
        "token": args[3] if len(args) > 3 else None,
    })


def _xml_peer_get(*args) -> dict:
    from .endpoints_peers import rpc_peer_get
    return _safe_call(rpc_peer_get, {"peer_id": args[0] if args else ""})


def _xml_peer_update_admin(*args) -> bool:
    auth.orch_check_admin_token(args[2] if len(args) > 2 else None)
    from .endpoints_peers import rpc_peer_update_admin
    return _safe_call(rpc_peer_update_admin, {
        "peer_id": args[0] if args else "",
        "fields": args[1] if len(args) > 1 else {},
    })


def _xml_peer_unregister(*args) -> bool:
    admin_token = args[2] if len(args) > 2 else None
    if admin_token:
        auth.orch_check_admin_token(admin_token)
    from .endpoints_peers import rpc_peer_unregister
    return _safe_call(rpc_peer_unregister, {
        "peer_id": args[0] if args else "",
        "token": args[1] if len(args) > 1 else None,
        "admin_token": admin_token or None,
    })


def _xml_peer_assign_network(*args) -> bool:
    auth.orch_check_admin_token(args[4] if len(args) > 4 else None)
    from .endpoints_peers import rpc_peer_assign_network
    return _safe_call(rpc_peer_assign_network, {
        "peer_id": args[0] if args else "",
        "network_id": args[1] if len(args) > 1 else "",
        "ip": args[2] if len(args) > 2 else "",
        "role": args[3] if len(args) > 3 else None,
    })


def _xml_peer_remove_from_network(*args) -> bool:
    auth.orch_check_admin_token(args[2] if len(args) > 2 else None)
    from .endpoints_peers import rpc_peer_remove_from_network
    return _safe_call(rpc_peer_remove_from_network, {
        "peer_id": args[0] if args else "",
        "network_id": args[1] if len(args) > 1 else "",
    })


def _register_xml_handlers(server) -> None:
    mapping: list[tuple[str, Any]] = [
        ("auth.login", _xml_login),
        ("auth.refresh", _xml_refresh),
        ("auth.whoami", _xml_whoami),
        ("orch.health", _xml_health),
        ("orch.metrics", _xml_metrics),
        ("orch.events", _xml_events),
        ("orch.user-create", _xml_user_create),
        ("orch.user-list", _xml_user_list),
        ("orch.user-get", _xml_user_get),
        ("orch.user-delete", _xml_user_delete),
        ("orch.issue-user-token", _xml_issue_user_token),
        ("orch.revoke", _xml_revoke),
        ("network.create", _xml_network_create),
        ("network.list", _xml_network_list),
        ("network.get", _xml_network_get),
        ("network.get_topology", _xml_network_get_topology),
        ("network.delete", _xml_network_delete),
        ("network.set_topology", _xml_network_set_topology),
        ("config.get_mesh_peers", _xml_config_get_mesh_peers),
        ("config.get_peer_config", _xml_config_get_peer_config),
        ("peer.list", _xml_peer_list),
        ("peer.register", _xml_peer_register),
        ("peer.get", _xml_peer_get),
        ("peer.heartbeat", _xml_peer_heartbeat),
        ("peer.request_network", _xml_peer_request_network),
        ("peer.rotate_key", _xml_peer_rotate_key),
        ("peer.report_reachability", _xml_peer_report_reachability),
        ("peer.update_admin", _xml_peer_update_admin),
        ("peer.unregister", _xml_peer_unregister),
        ("peer.assign_network", _xml_peer_assign_network),
        ("peer.remove_from_network", _xml_peer_remove_from_network),
    ]
    for name, fn in mapping:
        server.register_function(fn, name)
    config.log(f"Registrados {len(mapping)} handlers XML-RPC")


def main() -> None:
    config.check_dependencies()
    config.validate_tokens_at_startup()

    state.load_state()

    from .hub_client import hub_ping
    if hub_ping():
        config.log("Conexion con hub-agent: OK")
    else:
        config.log("ADVERTENCIA: hub-agent no responde")

    state.start_backup_loop()

    server = _Server(
        (config.ORCH_BIND, config.ORCH_PORT),
        requestHandler=_Handler,
        allow_none=True, logRequests=False,
    )
    _register_xml_handlers(server)

    config.log(f"Orchestrator listo en {config.ORCH_BIND}:{config.ORCH_PORT}/RPC2")
    config.log(f"Auto-approve: {'ACTIVADO' if config.AUTO_APPROVE_ENABLED else 'DESACTIVADO'}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        config.log("Apagando...")
        state.persist()
        server.server_close()


if __name__ == "__main__":
    main()
