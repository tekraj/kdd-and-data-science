import json


def parse_retrain_event(payload: str) -> tuple[int, int] | None:
    try:
        event = json.loads(payload)
        first_id = event.get("first_id")
        last_id = event.get("last_id")
        if first_id is None or last_id is None:
            print(f"[ML] Ignoring malformed event payload: {event}")
            return None
        return int(first_id), int(last_id)
    except Exception as err:
        print(f"[ML] Failed to parse retrain event payload: {err}")
        return None
