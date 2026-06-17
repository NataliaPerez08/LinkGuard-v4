"""
Cliente RPC hacia hub-agent via XML-RPC.
Llamadas al hub-agent en /RPC2 y helpers de allowed IPs.
"""

import ipaddress
import time
import xmlrpc.client  # nosec B411
from typing import Optional, Dict, Any, List
from xmlrpc.client import ServerProxy  # nosec B411

from . import config, state


def get_hub_client() -> ServerProxy:
    return ServerProxy(config.HUB_AGENT_URL, allow_none=True)


def _hub_call_with_retry(method: str, *args) -> Any:
    last_exc = None
    for attempt in range(config.HUB_RETRY_COUNT):
        try:
            c = get_hub_client()
            return getattr(c, method)(*args)
        except Exception as e:
            last_exc = e
            if attempt < config.HUB_RETRY_COUNT - 1:
                delay = config.HUB_RETRY_DELAY * (2 ** attempt)
                config.log(f"hub-agent '{method}' fallo (intento {attempt+1}/{config.HUB_RETRY_COUNT}): {e}. Reintentando en {delay:.1f}s...")
                time.sleep(delay)
    raise RuntimeError(f"hub-agent '{method}' fallo tras {config.HUB_RETRY_COUNT} intentos: {last_exc}")


def hub_apply_peer(pub: str, allowed_ips_csv: str, endpoint: str = "") -> bool:
    return bool(_hub_call_with_retry("hub.apply_peer", config.HUB_AGENT_TOKEN, pub, allowed_ips_csv, endpoint))


def hub_remove_peer(pub: str) -> bool:
    return bool(_hub_call_with_retry("hub.remove_peer", config.HUB_AGENT_TOKEN, pub))


def hub_ping() -> bool:
    try:
        return _hub_call_with_retry("hub.health", config.HUB_AGENT_TOKEN) in {"ok", "pong"}
    except Exception:
        return False


def _peer_all_allowed_ips(peer: Dict[str, Any]) -> List[str]:
    ips = []
    peer_ip = str(peer.get("ip") or "").strip()
    if peer_ip:
        ips.append(config.WG_PEER_ALLOWED_FMT.replace("{ip}", peer_ip.split("/")[0]))
    return ips


def _is_public_endpoint(ep: str) -> bool:
    if not ep:
        return False
    host = ep.rsplit(":", 1)[0].strip("[]")
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_global
    except ValueError:
        return True


def _get_wg_endpoint(pub_key: str) -> str:
    """Retrieve the real WG-learned endpoint (with correct NAT port) from the hub's WireGuard interface."""
    try:
        peers = _hub_call_with_retry("hub.list_mesh_peers", config.HUB_AGENT_TOKEN, "")
    except Exception:
        return ""
    for p in peers:
        if p.get("public_key") == pub_key:
            ep = p.get("endpoint")
            if ep:
                return ep
    return ""


def _hub_apply_peer_allowed_ips(peer_id: str) -> None:
    with state.LOCK_PEERS:
        peer = state.STATE["peers"].get(peer_id)
    if not peer:
        return
    ips = _peer_all_allowed_ips(peer)
    csv = ", ".join(ips)
    ep = str(peer.get("endpoint") or "")
    pub_key = str(peer.get("public_key") or "")
    if csv:
        final_ep = ""
        if _is_public_endpoint(ep):
            # On every re-push the self-reported port may be stale (NAT peers).
            # Preserve the WG-learned port if it differs from self-reported.
            wg_ep = _get_wg_endpoint(pub_key)
            if wg_ep and _is_public_endpoint(wg_ep) and ":" in wg_ep:
                wg_port = wg_ep.rsplit(":", 1)[1]
                ep_ip = ep.rsplit(":", 1)[0].strip("[]")
                final_ep = f"{ep_ip}:{wg_port}"
            else:
                final_ep = ep
        try:
            hub_apply_peer(pub_key, csv, endpoint=final_ep)
        except Exception as e:
            config.log(f"ERROR: No pude actualizar allowed_ips para {peer_id}: {e}")
        config.log(f"Actualizados allowed_ips para {peer_id}: {len(ips)} IPs" + (f", endpoint={final_ep}" if final_ep else ""))
