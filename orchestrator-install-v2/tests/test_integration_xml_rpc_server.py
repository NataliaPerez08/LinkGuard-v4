"""Tests de integracion del servidor XML-RPC del orchestrator.

Levanta el orchestrator real (main()) en un hilo background,
mockea hub_client para evitar dependencia del hub-agent real,
y hace llamadas XML-RPC autenticas via xmlrpc.client.ServerProxy.
"""

import os
import threading
import time
import xmlrpc.client

import pytest


# ──────────────────────── Fixtures ────────────────────────


@pytest.fixture(scope="module")
def orch_port():
    return int(os.environ.get("ORCH_PORT", "19999"))


@pytest.fixture(scope="module")
def admin_token():
    return os.environ.get("ADMIN_TOKEN", "test-admin-token-123")


@pytest.fixture(scope="module")
def orch_server(orch_port):
    """Arranca el orchestrator en un hilo background.

    Mockea hub_client para que no necesite un hub-agent real.
    """
    import threading
    import time
    from unittest.mock import patch, MagicMock

    errors = []

    def _run():
        try:
            with patch("orchestrator.hub_client.hub_ping", return_value=True):
                with patch("orchestrator.hub_client._hub_call_with_retry",
                          return_value=[{"public_key": "fake-hub-pubkey", "endpoint": None}]):
                    with patch("orchestrator.hub_client.hub_apply_peer", return_value=True):
                        with patch("orchestrator.hub_client.hub_remove_peer", return_value=True):
                            with patch("orchestrator.config.check_dependencies"):
                                with patch("orchestrator.config.validate_tokens_at_startup"):
                                    from orchestrator import main
                                    main()
        except Exception as e:
            import traceback
            errors.append((e, traceback.format_exc()))

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    # Wait for the server socket to be ready
    import socket
    for _ in range(20):
        time.sleep(0.5)
        if errors:
            exc, tb = errors[0]
            pytest.fail(f"Orchestrator failed to start: {exc}")
        try:
            s = socket.create_connection(("127.0.0.1", orch_port), timeout=1)
            s.close()
            break
        except (ConnectionRefusedError, OSError):
            continue
    else:
        if errors:
            exc, tb = errors[0]
            pytest.fail(f"Orchestrator failed to start: {exc}")
        pytest.fail("Orchestrator did not start in time")

    yield
    # No easy way to stop serve_forever() without KeyboardInterrupt,
    # but daemon=True kills it at process exit.


@pytest.fixture(scope="module")
def rpc_client(orch_port, orch_server):
    """Cliente XML-RPC apuntando al orchestrator de prueba (requiere orch_server)."""
    return xmlrpc.client.ServerProxy(
        f"http://127.0.0.1:{orch_port}/RPC2", allow_none=True
    )


def xml(client, method, *args):
    """Invoca un metodo XML-RPC."""
    return getattr(client, method)(*args)


# ──────────────────────── Tests ────────────────────────


class TestIntegrationOrch:
    def test_health(self, rpc_client):
        r = xml(rpc_client, "orch.health")
        assert r["status"] == "healthy"

    def test_user_crud(self, rpc_client, admin_token):
        r = xml(rpc_client, "orch.user-create", "inttest-user", 5, 5, {}, admin_token)
        assert "token" in r

        r = xml(rpc_client, "orch.user-list", admin_token)
        assert "inttest-user" in str(r)

        r = xml(rpc_client, "orch.user-get", "inttest-user", admin_token)
        assert r["user_id"] == "inttest-user"

        r = xml(rpc_client, "orch.issue-user-token", "inttest-user", admin_token)
        assert "token" in r

    def test_user_create_duplicate(self, rpc_client, admin_token):
        with pytest.raises(Exception):
            xml(rpc_client, "orch.user-create", "inttest-user", 5, 5, {}, admin_token)

    def test_user_delete(self, rpc_client, admin_token):
        r = xml(rpc_client, "orch.user-delete", "inttest-user", admin_token)
        assert r.get("deleted") is True

    def test_network_crud(self, rpc_client, admin_token):
        r = xml(rpc_client, "network.create", "intnet1", "10.100.0.0/24",
                "integration net", "test", "admin", admin_token)
        assert r["network_id"] == "intnet1"

        r = xml(rpc_client, "network.get", "intnet1")
        assert r["network"]["cidr"] == "10.100.0.0/24"

        r = xml(rpc_client, "network.set_topology", "intnet1", "mesh")
        assert r["topology"] == "mesh"

        r = xml(rpc_client, "network.get_topology", "intnet1")
        assert "peers" in r

        r = xml(rpc_client, "network.list", admin_token)
        assert "intnet1" in str(r)

    def test_peer_register(self, rpc_client, admin_token):
        from orchestrator import state
        state.STATE["users"]["inttest-user"] = {"max_peers": 5, "max_networks": 5}
        state.STATE["networks"]["default"] = {"cidr": "10.20.30.0/24"}

        from orchestrator.auth import _jwt_encode, _issue_user_token
        _issue_user_token("inttest-user")
        jwt_token, _ = _jwt_encode({
            "user_id": "inttest-user", "scopes": ["peer:write"],
        }, 600)

        r = xml(rpc_client, "peer.register", "intpeer1", "A" * 44,
                "1.2.3.4:51820", [], {}, jwt_token)
        assert "wg_ip" in r

    def test_peer_get(self, rpc_client):
        r = xml(rpc_client, "peer.get", "intpeer1")
        assert r["peer"]["public_key"] == "A" * 44

    def test_peer_list(self, rpc_client, admin_token):
        r = xml(rpc_client, "peer.list")
        assert "intpeer1" in str(r)

    def test_peer_heartbeat(self, rpc_client):
        from orchestrator.auth import _jwt_encode
        jwt_token, _ = _jwt_encode({
            "user_id": "inttest-user", "scopes": ["peer:write"],
        }, 600)
        r = xml(rpc_client, "peer.heartbeat", "intpeer1",
                {"wg": "ok", "endpoint": "5.6.7.8:51820", "nat_type": "full-cone"},
                jwt_token)
        assert r["heartbeat_ack"] is True

    def test_config_get_peer_config(self, rpc_client):
        from orchestrator.auth import _jwt_encode
        jwt_token, _ = _jwt_encode({
            "user_id": "inttest-user", "scopes": ["config:read"], "role": "admin",
        }, 600)
        r = xml(rpc_client, "config.get_peer_config", "intpeer1", jwt_token)
        assert "interface" in r
        assert "peer" in r

    def test_peer_unregister(self, rpc_client, admin_token):
        r = xml(rpc_client, "peer.unregister", "intpeer1", None, admin_token)
        assert r is True

    def test_network_delete(self, rpc_client):
        r = xml(rpc_client, "network.delete", "intnet1")
        assert r["deleted"] is True

    def test_jwt_lifecycle(self, rpc_client):
        from orchestrator.auth import _issue_user_token
        _issue_user_token("jwt-user")
        jwt_token, _ = (None, None)

        r = xml(rpc_client, "auth.login", "jwt-user", None,
                _issue_user_token("jwt-user"))
        assert "jwt" in r
        jwt_token = r["jwt"]

        r = xml(rpc_client, "auth.whoami", jwt_token)
        assert r["user_id"] == "jwt-user"

        r = xml(rpc_client, "auth.refresh", jwt_token)
        assert "jwt" in r

    def test_metrics(self, rpc_client, admin_token):
        r = xml(rpc_client, "orch.metrics", admin_token)
        assert "peers_total" in r

    def test_events(self, rpc_client):
        r = xml(rpc_client, "orch.events")
        assert "events" in r

    def test_error_mapping(self, rpc_client):
        """Verifica que errores se mapean a Fault XML-RPC."""
        with pytest.raises(xmlrpc.client.Fault):
            xml(rpc_client, "peer.get", "nonexistent-peer-xxx")

    def test_health_without_auth(self, rpc_client):
        r = xml(rpc_client, "orch.health")
        assert r["status"] == "healthy"
