"""
Escenario mixto Arch + Alpine detrás de NAT simétrico.

Objetivo:
  - modelar dos VMs en Huawei Cloud con IP pública expuesta por NAT
  - modelar que no existe conectividad privada entre ambas VMs
  - verificar el comportamiento esperado en hub-spoke, mesh y hub-mesh

IPs públicas usadas en el escenario:
  - Arch Linux:   46.250.168.185:51820
  - Alpine Linux: 122.8.179.57:51820
"""

import importlib
import json
import os
import sys
import tempfile
import time
from unittest.mock import patch


import pytest


_BASE = os.path.dirname(os.path.abspath(__file__))
_PEER_PKG = os.path.dirname(_BASE)
_ORCH_PKG = os.path.join(_BASE, "../../orchestrator-install-v2")
for _p in (_PEER_PKG, _ORCH_PKG):
    if _p not in sys.path:
        sys.path.insert(0, _p)


ARCH_PUBLIC_ENDPOINT = "46.250.168.185:51820"
ALPINE_PUBLIC_ENDPOINT = "122.8.179.57:51820"
TUNNEL_CIDR = "10.77.0.0/24"


def _set_orch_env(monkeypatch):
    jwt_secret = tempfile.NamedTemporaryFile(mode="w", delete=False)
    jwt_secret.write("mixed-nat-topology-secret-xxxxxxxxxxxx")
    jwt_secret.close()

    state_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
    state_file.close()

    revoked_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
    revoked_file.close()

    monkeypatch.setenv("ADMIN_TOKEN", "test-admin-token")
    monkeypatch.setenv("HUB_AGENT_TOKEN", "test-hub-token")
    monkeypatch.setenv("HUB_ENDPOINT", "101.44.24.91:51820")
    monkeypatch.setenv("ORCH_PORT", "19999")
    monkeypatch.setenv("AUTO_APPROVE_ENABLED", "0")
    monkeypatch.setenv("BACKUP_ENABLED", "0")
    monkeypatch.setenv("EVENTS_LOG_PATH", "/dev/null")
    monkeypatch.setenv("JWT_TTL_DEFAULT", "3600")
    monkeypatch.setenv("JWT_SECRET_PATH", jwt_secret.name)
    monkeypatch.setenv("ORCH_STATE_PATH", state_file.name)
    monkeypatch.setenv("JWT_REVOKED_PATH", revoked_file.name)


def _set_peer_env(monkeypatch):
    monkeypatch.setenv("ORCH_URL", "http://101.44.24.91:8000/RPC2")
    monkeypatch.setenv("ORCH_TOKEN", "test-orch-token")
    monkeypatch.setenv("PUBLIC_IP", ARCH_PUBLIC_ENDPOINT.split(":", 1)[0])
    monkeypatch.setenv("WG_LISTEN_PORT", "51820")
    monkeypatch.setenv("PEER_ID", "arch-peer")
    monkeypatch.setenv("PEER_OWNER", "lab-user")
    monkeypatch.setenv("WG_HEARTBEAT_INTERVAL", "5")
    monkeypatch.setenv("WG_KEEPALIVE", "10")
    monkeypatch.setenv("WG_JWT_TTL", "3600")


def _issue_jwt(user_id: str, peer_id: str = "") -> str:
    auth = _reload_orch_config_auth()

    token, _ = auth._jwt_encode(
        {
            "user_id": user_id,
            "peer_id": peer_id,
            "scopes": ["peer:*", "network:*", "config:*", "orch:read"],
            "role": "user",
        },
        600,
    )
    return token


def _reload_orch_config_auth():
    import orchestrator.config as orch_config
    import orchestrator.auth as orch_auth

    importlib.reload(orch_config)
    importlib.reload(orch_auth)
    return orch_auth


def _reload_peer_modules():
    from peer_register import config as peer_config
    from peer_register import config_gen

    importlib.reload(peer_config)
    importlib.reload(config_gen)
    return peer_config, config_gen


def _build_dual_nat_state(topology: str):
    _reload_orch_config_auth()
    from orchestrator.state import STATE, DEFAULT_STATE

    STATE.clear()
    STATE.update(json.loads(json.dumps(DEFAULT_STATE)))

    now = int(time.time())
    STATE["users"] = {
        "lab-user": {
            "token": "u_lab_user",
            "disabled": False,
            "created_ts": now - 3600,
            "max_peers": 5,
            "max_networks": 5,
            "metadata": {"provider": "huawei-cloud"},
        }
    }
    STATE["peers"] = {
        "arch-peer": {
            "public_key": "A" * 44,
            "ip": "10.77.0.2",
            "user_id": "lab-user",
            "nat_type": "symmetric",
            "endpoint": ARCH_PUBLIC_ENDPOINT,
            "last_heartbeat": now - 10,
            "networks": ["huawei-nat-lab"],
            "enabled": True,
            "created_ts": now - 3600,
            "keepalive": 25,
            "metadata": {
                "owner": "lab-user",
                "os": "arch",
                "provider": "Huawei Cloud",
                "private_ip": "172.16.10.10",
                "private_network_reachable": False,
            },
            "relay_mode": "auto",
        },
        "alpine-peer": {
            "public_key": "B" * 44,
            "ip": "10.77.0.3",
            "user_id": "lab-user",
            "nat_type": "symmetric",
            "endpoint": ALPINE_PUBLIC_ENDPOINT,
            "last_heartbeat": now - 10,
            "networks": ["huawei-nat-lab"],
            "enabled": True,
            "created_ts": now - 3600,
            "keepalive": 25,
            "metadata": {
                "owner": "lab-user",
                "os": "alpine",
                "provider": "Huawei Cloud",
                "private_ip": "172.16.20.10",
                "private_network_reachable": False,
            },
            "relay_mode": "auto",
        },
    }
    STATE["networks"] = {
        "huawei-nat-lab": {
            "cidr": TUNNEL_CIDR,
            "topology": topology,
            "description": "Arch + Alpine detrás de NAT simétrico",
            "user_id": "lab-user",
            "tag": "huawei-lab",
            "created_ts": now - 3600,
            "hub_mesh_relay_fallback_cidr": TUNNEL_CIDR,
            "alloc": {
                "reserved": [],
                "assigned": {
                    "arch-peer": "10.77.0.2",
                    "alpine-peer": "10.77.0.3",
                },
            },
        }
    }
    return STATE


class TestMixedDistrosDualNATTopologies:
    @patch("orchestrator.hub_client._hub_call_with_retry")
    def test_hub_spoke_arch_and_alpine_relay_via_hub(self, mock_hub, monkeypatch):
        _set_orch_env(monkeypatch)
        _set_peer_env(monkeypatch)
        mock_hub.side_effect = lambda method, *args: "hub-public-key" if method == "hub.public_key" else True

        _build_dual_nat_state("hub-spoke")
        jwt_token = _issue_jwt("lab-user", "arch-peer")

        from orchestrator.endpoints_config import rpc_config_get_peer_config

        cfg = rpc_config_get_peer_config({"peer_id": "arch-peer", "token": jwt_token})

        assert cfg["meta"]["topology"] == "hub-spoke"
        assert cfg["peer"]["endpoint"] == "101.44.24.91:51820"
        assert cfg["peer"]["allowed_ips"] == TUNNEL_CIDR
        assert "mesh_peers" not in cfg
        assert "hub_mesh_direct_peers" not in cfg

    @patch("orchestrator.hub_client._hub_call_with_retry")
    def test_mesh_arch_and_alpine_generates_direct_peer_blocks_even_without_private_reachability(self, mock_hub, monkeypatch):
        _set_orch_env(monkeypatch)
        _set_peer_env(monkeypatch)
        mock_hub.side_effect = lambda method, *args: "hub-public-key" if method == "hub.public_key" else True

        _, config_gen = _reload_peer_modules()
        _build_dual_nat_state("mesh")
        jwt_token = _issue_jwt("lab-user", "arch-peer")

        from orchestrator.endpoints_config import rpc_config_get_peer_config

        cfg = rpc_config_get_peer_config({"peer_id": "arch-peer", "token": jwt_token})
        conf = config_gen._build_mesh_blocks(cfg)

        assert cfg["meta"]["topology"] == "mesh"
        assert len(cfg["mesh_peers"]) == 1
        assert cfg["mesh_peers"][0]["peer_id"] == "alpine-peer"
        assert cfg["mesh_peers"][0]["endpoint"] == ALPINE_PUBLIC_ENDPOINT
        assert cfg["mesh_peers"][0]["alive"] is True
        assert "private_network_reachable" not in conf
        assert "Peer directo: alpine-peer" in conf
        assert ALPINE_PUBLIC_ENDPOINT in conf
        assert "AllowedIPs = 10.77.0.3/32" in conf

    @patch("orchestrator.hub_client._hub_call_with_retry")
    def test_hub_mesh_arch_and_alpine_falls_back_to_relay_only(self, mock_hub, monkeypatch):
        _set_orch_env(monkeypatch)
        _set_peer_env(monkeypatch)
        mock_hub.side_effect = lambda method, *args: "hub-public-key" if method == "hub.public_key" else True

        _, config_gen = _reload_peer_modules()
        _build_dual_nat_state("hub-mesh")
        jwt_token = _issue_jwt("lab-user", "arch-peer")

        from orchestrator.endpoints_config import rpc_config_get_mesh_peers, rpc_config_get_peer_config

        cfg = rpc_config_get_peer_config({"peer_id": "arch-peer", "token": jwt_token})
        conf = config_gen._build_hub_mesh_blocks(cfg)
        classification = rpc_config_get_mesh_peers(
            {"peer_id": "arch-peer", "network_id": "huawei-nat-lab", "token": jwt_token}
        )

        assert cfg["meta"]["topology"] == "hub-mesh"
        assert cfg["peer"]["endpoint"] == "101.44.24.91:51820"
        assert cfg["peer"]["allowed_ips"] == TUNNEL_CIDR
        assert cfg["hub_mesh_direct_peers"] == []
        assert [p["peer_id"] for p in cfg["hub_mesh_relay_peers"]] == ["alpine-peer"]
        assert classification["direct"] == []
        assert [p["peer_id"] for p in classification["relay_only"]] == ["alpine-peer"]
        assert classification["relay_cidr"] == TUNNEL_CIDR
        assert "Relay-via-HUB: alpine-peer" in conf
        assert "symmetric" in conf
        assert "# Directo:" not in conf
