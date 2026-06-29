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


# ──────────────────────── _read_jwt_secret ────────────────────────


class TestReadJwtSecret:
    def test_reads_secret(self, tmp_path, monkeypatch):
        secret_file = tmp_path / "jwt_secret"
        secret_file.write_text("my-secret-key-min-32-chars-xxxxxxxx")
        monkeypatch.setenv("JWT_SECRET_PATH", str(secret_file))
        from importlib import reload
        import orchestrator.config as cfg
        reload(cfg)
        from orchestrator.auth import _read_jwt_secret
        s = _read_jwt_secret()
        assert s == "my-secret-key-min-32-chars-xxxxxxxx"

    def test_caches_on_repeat(self, tmp_path, monkeypatch):
        secret_file = tmp_path / "jwt_secret"
        secret_file.write_text("my-secret-key-min-32-chars-xxxxxxxx")
        monkeypatch.setenv("JWT_SECRET_PATH", str(secret_file))
        from importlib import reload
        import orchestrator.config as cfg
        reload(cfg)
        from orchestrator.auth import _read_jwt_secret, _JWT_SECRET_HASH
        s1 = _read_jwt_secret()
        old_hash = _JWT_SECRET_HASH
        s2 = _read_jwt_secret()
        assert s1 == s2
        assert _JWT_SECRET_HASH == old_hash

    def test_detects_change(self, tmp_path, monkeypatch):
        secret_file = tmp_path / "jwt_secret"
        secret_file.write_text("initial-secret-min-32-chars-xxxxx")
        monkeypatch.setenv("JWT_SECRET_PATH", str(secret_file))
        from importlib import reload
        import orchestrator.config as cfg
        reload(cfg)
        from orchestrator.auth import _read_jwt_secret
        _read_jwt_secret()
        secret_file.write_text("changed-secret-min-32-chars-xxxxxxx")
        s2 = _read_jwt_secret()
        assert s2 == "changed-secret-min-32-chars-xxxxxxx"

    def test_empty_raises(self, tmp_path, monkeypatch):
        secret_file = tmp_path / "jwt_secret"
        secret_file.write_text("")
        monkeypatch.setenv("JWT_SECRET_PATH", str(secret_file))
        from importlib import reload
        import orchestrator.config as cfg
        reload(cfg)
        from orchestrator.auth import _read_jwt_secret
        with pytest.raises(RuntimeError, match="vacio"):
            _read_jwt_secret()

    def test_missing_raises(self, tmp_path, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_PATH", str(tmp_path / "no-such-file"))
        from importlib import reload
        import orchestrator.config as cfg
        reload(cfg)
        from orchestrator.auth import _read_jwt_secret
        with pytest.raises(RuntimeError, match="no existe"):
            _read_jwt_secret()


# ──────────────────────── _enforce_tenant_for_peer ────────────────────────


class TestEnforceTenantForPeer:
    def test_owner_match(self, sample_state):
        from orchestrator.auth import _enforce_tenant_for_peer
        _enforce_tenant_for_peer("alice", "p1")

    def test_cross_tenant(self, sample_state):
        from orchestrator.auth import _enforce_tenant_for_peer
        with pytest.raises(PermissionError, match="cross-tenant"):
            _enforce_tenant_for_peer("other-user", "p1")

    def test_missing_peer(self, sample_state):
        from orchestrator.auth import _enforce_tenant_for_peer
        with pytest.raises(KeyError):
            _enforce_tenant_for_peer("alice", "nonexistent")


# ──────────────────────── _filter_events_for_tenant ────────────────────────


class TestFilterEventsForTenant:
    def test_include_own_peer_events(self, init_state):
        from orchestrator import state
        from orchestrator.auth import _filter_events_for_tenant
        state.STATE["peers"]["p1"] = {"user_id": "alice"}
        state.STATE["events"] = [
            {"kind": "peer_created", "detail": {"peer_id": "p1"}},
        ]
        filtered = _filter_events_for_tenant("alice")
        assert len(filtered) == 1

    def test_exclude_other_peer_events(self, init_state):
        from orchestrator import state
        from orchestrator.auth import _filter_events_for_tenant
        state.STATE["peers"]["p1"] = {"user_id": "alice"}
        state.STATE["peers"]["p2"] = {"user_id": "other"}
        state.STATE["events"] = [
            {"kind": "peer_created", "detail": {"peer_id": "p2"}},
        ]
        filtered = _filter_events_for_tenant("alice")
        assert len(filtered) == 0

    def test_filter_by_network(self, init_state):
        from orchestrator import state
        from orchestrator.auth import _filter_events_for_tenant
        state.STATE["networks"]["n1"] = {"user_id": "alice"}
        state.STATE["networks"]["n2"] = {"user_id": "other"}
        state.STATE["events"] = [
            {"kind": "network_created", "detail": {"network_id": "n2"}},
        ]
        filtered = _filter_events_for_tenant("alice")
        assert len(filtered) == 0

    def test_filter_by_network_include(self, init_state):
        from orchestrator import state
        from orchestrator.auth import _filter_events_for_tenant
        state.STATE["networks"]["n1"] = {"user_id": "alice"}
        state.STATE["events"] = [
            {"kind": "network_created", "detail": {"network_id": "n1"}},
        ]
        filtered = _filter_events_for_tenant("alice")
        assert len(filtered) == 1

    def test_empty_events(self, init_state):
        from orchestrator.auth import _filter_events_for_tenant
        filtered = _filter_events_for_tenant("alice")
        assert filtered == []

    def test_missing_detail_graceful(self, init_state):
        from orchestrator import state
        from orchestrator.auth import _filter_events_for_tenant
        state.STATE["events"] = [
            {"kind": "unknown", "detail": None},
        ]
        filtered = _filter_events_for_tenant("alice")
        assert len(filtered) == 1
