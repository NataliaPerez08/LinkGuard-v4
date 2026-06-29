"""Prueba end-to-end full stack: multi-tenant, topologias y transiciones.

Escenario:
  1. Crear 2 tenants (alice, bob), 2 redes, registrar peers en cada red
  2. Verificar config get para cada peer (hub-spoke default)
  3. Transicionar a mesh → verificar mesh_peers en config
  4. Transicionar a hub-mesh → verificar clasificacion direct/relay
  5. Cambiar NAT type y verificar efecto en clasificacion
  6. Rotar key de un peer
  7. Reportar reachability y verificar efecto
  8. Limpiar todo
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
    return {"hub_agent": 19010, "orch": 19011}


@pytest.fixture(scope="module", autouse=True)
def env(ports):
    os.environ.setdefault("ADMIN_TOKEN", "fs-admin-token")
    os.environ.setdefault("HUB_AGENT_TOKEN", "fs-hub-token")
    os.environ.setdefault("HUB_ENDPOINT", "127.0.0.1:51820")
    os.environ.setdefault("ORCH_PORT", str(ports["orch"]))
    os.environ.setdefault("AUTO_APPROVE_ENABLED", "0")
    os.environ.setdefault("HUB_RETRY_COUNT", "1")
    os.environ.setdefault("BACKUP_ENABLED", "0")
    os.environ.setdefault("EVENTS_LOG_PATH", "/dev/null")
    os.environ.setdefault("ORCH_STATE_PATH", "/tmp/e2e_fs_state.json")
    os.environ.setdefault("JWT_REVOKED_PATH", "/tmp/e2e_fs_jwt_revoked.json")
    os.environ.setdefault("JWT_SECRET_PATH", "/tmp/e2e_fs_jwt_secret")
    os.environ.setdefault("HUB_AGENT_URL", f"http://127.0.0.1:{ports['hub_agent']}/RPC2")
    # ensure JWT secret exists
    if not os.path.exists(os.environ["JWT_SECRET_PATH"]):
        import pathlib
        pathlib.Path(os.environ["JWT_SECRET_PATH"]).write_text("e2e-fs-test-jwt-secret-32chars!!")
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
    import importlib.util
    _spec = importlib.util.spec_from_file_location("hub_agent", os.path.join(ORCH_DIR, "hub-agent.py"))
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
                                    allow_none=True, logRequests=False,
                                )
                                server.register_function(ha.hub_health, "hub.health")
                                server.register_function(ha.hub_public_key, "hub.public_key")
                                server.register_function(ha.hub_apply_peer, "hub.apply_peer")
                                server.register_function(ha.hub_remove_peer, "hub.remove_peer")
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
        pytest.fail(f"hub-agent failed: {errors[0]}")
    time.sleep(0.5)
    yield


@pytest.fixture(scope="module")
def orch_server(ports, hub_agent):
    import orchestrator
    ready = threading.Event()
    errors = []

    def _run():
        try:
            with patch("orchestrator.state.start_backup_loop", lambda: None):
                with patch("orchestrator.hub_client.config.HUB_RETRY_COUNT", 1):
                    with patch("orchestrator.hub_client.config.HUB_RETRY_DELAY", 0.1):
                        ready.set()
                        orchestrator.main()
        except Exception as e:
            errors.append(e)
            ready.set()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    ready.wait(timeout=5)
    if errors:
        pytest.fail(f"orchestrator failed: {errors[0]}")
    time.sleep(1)
    yield


@pytest.fixture(scope="module")
def rpc(ports, orch_server):
    return xmlrpc.client.ServerProxy(
        f"http://127.0.0.1:{ports['orch']}/RPC2", allow_none=True
    )


@pytest.fixture(scope="module")
def AT():
    return os.environ["ADMIN_TOKEN"]


# ──────────────────────── Helpers ────────────────────────


def _jwt_for(uid, scopes=None, peer_write=False):
    from orchestrator.auth import _jwt_encode
    s = scopes or (["peer:write"] if peer_write else ["config:read"])
    t, _ = _jwt_encode({"user_id": uid, "scopes": s, "role": "admin"}, 600)
    return t


# ──────────────────────── Tests ────────────────────────


class TestE2EFullStack:
    AT = "fs-admin-token"

    def test_01_setup_tenants(self, rpc):
        from orchestrator.auth import _issue_user_token
        for uid in ("alice", "bob"):
            r = getattr(rpc, "orch.user-create")(uid, 10, 10, {}, self.AT)
            assert "token" in r
            _issue_user_token(uid)

    def test_02_create_networks(self, rpc):
        for net_id, cidr in [("alice-net", "10.10.0.0/24"), ("bob-net", "10.20.0.0/24")]:
            r = getattr(rpc, "network.create")(net_id, cidr, "desc", "tag", "admin", self.AT)
            assert r["network_id"] == net_id

    def test_03_register_peers(self, rpc):
        from orchestrator import state
        state.STATE["networks"]["default"] = {"cidr": "10.30.0.0/24"}
        peers = [
            ("alice-peer1", "alice", "alice-net", "A" * 44),
            ("alice-peer2", "alice", "alice-net", "B" * 44),
            ("bob-peer1", "bob", "bob-net", "C" * 44),
        ]
        for pid, uid, net, pk in peers:
            jwt = _jwt_for(uid, peer_write=True)
            r = getattr(rpc, "peer.register")(pid, pk, "1.2.3.4:51820", [], {}, jwt)
            assert "wg_ip" in r

    def test_04_config_hub_spoke(self, rpc):
        for pid in ("alice-peer1", "alice-peer2", "bob-peer1"):
            jwt = _jwt_for("alice" if "alice" in pid else "bob", ["config:read"])
            r = getattr(rpc, "config.get_peer_config")(pid, jwt)
            assert r["meta"]["topology"] == "hub-spoke"
            assert "interface" in r
            assert "peer" in r

    def test_05_transition_to_mesh(self, rpc):
        r = getattr(rpc, "network.set_topology")("default", "mesh")
        assert r["topology"] == "mesh"

    def test_06_config_mesh(self, rpc):
        jwt = _jwt_for("alice", ["config:read"])
        r = getattr(rpc, "config.get_peer_config")("alice-peer1", jwt)
        assert r["meta"]["topology"] == "mesh"
        assert "mesh_peers" in r
        assert "mesh_peers_hash" in r["meta"]

    def test_07_transition_to_hub_mesh(self, rpc):
        r = getattr(rpc, "network.set_topology")("default", "hub-mesh")
        assert r["topology"] == "hub-mesh"

    def test_08_config_hub_mesh(self, rpc):
        jwt = _jwt_for("alice", ["config:read"])
        r = getattr(rpc, "config.get_peer_config")("alice-peer1", jwt)
        assert r["meta"]["topology"] == "hub-mesh"
        assert "hub_mesh_direct_peers" in r
        assert "hub_mesh_relay_peers" in r
        assert "hub_mesh_peers_hash" in r["meta"]

    def test_09_symmetric_nat_classification(self, rpc):
        import time
        from orchestrator import state
        state.STATE["peers"]["alice-peer1"]["nat_type"] = "symmetric"
        state.STATE["peers"]["alice-peer2"]["last_heartbeat"] = int(time.time())
        state.STATE["peers"]["alice-peer2"]["nat_type"] = "full-cone"
        state.STATE["peers"]["alice-peer2"]["endpoint"] = "1.2.3.4:51820"
        jwt = _jwt_for("alice", ["config:read"])
        r = getattr(rpc, "config.get_peer_config")("alice-peer1", jwt)
        assert len(r["hub_mesh_relay_peers"]) >= 1

    def test_10_rotate_key(self, rpc):
        from orchestrator.auth import _jwt_encode
        jwt, _ = _jwt_encode({"user_id": "alice", "scopes": ["peer:write"], "role": "admin"}, 600)
        r = getattr(rpc, "peer.rotate_key")("alice-peer1", "Z" * 44, jwt)
        assert r["rotated"] is True

    def test_11_verify_rotated_key(self, rpc):
        jwt = _jwt_for("alice", ["config:read"])
        r = getattr(rpc, "config.get_peer_config")("alice-peer1", jwt)
        # The key rotation updated the peer's public_key
        from orchestrator import state
        assert state.STATE["peers"]["alice-peer1"]["public_key"] == "Z" * 44

    def test_12_report_reachability(self, rpc):
        from orchestrator.auth import _jwt_encode
        jwt, _ = _jwt_encode({"user_id": "alice", "scopes": ["peer:write"], "role": "admin"}, 600)
        r = getattr(rpc, "peer.report_reachability")("alice-peer1", "alice-peer2", True, jwt)
        assert r["recorded"] is True

    def test_13_verify_reachability(self, rpc):
        from orchestrator import state
        pmap = state.STATE["peers"]["alice-peer1"].get("reachability_map", {})
        assert pmap.get("alice-peer2") == "direct"

    def test_14_cleanup(self, rpc):
        for pid in ("alice-peer1", "alice-peer2"):
            r = getattr(rpc, "peer.unregister")(pid, None, self.AT)
            assert r is True
        r = getattr(rpc, "peer.unregister")("bob-peer1", None, self.AT)
        assert r is True
        for net_id in ("alice-net", "bob-net"):
            r = getattr(rpc, "network.delete")(net_id)
            assert r["deleted"] is True
        for uid in ("alice", "bob"):
            r = getattr(rpc, "orch.user-delete")(uid, self.AT)
            assert r.get("deleted") is True
