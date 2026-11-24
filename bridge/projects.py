"""Persisted projects, with stable groups for existing conversations."""
import hashlib
import os
import subprocess
import threading
import uuid

from .common import LOG_DIR, PROJECT, read_json, write_json
from .workspace import git

LOCK = threading.RLock()

MACOS_FOLDER_PROMPT = '''try
    return POSIX path of (choose folder with prompt "选择 AnY 项目的工作文件夹")
on error messageText number errorNumber
    if errorNumber is -128 then return ""
    error messageText number errorNumber
end try'''


def choose_macos_workdir():
    result = subprocess.run(
        ["/usr/bin/osascript", "-e", MACOS_FOLDER_PROMPT],
        check=True, capture_output=True, encoding="utf-8", timeout=180,
    )
    path = result.stdout.removesuffix("\n")
    return os.path.normpath(path) if path else None


def legacy_id(workdir):
    return "folder-" + hashlib.sha256(os.path.normcase(os.path.abspath(workdir or PROJECT)).encode()).hexdigest()[:16]


def listing(conversations):
    with LOCK:
        saved = read_json(os.path.join(LOG_DIR, "projects.json")) or []
        result = {p["id"]: p for p in saved}
        for r in conversations:
            pid = r.get("project") or legacy_id(r["workdir"])
            if pid not in result:
                wd = r["workdir"]
                result[pid] = {"id": pid, "name": os.path.basename(wd.rstrip("\\/")) or wd, "workdir": wd}
        return [dict(p, workdirs=p.get("workdirs") or [p["workdir"]]) for p in result.values()]


def _settings(name, workdir, workdirs, existing=()):
    name = str(name or "").strip()[:60]
    if workdirs is None:
        workdirs = [workdir]
    if not isinstance(workdirs, list) or not workdirs or any(not isinstance(wd, str) for wd in workdirs):
        raise ValueError("请填写至少一个工作文件夹")
    known = {os.path.normcase(wd) for wd in existing}
    folders: dict[str, str] = {}
    for value in workdirs:
        raw = value.strip().strip('"')
        if not raw:
            raise ValueError("请填写工作文件夹完整路径")
        wd = os.path.normpath(os.path.expandvars(os.path.expanduser(raw)))
        key = os.path.normcase(wd)
        if not os.path.isabs(wd) or (key not in known and not os.path.isdir(wd)):
            raise ValueError("工作文件夹不存在：" + wd)
        folders.setdefault(key, wd)
    if not name:
        raise ValueError("请填写项目名称和存在的工作文件夹完整路径")
    paths = list(folders.values())
    return {"name": name, "workdir": paths[0], "workdirs": paths}


def create(name, workdir=None, workdirs=None):
    settings = _settings(name, workdir, workdirs)
    with LOCK:
        path = os.path.join(LOG_DIR, "projects.json")
        saved = read_json(path) or []
        p = {"id": uuid.uuid4().hex, **settings}
        saved.append(p)
        os.makedirs(LOG_DIR, exist_ok=True)
        write_json(path, saved)
        return p


def update(pid, name, workdirs, conversations):
    with LOCK:
        project = next((p for p in listing(conversations) if p["id"] == pid), None)
        if project is None:
            return None
        settings = _settings(name, None, workdirs, project["workdirs"])
        path = os.path.join(LOG_DIR, "projects.json")
        saved = {p["id"]: p for p in read_json(path) or []}
        saved[pid] = {**project, **settings}
        os.makedirs(LOG_DIR, exist_ok=True)
        write_json(path, list(saved.values()))
        return saved[pid]


def workspaces(project):
    folders = project.get("workdirs") or [project["workdir"]]
    result = {os.path.normcase(wd): {"path": wd, "branch": ""} for wd in folders if os.path.isdir(wd)}
    for folder in list(result.values()):
        cwd = folder["path"]
        try:
            head = git(["symbolic-ref", "--quiet", "--short", "HEAD"], cwd, check=False)
            if head.returncode == 0:
                folder["branch"] = os.fsdecode(head.stdout).rstrip("\r\n")
            entries = git(["worktree", "list", "--porcelain", "-z"], cwd)
        except (OSError, RuntimeError, subprocess.TimeoutExpired):
            continue
        for entry in entries.split(b"\0\0"):
            fields = entry.split(b"\0")
            if not fields[0].startswith(b"worktree ") or b"bare" in fields:
                continue
            wd = os.path.normpath(os.fsdecode(fields[0].removeprefix(b"worktree ")))
            if not os.path.isabs(wd) or not os.path.isdir(wd) or any(f.startswith(b"prunable") for f in fields):
                continue
            branch_prefix = b"branch refs/heads/"
            branch = next((os.fsdecode(f.removeprefix(branch_prefix)) for f in fields if f.startswith(branch_prefix)), "")
            result.setdefault(os.path.normcase(wd), {"path": wd, "branch": branch})
    return list(result.values())


def delete(pid, conversations=None):
    with LOCK:
        path = os.path.join(LOG_DIR, "projects.json")
        saved = read_json(path) or []
        remaining = [project for project in saved if project["id"] != pid]
        if len(remaining) != len(saved):
            write_json(path, remaining)
            return True, ""
        if any((room.get("project") or legacy_id(room["workdir"])) == pid for room in (conversations or [])):
            return True, ""
        return False, "项目不存在"
