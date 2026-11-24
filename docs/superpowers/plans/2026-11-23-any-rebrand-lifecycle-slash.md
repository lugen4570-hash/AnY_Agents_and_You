# AnY Full Rebrand, Zero-Residue Shutdown, and Harness Slash Commands Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the `Cojam` -> `AnY` rename across source, desktop client, CLI (`any`), packaging, local folders (`D:\AnY`), and GitHub cloud configs (`lugen4570-hash/AnY_Agents_and_You`); fix AnY process residue after closing; and surface all Harness slash commands cleanly grouped in the Web/desktop `/` menu while preserving the existing AnY logo.

**Architecture:** Fix backend process cleanup in `OwnerLifecycle` / `web._stop_runtime` / `detached_jobs` / `agents` so closing AnY terminates only AnY-owned processes and stdio child workers without touching standalone external Agent software. Expand `static/harness-ui.js` to expose the full Harness command catalog in separate command and skill groups while hiding repetitive single-agent skill pills. Sweep remaining `Cojam` / `合拍` symbols, build artifacts, Tauri config, Inno Setup scripts, CLI entrypoints, website manifests, and tests uniformly to `AnY` with safe backward-compatibility fallbacks for user data (`D:\Cojam\data` -> `D:\AnY\data`, `cojam_standby` alias, `cojam_device`/`cojam.draft.` fallbacks).

**Tech Stack:** Python 3.11+ (`bridge/`, `tests/`), Rust / Tauri 2 (`desktop_tauri/`), Vanilla JS / CSS (`static/`, `website/`), Inno Setup 6 (`ISCC.exe`), PyInstaller (`build_exe.ps1`).

**Spec:** Per user directive in conversation ("不改logol了，你直接改名" + Issues 1–3).

## Global Constraints

- Keep existing `make_icon.py` and existing AnY `∀` SVG/ICO/ICNS artwork intact (no logo redesign).
- Canonical brand & target repo: `AnY`, GitHub repo `lugen4570-hash/AnY_Agents_and_You`, Pages URL `https://lugen4570-hash.github.io/AnY_Agents_and_You/`.
- Binaries & CLI: desktop `AnY.exe`, core `AnYCore.exe`, installer `AnY-Setup-<ver>.exe`, CLI command `any` (drop `cojam` script alias after reinstall).
- Process cleanup boundary: terminate ONLY AnY's own processes and AnY-spawned stdio child trees (`AnY.exe`, `AnYCore.exe`, `detached-job`, `CodexServer`, `acp`, `room.procs`); NEVER kill independent external user-opened Agent software.
- Data safety: preserve user meeting history and drafts by migrating `D:\Cojam\data` -> `D:\AnY\data` cleanly and keeping read fallbacks (`cojam_standby`, `cojam_device`, `X-Cojam-*`, `cojam.draft.*`, `~/Library/Application Support/Cojam`).

## Review Focus

1. Closing Tauri/browser while a room is `running` or `queued` must NOT leave `AnYCore.exe` or `AnYCore.exe detached-job` stuck in Task Manager behind `is_busy` or deferred shutdown.
2. Shortening `OwnerLifecycle` reload `grace` must still let normal page reloads re-register cleanly without shutting down the backend prematurely, while exiting quickly on true close.
3. Temporary `CodexServer` subprocesses spawned by `codex_skills` / `_probe_hook_trust` must be tracked and terminated on AnY shutdown so no `codex` child processes linger.
4. Typing `/` in the Web/desktop composer must group built-in Harness commands above Agent skills, avoid repeating `[Codex]` badges on every skill when only one agent owns them, and pass `//...` through untouched as literal message text.
5. Windows/Mac updater (`bridge/updater.py`), Tauri probe (`backend.rs`), and Inno Setup (`any-desktop.iss`) must match window titles, process names (`AnY`, `AnYCore`), app identifier (`"AnY"`), and installer filenames (`AnY-Setup-<ver>.exe`) identically.

---

### Task 1: Zero-Residue AnY Process Shutdown

**Files:**
- Modify: `bridge/owner_lifecycle.py`
- Modify: `bridge/detached_jobs.py`
- Modify: `bridge/agents.py`
- Modify: `bridge/web.py`
- Modify: `bridge/terminal.py`
- Test: `tests/test_owner_lifecycle.py`, `tests/test_detached_jobs.py`

**Interfaces:**
- Produces: `bridge.agents.stop_all_codex() -> None`, `bridge.detached_jobs.cancel_all(rooms: list) -> int`, updated `OwnerLifecycle(shutdown, grace=1.5, expiry=45, interval=.5, is_busy=None)`.
- Consumes: `bridge.common.kill_tree`, `bridge.agents.stop_codex`, `bridge.acp.stop`.

- [ ] **Step 1: Add failing lifecycle regression test in `tests/test_owner_lifecycle.py`**
  Add `test_last_tab_close_stops_even_when_room_marked_busy_and_cleans_detached_worker` (headless `roundtable.py` subprocess with an active/busy room or detached job; after last `/api/ui/session` `close`, assert server process exits < 8s AND detached worker PID terminates with 0 lingering processes).
- [ ] **Step 2: Run `python tests/test_owner_lifecycle.py` to observe failure**
  Expected: FAIL / timeout because `is_busy` blocks exit and `_stop_runtime` leaves `detached-job` alive.
- [ ] **Step 3: Track all `CodexServer` instances & expose `stop_all_codex()` in `bridge/agents.py`**
  Register every started `CodexServer` in `_ACTIVE_CODEX_SERVERS` (under `_CODEX_LOCK`, removed on `stop()`), and implement `stop_all_codex()` to call `stop_codex(None)` plus terminate any active temporary `CodexServer` (`codex_skills` / `_probe_hook_trust`).
- [ ] **Step 4: Add `cancel_all(rooms)` in `bridge/detached_jobs.py`**
  Iterate rooms / jobs directory, cancel and `kill_tree` active `detached-job` workers + mark in-flight `.json` status `'cancelled'` (`'AnY 已退出'`). Keep existing `begin_shutdown()` unit behavior for callers explicitly setting `ROUNDTABLE_KEEP_DETACHED_ON_EXIT=1`.
- [ ] **Step 5: Update `bridge/owner_lifecycle.py` and `bridge/web.py` (`_stop_runtime`, `stop_application`, `OwnerLifecycle`)**
  Set `OwnerLifecycle` defaults `grace=1.5, expiry=45` (`desktop_tauri` heartbeats every 20s so 45s > 2× heartbeat). Remove `is_busy` blocker on `OwnerLifecycle` in `bridge/web.py` (window/tab confirmation happens before `close`). In `web._stop_runtime()`, stop all active rooms (`room.stop_ais()`) and terminate active AnY detached jobs via `detached_jobs.cancel_all(R.rooms.all())` unless `ROUNDTABLE_KEEP_DETACHED_ON_EXIT == '1'`, call `agents.stop_all_codex()` and `acp.stop()`. In `bridge/terminal.py`, ensure console close (`atexit` / signal cleanup) releases owner tab when exiting unexpectedly.
- [ ] **Step 6: Stabilize `tests/test_detached_jobs.py` Windows temp cleanup & run both test suites**
  Ensure temp worker processes finish before `TemporaryDirectory` removal in `tests/test_detached_jobs.py`, run `python tests/test_owner_lifecycle.py` and `python tests/test_detached_jobs.py`, verify PASS.

### Task 2: Complete Harness Slash Commands & Grouping in Web/Desktop UI

**Files:**
- Modify: `static/harness-ui.js`
- Modify: `static/harness-ui.css`
- Modify: `static/app-chat.js` (compatibility alias `AnYHarness` + `CojamHarness`)
- Test: `tests/test_harness_ui.py`

**Interfaces:**
- Produces: Expanded `SLASH_COMMANDS`, `filterSlashCommands`, `parseComposerSlashCommand`, `handleComposerSlashCommand`, grouped `updateSlashMenu` rendering (export `window.AnYHarness` and alias `window.CojamHarness`).

- [ ] **Step 1: Add failing command parity & single-agent skill grouping tests in `tests/test_harness_ui.py`**
  Assert all core Harness/AnY commands (`compact`, `skills`, `mode`, `model`, `stop`, `debate`, `debate-finish`, `wrapup`, `new`, `resume`, `agents`, `scan`, `connect`, `invite`, `handoff`, `return`, `project`, `announce`, `todo`, `done`, `status`, `undo`, `rename`, `help`, `quit`) appear in `filterSlashCommands('/', 1, ...)` and parse accurately in `parseComposerSlashCommand`. Assert single-agent skill list puts agent name in section header without repeating per-row tags, while multi-agent rooms still display per-row tags.
- [ ] **Step 2: Run `python tests/test_harness_ui.py` to observe failure**
  Expected: FAIL on missing commands (`mode`, `stop`, `debate`, etc.) and skill menu grouping.
- [ ] **Step 3: Expand `SLASH_COMMANDS`, `parseComposerSlashCommand`, `handleComposerSlashCommand`, and `updateSlashMenu` in `static/harness-ui.js` + CSS in `static/harness-ui.css`**
  Wire every Harness command to its real API call or existing UI modal/pane cleanly. Render separate **「内置命令」** and **「Agent 技能」** sections inside `#slashMenu`; omit per-row `.slash-agent-tag` when `uniqueOwners.size === 1` and show `Agent 技能 · <Name>` in the section header instead.
- [ ] **Step 4: Run `python tests/test_harness_ui.py` & `node --check static/harness-ui.js`**
  Expected: PASS.

### Task 3: Complete Cojam -> AnY Rebrand Across Source, Tauri, Packaging, Website & Tests

**Files:**
- Rename: `packaging/cojam-desktop.iss` -> `packaging/any-desktop.iss`, `packaging/cojam.iss` -> `packaging/any.iss`, `packaging/start-cojam.command` -> `packaging/start-any.command`, `packaging/build-cojam.command` -> `packaging/build-any.command`; remove `desktop_tauri/src-tauri/permissions/autogenerated/cojam_*.toml`.
- Modify: `pyproject.toml`, `roundtable.py`, `build_exe.ps1`, `build_desktop.ps1`, `sign_exe.ps1`, `.github/workflows/*.yml`, `packaging/*`, `desktop_shell/*`, `desktop_tauri/src-tauri/*`, `bridge/*`, `static/*`, `website/*`, `tests/*`, `docs/*` (active guides, excluding historical immutable release logs where explicitly historical).

**Interfaces:**
- Produces: App id `"AnY"`, binaries `AnY.exe` & `AnYCore.exe`, CLI command `any`, Tauri IPC `any_choose_workdir` / `any_choose_agent_file`, env `ANY_EXPECTED_VERSION` / `ANY_EXPECTED_API_REVISION` / `ANY_UPDATE_*`, MCP tool `any_standby` (with `cojam_standby` fallback), repo URLs `lugen4570-hash/AnY_Agents_and_You`.

- [ ] **Step 1: Rename Tauri / Rust / Build / Packaging files and scripts to `AnY` / `AnYCore` / `any-desktop`**
- [ ] **Step 2: Rename Python `bridge/` & `desktop_shell/` references with data/protocol fallbacks (`cojam_standby`, `cojam_device`, `X-Cojam-*`, macOS `Cojam` dir fallback)**
- [ ] **Step 3: Rename Frontend `static/` & `website/` (`update.json`, `site.js`, HTML download links) references with localStorage fallbacks**
- [ ] **Step 4: Update `tests/` expectations and run full static & unit test suite**
  Run `node --check`, `python -m mypy bridge`, `python -m ruff check bridge tests/test_headless.py packaging/build_release.py`, `cargo test --locked`, and `python tests/run_all.py`.

### Task 4: Rebuild Client, Migrate `D:\Cojam` -> `D:\AnY`, Install `any` CLI, Check GitHub Remote & Live Verification

- [ ] **Step 1: Reinstall editable package (`pip install --no-deps --no-build-isolation -e .`) and remove stale `D:\python\Scripts\cojam.exe`; verify `any --version` / `where.exe any`**
- [ ] **Step 2: Build Windows `AnY.exe`, `AnYCore.exe`, `AnYDesktop.exe`, `AnY-Setup-*.exe`, `AnY-Portable-*.exe` (`build_exe.ps1`, `build_desktop.ps1`, `ISCC.exe`, `packaging/build_release.py`)**
- [ ] **Step 3: Install/deploy clean build into `D:\AnY` while safely migrating `D:\Cojam\data` -> `D:\AnY\data` (and removing stale `D:\Cojam` binary dir after verifying `data` intact)**
- [ ] **Step 4: Run live startup & shutdown verification on `D:\AnY\AnY.exe` / `AnYCore.exe` confirming 0 leftover processes in `Get-Process AnY*, Cojam*`**
- [ ] **Step 5: Inspect/update GitHub remote (`lugen4570-hash/AnY_Agents_and_You`) and verify repo cloud state (reporting cleanly if auth/repo creation requires user sign-in or web action)**
