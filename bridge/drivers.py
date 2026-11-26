# -*- coding: utf-8 -*-
r"""通用驱动：把"叫一个 AI"这件事从具体厂商里拆出来。

agents.call_ai 只管内置的两个（claude / codex，各有专门的一套）。这里管另外两种，都靠注册表里的配置驱动：

    driver = "cli"   起一个命令行程序，把这一轮的话交给它，读它的输出
    driver = "http"  把这一轮 POST 给自己的服务，拿它的回复（自己的 harness 接会议室走这条）

两种都返回跟 agents.call_ai 一样的东西：(ok, text, session_id, edits)。

命令行的拼法（顺序固定，配置里怎么写就怎么排）：
    bin + args.base + (干活 ? args.work : args.read) + (有会话 ? args.resume : args.new) + 每个图片的 images
占位符：{prompt} {prompt_file} {session} {model} {effort} {cwd} {room} {room_title} {goal} {bridge_url} {bridge_key} {path}
args 里出现了 {prompt} 或 {prompt_file} 就走对应位置；没出现时看 prompt 字段："stdin" 写进标准输入，"arg" 接在最后。
"""
import json, os, re, subprocess, tempfile, urllib.error, urllib.request

from . import agents, registry
from .agents import bridge_url
from .common import run_stream, timeout_for

PH = re.compile(r"\{([a-z_]+)\}")
_WIN_BATCH_CMD_LIMIT = 6500
_WIN_CREATEPROCESS_CMD_LIMIT = 28000
_STDIN_PRINT_AGENTS = frozenset({
    "cursor", "cursor-agent", "agent",
    "qoder", "qodercn", "qodercli", "qoderclicn",
    "claude", "gemini",
})


def _fmt(s, ctx):
    """把 {xxx} 换成值；不认识的占位符原样留着（免得用户写错就崩）。"""
    return PH.sub(lambda m: str(ctx.get(m.group(1), m.group(0))), s)


def _get_path(obj, path):
    """{"a": {"b": 1}} 取 "a.b"；取不到返回 None。"""
    cur = obj
    for k in [x for x in str(path or "").split(".") if x]:
        if isinstance(cur, dict):
            cur = cur.get(k)
        elif isinstance(cur, list) and k.isdigit() and int(k) < len(cur):
            cur = cur[int(k)]
        else:
            return None
    return cur


def _ctx(pid, spec, room, mode, session_id):
    key = room.keys.get(pid, "") if room is not None else ""
    wd = room.workdir() if room is not None else os.getcwd()
    return {"cwd": wd, "session": session_id or "",
            "room": room.id if room is not None else "", "room_title": room.title() if room is not None else "",
            "session_name": room.session_name() if (room is not None and hasattr(room, "session_name")) else "",
            "goal": room.goal() if room is not None else "", "sid": session_id or "",
            "bridge_url": bridge_url("/mcp"), "bridge_key": key, "speaker": pid, "mode": mode,
            "title": room.title() if room is not None else ""}


# ===================== 命令行 =====================
def _build_arg_seq(spec, base_ctx, session_id, mode):
    a = spec["args"]
    seq = list(a["base"])
    seq += list(a["work"] if mode == "work" else a["read"])
    if base_ctx.get("model"):
        seq += list(a.get("model") or [])
    if base_ctx.get("effort"):
        seq += list(a.get("effort") or [])
    if base_ctx.get("session_name"):
        seq += list(a.get("title") or [])
    seq += list(a["resume"] if session_id else a["new"])
    return seq


def _compose(spec, base_ctx, session_id, images, mode, prompt):
    seq = _build_arg_seq(spec, base_ctx, session_id, mode)
    out = []
    if images and spec["images"]:
        ictx = dict(base_ctx)
        ictx["path"] = ""
        for p in images:
            ictx["path"] = p
            out += [_fmt(x, ictx) for x in spec["images"]]
    out = [_fmt(x, dict(base_ctx, prompt=prompt)) for x in seq] + out
    has_prompt = any(("{prompt}" in x or "{prompt_file}" in x) for x in seq)
    if not has_prompt and spec["prompt"] == "arg":
        out.append(prompt)
    return out, has_prompt


def _write_prompt_temp_file(text):
    """Write prompt text into a temporary UTF-8 file and return its path."""
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", prefix="any-prompt-", suffix=".txt", delete=False
    ) as handle:
        handle.write(text)
        return handle.name


def _win_cmd_limit(cmd):
    if cmd and str(cmd[0]).lower().endswith((".cmd", ".bat")):
        return _WIN_BATCH_CMD_LIMIT
    return _WIN_CREATEPROCESS_CMD_LIMIT


def _candidate_agent_names(pid, exe):
    names = {str(pid or "").strip().lower()}
    for part in exe or ():
        stem = os.path.splitext(os.path.basename(str(part)))[0].lower()
        if stem and stem != "node":
            names.add(stem)
    return names


def _prepare_prompt_delivery(pid, exe, spec, ctx, session_id, images, mode, prompt, *, cmd_limit=None):
    cleanup = []
    compose_ctx = dict(ctx)
    seq = _build_arg_seq(spec, compose_ctx, session_id, mode)
    if prompt is not None and any("{prompt_file}" in x for x in seq):
        tmp_path = _write_prompt_temp_file(str(prompt))
        cleanup.append(tmp_path)
        compose_ctx["prompt_file"] = tmp_path
    args, has_prompt = _compose(spec, compose_ctx, session_id, images, mode, prompt)
    stdin_text = "" if has_prompt else (prompt if spec["prompt"] == "stdin" else "")
    cmd = list(exe) + args
    limit = cmd_limit if cmd_limit is not None else (_win_cmd_limit(cmd) if os.name == "nt" else None)
    if limit is not None and not stdin_text and prompt and len(subprocess.list2cmdline(cmd)) > limit:
        names = _candidate_agent_names(pid, exe)
        if "grok" in names and "--prompt-file" not in args:
            idx = next((i for i, val in enumerate(args) if prompt in val), None)
            if idx is not None:
                tmp_path = _write_prompt_temp_file(args[idx])
                cleanup.append(tmp_path)
                if idx > 0 and args[idx - 1] in ("-p", "--single"):
                    args = args[: idx - 1] + ["--prompt-file", tmp_path] + args[idx + 1 :]
                else:
                    args = args[:idx] + ["--prompt-file", tmp_path] + args[idx + 1 :]
        elif (names & _STDIN_PRINT_AGENTS) and ("-p" in args or "--print" in args or "gemini" in names):
            idx = next((i for i, val in enumerate(args) if val == prompt), None)
            if idx is not None:
                args = args[:idx] + args[idx + 1 :]
                stdin_text = prompt
    return args, stdin_text, cleanup


def _pos_int(v):
    if isinstance(v, bool) or v is None:
        return 0
    try:
        n = int(v)
        return n if n > 0 else 0
    except (TypeError, ValueError):
        return 0


def _usage_from_dict(u):
    if not isinstance(u, dict):
        return 0, 0
    cache = u.get("cache") if isinstance(u.get("cache"), dict) else {}
    inp = (
        _pos_int(u.get("input_tokens"))
        or _pos_int(u.get("inputTokens"))
        or _pos_int(u.get("prompt_tokens"))
        or _pos_int(u.get("promptTokenCount"))
        or _pos_int(u.get("input"))
        or _pos_int(u.get("prompt"))
    )
    cr = (
        _pos_int(u.get("cache_read_input_tokens"))
        or _pos_int(u.get("cachedReadTokens"))
        or _pos_int(cache.get("read"))
    )
    cw = (
        _pos_int(u.get("cache_creation_input_tokens"))
        or _pos_int(u.get("cachedWriteTokens"))
        or _pos_int(cache.get("write"))
    )
    out = (
        _pos_int(u.get("output_tokens"))
        or _pos_int(u.get("outputTokens"))
        or _pos_int(u.get("completion_tokens"))
        or _pos_int(u.get("candidatesTokenCount"))
        or _pos_int(u.get("output"))
        or _pos_int(u.get("candidates"))
    )
    total = (
        _pos_int(u.get("total_tokens"))
        or _pos_int(u.get("totalTokens"))
        or _pos_int(u.get("totalTokenCount"))
        or _pos_int(u.get("total"))
    )
    summed = inp + cr + cw + out
    used = max(summed, total) if (summed or total) else 0
    win = (
        _pos_int(u.get("contextWindow"))
        or _pos_int(u.get("context_window"))
        or _pos_int(u.get("modelContextWindow"))
        or _pos_int(u.get("ctx_win"))
        or _pos_int(u.get("context_size"))
        or _pos_int(u.get("contextSize"))
    )
    return used, win


def extract_ctx_usage(obj, res):
    """Extract real token usage / context window fields into res without estimating."""
    if not isinstance(obj, dict) or res is None:
        return
    if obj.get("parent_tool_use_id"):
        return
    used = (
        _pos_int(obj.get("ctx_used"))
        or _pos_int(obj.get("context_used"))
        or _pos_int(obj.get("contextUsed"))
    )
    win = (
        _pos_int(obj.get("ctx_win"))
        or _pos_int(obj.get("context_window"))
        or _pos_int(obj.get("contextWindow"))
        or _pos_int(obj.get("modelContextWindow"))
        or _pos_int(obj.get("context_size"))
        or _pos_int(obj.get("contextSize"))
        or _pos_int(obj.get("window"))
    )
    if obj.get("sessionUpdate") == "usage_update":
        used = used or _pos_int(obj.get("used"))
        win = win or _pos_int(obj.get("size"))
    mu = obj.get("modelUsage")
    if isinstance(mu, dict):
        best = max(
            (v for v in mu.values() if isinstance(v, dict)),
            key=lambda v: _pos_int(v.get("cacheReadInputTokens")) + _pos_int(v.get("inputTokens")),
            default=None,
        )
        if best:
            win = win or _pos_int(best.get("contextWindow"))
    candidates = [
        obj.get("usage"),
        (obj.get("message") or {}).get("usage") if isinstance(obj.get("message"), dict) else None,
        (obj.get("_meta") or {}).get("usage") if isinstance(obj.get("_meta"), dict) else None,
        (obj.get("result") or {}).get("usage") if isinstance(obj.get("result"), dict) else None,
        (obj.get("part") or {}).get("tokens") if isinstance(obj.get("part"), dict) else None,
        obj.get("tokens"),
        obj.get("usageMetadata"),
        (obj.get("result") or {}).get("usageMetadata") if isinstance(obj.get("result"), dict) else None,
    ]
    stats = obj.get("stats")
    if isinstance(stats, dict):
        candidates.append(stats)
        models = stats.get("models")
        if isinstance(models, dict):
            best_toks = None
            best_total = -1
            for mval in models.values():
                if not isinstance(mval, dict):
                    continue
                toks = mval.get("tokens")
                if isinstance(toks, dict):
                    score = _pos_int(toks.get("total")) or _pos_int(toks.get("prompt"))
                    if score > best_total:
                        best_total = score
                        best_toks = toks
            if best_toks is not None:
                candidates.append(best_toks)
    for cand in candidates:
        c_used, c_win = _usage_from_dict(cand)
        if c_used and not used:
            used = c_used
        if c_win and not win:
            win = c_win
    if used:
        res["ctx_used"] = used
    if win:
        res["ctx_win"] = win


def _parse_ndjson(p, stdout, res=None):
    """一行一个 JSON（很多 CLI 的 --format json 是这样）：文本拼起来，会话 id 取第一个非空的。"""
    parts, sess, fallback = [], None, None
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        extract_ctx_usage(obj, res)
        if not sess and p["session"]:
            v = _get_path(obj, p["session"])
            if isinstance(v, (str, int)) and str(v):
                sess = str(v)
        if fallback is None and p["text"] == "result.response" and isinstance(obj.get("response"), str):
            fallback = obj["response"]
        if p["filter"] and any(_get_path(obj, k) != v for k, v in p["filter"].items()):
            continue
        if isinstance(res, dict):
            rdict = obj.get("result") if isinstance(obj.get("result"), dict) else obj
            err = rdict.get("error")
            if isinstance(err, str) and err.strip():
                res["error"] = err.strip()
            denied = rdict.get("denied_actions")
            if isinstance(denied, list) and denied:
                names = []
                for item in denied:
                    if isinstance(item, dict):
                        nm = str(item.get("display_name") or item.get("action") or "").strip()
                        if nm and nm not in names:
                            names.append(nm)
                    elif isinstance(item, str) and item.strip() and item.strip() not in names:
                        names.append(item.strip())
                if names:
                    res["denied_actions"] = names
        if p["text"]:
            v = _get_path(obj, p["text"])
            if isinstance(v, str) and v:
                parts.append(v)
    if not parts and fallback:
        parts.append(fallback)
    return (p["join"].join(parts) if parts else ""), sess


def _parse(spec, stdout, res=None):
    """按配置从输出里取回复文本和会话 id。返回 (text, session)。"""
    p = spec["parse"]
    text, sess = "", None
    if p["type"] == "ndjson":
        text, sess = _parse_ndjson(p, stdout, res)
    elif p["type"] == "json":
        data = None
        try:
            data = json.loads(stdout)
        except Exception:
            for line in reversed(stdout.splitlines()):   # 有的 CLI 打一行 JSON，前后还夹着别的输出
                line = line.strip()
                if not line.startswith("{"):
                    continue
                try:
                    data = json.loads(line)
                    break
                except Exception:
                    continue
        if isinstance(data, dict) or isinstance(data, list):
            if isinstance(data, dict):
                extract_ctx_usage(data, res)
            if p["text"]:
                got = _get_path(data, p["text"])
                text = got if isinstance(got, str) else ("" if got is None else json.dumps(got, ensure_ascii=False))
            else:
                text = stdout
            if p["session"]:
                got = _get_path(data, p["session"])
                sess = str(got) if isinstance(got, (str, int)) else None
        else:
            text = stdout
    else:
        text = stdout
    if not sess and p["session_regex"]:
        m = re.search(p["session_regex"], stdout, re.M)
        if m:
            sess = m.group(1) if m.groups() else m.group(0)
    return (text or "").strip(), sess


_AGY_SUFFIX_RE = re.compile(r"^(.*?)-(none|minimal|low|medium|high|xhigh|max)$", re.I)


def _resolve_cli_model_effort(pid, exe, spec, model, effort):
    names = _candidate_agent_names(pid, exe)
    if names & {"antigravity", "agy"}:
        if model in ("gemini-pro-orchestrator-g1-pro", "gpt-oss-120b-medium"):
            return model, ""
        if model and effort:
            m = _AGY_SUFFIX_RE.match(model)
            if m:
                model = m.group(1)
        return model, effort
    if (names & {"cursor", "cursor-agent", "agent"}) and not (spec.get("args") or {}).get("effort"):
        if model and effort and not _AGY_SUFFIX_RE.match(model):
            mapped = "extra-high" if (effort == "xhigh" and model in ("gpt-5.5", "gpt-5.5-fast")) else effort
            if model.endswith("-fast"):
                model = f"{model[:-5]}-{mapped}-fast"
            else:
                model = f"{model}-{mapped}"
            return model, ""
    return model, effort


def _extract_assistant_content(content):
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = [
            item["text"].strip()
            for item in content
            if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str) and item["text"].strip()
        ]
        return " ".join(parts).strip()
    return ""


def _live_text_from_cli_line(spec, line):
    """Extract only human-readable interim status text from a streamed CLI line."""
    p = spec.get("parse") or {}
    ptype = p.get("type") or "text"
    s = (line or "").strip()
    if not s:
        return ""
    if ptype not in ("ndjson", "json"):
        return s
    if not s.startswith("{"):
        return ""
    try:
        obj = json.loads(s)
    except Exception:
        return ""
    if not isinstance(obj, dict):
        return ""

    text_path = p.get("text")
    flt = p.get("filter")
    if text_path and (not flt or all(_get_path(obj, k) == v for k, v in flt.items())):
        val = _get_path(obj, text_path)
        if isinstance(val, str) and val.strip():
            return val.strip()

    delta = obj.get("delta")
    if isinstance(delta, str) and delta.strip():
        return delta.strip()
    if isinstance(delta, dict) and isinstance(delta.get("text"), str) and delta["text"].strip():
        return delta["text"].strip()

    if obj.get("type") == "text" and isinstance(obj.get("part"), dict):
        pt = obj["part"].get("text")
        if isinstance(pt, str) and pt.strip():
            return pt.strip()

    msg = obj.get("message")
    if isinstance(msg, dict) and msg.get("role") == "assistant":
        extracted = _extract_assistant_content(msg.get("content"))
        if extracted:
            return extracted

    su = obj.get("step_update")
    if isinstance(su, dict):
        for key in ("thinking", "text", "message"):
            sv = su.get(key)
            if isinstance(sv, str) and sv.strip():
                return sv.strip()

    return ""


def call_cli(pid, spec, prompt, session_id, images, mode, room):
    exe = registry.exe_of(spec)
    if not exe:
        return False, "找不到 %s 命令（要装：%s）" % (pid, "、".join(spec["bin"])), session_id, []
    ctx = _ctx(pid, spec, room, mode, session_id)
    extra = room.effective_models(pid) if room is not None else tuple(spec["default"])
    ctx["model"], ctx["effort"] = _resolve_cli_model_effort(pid, exe, spec, extra[0] or "", extra[1] or "")
    args, stdin_text, cleanup = _prepare_prompt_delivery(pid, exe, spec, ctx, session_id, images, mode, prompt)
    cmd = list(exe) + args
    if pid == "antigravity" and stdin_text and "--input-format" in args and args[args.index("--input-format") + 1] == "stream-json":
        # agy requires user-message NDJSON on stdin; long prompts must not enter Windows argv.
        stdin_text = json.dumps({"event": "user", "message": {"role": "user", "content": [
            {"type": "text", "text": stdin_text}
        ]}}, ensure_ascii=False) + "\n"
    env = dict(spec.get("env") or {})
    buf = []

    def on_line(line):
        buf.append(line)
        if room is not None:
            live = _live_text_from_cli_line(spec, line)
            if live:
                room.push_live(pid, {"live": live})   # 仅推可读状态文本，避免暴露原始协议 JSON

    try:
        rc, so, se, to = run_stream(cmd, stdin_text, on_line, timeout_for(mode, pid), cwd=ctx["cwd"], env=env,
                                    reg=(lambda p: getattr(room, "register_process", room.procs.__setitem__)(pid, p)) if room is not None else None)
    finally:
        for path in cleanup:
            try:
                os.unlink(path)
            except OSError:
                # Best-effort cleanup of temporary prompt files.
                pass
    stdout = "\n".join(buf) if buf else (so or "")
    if to:
        from .common import timeout_text
        return False, timeout_text(pid, to, mode), session_id, []
    res = {}
    text, sess = _parse(spec, stdout, res)
    if session_id:
        resume_missing = pid == "antigravity" and any(
            session_id.lower() in line and "conversation" in line and "not found" in line
            for line in (se or "").lower().splitlines()
        )
        if (sess and sess != session_id) or resume_missing:
            message = "%s 无法接续原会话，已保留原绑定。要新开请先重置会话接续。" % pid
            if sess and sess != session_id and len(sess) <= 100 and sess.isprintable():
                message += " 执行端返回了另一会话 ID：%s。" % sess
            return False, message, session_id, []
    if rc != 0 and not text:
        tail = "\n".join((se or "").strip().splitlines()[-6:])
        return False, "%s 出错了（退出码 %s）\n%s" % (pid, rc, tail), session_id, []
    if not text:
        if res.get("error"):
            return False, "%s 出错了：%s" % (pid, res["error"]), session_id, []
        if res.get("denied_actions"):
            return False, "%s 没有返回内容（非交互模式下被权限拦截：%s）" % (pid, "、".join(res["denied_actions"])), session_id, []
        return False, "%s 没有返回内容" % pid, session_id, []
    if room is not None and res.get("ctx_used"):
        room.note_ctx(pid, res)
    return True, text, (sess or session_id), []


# ===================== HTTP =====================
def call_http(pid, spec, prompt, session_id, images, mode, room):
    """把这一轮 POST 给用户自己的服务。请求 / 回复的格式见 docs/PROVIDERS.md。

    请求：{"room","room_title","speaker","mode","prompt","session","workdir","goal","images","bridge_url","bridge_key"}
    回复：{"text": "...", "session": "可选的新会话 id"}
    """
    idle, total = timeout_for(mode, pid)
    body = {"room": room.id if room is not None else "", "room_title": room.title() if room is not None else "",
            "speaker": pid, "mode": mode, "prompt": prompt, "session": session_id or "",
            "workdir": room.workdir() if room is not None else os.getcwd(),
            "goal": room.goal() if room is not None else "", "images": list(images or ()),
            "bridge_url": bridge_url("/mcp"), "bridge_key": (room.keys.get(pid, "") if room is not None else "")}
    if room is not None:
        from .access import permissions
        body["permissions"] = permissions(room, pid)
    model, effort = room.effective_models(pid) if room is not None else tuple(spec["default"])
    body["model"], body["effort"] = model, effort
    headers = {"Content-Type": "application/json"}
    headers.update(spec.get("headers") or {})
    if spec.get("token"):
        headers["Authorization"] = "Bearer " + spec["token"]
    req = urllib.request.Request(spec["endpoint"], data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=total) as r:
            raw = r.read().decode("utf-8", "replace")
            ctype = (r.headers.get("Content-Type") or "").lower()
    except urllib.error.HTTPError as e:
        tail = e.read().decode("utf-8", "replace")[:400] if hasattr(e, "read") else ""
        return False, "%s 的服务返回 %s\n%s" % (pid, e.code, tail), session_id, []
    except Exception as e:
        return False, "连不上 %s 的服务（%s）：%s" % (pid, spec["endpoint"], e), session_id, []
    text, sess, res = raw.strip(), None, {}
    if "json" in ctype or raw.lstrip().startswith("{"):
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                text = str(data.get("text") or data.get("message") or "").strip()
                sess = str(data["session"]) if data.get("session") else None
                extract_ctx_usage(data, res)
        except Exception:
            pass
    if not text:
        if res.get("error"):
            return False, "%s 出错了：%s" % (pid, res["error"]), session_id, []
        if res.get("denied_actions"):
            return False, "%s 没有返回内容（非交互模式下被权限拦截：%s）" % (pid, "、".join(res["denied_actions"])), session_id, []
        return False, "%s 没有返回内容" % pid, session_id, []
    if room is not None and res.get("ctx_used"):
        room.note_ctx(pid, res)
    return True, text, (sess or session_id), []


# ===================== 分派 =====================
def standby_worker(pid):
    """这个联系人现在是不是有桌面端在 MCP 待命。

    有的话优先派给它：桌面软件里的 agent 自己会执行并回复，比再起一个 CLI 更贴近用户看到的东西。
    待命端掉线就自然回落到本地 CLI，不需要用户改配置。
    """
    try:
        from .members import broker
        st = broker.status(pid)
    except Exception:
        return None
    return st if (st.get("automatic") and st.get("transport") == "standby") else None


def call(pid, prompt, session_id=None, images=(), mode=None, room=None):
    """叫一个 AI。跟 agents.call_ai 同签名，room.ai_caller 指的就是这里。"""
    spec = registry.get(pid)
    if not spec:                       # 没在注册表里（理论上不会）：退回内置处理
        return agents.call_ai(pid, prompt, session_id, images, mode, room)
    driver = spec["driver"]
    if mode is None:
        mode = room.mode() if room is not None else "discuss"
    if room is not None:
        from . import execution
        owner = execution.binding(room, pid)
        if owner["phase"] != "ready":
            return False, "会话正在交接执行端，请先完成或取消接管", session_id, []
        if owner["endpoint"] == "desktop":
            from .members import broker
            return broker.call(pid, prompt, session_id, mode, room)
    if driver in ("claude", "codex"):
        return agents.call_ai(pid, prompt, session_id, images, mode, room)
    try:
        if driver == "acp":
            from . import acp
            return acp.call(pid, spec, prompt, session_id, images, mode, room)
        if driver == "external":
            from .members import broker
            if room is None:
                return False, "请先加入会话并连接成员执行端", session_id, []
            return broker.call(pid, prompt, session_id, mode, room)
        if driver == "cli":
            return call_cli(pid, spec, prompt, session_id, images, mode, room)
        if driver == "http":
            if spec.get("http_protocol"):
                from . import direct_model
                model = room.effective_models(pid)[0] if room is not None else spec["default"][0]
                try:
                    return True, direct_model.reply(spec, prompt, model), None, []
                except ValueError as error:
                    return False, str(error), None, []
            return call_http(pid, spec, prompt, session_id, images, mode, room)
    except Exception as e:
        return False, "%s 调用失败：%s" % (pid, e), session_id, []
    return False, "%s 的 driver %r 不认识" % (pid, driver), session_id, []
