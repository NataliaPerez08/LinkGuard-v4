import pytest
import os


class TestAutoApproveRules:
    def test_parse_empty(self):
        from orchestrator.config import _parse_auto_approve_rules
        assert _parse_auto_approve_rules("") == {}

    def test_parse_single(self):
        from orchestrator.config import _parse_auto_approve_rules
        r = _parse_auto_approve_rules("office:10.0.0.0/24")
        assert r == {"office": "10.0.0.0/24"}

    def test_parse_multiple(self):
        from orchestrator.config import _parse_auto_approve_rules
        r = _parse_auto_approve_rules("office:10.0.0.0/24 | home:192.168.1.0/24")
        assert r == {"office": "10.0.0.0/24", "home": "192.168.1.0/24"}

    def test_parse_skips_malformed(self):
        from orchestrator.config import _parse_auto_approve_rules
        r = _parse_auto_approve_rules("office:10.0.0.0/24 | badrule | home:192.168.1.0/24")
        assert r == {"office": "10.0.0.0/24", "home": "192.168.1.0/24"}

    def test_parse_trims_whitespace(self):
        from orchestrator.config import _parse_auto_approve_rules
        r = _parse_auto_approve_rules("  office : 10.0.0.0/24  ")
        assert r == {"office": "10.0.0.0/24"}


class TestValidateTokens:
    def test_admin_token_required(self, monkeypatch):
        import orchestrator.config as cfg
        monkeypatch.setattr(cfg, "ADMIN_TOKEN", "")
        monkeypatch.setattr(cfg, "HUB_AGENT_TOKEN", "valid-token")
        monkeypatch.setattr(cfg, "HUB_ENDPOINT", "1.2.3.4:51820")
        try:
            cfg.validate_tokens_at_startup()
            assert False, "should have raised"
        except SystemExit:
            pass

    def test_valid_tokens_pass(self, monkeypatch):
        import orchestrator.config as cfg
        monkeypatch.setattr(cfg, "ADMIN_TOKEN", "secure-token-abc")
        monkeypatch.setattr(cfg, "HUB_AGENT_TOKEN", "secure-hub-token")
        monkeypatch.setattr(cfg, "HUB_ENDPOINT", "1.2.3.4:51820")
        cfg.validate_tokens_at_startup()

    def test_insecure_admin_token_fails(self, monkeypatch):
        import orchestrator.config as cfg
        monkeypatch.setattr(cfg, "ADMIN_TOKEN", "changeme")
        monkeypatch.setattr(cfg, "HUB_AGENT_TOKEN", "secure-hub-token")
        monkeypatch.setattr(cfg, "HUB_ENDPOINT", "1.2.3.4:51820")
        try:
            cfg.validate_tokens_at_startup()
            assert False, "should have raised"
        except SystemExit:
            pass


class TestCheckDependencies:
    def test_python3_found(self):
        from orchestrator.config import check_dependencies
        check_dependencies()
