import os
import importlib
import pytest
from unittest.mock import patch

from peer_register import config


class TestConfig:
    def test_orch_url_default(self):
        assert config.ORCH_URL == "http://127.0.0.1:17999/RPC2"

    def test_orch_token_from_env(self):
        assert config.ORCH_TOKEN == "test-orch-token"

    def test_wg_paths(self):
        assert config.WG_INTERFACE == "wg0"
        assert config.WG_BIN == "/usr/bin/wg"
        assert config.WG_QUICK == "/usr/bin/wg-quick"

    def test_keepalive_default(self):
        assert config.DEFAULT_KEEPALIVE == 10

    def test_jwt_ttl(self):
        assert config.JWT_TTL == 3600

    def test_peer_env_loading(self, peer_env, monkeypatch):
        monkeypatch.setenv("PEER_ENV_PATH", peer_env)
        monkeypatch.delenv("ORCH_TOKEN", raising=False)
        importlib.reload(config)
        assert config.ORCH_TOKEN == "from-env-file"
        reloaded = importlib.reload(config)
        assert reloaded.ORCH_URL == "http://127.0.0.1:17999/RPC2"

    def test_peer_env_env_var_takes_precedence(self, peer_env, monkeypatch):
        monkeypatch.setenv("PEER_ENV_PATH", peer_env)
        monkeypatch.setenv("ORCH_TOKEN", "explicit-value")
        importlib.reload(config)
        assert config.ORCH_TOKEN == "explicit-value"

    def test_config_module_attributes(self):
        assert hasattr(config, "WG_DIR")
        assert hasattr(config, "STATE_PATH")
        assert hasattr(config, "WG_CONF_PATH")
        assert hasattr(config, "WG_PRIV_KEY_PATH")
        assert hasattr(config, "WG_PUB_KEY_PATH")
