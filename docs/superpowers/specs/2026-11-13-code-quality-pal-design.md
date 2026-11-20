# Cojam Phase 2: Code Quality & Platform Abstraction Layer (`1+2`) Design

**Date:** 2026-11-13
**Scope:** Step 1 (`ISSUE-LOW-03..06`, `5.3`, `5.5`) + Step 2 (`5.2`) from `CODE_REVIEW_REPORT.md`

---

## 1. Boundaries & Non-Goals

- **Preserve `data/` next to app binary (`5.4` deferred):** `LOG_DIR` remains `<_APPDIR>/data` by default for beta compatibility and CI upgrade retention tests.
- **Keep `index.html` & `tests/test_frontend_runtime.py` single-file (`5.1` deferred):** Frontend modularization is deferred.
- **Do not touch pre-existing `agy` WIP:** Keep `bridge/drivers.py` and `bridge/presets/antigravity.json` untouched.
- **Keep `desktop_shell/` standalone:** `desktop_shell/` is packaged separately by `build_desktop.ps1` without bundling `bridge`, and `tests/test_desktop_shell.py` patches `shell_main.ctypes.windll` and `backend.subprocess.Popen` directly. Do not introduce `bridge` imports into `desktop_shell/`.
- **Preserve `roundtable.py:ensure_stdio()` `cojam.log` contract:** `tests/test_headless.py` and `desktop_shell/backend.py:log_path()` require windowed stdout/stderr redirection to `<LOG_DIR>/cojam.log`.

---

## 2. Step 2 Architecture First: Platform Abstraction Layer (`bridge/pal/`)

Implementing `bridge/pal/` cleanly before or alongside logging/typing avoids adding type annotations twice across platform branches.

### Package Structure

- `bridge/pal/__init__.py`
  - Re-exports platform constants and unified public functions by importing `_win32` when `os.name == "nt"` else `_posix`, plus small pure-Python dispatch helpers (testable under mocked platform parameters where appropriate).
- `bridge/pal/_win32.py`
  - Windows implementations (`winreg`, `taskkill /F /T /PID`, `subprocess.CREATE_NO_WINDOW`, `.cmd`/`.bat` shim unpacking, Start Menu + `WScript.Shell` shortcut lookup, `SO_EXCLUSIVEADDRUSE`, PowerShell command quoting + hidden updater launcher, `windows.sandbox="unelevated"`).
- `bridge/pal/_posix.py`
  - POSIX / macOS implementations (process group or `proc.kill()`, `shlex.join`, `~/.local/bin` / `/opt/homebrew/bin` extra paths, empty uninstall/Start Menu sets, `allow_reuse_address = True`).

### Unified PAL API Surface

| Symbol | Purpose | Migrated Callers |
| --- | --- | --- |
| `IS_WINDOWS`, `IS_MACOS` | Platform booleans (`os.name == "nt"`, `sys.platform == "darwin"`) | `common.py`, `agents.py`, `updater.py`, `registry.py`, `execution.py`, `web.py`, `member_ui.py` |
| `subprocess_kwargs()` -> `dict[str, Any]` | `{"creationflags": CREATE_NO_WINDOW}` on Windows; `{}` on POSIX | `common.NO_WINDOW`, `updater.py` |
| `find_command_path(name, extra_paths=None)` -> `str \| None` | Executable discovery including Windows registry `Path` & local shims vs POSIX `PATH` | `common.find_executable()` (kept as alias/wrapper) |
| `installed_app_names(ttl=30.0)` -> `frozenset[str]` | Windows Uninstall registry software names (cached); empty `frozenset()` on POSIX | `common.installed_app_names()` |
| `resolve_command(name)` -> `list[str] \| None` | Windows `.cmd`/`.bat` JS/EXE extraction vs POSIX `[path]` | `common.resolve_cmd()` |
| `kill_process_tree(proc)` -> `None` | Windows `taskkill /F /T` fallback to `proc.kill()`; POSIX `proc.kill()` | `common.kill_tree()` |
| `start_menu_dirs()` -> `list[str]` | Start Menu folders on Windows; `[]` on POSIX | `registry._start_menu_dirs()` |
| `resolve_shortcut_target(path)` -> `str` | COM `WScript.Shell` `.lnk` target on Windows; `""` on POSIX | `registry._shortcut_target()` |
| `shell_join(argv)` -> `str` | `& '...' '...'` PowerShell syntax on Windows; `shlex.join(argv)` on POSIX | `execution.py`, `agents.py` |
| `cli_shell_command(exe, script)` -> `str` | Platform wrapper snippet (`& "exe" "script"` vs `"exe" "script"`) | `agents.py` |
| `codex_platform_args()` -> `list[str]` | `["-c", CODEX_SANDBOX_OVERRIDE]` on Windows; `[]` on POSIX | `agents.py` |
| `socket_reuse_allowed()` -> `bool` & `apply_exclusive_socket(sock)` -> `None` | `allow_reuse_address` and `SO_EXCLUSIVEADDRUSE` on Windows | `web.py` (`ExclusiveServer`) |
| `can_install_desktop_update(frozen, executable)` -> `bool` | Checks `win32` + frozen `CojamCore.exe` + sibling `Cojam.exe` | `updater.can_install()` |
| `launch_hidden_powershell(script, env)` -> `subprocess.Popen[bytes]` | Launches hidden Windows PowerShell updater helper (`OSError` / unsupported on POSIX) | `updater.start_install()` |
| `prepend_member_gui_paths()` -> `None` | Adds macOS Homebrew / `.local/bin` PATH entries in `member_ui.py` | `member_ui.py` |

### Compatibility Guarantees

`bridge/common.py` retains `NO_WINDOW`, `find_executable`, `installed_app_names`, `app_installed`, `resolve_cmd`, and `kill_tree` backed by `bridge.pal` so existing callers and tests (`tests/test_rt.py`, etc.) continue to work unchanged. Testability hooks allow testing POSIX and Windows branches deterministically without modifying OS state.

---

## 3. Step 1 Architecture: Logging, Exceptions, Constants, Typing, Build Cleanup

### 3.1 Structured Rotating Logging (`5.3` + `ISSUE-LOW-05`)

- **Separate rotating log file `<LOG_DIR>/bridge.log`:**
  - `roundtable.py:ensure_stdio()` holds an open append handle to `<LOG_DIR>/cojam.log` when launched windowed. Rotating `cojam.log` from inside `RotatingFileHandler` would fail with `PermissionError` (`WinError 32`) on Windows during rollover.
  - Solution: `bridge/common.py` adds `setup_logging(log_dir: str | None = None, level: int = logging.INFO) -> logging.Logger` and `get_logger(name: str) -> logging.Logger`:
    - Configures root/package logger `"bridge"` lazily (idempotent helper, resets cleanly if `log_dir` changes in tests via `reconfigure_logging(log_dir)`).
    - Attaches `logging.handlers.RotatingFileHandler(os.path.join(target_dir, "bridge.log"), maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8")` (`2 * 1024 * 1024` bytes, `3` backups). Falls back safely to `NullHandler` if log directory is read-only.
    - Attaches `StreamHandler` only at `WARNING`+ when interactive/non-duplicate stderr is desired (or relies on `bridge.log` so CLI subcommands like `doctor.py` / `install.py` keep crisp Chinese terminal UX without noisy log prefixes).
- Replace the 4 `print(..., file=sys.stderr)` calls in `bridge/web.py` (`957, 961, 995, 1011`) with `logger.warning(...)` / `logger.exception(...)`. Keep interactive CLI `print(...)` in `doctor.py`, `install.py`, `member_package.py`, `server_runtime.py`, and startup URL banner in `web.py:main()`.

### 3.2 Silent `except: pass` Audit (`ISSUE-LOW-04`)

Audit all **58** silent/bare `except` blocks across `bridge/*.py` (skipping WIP `bridge/drivers.py:222`). Categorize strictly:

1. **Expected Control Flow / Optional Probe / Best-Effort Cleanup (~24 sites):**
   - Examples: `queue.Empty` in `member_ui.py:160`, `KeyboardInterrupt` in `web.py:1065`, `ImportError` on optional `winreg`, `ConnectionError` on shutdown/heartbeat in `member.py`, `OSError` unlinking temp files (`install.py`, `updater.py`, `room.py` cleanup rollback temp files), `socket` probe fallback in `common.py`.
   - Action: Narrow exception types where still overly broad (`Exception` -> explicit types where safe), keep non-fatal flow, add concise comment explaining why ignoring is intentional (`# Expected: ...`).
2. **Silent Error Swallowing (~34 sites):**
   - Examples: JSON parse failures (`agents.py:893`, `room.py:1645`, `discovery.py:308`, `native_session.py:87`), ACP / Codex RPC / cancel / thread name failures (`acp.py:241, 353, 361, 372, 422`, `agents.py:1018, 1102, 1152`), `registry.py:130, 136`, `mcp_stdio.py:47, 71, 101`, `guard.py:48`, `discovery.py:266`, `room.py:965, 1866`, `workspace.py:65`, `server_runtime.py:64`, `common.py:126, 141, 160, 493, 526, 559`.
   - Action: Log with `get_logger(__name__).debug(..., exc_info=True)` for non-critical degraded lookups/stream errors or `.warning(...)` for persistence/RPC/shutdown failures so diagnostics appear in `bridge.log` without altering user-visible fallback behavior.

### 3.3 Hardcoded Constants Consolidation (`ISSUE-LOW-06`)

Consolidate scattered limits and cache sizes into named constants cleanly:
- In `bridge/common.py`:
  - `LOG_MAX_BYTES = 2 * 1024 * 1024`
  - `LOG_BACKUP_COUNT = 3`
  - `SHORTCUT_CACHE_MAX = 128` (or module constant in `registry.py` / shared)
  - Retain existing `MAX_BODY`, `MAX_UPLOAD`, `MAX_ANN`, `MAX_ATTACH`, `MAX_IMAGES`, `TIMEOUT`, `IDLE_LIMIT`, `TOTAL_LIMIT`, `MODES`.
- In `bridge/members.py`:
  - `MAX_ACTIVE_TASKS = 100`
  - `MAX_RETAINED_TASKS = 200`
  - `MAX_MEMBER_REPLY_BYTES = 48 * 1024`
  - `MAX_SESSION_ID_LEN = 200`
- In `bridge/model_catalog.py`:
  - `MAX_CATALOG_ENTRIES = 128`
- In `bridge/registry.py`:
  - `SHORTCUT_CACHE_MAX = 128`
- In `bridge/acp.py`:
  - `STDERR_TAIL_BYTES = 1200`

### 3.4 Type Annotations + `mypy` (`ISSUE-LOW-03`)

- Update `pyproject.toml`:
  - Add `[project.optional-dependencies]` `dev = ["mypy>=1.11", "ruff>=0.6"]`.
  - Add `[tool.mypy]` targeting `python_version = "3.12"`, `files = ["bridge"]`, `ignore_missing_imports = true`, `warn_unused_ignores = true`, `warn_redundant_casts = true`.
  - Enforce strict/checked defs on clean typed core modules via `[[tool.mypy.overrides]]` (`check_untyped_defs = true`, `disallow_untyped_defs = true` for `bridge.version`, `bridge.pal.*`, `bridge.access`, `bridge.execution`, `bridge.common`, and `check_untyped_defs = true` incrementally across `bridge.acp`, `bridge.mcp`, `bridge.mcp_stdio`, `bridge.members`, `bridge.room`, `bridge.web`).
- Add PEP 484 type annotations (using `from __future__ import annotations` where helpful for clean Python 3.12 union syntax `X | None` without runtime overhead) across:
  - `bridge/version.py`
  - `bridge/pal/__init__.py`, `bridge/pal/_win32.py`, `bridge/pal/_posix.py`
  - `bridge/common.py`
  - `bridge/access.py`
  - `bridge/execution.py`
  - `bridge/mcp.py` & `bridge/mcp_stdio.py`
  - `bridge/members.py`
  - `bridge/acp.py`
  - Public/core class and function boundaries of `bridge/room.py` and `bridge/web.py` (enough for `mypy bridge` to pass cleanly with 0 errors and typed core interfaces).

### 3.5 Packaging & Build Cleanup (`5.5`)

- Remove unused root `package.json` (contains only orphaned `"list": "^2.0.19"`) and `package-lock.json`.
- Sync `packaging/cojam.iss` `MyAppVersion` and `OutputName` from `"2.5.1"` to `"2.8.0"` (matching `bridge/version.py`, `pyproject.toml`, and `packaging/cojam-desktop.iss`).
- Keep `Cojam.spec`, `AIBridge.spec`, and `CojamDesktop.spec` intact: they are already gitignored in `.gitignore`, and `tests/test_headless.py` asserts `console=False` in `Cojam.spec` and `AIBridge.spec`.

---

## 4. Verification Strategy

1. Unit tests via TDD before/alongside edits:
   - `tests/test_pal.py`: Verify `bridge.pal` Windows & POSIX dispatch paths, `find_command_path`, `resolve_command`, `kill_process_tree`, `shell_join`, `apply_exclusive_socket`, `start_menu_dirs`, `resolve_shortcut_target`, and `common` compatibility aliases.
   - `tests/test_logging_and_errors.py`: Verify `setup_logging()` creates `<LOG_DIR>/bridge.log`, respects `RotatingFileHandler` rotation (`maxBytes`/`backupCount`) independently from `cojam.log`, logs previously swallowed errors (`bridge/web.py`, `acp.py`, etc.), and preserves `members.py` / `model_catalog.py` constant bounds.
2. Static & Type Checks:
   - Run `mypy bridge` (0 errors) and `ruff check bridge tests/test_pal.py tests/test_logging_and_errors.py`.
3. Full Regression Suite:
   - Run `python tests/run_all.py` (`BypassSandbox: true`) and verify every test module passes cleanly (noting the 2 pre-existing WIP failures in `tests/test_agents_registry.py::AntigravityCli` if `drivers.py` / `antigravity.json` remain unchanged).
