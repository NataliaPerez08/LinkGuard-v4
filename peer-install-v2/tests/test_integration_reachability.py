"""
Tests de integración: escenarios de alcanzabilidad en redes hub-mesh.
Prueba el pipeline completo: clasificación del orquestador → generación de
config WireGuard → sondeo de handshakes y reporte de reachability.

Escenarios:
  1. Todos los peers son alcanzables (sin NAT, IP pública)
  2. Un peer detrás de NAT simétrico (orquestador como relay)
  3. Solo el orquestador es alcanzable (todos los peers vía relay)
"""

import json
import time
import os
import sys
from unittest.mock import patch, MagicMock

import pytest

# Necesitamos ambos paquetes en sys.path
_BASE = os.path.dirname(os.path.abspath(__file__))
_PEER_PKG = os.path.dirname(_BASE)                 # peer-install-v2/
_ORCH_PKG = os.path.join(_BASE, "../../orchestrator-install-v2")  # orchestrator-install-v2/
for _p in (_PEER_PKG, _ORCH_PKG):
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _set_orch_env(monkeypatch):
    """Configura variables de entorno necesarias para el orquestador."""
    monkeypatch.setenv("ADMIN_TOKEN", "test-admin-token")
    monkeypatch.setenv("HUB_AGENT_TOKEN", "test-hub-token")
    monkeypatch.setenv("HUB_ENDPOINT", "10.0.0.1:51820")
    monkeypatch.setenv("ORCH_PORT", "19999")
    monkeypatch.setenv("AUTO_APPROVE_ENABLED", "0")
    monkeypatch.setenv("BACKUP_ENABLED", "0")
    monkeypatch.setenv("EVENTS_LOG_PATH", "/dev/null")
    monkeypatch.setenv("JWT_TTL_DEFAULT", "3600")


def _set_peer_env(monkeypatch):
    """Configura variables de entorno necesarias para el peer."""
    monkeypatch.setenv("ORCH_URL", "http://127.0.0.1:17999/RPC2")
    monkeypatch.setenv("ORCH_TOKEN", "test-orch-token")
    monkeypatch.setenv("PUBLIC_IP", "192.0.2.1")
    monkeypatch.setenv("WG_LISTEN_PORT", "51820")
    monkeypatch.setenv("PEER_ID", "test-peer")
    monkeypatch.setenv("PEER_OWNER", "test-user")
    monkeypatch.setenv("WG_HEARTBEAT_INTERVAL", "5")
    monkeypatch.setenv("WG_KEEPALIVE", "10")
    monkeypatch.setenv("WG_JWT_TTL", "3600")
    monkeypatch.setenv("HUB_MESH_MODE", "hub-mesh")


def _build_orch_state(peers_config: dict, relay_cidr: str = None):
    """
    Construye el STATE del orquestador in-memory.
    peers_config: {peer_id: {pub, nat_type, endpoint, tunnel_ip}}
    """
    from orchestrator.state import STATE, DEFAULT_STATE
    STATE.clear()
    STATE.update(json.loads(json.dumps(DEFAULT_STATE)))

    now = int(time.time())
    STATE["peers"] = {}
    assigned = {}
    for pid, pc in peers_config.items():
        STATE["peers"][pid] = {
            "public_key": pc["pub"],
            "ip": pc["tunnel_ip"],
            "nat_type": pc.get("nat_type", "none"),
            "endpoint": pc.get("endpoint"),
            "last_heartbeat": now - 10,
            "networks": ["hub-net"],
            "enabled": True,
            "created_ts": now - 3600,
            "keepalive": 25,
            "metadata": {},
            "relay_mode": "auto",
        }
        assigned[pid] = pc["tunnel_ip"]

    n = {
        "cidr": "10.99.0.0/24",
        "topology": "hub-mesh",
        "description": "red hub-mesh de prueba",
        "user_id": "admin",
        "tag": "mesh-test",
        "created_ts": now - 3600,
        "alloc": {"reserved": [], "assigned": assigned},
    }
    if relay_cidr:
        n["hub_mesh_relay_fallback_cidr"] = relay_cidr
    STATE["networks"] = {"hub-net": n}
    return STATE


def _build_peer_config_response(classify_result: dict, hub_info: dict) -> dict:
    """Construye el dict que devolveria config.get_peer_config."""
    cfg = {
        "interface": {"address": "10.99.0.1/24", "mtu": 1420},
        "peer": {
            "public_key": hub_info["public_key"],
            "endpoint": hub_info["endpoint"],
            "allowed_ips": hub_info.get("allowed_ips", "10.99.0.0/24"),
            "persistent_keepalive": 25,
        },
        "meta": {
            "topology": "hub-mesh",
            "config_version": 5,
            "hub_mesh_peers_hash": "abc123def",
        },
        "hub_mesh_direct_peers": [
            {
                "peer_id": d["peer_id"],
                "public_key": d["public_key"],
                "endpoint": d["endpoint"],
                "tunnel_ip": d["tunnel_ip"],
            }
            for d in classify_result["direct"]
        ],
        "hub_mesh_relay_peers": [
            {
                "peer_id": r["peer_id"],
                "public_key": r["public_key"],
                "endpoint": r.get("endpoint"),
                "tunnel_ip": r["tunnel_ip"],
                "nat_type": r["nat_type"],
            }
            for r in classify_result["relay_only"]
        ],
    }
    return cfg


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def hub_info():
    return {
        "public_key": "hub-pub-key-xxxxxxxxxxxxxxxxxxxx",
        "endpoint": "10.0.0.1:51820",
        "allowed_ips": "10.99.0.0/24",
    }


# ===========================================================================
# ESCENARIO 1 — Todos los peers son alcanzables
# ===========================================================================

class TestEscenario1TodosReachables:
    """Dos peers con IP pública, sin NAT, comunicación directa P2P."""

    @pytest.fixture
    def peers(self):
        return {
            "peer-A": {
                "pub": "pk-A-aaaaaaaaaaaaaaaaaaaaaaaa",
                "nat_type": "none",
                "endpoint": "203.0.113.2:51820",
                "tunnel_ip": "10.99.0.2",
            },
            "peer-B": {
                "pub": "pk-B-bbbbbbbbbbbbbbbbbbbbbbbb",
                "nat_type": "full-cone",
                "endpoint": "203.0.113.3:51820",
                "tunnel_ip": "10.99.0.3",
            },
        }

    def test_orquestador_clasifica_todos_directos(self, monkeypatch, peers):
        """El orquestador clasifica ambos peers como directos."""
        _set_orch_env(monkeypatch)
        _build_orch_state(peers)

        from orchestrator.endpoints_config import _classify_peers_for_hub_mesh
        r = _classify_peers_for_hub_mesh("peer-A", "hub-net")

        direct_ids = sorted(d["peer_id"] for d in r["direct"])
        relay_ids = sorted(d["peer_id"] for d in r["relay_only"])

        assert direct_ids == ["peer-B"], f"Esperaba directo [peer-B], obtuve {direct_ids}"
        assert relay_ids == [], f"Esperaba relay vacio, obtuve {relay_ids}"

    def test_wireguard_genera_bloques_directos(self, monkeypatch, peers, hub_info):
        """La config WireGuard tiene [Peer] con Endpoint para cada peer directo."""
        _set_orch_env(monkeypatch)
        _set_peer_env(monkeypatch)
        _build_orch_state(peers)

        from orchestrator.endpoints_config import _classify_peers_for_hub_mesh
        r = _classify_peers_for_hub_mesh("peer-A", "hub-net")
        cfg = _build_peer_config_response(r, hub_info)

        from peer_register.config_gen import _build_hub_mesh_blocks
        # _build_hub_mesh_blocks solo genera los bloques de peers,
        # el bloque HUB lo genera _build_hub_block por separado
        conf = _build_hub_mesh_blocks(cfg)

        assert "Directo: peer-B" in conf
        assert "pk-B" in conf
        assert "203.0.113.3:51820" in conf
        assert "10.99.0.3/32" in conf
        assert "Relay-via-HUB" not in conf

    def test_probe_reporta_reachability_directa(self, monkeypatch, peers):
        """El probe detecta handshake y reporta alive=True al orquestador."""
        _set_peer_env(monkeypatch)
        from peer_register.probe import probe_direct_peers

        st = {
            "topology": "hub-mesh",
            "hub_mesh_direct_candidates": [
                {"public_key": "pk-B", "peer_id": "peer-B"},
            ],
            "direct_handshake_map": {"pk-B": False},
            "jwt": "test-jwt",
            "jwt_expires_at": 9999999999,
        }

        collector = RPCCollector()
        now = int(time.time())
        with (
            patch("peer_register.probe.subprocess.check_output") as mock_co,
            patch("peer_register.probe.rpc", return_value=collector),
            patch("peer_register.probe.time.time") as mock_time,
        ):
            # Handshake reciente (< 180s) => alive=True
            mock_co.return_value = f"pk-B\t{now - 10}\n"
            mock_time.return_value = float(now)
            probe_direct_peers("peer-A", st)

            assert len(collector.reported) == 1, (
                f"Esperaba 1 reporte, obtuve {len(collector.reported)}"
            )
            # report_reachability(peer_id, target_id, alive, token) -> 4 args
            peer_id, target_id, alive, _ = collector.reported[0]
            assert peer_id == "peer-A"
            assert target_id == "peer-B"
            assert alive is True

        # direct_handshake_map debe actualizarse
        assert st["direct_handshake_map"]["pk-B"] is True


# ===========================================================================
# ESCENARIO 2 — Un peer detrás de NAT simétrico
# ===========================================================================

class TestEscenario2UnPeerDetrasDeNAT:
    """Un peer es directo, el otro tiene NAT simétrico (solo relay)."""

    @pytest.fixture
    def peers(self):
        return {
            "peer-A": {
                "pub": "pk-A-aaaaaaaaaaaaaaaaaaaaaaaa",
                "nat_type": "none",
                "endpoint": "203.0.113.2:51820",
                "tunnel_ip": "10.99.0.2",
            },
            "peer-B": {
                "pub": "pk-B-bbbbbbbbbbbbbbbbbbbbbbbb",
                "nat_type": "symmetric",
                "endpoint": "203.0.113.3:51820",
                "tunnel_ip": "10.99.0.3",
            },
        }

    def test_orquestador_clasifica_mixto(self, monkeypatch, peers):
        """peer-A es directo, peer-B es relay-only (symmetric)."""
        _set_orch_env(monkeypatch)
        _build_orch_state(peers)

        from orchestrator.endpoints_config import _classify_peers_for_hub_mesh
        r = _classify_peers_for_hub_mesh("peer-A", "hub-net")

        direct_ids = sorted(d["peer_id"] for d in r["direct"])
        relay_ids = sorted(d["peer_id"] for d in r["relay_only"])

        assert direct_ids == [], (
            f"peer-B es symmetric, no deberia ser directo. Obtuve direct_ids={direct_ids}"
        )
        assert relay_ids == ["peer-B"], f"Esperaba relay [peer-B], obtuve {relay_ids}"

    def test_wireguard_genera_directo_y_relay(self, monkeypatch, peers, hub_info):
        """peer-A tiene [Peer], peer-B solo comentario Relay-via-HUB."""
        _set_orch_env(monkeypatch)
        _set_peer_env(monkeypatch)
        _build_orch_state(peers)

        from orchestrator.endpoints_config import _classify_peers_for_hub_mesh
        r = _classify_peers_for_hub_mesh("peer-A", "hub-net")
        cfg = _build_peer_config_response(r, hub_info)

        from peer_register.config_gen import _build_hub_mesh_blocks
        conf = _build_hub_mesh_blocks(cfg)

        assert "Relay-via-HUB: peer-B" in conf
        assert "symmetric" in conf
        # peer-B NO debe tener un bloque [Peer] directo
        directo_peer_b = "[Peer]\nPublicKey = pk-B" in conf
        assert not directo_peer_b, (
            "peer-B no debe tener bloque [Peer] directo porque es relay-only"
        )

    def test_probe_no_reporta_para_relay(self, monkeypatch, peers):
        """El probe solo monitorea candidatos directos; peer-B no es candidato."""
        _set_peer_env(monkeypatch)
        from peer_register.probe import probe_direct_peers

        # solo peer-A es candidato directo
        st = {
            "topology": "hub-mesh",
            "hub_mesh_direct_candidates": [
                {"public_key": "pk-A", "peer_id": "peer-A"},
            ],
            "direct_handshake_map": {"pk-A": False},
            "jwt": "test-jwt",
            "jwt_expires_at": 9999999999,
        }

        collector = RPCCollector()
        now = int(time.time())
        with (
            patch("peer_register.probe.subprocess.check_output") as mock_co,
            patch("peer_register.probe.rpc", return_value=collector),
            patch("peer_register.probe.time.time") as mock_time,
        ):
            mock_co.return_value = f"pk-A\t{now - 10}\n"
            mock_time.return_value = float(now)
            probe_direct_peers("peer-B", st)

            assert len(collector.reported) == 1
            _, target_id, alive, _ = collector.reported[0]
            assert target_id == "peer-A"
            assert alive is True


# ===========================================================================
# ESCENARIO 3 — Solo el orquestador es alcanzable
# ===========================================================================

class TestEscenario3SoloOrquestadorReachable:
    """Todos los peers tienen NAT simétrico, toda comunicación via relay."""

    @pytest.fixture
    def peers(self):
        return {
            "peer-A": {
                "pub": "pk-A-aaaaaaaaaaaaaaaaaaaaaaaa",
                "nat_type": "symmetric",
                "endpoint": "203.0.113.2:51820",
                "tunnel_ip": "10.99.0.2",
            },
            "peer-B": {
                "pub": "pk-B-bbbbbbbbbbbbbbbbbbbbbbbb",
                "nat_type": "symmetric",
                "endpoint": "10.0.0.99:51820",
                "tunnel_ip": "10.99.0.3",
            },
        }

    def test_orquestador_clasifica_todos_relay(self, monkeypatch, peers):
        """Ambos peers se clasifican como relay-only."""
        _set_orch_env(monkeypatch)
        _build_orch_state(peers)

        from orchestrator.endpoints_config import _classify_peers_for_hub_mesh
        r = _classify_peers_for_hub_mesh("peer-A", "hub-net")

        direct_ids = sorted(d["peer_id"] for d in r["direct"])
        relay_ids = sorted(d["peer_id"] for d in r["relay_only"])

        assert direct_ids == [], (
            f"Todos son symmetric, direct_ids deberia estar vacio. Obtuve {direct_ids}"
        )
        assert relay_ids == ["peer-B"], f"Esperaba relay [peer-B], obtuve {relay_ids}"

    def test_wireguard_solo_relay_sin_bloques_directos(self, monkeypatch, peers, hub_info):
        """La config solo tiene comentarios Relay-via-HUB, sin bloques [Peer] directos."""
        _set_orch_env(monkeypatch)
        _set_peer_env(monkeypatch)
        _build_orch_state(peers)

        from orchestrator.endpoints_config import _classify_peers_for_hub_mesh
        r = _classify_peers_for_hub_mesh("peer-A", "hub-net")
        cfg = _build_peer_config_response(r, hub_info)

        from peer_register.config_gen import _build_hub_mesh_blocks
        conf = _build_hub_mesh_blocks(cfg)

        assert "Relay-via-HUB: peer-B" in conf
        assert "# Directo:" not in conf, (
            "No deberia haber ningun bloque 'Directo' cuando todos son relay"
        )

    def test_probe_sin_candidatos_no_ejecuta(self, monkeypatch):
        """Sin candidatos directos, probe no llama a wg show ni reporta."""
        _set_peer_env(monkeypatch)
        from peer_register.probe import probe_direct_peers

        st = {
            "topology": "hub-mesh",
            "hub_mesh_direct_candidates": [],
            "direct_handshake_map": {},
        }

        collector = RPCCollector()
        with (
            patch("peer_register.probe.subprocess") as mock_sp,
            patch("peer_register.probe.rpc", return_value=collector),
        ):
            probe_direct_peers("peer-A", st)
            mock_sp.check_output.assert_not_called()
            assert len(collector.reported) == 0


# ===========================================================================
# Escenarios adicionales: relay_mode forzado y reachability_map
# ===========================================================================

class TestEscenariosAdicionales:
    """Casos borde: force_relay, force_direct, reachability_map del solicitante."""

    def test_force_relay_override(self, monkeypatch):
        """Un peer con relay_mode='force_relay' nunca es directo, aunque tenga
        nat_type='none' y endpoint."""
        _set_orch_env(monkeypatch)
        _build_orch_state({
            "peer-A": {"pub": "pk-A", "nat_type": "none", "endpoint": "10.0.0.2:51820", "tunnel_ip": "10.99.0.2"},
            "peer-B": {"pub": "pk-B", "nat_type": "none", "endpoint": "10.0.0.3:51820", "tunnel_ip": "10.99.0.3"},
        })
        from orchestrator import state
        state.STATE["peers"]["peer-B"]["relay_mode"] = "force_relay"

        from orchestrator.endpoints_config import _classify_peers_for_hub_mesh
        r = _classify_peers_for_hub_mesh("peer-A", "hub-net")
        relay_ids = [d["peer_id"] for d in r["relay_only"]]
        assert "peer-B" in relay_ids, (
            "peer-B con force_relay deberia estar en relay_only aunque tenga nat_type=none"
        )

    def test_force_direct_override(self, monkeypatch):
        """Un peer con relay_mode='force_direct' es directo aunque el
        solicitante lo reporte como hub-relay. Nota: force_direct NO
        sobreescribe nat_type='symmetric', solo sobreescribe
        reachability_map."""
        _set_orch_env(monkeypatch)
        _build_orch_state({
            "peer-A": {"pub": "pk-A", "nat_type": "none", "endpoint": "10.0.0.2:51820", "tunnel_ip": "10.99.0.2"},
            "peer-B": {"pub": "pk-B", "nat_type": "none", "endpoint": "10.0.0.3:51820", "tunnel_ip": "10.99.0.3"},
        })
        from orchestrator import state
        state.STATE["peers"]["peer-B"]["relay_mode"] = "force_direct"
        # peer-A reporta que peer-B solo es alcanzable via relay
        state.STATE["peers"]["peer-A"]["reachability_map"] = {"peer-B": "hub-relay"}

        from orchestrator.endpoints_config import _classify_peers_for_hub_mesh
        r = _classify_peers_for_hub_mesh("peer-A", "hub-net")
        direct_ids = [d["peer_id"] for d in r["direct"]]
        assert "peer-B" in direct_ids, (
            "peer-B con force_direct deberia ser directo aunque peer-A "
            "lo reporte como hub-relay"
        )

    def test_reachability_map_hub_relay(self, monkeypatch):
        """Si el reachability_map del solicitante reporta un peer como
        'hub-relay', ese peer va a relay_only."""
        _set_orch_env(monkeypatch)
        _build_orch_state({
            "peer-A": {"pub": "pk-A", "nat_type": "none", "endpoint": "10.0.0.2:51820", "tunnel_ip": "10.99.0.2"},
            "peer-B": {"pub": "pk-B", "nat_type": "none", "endpoint": "10.0.0.3:51820", "tunnel_ip": "10.99.0.3"},
        })
        from orchestrator import state
        state.STATE["peers"]["peer-A"]["reachability_map"] = {"peer-B": "hub-relay"}

        from orchestrator.endpoints_config import _classify_peers_for_hub_mesh
        r = _classify_peers_for_hub_mesh("peer-A", "hub-net")
        direct_ids = [d["peer_id"] for d in r["direct"]]
        relay_ids = [d["peer_id"] for d in r["relay_only"]]
        assert "peer-B" not in direct_ids, (
            "peer-B reportado como hub-relay no deberia estar en direct"
        )
        assert "peer-B" in relay_ids, (
            "peer-B reportado como hub-relay deberia estar en relay_only"
        )


# ===========================================================================
# RPCCollector helper
# ===========================================================================

class RPCCollector:
    """Objeto que simula un cliente RPC y colecciona llamadas a
    peer.report_reachability para verificacion en tests."""
    def __init__(self):
        self.reported = []

    def __getattr__(self, name):
        if name == "peer.report_reachability":
            def report(*a, **kw):
                self.reported.append(a)
            return report

        def stub(*a, **kw):
            return {"jwt": "test-jwt-refreshed", "expires_at": 9999999999}
        return stub
