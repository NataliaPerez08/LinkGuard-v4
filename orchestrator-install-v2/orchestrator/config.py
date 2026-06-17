"""
Configuracion del Orchestrator - LinkGuard v4
Todas las constantes de entorno, validacion de tokens y dependencias.
"""

import os
import logging
import ipaddress

logging.basicConfig(
    level=logging.INFO,
    format="[orchestrator] %(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("orchestrator")


def log(msg: str) -> None:
    logger.info(msg)


ORCH_BIND = os.getenv("ORCH_BIND", "0.0.0.0")  # nosec B104 — por defecto escucha en todas las interfaces
ORCH_PORT = int(os.getenv("ORCH_PORT", "8000"))
STATE_PATH = os.getenv("ORCH_STATE_PATH", "/var/lib/wg-orchestrator/state.json")

HUB_AGENT_URL = os.getenv("HUB_AGENT_URL", "http://127.0.0.1:9000/RPC2")
HUB_AGENT_TOKEN = os.getenv("HUB_AGENT_TOKEN", "")
HUB_ENDPOINT = os.getenv("HUB_ENDPOINT", "")

ORCH_TOKEN = os.getenv("ORCH_TOKEN", "")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

JWT_SECRET_PATH = os.getenv("JWT_SECRET_PATH", "/etc/linkguard/jwt_secret")
JWT_ISSUER = os.getenv("JWT_ISSUER", "linkguard-orchestrator")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "linkguard")
JWT_TTL_DEFAULT = int(os.getenv("JWT_TTL_DEFAULT", "600"))

HEARTBEAT_TTL_SEC = int(os.getenv("HEARTBEAT_TTL_SEC", "180"))

AUTO_APPROVE_ENABLED = os.getenv("AUTO_APPROVE_ENABLED", "0") == "1"
AUTO_APPROVE_RULES_RAW = os.getenv("AUTO_APPROVE_RULES", "").strip()
AUTO_APPROVE_REQUIRE_CONFIRM = os.getenv("AUTO_APPROVE_REQUIRE_CONFIRM", "0") == "1"

DEFAULT_NET_ID = os.getenv("DEFAULT_NET_ID", "default")
DEFAULT_NET_CIDR = os.getenv("DEFAULT_NET_CIDR", "10.20.30.0/24")
WG_PEER_ALLOWED_FMT = os.getenv("WG_PEER_ALLOWED_FMT", "{ip}/32")
WG_MTU = int(os.getenv("WG_MTU", "1420"))

BACKUP_ENABLED = os.getenv("BACKUP_ENABLED", "1") == "1"
BACKUP_DIR = os.getenv("BACKUP_DIR", "/var/lib/wg-orchestrator/backups")
BACKUP_MAX_KEEP = int(os.getenv("BACKUP_MAX_KEEP", "10"))
BACKUP_INTERVAL_SEC = int(os.getenv("BACKUP_INTERVAL_SEC", "300"))

EVENTS_LOG_PATH = os.getenv("EVENTS_LOG_PATH", "/var/lib/wg-orchestrator/events.jsonl")
EVENTS_IN_STATE_MAX = int(os.getenv("EVENTS_IN_STATE_MAX", "200"))

JWT_REVOKED_PATH = os.getenv("JWT_REVOKED_PATH", "/var/lib/wg-orchestrator/jwt_revoked.json")

DEFAULT_MAX_PEERS = int(os.getenv("DEFAULT_MAX_PEERS", "50"))
DEFAULT_MAX_NETWORKS = int(os.getenv("DEFAULT_MAX_NETWORKS", "10"))

HUB_RETRY_COUNT = int(os.getenv("HUB_RETRY_COUNT", "3"))
HUB_RETRY_DELAY = float(os.getenv("HUB_RETRY_DELAY", "1.0"))

VALID_TOPOLOGIES = {"hub-spoke", "mesh", "hub-mesh"}
MESH_DEFAULT_KEEPALIVE = int(os.getenv("MESH_DEFAULT_KEEPALIVE", "25"))
MESH_MAX_PEERS = int(os.getenv("MESH_MAX_PEERS", "50"))


INSECURE_TOKENS = {"changeme", "changeme-super-secret", "secret", "password", "12345", ""}


def check_dependencies() -> None:
    import shutil
    required = [("python3", "Python 3")]
    missing = [name for cmd, name in required if not shutil.which(cmd)]
    if missing:
        raise RuntimeError(
            f"Dependencias faltantes: {', '.join(missing)}. "
            "Instala los paquetes requeridos antes de iniciar el orchestrator."
        )
    log("Verificacion de dependencias: OK")


def validate_tokens_at_startup() -> None:
    errors = []
    if not ADMIN_TOKEN:
        errors.append(
            "ADMIN_TOKEN esta vacio. Genera uno con: openssl rand -hex 32"
        )
    elif ADMIN_TOKEN.lower() in INSECURE_TOKENS:
        errors.append(f"ADMIN_TOKEN tiene un valor inseguro ('{ADMIN_TOKEN}'). Usa un token aleatorio seguro.")

    if not HUB_AGENT_TOKEN:
        errors.append("HUB_AGENT_TOKEN esta vacio. Genera uno con: openssl rand -hex 32")
    elif HUB_AGENT_TOKEN.lower() in INSECURE_TOKENS:
        errors.append(f"HUB_AGENT_TOKEN tiene un valor inseguro ('{HUB_AGENT_TOKEN}').")

    if not HUB_ENDPOINT:
        errors.append("HUB_ENDPOINT esta vacio (ej: 1.2.3.4:51820).")

    if errors:
        for e in errors:
            logger.critical("CONFIGURACION INSEGURA: %s", e)
        raise SystemExit(
            "\n[ERROR CRITICO] El orchestrator no puede arrancar con la configuracion actual.\n"
            "Corrige las variables de entorno listadas arriba.\n"
            "Consulta install.sh para generar tokens seguros automaticamente."
        )
    log("Validacion de tokens de arranque: OK")


def _parse_auto_approve_rules(raw: str) -> dict:
    out: dict = {}
    if not raw:
        return out
    for part in [x.strip() for x in raw.split("|") if x.strip()]:
        if ":" not in part:
            continue
        tag, net = part.split(":", 1)
        out[tag.strip()] = net.strip()
    return out


AUTO_APPROVE_RULES = _parse_auto_approve_rules(AUTO_APPROVE_RULES_RAW)
