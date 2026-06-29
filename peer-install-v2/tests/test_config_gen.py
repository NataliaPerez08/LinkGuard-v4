import pytest
from peer_register.config_gen import (
    _build_interface_block,
    _build_hub_block,
    _build_mesh_blocks,
    _build_hub_mesh_blocks,
    _save_state_metadata,
    _sync_wg,
    _fetch_config,
    apply_config,
)
from unittest.mock import patch, MagicMock


class TestBuildInterfaceBlock:
    def test_basic_interface(self):
        d = {"interface": {"address": "10.20.30.2/24", "mtu": 1420}, "peer": {}}
        conf = _build_interface_block(d)
        assert "[Interface]" in conf
        assert "Address = 10.20.30.2/24" in conf
        assert "MTU = 1420" in conf
        assert "PrivateKey" in conf

    def test_custom_mtu(self):
        d = {"interface": {"address": "10.20.30.2/24", "mtu": 1500}, "peer": {}}
        conf = _build_interface_block(d)
        assert "MTU = 1500" in conf


class TestBuildHubBlock:
    def test_hub_block_hub_spoke(self):
        d = {
            "peer": {
                "public_key": "hub-pub-key-xxxxxxxxxxxxxxxxxxxx",
                "endpoint": "10.0.0.1:51820",
                "allowed_ips": "0.0.0.0/0",
                "persistent_keepalive": 25,
            },
            "meta": {"topology": "hub-spoke"},
        }
        conf = _build_hub_block(d)
        assert "bootstrap" in conf
        assert "hub-pub-key" in conf
        assert "0.0.0.0/0" in conf
        assert "25" in conf

    def test_hub_block_hub_mesh(self):
        d = {
            "peer": {
                "public_key": "hub-pub-key-xxxxxxxxxxxxxxxxxxxx",
                "endpoint": "10.0.0.1:51820",
                "allowed_ips": "10.20.30.0/24",
                "persistent_keepalive": 25,
            },
            "meta": {"topology": "hub-mesh"},
        }
        conf = _build_hub_block(d)
        assert "relay de fallback" in conf


class TestBuildMeshBlocks:
    def test_empty_mesh(self):
        d = {"peer": {}, "mesh_peers": []}
        conf = _build_mesh_blocks(d)
        assert conf == ""

    def test_with_peers(self):
        d = {
            "peer": {"persistent_keepalive": 25},
            "mesh_peers": [
                {"peer_id": "p1", "public_key": "pk1", "endpoint": "10.0.0.2:51820", "tunnel_ip": "10.20.30.2", "alive": True},
            ],
        }
        conf = _build_mesh_blocks(d)
        assert "p1" in conf
        assert "pk1" in conf
        assert "10.20.30.2/32" in conf
        assert "Endpoint" in conf

    def test_mesh_peer_not_alive_still_includes_endpoint(self):
        # El Endpoint se incluye siempre que exista, independientemente de alive
        # (fix intencional: que WireGuard conozca la direccion para reconectar)
        d = {
            "peer": {"persistent_keepalive": 25},
            "mesh_peers": [
                {"peer_id": "p2", "public_key": "pk2", "endpoint": "10.0.0.3:51820", "tunnel_ip": "10.20.30.3", "alive": False},
            ],
        }
        conf = _build_mesh_blocks(d)
        assert "p2" in conf
        assert "Endpoint = 10.0.0.3:51820" in conf
        assert "alive=False" in conf

    def test_mesh_peer_no_endpoint_omitted(self):
        # Solo se omite Endpoint cuando mp_ep es None/vacio
        d = {
            "peer": {"persistent_keepalive": 25},
            "mesh_peers": [
                {"peer_id": "p3", "public_key": "pk3", "endpoint": None, "tunnel_ip": "10.20.30.4", "alive": False},
            ],
        }
        conf = _build_mesh_blocks(d)
        assert "p3" in conf
        assert "Endpoint" not in conf


class TestBuildHubMeshBlocks:
    def test_direct_and_relay(self):
        d = {
            "peer": {"persistent_keepalive": 25},
            "hub_mesh_direct_peers": [
                {"peer_id": "d1", "public_key": "pk-d1", "endpoint": "10.0.0.4:51820", "tunnel_ip": "10.20.30.4"},
            ],
            "hub_mesh_relay_peers": [
                {"peer_id": "r1", "nat_type": "symmetric"},
            ],
        }
        conf = _build_hub_mesh_blocks(d)
        assert "d1" in conf
        assert "pk-d1" in conf
        assert "10.20.30.4/32" in conf
        assert "r1" in conf
        assert "symmetric" in conf
        assert "Relay-via-HUB" in conf
