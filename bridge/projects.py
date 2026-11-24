"""Persisted projects, with stable groups for existing conversations."""
import hashlib
import os
import subprocess
import threading
import uuid

from .common import LOG_DIR, PROJECT, read_json, write_json

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
        return list(result.values())


def create(name, workdir):
    name = str(name or "").strip()[:60]
    wd = os.path.normpath(os.path.expandvars(os.path.expanduser(str(workdir or "").strip().strip('"'))))
    if not name or not os.path.isabs(wd) or not os.path.isdir(wd):
        raise ValueError("请填写项目名称和存在的工作文件夹完整路径")
    with LOCK:
        path = os.path.join(LOG_DIR, "projects.json")
        saved = read_json(path) or []
        p = {"id": uuid.uuid4().hex, "name": name, "workdir": wd}
        saved.append(p)
        os.makedirs(LOG_DIR, exist_ok=True)
        write_json(path, saved)
        return p


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
