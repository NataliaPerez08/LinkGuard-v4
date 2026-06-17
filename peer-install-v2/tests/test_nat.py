import os
import pytest
from unittest.mock import patch, MagicMock

from peer_register.nat import detect_nat_type


class TestDetectNat:
    def test_no_public_ip_symmetric(self, monkeypatch):
        monkeypatch.delenv("PUBLIC_IP", raising=False)
        assert detect_nat_type() == "symmetric"

    def test_public_ip_equal_local_none(self, monkeypatch):
        monkeypatch.setenv("PUBLIC_IP", "192.0.2.1")
        monkeypatch.setenv("WG_LISTEN_PORT", "51820")
        with patch("peer_register.nat._get_local_ip") as mock_ip:
            mock_ip.return_value = "192.0.2.1"
            assert detect_nat_type() == "none"

    def test_no_listen_port_symmetric(self, monkeypatch):
        monkeypatch.setenv("PUBLIC_IP", "203.0.113.5")
        monkeypatch.setenv("WG_LISTEN_PORT", "0")
        with patch("peer_register.nat._get_local_ip") as mock_ip:
            mock_ip.return_value = "10.0.0.5"
            assert detect_nat_type() == "symmetric"

    def test_full_cone(self, monkeypatch):
        monkeypatch.setenv("PUBLIC_IP", "203.0.113.5")
        monkeypatch.setenv("WG_LISTEN_PORT", "51820")
        with (
            patch("peer_register.nat._get_local_ip") as mock_ip,
            patch("peer_register.nat.socket") as mock_socket,
        ):
            mock_ip.return_value = "10.0.0.5"
            mock_s1 = MagicMock()
            mock_s2 = MagicMock()
            mock_s1.getsockname.return_value = ("0.0.0.0", 51820)
            mock_s2.getsockname.return_value = ("0.0.0.0", 51820)
            mock_socket.socket.side_effect = [mock_s1, mock_s2]
            assert detect_nat_type() == "full-cone"

    def test_full_cone_not_matching_symmetric(self, monkeypatch):
        monkeypatch.setenv("PUBLIC_IP", "203.0.113.5")
        monkeypatch.setenv("WG_LISTEN_PORT", "51820")
        with (
            patch("peer_register.nat._get_local_ip") as mock_ip,
            patch("peer_register.nat.socket") as mock_socket,
        ):
            mock_ip.return_value = "10.0.0.5"
            mock_s1 = MagicMock()
            mock_s2 = MagicMock()
            mock_s1.getsockname.return_value = ("0.0.0.0", 51820)
            mock_s2.getsockname.return_value = ("0.0.0.0", 51821)
            mock_socket.socket.side_effect = [mock_s1, mock_s2]
            assert detect_nat_type() == "symmetric"
