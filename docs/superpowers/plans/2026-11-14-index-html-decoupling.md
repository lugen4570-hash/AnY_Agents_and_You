# Cojam Step 3: Frontend `index.html` Modularization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split inline CSS and JavaScript out of `index.html` into `static/app.css` and five cohesive classic JS modules (`static/app-core.js`, `app-chat.js`, `app-viewer.js`, `app-meeting.js`, `app-runtime.js`) while keeping server caching, PyInstaller packaging, and all frontend/backend tests green.

**Architecture:** Extract lines `18–467` of `index.html` into `static/app.css` loaded before `workspace.css` and `studio.css`, and split lines `540–1571` into five flat `static/app-*.js` classic scripts executed right after `execution-settings.js` and before `update.js`. All extracted filenames match `^[\w.\-]+$` in `bridge/web.py` so `ExclusiveServer.ui_assets` caches them cleanly and `build_exe.ps1` (`--add-data "static;static"`) bundles them automatically.

**Tech Stack:** Vanilla HTML5, CSS3, ES2022 classic browser scripts, Python 3.12 `unittest`, Node.js `vm` harness.

**Spec:** `docs/superpowers/specs/2026-11-14-index-html-decoupling-design.md`

## Global Constraints

- Flat filenames inside `static/` (`^[\w.\-]+$` required by `bridge/web.py:236` & `ExclusiveServer.__init__:939`).
- Preserve stylesheet cascade: `app.css` -> `workspace.css` -> `studio.css`.
- Preserve classic `<script>` order: `workspace.js` -> `qrcode.min.js` -> `connections.js` -> `model-settings.js` -> `agent-settings.js` -> `execution-settings.js` -> `app-core.js` -> `app-chat.js` -> `app-viewer.js` -> `app-meeting.js` -> `app-runtime.js` -> `update.js`.
- Zero duplicate top-level `let`/`const` declarations across any loaded `static/*.js` file (`modal` and `mbox` live only in `app-core.js`; `roomList` lives in `app-runtime.js`).
- Keep `index.html` token placeholder `__RT_TOKEN__`, `/manifest.webmanifest`, and `/static/icon-192.png?v=cojam-262` untouched (`tests/test_icons.py`).
- Do NOT touch `bridge/drivers.py`, `bridge/presets/antigravity.json`, `bridge/catalog/agents.json`, `data/` (`LOG_DIR`), or create `git commit`s.

## Review Focus

- **Global lexical collision (`let`/`const`):** Classic `<script>` tags share one global lexical environment; declaring `modal`, `mbox`, `feed`, `RID`, or `ROOMS` in two files throws `SyntaxError` at browser boot. Guard with a full multi-script Node `vm` boot test.
- **Temporal Dead Zone at parse time:** Code executing immediately on load (`drawQuick()`, `setInterval(...)`, `if (RID) switchRoom(...)`, `refreshContacts()`) must run only after all dependencies have been parsed; `app-runtime.js` runs last among `app-*.js`, and `app-core.js` keeps `typeof lastRun !== 'undefined'` / `typeof ROOMS !== 'undefined'` guards.
- **CSS cascade regression:** Moving `:root` defaults out of `<style>` must not accidentally place `app.css` after `studio.css`, which would override Cojam's violet/lime theme variables.
- **UI generation lock (`ExclusiveServer`):** Extracted files must end in `.css`/`.js` directly under `static/` so `ExclusiveServer.__init__` caches them in `ui_assets` and rejects hot-drift mismatches just like `connections.js`.
- **Test fragility (`test_frontend_runtime.py`, `test_meeting_navigation.py`):** Existing substring/regex slices in Node tests must be updated to target the new owning module (`app-core.js`, `app-meeting.js`, `app-runtime.js`) cleanly without dropping assertions or altering mocked behavior.

---

### Task 1: Add Failing Structural & Multi-Script Boot Guard Tests (TDD Red)

**Files:**
- Modify: `tests/test_frontend_runtime.py`

- [ ] **Step 1: Add `FrontendModularStructure` test class to `tests/test_frontend_runtime.py`**

Add tests checking:
1. `test_index_html_has_no_inline_style_or_script_and_valid_static_refs`:
   - `index.html` contains no `<style` tag and no non-empty `<script>` inline body.
   - `<link rel="stylesheet">` order is `/static/app.css` < `/static/workspace.css` < `/static/studio.css`.
   - Every `/static/*.js` and `/static/*.css` referenced in `index.html` exists under `static/`, matches `^[\w.\-]+$`, and appears in the expected order (`qrcode.min.js` before `connections.js`; `execution-settings.js` before `app-core.js`..`app-runtime.js` before `update.js`).
2. `test_extracted_app_scripts_load_sequentially_without_collisions`:
   - Uses Node `vm` to execute `static/workspace.js`, `static/connections.js`, `static/model-settings.js`, `static/agent-settings.js`, `static/execution-settings.js`, `static/app-core.js`, `static/app-chat.js`, `static/app-viewer.js`, `static/app-meeting.js`, `static/app-runtime.js`, `static/update.js` sequentially inside ONE shared `vm.createContext` with lightweight DOM/browser stubs, verifying zero `SyntaxError`/`ReferenceError` and confirming startup fetches `/api/ui/session`, `/api/rooms`, and `/api/agents`.
3. `test_exclusive_server_caches_all_extracted_frontend_assets`:
   - Spins up `web.ExclusiveServer` pointing at repo `index.html` and `static/` (temp overwrite check unnecessary — just verify `"app.css"`, `"app-core.js"`, `"app-chat.js"`, `"app-viewer.js"`, `"app-meeting.js"`, `"app-runtime.js"` exist in `server.ui_assets` and respond `200` over HTTP).

- [ ] **Step 2: Run `python tests/test_frontend_runtime.py` to verify the new tests fail before extraction**

Run: `python tests/test_frontend_runtime.py`
Expected: FAIL (`<style` / inline `<script>` still present in `index.html`, `static/app.css` & `static/app-*.js` missing).

---

### Task 2: Extract Styles into `static/app.css` and Split Scripts into `static/app-*.js`

**Files:**
- Create: `static/app.css`
- Create: `static/app-core.js`
- Create: `static/app-chat.js`
- Create: `static/app-viewer.js`
- Create: `static/app-meeting.js`
- Create: `static/app-runtime.js`
- Modify: `index.html`

- [ ] **Step 1: Create `static/app.css` from `index.html:18-467`**

Copy lines `18–467` verbatim from `index.html` into `static/app.css`.

- [ ] **Step 2: Create `static/app-core.js`, `static/app-chat.js`, `static/app-viewer.js`, `static/app-meeting.js`, `static/app-runtime.js`**

Split lines `540–1571` strictly preserving every comment, selector, string, and function body:
- `static/app-core.js`: token IIFE, `ownerTabId`, `ownerInstance`, owner session IIFE, `feed`/`ta`/`st`/`touch`/`since`/`curMeeting`/`S`/`msgById`/`RID`/`api`/SW registration, `esc`, `seenMap`, `markSeen`, `modal`/`mbox`/`modalReturnFocus`/`showModal`/`hideModal` + modal listeners, `apiError`, `post`, `fallbackCopy`, `copyText`.
- `static/app-chat.js`: `render`, `mdInline`, `mdBlock`, `fmtSize`, `attHtml`, `add`, `pend`/`uploading`/`pendEl`/`fileEl`/`drawPend`/`upload`/paste+drag+file listeners, `quote`/`quoteEl`/`setQuote`/`quoteX`/`selIn`/`cmenu`/`selectionTools`/`copyNotice`/`copyNoticeTimer`/`copyMessageText`/`placeMessageTools`/`hideMenu`/`updateSelectionTools`/menu+selection listeners, `send` + `#send`/`ta` listeners, `jumpEl`/`jUp`/`jDn`/`feedTop`/`myMsgs`/`prevMine`/`nextMine`/`atEnd`/`scrollFeed`/`goTo`/`syncJump`/`holdable`/`jumpRaf`/`queueJump`/`ResizeObserver`/`setInterval(queueJump, 1500)`, `tocEl`/`tocList`/`tocQ`/`narrow`/`tocLine`/`curMine`/`drawToc`/`placeToc`/`openToc`/`closeToc`/TOC listeners.
- `static/app-viewer.js`: `vw`/`vStage`/`vImg`/`vCv`/`vOv`/`vWrap`/`vHint`/`vctx`/`octx`/`vList`/`vIdx`/`ed`, `openViewer`, `closeViewer`, `showImg`, `step`, feed click handler, `vPrev`/`vNext`/`vClose`/`vImg`/`vStage`, swipe & keydown handlers, `TOOL_HINT`, `THICK`, `startEdit`, `endEdit`, `cancelEdit`, `setSize`, `fitCanvas`, `syncTools`, tool/color/thick/edit/cancel/undo handlers, `lw`, `snap`, `undoEdit`, `pt`, `stroke`, `drawArrow`, `box`, `preview`, `vWrap` pointer handlers, `finishDrag`, `editedName`, `canvasFile`, `vSave`, `vDone`.
- `static/app-meeting.js`: `lastRun`/`stLive`/`openLive`/`stLive.onclick`/`fmtDur`/`drawStatus`, `ann*`/`showAnn`/`loadAnn`/`closeEdit`/ann listeners, `board*`/`drawBoard`/`boardPost`/`boardAdd`/board listeners, `bar`/`titleEl`/`meetingToolsButton`/toolbar listeners/`meetingSide`/`meetingSideBg`/`sideReturnFocus`/`setMeetingSide`/card folds/details keydown, `fmtK`/`ctxHtml`/`ctxTitle`, `agentMeta`/`isAgent`/`agentColor`/`agentLetter`, `capsEl`/`drawCaps`/`quickEl`/`drawQuick`/`AG_DRV`/`agCat`/`capText`, `drawState`/`drawMeetingDetails`/`syncUndo`/`undoStep`/`toggleMode`, `openList`, `openAi`/`#bList`/`#bMode`/`drawStops`/`stopAi`/`#bWrap`/`#bAgents`, `claimList`/`claimSig`/`drawClaims`/`#cMine`, `loadTools`, `drawQuick();`. (Note: do NOT redeclare `const modal` or `const mbox` here since `app-core.js` declares them.)
- `static/app-runtime.js`: `polling`, `roomViewGeneration`, `poll`, `loadState`, `roomList`, `ROOMS`, `roomBadge`, `roomList` click listener, `resetRoomView`, `switchRoom`, `popstate`, `goneShown`, `roomGone`, `pickRoom`, `#rNew.onclick`, `visibilitychange` listener, polling `setInterval`s, `refreshContacts()` call, initial `if (RID) switchRoom(RID, true); else pickRoom();`.

- [ ] **Step 3: Update `index.html` to link `/static/app.css` and load `/static/app-*.js`**

Replace `<style>...</style>` with `<link rel="stylesheet" href="/static/app.css">` before `workspace.css` and `studio.css`; replace inline `<script>...</script>` with the 5 `<script src="/static/app-*.js"></script>` tags before `update.js`.

---

### Task 3: Update Existing Frontend Tests & Verify End-to-End

**Files:**
- Modify: `tests/test_frontend_runtime.py`
- Modify: `tests/test_meeting_navigation.py`
- Modify: `reports/CODE_REVIEW_FIX_HANDOFF.md`

- [ ] **Step 1: Update code-slice sources in `tests/test_frontend_runtime.py` and `tests/test_meeting_navigation.py`**

- In `tests/test_frontend_runtime.py`:
  - `drawQuick`: read from `static/app-meeting.js`
  - `poll`: read from `static/app-runtime.js`
  - `loadTools`: read from `static/app-meeting.js`
  - `ownerTabId` / `ownerInstance` / owner session IIFE: read from `static/app-core.js`; `switchRoom`: read from `static/app-runtime.js`
  - `apiError` / `post`: read from `static/app-core.js`
  - `fallbackCopy` / `copyText`: read exact functions from `static/app-core.js`
  - `visibilitychange` + interval loop: read from `static/app-runtime.js`
- In `tests/test_meeting_navigation.py`:
  - `test_toolbar_details_close_and_focus`: read `const meetingToolsButton=` .. `function fmtK(` slice from `static/app-meeting.js`.

- [ ] **Step 2: Run targeted tests and verify**

Run:
- `python tests/test_frontend_runtime.py`
- `python tests/test_meeting_navigation.py`
- `python tests/test_icons.py`
- `python tests/test_server_runtime.py`
- `python tests/test_model_settings.py`
- `python tests/test_agent_settings.py`
- `python tests/test_update_ui.py`
Expected: ALL PASS.

- [ ] **Step 3: Run static checks and full test suite after final edits**

Run:
- `python -m mypy bridge`
- `ruff check bridge tests/test_pal.py tests/test_logging_and_errors.py`
- `python tests/run_all.py`
- Update `reports/CODE_REVIEW_FIX_HANDOFF.md` and `task.md` artifact with exact post-edit results.
