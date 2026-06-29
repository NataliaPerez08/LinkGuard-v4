"""Tests unitarios para hub-agent.py.

Mockea subprocess, shutil, os y open para aislar todas las funciones
del hub-agent de las dependencias del sistema (WireGuard, iptables, sysctl).
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile

import pytest
from unittest.mock import patch, MagicMock, mock_open

_HUB_AGENT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hub-agent.py")


def _load_ha():
    """Load hub-agent.py from file path into sys.modules['hub_agent'] and return it."""
    spec = importlib.util.spec_from_file_location("hub_agent", _HUB_AGENT_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["hub_agent"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def env_vars(monkeypatch):
    monkeypatch.setenv("HUB_AGENT_TOKEN", "test-hub-token-secure-00000000000")
    monkeypatch.setenv("HUB_MESH_MODE", "off")
    monkeypatch.setenv("HUB_WG_IFACE", "wg-HUB-test")
    monkeypatch.setenv("HUB_LISTEN_PORT", "51820")
    monkeypatch.setenv("HUB_AGENT_PORT", "9000")
    monkeypatch.setenv("HUB_TUNNEL_IP", "10.20.30.1/24")
    monkeypatch.setenv("HUB_TUNNEL_CIDR", "10.20.30.0/24")
    monkeypatch.setenv("HUB_ENABLE_NAT", "1")
    monkeypatch.setenv("HUB_NAT_OUT_IFACE", "eth0")


@pytest.fixture
def ha():
    """Import (or reload) hub-agent AFTER env is set."""
    with patch("hub_agent.subprocess") as mock_sp:
        with patch("hub_agent.shutil") as mock_shutil:
            mock_shutil.which.return_value = "/usr/bin/wg"
            mod = _load_ha()
            yield mod


@pytest.fixture
def ha_mocked(monkeypatch):
    """hub-agent module with all I/O mocked."""
    mod = _load_ha()
    monkeypatch.setattr(mod, "run", lambda cmd, check=True, capture=False: "ok")
    monkeypatch.setattr(mod, "subprocess", MagicMock())
    yield mod


class TestCheckDependencies:
    def test_all_found(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod.shutil, "which", lambda x: x)
        mod.check_dependencies()

    def test_missing(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod.shutil, "which", lambda x: None)
        monkeypatch.setattr(os.path, "isfile", lambda x: False)
        with pytest.raises(SystemExit, match="Dependencias faltantes"):
            mod.check_dependencies()


class TestValidateToken:
    def test_valid_token(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod, "HUB_AGENT_TOKEN", "valid-secure-token-xxx")
        mod.validate_token_at_startup()

    @pytest.mark.parametrize("bad", ["", "changeme", "password", "12345", "changeme-super-secret"])
    def test_insecure_token(self, monkeypatch, bad):
        mod = _load_ha()
        monkeypatch.setattr(mod, "HUB_AGENT_TOKEN", bad)
        with pytest.raises(SystemExit, match="inseguro|vacío"):
            mod.validate_token_at_startup()


class TestCheckToken:
    def test_valid(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod, "HUB_AGENT_TOKEN", "my-token")
        mod.check_token("my-token")

    def test_invalid(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod, "HUB_AGENT_TOKEN", "my-token")
        with pytest.raises(PermissionError, match="invalid token"):
            mod.check_token("wrong")


class TestFileOps:
    def test_ensure_dir(self, tmp_path):
        mod = _load_ha()
        d = tmp_path / "sub" / "dir"
        mod.ensure_dir(str(d))
        assert d.is_dir()

    def test_file_exists(self, tmp_path):
        mod = _load_ha()
        f = tmp_path / "exists.txt"
        f.write_text("hello")
        assert mod.file_exists(str(f)) is True
        assert mod.file_exists(str(tmp_path / "no.txt")) is False

    def test_read_file(self, tmp_path):
        mod = _load_ha()
        f = tmp_path / "data.txt"
        f.write_text("  content  \n")
        assert mod.read_file(str(f)) == "content"

    def test_write_file(self, tmp_path):
        mod = _load_ha()
        f = tmp_path / "out.txt"
        mod.write_file(str(f), "hello\n")
        assert f.read_text() == "hello\n"
        assert oct(os.stat(str(f)).st_mode & 0o777) == "0o600"

    def test_write_file_mode(self, tmp_path):
        mod = _load_ha()
        f = tmp_path / "pub.txt"
        mod.write_file(str(f), "pubkey", 0o644)
        assert oct(os.stat(str(f)).st_mode & 0o777) == "0o644"


class TestIfaceExists:
    def test_exists(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod, "run", lambda cmd, check=True, capture=True: "interface: wg-HUB-test\n")
        assert mod.iface_exists() is True

    def test_not_exists(self, monkeypatch):
        mod = _load_ha()
        def _raise(*a, **kw):
            raise Exception("not found")
        monkeypatch.setattr(mod, "run", _raise)
        assert mod.iface_exists() is False


class TestEnsureKeys:
    def test_keys_exist(self, tmp_path, monkeypatch):
        mod = _load_ha()
        priv_path = str(tmp_path / "wg-HUB-test.key")
        pub_path = str(tmp_path / "wg-HUB-test.pub")
        monkeypatch.setattr(mod, "WG_DIR", str(tmp_path))
        monkeypatch.setattr(mod, "HUB_PRIVKEY_PATH", priv_path)
        monkeypatch.setattr(mod, "HUB_PUBKEY_PATH", pub_path)
        priv = tmp_path / "wg-HUB-test.key"
        pub = tmp_path / "wg-HUB-test.pub"
        priv.write_text("privkey\n")
        pub.write_text("pubkey\n")
        mod.ensure_keys()
        assert priv.read_text() == "privkey\n"

    def test_keys_generated(self, tmp_path, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod, "WG_DIR", str(tmp_path))
        monkeypatch.setattr(mod, "HUB_PRIVKEY_PATH", str(tmp_path / "wg-HUB-test.key"))
        monkeypatch.setattr(mod, "HUB_PUBKEY_PATH", str(tmp_path / "wg-HUB-test.pub"))
        monkeypatch.setattr(mod, "run", lambda cmd, check=True, capture=True: "generated-privkey\n")
        monkeypatch.setattr(mod.subprocess, "check_output", lambda cmd, input, text: "generated-pubkey\n")
        mod.ensure_keys()
        priv = tmp_path / "wg-HUB-test.key"
        pub = tmp_path / "wg-HUB-test.pub"
        assert priv.read_text().strip() == "generated-privkey"
        assert pub.read_text().strip() == "generated-pubkey"


class TestEnsureConf:
    def test_conf_exists(self, tmp_path, monkeypatch):
        mod = _load_ha()
        priv_path = str(tmp_path / "wg-HUB-test.key")
        pub_path = str(tmp_path / "wg-HUB-test.pub")
        conf_path = str(tmp_path / "wg-HUB-test.conf")
        monkeypatch.setattr(mod, "HUB_CONF_PATH", conf_path)
        monkeypatch.setattr(mod, "HUB_PRIVKEY_PATH", priv_path)
        monkeypatch.setattr(mod, "HUB_PUBKEY_PATH", pub_path)
        monkeypatch.setattr(mod, "WG_DIR", str(tmp_path))
        (tmp_path / "wg-HUB-test.conf").write_text("existing\n")
        (tmp_path / "wg-HUB-test.key").write_text("priv\n")
        (tmp_path / "wg-HUB-test.pub").write_text("pub\n")
        mod.ensure_conf()
        assert (tmp_path / "wg-HUB-test.conf").read_text() == "existing\n"

    def test_conf_created(self, tmp_path, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod, "HUB_CONF_PATH", str(tmp_path / "wg-HUB-test.conf"))
        monkeypatch.setattr(mod, "HUB_LISTEN_PORT", 51820)
        monkeypatch.setattr(mod, "HUB_TUNNEL_IP", "10.20.30.1/24")
        monkeypatch.setattr(mod, "HUB_PRIVKEY_PATH", str(tmp_path / "wg-HUB-test.key"))
        monkeypatch.setattr(mod, "HUB_PUBKEY_PATH", str(tmp_path / "wg-HUB-test.pub"))
        (tmp_path / "wg-HUB-test.key").write_text("my-priv-key\n")
        (tmp_path / "wg-HUB-test.pub").write_text("my-pub-key\n")
        mod.ensure_conf()
        conf = (tmp_path / "wg-HUB-test.conf").read_text()
        assert "[Interface]" in conf
        assert "Address = 10.20.30.1/24" in conf
        assert "ListenPort = 51820" in conf
        assert "PrivateKey = my-priv-key" in conf


class TestIptables:
    def test_iptables_exists(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod.subprocess, "run", lambda *a, **kw: MagicMock(returncode=0))
        assert mod._iptables_exists(["-C", "FORWARD"]) is True

    def test_iptables_not_exists(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod.subprocess, "run", lambda *a, **kw: MagicMock(returncode=1))
        assert mod._iptables_exists(["-C", "FORWARD"]) is False

    def test_ensure_forward_rule_adds(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod, "_iptables_exists", lambda a: False)
        calls = []
        monkeypatch.setattr(mod, "run", lambda cmd, check=True: calls.append(cmd))
        mod.ensure_forward_rule()
        assert any("FORWARD" in str(c) for c in calls)

    def test_ensure_forward_rule_skips(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod, "_iptables_exists", lambda a: True)
        calls = []
        monkeypatch.setattr(mod, "run", lambda cmd, check=True: calls.append(cmd))
        mod.ensure_forward_rule()
        assert calls == []

    def test_ensure_nat_rules_disabled(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod, "HUB_ENABLE_NAT", False)
        calls = []
        monkeypatch.setattr(mod, "run", lambda cmd, check=True: calls.append(cmd))
        mod.ensure_nat_rules()
        assert calls == []

    def test_ensure_nat_rules_enabled(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod, "HUB_ENABLE_NAT", True)
        monkeypatch.setattr(mod, "TUNNEL_CIDR", "10.20.30.0/24")
        monkeypatch.setattr(mod, "HUB_NAT_OUT_IFACE", "eth0")
        monkeypatch.setattr(mod, "_iptables_exists", lambda a: False)
        calls = []
        monkeypatch.setattr(mod, "run", lambda cmd, check=True: calls.append(cmd))
        mod.ensure_nat_rules()
        assert len(calls) == 3
        assert any("MASQUERADE" in str(c) for c in calls)

    def test_cleanup_iptables_rules(self, monkeypatch):
        mod = _load_ha()
        mock_run = MagicMock()
        monkeypatch.setattr(mod.subprocess, "run", mock_run)
        mod.cleanup_iptables_rules()
        assert mock_run.call_count == 4
        args_str = " ".join(str(a) for a in mock_run.call_args_list[0][0][0])
        assert "FORWARD" in args_str


class TestHubEndpoints:
    def test_hub_health(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod, "HUB_AGENT_TOKEN", "t")
        assert mod.hub_health("t") == "ok"

    def test_hub_health_bad_token(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod, "HUB_AGENT_TOKEN", "t")
        with pytest.raises(PermissionError):
            mod.hub_health("wrong")

    def test_hub_show(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod, "HUB_AGENT_TOKEN", "t")
        monkeypatch.setattr(mod, "ensure_wg_up", lambda: None)
        monkeypatch.setattr(mod, "run", lambda cmd, check=True, capture=True: "wg show output\n")
        out = mod.hub_show("t")
        assert "wg show" in out

    def test_hub_public_key(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod, "HUB_AGENT_TOKEN", "t")
        monkeypatch.setattr(mod.subprocess, "check_output", lambda cmd, text: "pubkey123\n")
        assert mod.hub_public_key("t") == "pubkey123"

    def test_hub_public_key_error(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod, "HUB_AGENT_TOKEN", "t")
        with patch.object(mod.subprocess, "check_output", side_effect=subprocess.CalledProcessError(1, "wg")):
            with pytest.raises(RuntimeError):
                mod.hub_public_key("t")

    def test_hub_ensure_base_rules(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod, "HUB_AGENT_TOKEN", "t")
        calls = []
        monkeypatch.setattr(mod, "ensure_wg_up", lambda: calls.append("wg_up"))
        monkeypatch.setattr(mod, "ensure_ip_forward", lambda: calls.append("ip_fwd"))
        monkeypatch.setattr(mod, "ensure_forward_rule", lambda: calls.append("fwd"))
        monkeypatch.setattr(mod, "ensure_nat_rules", lambda: calls.append("nat"))
        assert mod.hub_ensure_base_rules("t") is True
        assert calls == ["wg_up", "ip_fwd", "fwd", "nat"]

    def test_hub_cleanup(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod, "HUB_AGENT_TOKEN", "t")
        calls = []
        monkeypatch.setattr(mod, "cleanup_iptables_rules", lambda: calls.append("cleanup"))
        assert mod.hub_cleanup("t") is True
        assert calls == ["cleanup"]


class TestHubApplyPeer:
    PUBKEY = "A" * 44

    def test_invalid_pubkey(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod, "HUB_AGENT_TOKEN", "t")
        with pytest.raises(ValueError, match="public_key"):
            mod.hub_apply_peer("t", "short", "10.0.0.1/32")

    def test_invalid_allowed_ips(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod, "HUB_AGENT_TOKEN", "t")
        with pytest.raises(ValueError, match="allowed_ips"):
            mod.hub_apply_peer("t", self.PUBKEY, "")

    def test_off_mode(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod, "HUB_AGENT_TOKEN", "t")
        monkeypatch.setattr(mod, "HUB_MESH_MODE", "off")
        calls = []
        monkeypatch.setattr(mod, "run", lambda cmd, check=True: calls.append(cmd))
        monkeypatch.setattr(mod, "ensure_wg_up", lambda: None)
        result = mod.hub_apply_peer("t", self.PUBKEY, "10.0.0.1/32", endpoint="1.2.3.4:51820")
        assert result is True
        assert any("wg" in str(c).lower() for c in calls)

    def test_mesh_mode_filters_to_32(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod, "HUB_AGENT_TOKEN", "t")
        monkeypatch.setattr(mod, "HUB_MESH_MODE", "mesh")
        calls = []
        monkeypatch.setattr(mod, "run", lambda cmd, check=True: calls.append(cmd))
        monkeypatch.setattr(mod, "ensure_wg_up", lambda: None)
        mod.hub_apply_peer("t", self.PUBKEY, "10.0.0.1/32,10.0.0.0/24")
        assert any("10.0.0.1/32" in str(c) for c in calls)
        assert not any("10.0.0.0/24" in str(c) for c in calls)

    def test_hub_mesh_mode(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod, "HUB_AGENT_TOKEN", "t")
        monkeypatch.setattr(mod, "HUB_MESH_MODE", "hub-mesh")
        calls = []
        monkeypatch.setattr(mod, "run", lambda cmd, check=True: calls.append(cmd))
        monkeypatch.setattr(mod, "ensure_wg_up", lambda: None)
        mod.hub_apply_peer("t", self.PUBKEY, "10.0.0.1/32")
        assert any("wg" in str(c).lower() for c in calls)

    def test_endpoint_included(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod, "HUB_AGENT_TOKEN", "t")
        monkeypatch.setattr(mod, "HUB_MESH_MODE", "off")
        calls = []
        monkeypatch.setattr(mod, "run", lambda cmd, check=True: calls.append(cmd))
        monkeypatch.setattr(mod, "ensure_wg_up", lambda: None)
        mod.hub_apply_peer("t", self.PUBKEY, "10.0.0.1/32", endpoint="5.6.7.8:51820")
        assert any("5.6.7.8" in str(c) for c in calls)

    def test_no_endpoint_ok(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod, "HUB_AGENT_TOKEN", "t")
        monkeypatch.setattr(mod, "HUB_MESH_MODE", "off")
        calls = []
        monkeypatch.setattr(mod, "run", lambda cmd, check=True: calls.append(cmd))
        monkeypatch.setattr(mod, "ensure_wg_up", lambda: None)
        mod.hub_apply_peer("t", self.PUBKEY, "10.0.0.1/32")
        assert any("wg" in str(c).lower() for c in calls)


class TestHubRemovePeer:
    PUBKEY = "B" * 44

    def test_remove(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod, "HUB_AGENT_TOKEN", "t")
        calls = []
        monkeypatch.setattr(mod, "run", lambda cmd, check=True: calls.append(cmd))
        monkeypatch.setattr(mod, "ensure_wg_up", lambda: None)
        result = mod.hub_remove_peer("t", self.PUBKEY)
        assert result is True
        assert any("remove" in str(c) for c in calls)

    def test_remove_invalid_key(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod, "HUB_AGENT_TOKEN", "t")
        with pytest.raises(ValueError):
            mod.hub_remove_peer("t", "short")


class TestHubListMeshPeers:
    @pytest.fixture
    def wg_dump(self):
        return (
            "interface: wg-HUB\n"
            "pubkey1\t(pre)\t1.2.3.4:51820\t10.0.0.1/32\t100\t1000\t2000\toff\n"
            "pubkey2\t(pre)\t5.6.7.8:51820\t10.0.0.2/32,10.0.0.3/32\t200\t2000\t3000\toff\n"
        )

    def test_parse_all_peers(self, monkeypatch, wg_dump):
        mod = _load_ha()
        monkeypatch.setattr(mod, "HUB_AGENT_TOKEN", "t")
        monkeypatch.setattr(mod, "ensure_wg_up", lambda: None)
        monkeypatch.setattr(mod.subprocess, "check_output", lambda cmd, **kw: wg_dump)
        monkeypatch.setattr(mod.time, "time", lambda: 200)
        peers = mod.hub_list_mesh_peers("t")
        assert len(peers) == 2
        assert peers[0]["public_key"] == "pubkey1"
        assert peers[1]["public_key"] == "pubkey2"
        assert peers[0]["alive"] is True
        assert peers[1]["alive"] is True

    def test_stale_peer(self, monkeypatch, wg_dump):
        mod = _load_ha()
        monkeypatch.setattr(mod, "HUB_AGENT_TOKEN", "t")
        monkeypatch.setattr(mod, "ensure_wg_up", lambda: None)
        monkeypatch.setattr(mod.subprocess, "check_output", lambda cmd, **kw: wg_dump)
        monkeypatch.setattr(mod.time, "time", lambda: 500)
        peers = mod.hub_list_mesh_peers("t")
        assert peers[0]["alive"] is False

    def test_filter_by_cidr(self, monkeypatch, wg_dump):
        mod = _load_ha()
        monkeypatch.setattr(mod, "HUB_AGENT_TOKEN", "t")
        monkeypatch.setattr(mod, "ensure_wg_up", lambda: None)
        monkeypatch.setattr(mod.subprocess, "check_output", lambda cmd, **kw: wg_dump)
        monkeypatch.setattr(mod.time, "time", lambda: 500)
        peers = mod.hub_list_mesh_peers("t", network_cidr="10.0.0.0/24")
        assert len(peers) == 2

    def test_filter_excludes(self, monkeypatch, wg_dump):
        mod = _load_ha()
        monkeypatch.setattr(mod, "HUB_AGENT_TOKEN", "t")
        monkeypatch.setattr(mod, "ensure_wg_up", lambda: None)
        monkeypatch.setattr(mod.subprocess, "check_output", lambda cmd, **kw: wg_dump)
        monkeypatch.setattr(mod.time, "time", lambda: 500)
        peers = mod.hub_list_mesh_peers("t", network_cidr="10.10.0.0/24")
        assert len(peers) == 0

    def test_endpoint_none(self, monkeypatch):
        mod = _load_ha()
        dump = "interface: wg-HUB\npubkey1\t(pre)\t(none)\t10.0.0.1/32\t100\t0\t0\toff\n"
        monkeypatch.setattr(mod, "HUB_AGENT_TOKEN", "t")
        monkeypatch.setattr(mod, "ensure_wg_up", lambda: None)
        monkeypatch.setattr(mod.subprocess, "check_output", lambda cmd, **kw: dump)
        monkeypatch.setattr(mod.time, "time", lambda: 500)
        peers = mod.hub_list_mesh_peers("t")
        assert peers[0]["endpoint"] is None

    def test_wg_error(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod, "HUB_AGENT_TOKEN", "t")
        monkeypatch.setattr(mod, "ensure_wg_up", lambda: None)
        from unittest.mock import patch
        with patch.object(mod.subprocess, "check_output", side_effect=subprocess.CalledProcessError(1, "wg")):
            with pytest.raises(RuntimeError, match="wg show dump failed"):
                mod.hub_list_mesh_peers("t")

    def test_short_line_skipped(self, monkeypatch):
        mod = _load_ha()
        dump = "interface: wg-HUB\npubkey1\t(pre)\t1.2.3.4:51820\n"
        monkeypatch.setattr(mod, "HUB_AGENT_TOKEN", "t")
        monkeypatch.setattr(mod, "ensure_wg_up", lambda: None)
        monkeypatch.setattr(mod.subprocess, "check_output", lambda cmd, **kw: dump)
        monkeypatch.setattr(mod.time, "time", lambda: 500)
        peers = mod.hub_list_mesh_peers("t")
        assert len(peers) == 0

    def test_bad_handshake_ts(self, monkeypatch):
        mod = _load_ha()
        dump = "interface: wg-HUB\npubkey1\t(pre)\t1.2.3.4:51820\t10.0.0.1/32\tnot_a_number\t0\t0\toff\n"
        monkeypatch.setattr(mod, "HUB_AGENT_TOKEN", "t")
        monkeypatch.setattr(mod, "ensure_wg_up", lambda: None)
        monkeypatch.setattr(mod.subprocess, "check_output", lambda cmd, **kw: dump)
        monkeypatch.setattr(mod.time, "time", lambda: 500)
        peers = mod.hub_list_mesh_peers("t")
        assert peers[0]["latest_handshake"] == 0
        assert peers[0]["alive"] is False


class TestEnsureWgUp:
    def test_already_up(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod, "ensure_conf", lambda: None)
        monkeypatch.setattr(mod, "iface_exists", lambda: True)
        calls = []
        monkeypatch.setattr(mod, "run", lambda cmd, check=True: calls.append(cmd))
        mod.ensure_wg_up()
        assert len(calls) == 0

    def test_bring_up(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod, "ensure_conf", lambda: None)
        exists = [False, True]
        monkeypatch.setattr(mod, "iface_exists", lambda: exists.pop(0))
        calls = []
        monkeypatch.setattr(mod, "run", lambda cmd, check=True: calls.append(cmd))
        mod.ensure_wg_up()
        assert any("up" in str(c) for c in calls)

    def test_fail_to_bring_up(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod, "ensure_conf", lambda: None)
        monkeypatch.setattr(mod, "iface_exists", lambda: False)
        monkeypatch.setattr(mod, "run", lambda cmd, check=True: None)
        with pytest.raises(RuntimeError, match="No se pudo levantar"):
            mod.ensure_wg_up()


class TestConfigConstants:
    def test_hub_mesh_mode_enum_off(self, monkeypatch):
        monkeypatch.setenv("HUB_MESH_MODE", "off")
        mod = _load_ha()
        assert mod.HUB_MESH_MODE == "off"

    def test_hub_mesh_mode_enum_mesh(self, monkeypatch):
        monkeypatch.setenv("HUB_MESH_MODE", "mesh")
        mod = _load_ha()
        assert mod.HUB_MESH_MODE == "mesh"

    def test_hub_mesh_mode_enum_hub_mesh(self, monkeypatch):
        monkeypatch.setenv("HUB_MESH_MODE", "hub-mesh")
        mod = _load_ha()
        assert mod.HUB_MESH_MODE == "hub-mesh"

    def test_hub_mesh_mode_compat_0(self, monkeypatch):
        monkeypatch.setenv("HUB_MESH_MODE", "0")
        mod = _load_ha()
        assert mod.HUB_MESH_MODE == "off"

    def test_hub_mesh_mode_compat_1(self, monkeypatch):
        monkeypatch.setenv("HUB_MESH_MODE", "1")
        mod = _load_ha()
        assert mod.HUB_MESH_MODE == "mesh"

    def test_hub_mesh_mode_invalid(self, monkeypatch):
        monkeypatch.setenv("HUB_MESH_MODE", "invalid")
        with pytest.raises(SystemExit, match="inválido"):
            _load_ha()

    def test_port_valid(self, monkeypatch):
        monkeypatch.setenv("HUB_AGENT_PORT", "9000")
        monkeypatch.setenv("HUB_LISTEN_PORT", "51820")
        mod = _load_ha()
        assert mod.HUB_AGENT_PORT == 9000
        assert mod.HUB_LISTEN_PORT == 51820

    def test_port_invalid(self, monkeypatch):
        monkeypatch.setenv("HUB_AGENT_PORT", "abc")
        with pytest.raises(SystemExit, match="entero"):
            _load_ha()

    def test_port_out_of_range(self, monkeypatch):
        monkeypatch.setenv("HUB_AGENT_PORT", "99999")
        with pytest.raises(SystemExit, match="rango"):
            _load_ha()


class TestEnsureBaseRulesInternal:
    def test_hub_mesh_log(self, monkeypatch):
        mod = _load_ha()
        monkeypatch.setattr(mod, "HUB_MESH_MODE", "hub-mesh")
        monkeypatch.setattr(mod, "TUNNEL_CIDR", "10.0.0.0/24")
        monkeypatch.setattr(mod, "ensure_wg_up", lambda: None)
        monkeypatch.setattr(mod, "ensure_ip_forward", lambda: None)
        monkeypatch.setattr(mod, "ensure_forward_rule", lambda: None)
        monkeypatch.setattr(mod, "ensure_nat_rules", lambda: None)
        mod.ensure_base_rules_internal()
