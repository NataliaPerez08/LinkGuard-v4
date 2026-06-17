"""
Persistencia del estado del peer (JWT, config version, etc).
"""

import json
import os

from . import config as cfg
from .utils import ensure_dir


def load_state() -> dict:
    try:
        with open(cfg.STATE_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(st: dict) -> None:
    ensure_dir()
    with open(cfg.STATE_PATH, "w") as f:
        json.dump(st, f, indent=2, sort_keys=True)
    os.chmod(cfg.STATE_PATH, 0o600)
