import json
import tempfile
import os


class TestCore:
    def test_now_ts(self):
        from orchestrator.state import now_ts
        import time
        now = now_ts()
        assert isinstance(now, int)
        assert abs(now - int(time.time())) < 2

    def test_ensure_dir_creates(self):
        from orchestrator.state import ensure_dir
        f = tempfile.mktemp() + "/subdir/file.json"
        ensure_dir(f)
        assert os.path.isdir(os.path.dirname(f))
        os.removedirs(os.path.dirname(f))

    def test_save_and_load_json(self):
        from orchestrator.state import save_json, load_json
        f = tempfile.mktemp()
        data = {"a": 1, "b": [2, 3]}
        save_json(f, data)
        loaded = load_json(f)
        assert loaded == data
        os.remove(f)

    def test_load_json_missing(self):
        from orchestrator.state import load_json
        assert load_json("/nonexistent/path.json") == {}

    def test_load_json_corrupt(self):
        from orchestrator.state import load_json
        f = tempfile.mktemp()
        with open(f, "w") as fh:
            fh.write("not-json")
        assert load_json(f) == {}
        os.remove(f)


class TestStateLifecycle:
    def test_load_state_creates_default(self):
        import orchestrator.state as st
        import os
        st.STATE.clear()
        with open(os.environ["ORCH_STATE_PATH"], "w") as f:
            f.write("")
        st.load_state()
        assert st.STATE.get("version") == 4
        assert st.STATE.get("users") == {}
        assert st.STATE.get("peers") == {}
        assert st.STATE.get("networks") == {}
        assert st.STATE.get("events") == []

    def test_persist_roundtrip(self, init_state):
        import orchestrator.state as st
        st.STATE["users"] = {"alice": {"token": "t1"}}
        st.persist()
        st.STATE.clear()
        st.load_state()
        assert st.STATE["users"]["alice"]["token"] == "t1"

    def test_bump_config_version(self):
        import orchestrator.state as st
        st.STATE.clear()
        st.load_state()
        v1 = st.STATE.get("config_version")
        v2 = st.bump_config_version_locked()
        assert v2 == v1 + 1


class TestEvents:
    def test_add_event(self, init_state):
        import orchestrator.state as st
        st.add_event("test_event", {"key": "val"})
        assert len(st.STATE["events"]) == 1
        ev = st.STATE["events"][0]
        assert ev["kind"] == "test_event"
        assert ev["detail"]["key"] == "val"

    def test_events_truncated(self, monkeypatch):
        monkeypatch.setenv("EVENTS_IN_STATE_MAX", "5")
        from importlib import reload
        import orchestrator.config as cfg
        reload(cfg)
        import orchestrator.state as st
        st.STATE.clear()
        st.load_state()
        for i in range(10):
            st.add_event("ev", {"i": i})
        assert len(st.STATE["events"]) == 5
        assert st.STATE["events"][0]["detail"]["i"] == 5


class TestBackup:
    def test_backup_disabled(self, monkeypatch):
        monkeypatch.setenv("BACKUP_ENABLED", "0")
        from importlib import reload
        import orchestrator.config as cfg
        reload(cfg)
        from orchestrator.state import _do_backup
        _do_backup()
