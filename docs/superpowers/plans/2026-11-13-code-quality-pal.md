# Cojam Phase 2: Code Quality & Platform Abstraction Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor platform-specific logic into `bridge/pal/`, add rotating logging, remediate silent `except: pass` handlers, centralize magic numbers, clean packaging residue, and add PEP 484 type annotations verified by `mypy`.

**Architecture:** Extract OS-specific process, registry, socket, shortcut, and shell helpers into `bridge/pal/` (`_win32.py` / `_posix.py`) while keeping `bridge/common.py` backward-compatible aliases. Add lazy idempotent `RotatingFileHandler` logging targeting `<LOG_DIR>/bridge.log` so it never contends with `roundtable.py:ensure_stdio()`'s open handle on `cojam.log`, then systematically audit exception handlers, constants, build artifacts, and `mypy` configuration.

**Tech Stack:** Python 3.12 stdlib (`logging.handlers`, `subprocess`, `socket`, `winreg`, `shlex`), `ruff`, `mypy`, `unittest`.

**Spec:** `docs/superpowers/specs/2026-11-13-code-quality-pal-design.md`

## Global Constraints

- Do NOT migrate runtime `data/` (`LOG_DIR`) to `%APPDATA%` (`5.4` deferred for beta).
- Do NOT split `index.html` or refactor `tests/test_frontend_runtime.py` (`5.1` deferred).
- Do NOT modify pre-existing WIP `bridge/drivers.py` or `bridge/presets/antigravity.json`.
- Keep `desktop_shell/` zero-dependency on `bridge` (`build_desktop.ps1` + `tests/test_desktop_shell.py`).
- Preserve `roundtable.py:ensure_stdio()` writing to `<LOG_DIR>/cojam.log` (`tests/test_headless.py`).
- Keep `Cojam.spec`, `AIBridge.spec`, `CojamDesktop.spec` intact (`tests/test_headless.py` checks `Cojam.spec` & `AIBridge.spec`).
- Do NOT create `git commit`s or stage untracked reports (`CODE_REVIEW_REPORT.md`, `reports/`, `.agents/`, `research_notes/`).

## Review Focus

- **Windows log file lock:** `RotatingFileHandler` rolling `bridge.log` must never collide with `ensure_stdio()`'s open handle on `cojam.log`, nor crash when `LOG_DIR` is unwritable.
- **Backward-compatible test mocks:** Existing tests patch `common.kill_tree`, `common.resolve_cmd`, `common.NO_WINDOW`, and `desktop_shell` directly; aliases in `common.py` and isolated `desktop_shell/` boundaries must keep all mocks functional.
- **Expected vs silent excepts:** Turning silent `except` into logging must not crash optional cleanup (unlinking temp files, closed sockets/pipes) or leak stack traces onto interactive CLI output.
- **Windows vs POSIX PAL parity:** Both `_win32` and `_posix` implementations must match identical function signatures and pass unit tests regardless of the host OS running tests.
- **`mypy` runtime safety:** Adding PEP 484 type hints (with `from __future__ import annotations`) must not introduce circular imports or runtime `TypeError`s in Python 3.12.

---

### Task 1: Platform Abstraction Layer (`bridge/pal/`) & Caller Migration

**Files:**
- Create: `bridge/pal/__init__.py`
- Create: `bridge/pal/_win32.py`
- Create: `bridge/pal/_posix.py`
- Create: `tests/test_pal.py`
- Modify: `bridge/common.py`
- Modify: `bridge/registry.py`
- Modify: `bridge/agents.py`
- Modify: `bridge/updater.py`
- Modify: `bridge/execution.py`
- Modify: `bridge/web.py`
- Modify: `bridge/member_ui.py`

**Interfaces:**
- Produces in `bridge/pal/__init__.py`:
  - `IS_WINDOWS: bool`, `IS_MACOS: bool`
  - `subprocess_kwargs() -> dict[str, Any]`
  - `find_command_path(name: str, extra_paths: Sequence[str] | None = None) -> str | None`
  - `installed_app_names(ttl: float = 30.0) -> frozenset[str]`
  - `resolve_command(name: str) -> list[str] | None`
  - `kill_process_tree(proc: subprocess.Popen[Any]) -> None`
  - `start_menu_dirs() -> list[str]`
  - `resolve_shortcut_target(path: str, modified_ns: int, size: int) -> str`
  - `shell_join(argv: Sequence[str]) -> str`
  - `cli_shell_command(executable: str, script: str) -> str`
  - `codex_platform_args() -> list[str]`
  - `socket_reuse_allowed() -> bool`
  - `apply_exclusive_socket(sock: socket.socket) -> None`
  - `can_install_desktop_update(frozen: bool | None = None, executable: str | None = None) -> bool`
  - `launch_hidden_powershell(encoded_command: str, env: Mapping[str, str]) -> subprocess.Popen[bytes]`
  - `prepend_member_gui_paths() -> None`

- [ ] **Step 1: Write failing PAL unit tests (`tests/test_pal.py`)**

Write unit tests exercising `bridge.pal` (both `_win32` and `_posix` implementations directly plus top-level dispatch and `bridge.common` aliases): `test_subprocess_kwargs_per_platform`, `test_shell_join_win32_and_posix`, `test_cli_shell_command_and_codex_args`, `test_resolve_cmd_unpacks_cmd_shim_and_exe`, `test_installed_app_names_caches_and_returns_empty_on_posix`, `test_start_menu_and_shortcut_on_posix_and_win32`, `test_kill_process_tree_falls_back_to_kill`, `test_exclusive_socket_options`, `test_can_install_desktop_update_checks_win32_frozen`, `test_common_aliases_match_pal`.

- [ ] **Step 2: Run `python tests/test_pal.py` to verify failure**

Run: `python tests/test_pal.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'bridge.pal'`

- [ ] **Step 3: Implement `bridge/pal/_win32.py`, `bridge/pal/_posix.py`, and `bridge/pal/__init__.py`**

Move platform-specific logic into `_win32.py` (using `winreg`, `CREATE_NO_WINDOW`, `taskkill /F /T /PID`, `.cmd`/`.bat` parser, Start Menu & `WScript.Shell` COM resolution with `SHORTCUT_CACHE_MAX`, `SO_EXCLUSIVEADDRUSE`, PowerShell quoting & detached launcher) and `_posix.py` (`shlex.join`, standard PATH extras, `proc.kill()`, `allow_reuse_address = True`, macOS member GUI PATH prepending, safe no-op/false returns for Windows-only features). Export unified typed interface in `bridge/pal/__init__.py`.

- [ ] **Step 4: Migrate callers to `bridge.pal` while keeping `bridge/common.py` aliases**

Update `common.py`, `registry.py`, `agents.py`, `updater.py`, `execution.py`, `web.py`, and `member_ui.py` to call `bridge.pal`. Keep `NO_WINDOW`, `find_executable`, `installed_app_names`, `app_installed`, `resolve_cmd`, and `kill_tree` on `bridge.common`.

- [ ] **Step 5: Run `tests/test_pal.py` + affected suites**

Run: `python tests/test_pal.py` and `python tests/test_rt.py` and `python tests/test_server_runtime.py` (`BypassSandbox: true` for socket/kill_tree tests).
Expected: PASS cleanly.

---

### Task 2: Structured Rotating Logging (`5.3` + `ISSUE-LOW-05`)

**Files:**
- Modify: `bridge/common.py`
- Modify: `bridge/web.py`
- Create: `tests/test_logging_and_errors.py`

**Interfaces:**
- Produces in `bridge/common.py`:
  - `LOG_FILENAME: str = "bridge.log"`
  - `LOG_MAX_BYTES: int = 2 * 1024 * 1024`
  - `LOG_BACKUP_COUNT: int = 3`
  - `setup_logging(log_dir: str | None = None, *, level: int = logging.INFO, max_bytes: int = LOG_MAX_BYTES, backup_count: int = LOG_BACKUP_COUNT, force: bool = False) -> logging.Logger`
  - `get_logger(name: str = "bridge") -> logging.Logger`

- [ ] **Step 1: Write failing logging tests in `tests/test_logging_and_errors.py`**

Test `setup_logging` creates `bridge.log` (distinct from `cojam.log`), idempotency without `force=True`, `force=True` directory switch & clean close of prior handlers (Windows file handles must close before `TemporaryDirectory` cleanup!), `RotatingFileHandler` rollover with backup files, graceful fallback if log directory cannot be created, and `web.start_lan_listener` failure logging through `bridge.web` logger instead of bare stderr crash.

- [ ] **Step 2: Run `python tests/test_logging_and_errors.py` to verify failure**

Run: `python tests/test_logging_and_errors.py`
Expected: FAIL (`AttributeError: module 'bridge.common' has no attribute 'setup_logging'`)

- [ ] **Step 3: Implement `setup_logging` & `get_logger` in `bridge/common.py` and update `bridge/web.py`**

Configure `"bridge"` logger cleanly via lock (`_LOG_LOCK`), attaching `RotatingFileHandler` (`delay=True` or clean file creation, `encoding="utf-8"`) + optional `NullHandler` fallback on `OSError`. Update `bridge/web.py` lines `957, 961, 995, 1011` from `print(..., file=sys.stderr)` to `logger.warning(...)` / `logger.exception(...)`.

- [ ] **Step 4: Run `python tests/test_logging_and_errors.py` & `python tests/test_headless.py`**

Run: `python tests/test_logging_and_errors.py` and `python tests/test_headless.py` (`BypassSandbox: true` for socket tests).
Expected: PASS.

---

### Task 3: Named Constants Consolidation (`ISSUE-LOW-06`)

**Files:**
- Modify: `bridge/members.py`
- Modify: `bridge/model_catalog.py`
- Modify: `bridge/registry.py`
- Modify: `bridge/acp.py`
- Test: `tests/test_logging_and_errors.py`

- [ ] **Step 1: Add test assertions verifying named constants and behavior in `tests/test_logging_and_errors.py`**

Test `members.MAX_ACTIVE_TASKS == 100`, `members.MAX_RETAINED_TASKS == 200`, `members.MAX_MEMBER_REPLY_BYTES == 48 * 1024`, `members.MAX_SESSION_ID_LEN == 200`, `model_catalog.MAX_CATALOG_ENTRIES == 128`, `registry.SHORTCUT_CACHE_MAX == 128` (and/or `pal` constant), `acp.STDERR_TAIL_BYTES == 1200`.

- [ ] **Step 2: Run test to verify failure**

Expected: FAIL (`AttributeError`)

- [ ] **Step 3: Replace inline magic numbers with module constants**

Define constants cleanly at top of each module and reference them inside `Broker.dispatch`/`complete`, `_store`, `_shortcut_target` (`bridge/pal`), and `AcpProcess._read_stderr`.

- [ ] **Step 4: Run `python tests/test_logging_and_errors.py`, `tests/test_members.py`, `tests/test_acp.py`**

Expected: PASS.

---

### Task 4: Remediate 58 Silent `except: pass` Handlers (`ISSUE-LOW-04`)

**Files:**
- Modify: `bridge/acp.py`, `bridge/agents.py`, `bridge/common.py`, `bridge/discovery.py`, `bridge/guard.py`, `bridge/install.py`, `bridge/invites.py`, `bridge/mcp_stdio.py`, `bridge/member.py`, `bridge/member_ui.py`, `bridge/native_session.py`, `bridge/registry.py`, `bridge/room.py`, `bridge/server_runtime.py`, `bridge/updater.py`, `bridge/workspace.py`
- Test: `tests/test_logging_and_errors.py`

- [ ] **Step 1: Add AST exception-hygiene & behavioral error-logging tests in `tests/test_logging_and_errors.py`**

Write:
1) An AST audit test across `bridge/*.py` (excluding WIP `bridge/drivers.py`) asserting zero bare `except:` clauses remain and any `except ...: pass` (if still needed for explicit control flow like `KeyboardInterrupt` or `queue.Empty`) uses specific non-`Exception` types and an explanatory comment.
2) Behavioral tests triggering invalid JSONL in `room.scan`/load, `mcp_stdio` worker exception, and `agents` invalid Codex JSON stdout line to assert they log safely without crashing callers.

- [ ] **Step 2: Run `python tests/test_logging_and_errors.py` to verify failure**

Expected: FAIL on AST audit of ~58 silent `except ...: pass` blocks.

- [ ] **Step 3: Fix all 58 `except` handlers across `bridge/*.py`**

Replace `except Exception: pass` / `except OSError: pass` in persistence, RPC, JSON parsing, shutdown, and process management paths with structured `logger.debug(..., exc_info=True)` or `logger.warning(...)` (avoiding noisy logs for genuinely expected `queue.Empty` / `KeyboardInterrupt` / `ImportError("winreg")` / `OSError` cleanup annotated explicitly with `# Expected: ...` or `contextlib.suppress`). Never alter `bridge/drivers.py`.

- [ ] **Step 4: Run `python tests/test_logging_and_errors.py` and targeted module tests**

Expected: PASS.

---

### Task 5: Build & Packaging Cleanup (`5.5`)

**Files:**
- Delete: `package.json`, `package-lock.json`
- Modify: `packaging/cojam.iss`
- Test: `tests/test_logging_and_errors.py`, `tests/test_headless.py`

- [ ] **Step 1: Add version consistency & leftover artifact test in `tests/test_logging_and_errors.py`**

Assert `package.json` and `package-lock.json` do not exist at repo root, and `packaging/cojam.iss` `MyAppVersion` equals `bridge.version.VERSION` (matching `pyproject.toml` and `packaging/cojam-desktop.iss`).

- [ ] **Step 2: Run test to verify failure**

Expected: FAIL (`package.json` exists, `cojam.iss` is `"2.5.1"` != `"2.8.0"`).

- [ ] **Step 3: Delete `package.json` & `package-lock.json`; sync `packaging/cojam.iss` to `"2.8.0"`**

Update `MyAppVersion` and `OutputName` lines in `packaging/cojam.iss` from `2.5.1` to `2.8.0`. Keep `Cojam.spec`, `AIBridge.spec`, `CojamDesktop.spec` untouched.

- [ ] **Step 4: Run `python tests/test_logging_and_errors.py` and `python tests/test_headless.py`**

Expected: PASS.

---

### Task 6: PEP 484 Type Annotations & `mypy` Gate (`ISSUE-LOW-03`)

**Files:**
- Modify: `pyproject.toml`
- Modify: `bridge/version.py`, `bridge/pal/*.py`, `bridge/common.py`, `bridge/access.py`, `bridge/execution.py`, `bridge/mcp.py`, `bridge/mcp_stdio.py`, `bridge/members.py`, `bridge/acp.py`, `bridge/room.py`, `bridge/web.py` (plus minimal imports/annotations needed for clean `mypy bridge`)

- [ ] **Step 1: Add `[project.optional-dependencies].dev` and `[tool.mypy]` to `pyproject.toml`**

Configure `python_version = "3.12"`, `files = ["bridge"]`, `ignore_missing_imports = true`, `warn_unused_ignores = true`, plus strict overrides for `bridge.version`, `bridge.pal.*`, `bridge.access`, `bridge.common`, `bridge.execution`.

- [ ] **Step 2: Run `python -m mypy bridge` to establish baseline errors**

Run: `python -m mypy bridge`

- [ ] **Step 3: Add PEP 484 type hints across core `bridge/` modules and fix all `mypy` findings**

Annotate function signatures, return types, module caches/globals (`from __future__ import annotations`), and fix any latent type bugs surfaced by `mypy` without altering runtime semantics.

- [ ] **Step 4: Verify `python -m mypy bridge` and `ruff check`**

Run: `python -m mypy bridge` and `ruff check bridge tests/test_pal.py tests/test_logging_and_errors.py`
Expected: `Success: no issues found` from `mypy`, zero errors from `ruff check`.

---

### Task 7: Final Regression & Verification Gate

- [ ] **Step 1: Run `python tests/run_all.py` (`BypassSandbox: true`)**
- [ ] **Step 2: Run `python -m mypy bridge` and `ruff check` on all modified files**
- [ ] **Step 3: Verify `git status` shows WIP (`bridge/drivers.py`, `bridge/presets/antigravity.json`) and untracked docs (`CODE_REVIEW_REPORT.md`, `reports/`, `.agents/`, `research_notes/`) untouched, and `data/` layout intact.**
- [ ] **Step 4: Update `reports/CODE_REVIEW_FIX_HANDOFF.md` with Phase 2 completion & exact verified test/tool outputs.**
