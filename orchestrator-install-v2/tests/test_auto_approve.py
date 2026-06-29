import pytest
import os


class TestEnsureDefaultNetwork:
    def test_creates_if_missing(self, init_state, monkeypatch):
        monkeypatch.setenv("AUTO_APPROVE_ENABLED", "1")
        monkeypatch.setenv("AUTO_APPROVE_RULES", "office:10.0.0.0/24")
        from importlib import reload
        import orchestrator.config as cfg
        reload(cfg)
        from orchestrator.auto_approve import _ensure_default_network
        net_id = _ensure_default_network()
        assert net_id == "default"
        from orchestrator import state
        assert "default" in state.STATE["networks"]

    def test_returns_existing(self, sample_state):
        from orchestrator.auto_approve import _ensure_default_network
        net_id = _ensure_default_network()
        assert net_id == "default"


class TestTryAutoApprove:
    def test_disabled(self, init_state, monkeypatch):
        monkeypatch.setenv("AUTO_APPROVE_ENABLED", "0")
        from importlib import reload
        import orchestrator.config as cfg
        reload(cfg)
        from orchestrator.auto_approve import try_auto_approve
        assert try_auto_approve("pubkey", {}) is None

    def test_no_matching_rule(self, init_state, monkeypatch):
        monkeypatch.setenv("AUTO_APPROVE_ENABLED", "1")
        monkeypatch.setenv("AUTO_APPROVE_RULES", "office:10.0.0.0/24")
        from importlib import reload
        import orchestrator.config as cfg
        reload(cfg)
        from orchestrator.auto_approve import try_auto_approve
        result = try_auto_approve("pubkey", {"tag": "home"})
        assert result is None

    def test_existing_peer(self, sample_state, monkeypatch):
        monkeypatch.setenv("AUTO_APPROVE_ENABLED", "1")
        monkeypatch.setenv("AUTO_APPROVE_RULES", "office:10.0.0.0/24")
        from importlib import reload
        import orchestrator.config as cfg
        reload(cfg)
        from orchestrator.auto_approve import try_auto_approve
        result = try_auto_approve("pk_p1", {"tag": "office"})
        assert result is None

    def test_success(self, init_state, monkeypatch):
        monkeypatch.setenv("AUTO_APPROVE_ENABLED", "1")
        monkeypatch.setenv("AUTO_APPROVE_RULES", "office:10.0.0.0/24")
        from importlib import reload
        import orchestrator.config as cfg
        reload(cfg)
        from orchestrator.auto_approve import try_auto_approve
        import orchestrator.state as state_mod
        state_mod.STATE["peers"] = {}
        result = try_auto_approve("new_pubkey", {"tag": "office"})
        assert result is not None
        assert "peer_id" in result
        # .1 reservada para el HUB de WireGuard (ver network_alloc._allocate_ip_in_network)
        assert result["ip"] == "10.0.0.2"
