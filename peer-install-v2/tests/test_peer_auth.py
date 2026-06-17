import time
import pytest
from unittest.mock import patch, MagicMock

from peer_register.auth import _jwt_needs_refresh, ensure_jwt_session, orch_token_for_call
from peer_register.state import save_state


class TestJwtNeedsRefresh:
    def test_no_expiry_needs_refresh(self):
        assert _jwt_needs_refresh({}) is True

    def test_expired_needs_refresh(self):
        st = {"jwt_expires_at": int(time.time()) - 10}
        assert _jwt_needs_refresh(st) is True

    def test_valid_no_refresh(self):
        st = {"jwt_expires_at": int(time.time()) + 3600}
        assert _jwt_needs_refresh(st) is False


class TestEnsureJwtSession:
    def test_returns_cached_jwt(self):
        st = {"jwt": "cached-jwt", "jwt_expires_at": int(time.time()) + 3600}
        token = ensure_jwt_session("test-peer", st)
        assert token == "cached-jwt"

    def test_login_on_missing_jwt(self):
        st = {}
        with patch("peer_register.auth.rpc") as mock_factory:
            mock_client = MagicMock()
            mock_client.__getattr__("auth.login").return_value = {
                "jwt": "default-jwt",
                "expires_at": int(time.time()) + 3600,
            }
            mock_factory.return_value = mock_client
            token = ensure_jwt_session("test-peer", st)
            assert token == "default-jwt"

    def test_refresh_on_expired(self):
        st = {"jwt": "old-jwt", "jwt_expires_at": int(time.time()) - 10}
        rpc_client = MagicMock()
        rpc_client.__getattr__("auth.refresh").return_value = {
            "jwt": "refreshed-jwt",
            "expires_at": int(time.time()) + 3600,
        }
        with patch("peer_register.auth.rpc", return_value=rpc_client):
            token = ensure_jwt_session("test-peer", st)
            assert token == "refreshed-jwt"

    def test_login_on_refresh_failure(self):
        st = {"jwt": "old-jwt", "jwt_expires_at": int(time.time()) - 10}
        with patch("peer_register.auth.rpc") as mock_factory:
            mock_client = MagicMock()
            mock_client.__getattr__("auth.refresh").side_effect = RuntimeError("refresh failed")
            mock_client.__getattr__("auth.login").return_value = {
                "jwt": "login-after-fail",
                "expires_at": int(time.time()) + 3600,
            }
            mock_factory.return_value = mock_client
            token = ensure_jwt_session("test-peer", st)
            assert token == "login-after-fail"


class TestOrchTokenForCall:
    def test_returns_token(self, tmp_path):
        state_file = tmp_path / "state.json"
        import os
        os.environ["WG_AUTO_STATE"] = str(state_file)
        st = {"jwt": "stored-jwt", "jwt_expires_at": int(time.time()) + 3600}
        save_state(st)
        token = orch_token_for_call("test-peer")
        assert token == "stored-jwt"
