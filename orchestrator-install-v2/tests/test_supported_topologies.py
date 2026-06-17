from unittest.mock import patch


def _issue_jwt(user_id: str, peer_id: str = "") -> str:
    from orchestrator import auth

    token, _ = auth._jwt_encode(
        {
            "user_id": user_id,
            "peer_id": peer_id,
            "scopes": ["peer:*", "network:*", "config:*", "orch:read"],
            "role": "user",
        },
        600,
    )
    return token


def _seed_topology_state(init_state, topology: str, relay_cidr: str | None = None):
    from orchestrator import state

    now = state.now_ts()
    state.STATE["users"]["alice"] = {
        "token": "u_token_alice",
        "disabled": False,
        "created_ts": now,
        "max_peers": 10,
        "max_networks": 10,
        "metadata": {},
    }
    net = {
        "cidr": "10.20.30.0/24",
        "description": "topology test network",
        "user_id": "alice",
        "tag": "lab",
        "topology": topology,
        "created_ts": now,
        "alloc": {
            "reserved": [],
            "assigned": {
                "peer-a": "10.20.30.2",
                "peer-b": "10.20.30.3",
                "peer-c": "10.20.30.4",
            },
        },
    }
    if relay_cidr:
        net["hub_mesh_relay_fallback_cidr"] = relay_cidr
    state.STATE["networks"]["net1"] = net
    state.STATE["peers"] = {
        "peer-a": {
            "public_key": "A" * 44,
            "ip": "10.20.30.2",
            "networks": ["net1"],
            "user_id": "alice",
            "enabled": True,
            "created_ts": now,
            "keepalive": 25,
            "metadata": {"owner": "alice"},
            "endpoint": "198.51.100.10:51820",
            "last_heartbeat": now,
            "nat_type": "none",
        },
        "peer-b": {
            "public_key": "B" * 44,
            "ip": "10.20.30.3",
            "networks": ["net1"],
            "user_id": "alice",
            "enabled": True,
            "created_ts": now,
            "keepalive": 25,
            "metadata": {"owner": "alice"},
            "endpoint": "198.51.100.11:51820",
            "last_heartbeat": now,
            "nat_type": "full-cone",
        },
        "peer-c": {
            "public_key": "C" * 44,
            "ip": "10.20.30.4",
            "networks": ["net1"],
            "user_id": "alice",
            "enabled": True,
            "created_ts": now,
            "keepalive": 25,
            "metadata": {"owner": "alice"},
            "endpoint": "198.51.100.12:51820",
            "last_heartbeat": now,
            "nat_type": "symmetric",
        },
    }
    return state.STATE


class TestSupportedTopologies:
    @patch("orchestrator.hub_client._hub_call_with_retry")
    def test_hub_spoke_config_uses_hub_only(self, mock_hub, init_state):
        from orchestrator.endpoints_config import rpc_config_get_mesh_peers, rpc_config_get_peer_config
        from orchestrator.endpoints_peers import rpc_peer_heartbeat

        mock_hub.side_effect = lambda method, *args: "hub-public-key" if method == "hub.public_key" else True
        _seed_topology_state(init_state, "hub-spoke")
        jwt_token = _issue_jwt("alice", "peer-a")

        cfg = rpc_config_get_peer_config({"peer_id": "peer-a", "token": jwt_token})
        assert cfg["meta"]["topology"] == "hub-spoke"
        assert cfg["interface"]["address"] == "10.20.30.2/32"
        assert cfg["peer"]["public_key"] == "hub-public-key"
        assert cfg["peer"]["allowed_ips"] == "10.20.30.0/24"
        assert "mesh_peers" not in cfg
        assert "hub_mesh_direct_peers" not in cfg

        hb = rpc_peer_heartbeat(
            {"peer_id": "peer-a", "status": {"endpoint": "198.51.100.10:51820"}, "token": jwt_token}
        )
        assert hb == {"heartbeat_ack": True, "desired_config_version": 1}

        try:
            rpc_config_get_mesh_peers({"peer_id": "peer-a", "network_id": "net1", "token": jwt_token})
            assert False, "hub-spoke no debe exponer peers mesh"
        except ValueError:
            pass

    @patch("orchestrator.hub_client._hub_call_with_retry")
    def test_mesh_config_returns_alive_peer_list(self, mock_hub, init_state):
        from orchestrator import state
        from orchestrator.endpoints_config import rpc_config_get_mesh_peers, rpc_config_get_peer_config
        from orchestrator.endpoints_peers import rpc_peer_heartbeat

        mock_hub.side_effect = lambda method, *args: "hub-public-key" if method == "hub.public_key" else True
        _seed_topology_state(init_state, "mesh")
        state.STATE["peers"]["peer-c"]["last_heartbeat"] = 1
        jwt_token = _issue_jwt("alice", "peer-a")

        cfg = rpc_config_get_peer_config({"peer_id": "peer-a", "token": jwt_token})
        assert cfg["meta"]["topology"] == "mesh"
        assert len(cfg["mesh_peers"]) == 2
        assert cfg["mesh_peers"][0]["peer_id"] == "peer-b"
        assert cfg["mesh_peers"][0]["alive"] is True
        assert cfg["mesh_peers"][1]["peer_id"] == "peer-c"
        assert cfg["mesh_peers"][1]["alive"] is False
        assert cfg["meta"]["mesh_peers_hash"]

        mesh_peers = rpc_config_get_mesh_peers({"peer_id": "peer-a", "network_id": "net1", "token": jwt_token})
        assert len(mesh_peers) == 2
        assert mesh_peers[0]["peer_id"] == "peer-b"

        hb = rpc_peer_heartbeat(
            {"peer_id": "peer-a", "status": {"endpoint": "198.51.100.10:51820"}, "token": jwt_token}
        )
        assert hb["heartbeat_ack"] is True
        assert hb["desired_config_version"] == 1
        assert hb["mesh_peers_hash"]

    @patch("orchestrator.hub_client._hub_call_with_retry")
    def test_hub_mesh_config_splits_direct_and_relay(self, mock_hub, init_state):
        from orchestrator import state
        from orchestrator.endpoints_config import rpc_config_get_mesh_peers, rpc_config_get_peer_config
        from orchestrator.endpoints_peers import rpc_peer_heartbeat

        mock_hub.side_effect = lambda method, *args: "hub-public-key" if method == "hub.public_key" else True
        _seed_topology_state(init_state, "hub-mesh", relay_cidr="10.20.30.0/24")
        state.STATE["peers"]["peer-a"]["reachability_map"] = {"peer-c": "hub-relay"}
        jwt_token = _issue_jwt("alice", "peer-a")

        cfg = rpc_config_get_peer_config({"peer_id": "peer-a", "token": jwt_token})
        assert cfg["meta"]["topology"] == "hub-mesh"
        assert cfg["peer"]["allowed_ips"] == "10.20.30.0/24"
        assert [p["peer_id"] for p in cfg["hub_mesh_direct_peers"]] == ["peer-b"]
        assert [p["peer_id"] for p in cfg["hub_mesh_relay_peers"]] == ["peer-c"]
        assert cfg["meta"]["hub_mesh_peers_hash"]

        mesh_view = rpc_config_get_mesh_peers({"peer_id": "peer-a", "network_id": "net1", "token": jwt_token})
        assert [p["peer_id"] for p in mesh_view["direct"]] == ["peer-b"]
        assert [p["peer_id"] for p in mesh_view["relay_only"]] == ["peer-c"]
        assert mesh_view["relay_cidr"] == "10.20.30.0/24"

        hb = rpc_peer_heartbeat(
            {"peer_id": "peer-a", "status": {"endpoint": "198.51.100.10:51820"}, "token": jwt_token}
        )
        assert hb["heartbeat_ack"] is True
        assert hb["hub_mesh_peers_hash"]
