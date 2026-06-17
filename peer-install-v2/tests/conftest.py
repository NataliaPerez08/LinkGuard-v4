import os, sys, tempfile, pytest, json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PACKAGE_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, PACKAGE_DIR)

_WG_DIR = tempfile.mktemp()
_STATE_FILE = os.path.join(_WG_DIR, "wg-auto.json")
_PRIV_KEY = os.path.join(_WG_DIR, "wg0.key")
_PUB_KEY = os.path.join(_WG_DIR, "wg0.pub")
_CONF = os.path.join(_WG_DIR, "wg0.conf")


def pytest_configure():
    os.environ.setdefault("WG_DIR", _WG_DIR)
    os.environ.setdefault("WG_AUTO_STATE", _STATE_FILE)
    os.environ.setdefault("WG_PRIV_KEY_PATH", _PRIV_KEY)
    os.environ.setdefault("WG_PUB_KEY_PATH", _PUB_KEY)
    os.environ.setdefault("WG_CONF_PATH", _CONF)
    os.environ.setdefault("ORCH_URL", "http://127.0.0.1:17999/RPC2")
    os.environ.setdefault("ORCH_TOKEN", "test-orch-token")
    os.environ.setdefault("PUBLIC_IP", "192.0.2.1")
    os.environ.setdefault("WG_LISTEN_PORT", "51820")
    os.environ.setdefault("PEER_ID", "test-peer")
    os.environ.setdefault("PEER_OWNER", "test-user")
    os.environ.setdefault("HUB_MESH_MODE", "off")
    os.environ.setdefault("WG_HEARTBEAT_INTERVAL", "5")
    os.environ.setdefault("WG_KEEPALIVE", "10")
    os.environ.setdefault("WG_JWT_TTL", "3600")
    os.makedirs(_WG_DIR, exist_ok=True)
    with open(_PRIV_KEY, "w") as f:
        f.write("test-priv-key-xxxxxxxxxxxxxxxxxxxxxx\n")
    with open(_PUB_KEY, "w") as f:
        f.write("test-pub-key-xxxxxxxxxxxxxxxxxxxxxxx\n")


@pytest.fixture
def state_data() -> dict:
    return {
        "peer_id": "test-peer",
        "config_version": 1,
        "jwt": "test-jwt-xxx",
        "jwt_expires_at": 9999999999,
        "topology": "hub-spoke",
    }


@pytest.fixture
def peer_env() -> str:
    path = os.path.join(_WG_DIR, "peer.env")
    content = "ORCH_TOKEN=from-env-file\nPUBLIC_IP=10.0.0.99\n"
    with open(path, "w") as f:
        f.write(content)
    return path


def reload_config():
    import importlib
    from peer_register import config
    importlib.reload(config)
