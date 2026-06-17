import pytest


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
