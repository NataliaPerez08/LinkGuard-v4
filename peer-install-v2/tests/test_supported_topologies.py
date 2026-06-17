import os

from peer_register import config as cfg
from peer_register.config_gen import apply_config
from peer_register.state import load_state, save_state


def _reset_peer_runtime() -> None:
    save_state({})
    for path in (cfg.WG_CONF_PATH,):
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def _read_conf() -> str:
    with open(cfg.WG_CONF_PATH, "r") as f:
        return f.read()


class TestSupportedTopologies:
    def test_apply_config_hub_spoke(self, monkeypatch):
        _reset_peer_runtime()
        monkeypatch.setattr(
            "peer_register.config_gen._fetch_config",
            lambda peer_id: {
                "interface": {"address": "10.20.30.2/32", "mtu": 1420},
                "peer": {
                    "public_key": "hub-pub-key-xxxxxxxxxxxxxxxxxxxx",
                    "endpoint": "198.51.100.1:51820",
                    "allowed_ips": "10.20.30.0/24",
                    "persistent_keepalive": 25,
                },
                "meta": {"topology": "hub-spoke", "config_version": 2},
            },
        )
        monkeypatch.setattr("peer_register.config_gen._sync_wg", lambda: None)

        version = apply_config("peer-a")
        conf = _read_conf()
        st = load_state()

        assert version == 2
        assert "Address = 10.20.30.2/32" in conf
        assert "# HUB (bootstrap)" in conf
        assert "AllowedIPs = 10.20.30.0/24" in conf
        assert "Directo:" not in conf
        assert "Relay-via-HUB" not in conf
        assert st["topology"] == "hub-spoke"
        assert st["mesh_peers_hash"] == ""

    def test_apply_config_mesh(self, monkeypatch):
        _reset_peer_runtime()
        monkeypatch.setattr(
            "peer_register.config_gen._fetch_config",
            lambda peer_id: {
                "interface": {"address": "10.20.30.2/32", "mtu": 1420},
                "peer": {
                    "public_key": "hub-pub-key-xxxxxxxxxxxxxxxxxxxx",
                    "endpoint": "198.51.100.1:51820",
                    "allowed_ips": "10.20.30.0/24",
                    "persistent_keepalive": 25,
                },
                "meta": {"topology": "mesh", "config_version": 3, "mesh_peers_hash": "mesh-hash-1"},
                "mesh_peers": [
                    {
                        "peer_id": "peer-b",
                        "public_key": "mesh-peer-b-pubkey",
                        "endpoint": "198.51.100.11:51820",
                        "tunnel_ip": "10.20.30.3",
                        "alive": True,
                    }
                ],
            },
        )
        monkeypatch.setattr("peer_register.config_gen._sync_wg", lambda: None)

        version = apply_config("peer-a")
        conf = _read_conf()
        st = load_state()

        assert version == 3
        assert "# HUB (bootstrap)" in conf
        assert "# Peer directo: peer-b" in conf
        assert "AllowedIPs = 10.20.30.3/32" in conf
        assert "Endpoint = 198.51.100.11:51820" in conf
        assert st["topology"] == "mesh"
        assert st["mesh_peers_hash"] == "mesh-hash-1"
        assert st["hub_mesh_direct_candidates"] == []

    def test_apply_config_hub_mesh(self, monkeypatch):
        _reset_peer_runtime()
        monkeypatch.setattr(
            "peer_register.config_gen._fetch_config",
            lambda peer_id: {
                "interface": {"address": "10.20.30.2/32", "mtu": 1420},
                "peer": {
                    "public_key": "hub-pub-key-xxxxxxxxxxxxxxxxxxxx",
                    "endpoint": "198.51.100.1:51820",
                    "allowed_ips": "10.20.30.0/24",
                    "persistent_keepalive": 25,
                },
                "meta": {"topology": "hub-mesh", "config_version": 4, "hub_mesh_peers_hash": "hub-mesh-hash-1"},
                "hub_mesh_direct_peers": [
                    {
                        "peer_id": "peer-b",
                        "public_key": "mesh-peer-b-pubkey",
                        "endpoint": "198.51.100.11:51820",
                        "tunnel_ip": "10.20.30.3",
                    }
                ],
                "hub_mesh_relay_peers": [
                    {
                        "peer_id": "peer-c",
                        "public_key": "mesh-peer-c-pubkey",
                        "endpoint": "198.51.100.12:51820",
                        "tunnel_ip": "10.20.30.4",
                        "nat_type": "symmetric",
                    }
                ],
            },
        )
        monkeypatch.setattr("peer_register.config_gen._sync_wg", lambda: None)

        version = apply_config("peer-a")
        conf = _read_conf()
        st = load_state()

        assert version == 4
        assert "# HUB (relay de fallback)" in conf
        assert "# Directo: peer-b" in conf
        assert "AllowedIPs = 10.20.30.3/32" in conf
        assert "# Relay-via-HUB: peer-c (nat=symmetric, sin bloque directo)" in conf
        assert st["topology"] == "hub-mesh"
        assert st["mesh_peers_hash"] == "hub-mesh-hash-1"
        assert st["hub_mesh_direct_candidates"][0]["peer_id"] == "peer-b"
