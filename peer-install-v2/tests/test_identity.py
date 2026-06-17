import os
import socket
import pytest
from unittest.mock import patch

from peer_register.identity import peer_id_default, owner_default, _get_local_ip, peer_endpoint_guess


class TestPeerId:
    def test_peer_id_from_env(self):
        pid = peer_id_default()
        assert pid == "test-peer"

    def test_peer_id_fallback_hostname(self, monkeypatch):
        monkeypatch.delenv("PEER_ID", raising=False)
        pid = peer_id_default()
        assert pid == socket.gethostname()


class TestOwner:
    def test_owner_from_env(self):
        assert owner_default() == "test-user"

    def test_owner_fallback(self, monkeypatch):
        monkeypatch.delenv("PEER_OWNER", raising=False)
        monkeypatch.delenv("USER_ID", raising=False)
        assert owner_default() == "default"


class TestLocalIP:
    @patch("peer_register.identity.socket.socket")
    def test_get_local_ip_ok(self, mock_sock):
        mock_instance = mock_sock.return_value.__enter__.return_value
        mock_instance.getsockname.return_value = ("10.0.0.5", 12345)
        ip = _get_local_ip()
        assert ip == "10.0.0.5"

    @patch("peer_register.identity.socket.socket")
    def test_get_local_ip_fallback_hostname(self, mock_sock):
        mock_instance = mock_sock.return_value.__enter__.return_value
        mock_instance.connect.side_effect = OSError()
        with patch("peer_register.identity.socket.gethostbyname") as mock_ghbn:
            mock_ghbn.return_value = "127.0.0.1"
            ip = _get_local_ip()
            assert ip == "127.0.0.1"


class TestEndpointGuess:
    def test_endpoint_from_env(self, monkeypatch):
        monkeypatch.setenv("PUBLIC_IP", "203.0.113.5")
        monkeypatch.setenv("WG_LISTEN_PORT", "51820")
        ep = peer_endpoint_guess()
        assert ep == "203.0.113.5:51820"

    def test_endpoint_local_ip(self, monkeypatch):
        monkeypatch.delenv("PUBLIC_IP", raising=False)
        with patch("peer_register.identity._get_local_ip") as mock_ip:
            mock_ip.return_value = "192.168.1.10"
            with patch("subprocess.check_output") as mock_co:
                mock_co.return_value = "51820\n"
                ep = peer_endpoint_guess()
                assert ep == "192.168.1.10:51820"
