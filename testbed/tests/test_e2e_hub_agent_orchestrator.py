"""Pruebas end-to-end: hub-agent + orchestrator in-process.

Levanta ambos servidores XML-RPC en hilos separados, mockeando solo las
llamadas a subprocess/wg/iptables del hub-agent, y verifica el ciclo de
vida completo: registro de peer → heartbeat → config → cleanup.
"""

import os
import sys
import threading
import time
import xmlrpc.client

import pytest
from unittest.mock import patch, MagicMock


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ORCH_DIR = os.path.join(BASE_DIR, "..", "..", "orchestrator-install-v2")
sys.path.insert(0, ORCH_DIR)


# ──────────────────────── Fixtures ────────────────────────


@pytest.fixture(scope="module")
def ports():
    return {
        "hub_agent": 19000,
        "orch": 19001,
    }


@pytest.fixture(scope="module", autouse=True)
def env(ports):
    os.environ.setdefault("ADMIN_TOKEN", "e2e-admin-token-xxx")
    os.environ.setdefault("HUB_AGENT_TOKEN", "e2e-hub-token-yyy")
    os.environ.setdefault("HUB_ENDPOINT", "127.0.0.1:51820")
    os.environ.setdefault("ORCH_PORT", str(ports["orch"]))
    os.environ.setdefault("AUTO_APPROVE_ENABLED", "0")
    os.environ.setdefault("HUB_RETRY_COUNT", "1")
    os.environ.setdefault("BACKUP_ENABLED", "0")
    os.environ.setdefault("EVENTS_LOG_PATH", "/dev/null")
    os.environ.setdefault("ORCH_STATE_PATH", "/tmp/e2e_ha_state.json")
    os.environ.setdefault("JWT_REVOKED_PATH", "/tmp/e2e_ha_jwt_revoked.json")
    os.environ.setdefault("JWT_SECRET_PATH", "/tmp/e2e_ha_jwt_secret")
    os.environ.setdefault("HUB_AGENT_URL", f"http://127.0.0.1:{ports['hub_agent']}/RPC2")
    # ensure JWT secret exists
    if not os.path.exists(os.environ["JWT_SECRET_PATH"]):
        import pathlib
        pathlib.Path(os.environ["JWT_SECRET_PATH"]).write_text("e2e-test-jwt-secret-32chars!!xxxxx")
    # ensure state file exists
    if not os.path.exists(os.environ["ORCH_STATE_PATH"]):
        import json
        with open(os.environ["ORCH_STATE_PATH"], "w") as f:
            json.dump({}, f)
    if not os.path.exists(os.environ["JWT_REVOKED_PATH"]):
        with open(os.environ["JWT_REVOKED_PATH"], "w") as f:
            f.write("{}")


@pytest.fixture(scope="module")
def hub_agent(ports):
    """Arranca hub-agent en un hilo, con subprocess completamente mockeado."""
    import importlib.util
    _spec = importlib.util.spec_from_file_location("hub_agent", os.path.join(BASE_DIR, "..", "..", "orchestrator-install-v2", "hub-agent.py"))
    ha = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(ha)

    ready = threading.Event()
    errors = []

    def _run():
        try:
            with patch.object(ha, "subprocess") as mock_sp:
                mock_run = MagicMock()
                mock_run.returncode = 0
                mock_sp.run.return_value = mock_run
                mock_sp.check_output.return_value = "interface: wg-HUB\n"
                mock_sp.CalledProcessError = __import__("subprocess").CalledProcessError

                with patch.object(ha, "shutil") as mock_sh:
                    mock_sh.which.return_value = "/usr/bin/wg"

                    with patch.object(ha, "check_dependencies", lambda: None):
                        with patch.object(ha, "validate_token_at_startup", lambda: None):
                            with patch.object(ha, "ensure_base_rules_internal", lambda: None):
                                from xmlrpc.server import SimpleXMLRPCServer
                                server = SimpleXMLRPCServer(
                                    ("127.0.0.1", ports["hub_agent"]),
                                    requestHandler=ha.Handler,
                                    allow_none=True,
                                    logRequests=False,
                                )
                                server.register_function(ha.hub_health, "hub.health")
                                server.register_function(ha.hub_public_key, "hub.public_key")
                                server.register_function(ha.hub_apply_peer, "hub.apply_peer")
                                server.register_function(ha.hub_remove_peer, "hub.remove_peer")
                                server.register_function(ha.hub_show, "hub.show")
                                server.register_function(ha.hub_list_mesh_peers, "hub.list_mesh_peers")
                                ready.set()
                                server.serve_forever()
        except Exception as e:
            errors.append(e)
            ready.set()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    ready.wait(timeout=5)
    if errors:
        pytest.fail(f"hub-agent failed to start: {errors[0]}")
    time.sleep(0.5)
    yield
    # daemon thread killed at process exit


@pytest.fixture(scope="module")
def orch_server(ports, hub_agent):
    """Arranca orchestrator conectado al hub-agent."""
    import orchestrator
    ready = threading.Event()
    errors = []

    def _run():
        try:
            from unittest.mock import patch as p
            with p("orchestrator.state.start_backup_loop", lambda: None):
                with p("orchestrator.hub_client.config.HUB_RETRY_COUNT", 1):
                    with p("orchestrator.hub_client.config.HUB_RETRY_DELAY", 0.1):
                        # Actual ServerProxy calls will go to our mock hub_agent
                        ready.set()
                        orchestrator.main()
        except Exception as e:
            errors.append(e)
            ready.set()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    ready.wait(timeout=5)
    if errors:
        pytest.fail(f"orchestrator failed to start: {errors[0]}")
    time.sleep(1)
    yield


@pytest.fixture(scope="module")
def rpc(ports, orch_server):
    """Cliente XML-RPC al orchestrator."""
    return xmlrpc.client.ServerProxy(
        f"http://127.0.0.1:{ports['orch']}/RPC2", allow_none=True
    )


@pytest.fixture(scope="module")
def admin_token():
    return os.environ["ADMIN_TOKEN"]


# ──────────────────────── Tests ────────────────────────


class TestE2EHubAgentOrch:
    def test_01_health(self, rpc):
        r = getattr(rpc, "orch.health")()
        assert r["status"] == "healthy"

    def test_02_create_user(self, rpc, admin_token):
        r = getattr(rpc, "orch.user-create")("e2e-user", 10, 10, {}, admin_token)
        assert "token" in r

    def test_03_create_network(self, rpc, admin_token):
        r = getattr(rpc, "network.create")(
            "e2e-net", "10.200.0.0/24", "e2e test", "e2e", "admin", admin_token
        )
        assert r["network_id"] == "e2e-net"

    def test_04_register_peer(self, rpc, admin_token):
        from orchestrator.auth import _jwt_encode, _issue_user_token
        _issue_user_token("e2e-user")
        jwt, _ = _jwt_encode({"user_id": "e2e-user", "scopes": ["peer:write"]}, 600)
        from orchestrator import state
        state.STATE["networks"]["default"] = {"cidr": "10.20.30.0/24"}
        r = getattr(rpc, "peer.register")(
            "e2e-peer1", "A" * 44, "1.2.3.4:51820", [], {}, jwt
        )
        assert "wg_ip" in r

    def test_05_heartbeat(self, rpc):
        from orchestrator.auth import _jwt_encode
        jwt, _ = _jwt_encode({"user_id": "e2e-user", "scopes": ["peer:write"]}, 600)
        r = getattr(rpc, "peer.heartbeat")(
            "e2e-peer1", {"wg": "ok", "endpoint": "1.2.3.4:51820"}, jwt
        )
        assert r["heartbeat_ack"] is True

    def test_06_config_get(self, rpc):
        from orchestrator.auth import _jwt_encode
        jwt, _ = _jwt_encode({
            "user_id": "e2e-user", "scopes": ["config:read"], "role": "admin",
        }, 600)
        r = getattr(rpc, "config.get_peer_config")("e2e-peer1", jwt)
        assert "interface" in r
        assert "peer" in r
        assert r["meta"]["topology"] == "hub-spoke"

    def test_07_metrics(self, rpc, admin_token):
        r = getattr(rpc, "orch.metrics")(admin_token)
        assert r["peers_total"] >= 1

    def test_08_cleanup(self, rpc, admin_token):
        r = getattr(rpc, "peer.unregister")("e2e-peer1", None, admin_token)
        assert r is True
        r = getattr(rpc, "network.delete")("e2e-net")
        assert r["deleted"] is True
        r = getattr(rpc, "orch.user-delete")("e2e-user", admin_token)
        assert "deleted" in str(r).lower()
