import pytest
from unittest.mock import patch, MagicMock


class TestOrchEndpoints:
    def test_health(self, sample_state):
        from orchestrator.endpoints_orch import rpc_health
        r = rpc_health({})
        assert r["status"] == "healthy"
        assert r["peers_count"] >= 1
        assert r["networks_count"] >= 1

    def test_state_dump(self, sample_state):
        from orchestrator.endpoints_orch import rpc_state_dump
        r = rpc_state_dump({})
        assert "state" in r

    def test_state_persist(self, sample_state):
        from orchestrator.endpoints_orch import rpc_state_persist
        r = rpc_state_persist({})
        assert r["persisted"] is True

    def test_events_empty(self, sample_state):
        from orchestrator.endpoints_orch import rpc_events
        r = rpc_events({})
        assert "events" in r

    def test_metrics_admin(self, sample_state):
        from orchestrator.endpoints_orch import rpc_metrics
        r = rpc_metrics({"token": "test-admin-token-123"})
        assert r.get("peers_total") == 1
        assert r.get("users_total") == 1
        assert r.get("networks_total") == 1

    def test_metrics_no_auth(self, sample_state):
        from orchestrator.endpoints_orch import rpc_metrics
        with pytest.raises(PermissionError):
            rpc_metrics({"token": None})


class TestUserEndpoints:
    def test_create(self, init_state):
        from orchestrator.endpoints_users import rpc_user_create
        r = rpc_user_create({"user_id": "bob", "max_peers": 3, "max_networks": 2})
        assert r["user_id"] == "bob"
        assert "token" in r

    def test_create_duplicate(self, init_state):
        from orchestrator.endpoints_users import rpc_user_create
        rpc_user_create({"user_id": "bob"})
        with pytest.raises(ValueError, match="already exists"):
            rpc_user_create({"user_id": "bob"})

    def test_list(self, init_state):
        from orchestrator.endpoints_users import rpc_user_create, rpc_user_list
        rpc_user_create({"user_id": "bob"})
        r = rpc_user_list({})
        assert "bob" in r["users"]

    def test_delete(self, init_state):
        from orchestrator.endpoints_users import rpc_user_create, rpc_user_delete
        rpc_user_create({"user_id": "bob"})
        r = rpc_user_delete({"user_id": "bob"})
        assert r["deleted"] is True

    def test_delete_missing(self, init_state):
        from orchestrator.endpoints_users import rpc_user_delete
        with pytest.raises(KeyError):
            rpc_user_delete({"user_id": "nonexistent"})

    def test_token_reset(self, init_state):
        from orchestrator.endpoints_users import rpc_user_create, rpc_user_token_reset
        rpc_user_create({"user_id": "bob"})
        r = rpc_user_token_reset({"user_id": "bob"})
        assert "token" in r

    def test_disable(self, init_state):
        from orchestrator.endpoints_users import rpc_user_create, rpc_user_disable
        rpc_user_create({"user_id": "bob"})
        r = rpc_user_disable({"user_id": "bob"})
        assert r["disabled"] is True


class TestNetworkEndpoints:
    def test_create(self, init_state):
        from orchestrator.endpoints_networks import rpc_network_create
        r = rpc_network_create({"net_id": "n1", "cidr": "10.0.0.0/24", "user_id": "admin"})
        assert r["network_id"] == "n1"

    def test_create_duplicate(self, init_state):
        from orchestrator.endpoints_networks import rpc_network_create
        rpc_network_create({"net_id": "n1", "cidr": "10.0.0.0/24", "user_id": "admin"})
        with pytest.raises(ValueError, match="already exists"):
            rpc_network_create({"net_id": "n1", "cidr": "10.0.0.0/24", "user_id": "admin"})

    def test_list(self, init_state):
        from orchestrator.endpoints_networks import rpc_network_create, rpc_network_list
        rpc_network_create({"net_id": "n1", "cidr": "10.0.0.0/24"})
        r = rpc_network_list({})
        assert "n1" in r["networks"]

    def test_get(self, init_state):
        from orchestrator.endpoints_networks import rpc_network_create, rpc_network_get
        rpc_network_create({"net_id": "n1", "cidr": "10.0.0.0/24"})
        r = rpc_network_get({"network_id": "n1"})
        assert r["network"]["cidr"] == "10.0.0.0/24"

    def test_get_missing(self, init_state):
        from orchestrator.endpoints_networks import rpc_network_get
        with pytest.raises(KeyError):
            rpc_network_get({"network_id": "nonexistent"})

    def test_delete(self, init_state):
        from orchestrator.endpoints_networks import rpc_network_create, rpc_network_delete
        rpc_network_create({"net_id": "n1", "cidr": "10.0.0.0/24"})
        r = rpc_network_delete({"network_id": "n1"})
        assert r["deleted"] is True

    def test_set_topology(self, init_state):
        from orchestrator.endpoints_networks import rpc_network_create, rpc_network_set_topology
        rpc_network_create({"net_id": "n1", "cidr": "10.0.0.0/24"})
        r = rpc_network_set_topology({"network_id": "n1", "topology": "mesh"})
        assert r["topology"] == "mesh"

    def test_set_topology_invalid(self, init_state):
        from orchestrator.endpoints_networks import rpc_network_create, rpc_network_set_topology
        rpc_network_create({"net_id": "n1", "cidr": "10.0.0.0/24"})
        with pytest.raises(ValueError):
            rpc_network_set_topology({"network_id": "n1", "topology": "invalid"})

    def test_network_peers(self, sample_state):
        from orchestrator.endpoints_networks import rpc_network_peers
        r = rpc_network_peers({"network_id": "lan1"})
        assert r["count"] == 1

    def test_get_topology(self, sample_state):
        from orchestrator import state
        from orchestrator.endpoints_networks import rpc_network_get_topology
        state.STATE["networks"]["lan1"]["alloc"] = {"assigned": {"p1": "10.0.0.1"}}
        r = rpc_network_get_topology({"network_id": "lan1"})
        assert r["network_id"] == "lan1"
        assert "p1" in r["peers"]


class TestPeerEndpoints:
    def test_create(self, init_state):
        from orchestrator.endpoints_peers import rpc_peer_create
        from orchestrator import state
        state.STATE["users"]["admin"] = {"max_peers": 50, "max_networks": 10}
        state.STATE["networks"]["default"] = {"cidr": "10.20.30.0/24"}
        r = rpc_peer_create({"public_key": "pk_test", "peer_id": "p_test", "user_id": "admin"})
        assert r["peer_id"] == "p_test"

    def test_get(self, sample_state):
        from orchestrator.endpoints_peers import rpc_peer_get
        r = rpc_peer_get({"peer_id": "p1"})
        assert r["peer"]["public_key"] == "pk_p1"

    def test_get_missing(self, sample_state):
        from orchestrator.endpoints_peers import rpc_peer_get
        with pytest.raises(KeyError):
            rpc_peer_get({"peer_id": "nonexistent"})

    def test_list(self, sample_state):
        from orchestrator.endpoints_peers import rpc_peer_list
        r = rpc_peer_list({})
        assert "p1" in r["peers"]

    def test_update(self, sample_state):
        from orchestrator.endpoints_peers import rpc_peer_update
        r = rpc_peer_update({"peer_id": "p1", "endpoint": "1.2.3.4:51820"})
        assert r["updated"] is True

    def test_delete(self, sample_state):
        from orchestrator.endpoints_peers import rpc_peer_delete
        r = rpc_peer_delete({"peer_id": "p1"})
        assert r["deleted"] is True

    def test_enable(self, sample_state):
        from orchestrator.endpoints_peers import rpc_peer_enable
        r = rpc_peer_enable({"peer_id": "p1"})
        assert r["enabled"] is True

    def test_disable(self, sample_state):
        from orchestrator.endpoints_peers import rpc_peer_disable
        r = rpc_peer_disable({"peer_id": "p1"})
        assert r["disabled"] is True

    def test_heartbeat(self, sample_state):
        from orchestrator.endpoints_peers import rpc_peer_heartbeat
        r = rpc_peer_heartbeat({"peer_id": "p1"})
        assert r["heartbeat_ack"] is True

    def test_set_metadata(self, sample_state):
        from orchestrator.endpoints_peers import rpc_peer_set_metadata
        r = rpc_peer_set_metadata({"peer_id": "p1", "metadata": {"hostname": "test"}})
        assert r["updated"] is True

    def test_verify_exists(self, sample_state):
        from orchestrator.endpoints_peers import rpc_peer_verify
        r = rpc_peer_verify({"peer_id": "p1", "public_key": ""})
        assert r["exists"] is True

    def test_verify_missing(self, sample_state):
        from orchestrator.endpoints_peers import rpc_peer_verify
        r = rpc_peer_verify({"peer_id": "nonexistent", "public_key": ""})
        assert r["exists"] is False

    def test_stats(self, sample_state):
        from orchestrator.endpoints_peers import rpc_peer_stats
        r = rpc_peer_stats({})
        assert r["total"] >= 1

    def test_cleanup(self, sample_state):
        from orchestrator.endpoints_peers import rpc_peer_cleanup
        from orchestrator import state
        state.STATE["peers"]["p1"]["last_heartbeat"] = 1
        r = rpc_peer_cleanup({"threshold_seconds": 1})
        assert r["cleaned"] == 1


class TestConfigEndpoints:
    def test_config_get(self, sample_state):
        from orchestrator.endpoints_config import rpc_config_get
        r = rpc_config_get({})
        assert "config_version" in r

    def test_state_reset(self, init_state):
        from orchestrator.endpoints_config import rpc_state_reset
        r = rpc_state_reset({"confirm": "RESET"})
        assert r["reset"] is True

    def test_state_reset_no_confirm(self, init_state):
        from orchestrator.endpoints_config import rpc_state_reset
        with pytest.raises(ValueError):
            rpc_state_reset({"confirm": "no"})

    def test_alive_mesh_peers_empty(self, init_state):
        from orchestrator.endpoints_config import _get_alive_mesh_peers
        from orchestrator import state
        state.STATE["networks"]["n1"] = {"cidr": "10.0.0.0/24", "alloc": {"assigned": {}}}
        r = _get_alive_mesh_peers("p1", "n1")
        assert r == []

    def test_alive_mesh_peers(self, sample_state):
        from orchestrator.endpoints_config import _get_alive_mesh_peers
        from orchestrator import state
        import time
        state.STATE["peers"]["p1"]["last_heartbeat"] = int(time.time())
        r = _get_alive_mesh_peers("p_other", "lan1")
        assert len(r) == 1
        assert r[0]["peer_id"] == "p1"

    def test_classify_empty(self, init_state):
        from orchestrator.endpoints_config import _classify_peers_for_hub_mesh
        from orchestrator import state
        state.STATE["networks"]["n1"] = {"cidr": "10.0.0.0/24", "alloc": {"assigned": {}}}
        r = _classify_peers_for_hub_mesh("p1", "n1")
        assert r["direct"] == []
        assert r["relay_only"] == []


class TestAuthEndpoints:
    def test_jwt_issue(self):
        from orchestrator.endpoints_auth import rpc_jwt_issue
        r = rpc_jwt_issue({"user_id": "alice"})
        assert "token" in r

    def test_jwt_verify(self):
        from orchestrator.endpoints_auth import rpc_jwt_issue, rpc_jwt_verify
        r = rpc_jwt_issue({"user_id": "alice"})
        v = rpc_jwt_verify({"token": r["token"]})
        assert v["valid"] is True

    def test_jwt_revoke(self):
        from orchestrator.endpoints_auth import rpc_jwt_issue, rpc_jwt_revoke, rpc_jwt_verify
        r = rpc_jwt_issue({"user_id": "alice"})
        rv = rpc_jwt_revoke({"token": r["token"], "reason": "test"})
        assert rv["revoked"] is True
        with pytest.raises(PermissionError):
            rpc_jwt_verify({"token": r["token"]})


class TestAdvertisedEndpoints:
    def test_advertised_ips(self, sample_state):
        from orchestrator.endpoints_advertised import rpc_advertised_ips
        r = rpc_advertised_ips({"network_id": "lan1"})
        assert r["count"] == 1
        assert "p1" in r["peers"]

    def test_advertised_endpoint(self, sample_state):
        from orchestrator.endpoints_advertised import rpc_advertised_endpoint
        r = rpc_advertised_endpoint({"peer_id": "p1", "endpoint": "1.2.3.4:51820"})
        assert r["recorded"] is True

    def test_advertised_unset(self, sample_state):
        from orchestrator.endpoints_advertised import rpc_advertised_unset
        r = rpc_advertised_unset({"peer_id": "p1"})
        assert r["unset"] is True

    def test_advertised_missing_peer(self, init_state):
        from orchestrator.endpoints_advertised import rpc_advertised_endpoint
        with pytest.raises(KeyError):
            rpc_advertised_endpoint({"peer_id": "nonexistent", "endpoint": "x:1"})


class TestPeerAdminOps:
    def test_update_admin(self, sample_state):
        from orchestrator.endpoints_peers import rpc_peer_update_admin
        r = rpc_peer_update_admin({"peer_id": "p1", "fields": {"tags": ["test"]}})
        assert r is True

    def test_update_admin_bad_fields(self, sample_state):
        from orchestrator.endpoints_peers import rpc_peer_update_admin
        with pytest.raises(ValueError):
            rpc_peer_update_admin({"peer_id": "p1", "fields": "not-a-dict"})

    def test_unregister(self, sample_state):
        from orchestrator.endpoints_peers import rpc_peer_unregister
        r = rpc_peer_unregister({"peer_id": "p1", "token": None})
        assert r is True

    def test_assign_network(self, sample_state):
        from orchestrator.endpoints_peers import rpc_peer_assign_network
        from orchestrator import state
        state.STATE["peers"]["p1"]["networks"] = []
        r = rpc_peer_assign_network({"peer_id": "p1", "network_id": "lan1", "ip": "10.0.0.5"})
        assert r is True

    def test_remove_from_network(self, sample_state):
        from orchestrator.endpoints_peers import rpc_peer_remove_from_network
        r = rpc_peer_remove_from_network({"peer_id": "p1", "network_id": "lan1"})
        assert r is True

    def test_set_networks(self, sample_state):
        from orchestrator.endpoints_peers import rpc_peer_set_networks
        r = rpc_peer_set_networks({"peer_id": "p1", "networks": ["lan1"]})
        assert r["networks"] == ["lan1"]


# ──────────────────────── _require_peer_jwt ────────────────────────


class TestRequirePeerJwt:
    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_valid_jwt(self, mock_hub, sample_state):
        from orchestrator.auth import _jwt_encode
        token, _ = _jwt_encode({"user_id": "alice", "scopes": ["peer:write"]}, 60)
        from orchestrator.endpoints_peers import _require_peer_jwt
        uid = _require_peer_jwt(token, "p1", "peer:write")
        assert uid == "alice"

    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_no_token(self, mock_hub, sample_state):
        from orchestrator.endpoints_peers import _require_peer_jwt
        with pytest.raises(PermissionError, match="authentication required"):
            _require_peer_jwt(None, "p1", "peer:write")

    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_cross_tenant_forbidden(self, mock_hub, sample_state):
        from orchestrator.auth import _jwt_encode
        token, _ = _jwt_encode({"user_id": "other-tenant", "scopes": ["peer:write"]}, 60)
        from orchestrator.endpoints_peers import _require_peer_jwt
        with pytest.raises(PermissionError, match="cross-tenant"):
            _require_peer_jwt(token, "p1", "peer:write")

    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_admin_bypasses_tenant_check(self, mock_hub, sample_state):
        from orchestrator.auth import _jwt_encode
        token, _ = _jwt_encode({"user_id": "admin", "scopes": ["peer:write"], "role": "admin"}, 60)
        from orchestrator.endpoints_peers import _require_peer_jwt
        uid = _require_peer_jwt(token, "p1", "peer:write")
        assert uid == "admin"

    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_missing_scope(self, mock_hub, sample_state):
        from orchestrator.auth import _jwt_encode
        token, _ = _jwt_encode({"user_id": "alice", "scopes": ["peer:read"]}, 60)
        from orchestrator.endpoints_peers import _require_peer_jwt
        with pytest.raises(PermissionError, match="missing scope"):
            _require_peer_jwt(token, "p1", "peer:write")


# ──────────────────────── _mesh_hash ────────────────────────


class TestMeshHash:
    def test_consistency(self):
        from orchestrator.endpoints_peers import _mesh_hash
        h1 = _mesh_hash([{"peer_id": "p1"}, {"peer_id": "p2"}])
        h2 = _mesh_hash([{"peer_id": "p1"}, {"peer_id": "p2"}])
        assert h1 == h2

    def test_changes_with_data(self):
        from orchestrator.endpoints_peers import _mesh_hash
        h1 = _mesh_hash([{"peer_id": "p1"}])
        h2 = _mesh_hash([{"peer_id": "p2"}])
        assert h1 != h2


# ──────────────────────── rpc_peer_register ────────────────────────


class TestPeerRegister:
    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_register_new_peer(self, mock_hub, init_state):
        from orchestrator import state
        state.STATE["users"]["alice"] = {"max_peers": 5, "max_networks": 5}
        state.STATE["networks"]["default"] = {"cidr": "10.0.0.0/24"}
        from orchestrator.auth import _jwt_encode
        token, _ = _jwt_encode({"user_id": "alice", "scopes": ["peer:write"]}, 60)
        from orchestrator.endpoints_peers import rpc_peer_register
        r = rpc_peer_register({
            "peer_id": "p_new", "public_key": "A" * 44,
            "endpoint": "1.2.3.4:51820", "token": token,
        })
        assert r["peer_id"] == "p_new"
        assert "wg_ip" in r
        assert "config_version" in r

    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_register_existing_peer(self, mock_hub, sample_state):
        from orchestrator.auth import _jwt_encode
        token, _ = _jwt_encode({"user_id": "alice", "scopes": ["peer:write"]}, 60)
        from orchestrator.endpoints_peers import rpc_peer_register
        r = rpc_peer_register({
            "peer_id": "p1", "public_key": "new_pubkey_here_00000000000000000000",
            "endpoint": "5.6.7.8:51820", "token": token,
        })
        assert r["peer_id"] == "p1"

    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_register_missing_peer_id(self, mock_hub, init_state):
        from orchestrator.auth import _jwt_encode
        token, _ = _jwt_encode({"user_id": "alice", "scopes": ["peer:write"]}, 60)
        from orchestrator.endpoints_peers import rpc_peer_register
        with pytest.raises(ValueError, match="peer_id"):
            rpc_peer_register({"public_key": "A" * 44, "token": token})

    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_register_cross_tenant(self, mock_hub, sample_state):
        from orchestrator.auth import _jwt_encode
        token, _ = _jwt_encode({"user_id": "other-tenant", "scopes": ["peer:write"]}, 60)
        from orchestrator.endpoints_peers import rpc_peer_register
        with pytest.raises(PermissionError, match="cross-tenant"):
            rpc_peer_register({
                "peer_id": "p1", "public_key": "A" * 44, "token": token,
            })


# ──────────────────────── rpc_peer_heartbeat (extendido) ────────────────────────


class TestPeerHeartbeatExtended:
    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    @patch("orchestrator.endpoints_peers.hub_client._get_wg_endpoint")
    def test_endpoint_override_private(self, mock_get_wg, mock_hub, sample_state):
        mock_get_wg.return_value = "10.0.0.99:51820"
        from orchestrator.endpoints_peers import rpc_peer_heartbeat
        r = rpc_peer_heartbeat({
            "peer_id": "p1",
            "status": {"endpoint": "192.168.1.1:51820", "nat_type": "symmetric"},
            "remote_addr": "100.64.0.1",
        })
        assert r["heartbeat_ack"] is True

    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_endpoint_public_preserved(self, mock_hub, sample_state):
        from orchestrator.endpoints_peers import rpc_peer_heartbeat
        r = rpc_peer_heartbeat({
            "peer_id": "p1",
            "status": {"endpoint": "1.2.3.4:51820", "nat_type": "full-cone"},
            "remote_addr": "100.64.0.1",
        })
        assert r["heartbeat_ack"] is True

    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_heartbeat_mesh_topology(self, mock_hub, sample_state):
        from orchestrator import state
        state.STATE["networks"]["lan1"]["topology"] = "mesh"
        from orchestrator.endpoints_peers import rpc_peer_heartbeat
        r = rpc_peer_heartbeat({"peer_id": "p1", "status": {"wg": "ok"}})
        assert "mesh_peers_hash" in r

    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_heartbeat_hub_mesh_topology(self, mock_hub, sample_state):
        from orchestrator import state
        state.STATE["networks"]["lan1"]["topology"] = "hub-mesh"
        from orchestrator.endpoints_peers import rpc_peer_heartbeat
        r = rpc_peer_heartbeat({"peer_id": "p1", "status": {"wg": "ok"}})
        assert "hub_mesh_peers_hash" in r

    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_heartbeat_no_networks(self, mock_hub, init_state):
        from orchestrator import state
        state.STATE["peers"]["p_no_net"] = {
            "public_key": "pk", "networks": [], "user_id": "admin",
        }
        from orchestrator.endpoints_peers import rpc_peer_heartbeat
        r = rpc_peer_heartbeat({"peer_id": "p_no_net", "status": {}})
        assert r["heartbeat_ack"] is True


# ──────────────────────── rpc_peer_request_network ────────────────────────


class TestPeerRequestNetwork:
    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_request_network(self, mock_hub, init_state):
        from orchestrator import state
        state.STATE["peers"]["p1"] = {"public_key": "pk", "user_id": "alice", "networks": []}
        state.STATE["networks"]["n1"] = {"cidr": "10.0.0.0/24", "user_id": "alice"}
        state.STATE["users"]["alice"] = {"max_peers": 5, "max_networks": 5}
        from orchestrator.auth import _jwt_encode
        token, _ = _jwt_encode({"user_id": "alice", "scopes": ["network:write"]}, 60)
        from orchestrator.endpoints_peers import rpc_peer_request_network
        r = rpc_peer_request_network({"peer_id": "p1", "network_id": "n1", "token": token})
        assert r["network_id"] == "n1"
        assert "ip" in r

    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_request_network_missing(self, mock_hub, init_state):
        from orchestrator.auth import _jwt_encode
        token, _ = _jwt_encode({"user_id": "alice", "scopes": ["network:write"]}, 60)
        from orchestrator.endpoints_peers import rpc_peer_request_network
        with pytest.raises(KeyError):
            rpc_peer_request_network({"peer_id": "p1", "network_id": "nonexistent", "token": token})

    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_request_network_no_id(self, mock_hub, init_state):
        from orchestrator.auth import _jwt_encode
        token, _ = _jwt_encode({"user_id": "alice", "scopes": ["network:write"]}, 60)
        from orchestrator.endpoints_peers import rpc_peer_request_network
        with pytest.raises(ValueError):
            rpc_peer_request_network({"peer_id": "p1", "network_id": "", "token": token})


# ──────────────────────── rpc_peer_rotate_key ────────────────────────


class TestPeerRotateKey:
    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_rotate_key(self, mock_hub, sample_state):
        from orchestrator.auth import _jwt_encode
        token, _ = _jwt_encode({"user_id": "alice", "scopes": ["peer:write"]}, 60)
        from orchestrator.endpoints_peers import rpc_peer_rotate_key
        r = rpc_peer_rotate_key({
            "peer_id": "p1", "public_key": "new_pubkey_abc", "token": token,
        })
        assert r["rotated"] is True
        assert "config_version" in r

    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_rotate_key_missing_pubkey(self, mock_hub, sample_state):
        from orchestrator.auth import _jwt_encode
        token, _ = _jwt_encode({"user_id": "alice", "scopes": ["peer:write"]}, 60)
        from orchestrator.endpoints_peers import rpc_peer_rotate_key
        with pytest.raises(ValueError, match="public_key"):
            rpc_peer_rotate_key({"peer_id": "p1", "public_key": "", "token": token})

    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_rotate_key_missing_peer(self, mock_hub, sample_state):
        from orchestrator.auth import _jwt_encode
        token, _ = _jwt_encode({"user_id": "alice", "scopes": ["peer:write"]}, 60)
        from orchestrator.endpoints_peers import rpc_peer_rotate_key
        with pytest.raises(KeyError):
            rpc_peer_rotate_key({"peer_id": "nonexistent", "public_key": "x" * 44, "token": token})


# ──────────────────────── rpc_peer_report_reachability ────────────────────────


class TestPeerReportReachability:
    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_report_reachable(self, mock_hub, sample_state):
        from orchestrator.auth import _jwt_encode
        token, _ = _jwt_encode({"user_id": "alice", "scopes": ["peer:write"]}, 60)
        from orchestrator.endpoints_peers import rpc_peer_report_reachability
        r = rpc_peer_report_reachability({
            "peer_id": "p1", "target_peer_id": "p2",
            "reachable": True, "token": token,
        })
        assert r["recorded"] is True

    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_report_not_reachable(self, mock_hub, sample_state):
        from orchestrator.auth import _jwt_encode
        token, _ = _jwt_encode({"user_id": "alice", "scopes": ["peer:write"]}, 60)
        from orchestrator.endpoints_peers import rpc_peer_report_reachability
        r = rpc_peer_report_reachability({
            "peer_id": "p1", "target_peer_id": "p2",
            "reachable": False, "token": token,
        })
        assert r["recorded"] is True


# ──────────────────────── rpc_peer_unregister (extendido) ────────────────────────


class TestPeerUnregisterExtended:
    @patch("orchestrator.endpoints_peers.hub_client.hub_remove_peer")
    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_unregister_admin_token(self, mock_hub, mock_remove, sample_state):
        from orchestrator.endpoints_peers import rpc_peer_unregister
        r = rpc_peer_unregister({
            "peer_id": "p1", "admin_token": "test-admin-token-123",
        })
        assert r is True

    @patch("orchestrator.endpoints_peers.hub_client.hub_remove_peer")
    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_unregister_jwt(self, mock_hub, mock_remove, sample_state):
        from orchestrator.auth import _jwt_encode
        token, _ = _jwt_encode({"user_id": "alice", "scopes": ["peer:delete"]}, 60)
        from orchestrator.endpoints_peers import rpc_peer_unregister
        r = rpc_peer_unregister({"peer_id": "p1", "token": token})
        assert r is True

    @patch("orchestrator.endpoints_peers.hub_client.hub_remove_peer")
    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_unregister_missing_peer(self, mock_hub, mock_remove, init_state):
        from orchestrator.endpoints_peers import rpc_peer_unregister
        r = rpc_peer_unregister({"peer_id": "nonexistent", "admin_token": "test-admin-token-123"})
        assert r is True


# ──────────────────────── rpc_peer_assign_network (extendido) ────────────────────────


class TestPeerAssignNetworkExtended:
    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_assign_network_ip_outside_cidr(self, mock_hub, sample_state):
        from orchestrator.endpoints_peers import rpc_peer_assign_network
        with pytest.raises(ValueError, match="ip not in network cidr"):
            rpc_peer_assign_network({
                "peer_id": "p1", "network_id": "lan1",
                "ip": "192.168.1.1", "admin_token": "test-admin-token-123",
            })

    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_assign_network_ip_conflict(self, mock_hub, sample_state):
        from orchestrator import state
        from orchestrator.endpoints_peers import rpc_peer_assign_network
        state.STATE["peers"]["p2"] = {"public_key": "pk2", "user_id": "admin", "networks": []}
        with pytest.raises(ValueError, match="already assigned"):
            rpc_peer_assign_network({
                "peer_id": "p2", "network_id": "lan1",
                "ip": "10.0.0.1", "admin_token": "test-admin-token-123",
            })

    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_assign_network_success(self, mock_hub, sample_state):
        from orchestrator.endpoints_peers import rpc_peer_assign_network
        r = rpc_peer_assign_network({
            "peer_id": "p1", "network_id": "lan1",
            "ip": "10.0.0.5", "admin_token": "test-admin-token-123",
        })
        assert r is True


# ──────────────────────── rpc_config_get_mesh_peers ────────────────────────


class TestConfigGetMeshPeers:
    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_mesh_topology_dispatches(self, mock_hub, init_state):
        from orchestrator import state
        state.STATE["networks"]["n1"] = {
            "cidr": "10.0.0.0/24", "topology": "mesh",
            "alloc": {"assigned": {}, "reserved": []},
        }
        from orchestrator.endpoints_config import rpc_config_get_mesh_peers
        r = rpc_config_get_mesh_peers({"peer_id": "p1", "network_id": "n1"})
        assert isinstance(r, list)

    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_hub_mesh_topology_dispatches(self, mock_hub, init_state):
        from orchestrator import state
        state.STATE["networks"]["n1"] = {
            "cidr": "10.0.0.0/24", "topology": "hub-mesh",
            "alloc": {"assigned": {}, "reserved": []},
        }
        from orchestrator.endpoints_config import rpc_config_get_mesh_peers
        r = rpc_config_get_mesh_peers({"peer_id": "p1", "network_id": "n1"})
        assert "direct" in r
        assert "relay_only" in r

    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_hub_spoke_raises(self, mock_hub, init_state):
        from orchestrator import state
        state.STATE["networks"]["n1"] = {
            "cidr": "10.0.0.0/24", "topology": "hub-spoke",
        }
        from orchestrator.endpoints_config import rpc_config_get_mesh_peers
        with pytest.raises(ValueError, match="hub-spoke"):
            rpc_config_get_mesh_peers({"peer_id": "p1", "network_id": "n1"})


# ──────────────────────── _classify_peers_for_hub_mesh (extendido) ────────────────────────


class TestClassifyPeersForHubMeshExtended:
    def test_symmetric_nat_requester(self, sample_state):
        import time
        from orchestrator import state
        state.STATE["networks"]["lan1"]["topology"] = "hub-mesh"
        state.STATE["peers"]["p_requester"] = {
            "public_key": "pk_req", "user_id": "alice",
            "networks": ["lan1"], "nat_type": "symmetric",
        }
        state.STATE["peers"]["p_target"] = {
            "public_key": "pk_target", "user_id": "alice",
            "networks": ["lan1"], "endpoint": "1.2.3.4:51820",
            "nat_type": "full-cone", "last_heartbeat": int(time.time()),
        }
        state.STATE["networks"]["lan1"]["alloc"]["assigned"]["p_target"] = "10.0.0.2"
        from orchestrator.endpoints_config import _classify_peers_for_hub_mesh
        r = _classify_peers_for_hub_mesh("p_requester", "lan1")
        assert len(r["relay_only"]) == 1
        assert len(r["direct"]) == 0

    def test_force_relay(self, sample_state):
        import time
        from orchestrator import state
        state.STATE["networks"]["lan1"]["topology"] = "hub-mesh"
        state.STATE["peers"]["p_target"] = {
            "public_key": "pk_target", "user_id": "alice",
            "networks": ["lan1"], "endpoint": "1.2.3.4:51820",
            "nat_type": "full-cone", "relay_mode": "force_relay",
            "last_heartbeat": int(time.time()),
        }
        state.STATE["networks"]["lan1"]["alloc"]["assigned"]["p_target"] = "10.0.0.2"
        from orchestrator.endpoints_config import _classify_peers_for_hub_mesh
        r = _classify_peers_for_hub_mesh("p1", "lan1")
        assert len(r["relay_only"]) == 1
        assert len(r["direct"]) == 0

    def test_force_direct(self, sample_state):
        import time
        from orchestrator import state
        state.STATE["networks"]["lan1"]["topology"] = "hub-mesh"
        state.STATE["peers"]["p_target"] = {
            "public_key": "pk_target", "user_id": "alice",
            "networks": ["lan1"], "endpoint": "1.2.3.4:51820",
            "nat_type": "full-cone", "relay_mode": "force_direct",
            "last_heartbeat": int(time.time()),
        }
        state.STATE["networks"]["lan1"]["alloc"]["assigned"]["p_target"] = "10.0.0.2"
        from orchestrator.endpoints_config import _classify_peers_for_hub_mesh
        r = _classify_peers_for_hub_mesh("p1", "lan1")
        assert len(r["direct"]) == 1
        assert len(r["relay_only"]) == 0

    def test_reachability_map_override(self, sample_state):
        import time
        from orchestrator import state
        state.STATE["networks"]["lan1"]["topology"] = "hub-mesh"
        state.STATE["peers"]["p_requester"] = {
            "public_key": "pk_req", "user_id": "alice",
            "networks": ["lan1"], "nat_type": "full-cone",
            "reachability_map": {"p_target": "hub-relay"},
        }
        state.STATE["peers"]["p_target"] = {
            "public_key": "pk_target", "user_id": "alice",
            "networks": ["lan1"], "endpoint": "1.2.3.4:51820",
            "nat_type": "full-cone", "last_heartbeat": int(time.time()),
        }
        state.STATE["networks"]["lan1"]["alloc"]["assigned"]["p_target"] = "10.0.0.2"
        from orchestrator.endpoints_config import _classify_peers_for_hub_mesh
        r = _classify_peers_for_hub_mesh("p_requester", "lan1")
        assert len(r["relay_only"]) == 1

    def test_dead_peer_excluded(self, sample_state):
        from orchestrator import state
        state.STATE["networks"]["lan1"]["topology"] = "hub-mesh"
        state.STATE["peers"]["p_target"] = {
            "public_key": "pk_target", "user_id": "alice",
            "networks": ["lan1"], "endpoint": "1.2.3.4:51820",
            "nat_type": "full-cone", "last_heartbeat": 0,
        }
        state.STATE["networks"]["lan1"]["alloc"]["assigned"]["p_target"] = "10.0.0.2"
        from orchestrator.endpoints_config import _classify_peers_for_hub_mesh
        r = _classify_peers_for_hub_mesh("p1", "lan1")
        assert len(r["direct"]) == 0
        assert len(r["relay_only"]) == 0


# ──────────────────────── rpc_config_get_peer_config ────────────────────────


class TestConfigGetPeerConfig:
    @patch("orchestrator.hub_client._hub_call_with_retry")
    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_hub_spoke_config(self, mock_hub, mock_hub_call, sample_state):
        mock_hub_call.return_value = "hub-pubkey-xxxx"
        from orchestrator import state
        state.STATE["networks"]["lan1"]["topology"] = "hub-spoke"
        from orchestrator.auth import _jwt_encode
        token, _ = _jwt_encode({"user_id": "alice", "scopes": ["config:read"], "role": "admin"}, 60)
        from orchestrator.endpoints_config import rpc_config_get_peer_config
        r = rpc_config_get_peer_config({"peer_id": "p1", "token": token})
        assert r["interface"]["address"] == "10.0.0.1/32"
        assert r["peer"]["public_key"] == "hub-pubkey-xxxx"
        assert r["meta"]["topology"] == "hub-spoke"

    @patch("orchestrator.hub_client._hub_call_with_retry")
    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_mesh_config(self, mock_hub, mock_hub_call, sample_state):
        mock_hub_call.return_value = "hub-pubkey-xxxx"
        import time
        from orchestrator import state
        state.STATE["networks"]["lan1"]["topology"] = "mesh"
        state.STATE["peers"]["p1"]["last_heartbeat"] = int(time.time())
        from orchestrator.auth import _jwt_encode
        token, _ = _jwt_encode({"user_id": "alice", "scopes": ["config:read"], "role": "admin"}, 60)
        from orchestrator.endpoints_config import rpc_config_get_peer_config
        r = rpc_config_get_peer_config({"peer_id": "p1", "token": token})
        assert "mesh_peers" in r
        assert "mesh_peers_hash" in r["meta"]

    @patch("orchestrator.hub_client._hub_call_with_retry")
    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_hub_mesh_config(self, mock_hub, mock_hub_call, sample_state):
        mock_hub_call.return_value = "hub-pubkey-xxxx"
        import time
        from orchestrator import state
        state.STATE["networks"]["lan1"]["topology"] = "hub-mesh"
        state.STATE["peers"]["p1"]["last_heartbeat"] = int(time.time())
        from orchestrator.auth import _jwt_encode
        token, _ = _jwt_encode({"user_id": "alice", "scopes": ["config:read"], "role": "admin"}, 60)
        from orchestrator.endpoints_config import rpc_config_get_peer_config
        r = rpc_config_get_peer_config({"peer_id": "p1", "token": token})
        assert "hub_mesh_direct_peers" in r
        assert "hub_mesh_relay_peers" in r
        assert "hub_mesh_peers_hash" in r["meta"]

    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_no_auth(self, mock_hub, sample_state):
        from orchestrator.endpoints_config import rpc_config_get_peer_config
        with pytest.raises(PermissionError):
            rpc_config_get_peer_config({"peer_id": "p1", "token": None})

    @patch("orchestrator.endpoints_peers.hub_client._hub_apply_peer_allowed_ips")
    def test_missing_peer(self, mock_hub, sample_state):
        from orchestrator.auth import _jwt_encode
        token, _ = _jwt_encode({"user_id": "alice", "scopes": ["config:read"], "role": "admin"}, 60)
        from orchestrator.endpoints_config import rpc_config_get_peer_config
        with pytest.raises(KeyError):
            rpc_config_get_peer_config({"peer_id": "nonexistent", "token": token})


# ──────────────────────── rpc_config_reload ────────────────────────


class TestConfigReload:
    def test_reload(self):
        from orchestrator.endpoints_config import rpc_config_reload
        r = rpc_config_reload({})
        assert r["reloaded"] is True


# ──────────────────────── rpc_metrics JWT scoped ────────────────────────


class TestMetricsJwt:
    def test_jwt_tenant_scoped(self, init_state):
        from orchestrator import state
        state.STATE["users"]["alice"] = {"max_peers": 5, "max_networks": 5}
        state.STATE["peers"]["p1"] = {"user_id": "alice", "enabled": True}
        state.STATE["peers"]["p2"] = {"user_id": "other", "enabled": True}
        from orchestrator.auth import _jwt_encode
        token, _ = _jwt_encode({"user_id": "alice", "scopes": ["*"], "role": "admin"}, 60)
        from orchestrator.endpoints_orch import rpc_metrics
        r = rpc_metrics({"token": token})
        assert r["peers_total"] == 2
        assert r["users_total"] == 1
