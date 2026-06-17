"""
LinkGuard Peer Auto-Register v4 - Paquete modular.
Punto de entrada: main()
"""

import argparse
import os

from . import config as cfg
from .commands import cmd_register, cmd_heartbeat, cmd_run, cmd_request_network, cmd_rotate_key


def main() -> None:
    ap = argparse.ArgumentParser(description="Peer auto-register + heartbeat + JWT session + multi-network")
    sub = ap.add_subparsers(dest="cmd")

    p_reg = sub.add_parser("register")
    p_reg.set_defaults(func=cmd_register)

    p_hb = sub.add_parser("heartbeat")
    p_hb.set_defaults(func=cmd_heartbeat)

    p_run = sub.add_parser("run", help="Daemon: register + heartbeat en loop")
    p_run.add_argument("--interval", type=int, default=cfg.WG_HEARTBEAT_INTERVAL, help="segundos entre heartbeats")
    p_run.add_argument("--session", default=os.getenv("WG_SESSION", "default"), help="session id (default)")
    p_run.set_defaults(func=cmd_run)

    p_req = sub.add_parser("request-network")
    p_req.add_argument("network_id")
    p_req.add_argument("--apply", action="store_true")
    p_req.set_defaults(func=cmd_request_network)

    p_rot = sub.add_parser("rotate-key")
    p_rot.set_defaults(func=cmd_rotate_key)

    args = ap.parse_args()
    if not getattr(args, "cmd", None):
        ap.error("the following arguments are required: cmd")
    args.func(args)


if __name__ == "__main__":
    main()
