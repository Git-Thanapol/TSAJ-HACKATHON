"""M3: outbound webhook (inspection.completed) to the local Yard System receiver.

The ONLY intentional network call in the system, and it stays on localhost.
Delivery is best-effort: a dead subscriber must never break the sign-off.
"""
import httpx


def fire(url: str, event_type: str, payload: dict, timeout: float = 3.0) -> dict:
    """POST {event, payload} to the subscriber. Returns a delivery report."""
    try:
        r = httpx.post(url, json={"event": event_type, "payload": payload}, timeout=timeout)
        return {"url": url, "delivered": r.is_success, "status_code": r.status_code}
    except httpx.HTTPError as exc:
        return {"url": url, "delivered": False, "error": str(exc)}
