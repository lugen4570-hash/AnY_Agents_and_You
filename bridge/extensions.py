# -*- coding: utf-8 -*-
"""Global extensions discovery (skills / plugins / MCP), safe folder opening, and local skill import."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from typing import Any

from . import agents, projects, registry
from .common import in_dir

HOME = os.path.expanduser("~")

SAFE_SKILL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
_ROOT_INDEX: dict[str, dict[str, Any]] = {}


class ExtensionError(Exception):
    def __init__(self, code: int, message: str, *, conflict_name: str = ""):
        super().__init__(message)
        self.code = code
        self.message = message
        self.conflict_name = conflict_name


def _resolve_project_workdir(project_id: str, conversations: list[dict[str, Any]] | None = None) -> str:
    pid = str(project_id or "").strip()
    if not pid:
        return ""
    for proj in projects.listing(conversations or []):
        if proj.get("id") == pid:
            wd = str(proj.get("workdir") or "").strip()
            if wd and os.path.isdir(wd):
                return wd
    return ""


def _read_skill_desc(skill_dir: str) -> str:
    md_path = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(md_path):
        return ""
    try:
        with open(md_path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read(4096)
    except OSError:
        return ""
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for line in lines[1:40]:
            if line.strip() == "---":
                break
            m = re.match(r"^\s*description\s*:\s*(.+?)\s*$", line)
            if m:
                return m.group(1).strip().strip("\"'")[:160]
    for line in lines:
        s = line.strip()
        if s and not s.startswith("#") and s != "---":
            return s[:160]
    return ""


def _scan_skill_dir(root_dir: str, *, agent_id: str, scope: str, tags: list[str] | None = None) -> list[dict[str, Any]]:
    if not root_dir or not os.path.isdir(root_dir):
        return []
    out: list[dict[str, Any]] = []
    try:
        entries = sorted(os.listdir(root_dir))
    except OSError:
        return []
    for name in entries:
        if not SAFE_SKILL_NAME.match(name):
            continue
        full = os.path.join(root_dir, name)
        if not os.path.isdir(full) or not os.path.isfile(os.path.join(full, "SKILL.md")):
            continue
        item: dict[str, Any] = {
            "id": f"skill:{agent_id}:{scope}:{name}",
            "kind": "skill",
            "name": name,
            "description": _read_skill_desc(full),
            "source": full,
            "agent_ids": [agent_id],
            "scope": scope,
        }
        if tags:
            item["tags"] = list(tags)
        out.append(item)
    return out


def _codex_home() -> str:
    return os.environ.get("CODEX_HOME") or agents.CODEX_HOME


def _antigravity_skill_dirs() -> list[str]:
    home = os.path.expanduser("~") or HOME
    candidates = [
        os.path.join(home, ".gemini", "skills"),
        os.path.join(home, ".gemini", "config", "skills"),
    ]
    return [p for p in candidates if os.path.isdir(p)]


def _build_skill_roots(project_id: str, project_workdir: str, local_host: bool) -> list[dict[str, Any]]:
    roots: list[dict[str, Any]] = [
        {
            "id": "codex:user",
            "agent_id": "codex",
            "scope": "user",
            "path": os.path.join(_codex_home(), "skills"),
            "can_open": bool(local_host),
            "can_import": bool(local_host),
        }
    ]
    if project_id and project_workdir:
        roots.append({
            "id": f"codex:project:{project_id}",
            "agent_id": "codex",
            "scope": "project",
            "path": os.path.join(project_workdir, ".codex", "skills"),
            "can_open": bool(local_host),
            "can_import": bool(local_host),
        })
    for idx, agy_dir in enumerate(_antigravity_skill_dirs()):
        roots.append({
            "id": f"antigravity:host:{idx}",
            "agent_id": "antigravity",
            "scope": "user",
            "path": agy_dir,
            "can_open": bool(local_host),
            "can_import": False,
        })
    for r in roots:
        _ROOT_INDEX[r["id"]] = dict(r)
    return roots


def list_extensions(
    project_id: str = "",
    *,
    refresh: bool = False,
    local_host: bool = True,
    conversations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return {items, skill_roots} following the agreed /api/extensions contract."""
    _ = refresh  # Scan directly on each request so refresh=1 always reflects live disk state.
    pid = str(project_id or "").strip()
    project_workdir = _resolve_project_workdir(pid, conversations) if pid else ""
    skill_roots = _build_skill_roots(pid, project_workdir, local_host)

    items: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    def push(item: dict[str, Any]) -> None:
        key = item["id"]
        if key not in seen_ids:
            seen_ids.add(key)
            items.append(item)

    # 1. Codex skills (user + optional project)
    codex_home = _codex_home()
    for sk in _scan_skill_dir(os.path.join(codex_home, "skills"), agent_id="codex", scope="user"):
        push(sk)
    for sk in _scan_skill_dir(os.path.join(os.path.expanduser("~") or HOME, ".agents", "skills"), agent_id="codex", scope="user"):
        push(sk)
    if project_workdir:
        for sk in _scan_skill_dir(os.path.join(project_workdir, ".codex", "skills"), agent_id="codex", scope="project"):
            push(sk)
        for sk in _scan_skill_dir(os.path.join(project_workdir, ".agents", "skills"), agent_id="codex", scope="project"):
            push(sk)

    # 2. Antigravity host-managed skills (read-only)
    if registry.get("antigravity") or _antigravity_skill_dirs():
        for agy_dir in _antigravity_skill_dirs():
            for sk in _scan_skill_dir(agy_dir, agent_id="antigravity", scope="host", tags=["host_managed"]):
                push(sk)

    # 3. Codex plugins
    for plug in agents.codex_plugins():
        push({
            "id": f"plugin:codex:{plug['id']}",
            "kind": "plugin",
            "name": plug.get("label") or plug["id"],
            "description": "Codex 插件总开关（会议内可单独控制）",
            "source": "codex",
            "agent_ids": ["codex"],
            "scope": "user",
            "default_on": bool(plug.get("enabled", True)),
        })

    # 4. Codex MCP servers
    off_cfg = set(agents.codex_mcp_off_by_config())
    for name in agents.codex_mcp_names():
        push({
            "id": f"mcp:codex:{name}",
            "kind": "mcp",
            "name": name,
            "description": "Codex config.toml 中配置的 MCP 服务",
            "source": os.path.join(codex_home, "config.toml"),
            "agent_ids": ["codex"],
            "scope": "user",
            "default_on": name not in off_cfg,
        })

    return {"items": items, "skill_roots": skill_roots}


def _open_os_folder(path: str) -> None:
    if sys.platform == "win32":
        getattr(os, "startfile")(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def open_folder(
    root_id: str,
    *,
    local_host: bool = True,
    conversations: list[dict[str, Any]] | None = None,
    opener: Any = None,
) -> dict[str, Any]:
    if not local_host:
        raise ExtensionError(403, "只能在运行 AnY 的本机上打开目录。")
    rid = str(root_id or "").strip()
    if not rid:
        raise ExtensionError(400, "缺少 root_id。")
    # Refresh roots index if needed (including project root if root_id encodes project id).
    if rid not in _ROOT_INDEX:
        pid = rid.split("codex:project:", 1)[1] if rid.startswith("codex:project:") else ""
        list_extensions(pid, local_host=local_host, conversations=conversations)
    root = _ROOT_INDEX.get(rid)
    if not root or not root.get("can_open"):
        raise ExtensionError(404, "未找到允许打开的技能目录。")
    path = root["path"]
    os.makedirs(path, exist_ok=True)
    fn = opener or _open_os_folder
    try:
        fn(path)
    except Exception as error:
        raise ExtensionError(500, f"打开目录失败：{error}") from error
    return {"ok": True, "path": path}


def import_skill(
    *,
    agent_id: str,
    scope: str,
    project_id: str = "",
    source_path: str,
    local_host: bool = True,
    conversations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not local_host:
        raise ExtensionError(403, "只能在运行 AnY 的本机上导入本地技能。")
    aid = str(agent_id or "").strip()
    sc = str(scope or "").strip()
    src_raw = str(source_path or "").strip().strip('"')
    if aid != "codex":
        raise ExtensionError(400, "首版仅支持导入 Codex 本地技能；其他 Agent 技能由原软件管理。")
    if sc not in ("user", "project"):
        raise ExtensionError(400, "导入范围必须是 user（个人）或 project（项目）。")
    if not src_raw:
        raise ExtensionError(400, "请提供本地技能文件夹路径。")
    src = os.path.normpath(os.path.expandvars(os.path.expanduser(src_raw)))
    if not os.path.isabs(src) or not os.path.isdir(src) or os.path.islink(src):
        raise ExtensionError(400, "技能文件夹不存在或路径无效。")
    if not os.path.isfile(os.path.join(src, "SKILL.md")):
        raise ExtensionError(400, "该文件夹中未找到 SKILL.md，无法作为技能导入。")

    skill_name = os.path.basename(src.rstrip("\\/"))
    if not SAFE_SKILL_NAME.match(skill_name):
        raise ExtensionError(400, f"技能文件夹名称「{skill_name}」包含不支持的字符。")

    if sc == "project":
        pid = str(project_id or "").strip()
        if not pid:
            raise ExtensionError(400, "项目范围导入必须提供 project_id。")
        wd = _resolve_project_workdir(pid, conversations)
        if not wd:
            raise ExtensionError(404, "找不到对应的项目工作目录。")
        target_root = os.path.join(wd, ".codex", "skills")
    else:
        target_root = os.path.join(_codex_home(), "skills")

    os.makedirs(target_root, exist_ok=True)
    dest = os.path.normpath(os.path.join(target_root, skill_name))
    if not in_dir(dest, target_root):
        raise ExtensionError(400, "目标路径校验失败。")
    if os.path.lexists(dest):
        raise ExtensionError(409, f"已存在同名技能「{skill_name}」，已保留原技能。", conflict_name=skill_name)
    if in_dir(dest, src):
        raise ExtensionError(400, "不能将技能目录导入到其自身子目录中。")

    try:
        shutil.copytree(src, dest, symlinks=False)
    except OSError as error:
        raise ExtensionError(500, f"复制技能目录失败：{error}") from error

    item = {
        "id": f"skill:{aid}:{sc}:{skill_name}",
        "kind": "skill",
        "name": skill_name,
        "description": _read_skill_desc(dest),
        "source": dest,
        "agent_ids": [aid],
        "scope": sc,
    }
    return {"item": item}
