import pytest
from unittest.mock import patch, MagicMock

from peer_register.probe import probe_direct_peers


class RPCCollector:
    def __init__(self):
        self.reported = []

    def __getattr__(self, name):
        if name == "peer.report_reachability":
            def report(*a, **kw):
                self.reported.append(a)
            return report
        def stub(*a, **kw):
            return {}
        return stub


class TestProbe:
    def test_skip_if_not_hub_mesh(self):
        st = {"topology": "mesh"}
        with patch("peer_register.probe.subprocess") as mock_sp:
            probe_direct_peers("p1", st)
            mock_sp.check_output.assert_not_called()

    def test_skip_if_no_candidates(self):
        st = {"topology": "hub-mesh", "hub_mesh_direct_candidates": []}
        with patch("peer_register.probe.subprocess") as mock_sp:
            probe_direct_peers("p1", st)
            mock_sp.check_output.assert_not_called()

    def test_no_change_no_report(self):
        st = {
            "topology": "hub-mesh",
            "hub_mesh_direct_candidates": [
                {"public_key": "pk1", "peer_id": "p1"}
            ],
            "direct_handshake_map": {"pk1": True},
            "jwt": "valid-jwt",
            "jwt_expires_at": 9999999999,
        }
        rpc = RPCCollector()
        with (
            patch("peer_register.probe.subprocess.check_output") as mock_co,
            patch("peer_register.probe.rpc", return_value=rpc),
        ):
            now = 1000
            mock_co.return_value = f"pk1\t{now - 30}\n"
            with patch("peer_register.probe.time.time") as mock_time:
                mock_time.return_value = float(now)
                probe_direct_peers("test-peer", st)
                assert len(rpc.reported) == 0

    def test_reports_alive_change(self):
        st = {
            "topology": "hub-mesh",
            "hub_mesh_direct_candidates": [
                {"public_key": "pk1", "peer_id": "p1"}
            ],
            "direct_handshake_map": {"pk1": False},
            "jwt": "valid-jwt",
            "jwt_expires_at": 9999999999,
        }
        rpc = RPCCollector()
        with (
            patch("peer_register.probe.subprocess.check_output") as mock_co,
            patch("peer_register.probe.rpc", return_value=rpc),
        ):
            now = 1000
            mock_co.return_value = f"pk1\t{now - 10}\n"
            with patch("peer_register.probe.time.time") as mock_time:
                mock_time.return_value = float(now)
                probe_direct_peers("test-peer", st)
                assert len(rpc.reported) == 1
                args = rpc.reported[0]
                assert args[0] == "test-peer"
                assert args[1] == "p1"
                assert args[2] is True
