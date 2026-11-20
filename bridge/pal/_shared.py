"""Shared helpers for Cojam Platform Abstraction Layer."""
from __future__ import annotations

import os
import shutil
from collections.abc import Callable, Sequence


def common_dot_dirs(home: str) -> list[str]:
    return [
        os.path.join(home, ".gemini", "bin"),
        os.path.join(home, ".local", "bin"),
        os.path.join(home, ".cargo", "bin"),
        os.path.join(home, ".bun", "bin"),
        os.path.join(home, ".opencode", "bin"),
        os.path.join(home, ".cursor", "bin"),
    ]


def find_command_with_dirs(
    name: str,
    dir_provider: Callable[[str], list[str]],
    extra_paths: Sequence[str] | None = None,
) -> str | None:
    cleaned_name = str(name or "").strip().strip("\"'")
    expanded_name = os.path.expandvars(os.path.expanduser(cleaned_name))
    if not expanded_name:
        return None
    if os.path.dirname(expanded_name) and os.path.isfile(expanded_name):
        return expanded_name
    home = os.path.expanduser("~")
    paths = [os.environ.get("PATH", ""), *dir_provider(home)]
    for path_item in extra_paths or ():
        cleaned_item = str(path_item or "").strip().strip("\"'")
        if not cleaned_item:
            continue
        exp = os.path.expandvars(os.path.expanduser(cleaned_item))
        if os.path.isfile(exp):
            return exp
        if os.path.isdir(exp):
            paths.append(exp)
    return shutil.which(expanded_name, path=os.pathsep.join(p for p in paths if p))
