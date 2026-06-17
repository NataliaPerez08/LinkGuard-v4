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


class TestPeerCompat:
    @patch("orchestrator.hub_client._hub_call_with_retry")
    def test_peer_register_and_config(self, mock_hub, init_state):
        from orchestrator import state
        from orchestrator.endpoints_peers import rpc_peer_register, rpc_peer_heartbeat
        from orchestrator.endpoints_config import rpc_config_get_peer_config

        mock_hub.side_effect = lambda method, *args: "hub-public-key" if method == "hub.public_key" else True

        state.STATE["users"]["alice"] = {
            "token": "u_token_alice",
            "disabled": False,
            "created_ts": 1000,
            "max_peers": 5,
            "max_networks": 5,
            "metadata": {},
        }

        jwt_token = _issue_jwt("alice", "peer-a")
        reg = rpc_peer_register(
            {
                "peer_id": "peer-a",
                "public_key": "A" * 44,
                "endpoint": "198.51.100.10:51820",
                "metadata": {"hostname": "peer-a"},
                "token": jwt_token,
            }
        )
        assert reg["peer_id"] == "peer-a"
        assert reg["wg_ip"].endswith("/32")

        hb = rpc_peer_heartbeat(
            {
                "peer_id": "peer-a",
                "status": {"endpoint": "198.51.100.10:51820", "nat_type": "none"},
                "token": jwt_token,
            }
        )
        assert hb["heartbeat_ack"] is True
        assert "desired_config_version" in hb

        cfg = rpc_config_get_peer_config({"peer_id": "peer-a", "token": jwt_token})
        assert cfg["interface"]["address"].endswith("/32")
        assert cfg["peer"]["public_key"] == "hub-public-key"
        assert cfg["peer"]["endpoint"] == "10.0.0.1:51820"
        assert cfg["meta"]["topology"] == "hub-spoke"

    @patch("orchestrator.hub_client._hub_call_with_retry")
    def test_peer_request_network_and_rotate_key(self, mock_hub, sample_state):
        from orchestrator.endpoints_peers import rpc_peer_request_network, rpc_peer_rotate_key

        mock_hub.return_value = True
        jwt_token = _issue_jwt("alice", "p1")

        req = rpc_peer_request_network({"peer_id": "p1", "network_id": "lan1", "token": jwt_token})
        assert req["network_id"] == "lan1"

        rot = rpc_peer_rotate_key({"peer_id": "p1", "public_key": "B" * 44, "token": jwt_token})
        assert rot["rotated"] is True

    def test_peer_report_reachability(self, sample_state):
        from orchestrator import state
        from orchestrator.endpoints_peers import rpc_peer_report_reachability

        jwt_token = _issue_jwt("alice", "p1")
        resp = rpc_peer_report_reachability(
            {"peer_id": "p1", "target_peer_id": "p2", "reachable": False, "token": jwt_token}
        )
        assert resp["recorded"] is True
        assert state.STATE["peers"]["p1"]["reachability_map"]["p2"] == "hub-relay"
