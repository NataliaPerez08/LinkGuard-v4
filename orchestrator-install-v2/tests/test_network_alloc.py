import pytest


class TestAllocateIP:
    def test_first_ip(self):
        from orchestrator.network_alloc import _allocate_ip_in_network
        ip = _allocate_ip_in_network("10.0.0.0/24", [])
        assert ip == "10.0.0.2"

    def test_skip_used(self):
        from orchestrator.network_alloc import _allocate_ip_in_network
        ip = _allocate_ip_in_network("10.0.0.0/24", ["10.0.0.1", "10.0.0.2"])
        assert ip == "10.0.0.3"

    def test_full_subnet(self):
        from orchestrator.network_alloc import _allocate_ip_in_network
        used = [f"10.0.0.{i}" for i in range(1, 255)]
        ip = _allocate_ip_in_network("10.0.0.0/24", used)
        assert ip is None

    def test_invalid_cidr(self):
        from orchestrator.network_alloc import _allocate_ip_in_network
        ip = _allocate_ip_in_network("not-a-cidr", [])
        assert ip is None

    def test_small_subnet(self):
        from orchestrator.network_alloc import _allocate_ip_in_network
        ip = _allocate_ip_in_network("10.0.0.0/30", [])
        assert ip == "10.0.0.2"


class TestNetworkAllocStruct:
    def test_ensure_struct_adds(self):
        from orchestrator.network_alloc import _ensure_network_alloc_struct
        n = {}
        _ensure_network_alloc_struct(n)
        assert "alloc" in n
        assert n["alloc"]["reserved"] == []
        assert n["alloc"]["assigned"] == {}

    def test_ensure_struct_preserves(self):
        from orchestrator.network_alloc import _ensure_network_alloc_struct
        n = {"alloc": {"reserved": ["10.0.0.10"], "assigned": {"p1": "10.0.0.1"}}}
        _ensure_network_alloc_struct(n)
        assert n["alloc"]["assigned"]["p1"] == "10.0.0.1"


class TestReleaseIP:
    def test_release_existing(self, sample_state):
        from orchestrator.network_alloc import _network_release_ip
        _network_release_ip("lan1", "p1")
        assert "p1" not in sample_state["networks"]["lan1"]["alloc"]["assigned"]

    def test_release_nonexistent(self, sample_state):
        from orchestrator.network_alloc import _network_release_ip
        _network_release_ip("lan1", "p_nonexistent")
        assert sample_state["networks"]["lan1"]["alloc"]["assigned"]["p1"] == "10.0.0.1"

    def test_release_missing_network(self):
        from orchestrator.network_alloc import _network_release_ip
        _network_release_ip("nonexistent", "p1")


class TestAssignIP:
    def test_assign_new(self, sample_state):
        from orchestrator import state
        from orchestrator.network_alloc import _assign_ip_to_peer_in_network
        state.STATE["peers"]["p2"] = {"public_key": "pk_p2", "networks": [], "ip": None}
        ip = _assign_ip_to_peer_in_network("p2", "lan1")
        assert ip == "10.0.0.2"

    def test_reuse_existing(self, sample_state):
        from orchestrator.network_alloc import _assign_ip_to_peer_in_network
        ip = _assign_ip_to_peer_in_network("p1", "lan1")
        assert ip == "10.0.0.1"

    def test_missing_network(self, sample_state):
        from orchestrator.network_alloc import _assign_ip_to_peer_in_network
        ip = _assign_ip_to_peer_in_network("p1", "nonexistent")
        assert ip is None
