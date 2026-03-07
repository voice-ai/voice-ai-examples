import json
import re
import sys
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import telnyx


# =============================================================================
# CONFIGURATION
# =============================================================================
TELNYX_API_KEY = "YOUR_TELNYX_API_KEY"
TELNYX_PHONE_NUMBER = "+12137339768"
TELNYX_APP_NAME = "tts-telnyx-test"
TELNYX_WEBHOOK_URL = "https://voiceai.ngrok.app/telnyx/webhook"
TELNYX_HD_VOICE_ENABLED = True


TELNYX_API_BASE = "https://api.telnyx.com/v2"


def _normalize_phone_number(phone_number: str) -> str:
    normalized = re.sub(r"[^\d+]", "", phone_number)
    if not normalized.startswith("+"):
        raise SystemExit(f"TELNYX_PHONE_NUMBER must be E.164 formatted, got: {phone_number}")
    return normalized


def _api_request(
    method: str,
    path: str,
    payload: Optional[Dict[str, Any]] = None,
    query: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    url = f"{TELNYX_API_BASE}{path}"
    if query:
        url = f"{url}?{urlencode(query)}"

    body = None
    headers = {
        "Authorization": f"Bearer {TELNYX_API_KEY}",
        "Accept": "application/json",
    }
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request) as response:
            raw = response.read()
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Telnyx API {method} {path} failed: {exc.code} {error_body}") from exc
    except URLError as exc:
        raise SystemExit(f"Failed to reach Telnyx API: {exc}") from exc

    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def _item_to_dict(item: Any) -> Dict[str, Any]:
    if isinstance(item, dict):
        return item
    if hasattr(item, "to_dict"):
        return item.to_dict()
    if hasattr(item, "__dict__"):
        return {k: v for k, v in vars(item).items() if not k.startswith("_")}
    raise SystemExit(f"Unsupported Telnyx SDK object type: {type(item)!r}")


def ensure_call_control_application() -> Dict[str, Any]:
    response = _api_request(
        "GET",
        "/call_control_applications",
        query={"page[size]": 100},
    )
    apps = response.get("data", [])
    existing = next((app for app in apps if app.get("application_name") == TELNYX_APP_NAME), None)

    payload = {
        "application_name": TELNYX_APP_NAME,
        "webhook_event_url": TELNYX_WEBHOOK_URL,
        "webhook_api_version": "2",
    }

    if existing is None:
        created = _api_request("POST", "/call_control_applications", payload=payload)
        return created.get("data", {})

    if (
        existing.get("webhook_event_url") != TELNYX_WEBHOOK_URL
        or str(existing.get("webhook_api_version", "")) != "2"
    ):
        updated = _api_request(
            "PATCH",
            f"/call_control_applications/{existing['id']}",
            payload=payload,
        )
        return updated.get("data", {})

    return existing


def get_phone_number_record(client: Any) -> Dict[str, Any]:
    normalized = _normalize_phone_number(TELNYX_PHONE_NUMBER)
    numbers = client.phone_numbers.list(filter={"phone_number": normalized.lstrip("+")})
    items = getattr(numbers, "data", None) or []
    if not items:
        raise SystemExit(f"Phone number not found in Telnyx account: {normalized}")

    for item in items:
        data = _item_to_dict(item)
        if data.get("phone_number") == normalized:
            return data
    return _item_to_dict(items[0])


def update_phone_number(phone_number_id: str, connection_id: str) -> Dict[str, Any]:
    payload = {
        "connection_id": connection_id,
        "hd_voice_enabled": TELNYX_HD_VOICE_ENABLED,
    }
    updated = _api_request("PATCH", f"/phone_numbers/{phone_number_id}", payload=payload)
    return updated.get("data", {})


def main() -> int:
    if not TELNYX_API_KEY:
        raise SystemExit("TELNYX_API_KEY is required")
    if not TELNYX_PHONE_NUMBER:
        raise SystemExit("TELNYX_PHONE_NUMBER is required")
    if not TELNYX_WEBHOOK_URL:
        raise SystemExit("TELNYX_WEBHOOK_URL is required")

    client = telnyx.Telnyx(api_key=TELNYX_API_KEY)

    application = ensure_call_control_application()
    application_id = application.get("id")
    if not application_id:
        raise SystemExit("Failed to resolve Telnyx call control application ID")

    phone_record = get_phone_number_record(client)
    phone_number_id = phone_record.get("id")
    if not phone_number_id:
        raise SystemExit(f"Failed to resolve Telnyx phone number ID for {TELNYX_PHONE_NUMBER}")

    updated_number = update_phone_number(phone_number_id=phone_number_id, connection_id=application_id)

    summary = {
        "application_id": application_id,
        "application_name": application.get("application_name", TELNYX_APP_NAME),
        "webhook_event_url": application.get("webhook_event_url", TELNYX_WEBHOOK_URL),
        "phone_number": updated_number.get("phone_number", phone_record.get("phone_number", TELNYX_PHONE_NUMBER)),
        "phone_number_id": updated_number.get("id", phone_number_id),
        "connection_id": updated_number.get("connection_id", application_id),
        "hd_voice_enabled": updated_number.get("hd_voice_enabled", TELNYX_HD_VOICE_ENABLED),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
