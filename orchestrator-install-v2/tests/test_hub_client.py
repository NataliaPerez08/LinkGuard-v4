import pytest
from unittest.mock import patch, MagicMock


class TestPeerAllowedIPs:
    def test_from_networks(self, sample_state):
        from orchestrator.hub_client import _peer_all_allowed_ips
        from orchestrator import state
        peer = state.STATE["peers"]["p1"]
        ips = _peer_all_allowed_ips(peer)
        assert len(ips) == 1
        assert ips[0] == "10.0.0.1/32"

    def test_no_networks(self):
        from orchestrator.hub_client import _peer_all_allowed_ips
        ips = _peer_all_allowed_ips({"networks": []})
        assert ips == []

    def test_unknown_network(self, init_state):
        from orchestrator.hub_client import _peer_all_allowed_ips
        ips = _peer_all_allowed_ips({"networks": ["nonexistent"]})
        assert ips == []


class TestHubApply:
    def test_apply_missing_peer(self, init_state):
        from orchestrator.hub_client import _hub_apply_peer_allowed_ips
        _hub_apply_peer_allowed_ips("nonexistent")


class TestHubCall:
    @patch("orchestrator.hub_client.ServerProxy")
    @pytest.mark.parametrize("reply", ["ok", "pong"])
    def test_hub_ping_ok(self, mock_proxy, reply):
        import orchestrator.hub_client as hub_client
        mock_client = MagicMock()
        getattr(mock_client, "hub.health").return_value = reply
        mock_proxy.return_value = mock_client
        with patch.object(hub_client.config, "HUB_AGENT_TOKEN", "hub-token"):
            assert hub_client.hub_ping() is True
        getattr(mock_client, "hub.health").assert_called_once_with("hub-token")

    @patch("orchestrator.hub_client.ServerProxy")
    def test_hub_ping_fail(self, mock_proxy):
        import orchestrator.hub_client as hub_client
        mock_client = MagicMock()
        getattr(mock_client, "hub.health").side_effect = Exception("timeout")
        mock_proxy.return_value = mock_client
        with patch.object(hub_client.config, "HUB_AGENT_TOKEN", "hub-token"):
            assert hub_client.hub_ping() is False

    @patch("orchestrator.hub_client.ServerProxy")
    def test_hub_apply_peer(self, mock_proxy):
        from orchestrator.hub_client import hub_apply_peer
        mock_client = MagicMock()
        getattr(mock_client, "hub.apply_peer").return_value = True
        mock_proxy.return_value = mock_client
        assert hub_apply_peer("pubkey", "10.0.0.1/32") is True

    @patch("orchestrator.hub_client.ServerProxy")
    def test_hub_remove_peer(self, mock_proxy):
        from orchestrator.hub_client import hub_remove_peer
        mock_client = MagicMock()
        getattr(mock_client, "hub.remove_peer").return_value = True
        mock_proxy.return_value = mock_client
        assert hub_remove_peer("pubkey") is True
