"""Tests del front-end CLI (orch-cli.py).

Estos tests NO tocan el orchestrator real: mockean `xmlrpc.client.ServerProxy`
para capturar el metodo RPC invocado y sus argumentos. Verifican que el parser
argparse y el dispatcher del CLI mapeen cada subcomando al metodo y argumentos
correctos, incluyendo los defaults y el contrato de tokens.

No modifica ningun test existente; es un archivo nuevo e independiente.
"""

import importlib.util
import json
import os
import sys

import pytest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PKG_DIR = os.path.dirname(BASE_DIR)
_CLI_PATH = os.path.join(PKG_DIR, "orch-cli.py")


def _load_cli():
    spec = importlib.util.spec_from_file_location("_orch_cli_under_test", _CLI_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _FakeClient:
    """ServerProxy simulado: registra (method, args) de cada llamada RPC."""

    def __init__(self):
        self.calls = []
        self._responses = {}

    def set_response(self, method, value):
        self._responses[method] = value

    def __getattr__(self, name):
        # name contiene puntos ("orch.health"); se accede via __getattr__ en el CLI
        def _invoke(*args):
            self.calls.append((name, args))
            if name in self._responses:
                resp = self._responses[name]
                return resp(*args) if callable(resp) else resp
            return {"ok": True}

        return _invoke


@pytest.fixture
def orch_cli(monkeypatch, capsys):
    mod = _load_cli()
    state = {"client": None, "responses": {}}

    def _factory(url, *a, **kw):
        c = _FakeClient()
        # respuestas que el CLI lee internamente (result['jwt'])
        c.set_response("auth.login", {"jwt": "JWTVALUE", "expires_at": 123})
        c.set_response("auth.refresh", {"jwt": "JWTVALUE", "expires_at": 123})
        for m, v in state["responses"].items():
            c.set_response(m, v)
        state["client"] = c
        return c

    mod.ServerProxy = _factory
    # aislar defaults: que --admin-token/--token por defecto sean "" (sin env)
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("JWT", raising=False)

    class _Runner:
        def run(self, argv, responses=None):
            state["client"] = None
            state["responses"] = responses or {}
            monkeypatch.setattr(sys, "argv", ["orch-cli"] + list(argv))
            mod.main()
            return state["client"], capsys.readouterr()

    return _Runner()


def _last(client):
    """Devuelve la ultima llamada RPC como (method, args)."""
    assert client.calls, "el CLI no invoco ningun metodo RPC"
    return client.calls[-1]


# ───────────────────────────── core ─────────────────────────────


class TestCore:
    def test_health(self, orch_cli):
        client, _ = orch_cli.run(["health"])
        method, args = _last(client)
        assert method == "orch.health"
        assert args == (None,)

    def test_health_with_token(self, orch_cli):
        client, _ = orch_cli.run(["--token", "T", "health"])
        method, args = _last(client)
        assert method == "orch.health"
        assert args == ("T",)

    def test_metrics_admin_token(self, orch_cli):
        client, _ = orch_cli.run(["--admin-token", "AT", "metrics"])
        method, args = _last(client)
        assert method == "orch.metrics"
        assert args == ("AT",)

    def test_metrics_falls_back_to_token(self, orch_cli):
        # sin --admin-token (default ""), metrics usa --token
        client, _ = orch_cli.run(["--token", "T", "metrics"])
        method, args = _last(client)
        assert method == "orch.metrics"
        assert args == ("T",)

    def test_metrics_no_token(self, orch_cli):
        client, _ = orch_cli.run(["metrics"])
        method, args = _last(client)
        assert args == (None,)

    def test_events_admin_token(self, orch_cli):
        client, _ = orch_cli.run(["--admin-token", "AT", "events"])
        method, args = _last(client)
        assert method == "orch.events"
        assert args == ("AT",)


# ───────────────────────────── users ─────────────────────────────


class TestUsers:
    def test_user_create(self, orch_cli):
        client, _ = orch_cli.run(["--admin-token", "AT", "user-create", "bob"])
        method, args = _last(client)
        assert method == "orch.user-create"
        assert args == ("bob", "AT")

    def test_user_list(self, orch_cli):
        client, _ = orch_cli.run(["--admin-token", "AT", "user-list"])
        method, args = _last(client)
        assert method == "orch.user-list"
        assert args == ("AT",)

    def test_user_get(self, orch_cli):
        client, _ = orch_cli.run(["--admin-token", "AT", "user-get", "bob"])
        method, args = _last(client)
        assert method == "orch.user-get"
        assert args == ("bob", "AT")

    def test_user_delete(self, orch_cli):
        client, _ = orch_cli.run(["--admin-token", "AT", "user-delete", "bob"])
        method, args = _last(client)
        assert args == ("bob", False, "AT")

    def test_user_delete_purge(self, orch_cli):
        client, _ = orch_cli.run(["--admin-token", "AT", "user-delete", "bob", "--purge"])
        method, args = _last(client)
        assert method == "orch.user-delete"
        assert args == ("bob", True, "AT")

    def test_issue_user_token(self, orch_cli):
        client, _ = orch_cli.run(["--admin-token", "AT", "issue-user-token", "bob"])
        method, args = _last(client)
        assert method == "orch.issue-user-token"
        assert args == ("bob", "AT")


# ───────────────────────────── auth ─────────────────────────────


class TestAuth:
    def test_auth_login(self, orch_cli):
        client, out = orch_cli.run(["auth-login", "alice", "secret"])
        method, args = _last(client)
        assert method == "auth.login"
        # contrato: (user_id, peer_id=user_id, user_token, scopes, ttl)
        assert args[0] == "alice"
        assert args[1] == "alice"
        assert args[2] == "secret"
        assert args[3] == ["*"]
        assert args[4] is None
        # el CLI imprime el JWT recibido
        assert "JWTVALUE" in out.out
        assert "Exporta el JWT" in out.out

    def test_auth_login_scopes_ttl(self, orch_cli):
        client, _ = orch_cli.run(
            ["auth-login", "alice", "secret", "--scopes", "peer:read, peer:write", "--ttl", "120"]
        )
        method, args = _last(client)
        assert method == "auth.login"
        assert args[3] == ["peer:read", "peer:write"]
        assert args[4] == 120

    def test_auth_refresh(self, orch_cli):
        client, out = orch_cli.run(["auth-refresh", "OLDJWT", "--ttl", "60"])
        method, args = _last(client)
        assert method == "auth.refresh"
        assert args == ("OLDJWT", 60)
        assert "JWTVALUE" in out.out

    def test_auth_refresh_from_env(self, monkeypatch, orch_cli):
        monkeypatch.setenv("JWT", "ENVJWT")
        client, _ = orch_cli.run(["auth-refresh"])
        method, args = _last(client)
        assert method == "auth.refresh"
        assert args == ("ENVJWT", None)

    def test_auth_whoami(self, orch_cli):
        client, _ = orch_cli.run(["--token", "TOK", "auth-whoami"])
        method, args = _last(client)
        assert method == "auth.whoami"
        assert args == ("TOK",)


# ───────────────────────────── revoke ─────────────────────────────


class TestRevoke:
    def test_revoke(self, orch_cli):
        client, _ = orch_cli.run(["--admin-token", "AT", "revoke", "JTI123"])
        method, args = _last(client)
        assert method == "orch.revoke"
        assert args == ("JTI123", "AT")


# ───────────────────────────── networks ─────────────────────────────


class TestNetworks:
    def test_net_create_defaults(self, orch_cli):
        client, _ = orch_cli.run(
            ["--admin-token", "AT", "net-create", "lan1", "10.0.0.0/24"]
        )
        method, args = _last(client)
        assert method == "network.create"
        # (network_id, tunnel_cidr, topology, hub_peer_id, user_id, admin_token)
        assert args == ("lan1", "10.0.0.0/24", "hub-spoke", "HUB", None, "AT")

    def test_net_create_full(self, orch_cli):
        client, _ = orch_cli.run(
            [
                "--admin-token", "AT",
                "net-create", "lan1", "10.0.0.0/24",
                "--topology", "mesh",
                "--hub-peer-id", "hub01",
                "--user-id", "tenant-a",
            ]
        )
        method, args = _last(client)
        assert args == ("lan1", "10.0.0.0/24", "mesh", "hub01", "tenant-a", "AT")

    def test_net_list(self, orch_cli):
        client, _ = orch_cli.run(["--admin-token", "AT", "net-list", "--user-id", "u1"])
        method, args = _last(client)
        assert method == "network.list"
        assert args == ("u1", "AT", None)

    def test_net_list_with_tenant_token(self, orch_cli):
        client, _ = orch_cli.run(["--token", "T", "net-list"])
        method, args = _last(client)
        assert method == "network.list"
        # user_id None, admin_token "", tenant token "T"
        assert args == (None, "", "T")

    def test_net_get(self, orch_cli):
        client, _ = orch_cli.run(["--admin-token", "AT", "net-get", "lan1"])
        method, args = _last(client)
        assert method == "network.get"
        assert args == ("lan1", "AT", None)

    def test_net_topology(self, orch_cli):
        client, _ = orch_cli.run(["--admin-token", "AT", "net-topology", "lan1"])
        method, args = _last(client)
        assert method == "network.get_topology"
        assert args == ("lan1", "AT", None)

    def test_net_delete(self, orch_cli):
        client, _ = orch_cli.run(["--admin-token", "AT", "net-delete", "lan1"])
        method, args = _last(client)
        assert method == "network.delete"
        assert args == ("lan1", False, "AT")

    def test_net_delete_purge(self, orch_cli):
        client, _ = orch_cli.run(["--admin-token", "AT", "net-delete", "lan1", "--purge"])
        method, args = _last(client)
        assert args == ("lan1", True, "AT")

    def test_net_set_topology(self, orch_cli):
        client, _ = orch_cli.run(["--admin-token", "AT", "net-set-topology", "lan1", "mesh"])
        method, args = _last(client)
        assert method == "network.set_topology"
        assert args == ("lan1", "mesh", "AT")

    def test_net_set_topology_invalid_rejected(self, orch_cli):
        with pytest.raises(SystemExit):
            orch_cli.run(["--admin-token", "AT", "net-set-topology", "lan1", "bogus"])

    def test_net_set_topology_changed_branch(self, orch_cli):
        client, out = orch_cli.run(
            ["--admin-token", "AT", "net-set-topology", "lan1", "hub-mesh"],
            responses={"network.set_topology": {"changed": True, "topology": "hub-mesh"}},
        )
        assert _last(client)[0] == "network.set_topology"
        assert "hub-mesh activo" in out.out

    def test_net_set_topology_unchanged_branch(self, orch_cli):
        client, out = orch_cli.run(
            ["--admin-token", "AT", "net-set-topology", "lan1", "mesh"],
            responses={"network.set_topology": {"changed": False}},
        )
        assert "sin cambios" in out.out


# ───────────────────────────── mesh / reachability ─────────────────────────────


_MESH_LIST_RESPONSE = [
    {"peer_id": "p1", "tunnel_ip": "10.0.0.1",
     "endpoint": "1.2.3.4:51820", "alive": True},
    {"peer_id": "p2", "tunnel_ip": "10.0.0.2",
     "endpoint": None, "alive": False},
]

_HUBMESH_DICT_RESPONSE = {
    "direct": [
        {"peer_id": "p1", "tunnel_ip": "10.0.0.1",
         "endpoint": "1.2.3.4:51820", "nat_type": "full-cone", "relay_mode": "auto"},
    ],
    "relay_only": [
        {"peer_id": "p2", "tunnel_ip": "10.0.0.2",
         "endpoint": None, "nat_type": "symmetric", "relay_mode": "force_relay"},
    ],
    "relay_cidr": "10.0.0.0/24",
}


class TestMeshCommands:
    def test_mesh_peers_list_response(self, orch_cli):
        client, out = orch_cli.run(
            ["--admin-token", "AT", "mesh-peers", "lan1"],
            responses={"config.get_mesh_peers": _MESH_LIST_RESPONSE},
        )
        method, args = _last(client)
        assert method == "config.get_mesh_peers"
        # peer_id por defecto "admin-query" cuando no se pasa --peer-id
        assert args == ("admin-query", "lan1", "AT")
        # tabla lista: cabeceras y al menos un peer
        assert "PEER ID" in out.out
        assert "p1" in out.out

    def test_mesh_peers_with_peer_id(self, orch_cli):
        client, _ = orch_cli.run(
            ["--admin-token", "AT", "mesh-peers", "lan1", "--peer-id", "p_me"],
            responses={"config.get_mesh_peers": _MESH_LIST_RESPONSE},
        )
        method, args = _last(client)
        assert args == ("p_me", "lan1", "AT")

    def test_mesh_peers_dict_response(self, orch_cli):
        client, out = orch_cli.run(
            ["--admin-token", "AT", "mesh-peers", "lan1"],
            responses={"config.get_mesh_peers": _HUBMESH_DICT_RESPONSE},
        )
        assert _last(client)[0] == "config.get_mesh_peers"
        # tabla hub-mesh: columnas MODO con DIRECTO / RELAY
        assert "MODO" in out.out
        assert "DIRECTO" in out.out
        assert "RELAY" in out.out

    def test_peer_reachability_dict_response(self, orch_cli):
        client, out = orch_cli.run(
            ["--admin-token", "AT", "peer-reachability", "lan1"],
            responses={"config.get_mesh_peers": _HUBMESH_DICT_RESPONSE},
        )
        method, args = _last(client)
        assert method == "config.get_mesh_peers"
        assert args == ("admin-query", "lan1", "AT")
        assert "Relay CIDR" in out.out
        assert "DIRECTO" in out.out
        assert "RELAY" in out.out

    def test_peer_reachability_list_response_warns(self, orch_cli):
        client, out = orch_cli.run(
            ["--admin-token", "AT", "peer-reachability", "lan1"],
            responses={"config.get_mesh_peers": _MESH_LIST_RESPONSE},
        )
        # mesh puro: el CLI avisa que use mesh-peers
        assert "mesh puro" in out.out


# ───────────────────────────── peers ─────────────────────────────


class TestPeers:
    def test_peer_list(self, orch_cli):
        client, _ = orch_cli.run(["--admin-token", "AT", "peer-list", "--user-id", "u1"])
        method, args = _last(client)
        assert method == "peer.list"
        assert args == ("u1", "AT", None)

    def test_peer_get(self, orch_cli):
        client, _ = orch_cli.run(["--admin-token", "AT", "peer-get", "p1"])
        method, args = _last(client)
        assert method == "peer.get"
        assert args == ("p1", "AT", None)

    def test_peer_update_admin(self, orch_cli):
        client, _ = orch_cli.run(
            ["--admin-token", "AT", "peer-update-admin", "p1", '{"tags":["x"]}']
        )
        method, args = _last(client)
        assert method == "peer.update_admin"
        assert args == ("p1", {"tags": ["x"]}, "AT")

    def test_peer_update_admin_bad_json(self, orch_cli):
        with pytest.raises(json.JSONDecodeError):
            orch_cli.run(["--admin-token", "AT", "peer-update-admin", "p1", "not-json"])

    def test_peer_unregister(self, orch_cli):
        client, _ = orch_cli.run(["--token", "T", "peer-unregister", "p1"])
        method, args = _last(client)
        assert method == "peer.unregister"
        assert args == ("p1", "T", "")

    def test_assign_network(self, orch_cli):
        client, _ = orch_cli.run(
            ["--admin-token", "AT", "assign-network", "p1", "lan1", "10.0.0.5"]
        )
        method, args = _last(client)
        assert method == "peer.assign_network"
        assert args == ("p1", "lan1", "10.0.0.5", None, "AT", None)

    def test_assign_network_with_role(self, orch_cli):
        client, _ = orch_cli.run(
            ["--admin-token", "AT", "assign-network", "p1", "lan1", "10.0.0.5", "--role", "spoke"]
        )
        method, args = _last(client)
        assert args == ("p1", "lan1", "10.0.0.5", "spoke", "AT", None)

    def test_remove_network(self, orch_cli):
        client, _ = orch_cli.run(["--admin-token", "AT", "remove-network", "p1", "lan1"])
        method, args = _last(client)
        assert method == "peer.remove_from_network"
        assert args == ("p1", "lan1", "AT")


# ───────────────────────────── argparse contract ─────────────────────────────


class TestArgparseContract:
    """--admin-token/--token viven en el parser principal (no en subparsers).

    Esto documenta el contrato actual (ver AGENTS.md): deben ir ANTES del
    subcomando. Si se ponen despues, argparse los rechaza.
    """

    def test_token_before_subcommand(self, orch_cli):
        client, _ = orch_cli.run(["--admin-token", "AT", "--token", "T", "health"])
        method, args = _last(client)
        assert method == "orch.health"
        # health usa args.token
        assert args == ("T",)

    def test_token_after_subcommand_rejected(self, orch_cli):
        with pytest.raises(SystemExit):
            orch_cli.run(["health", "--admin-token", "AT"])

    def test_url_override_via_env(self, monkeypatch, orch_cli):
        # ORCH_URL solo cambia la URL pasada al ServerProxy mockeado
        monkeypatch.setenv("ORCH_URL", "http://example:9999/RPC2")
        client, _ = orch_cli.run(["health"])
        assert client.calls

    def test_no_subcommand_rejected(self, orch_cli):
        with pytest.raises(SystemExit):
            orch_cli.run([])
