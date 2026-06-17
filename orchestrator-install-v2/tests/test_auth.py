import pytest


class TestJWT:
    def test_encode_decode(self):
        from orchestrator.auth import _jwt_encode, _jwt_decode
        token, exp = _jwt_encode({"user_id": "alice", "role": "admin"}, 60)
        assert isinstance(token, str)
        assert token.count(".") == 2
        payload = _jwt_decode(token)
        assert payload["user_id"] == "alice"
        assert payload["role"] == "admin"

    def test_decode_bad_token(self):
        from orchestrator.auth import _jwt_decode
        with pytest.raises(Exception):
            _jwt_decode("bad.token.here")

    def test_decode_expired(self):
        from orchestrator.auth import _jwt_encode, _jwt_decode
        import time
        token, _ = _jwt_encode({"user_id": "bob"}, 1)
        time.sleep(2)
        with pytest.raises(Exception):
            _jwt_decode(token)


class TestRevocation:
    def test_revoke_and_check(self):
        from orchestrator.auth import _jwt_encode, _revoke_jti, _is_revoked_jti
        import jwt as pyjwt
        token, exp = _jwt_encode({"user_id": "alice"}, 600)
        payload = pyjwt.decode(token, options={"verify_signature": False})
        jti = payload["jti"]
        assert not _is_revoked_jti(jti)
        _revoke_jti(jti, "test revocation", exp)
        assert _is_revoked_jti(jti)

    def test_revoked_cache(self):
        from orchestrator.auth import _REVOKED_CACHE, _load_revoked
        _REVOKED_CACHE = None
        r = _load_revoked()
        assert isinstance(r, dict)


class TestAuthFromToken:
    def test_no_token(self):
        from orchestrator.auth import _auth_from_token
        mode, uid, scopes, is_admin = _auth_from_token(None)
        assert mode == "none"

    def test_legacy_token(self):
        from orchestrator.auth import _auth_from_token
        mode, uid, scopes, is_admin = _auth_from_token("simple-legacy-token")
        assert mode == "legacy"

    def test_jwt_token(self):
        from orchestrator.auth import _auth_from_token, _jwt_encode
        token, _ = _jwt_encode({"user_id": "alice", "scopes": ["peer:*"], "role": "admin"}, 60)
        mode, uid, scopes, is_admin = _auth_from_token(token)
        assert mode == "jwt"
        assert uid == "alice"
        assert "peer:*" in scopes
        assert is_admin is True

    def test_revoked_jwt(self):
        from orchestrator.auth import _auth_from_token, _jwt_encode, _revoke_jti
        import jwt as pyjwt
        token, _ = _jwt_encode({"user_id": "alice"}, 60)
        payload = pyjwt.decode(token, options={"verify_signature": False})
        _revoke_jti(payload["jti"], "test", 9999999999)
        with pytest.raises(PermissionError, match="jwt revoked"):
            _auth_from_token(token)


class TestScopes:
    def test_exact_scope(self):
        from orchestrator.auth import _require_scope
        _require_scope(["peer:read", "peer:write"], "peer:read")

    def test_wildcard_prefix(self):
        from orchestrator.auth import _require_scope
        _require_scope(["peer:*"], "peer:read")

    def test_wildcard_all(self):
        from orchestrator.auth import _require_scope
        _require_scope(["*:*"], "peer:read")

    def test_wildcard_global(self):
        from orchestrator.auth import _require_scope
        _require_scope(["*"], "peer:read")

    def test_missing_scope(self):
        from orchestrator.auth import _require_scope
        with pytest.raises(PermissionError, match="missing scope"):
            _require_scope(["network:read"], "peer:read")


class TestAdminToken:
    def test_valid(self):
        from orchestrator.auth import orch_check_admin_token
        orch_check_admin_token("test-admin-token-123")

    def test_invalid(self):
        from orchestrator.auth import orch_check_admin_token
        with pytest.raises(PermissionError):
            orch_check_admin_token("wrong-token")

    def test_none(self):
        from orchestrator.auth import orch_check_admin_token
        with pytest.raises(PermissionError):
            orch_check_admin_token(None)


class TestUsers:
    def test_user_exists(self, init_state):
        from orchestrator.auth import _user_exists, _get_user, _issue_user_token, _check_user_token
        assert not _user_exists("alice")
        tok = _issue_user_token("alice")
        assert _user_exists("alice")
        u = _get_user("alice")
        assert u["token"] == tok
        _check_user_token("alice", tok)
        with pytest.raises(PermissionError):
            _check_user_token("alice", "wrong-token")

    def test_get_user_missing(self, init_state):
        from orchestrator.auth import _get_user
        with pytest.raises(KeyError):
            _get_user("nonexistent")


class TestQuotas:
    def test_peer_quota(self, init_state):
        from orchestrator.auth import _check_peer_quota, _get_tenant_quota
        q = _get_tenant_quota("alice")
        assert q["max_peers"] >= 1
        _check_peer_quota("alice")

    def test_peer_quota_exceeded(self, init_state):
        from orchestrator import state
        from orchestrator.auth import _check_peer_quota
        state.STATE["users"]["alice"] = {"max_peers": 0, "max_networks": 5}
        pid = "p_quota_test"
        state.STATE["peers"][pid] = {"public_key": "pk", "user_id": "alice"}
        with pytest.raises(PermissionError, match="quota"):
            _check_peer_quota("alice")

    def test_network_quota(self, init_state):
        from orchestrator.auth import _check_network_quota
        _check_network_quota("alice")

    def test_network_quota_exceeded(self, init_state):
        from orchestrator import state
        from orchestrator.auth import _check_network_quota
        state.STATE["users"]["alice"] = {"max_peers": 5, "max_networks": 0}
        with pytest.raises(PermissionError, match="quota"):
            _check_network_quota("alice")


class TestPeerOwner:
    def test_from_metadata_owner(self):
        from orchestrator.auth import _peer_owner_from_metadata
        assert _peer_owner_from_metadata({"owner": "bob"}) == "bob"

    def test_from_metadata_user_id(self):
        from orchestrator.auth import _peer_owner_from_metadata
        assert _peer_owner_from_metadata({"user_id": "bob"}) == "bob"

    def test_from_metadata_tenant(self):
        from orchestrator.auth import _peer_owner_from_metadata
        assert _peer_owner_from_metadata({"tenant": "bob"}) == "bob"

    def test_default(self):
        from orchestrator.auth import _peer_owner_from_metadata
        assert _peer_owner_from_metadata(None) == "default"
        assert _peer_owner_from_metadata({}) == "default"
