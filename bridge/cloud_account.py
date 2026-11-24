"""Local owner-only relay for optional cloud accounts."""
from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import secrets
import tempfile
import threading
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4

from .common import LOG_DIR

_LOCK = threading.RLock()
_ACTION_FIELDS = {
    "capabilities": (), "qr_create": ("consent",), "qr_poll": (),
    "sms_send": ("phone", "consent"), "sms_verify": ("phone", "code", "consent"),
    "sms_bind": ("phone", "code", "consent"), "session": (), "devices": (),
    "rename": ("name",), "revoke": ("id",), "logout": (), "preferences": (),
    "sync": ("version", "preferences"),
}
_PREFERENCES = {"theme": ("system", "light", "dark"), "language": ("auto", "zh-CN", "en")}
_attempt: dict[str, Any] | None = None


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


def endpoint() -> str:
    # Test deployments opt in. A production endpoint is intentionally unset.
    raw = os.environ.get("ANY_TEST_CLOUD_URL", "").rstrip("/")
    try:
        url = urlsplit(raw)
        local = url.hostname in ("localhost", "127.0.0.1", "::1")
        if not url.hostname or url.username or url.password or url.query or url.fragment:
            return ""
        if url.scheme == "https" or (local and url.scheme == "http"):
            return raw
    except ValueError:
        return ""
    return ""


def _state_path() -> Path:
    return Path(LOG_DIR) / "cloud-account.json"


def _save(state: dict[str, Any]) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, mode="w", encoding="utf-8", delete=False) as handle:
        temp = Path(handle.name)
        json.dump(state, handle, ensure_ascii=False)
    try:
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def _state() -> dict[str, Any]:
    try:
        state = json.loads(_state_path().read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        state = None
    if isinstance(state, dict) and state.get("installation") and state.get("name"):
        return state
    label = {"Darwin": "Mac", "Windows": "Windows 设备", "Linux": "Linux 设备"}.get(platform.system(), "AnY 设备")
    state = {"installation": str(uuid4()), "name": label}
    _save(state)
    return state


def _call(url: str, payload: dict[str, Any], token: str):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    test = os.environ.get("ANY_TEST_CLOUD_KEY")
    if test:
        headers["X-AnY-Test-Key"] = test
    request = Request(url, json.dumps(payload).encode(), headers, method="POST")
    try:
        with build_opener(NoRedirect).open(request, timeout=16) as response:
            status, raw = response.status, response.read(65537)
    except HTTPError as response:
        with response:
            status, raw = response.code, response.read(65537)
    if len(raw) > 65536:
        raise ValueError("Cloud response too large")
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError("Invalid cloud response")
    return status, result


def handle(data: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    global _attempt
    action = data.get("action")
    if not isinstance(action, str) or action not in _ACTION_FIELDS:
        return 400, {"error": "invalid_request"}
    url = endpoint()
    if not url:
        if action == "capabilities":
            return 200, {"enabled": False}
        return 503, {"error": "channel_unavailable"}
    payload = {key: data[key] for key in _ACTION_FIELDS[action] if key in data}
    if action == "sync":
        prefs = payload.get("preferences")
        if (not isinstance(prefs, dict) or not prefs
                or any(key not in _PREFERENCES or value not in _PREFERENCES[key] for key, value in prefs.items())
                or type(payload.get("version")) is not int):
            return 400, {"error": "invalid_request"}
    if action == "rename":
        name = payload.get("name")
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 60:
            return 400, {"error": "invalid_request"}
        payload["name"] = name.strip()
    payload["action"] = action
    try:
        with _LOCK:
            state = _state()
            if state.get("endpoint") != url:
                state.pop("token", None)
            old_token = str(state.get("token") or "")
            attempt = _attempt
            if action == "qr_create":
                attempt = {"local_id": secrets.token_urlsafe(18), "endpoint": url, "token": old_token}
                _attempt = attempt
            if action == "qr_poll":
                if (not attempt or attempt["endpoint"] != url or attempt["token"] != old_token
                        or attempt["local_id"] != data.get("attempt") or "id" not in attempt):
                    return 200, {"status": "expired"}
                payload.update(id=attempt["id"], key=attempt["key"])
            if action in ("qr_create", "sms_verify", "sms_bind"):
                payload.update(installation=state["installation"], name=state["name"])
            if action == "session" and not old_token:
                return 401, {"error": "signed_out"}
        status, result = _call(url, payload, old_token)
        with _LOCK:
            state = _state()
            same_session = str(state.get("token") or "") == old_token and state.get("endpoint") == url
            if action == "capabilities" and status == 200:
                result.update(enabled=True, signed_in=same_session and bool(old_token), name=state["name"])
            if status == 401 and old_token and same_session:
                state.pop("token", None)
                _save(state)
            if action == "qr_create" and not result.get("error"):
                if attempt is None or attempt is not _attempt or not result.get("id") or not result.get("key"):
                    return 200, {"status": "expired"}
                attempt.update(id=result.pop("id"), key=result.pop("key"))
                result["attempt"] = attempt["local_id"]
            token = result.pop("token", None)
            if token and action in ("qr_poll", "sms_verify"):
                if action == "qr_poll" and (attempt is not _attempt or (old_token and not same_session)):
                    return 200, {"status": "expired"}
                state.update(token=token, endpoint=url)
                _save(state)
                _attempt = None
                result["signed_in"] = True
            if same_session and result.get("ok"):
                if action == "logout" or (action == "revoke" and result.get("current")):
                    state.pop("token", None)
                    _attempt = None
                    _save(state)
                if action == "rename":
                    state["name"] = payload["name"]
                    _save(state)
        return status, result
    except (OSError, ValueError, URLError):
        return 503, {"error": "cloud_unavailable"}
