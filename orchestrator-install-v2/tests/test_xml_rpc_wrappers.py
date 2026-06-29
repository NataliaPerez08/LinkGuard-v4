"""Tests unitarios para el modulo __init__.py (wrappers XML-RPC).

Verifica que cada `_xml_*` wrapper:
  1. Construye el dict params correcto a partir de args posicionales
  2. Delega al handler endpoint correspondiente via _safe_call
  3. Aplica auth checks (admin_token, JWT) correctamente
  4. Mapea excepciones a Fault XML-RPC via _safe_call
"""

import threading
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from xmlrpc.client import Fault


# ──────────────────────── _safe_call ────────────────────────


class TestSafeCall:
    def test_handler_ok(self):
        from orchestrator import _safe_call
        result = _safe_call(lambda p: {"ok": True}, {})
        assert result == {"ok": True}

    def test_permission_error(self):
        from orchestrator import _safe_call
        def h(p):
            raise PermissionError("access denied")
        with pytest.raises(Fault) as exc:
            _safe_call(h, {})
        assert "403:" in str(exc.value)

    def test_key_error(self):
        from orchestrator import _safe_call
        def h(p):
            raise KeyError("not found")
        with pytest.raises(Fault) as exc:
            _safe_call(h, {})
        assert "404:" in str(exc.value)

    def test_value_error(self):
        from orchestrator import _safe_call
        def h(p):
            raise ValueError("bad input")
        with pytest.raises(Fault) as exc:
            _safe_call(h, {})
        assert "400:" in str(exc.value)

    def test_runtime_error(self):
        from orchestrator import _safe_call
        def h(p):
            raise RuntimeError("service unavailable")
        with pytest.raises(Fault) as exc:
            _safe_call(h, {})
        assert "503:" in str(exc.value)


# ──────────────────────── Auth wrappers ────────────────────────


class TestXmlLogin:
    def test_login_success(self, init_state):
        from orchestrator.auth import _issue_user_token
        tok = _issue_user_token("alice")
        from orchestrator import _xml_login
        r = _xml_login("alice", None, tok)
        assert "jwt" in r
        assert "expires_at" in r

    def test_login_missing_args(self):
        from orchestrator import _xml_login
        with pytest.raises(ValueError, match="user_id"):
            _xml_login("", "", "")

    def test_login_bad_token(self, init_state):
        from orchestrator.auth import _issue_user_token
        _issue_user_token("alice")
        from orchestrator import _xml_login
        with pytest.raises(PermissionError):
            _xml_login("alice", None, "wrong-token")


class TestXmlRefresh:
    def test_refresh_valid(self, init_state):
        from orchestrator.auth import _issue_user_token
        tok = _issue_user_token("alice")
        from orchestrator import _xml_login, _xml_refresh
        r1 = _xml_login("alice", None, tok)
        r2 = _xml_refresh(r1["jwt"])
        assert "jwt" in r2

    def test_refresh_revoked(self, init_state):
        from orchestrator.auth import _issue_user_token
        tok = _issue_user_token("alice")
        from orchestrator import _xml_login, _xml_refresh
        from orchestrator.auth import _revoke_jti
        import jwt as pyjwt
        r1 = _xml_login("alice", None, tok)
        payload = pyjwt.decode(r1["jwt"], options={"verify_signature": False})
        _revoke_jti(payload["jti"], "test", 9999999999)
        with pytest.raises(PermissionError, match="jwt revoked"):
            _xml_refresh(r1["jwt"])

    def test_refresh_expired(self, init_state):
        from orchestrator.auth import _jwt_encode
        from orchestrator import _xml_refresh
        import time
        token, _ = _jwt_encode({"user_id": "alice"}, 1)
        time.sleep(2)
        with pytest.raises(Exception):
            _xml_refresh(token)


class TestXmlWhoami:
    def test_whoami(self, init_state):
        from orchestrator.auth import _issue_user_token
        tok = _issue_user_token("alice")
        from orchestrator import _xml_login, _xml_whoami
        r1 = _xml_login("alice", None, tok)
        p = _xml_whoami(r1["jwt"])
        assert p["user_id"] == "alice"
        assert "iat" not in p


# ──────────────────────── Orch endpoints — delegation ────────────────────────


class TestXmlOrchEndpoints:
    def test_health(self, init_state):
        from orchestrator import _xml_health
        with patch("orchestrator.endpoints_orch.rpc_health", return_value={"status": "healthy"}):
            r = _xml_health()
            assert r["status"] == "healthy"

    def test_metrics(self, init_state):
        from orchestrator import _xml_metrics
        with patch("orchestrator.endpoints_orch.rpc_metrics", return_value={"peers_total": 0}):
            r = _xml_metrics("admintoken")
            assert r["peers_total"] == 0

    def test_events(self, init_state):
        from orchestrator import _xml_events
        with patch("orchestrator.endpoints_orch.rpc_events", return_value={"events": []}):
            r = _xml_events()
            assert "events" in r


# ──────────────────────── User wrappers ────────────────────────


class TestXmlUserWrappers:
    def test_user_create_5_args(self, init_state):
        from orchestrator import _xml_user_create
        with patch("orchestrator.endpoints_users.rpc_user_create") as mock_create:
            mock_create.return_value = {"user_id": "bob"}
            r = _xml_user_create("bob", "5", "3", {}, "test-admin-token-123")
            assert r["user_id"] == "bob"

    def test_user_create_2_args_cli_convention(self, init_state):
        from orchestrator import _xml_user_create
        with patch("orchestrator.endpoints_users.rpc_user_create") as mock_create:
            mock_create.return_value = {"user_id": "bob"}
            r = _xml_user_create("bob", "test-admin-token-123")
            assert r["user_id"] == "bob"

    def test_user_list(self, init_state):
        from orchestrator import _xml_user_list
        with patch("orchestrator.endpoints_users.rpc_user_list") as mock_list:
            mock_list.return_value = {"users": {"alice": {}}}
            r = _xml_user_list("test-admin-token-123")
            assert "alice" in r["users"]

    def test_user_get(self, init_state):
        from orchestrator.auth import _issue_user_token
        _issue_user_token("alice")
        from orchestrator import _xml_user_get
        r = _xml_user_get("alice", "test-admin-token-123")
        assert r["user_id"] == "alice"

    def test_user_delete(self, init_state):
        from orchestrator import _xml_user_delete
        from orchestrator.auth import _issue_user_token
        _issue_user_token("alice")
        with patch("orchestrator.endpoints_users.rpc_user_delete") as mock_del:
            mock_del.return_value = {"deleted": True}
            r = _xml_user_delete("alice", "test-admin-token-123")
            assert r["deleted"] is True

    def test_issue_user_token(self, init_state):
        from orchestrator import _xml_issue_user_token
        r = _xml_issue_user_token("alice", "test-admin-token-123")
        assert "token" in r

    def test_revoke(self, init_state):
        from orchestrator import _xml_revoke
        from orchestrator.auth import _jwt_encode
        from orchestrator.auth import _issue_user_token
        _issue_user_token("alice")
        token, _ = _jwt_encode({"user_id": "alice"}, 600)
        with patch("orchestrator.endpoints_auth.rpc_jwt_revoke") as mock_revoke:
            mock_revoke.return_value = {"revoked": True}
            r = _xml_revoke(token, "test reason", "test-admin-token-123")
            assert r["revoked"] is True


# ──────────────────────── Network wrappers ────────────────────────


class TestXmlNetworkWrappers:
    def test_create(self, init_state):
        from orchestrator import _xml_network_create
        with patch("orchestrator.endpoints_networks.rpc_network_create") as mock:
            mock.return_value = {"network_id": "n1"}
            r = _xml_network_create("n1", "10.0.0.0/24", "desc", "tag", "admin", "test-admin-token-123")
            assert r["network_id"] == "n1"

    def test_list(self, init_state):
        from orchestrator import _xml_network_list
        with patch("orchestrator.endpoints_networks.rpc_network_list") as mock:
            mock.return_value = {"networks": {}}
            r = _xml_network_list()
            assert "networks" in r

    def test_get(self, init_state):
        from orchestrator import _xml_network_get
        with patch("orchestrator.endpoints_networks.rpc_network_get") as mock:
            mock.return_value = {"network": {"cidr": "10.0.0.0/24"}}
            r = _xml_network_get("n1")
            assert r["network"]["cidr"] == "10.0.0.0/24"

    def test_delete(self, init_state):
        from orchestrator import _xml_network_delete
        with patch("orchestrator.endpoints_networks.rpc_network_delete") as mock:
            mock.return_value = {"deleted": True}
            r = _xml_network_delete("n1")
            assert r["deleted"] is True

    def test_set_topology(self, init_state):
        from orchestrator import _xml_network_set_topology
        with patch("orchestrator.endpoints_networks.rpc_network_set_topology") as mock:
            mock.return_value = {"topology": "mesh"}
            r = _xml_network_set_topology("n1", "mesh")
            assert r["topology"] == "mesh"

    def test_get_topology(self, init_state):
        from orchestrator import _xml_network_get_topology
        with patch("orchestrator.endpoints_networks.rpc_network_get_topology") as mock:
            mock.return_value = {"network_id": "n1", "peers": {}}
            r = _xml_network_get_topology("n1")
            assert r["network_id"] == "n1"


# ──────────────────────── Config wrappers ────────────────────────


class TestXmlConfigWrappers:
    def test_get_mesh_peers(self, init_state):
        from orchestrator import _xml_config_get_mesh_peers
        with patch("orchestrator.endpoints_config.rpc_config_get_mesh_peers") as mock:
            mock.return_value = {"direct": [], "relay_only": []}
            r = _xml_config_get_mesh_peers("p1", "n1", "jwt-token")
            assert "direct" in r

    def test_get_peer_config(self, init_state):
        from orchestrator import _xml_config_get_peer_config
        with patch("orchestrator.endpoints_config.rpc_config_get_peer_config") as mock:
            mock.return_value = {"interface": {}, "peer": {}}
            r = _xml_config_get_peer_config("p1", "jwt-token")
            assert "interface" in r


# ──────────────────────── Peer wrappers ────────────────────────


class TestXmlPeerWrappers:
    def test_list(self, init_state):
        from orchestrator import _xml_peer_list
        with patch("orchestrator.endpoints_peers.rpc_peer_list") as mock:
            mock.return_value = {"peers": {}}
            r = _xml_peer_list()
            assert "peers" in r

    def test_get(self, init_state):
        from orchestrator import _xml_peer_get
        with patch("orchestrator.endpoints_peers.rpc_peer_get") as mock:
            mock.return_value = {"peer": {"public_key": "pk"}}
            r = _xml_peer_get("p1")
            assert r["peer"]["public_key"] == "pk"

    def test_register(self, init_state):
        from orchestrator import _xml_peer_register
        with patch("orchestrator.endpoints_peers.rpc_peer_register") as mock:
            mock.return_value = {"peer_id": "p1", "wg_ip": "10.0.0.2/32"}
            r = _xml_peer_register("p1", "pubkey123", "1.2.3.4:51820", [], {}, "jwt-token")
            assert r["peer_id"] == "p1"

    def test_heartbeat_with_remote_addr(self, init_state):
        from orchestrator import _xml_peer_heartbeat, _rpc_context
        _rpc_context.client_address = ("10.0.0.99", 54321)
        try:
            with patch("orchestrator.endpoints_peers.rpc_peer_heartbeat") as mock:
                mock.return_value = {"heartbeat_ack": True}
                r = _xml_peer_heartbeat("p1", {"wg": "ok"}, "jwt-token")
                assert r["heartbeat_ack"] is True
                args, _ = mock.call_args
                assert args[0]["remote_addr"] == "10.0.0.99"
        finally:
            _rpc_context.client_address = None

    def test_request_network(self, init_state):
        from orchestrator import _xml_peer_request_network
        with patch("orchestrator.endpoints_peers.rpc_peer_request_network") as mock:
            mock.return_value = {"network_id": "n1", "ip": "10.0.0.5"}
            r = _xml_peer_request_network("p1", "n1", "jwt-token")
            assert r["ip"] == "10.0.0.5"

    def test_rotate_key(self, init_state):
        from orchestrator import _xml_peer_rotate_key
        with patch("orchestrator.endpoints_peers.rpc_peer_rotate_key") as mock:
            mock.return_value = {"rotated": True}
            r = _xml_peer_rotate_key("p1", "new-pubkey", "jwt-token")
            assert r["rotated"] is True

    def test_report_reachability(self, init_state):
        from orchestrator import _xml_peer_report_reachability
        with patch("orchestrator.endpoints_peers.rpc_peer_report_reachability") as mock:
            mock.return_value = {"recorded": True}
            r = _xml_peer_report_reachability("p1", "p2", True, "jwt-token")
            assert r["recorded"] is True

    def test_update_admin(self, init_state):
        from orchestrator import _xml_peer_update_admin
        with patch("orchestrator.endpoints_peers.rpc_peer_update_admin") as mock:
            mock.return_value = True
            r = _xml_peer_update_admin("p1", {"tags": ["t1"]}, "test-admin-token-123")
            assert r is True

    def test_unregister(self, init_state):
        from orchestrator import _xml_peer_unregister
        with patch("orchestrator.endpoints_peers.rpc_peer_unregister") as mock:
            mock.return_value = True
            r = _xml_peer_unregister("p1", "jwt-token", "test-admin-token-123")
            assert r is True

    def test_assign_network(self, init_state):
        from orchestrator import _xml_peer_assign_network
        with patch("orchestrator.endpoints_peers.rpc_peer_assign_network") as mock:
            mock.return_value = True
            r = _xml_peer_assign_network("p1", "n1", "10.0.0.5", None, "test-admin-token-123")
            assert r is True

    def test_remove_from_network(self, init_state):
        from orchestrator import _xml_peer_remove_from_network
        with patch("orchestrator.endpoints_peers.rpc_peer_remove_from_network") as mock:
            mock.return_value = True
            r = _xml_peer_remove_from_network("p1", "n1", "test-admin-token-123")
            assert r is True


# ──────────────────────── _register_xml_handlers ────────────────────────


class TestRegisterXmlHandlers:
    def test_all_handlers_registered(self):
        from orchestrator import _register_xml_handlers
        server = MagicMock()
        _register_xml_handlers(server)
        expected_names = [
            "auth.login", "auth.refresh", "auth.whoami",
            "orch.health", "orch.metrics", "orch.events",
            "orch.user-create", "orch.user-list", "orch.user-get",
            "orch.user-delete", "orch.issue-user-token", "orch.revoke",
            "network.create", "network.list", "network.get",
            "network.get_topology", "network.delete", "network.set_topology",
            "config.get_mesh_peers", "config.get_peer_config",
            "peer.list", "peer.register", "peer.get",
            "peer.heartbeat", "peer.request_network", "peer.rotate_key",
            "peer.report_reachability", "peer.update_admin",
            "peer.unregister", "peer.assign_network", "peer.remove_from_network",
        ]
        assert server.register_function.call_count == len(expected_names)
        from unittest.mock import ANY
        for name in expected_names:
            server.register_function.assert_any_call(ANY, name)


# ──────────────────────── main() ────────────────────────


class TestMain:
    def test_main_bootstrap(self, monkeypatch, init_state):
        import orchestrator
        mock_server = MagicMock()
        monkeypatch.setattr(orchestrator, "_Server", lambda *a, **kw: mock_server)
        monkeypatch.setattr(orchestrator.config, "check_dependencies", lambda: None)
        monkeypatch.setattr(orchestrator.config, "validate_tokens_at_startup", lambda: None)
        monkeypatch.setattr(orchestrator.state, "load_state", lambda: None)
        monkeypatch.setattr(orchestrator.state, "start_backup_loop", lambda: None)
        monkeypatch.setattr(orchestrator.hub_client, "hub_ping", lambda: True)
        orchestrator.main()
        assert mock_server.serve_forever.called

    def test_main_with_keyboard_interrupt(self, monkeypatch, init_state):
        import orchestrator
        mock_server = MagicMock()
        mock_server.serve_forever.side_effect = KeyboardInterrupt()
        monkeypatch.setattr(orchestrator, "_Server", lambda *a, **kw: mock_server)
        monkeypatch.setattr(orchestrator.config, "check_dependencies", lambda: None)
        monkeypatch.setattr(orchestrator.config, "validate_tokens_at_startup", lambda: None)
        monkeypatch.setattr(orchestrator.state, "load_state", lambda: None)
        monkeypatch.setattr(orchestrator.state, "start_backup_loop", lambda: None)
        monkeypatch.setattr(orchestrator.hub_client, "hub_ping", lambda: True)
        orchestrator.main()
        assert mock_server.server_close.called
