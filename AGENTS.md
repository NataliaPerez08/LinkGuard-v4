# AGENTS.md — Session Context

## Goal
Replace parrot with QEMU VMs (peer01/02/03) as local test peers and run all three report topologies.

## Status
✅ **hub-spoke** — completed with 8 peers (5 real + 3 QEMU).
✅ **hub-mesh** — completed with 8 peers (fast mode).
✅ **mesh** — completed (fast mode). EC2-to-EC2: 6-7/7 OK. NAT peers (jump/QEMU): 3/7 OK (expected).

## Testbed
- Orchestrator: `34.193.139.170` (ADMIN_TOKEN in .env.orch)
- 5 real peers (Ubuntu, Amazon Linux, AlmaLinux, VM40, RPi5)
- 3 QEMU Alpine VMs on br0/br1/br2: orq(192.168.100.10), pa(192.168.100.20), pb(192.168.100.30)
- Tenants: admin + tenant-a (multi-user)
- SSH: cloud via `linkguard-key.pem`; QEMU via sshpass `linkguard-test`; terminal via jump `root@100.115.215.49`
- QEMU peer IDs: peer01/02/03 registered under tenant-a

## Key Decisions
- `rp_filter=0` on hub for asymmetric NAT routing
- `--admin-token`/`--token` only on main parser (not subparsers) — argparse fix
- CLI-based RPC calls (orch-cli) preferred over direct XML-RPC
- `LOCAL_PEER` removed; `QEMU_PEERS` replaces parrot
- `USER_ID=tenant-a` required on QEMU peer.env (ORCH_TOKEN belongs to tenant, not peer)

## Known Issues
- **mesh topology**: 0/7 pings — all peers behind NAT, no direct connectivity. Hub-mesh works via hub relay.
- **hub-mesh**: terminal peers behind jump host get 1-3/7 pings (expected NAT behavior)
- **wireguard rekey**: first ping after idle drops (accepted WireGuard behavior)
- QEMU VMs can die if testbed is not kept alive; restart with `launch-testbed.py up`
- **mesh fix**: required `WG_LISTEN_PORT=51820` on EC2 peers (fixed port open in SG) + `config_gen.py` fix to include Endpoint regardless of `alive` status

## Relevant Files
- `tests-linkguard-aws/report_common.py`: QEMU_PEERS, ssh_qemu helpers, ping/throughput
- `tests-linkguard-aws/generate-report-hubspoke.py`: hub-spoke entry point
- `tests-linkguard-aws/generate-report-hubmesh.py`: hub-mesh entry point
- `tests-linkguard-aws/generate-report-mesh.py`: mesh entry point
- `orchestrator-install-v2/orch-cli.py`: CLI tool (argparse fixed)
- `peer-install-v2/peer_register/`: wg-auto-register v4 package
- `testbed/scripts/launch-testbed.py`: QEMU VM launcher
