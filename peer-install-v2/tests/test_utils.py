import os
import subprocess
import pytest
import tempfile

from peer_register import config
from peer_register.utils import ensure_dir, write_file, read_file, run, log


class TestFileOps:
    def test_ensure_dir_creates(self):
        path = tempfile.mktemp()
        ensure_dir(path)
        assert os.path.isdir(path)
        os.rmdir(path)

    def test_write_and_read_file(self):
        path = tempfile.mktemp()
        content = "line1\nline2\n"
        write_file(path, content)
        assert os.path.isfile(path)
        assert read_file(path) == "line1\nline2"

    def test_read_file_strips(self):
        path = tempfile.mktemp()
        with open(path, "w") as f:
            f.write("  hello world  \n")
        assert read_file(path) == "hello world"

    def test_write_file_sets_mode(self):
        path = tempfile.mktemp()
        write_file(path, "data", 0o600)
        st = os.stat(path)
        assert st.st_mode & 0o777 == 0o600


class TestRun:
    def test_run_capture_ok(self):
        out = run(["echo", "hello"], capture=True)
        assert "hello" in out

    def test_run_capture_fail(self):
        with pytest.raises(RuntimeError):
            run(["/bin/false"], capture=True)

    def test_run_no_capture(self):
        r = run(["echo", "ok"], capture=False)
        assert r == ""


class TestLog:
    def test_log_output(self, capsys):
        log("test message")
        captured = capsys.readouterr()
        assert "test message" in captured.out
