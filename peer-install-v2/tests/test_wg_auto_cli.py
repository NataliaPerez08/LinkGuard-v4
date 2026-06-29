"""Tests del front-end CLI del peer (wg-auto-cli.py).

Mockean `xmlrpc.client.ServerProxy` para capturar el metodo RPC invocado y
sus argumentos, y verifican el parser argparse + dispatcher del CLI local.
Incluye pruebas de rotate-key (subprocess mockeado) y mesh-status (lectura
del .conf + state).

No modifica ningun test existente; es un archivo nuevo e independiente.
"""

import importlib.util
import json
import os
import sys

import pytest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PKG_DIR = os.path.dirname(BASE_DIR)
_CLI_PATH = os.path.join(PKG_DIR, "wg-auto-cli.py")


def _load_cli():
    spec = importlib.util.spec_from_file_location("_wg_auto_cli_under_test", _CLI_PATH)
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
        def _invoke(*args):
            self.calls.append((name, args))
            if name in self._responses:
                resp = self._responses[name]
                return resp(*args) if callable(resp) else resp
            return {"ok": True}

        return _invoke


@pytest.fixture
def peer_cli(monkeypatch, capsys, tmp_path):
    # aislar entorno ANTES de cargar el modulo (lee env al importar)
    monkeypatch.setenv("PEER_ID", "test-peer")
    monkeypatch.setenv("ORCH_TOKEN", "TEST-ORCH-TOK")
    monkeypatch.setenv("PEER_ENV_PATH", str(tmp_path / "no-such.env"))
    monkeypatch.setenv("WG_AUTO_STATE", str(tmp_path / "wg-auto.json"))
    monkeypatch.setenv("WG_CONF_PATH", str(tmp_path / "wg0.conf"))
    monkeypatch.setenv("WG_INTERFACE", "wg0")
    monkeypatch.setenv("WG_DIR", str(tmp_path))
    monkeypatch.delenv("JWT", raising=False)

    mod = _load_cli()
    state = {"client": None, "responses": {}, "state_data": None}

    def _factory(url, *a, **kw):
        c = _FakeClient()
        for m, v in state["responses"].items():
            c.set_response(m, v)
        state["client"] = c
        return c

    mod.ServerProxy = _factory

    class _Runner:
        def run(self, argv, responses=None, state_data=None):
            state["client"] = None
            state["responses"] = responses or {}
            # escribir state JSON si se pide
            if state_data is not None:
                with open(os.environ["WG_AUTO_STATE"], "w") as f:
                    json.dump(state_data, f)
            else:
                # asegurar state vacio
                try:
                    os.remove(os.environ["WG_AUTO_STATE"])
                except FileNotFoundError:
                    pass
            monkeypatch.setattr(sys, "argv", ["wg-auto-cli"] + list(argv))
            mod.main()
            # comandos como mesh-status no abren ServerProxy -> client None
            client = state["client"] or _FakeClient()
            return client, capsys.readouterr()

    return _Runner()


def _last(client):
    assert client.calls, "el CLI no invoco ningun metodo RPC"
    return client.calls[-1]


# ───────────────────────────── peer ops ─────────────────────────────


class TestPeerOps:
    def test_unregister(self, peer_cli):
        client, _ = peer_cli.run(["unregister"])
        method, args = _last(client)
        assert method == "peer.unregister"
        # rpc_call añade el token al final
        assert args == ("test-peer", "TEST-ORCH-TOK")

    def test_unregister_uses_url_flag(self, peer_cli):
        client, _ = peer_cli.run(["--url", "http://x:9999/RPC2", "unregister"])
        # el mock captura igualmente la llamada
        assert _last(client)[0] == "peer.unregister"

    def test_update(self, peer_cli):
        client, _ = peer_cli.run(["update", '{"hostname":"h1"}'])
        method, args = _last(client)
        assert method == "peer.update"
        assert args == ("test-peer", {"hostname": "h1"}, "TEST-ORCH-TOK")

    def test_update_bad_json_exits(self, peer_cli):
        with pytest.raises(SystemExit):
            peer_cli.run(["update", "not-json"])

    def test_status(self, peer_cli):
        client, _ = peer_cli.run(["status"])
        method, args = _last(client)
        assert method == "peer.get_status"
        assert args == ("test-peer", "TEST-ORCH-TOK")

    def test_orch_health(self, peer_cli):
        client, _ = peer_cli.run(["orch-health"])
        method, args = _last(client)
        assert method == "orch.health"
        assert args == ("TEST-ORCH-TOK",)


# ───────────────────────────── networks ─────────────────────────────


class TestNetworks:
    def test_list_networks(self, peer_cli):
        client, _ = peer_cli.run(["list-networks"])
        method, args = _last(client)
        assert method == "network.list"
        # llamada directa con (None, None, token)
        assert args == (None, None, "TEST-ORCH-TOK")

    def test_add_to_network(self, peer_cli):
        client, _ = peer_cli.run(["add-to-network", "lan1", "spoke", "10.0.0.5"])
        method, args = _last(client)
        assert method == "network.add_peer"
        assert args == ("lan1", "test-peer", "spoke", "10.0.0.5", "TEST-ORCH-TOK")

    def test_rm_from_network(self, peer_cli):
        client, _ = peer_cli.run(["rm-from-network", "lan1"])
        method, args = _last(client)
        assert method == "network.remove_peer"
        assert args == ("lan1", "test-peer", "TEST-ORCH-TOK")

    def test_topology(self, peer_cli):
        client, _ = peer_cli.run(["topology", "lan1"])
        method, args = _last(client)
        assert method == "network.get_topology"
        assert args == ("lan1", None, "TEST-ORCH-TOK")


# ───────────────────────────── advertised LANs ─────────────────────────────


class TestAdvertised:
    def test_list_advertised(self, peer_cli):
        client, _ = peer_cli.run(["list-advertised"])
        method, args = _last(client)
        assert method == "peer.list_advertised_networks"
        assert args == ("test-peer", "TEST-ORCH-TOK")

    def test_add_advertised(self, peer_cli):
        client, _ = peer_cli.run(
            ["add-advertised", "192.168.1.0/24", "lan1", "routes"]
        )
        method, args = _last(client)
        assert method == "peer.add_advertised_network"
        assert args == ("test-peer", "192.168.1.0/24", "lan1", "routes", "TEST-ORCH-TOK")

    def test_rm_advertised(self, peer_cli):
        client, _ = peer_cli.run(["rm-advertised", "3"])
        method, args = _last(client)
        assert method == "peer.remove_advertised_network"
        # el CLI convierte adv_id a int
        assert args == ("test-peer", 3, "TEST-ORCH-TOK")

    def test_rm_advertised_non_int_rejected(self, peer_cli):
        with pytest.raises((SystemExit, ValueError)):
            peer_cli.run(["rm-advertised", "abc"])


# ───────────────────────────── rotate-key ─────────────────────────────


class TestRotateKey:
    def test_rotate_key_delegates_and_exits(self, monkeypatch, peer_cli):
        # recargar el modulo para parchear subprocess en el modulo del CLI
        monkeypatch.setenv("PEER_ID", "test-peer")
        monkeypatch.setenv("ORCH_TOKEN", "TEST-ORCH-TOK")
        monkeypatch.setenv("PEER_ENV_PATH", "/no/such/env")
        mod = _load_cli()
        called = {"cmd": None}

        def _fake_call(cmd):
            called["cmd"] = cmd
            return 0

        monkeypatch.setattr(mod.subprocess, "call", _fake_call)
        monkeypatch.setattr(sys, "argv", ["wg-auto-cli", "rotate-key"])
        with pytest.raises(SystemExit) as exc:
            mod.main()
        assert exc.value.code == 0
        assert called["cmd"] == ["wg-auto-register", "rotate-key"]


# ───────────────────────────── mesh-status ─────────────────────────────


_SAMPLE_CONF_MESH = """[Interface]
PrivateKey = key
Address = 10.0.0.5/24

# Relay-via-HUB: relaypeer
[Peer]
# peer-a
PublicKey = PUBAAA
Endpoint = 1.2.3.4:51820
AllowedIPs = 10.0.0.1/32

[Peer]
# Directo: peer-b
PublicKey = PUBBBB
Endpoint = 5.6.7.8:51820
AllowedIPs = 10.0.0.2/32
"""


class TestMeshStatus:
    def test_mesh_puro(self, monkeypatch, peer_cli, tmp_path):
        conf = tmp_path / "wg0.conf"
        conf.write_text(_SAMPLE_CONF_MESH)
        monkeypatch.setenv("WG_CONF_PATH", str(conf))
        client, out = peer_cli.run(
            ["mesh-status"],
            state_data={"topology": "mesh", "peer_id": "test-peer"},
        )
        # no hay llamadas RPC; mesh-status solo lee el .conf
        assert client.calls == []
        assert "Topología: mesh" in out.out
        assert "peer-a" in out.out
        assert "peer-b" in out.out

    def test_hub_mesh_shows_mode_column(self, monkeypatch, peer_cli, tmp_path):
        conf = tmp_path / "wg0.conf"
        conf.write_text(_SAMPLE_CONF_MESH)
        monkeypatch.setenv("WG_CONF_PATH", str(conf))
        client, out = peer_cli.run(
            ["mesh-status"],
            state_data={"topology": "hub-mesh", "nat_type": "full-cone"},
        )
        assert "Topología: hub-mesh" in out.out
        assert "NAT type" in out.out
        assert "full-cone" in out.out
        # columna MODO con DIRECTO / HUB-RELAY
        assert "MODO" in out.out
        assert "DIRECTO" in out.out
        assert "HUB-RELAY" in out.out
        # relay sin bloque [Peer] aparece como comentario
        assert "relaypeer" in out.out

    def test_mesh_status_missing_conf(self, monkeypatch, peer_cli, tmp_path):
        monkeypatch.setenv("WG_CONF_PATH", str(tmp_path / "does-not-exist.conf"))
        client, out = peer_cli.run(
            ["mesh-status"],
            state_data={"topology": "mesh"},
        )
        assert "No se encontró" in out.out

    def test_mesh_status_defaults_to_hub_spoke(self, peer_cli):
        # sin state file -> topology default hub-spoke
        client, out = peer_cli.run(["mesh-status"])
        assert "Topología: hub-spoke" in out.out


# ───────────────────────────── auth token precedence ─────────────────────────────


class TestAuthPrecedence:
    def test_jwt_from_state_overrides_env(self, monkeypatch, peer_cli):
        # el state con jwt tiene prioridad sobre ORCH_TOKEN
        monkeypatch.setenv("PEER_ID", "test-peer")
        monkeypatch.setenv("ORCH_TOKEN", "TEST-ORCH-TOK")
        monkeypatch.setenv("PEER_ENV_PATH", "/no/such")
        monkeypatch.setenv("WG_AUTO_STATE", "/tmp/_wg_state_jwt.json")
        with open("/tmp/_wg_state_jwt.json", "w") as f:
            json.dump({"peer_id": "p-from-state", "jwt": "JWT-FROM-STATE"}, f)
        try:
            mod = _load_cli()
            captured = {}

            class _C:
                def __init__(self):
                    self.calls = []

                def __getattr__(self, n):
                    def _i(*a):
                        self.calls.append((n, a))
                        return {"ok": True}

                    return _i

            def _f(url, *a, **kw):
                captured["c"] = _C()
                return captured["c"]

            mod.ServerProxy = _f
            monkeypatch.setattr(sys, "argv", ["wg-auto-cli", "status"])
            mod.main()
            os.remove("/tmp/_wg_state_jwt.json")
        finally:
            pass
        method, args = captured["c"].calls[-1]
        assert method == "peer.get_status"
        # peer_id y token vienen del state
        assert args == ("p-from-state", "JWT-FROM-STATE")

    def test_env_token_when_no_state(self, peer_cli):
        client, _ = peer_cli.run(["status"])
        method, args = _last(client)
        assert args == ("test-peer", "TEST-ORCH-TOK")
