"""
Manejo de llaves WireGuard del peer.
"""

import os
import subprocess
from typing import Tuple

from . import config as cfg
from .utils import log, ensure_dir, write_file, read_file


def gen_keys_if_needed() -> None:
    ensure_dir()
    if os.path.exists(cfg.WG_PRIV_KEY_PATH) and os.path.exists(cfg.WG_PUB_KEY_PATH):
        return
    priv = subprocess.check_output([cfg.WG_BIN, "genkey"], universal_newlines=True).strip()  # nosec B603
    write_file(cfg.WG_PRIV_KEY_PATH, priv + "\n", 0o600)
    pub = subprocess.check_output([cfg.WG_BIN, "pubkey"], input=priv + "\n", universal_newlines=True).strip()  # nosec B603
    write_file(cfg.WG_PUB_KEY_PATH, pub + "\n", 0o600)
    log("Llaves del peer generadas")


def rotate_keys() -> Tuple[str, str]:
    """
    Genera nuevo par de llaves y las persiste.
    Retorna (privada, publica).
    """
    ensure_dir()
    priv = subprocess.check_output([cfg.WG_BIN, "genkey"], universal_newlines=True).strip()  # nosec B603
    pub = subprocess.check_output([cfg.WG_BIN, "pubkey"], input=priv + "\n", universal_newlines=True).strip()  # nosec B603
    write_file(cfg.WG_PRIV_KEY_PATH, priv + "\n", 0o600)
    write_file(cfg.WG_PUB_KEY_PATH, pub + "\n", 0o600)
    return priv, pub


def load_public_key() -> str:
    return read_file(cfg.WG_PUB_KEY_PATH)


def load_private_key() -> str:
    return read_file(cfg.WG_PRIV_KEY_PATH)
