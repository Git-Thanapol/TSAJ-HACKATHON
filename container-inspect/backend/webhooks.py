"""M3: outbound webhook (inspection.completed) to the local Yard System tab.

The ONLY intentional network call in the system, and it stays on localhost.
"""


def fire(event_type: str, payload: dict) -> None:
    raise NotImplementedError("M3: fire inspection.completed to subscriber_url")
