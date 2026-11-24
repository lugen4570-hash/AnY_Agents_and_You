"""Plain-text model contacts using an OpenAI-compatible Chat Completions endpoint."""
import base64
import json
import os
from urllib import error, parse, request

PROTOCOL = "openai_chat"
MAX_RESPONSE_BYTES = 2 * 1024 * 1024


def endpoint(value):
    original = str(value or "").strip()
    try:
        url = parse.urlsplit(original)
        host = url.hostname
        url.port  # Validate an explicitly supplied port.
    except ValueError:
        raise ValueError("模型服务地址格式不正确") from None
    if (not host or url.username is not None or url.password is not None or url.query or url.fragment
            or any(ch.isspace() or ord(ch) < 32 for ch in original) or "\\" in original):
        raise ValueError("请填写完整的模型服务地址，地址里不要带账号、参数或 API Key")
    if url.scheme != "https" and not (url.scheme == "http" and host in {"localhost", "127.0.0.1", "::1"}):
        raise ValueError("模型服务地址需使用 HTTPS，本机服务可使用 HTTP")
    path = url.path.rstrip("/") or "/v1"
    if not path.endswith("/chat/completions"):
        path += "/chat/completions"
    return parse.urlunsplit((url.scheme, url.netloc, path, "", ""))


def _windows_secret(data, protect):
    import ctypes
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_byte))]

    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    result = Blob()
    api = ctypes.windll.crypt32.CryptProtectData if protect else ctypes.windll.crypt32.CryptUnprotectData
    api.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                    ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    api.restype = wintypes.BOOL
    if not api(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(result)):
        raise ValueError("无法访问当前 Windows 用户保存的 API Key，请重新填写后保存")
    try:
        return ctypes.string_at(result.data, result.size)
    finally:
        local_free = ctypes.windll.kernel32.LocalFree
        local_free.argtypes = [ctypes.c_void_p]
        local_free.restype = ctypes.c_void_p
        local_free(result.data)


def key_from_config(raw):
    value = raw.get("token")
    if not value and raw.get("token_dpapi") and os.name == "nt":
        try:
            value = _windows_secret(base64.b64decode(raw["token_dpapi"], validate=True), False).decode("ascii")
        except (TypeError, ValueError) as exc:
            raise ValueError("无法读取已保存的 API Key，请重新填写后保存") from exc
    value = str(value or "").strip()
    if not value or len(value) > 4096 or any(not 33 <= ord(ch) <= 126 for ch in value):
        raise ValueError("请填写有效的 API Key")
    return value


def stored_config(raw, key):
    saved = dict(raw)
    if os.name == "nt":
        saved["token_dpapi"] = base64.b64encode(_windows_secret(key.encode("ascii"), True)).decode("ascii")
        saved.pop("token", None)
    else:
        saved["token"] = key  # The application's atomic JSON writer creates a private file.
    return saved


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def reply(spec, text, model=None, timeout=25):
    key = spec["token"]
    body = {"model": model or spec["default"][0], "messages": [{"role": "user", "content": text}]}
    req = request.Request(spec["endpoint"], data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                          headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    try:
        with request.build_opener(_NoRedirect).open(req, timeout=timeout) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except error.HTTPError as exc:
        code = exc.code
        exc.close()
        if code in (401, 403):
            message = "服务拒绝认证，请检查 API Key 和模型权限"
        elif code in (400, 404):
            message = "服务或模型不可用，请检查服务地址和模型名称"
        elif code in (402, 429):
            message = "服务限流或额度不足，请检查服务商账户"
        elif 300 <= code < 400:
            message = "服务地址发生重定向，请填写最终地址"
        else:
            message = "模型服务暂时无法回复"
        raise ValueError("%s（HTTP %d）" % (message, code)) from None
    except (error.URLError, TimeoutError, OSError):
        raise ValueError("无法连接模型服务或等待超时，请检查服务地址和网络") from None
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError("模型回复太大，无法读取")
    try:
        content = json.loads(raw)["choices"][0]["message"]["content"]
    except (KeyError, TypeError, IndexError, ValueError):
        raise ValueError("服务回复不符合 Chat Completions 协议，请检查服务地址") from None
    if not isinstance(content, str) or not content.strip():
        raise ValueError("模型没有返回可读的文字回复")
    return content.strip().replace(key, "[API Key 已隐藏]")
