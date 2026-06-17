import os, sys, tempfile, pytest, json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PACKAGE_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, PACKAGE_DIR)

_JWT_SECRET_FILE = tempfile.mktemp()
_STATE_FILE = tempfile.mktemp()
_REVOKED_FILE = tempfile.mktemp()


def pytest_configure():
    with open(_JWT_SECRET_FILE, "w") as f:
        f.write("test-secret-min-32-chars-xxxxxxxxxxxxxx")
    open(_STATE_FILE, "w").close()
    open(_REVOKED_FILE, "w").close()

    os.environ.setdefault("ADMIN_TOKEN", "test-admin-token-123")
    os.environ.setdefault("HUB_AGENT_TOKEN", "test-hub-token-456")
    os.environ.setdefault("HUB_ENDPOINT", "10.0.0.1:51820")
    os.environ.setdefault("ORCH_PORT", "19999")
    os.environ.setdefault("AUTO_APPROVE_ENABLED", "0")
    os.environ.setdefault("HUB_RETRY_COUNT", "1")
    os.environ.setdefault("BACKUP_ENABLED", "0")
    os.environ.setdefault("EVENTS_LOG_PATH", "/dev/null")
    os.environ["JWT_SECRET_PATH"] = _JWT_SECRET_FILE
    os.environ["ORCH_STATE_PATH"] = _STATE_FILE
    os.environ["JWT_REVOKED_PATH"] = _REVOKED_FILE


def pytest_unconfigure():
    for f in (_JWT_SECRET_FILE, _STATE_FILE, _REVOKED_FILE):
        try:
            os.remove(f)
        except OSError:
            pass


@pytest.fixture
def init_state():
    from orchestrator.state import STATE, DEFAULT_STATE
    STATE.clear()
    STATE.update(json.loads(json.dumps(DEFAULT_STATE)))
    return STATE


@pytest.fixture
def sample_state(init_state):
    from orchestrator import state
    state.STATE["users"] = {
        "alice": {
            "token": "u_token_alice",
            "disabled": False,
            "created_ts": 1000,
            "max_peers": 5,
            "max_networks": 5,
            "metadata": {},
        }
    }
    state.STATE["peers"] = {
        "p1": {
            "public_key": "pk_p1",
            "ip": "10.0.0.1",
            "networks": ["lan1"],
            "user_id": "alice",
            "enabled": True,
            "created_ts": 1000,
            "keepalive": 25,
            "metadata": {},
        }
    }
    state.STATE["networks"] = {
        "lan1": {
            "cidr": "10.0.0.0/24",
            "description": "test lan",
            "user_id": "alice",
            "tag": "office",
            "created_ts": 1000,
            "alloc": {"reserved": [], "assigned": {"p1": "10.0.0.1"}},
        }
    }
    return state.STATE
