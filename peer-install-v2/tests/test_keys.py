import os
import pytest
from unittest.mock import patch

from peer_register import config
from peer_register.keys import gen_keys_if_needed, rotate_keys, load_public_key, load_private_key


class TestKeys:
    def test_gen_keys_skips_if_exist(self, tmp_path, monkeypatch):
        priv_path = tmp_path / "wg0.key"
        pub_path = tmp_path / "wg0.pub"
        priv_path.write_text("existing-priv\n")
        pub_path.write_text("existing-pub\n")
        monkeypatch.setattr(config, "WG_PRIV_KEY_PATH", str(priv_path))
        monkeypatch.setattr(config, "WG_PUB_KEY_PATH", str(pub_path))
        monkeypatch.setattr(config, "WG_DIR", str(tmp_path))
        with patch("subprocess.check_output") as mock_co:
            gen_keys_if_needed()
            mock_co.assert_not_called()

    def test_gen_keys_creates_missing(self, tmp_path, monkeypatch):
        priv_path = tmp_path / "wg0.key"
        pub_path = tmp_path / "wg0.pub"
        monkeypatch.setattr(config, "WG_PRIV_KEY_PATH", str(priv_path))
        monkeypatch.setattr(config, "WG_PUB_KEY_PATH", str(pub_path))
        monkeypatch.setattr(config, "WG_DIR", str(tmp_path))
        with patch("subprocess.check_output") as mock_co:
            mock_co.side_effect = ["gen-priv-key-xxx\n", "gen-pub-key-yyy\n"]
            gen_keys_if_needed()
            assert mock_co.call_count == 2
        assert priv_path.is_file()
        assert priv_path.read_text().strip() == "gen-priv-key-xxx"

    def test_rotate_keys(self, tmp_path, monkeypatch):
        priv_path = tmp_path / "wg0.key"
        pub_path = tmp_path / "wg0.pub"
        monkeypatch.setattr(config, "WG_PRIV_KEY_PATH", str(priv_path))
        monkeypatch.setattr(config, "WG_PUB_KEY_PATH", str(pub_path))
        monkeypatch.setattr(config, "WG_DIR", str(tmp_path))
        with patch("subprocess.check_output") as mock_co:
            mock_co.side_effect = ["new-priv-xxx\n", "new-pub-yyy\n"]
            priv, pub = rotate_keys()
            assert priv == "new-priv-xxx"
            assert pub == "new-pub-yyy"

    def test_load_public_key(self, tmp_path, monkeypatch):
        pub_path = tmp_path / "wg0.pub"
        pub_path.write_text("test-pub-key\n")
        monkeypatch.setattr(config, "WG_PUB_KEY_PATH", str(pub_path))
        assert load_public_key() == "test-pub-key"

    def test_load_private_key(self, tmp_path, monkeypatch):
        priv_path = tmp_path / "wg0.key"
        priv_path.write_text("test-priv-key\n")
        monkeypatch.setattr(config, "WG_PRIV_KEY_PATH", str(priv_path))
        assert load_private_key() == "test-priv-key"
