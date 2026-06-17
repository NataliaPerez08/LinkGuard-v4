#!/usr/bin/env python3
"""Tests funcionales del paquete orchestrator via XML-RPC."""

import os, sys, threading, time, xmlrpc.client, tempfile


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault("ADMIN_TOKEN", "test-admin-token-123")
os.environ.setdefault("HUB_AGENT_TOKEN", "test-hub-token-456")
os.environ.setdefault("HUB_ENDPOINT", "10.0.0.1:51820")
os.environ.setdefault("ORCH_PORT", "19999")
os.environ.setdefault("AUTO_APPROVE_ENABLED", "0")
os.environ.setdefault("HUB_RETRY_COUNT", "1")
os.environ.setdefault("BACKUP_ENABLED", "0")
os.environ.setdefault("EVENTS_LOG_PATH", "/dev/null")
os.environ.setdefault("JWT_REVOKED_PATH", tempfile.mktemp())

jwt_secret = tempfile.mktemp()
with open(jwt_secret, "w") as f:
    f.write("test-secret-min-32-chars-xxxxxxxxxxxxxx")
os.environ["JWT_SECRET_PATH"] = jwt_secret

state_file = tempfile.mktemp()
os.environ["ORCH_STATE_PATH"] = state_file

from orchestrator import main

def run():
    try:
        main()
    except: pass

t = threading.Thread(target=run, daemon=True)
t.start()
time.sleep(4)

c = xmlrpc.client.ServerProxy("http://127.0.0.1:19999/RPC2", allow_none=True)

def xml(method, *args):
    return getattr(c, method)(*args)

AT = "test-admin-token-123"
passed = 0
failed = []

def check(name, cond):
    global passed
    if cond:
        passed += 1
    else:
        failed.append(name)

# === HEALTH ===
r = xml("orch.health")
check("orch.health", r.get("status") == "healthy")

# === USERS ===
r = xml("orch.user-create", "alice", 5, 5, {}, AT)
check("orch.user-create", "token" in r)

try:
    xml("orch.user-create", "alice", 5, 5, {}, AT)
    check("orch.user-create dupe", False)
except Exception:
    check("orch.user-create dupe", True)

r = xml("orch.user-list", AT)
check("orch.user-list", "alice" in str(r))

r = xml("orch.user-get", "alice", AT)
check("orch.user-get", r.get("user_id") == "alice")

r = xml("orch.issue-user-token", "alice", AT)
check("orch.issue-user-token", "token" in r)

# === NETWORKS ===
r = xml("network.create", "lan1", "10.0.0.0/24", "test lan", "office", "admin", AT)
check("network.create", r.get("network_id") == "lan1")

r = xml("network.get", "lan1")
check("network.get", r.get("network", {}).get("cidr") == "10.0.0.0/24")

r = xml("network.set_topology", "lan1", "mesh")
check("network.set_topology", r.get("topology") == "mesh")

r = xml("network.get_topology", "lan1")
check("network.get_topology", "lan1" in str(r))

r = xml("network.list", AT)
check("network.list", "lan1" in str(r))

# === PEERS ===
# peer.create no está en el mapping XML-RPC original, crear via admin
from orchestrator.endpoints_peers import rpc_peer_create
r = rpc_peer_create({
    "public_key": "pk_alice_001", "peer_id": "p1", "network": "lan1",
    "metadata": {"hostname": "laptop"},
})
check("peer_create (direct)", r.get("ip") == "10.0.0.1")

r = xml("peer.get", "p1")
check("peer.get", r.get("peer", {}).get("public_key") == "pk_alice_001")

r = xml("peer.list", AT)
check("peer.list", "p1" in str(r))

# === ADVERTISED (via dict handler) ===
from orchestrator.endpoints_advertised import rpc_advertised_ips, rpc_advertised_endpoint, rpc_advertised_unset
r = rpc_advertised_ips({"network_id": "lan1"})
check("advertised_ips", r.get("count") == 1)

r = rpc_advertised_endpoint({"peer_id": "p1", "endpoint": "1.2.3.4:51820"})
check("advertised_endpoint", r.get("recorded"))

r = rpc_advertised_unset({"peer_id": "p1"})
check("advertised_unset", r.get("unset"))

# === EVENTS ===
r = xml("orch.events")
check("orch.events", isinstance(r.get("events"), list))

# === JWT (via dict handlers) ===
from orchestrator.endpoints_auth import rpc_jwt_issue, rpc_jwt_verify, rpc_jwt_revoke
r = rpc_jwt_issue({"user_id": "alice", "ttl": 30})
check("jwt_issue (direct)", "token" in r)
jwt_token = r["token"]

r = rpc_jwt_verify({"token": jwt_token})
check("jwt_verify (direct)", r.get("valid"))

r = rpc_jwt_revoke({"token": jwt_token, "reason": "test"})
check("jwt_revoke (direct)", r.get("revoked"))

try:
    rpc_jwt_verify({"token": jwt_token})
    check("jwt_verify revoked", False)
except Exception:
    check("jwt_verify revoked", True)

# === AUTH LOGIN/REFRESH/WHOAMI ===
try:
    r = xml("auth.login", "alice", None, "bad-token")
    check("auth.login bad token", False)
except Exception:
    check("auth.login bad token", True)

# === CONFIG ===
from orchestrator.endpoints_config import rpc_config_get, rpc_config_reload
r = rpc_config_get({})
check("config_get (direct)", "config_version" in r)

# === METRICS ===
from orchestrator.endpoints_orch import rpc_metrics
r = rpc_metrics({"token": AT})
check("rpc_metrics (direct)", r.get("peers_total", 0) >= 1)

# === PEER ADMIN OPS (via dict handlers) ===
from orchestrator.endpoints_peers import rpc_peer_stats, rpc_peer_verify
r = rpc_peer_stats({})
check("rpc_peer_stats", r.get("total") >= 1)

r = rpc_peer_verify({"peer_id": "p1", "public_key": "pk_alice_001"})
check("rpc_peer_verify exists", r.get("exists"))

r = rpc_peer_verify({"peer_id": "nonexistent", "public_key": ""})
check("rpc_peer_verify missing", not r.get("exists"))

# === CLEANUP ===
from orchestrator.endpoints_peers import rpc_peer_delete
from orchestrator.endpoints_networks import rpc_network_delete

r = rpc_peer_delete({"peer_id": "p1"})
check("peer_delete (direct)", r.get("deleted"))

r = rpc_network_delete({"network_id": "lan1"})
check("network_delete (direct)", r.get("deleted"))

r = xml("orch.user-delete", "alice", AT)
check("orch.user-delete", r.get("deleted") or "deleted" in str(r).lower())

from orchestrator.endpoints_orch import rpc_state_persist
r = rpc_state_persist({})
check("rpc_state_persist", r.get("persisted"))

# === SUMMARY ===
total = passed + len(failed)
print(f"\n{'='*50}")
print(f"  {passed}/{total} tests passed")
print(f"{'='*50}")
for name in failed:
    print(f"  [FAIL] {name}")
if failed:
    print(f"\n  {len(failed)} failures")
    sys.exit(1)
else:
    print(f"\n  All tests passed!")
    sys.exit(0)
