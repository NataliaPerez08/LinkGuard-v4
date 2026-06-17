import os
import pytest

from peer_register import config
from peer_register.state import load_state, save_state


class TestState:
    def test_load_empty_when_missing(self, monkeypatch):
        monkeypatch.setattr(config, "STATE_PATH", "/nonexistent-dir/state.json")
        st = load_state()
        assert st == {}

    def test_save_and_load_roundtrip(self, tmp_path, monkeypatch):
        state_file = str(tmp_path / "state.json")
        monkeypatch.setattr(config, "STATE_PATH", state_file)
        monkeypatch.setattr(config, "WG_DIR", str(tmp_path))
        st = {"peer_id": "p1", "version": 2}
        save_state(st)
        loaded = load_state()
        assert loaded["peer_id"] == "p1"
        assert loaded["version"] == 2

    def test_save_state_restricted_perms(self, tmp_path, monkeypatch):
        state_file = str(tmp_path / "state.json")
        monkeypatch.setattr(config, "STATE_PATH", state_file)
        monkeypatch.setattr(config, "WG_DIR", str(tmp_path))
        save_state({"a": 1})
        mode = os.stat(state_file).st_mode & 0o777
        assert mode == 0o600

    def test_load_corrupt_json(self, tmp_path, monkeypatch):
        state_file = str(tmp_path / "state.json")
        monkeypatch.setattr(config, "STATE_PATH", state_file)
        monkeypatch.setattr(config, "WG_DIR", str(tmp_path))
        with open(state_file, "w") as f:
            f.write("{corrupt")
        st = load_state()
        assert st == {}
