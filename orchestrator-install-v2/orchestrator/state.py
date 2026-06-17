"""
Estado persistente del Orchestrator.
STATE, locks, persistencia, backup automatico y eventos.
"""

import json
import os
import time
import threading

from . import config


# Locks granulares — orden: USERS > NETWORKS > PEERS > EVENTS (nunca invertir)
LOCK_PEERS = threading.RLock()
LOCK_NETWORKS = threading.RLock()
LOCK_USERS = threading.RLock()
LOCK_EVENTS = threading.RLock()
LOCK_STATE = threading.RLock()
LOCK_REVOKED = threading.RLock()


def now_ts() -> int:
    return int(time.time())


def ensure_dir(path: str) -> None:
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)


def load_json(path: str) -> dict:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_json(path: str, data: dict) -> None:
    ensure_dir(path)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    os.replace(tmp, path)


DEFAULT_STATE = {
    "version": 4,
    "config_version": 1,
    "users": {},
    "peers": {},
    "networks": {},
    "events": [],
}

STATE: dict = {}


def _append_event_to_log(ev: dict) -> None:
    try:
        ensure_dir(config.EVENTS_LOG_PATH)
        with open(config.EVENTS_LOG_PATH, "a") as f:
            f.write(json.dumps(ev, sort_keys=True) + "\n")
    except Exception as e:
        config.log(f"WARNING: No pude escribir evento en log: {e}")


def add_event(kind: str, detail: dict) -> None:
    ev = {"ts": now_ts(), "kind": kind, "detail": detail}
    _append_event_to_log(ev)
    with LOCK_EVENTS:
        STATE["events"].append(ev)
        if len(STATE["events"]) > config.EVENTS_IN_STATE_MAX:
            STATE["events"] = STATE["events"][-config.EVENTS_IN_STATE_MAX:]


def _do_backup() -> None:
    if not config.BACKUP_ENABLED:
        return
    try:
        os.makedirs(config.BACKUP_DIR, exist_ok=True)
        ts = time.strftime("%Y%m%dT%H%M%S")
        backup_path = os.path.join(config.BACKUP_DIR, f"state-{ts}.json")
        with LOCK_STATE:
            save_json(backup_path, STATE)
        backups = sorted([f for f in os.listdir(config.BACKUP_DIR)
                          if f.startswith("state-") and f.endswith(".json")])
        for old in backups[:-config.BACKUP_MAX_KEEP]:
            try:
                os.remove(os.path.join(config.BACKUP_DIR, old))
            except OSError:
                pass
        config.log(f"Backup guardado: {backup_path}")
    except Exception as e:
        config.log(f"WARNING: Backup fallo: {e}")


def _backup_loop() -> None:
    while True:
        time.sleep(config.BACKUP_INTERVAL_SEC)
        _do_backup()


def start_backup_loop() -> None:
    threading.Thread(target=_backup_loop, daemon=True, name="backup-loop").start()
    config.log(f"Backup automatico: cada {config.BACKUP_INTERVAL_SEC}s -> {config.BACKUP_DIR} (max {config.BACKUP_MAX_KEEP} copias)")


def persist() -> None:
    with LOCK_STATE:
        save_json(config.STATE_PATH, STATE)


def load_state() -> None:
    global STATE
    data = load_json(config.STATE_PATH)
    if not data:
        STATE = json.loads(json.dumps(DEFAULT_STATE))
        persist()
        return
    merged = json.loads(json.dumps(DEFAULT_STATE))
    for k in ("users", "peers", "networks", "events"):
        merged[k] = data.get(k, merged[k])
    merged["version"] = data.get("version", merged["version"])
    merged["config_version"] = data.get("config_version", merged["config_version"])
    STATE = merged


def bump_config_version_locked() -> int:
    with LOCK_STATE:
        STATE["config_version"] = int(STATE.get("config_version", 1)) + 1
        return STATE["config_version"]
