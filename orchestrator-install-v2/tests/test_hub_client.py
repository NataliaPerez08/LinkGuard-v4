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


# ──────────────────────── _hub_call_with_retry ────────────────────────


class TestHubCallWithRetry:
    @patch("orchestrator.hub_client.time")
    @patch("orchestrator.hub_client.ServerProxy")
    def test_success_first_try(self, mock_proxy, mock_time):
        import orchestrator.hub_client as hub_client
        with patch.object(hub_client.config, "HUB_RETRY_COUNT", 3):
            with patch.object(hub_client.config, "HUB_RETRY_DELAY", 0.1):
                mock_client = MagicMock()
                getattr(mock_client, "hub.health").return_value = "ok"
                mock_proxy.return_value = mock_client
                r = hub_client._hub_call_with_retry("hub.health", "t")
                assert r == "ok"

    @patch("orchestrator.hub_client.time")
    @patch("orchestrator.hub_client.ServerProxy")
    def test_retry_then_success(self, mock_proxy, mock_time):
        import orchestrator.hub_client as hub_client
        with patch.object(hub_client.config, "HUB_RETRY_COUNT", 3):
            with patch.object(hub_client.config, "HUB_RETRY_DELAY", 0.1):
                mock_client = MagicMock()
                method = getattr(mock_client, "hub.health")
                method.side_effect = [Exception("fail1"), Exception("fail2"), "ok"]
                mock_proxy.return_value = mock_client
                r = hub_client._hub_call_with_retry("hub.health", "t")
                assert r == "ok"
                assert method.call_count == 3

    @patch("orchestrator.hub_client.time")
    @patch("orchestrator.hub_client.ServerProxy")
    def test_all_fail(self, mock_proxy, mock_time):
        import orchestrator.hub_client as hub_client
        with patch.object(hub_client.config, "HUB_RETRY_COUNT", 2):
            with patch.object(hub_client.config, "HUB_RETRY_DELAY", 0.1):
                mock_client = MagicMock()
                method = getattr(mock_client, "hub.health")
                method.side_effect = Exception("always fail")
                mock_proxy.return_value = mock_client
                with pytest.raises(RuntimeError, match="fallo tras"):
                    hub_client._hub_call_with_retry("hub.health", "t")


# ──────────────────────── _is_public_endpoint ────────────────────────


class TestIsPublicEndpoint:
    def test_public_ipv4(self):
        from orchestrator.hub_client import _is_public_endpoint
        assert _is_public_endpoint("1.2.3.4:51820") is True

    def test_private_ipv4(self):
        from orchestrator.hub_client import _is_public_endpoint
        assert _is_public_endpoint("10.0.0.1:51820") is False
        assert _is_public_endpoint("192.168.1.1:51820") is False
        assert _is_public_endpoint("172.16.0.1:51820") is False

    def test_dns_name(self):
        from orchestrator.hub_client import _is_public_endpoint
        assert _is_public_endpoint("hub.example.com:51820") is True

    def test_empty(self):
        from orchestrator.hub_client import _is_public_endpoint
        assert _is_public_endpoint("") is False

    def test_ipv6(self):
        from orchestrator.hub_client import _is_public_endpoint
        assert _is_public_endpoint("[2600:1f18::1]:51820") is True


# ──────────────────────── _get_wg_endpoint ────────────────────────


class TestGetWGEndpoint:
    @patch("orchestrator.hub_client._hub_call_with_retry")
    def test_found(self, mock_retry):
        from orchestrator.hub_client import _get_wg_endpoint
        mock_retry.return_value = [
            {"public_key": "pk1", "endpoint": "1.2.3.4:51820"},
            {"public_key": "pk2", "endpoint": "5.6.7.8:51820"},
        ]
        ep = _get_wg_endpoint("pk2")
        assert ep == "5.6.7.8:51820"

    @patch("orchestrator.hub_client._hub_call_with_retry")
    def test_not_found(self, mock_retry):
        from orchestrator.hub_client import _get_wg_endpoint
        mock_retry.return_value = [
            {"public_key": "pk1", "endpoint": "1.2.3.4:51820"},
        ]
        ep = _get_wg_endpoint("nonexistent")
        assert ep == ""

    @patch("orchestrator.hub_client._hub_call_with_retry")
    def test_no_endpoint_field(self, mock_retry):
        from orchestrator.hub_client import _get_wg_endpoint
        mock_retry.return_value = [
            {"public_key": "pk1"},
        ]
        ep = _get_wg_endpoint("pk1")
        assert ep == ""

    @patch("orchestrator.hub_client._hub_call_with_retry")
    def test_exception(self, mock_retry):
        from orchestrator.hub_client import _get_wg_endpoint
        mock_retry.side_effect = Exception("timeout")
        ep = _get_wg_endpoint("pk1")
        assert ep == ""


# ──────────────────────── _hub_apply_peer_allowed_ips ────────────────────────


class TestHubApplyPeerAllowedIPs:
    @patch("orchestrator.hub_client._peer_all_allowed_ips")
    @patch("orchestrator.hub_client._is_public_endpoint")
    @patch("orchestrator.hub_client._get_wg_endpoint")
    @patch("orchestrator.hub_client.hub_apply_peer")
    def test_public_endpoint_port_preservation(self, mock_apply, mock_get_wg, mock_is_public, mock_peer_ips, sample_state):
        mock_peer_ips.return_value = ["10.0.0.1/32"]
        def is_public_side_effect(ep):
            return ep and ep != "10.0.0.1:51820"
        mock_is_public.side_effect = is_public_side_effect
        mock_get_wg.return_value = "100.64.0.1:51821"
        from orchestrator import state, hub_client
        with patch.object(hub_client.config, "HUB_AGENT_TOKEN", "t"):
            hub_client._hub_apply_peer_allowed_ips("p1")
        call_args = mock_apply.call_args[0]
        assert call_args[0] == state.STATE["peers"]["p1"]["public_key"]
        assert "10.0.0.1/32" in call_args[1]
        # endpoint should be preserved from WG-learned
        assert mock_apply.called

    @patch("orchestrator.hub_client._peer_all_allowed_ips")
    @patch("orchestrator.hub_client._is_public_endpoint")
    @patch("orchestrator.hub_client._get_wg_endpoint")
    @patch("orchestrator.hub_client.hub_apply_peer")
    def test_no_csv_skips_apply(self, mock_apply, mock_get_wg, mock_is_public, mock_peer_ips):
        mock_peer_ips.return_value = []
        from orchestrator.hub_client import _hub_apply_peer_allowed_ips
        _hub_apply_peer_allowed_ips("p1")
        assert not mock_apply.called

    @patch("orchestrator.hub_client._peer_all_allowed_ips")
    @patch("orchestrator.hub_client._is_public_endpoint")
    @patch("orchestrator.hub_client._get_wg_endpoint")
    @patch("orchestrator.hub_client.hub_apply_peer")
    def test_hub_apply_exception_logged(self, mock_apply, mock_get_wg, mock_is_public, mock_peer_ips, caplog):
        import logging
        caplog.set_level(logging.INFO)
        mock_peer_ips.return_value = ["10.0.0.1/32"]
        mock_is_public.return_value = True
        mock_apply.side_effect = Exception("hub error")
        from orchestrator.hub_client import _hub_apply_peer_allowed_ips
        _hub_apply_peer_allowed_ips("p1")
        assert "No pude actualizar" in caplog.text
