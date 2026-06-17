"""
Utilidades base: log, subprocess helper, manejo de archivos.
"""

import os
import subprocess
from typing import Any
from xmlrpc.client import ServerProxy

from . import config as cfg


def log(msg: str) -> None:
    print(f"[wg-auto-register] {msg}", flush=True)


def run(cmd: list, check: bool = True, capture: bool = False) -> str:  # nosec B603
    log(f"RUN: {' '.join(cmd)}")
    if capture:
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        if check and r.returncode != 0:
            raise RuntimeError(r.stdout.strip())
        return r.stdout
    r = subprocess.run(cmd, universal_newlines=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    return ""


def ensure_dir(path: str = cfg.WG_DIR) -> None:
    os.makedirs(path, exist_ok=True)


def write_file(path: str, content: str, mode: int = 0o600) -> None:
    with open(path, "w") as f:
        f.write(content)
    os.chmod(path, mode)


def read_file(path: str) -> str:
    with open(path, "r") as f:
        return f.read().strip()


def rpc() -> Any:
    return ServerProxy(cfg.ORCH_URL, allow_none=True)
