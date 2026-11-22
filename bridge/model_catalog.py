"""Model indexes and requested/accepted/observed settings for the selected endpoint."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import subprocess
import threading
import time
from typing import Any

from . import agents, execution, registry
from .common import read_json, write_json

LOCK = threading.RLock()
CACHE: dict[tuple[str, str, str], dict[str, Any]] = {}
TTL = 300
MAX_CATALOG_ENTRIES = 128


def cli_settings(pid):
    """Read the model and effort that Antigravity CLI exposes in its local settings."""
    if pid != "antigravity":
        return "", ""
    settings = read_json(os.path.expanduser("~/.gemini/antigravity-cli/settings.json"), {})
    if not isinstance(settings, dict):
        return "", ""
    model, effort = settings.get("model"), settings.get("effort")
    model = model.strip() if isinstance(model, str) else ""
    effort = effort.strip().lower() if isinstance(effort, str) else ""
    suffix = r"(?:-|\s+\()(low|medium|high|xhigh|max)\)?$"
    match = re.search(suffix, model, re.I)
    if not effort and not match and model.lower().startswith(("orchestrator", "gemini-pro-orchestrator-")):
        orchestrator = settings.get("orchestrator")
        planner = orchestrator.get("planner") if isinstance(orchestrator, dict) else ""
        if isinstance(planner, str):
            match = re.search(suffix, planner.strip(), re.I)
    if not effort and match:
        effort = match[1].lower()
    return model, effort if effort in {"low", "medium", "high", "xhigh", "max"} else ""


def _key(pid, room=None):
    spec = registry.get(pid) or {}
    fields: dict[str, Any] = {"v": 2}
    for key in ("driver", "bin", "env"):
        fields[key] = spec.get(key)
    if spec.get("driver") == "acp" and room is not None:
        fields["workdir"] = room.workdir()
    return registry.LOG_DIR, pid, hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()


def _cached(key):
    with LOCK:
        if key not in CACHE:
            saved=read_json(os.path.join(key[0],"model_catalog.json"),{}) or {}
            row=saved.get(key[1]+":"+key[2],{}) if isinstance(saved,dict) else {}
            CACHE[key]=row if isinstance(row,dict) else {}
        return copy.deepcopy(CACHE[key])


def _store(key, result):
    with LOCK:
        CACHE[key]=result
        path=os.path.join(key[0],"model_catalog.json")
        saved=read_json(path,{}) or {}
        if not isinstance(saved,dict):saved={}
        saved[key[1]+":"+key[2]]=result
        if len(saved) > MAX_CATALOG_ENTRIES:
            saved = dict(list(saved.items())[-MAX_CATALOG_ENTRIES:])
        try:
            write_json(path,saved)
        except OSError:
            CACHE[key]=dict(result,error="索引已获取，但缓存无法保存，请检查应用数据目录",stale=True)


def _flatten_pairs(options):
    result = []
    for option in options or []:
        if not isinstance(option, dict):
            continue
        val = option.get("value")
        if isinstance(val, str):
            name = option.get("name")
            result.append((val, name.strip() if isinstance(name, str) else ""))
        result.extend(_flatten_pairs(option.get("options")))
    return result


def _flatten(options):
    return [val for val, _ in _flatten_pairs(options)]


def _acp_options_to_result(config_options, pid=None, workdir=None):
    model_pairs, levels = [], []
    for option in config_options or ():
        if not isinstance(option, dict):
            continue
        category = option.get("category") or option.get("id")
        if category == "model":
            model_pairs = _flatten_pairs(option.get("options"))
        if category in ("thought_level", "effort"):
            levels = _flatten(option.get("options"))
    if pid == "opencode":
        oc_items, configured_providers = agents.opencode_catalog(workdir)
        if configured_providers and "opencode" not in configured_providers:
            filtered = [(m, lbl) for m, lbl in model_pairs if "/" in m and m.split("/", 1)[0] in configured_providers]
            if filtered:
                model_pairs = filtered
            elif oc_items:
                model_pairs = [(m, "") for m, _ in oc_items]
    models = [val for val, _ in model_pairs]
    model_labels = {val: lbl for val, lbl in model_pairs if lbl and lbl != val}
    return {
        "models": models,
        "efforts_by_model": {model: levels for model in models},
        "model_labels": model_labels,
        "effort_supported": bool(levels),
        "source": "ACP 会话声明",
    }


def record_acp_options(room, pid, config_options):
    wd = room.workdir() if room is not None else None
    result = _acp_options_to_result(config_options, pid=pid, workdir=wd)
    if not result["models"] and not result["effort_supported"]:
        return
    result.update(checked_at=time.time(), error="")
    _store(_key(pid, room), result)


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_ZW_RE = re.compile(r"[\u200b-\u200d\ufeff]")
_DISPLAY_EFFORT_SUFFIX_RE = re.compile(r"-(extra-high|xhigh|high|medium|low|max|minimal|none)$", re.I)
_MODEL_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{1,120}$")


def display_model_name(model: str, model_labels: dict[str, str] | None) -> str:
    text = str(model or "").strip()
    if not text:
        return ""
    labels = model_labels or {}
    if text in labels and labels[text]:
        return labels[text]
    base = _DISPLAY_EFFORT_SUFFIX_RE.sub("", text)
    if base and base != text and base in labels and labels[base]:
        return labels[base]
    return text
_KNOWN_PLAIN_MODELS = frozenset({"auto", "fast", "opus", "sonnet", "haiku", "fable"})
_NOISE_PREFIXES = (
    "available ", "model:", "models:", "usage:", "tip:", "note:",
    "error:", "warning:", "loading", "fetching", "default model:",
    "you are not", "please ", "run ", "press ", "select ", "current ",
)
_VARIANT_RE = re.compile(r"^(.*?)-(none|minimal|low|medium|high|xhigh|extra-high|max)(-fast)?$", re.I)
_PAREN_EFFORT_RE = re.compile(r"\s*\((?:None|Minimal|Low|Medium|High|XHigh|Extra High|Max)\)\s*$", re.I)
_TRAILING_EFFORT_RE = re.compile(
    r"\s+(?:None|Minimal|Low|Medium|High|XHigh|Extra High|Max)"
    r"((?:\s+Fast)?(?:\s+(?:No\s+)?Thinking)?(?:\s+\(NO ZDR\))?)\s*$",
    re.I,
)


def _clean_model_label(label, fast=False):
    text = _ZW_RE.sub("", str(label or ""))
    text = re.sub(r"\s*\(default\)\s*$", "", text, flags=re.I).strip()
    if not text:
        return ""
    text = _PAREN_EFFORT_RE.sub("", text).strip()
    text = _TRAILING_EFFORT_RE.sub(lambda m: m.group(1) or "", text).strip()
    return re.sub(r"\s{2,}", " ", text)


def _parse_cli_model_rows(stdout):
    rows, seen = [], set()
    in_table = False
    for raw in (stdout or "").splitlines():
        line = _ZW_RE.sub("", _ANSI_RE.sub("", raw)).strip()
        if not line or line.startswith(("-", "=", "#", ">")):
            continue
        low = line.lower()
        if low in ("model", "models", "available models", "available models:") or low.startswith("available models"):
            in_table = True
            continue
        if any(low.startswith(p) for p in _NOISE_PREFIXES):
            continue
        bulleted = line.startswith(("* ", "• "))
        if bulleted:
            line = line[2:].strip()
            if not line:
                continue
        elif line.startswith(("*", "•")):
            continue
        label = ""
        rest = ""
        if "\t" in line:
            parts = line.split("\t", 1)
            token = parts[0].strip().strip(",:;")
            label = re.sub(r"\s*\(default\)\s*$", "", parts[1].strip(), flags=re.I).strip()
        elif " - " in line:
            parts = line.split(" - ", 1)
            token = parts[0].strip().strip(",:;")
            cand = re.sub(r"\s*\(default\)\s*$", "", parts[1].strip(), flags=re.I).strip()
            if cand.lower() != "default":
                label = cand
        else:
            parts = line.split(None, 1)
            token = parts[0].strip().strip(",:;")
            rest = parts[1].strip() if len(parts) > 1 else ""
            if rest and not re.fullmatch(r"\((?:default|current)\)|\[.*\]", rest, re.I):
                continue
        if token.startswith("http"):
            continue
        has_sep_or_digit = any(ch in token for ch in "/.-:") or any(ch.isdigit() for ch in token)
        if not has_sep_or_digit:
            if not (in_table or bulleted or token.lower() in _KNOWN_PLAIN_MODELS):
                continue
        if _MODEL_TOKEN_RE.match(token) and token not in seen:
            seen.add(token)
            rows.append((token, label))
    return rows


def _parse_cli_models(stdout):
    return [token for token, _ in _parse_cli_model_rows(stdout)]


_AGY_NO_EFFORT_MODELS = frozenset({"gemini-pro-orchestrator-g1-pro"})


def _apply_agy_default_efforts(models, efforts_by_model, fallback_efforts, explicit_model_efforts=None):
    """Fill preset efforts for Antigravity models that have no collapsed effort-suffix variants."""
    changed = False
    if not fallback_efforts:
        return False
    explicit = explicit_model_efforts or {}
    for model in models or ():
        if (
            not efforts_by_model.get(model)
            and not _VARIANT_RE.match(model)
            and model not in _AGY_NO_EFFORT_MODELS
            and model not in explicit
        ):
            efforts_by_model[model] = list(fallback_efforts)
            changed = True
    return changed


def _collapse_effort_variants(rows):
    """Collapse <model>-<effort>[-fast] variants into base model + per-model efforts."""
    base_counts: dict[str, int] = {}
    for token, _ in rows:
        m = _VARIANT_RE.match(token)
        if m:
            key = m.group(1) + (m.group(3) or "")
            base_counts[key] = base_counts.get(key, 0) + 1
    models: list[str] = []
    efforts_by_model: dict[str, list[str]] = {}
    model_labels: dict[str, str] = {}
    for token, label in rows:
        m = _VARIANT_RE.match(token)
        if m:
            fast = bool(m.group(3))
            base_key = m.group(1) + (m.group(3) or "")
            eff = m.group(2).lower()
            if eff == "extra-high":
                eff = "xhigh"
            if base_counts.get(base_key, 0) > 1:
                if base_key not in efforts_by_model:
                    models.append(base_key)
                    efforts_by_model[base_key] = []
                if eff not in efforts_by_model[base_key]:
                    efforts_by_model[base_key].append(eff)
                clean = _clean_model_label(label, fast=fast)
                if clean and base_key not in model_labels:
                    model_labels[base_key] = clean
                continue
        if token not in efforts_by_model:
            models.append(token)
            efforts_by_model[token] = []
        clean = re.sub(r"\s*\(default\)\s*$", "", label, flags=re.I).strip() if label else ""
        if clean:
            model_labels[token] = clean
    for key, levels in list(efforts_by_model.items()):
        efforts_by_model[key] = agents._sort_efforts(levels)
    return {
        "models": models,
        "efforts_by_model": efforts_by_model,
        "model_labels": model_labels,
        "effort_supported": any(bool(v) for v in efforts_by_model.values()),
        "source": "CLI 模型查询",
    }


def _run_probe(exe, subargs, spec, room, timeout=10):
    env = dict(os.environ)
    for k, v in (spec.get("env") or {}).items():
        env[str(k)] = str(v)
    return subprocess.run(
        list(exe) + list(subargs),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        cwd=room.workdir() if room is not None else None,
        env=env,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
    )


def _probe_cli_catalog(pid, spec, room):
    names = {str(pid or "").strip().lower()}
    exe = registry.exe_of(spec)
    for part in list(exe or []) + list(spec.get("bin") or []):
        stem = os.path.splitext(os.path.basename(str(part)))[0].lower()
        if stem and stem not in ("node", "cmd", "powershell", "pwsh"):
            names.add(stem)
    cwd = room.workdir() if room is not None else None
    if "grok" in names:
        cached_grok = agents.grok_catalog()
        efforts_by_model = dict(cached_grok)
        models = [slug for slug, _ in cached_grok]
        cli_rows = []
        if exe:
            try:
                proc = _run_probe(exe, ["models"], spec, room, timeout=12)
                if proc.returncode == 0:
                    cli_rows = _parse_cli_model_rows(proc.stdout)
            except Exception:
                cli_rows = []
        for token, _ in cli_rows:
            if token not in efforts_by_model:
                models.append(token)
                efforts_by_model[token] = agents.effort_options(pid, token)
        if not models:
            return None
        source = "Grok 模型缓存" if cached_grok else "CLI 模型查询"
        return {"models": models, "efforts_by_model": efforts_by_model, "model_labels": {}, "source": source}
    if "opencode" in names:
        oc_items, configured_providers = agents.opencode_catalog(cwd)
        oc_map = dict(oc_items)
        cli_rows = []
        if exe:
            try:
                proc = _run_probe(exe, ["models"], spec, room, timeout=15)
                if proc.returncode == 0:
                    cli_rows = _parse_cli_model_rows(proc.stdout)
            except Exception:
                cli_rows = []
        models = []
        for m in oc_map:
            if m not in models:
                models.append(m)
        filter_by_provider = bool(configured_providers) and "opencode" not in configured_providers
        for token, _ in cli_rows:
            prov = token.split("/", 1)[0] if "/" in token else ""
            if filter_by_provider and prov not in configured_providers:
                continue
            if token not in models:
                models.append(token)
        if not models:
            return None
        source = "OpenCode 配置与 CLI" if (cli_rows and oc_items) else ("CLI 模型查询" if cli_rows else "本机 OpenCode 配置")
        return {"models": models, "efforts_by_model": {}, "model_labels": {}, "source": source}
    if not exe:
        return None
    if names & {"antigravity", "agy"}:
        try:
            proc = _run_probe(exe, ["models"], spec, room, timeout=15)
        except Exception:
            return None
        if proc.returncode != 0:
            return None
        rows = _parse_cli_model_rows(proc.stdout)
        if not rows:
            return None
        res = _collapse_effort_variants(rows)
        fallback_efforts = agents._sort_efforts(spec.get("efforts") or [])
        if _apply_agy_default_efforts(res["models"], res["efforts_by_model"], fallback_efforts):
            res["effort_supported"] = True
        return res
    if names & {"cursor", "cursor-agent", "agent"}:
        try:
            proc = _run_probe(exe, ["--list-models"], spec, room, timeout=15)
        except Exception:
            return None
        if proc.returncode != 0:
            return None
        rows = _parse_cli_model_rows(proc.stdout)
        return _collapse_effort_variants(rows) if rows else None
    if names & {"qoder", "qodercli", "qoderclicn", "qodercn"}:
        try:
            proc = _run_probe(exe, ["--list-models"], spec, room, timeout=25)
        except Exception:
            return None
        has_header = any(ln.strip().lower() in ("model", "models") for ln in (proc.stdout or "").splitlines())
        if proc.returncode != 0 and not has_header:
            return None
        rows = _parse_cli_model_rows(proc.stdout)
        if not rows:
            return None
        models = [token for token, _ in rows]
        return {"models": models, "efforts_by_model": {m: agents.effort_options(pid, m) for m in models},
                "model_labels": {}, "source": "CLI 模型查询"}
    return None


def _probe_cli_models(pid, spec, room):
    res = _probe_cli_catalog(pid, spec, room)
    return list(res["models"]) if res and res.get("models") else []


def refresh(room, pid):
    spec = registry.get(pid) or {}
    if pid not in room.ais:
        raise ValueError("此 Agent 不在会话中")
    if room.busy_for(pid):
        raise ValueError("此 AI 正在运行或排队，请结束后再刷新模型索引")
    with room.ai_lock(pid):
        if room.busy_for(pid) or execution.binding(room, pid)["phase"] != "ready":
            raise ValueError("此 AI 正在运行或交接，请结束后再刷新模型索引")
        if execution.binding(room, pid)["endpoint"] == "desktop":
            return capabilities(room, pid)
        key = _key(pid, room)
        try:
            explicit = agents.user_explicit_models(spec)
            if spec.get("driver") == "codex":
                cmd, env = agents.codex_launch(None, "discuss")
                process = agents.CodexServer(cmd, env)
                try:
                    process.start()
                    rows: list[dict[str, Any]] = []
                    cursor = None
                    for _ in range(20):
                        response = process.request("model/list", {"limit": 100, "cursor": cursor}, timeout=20)
                        rows.extend(response.get("data") or [])
                        cursor = response.get("nextCursor")
                        if not cursor:
                            break
                finally:
                    process.stop()
                models, efforts = [], {}
                for row in rows:
                    if row.get("hidden") is True:
                        continue
                    slug = row.get("model") or row.get("id")
                    if not isinstance(slug, str):
                        continue
                    models.append(slug)
                    efforts[slug] = [item.get("reasoningEffort") or item.get("effort") for item in row.get("supportedReasoningEfforts", []) if isinstance(item, dict)]
                    efforts[slug] = [value for value in efforts[slug] if isinstance(value, str)]
                result: dict[str, Any] = {"models": models, "efforts_by_model": efforts, "model_labels": {}, "source": "Codex model/list"}
            elif spec.get("driver") == "claude":
                models = agents.model_options("claude")
                result = {
                    "models": models,
                    "efforts_by_model": {m: agents.effort_options("claude", m) for m in models},
                    "model_labels": {},
                    "effort_supported": True,
                    "source": "本机 Claude 配置",
                }
            elif spec.get("driver") == "acp":
                from . import acp
                acp_proc: acp.AcpProcess | None = None
                try:
                    command = acp._cmd_for(spec)
                    if not command:
                        raise ValueError("找不到 ACP 程序")
                    acp_proc = acp.AcpProcess(pid, command, room.workdir(), env=spec.get("env"), init_timeout=12)
                    acp_proc.ensure_session(None, [], timeout=15)
                    result = _acp_options_to_result(acp_proc.config_options, pid=pid, workdir=room.workdir())
                finally:
                    if acp_proc is not None:
                        acp_proc.close()
            else:
                probed = _probe_cli_catalog(pid, spec, room) if spec.get("driver") == "cli" else None
                if probed and probed.get("models"):
                    models = list(dict.fromkeys(list(probed["models"]) + explicit))
                    base_cap = agents.model_capabilities(pid)
                    efforts_map = dict(probed.get("efforts_by_model") or {})
                    if base_cap["effort_supported"] or probed.get("effort_supported"):
                        for m in explicit:
                            efforts_map.setdefault(m, agents.effort_options(pid, m))
                    else:
                        efforts_map = {}
                    result = {
                        "models": models,
                        "efforts_by_model": efforts_map,
                        "model_labels": dict(probed.get("model_labels") or {}),
                        "source": probed.get("source") or "CLI 模型查询",
                    }
                    if "effort_supported" in probed:
                        result["effort_supported"] = bool(probed["effort_supported"])
                else:
                    previous = _cached(key)
                    if previous.get("models") and pid in ("antigravity", "agy", "cursor", "cursor-agent", "agent",
                                                          "qoder", "qodercli", "qoderclicn", "qodercn", "grok", "opencode"):
                        raise ValueError("执行端未返回模型列表，保留上次索引；也可在 Agent 设置中补充")
                    models = list(dict.fromkeys(agents.model_options(pid) + explicit))
                    base_cap = agents.model_capabilities(pid)
                    result = {
                        "models": models,
                        "efforts_by_model": {model: agents.effort_options(pid, model) for model in models} if base_cap["effort_supported"] else {},
                        "model_labels": {},
                        "source": "本机配置" if (models and not explicit) else "应用内 Agent 设置",
                    }
            if not result["models"]:
                raise ValueError("执行端未返回模型列表，保留上次索引；也可在 Agent 设置中补充")
            result.update(checked_at=time.time(), error="")
            _store(key, result)
        except Exception as error:
            previous = _cached(key)
            previous.update(error=str(error)[:500], stale=True)
            _store(key, previous)
        return capabilities(room, pid)


def capabilities(room, pid):
    base = agents.model_capabilities(pid)
    if room is not None:
        owner = execution.binding(room, pid)
        if owner["endpoint"] == "desktop":
            from . import native_session
            actual = native_session.observed(pid, room.meta.get(pid + "_session") or "")
            return dict(base, model_supported=False, effort_supported=False, models=[actual["model"]] if actual["model"] else [],
                        efforts_by_model={}, model_labels={}, observed=actual, source="桌面原生会话", checked_at=None, stale=False, error="",
                        note="此桌面 MCP 接入支持接单与读取实际模型，未提供模型/effort 写入接口；可继续参与，切换控件受限。")
    spec = registry.get(pid) or {}
    cached = _cached(_key(pid, room))
    default_source = (
        "本机 Codex 缓存" if spec.get("driver") == "codex"
        else "本机 Claude 配置" if spec.get("driver") == "claude"
        else "本机 Grok 缓存" if (pid == "grok" and base["models"])
        else "本机 OpenCode 配置" if (pid == "opencode" and base["models"])
        else "本机 Cursor 配置" if (pid == "cursor" and base["models"])
        else "应用内 Agent 设置"
    )
    explicit = agents.user_explicit_models(spec)
    models = list(dict.fromkeys(list(cached["models"]) + explicit)) if cached.get("models") else base["models"]
    effort_map = dict(base["efforts_by_model"], **(cached.get("efforts_by_model") or {}))
    if pid in ("antigravity", "agy"):
        _apply_agy_default_efforts(
            models,
            effort_map,
            agents._sort_efforts(spec.get("efforts") or []),
            spec.get("model_efforts") or {},
        )
    # Explicit per-model preferences remain editable, including an empty effort list.
    effort_map.update(spec.get("model_efforts") or {})
    model_labels = dict(cached.get("model_labels") or {})
    model_supported = base["model_supported"] or (spec.get("driver") == "acp" and bool(cached.get("models")))
    effort_supported = base["effort_supported"] or bool(cached.get("effort_supported"))
    note = "模型列表来自执行端查询；可在 Agent 设置中补充自定义模型，账户权限以实际调用为准。" if cached.get("models") else base["note"]
    return dict(base, note=note, models=models, efforts_by_model=effort_map, model_labels=model_labels,
                source=cached.get("source") or default_source,
                checked_at=cached.get("checked_at"), error=cached.get("error", ""),
                stale=bool(cached.get("error") or (cached.get("checked_at") and time.time() - cached["checked_at"] > TTL)),
                model_supported=model_supported, effort_supported=effort_supported)


def request_id(room, pid):
    model, effort = room.effective_models(pid)
    return hashlib.sha256(json.dumps([model, effort, execution.version(room, pid)]).encode()).hexdigest()[:24]


def state(room, pid):
    owner = execution.binding(room, pid)
    selected = room.effective_models(pid)
    requested = {"model": selected[0], "effort": selected[1], "revision": request_id(room, pid)}
    saved = room.meta.get("model_state", {}).get(pid) or {}
    status = saved.get("status", "pending") if saved.get("request_id") == requested["revision"] else "pending"
    if owner["endpoint"] == "desktop":
        status = "read_only"
    return {"requested": requested, "accepted": saved.get("accepted"), "observed": saved.get("observed"),
            "apply_status": status, "apply_error": saved.get("error", "") if status == "failed" else ""}


def accepted(room, pid, revision, source, observed=None):
    if revision != request_id(room, pid):
        return
    model, effort = room.effective_models(pid)
    with room.lock:
        old = copy.deepcopy(room.meta.get("model_state", {}))
        room.meta.setdefault("model_state", {})[pid] = {"request_id": revision, "status": "applied", "error": "",
            "accepted": {"model": model, "effort": effort, "source": source, "at": time.time()}, "observed": observed}
        try:
            room.save_meta()
        except OSError:
            room.meta["model_state"] = old
            raise


def result(room, pid, revision, ok, text, sid):
    if execution.binding(room, pid)["endpoint"] == "desktop" or revision != request_id(room, pid):
        return
    if ok:
        from . import native_session
        actual = native_session.observed(pid, sid) if native_session.provider(pid) else None
        accepted(room, pid, revision, "使用指定设置的调用已完成", actual)
    elif any(marker in text for marker in ("ACP 拒绝", "设置接口", "model_not_found", "unsupported model", "invalid model")):
        with room.lock:
            row = room.meta.setdefault("model_state", {}).setdefault(pid, {})
            row.update(request_id=revision, status="failed", error=text[:500])
            room.save_meta()
