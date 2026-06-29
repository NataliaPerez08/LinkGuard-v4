"""Tests unitarios para peer_register/commands.py.

Mockea todas las dependencias (keys, identity, state, auth, nat, probe,
config_gen, utils) para verificar el flujo de cada comando
(cmd_register, cmd_heartbeat, cmd_run, cmd_request_network, cmd_rotate_key)
sin necesidad de sistema operativo ni RPC real.
"""

import json
import os
import time

import pytest
from unittest.mock import MagicMock, patch, PropertyMock


# ──────────────────────── Fixtures ────────────────────────


@pytest.fixture
def mock_deps(monkeypatch, tmp_path):
    """Monkeypatch todas las dependencias de commands.py antes de importar."""
    monkeypatch.setenv("WG_AUTO_STATE", str(tmp_path / "wg-auto.json"))
    monkeypatch.setenv("PEER_ID", "test-peer")

    mocks = {}

    mocks["keys"] = MagicMock()
    mocks["identity"] = MagicMock()
    mocks["state"] = MagicMock()
    mocks["auth"] = MagicMock()
    mocks["nat"] = MagicMock()
    mocks["probe"] = MagicMock()
    mocks["config_gen"] = MagicMock()
    mocks["utils"] = MagicMock()

    monkeypatch.setattr("peer_register.commands.gen_keys_if_needed", mocks["keys"].gen_keys_if_needed)
    monkeypatch.setattr("peer_register.commands.load_public_key", mocks["keys"].load_public_key)
    monkeypatch.setattr("peer_register.commands.rotate_keys", mocks["keys"].rotate_keys)
    monkeypatch.setattr("peer_register.commands.peer_id_default", mocks["identity"].peer_id_default)
    monkeypatch.setattr("peer_register.commands.peer_endpoint_guess", mocks["identity"].peer_endpoint_guess)
    monkeypatch.setattr("peer_register.commands.owner_default", mocks["identity"].owner_default)
    monkeypatch.setattr("peer_register.commands.load_state", mocks["state"].load_state)
    monkeypatch.setattr("peer_register.commands.save_state", mocks["state"].save_state)
    monkeypatch.setattr("peer_register.commands.orch_token_for_call", mocks["auth"].orch_token_for_call)
    monkeypatch.setattr("peer_register.commands.ensure_jwt_session", mocks["auth"].ensure_jwt_session)
    monkeypatch.setattr("peer_register.commands.detect_nat_type", mocks["nat"].detect_nat_type)
    monkeypatch.setattr("peer_register.commands.probe_direct_peers", mocks["probe"].probe_direct_peers)
    monkeypatch.setattr("peer_register.commands.apply_config", mocks["config_gen"].apply_config)
    monkeypatch.setattr("peer_register.commands.log", mocks["utils"].log)
    monkeypatch.setattr("peer_register.commands.run", mocks["utils"].run)
    monkeypatch.setattr("peer_register.commands.rpc", mocks["utils"].rpc)

    return mocks


@pytest.fixture
def mock_args():
    """Simula args del CLI argparse."""
    return MagicMock()


@ pytest.fixture
def fake_rpc_client(mock_deps):
    """Configura utils.rpc() para devolver un FakeRPCClient."""
    class FakeRPCClient:
        def __init__(self):
            self.calls = []

        def __getattr__(self, name):
            def _invoke(*args):
                self.calls.append((name, args))
                return {"peer_id": "test-peer", "config_version": 2, "wg_ip": "10.0.0.2/32"}
            return _invoke

    client = FakeRPCClient()
    mock_deps["utils"].rpc.return_value = client
    return client


# ──────────────────────── cmd_register ────────────────────────


class TestCmdRegister:
    def test_register_success(self, mock_deps, fake_rpc_client, mock_args):
        mock_deps["identity"].peer_id_default.return_value = "test-peer"
        mock_deps["keys"].load_public_key.return_value = "pubkey123"
        mock_deps["identity"].peer_endpoint_guess.return_value = "1.2.3.4:51820"
        mock_deps["identity"].owner_default.return_value = "test-user"
        mock_deps["auth"].orch_token_for_call.return_value = "jwt-token"
        mock_deps["state"].load_state.return_value = {}

        from peer_register.commands import cmd_register
        cmd_register(mock_args)

        assert mock_deps["keys"].gen_keys_if_needed.called
        assert mock_deps["keys"].load_public_key.called
        assert mock_deps["identity"].peer_id_default.called
        assert fake_rpc_client.calls[-1][0] == "peer.register"
        assert mock_deps["config_gen"].apply_config.called
        assert mock_deps["state"].save_state.called

    def test_register_applies_config(self, mock_deps, fake_rpc_client, mock_args):
        mock_deps["identity"].peer_id_default.return_value = "test-peer"
        mock_deps["keys"].load_public_key.return_value = "pubkey123"
        mock_deps["identity"].peer_endpoint_guess.return_value = ""
        mock_deps["state"].load_state.return_value = {}

        from peer_register.commands import cmd_register
        cmd_register(mock_args)

        apply_call = mock_deps["config_gen"].apply_config.call_args[0][0]
        assert apply_call == "test-peer"

    def test_register_show_wg(self, mock_deps, fake_rpc_client, mock_args):
        mock_deps["identity"].peer_id_default.return_value = "test-peer"
        mock_deps["keys"].load_public_key.return_value = "pubkey123"
        mock_deps["state"].load_state.return_value = {}

        from peer_register.commands import cmd_register
        cmd_register(mock_args)

        assert mock_deps["utils"].run.called


# ──────────────────────── cmd_heartbeat ────────────────────────


class TestCmdHeartbeat:
    def test_basic_heartbeat(self, mock_deps, mock_args):
        mock_deps["state"].load_state.return_value = {
            "peer_id": "test-peer",
            "config_version": 1,
            "topology": "hub-spoke",
        }
        mock_deps["identity"].peer_endpoint_guess.return_value = "1.2.3.4:51820"
        mock_deps["auth"].ensure_jwt_session.return_value = "jwt-token"

        class FakeRPC:
            def __getattr__(self, name):
                def _invoke(*a):
                    return {"heartbeat_ack": True, "desired_config_version": 1}
                return _invoke

        mock_deps["utils"].rpc.return_value = FakeRPC()
        mock_deps["utils"].run.return_value = "wg show output"

        from peer_register.commands import cmd_heartbeat
        cmd_heartbeat(mock_args)

        assert mock_deps["state"].load_state.called
        assert mock_deps["utils"].rpc.called

    def test_heartbeat_config_version_change(self, mock_deps, mock_args):
        mock_deps["state"].load_state.return_value = {
            "peer_id": "test-peer",
            "config_version": 1,
            "topology": "hub-spoke",
        }
        mock_deps["identity"].peer_endpoint_guess.return_value = "1.2.3.4:51820"
        mock_deps["auth"].ensure_jwt_session.return_value = "jwt-token"

        class FakeRPC:
            def __getattr__(self, name):
                def _invoke(*a):
                    return {"heartbeat_ack": True, "desired_config_version": 5}
                return _invoke

        mock_deps["utils"].rpc.return_value = FakeRPC()
        mock_deps["utils"].run.return_value = "wg show output"

        from peer_register.commands import cmd_heartbeat
        cmd_heartbeat(mock_args)

        assert mock_deps["config_gen"].apply_config.called
        save_call = mock_deps["state"].save_state.call_args[0][0]
        assert save_call["config_version"] == 5

    def test_heartbeat_mesh_peers_hash_change(self, mock_deps, mock_args):
        mock_deps["state"].load_state.side_effect = [
            {
                "peer_id": "test-peer",
                "config_version": 1,
                "mesh_peers_hash": "old-hash",
                "topology": "mesh",
            },
            {"peer_id": "test-peer", "config_version": 1, "topology": "mesh"},
        ]
        mock_deps["identity"].peer_endpoint_guess.return_value = "1.2.3.4:51820"
        mock_deps["auth"].ensure_jwt_session.return_value = "jwt-token"

        class FakeRPC:
            def __getattr__(self, name):
                def _invoke(*a):
                    return {
                        "heartbeat_ack": True,
                        "desired_config_version": 1,
                        "mesh_peers_hash": "new-hash",
                    }
                return _invoke

        mock_deps["utils"].rpc.return_value = FakeRPC()
        mock_deps["utils"].run.return_value = "wg show output"

        from peer_register.commands import cmd_heartbeat
        cmd_heartbeat(mock_args)

        assert mock_deps["config_gen"].apply_config.called

    def test_heartbeat_nat_cache(self, mock_deps, mock_args):
        old_ts = int(time.time()) - 600
        mock_deps["state"].load_state.return_value = {
            "peer_id": "test-peer",
            "config_version": 1,
            "nat_type_detected_ts": old_ts,
            "nat_type": "full-cone",
            "topology": "hub-spoke",
        }
        mock_deps["identity"].peer_endpoint_guess.return_value = "1.2.3.4:51820"
        mock_deps["auth"].ensure_jwt_session.return_value = "jwt-token"
        mock_deps["nat"].detect_nat_type.return_value = "symmetric"

        class FakeRPC:
            def __getattr__(self, name):
                def _invoke(*a):
                    return {"heartbeat_ack": True, "desired_config_version": 1}
                return _invoke

        mock_deps["utils"].rpc.return_value = FakeRPC()
        mock_deps["utils"].run.return_value = "wg show output"

        from peer_register.commands import cmd_heartbeat
        cmd_heartbeat(mock_args)

        assert mock_deps["nat"].detect_nat_type.called

    def test_heartbeat_nat_cache_hit(self, mock_deps, mock_args):
        recent_ts = int(time.time()) - 60
        mock_deps["state"].load_state.return_value = {
            "peer_id": "test-peer",
            "config_version": 1,
            "nat_type_detected_ts": recent_ts,
            "nat_type": "full-cone",
            "topology": "hub-spoke",
        }
        mock_deps["identity"].peer_endpoint_guess.return_value = "1.2.3.4:51820"
        mock_deps["auth"].ensure_jwt_session.return_value = "jwt-token"

        class FakeRPC:
            def __getattr__(self, name):
                def _invoke(*a):
                    return {"heartbeat_ack": True, "desired_config_version": 1}
                return _invoke

        mock_deps["utils"].rpc.return_value = FakeRPC()
        mock_deps["utils"].run.return_value = "wg show output"

        from peer_register.commands import cmd_heartbeat
        cmd_heartbeat(mock_args)

        assert not mock_deps["nat"].detect_nat_type.called

    def test_heartbeat_hub_mesh_triggers_probe(self, mock_deps, mock_args):
        mock_deps["state"].load_state.return_value = {
            "peer_id": "test-peer",
            "config_version": 1,
            "topology": "hub-mesh",
        }
        mock_deps["identity"].peer_endpoint_guess.return_value = "1.2.3.4:51820"
        mock_deps["auth"].ensure_jwt_session.return_value = "jwt-token"

        class FakeRPC:
            def __getattr__(self, name):
                def _invoke(*a):
                    return {"heartbeat_ack": True, "desired_config_version": 1}
                return _invoke

        mock_deps["utils"].rpc.return_value = FakeRPC()
        mock_deps["utils"].run.return_value = "wg show output"

        from peer_register.commands import cmd_heartbeat
        cmd_heartbeat(mock_args)

        assert mock_deps["probe"].probe_direct_peers.called


# ──────────────────────── cmd_run ────────────────────────


class TestCmdRun:
    def test_run_register_then_heartbeat_loop(self, mock_deps, mock_args):
        mock_deps["identity"].peer_id_default.return_value = "test-peer"
        mock_deps["keys"].load_public_key.return_value = "pubkey123"
        mock_deps["identity"].peer_endpoint_guess.return_value = "1.2.3.4:51820"
        mock_deps["auth"].ensure_jwt_session.return_value = "jwt-token"
        mock_deps["state"].load_state.return_value = {"peer_id": "test-peer", "config_version": 1}

        heartbeat_count = [0]

        class FakeRPC:
            def __getattr__(self, name):
                def _invoke(*a):
                    if name == "peer.heartbeat":
                        heartbeat_count[0] += 1
                        if heartbeat_count[0] >= 2:
                            raise KeyboardInterrupt()
                    return {"peer_id": "test-peer", "config_version": 2, "wg_ip": "10.0.0.2/32"}
                return _invoke

        mock_deps["utils"].rpc.return_value = FakeRPC()
        mock_deps["utils"].run.return_value = "wg show output"
        mock_deps["auth"].orch_token_for_call.return_value = "jwt-token"
        mock_args.interval = 1

        from peer_register.commands import cmd_run
        with pytest.raises(KeyboardInterrupt):
            cmd_run(mock_args)

        assert mock_deps["keys"].gen_keys_if_needed.called
        assert heartbeat_count[0] >= 2

    def test_run_register_fail_retries(self, mock_deps, mock_args):
        mock_deps["identity"].peer_id_default.side_effect = Exception("no peer id")
        mock_deps["state"].load_state.return_value = {"peer_id": "test-peer", "config_version": 1}

        heartbeat_count = [0]

        class FakeRPC:
            def __getattr__(self, name):
                def _invoke(*a):
                    if name == "peer.heartbeat":
                        heartbeat_count[0] += 1
                        if heartbeat_count[0] >= 2:
                            raise KeyboardInterrupt()
                    return {"heartbeat_ack": True, "desired_config_version": 1}
                return _invoke

        mock_deps["utils"].rpc.return_value = FakeRPC()
        mock_deps["utils"].run.return_value = "wg show output"
        mock_deps["auth"].ensure_jwt_session.return_value = "jwt-token"
        mock_args.interval = 1

        from peer_register.commands import cmd_run
        with pytest.raises(KeyboardInterrupt):
            cmd_run(mock_args)

        assert heartbeat_count[0] >= 2

    def test_run_heartbeat_fault(self, mock_deps, mock_args):
        mock_deps["identity"].peer_id_default.return_value = "test-peer"
        mock_deps["keys"].load_public_key.return_value = "pubkey123"
        mock_deps["identity"].peer_endpoint_guess.return_value = "1.2.3.4:51820"
        mock_deps["auth"].ensure_jwt_session.return_value = "jwt-token"
        mock_deps["state"].load_state.return_value = {"peer_id": "test-peer", "config_version": 1}

        from xmlrpc.client import Fault
        heartbeat_count = [0]

        class FakeRPC:
            def __getattr__(self, name):
                def _invoke(*a):
                    if name == "peer.heartbeat":
                        heartbeat_count[0] += 1
                        if heartbeat_count[0] == 1:
                            raise Fault(1, "test fault")
                        if heartbeat_count[0] >= 2:
                            raise KeyboardInterrupt()
                    return {"peer_id": "test-peer", "config_version": 2, "wg_ip": "10.0.0.2/32"}
                return _invoke

        mock_deps["utils"].rpc.return_value = FakeRPC()
        mock_deps["utils"].run.return_value = "wg show output"
        mock_deps["auth"].orch_token_for_call.return_value = "jwt-token"
        mock_args.interval = 1

        from peer_register.commands import cmd_run
        with pytest.raises(KeyboardInterrupt):
            cmd_run(mock_args)

        assert heartbeat_count[0] >= 2


# ──────────────────────── cmd_request_network ────────────────────────


class TestCmdRequestNetwork:
    def test_request_network_apply(self, mock_deps, mock_args):
        mock_deps["state"].load_state.return_value = {"peer_id": "test-peer"}
        mock_deps["identity"].peer_id_default.return_value = "test-peer"
        mock_deps["auth"].ensure_jwt_session.return_value = "jwt-token"
        mock_args.network_id = "lan1"
        mock_args.apply = True

        class FakeRPC:
            def __getattr__(self, name):
                def _invoke(*a):
                    return {"network_id": "lan1", "ip": "10.0.0.5", "config_version": 3}
                return _invoke

        mock_deps["utils"].rpc.return_value = FakeRPC()

        from peer_register.commands import cmd_request_network
        cmd_request_network(mock_args)

        assert mock_deps["config_gen"].apply_config.called

    def test_request_network_no_apply(self, mock_deps, mock_args):
        mock_deps["state"].load_state.return_value = {"peer_id": "test-peer"}
        mock_deps["identity"].peer_id_default.return_value = "test-peer"
        mock_deps["auth"].ensure_jwt_session.return_value = "jwt-token"
        mock_args.network_id = "lan1"
        mock_args.apply = False

        class FakeRPC:
            def __getattr__(self, name):
                def _invoke(*a):
                    return {"network_id": "lan1", "ip": "10.0.0.5", "config_version": 3}
                return _invoke

        mock_deps["utils"].rpc.return_value = FakeRPC()

        from peer_register.commands import cmd_request_network
        cmd_request_network(mock_args)

        assert not mock_deps["config_gen"].apply_config.called


# ──────────────────────── cmd_rotate_key ────────────────────────


class TestCmdRotateKey:
    def test_rotate_key(self, mock_deps, mock_args):
        mock_deps["state"].load_state.return_value = {"peer_id": "test-peer"}
        mock_deps["identity"].peer_id_default.return_value = "test-peer"
        mock_deps["auth"].ensure_jwt_session.return_value = "jwt-token"
        mock_deps["keys"].rotate_keys.return_value = ("new-priv", "new-pub")

        class FakeRPC:
            def __getattr__(self, name):
                def _invoke(*a):
                    return {"rotated": True, "config_version": 4}
                return _invoke

        mock_deps["utils"].rpc.return_value = FakeRPC()

        from peer_register.commands import cmd_rotate_key
        cmd_rotate_key(mock_args)

        assert mock_deps["keys"].rotate_keys.called
        assert mock_deps["config_gen"].apply_config.called
