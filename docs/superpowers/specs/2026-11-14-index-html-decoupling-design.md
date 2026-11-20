# Cojam Step 3: Frontend `index.html` Modularization Design (`5.1`)

**Date:** 2026-11-14
**Scope:** Extract inline CSS and inline JavaScript from `index.html` into modular static files, update frontend runtime/navigation tests, and preserve server caching and PyInstaller/Inno Setup packaging.

---

## 1. Existing Architecture Constraints Discovered

1. **Flat `/static/` routing & preload cache (`bridge/web.py`):**
   - `Handler.do_GET()` serves `/static/*` strictly matching `^/static/[\w.\-]+$` (`bridge/web.py:236`) — subdirectories such as `/static/js/...` are not matched.
   - `ExclusiveServer.__init__()` caches top-level `.js`, `.css`, `.html`, `.webmanifest` files via `os.listdir(STATIC)` (`bridge/web.py:939-942`) to bind frontend assets to the running backend generation.
2. **Existing classic-script frontend modules (`static/`):**
   - Seven modules (`workspace.js`, `connections.js`, `model-settings.js`, `agent-settings.js`, `execution-settings.js`, `update.js`, plus `qrcode.min.js`) and two stylesheets (`workspace.css`, `studio.css`) already live flat in `static/` and share classic global symbols (`RID`, `S`, `CONTACTS`, `PROJECTS`, `ROOMS`, `agCat`, `AG_DRV`, `esc`, `post`, `showModal`, `hideModal`, `copyText`, `poll`, `pollRooms`, `loadState`, `refreshContacts`, `openAi`).
   - Inline DOM attributes (e.g. `onclick="hideModal()"`) and Node `vm.runInContext` test suites (`tests/test_frontend_runtime.py`, `tests/test_meeting_navigation.py`) expect classic script semantics.
3. **CSS cascade order (`index.html` + `studio.css`):**
   - `static/studio.css` overrides `:root` design tokens originally declared in `index.html`'s inline `<style>`. Extracted base styles MUST load before `workspace.css` and `studio.css`.
4. **Packaging (`build_exe.ps1`, `packaging/build_macos.sh`, `.spec`):**
   - `--add-data "static;static"` already bundles every file inside `static/`.

---

## 2. Approaches Considered & Chosen Design

- **Rejected Alternative (Literal `5.1` `static/js/` + ES Modules):** Changing `<script type="module">` and nesting under `static/js/` would require changing `web.py` routing regex, changing `ExclusiveServer` recursive caching, rewriting all 7 existing `static/*.js` scripts and inline handlers into `import`/`export`, and rewriting all existing Node `vm` test suites. High churn for zero runtime benefit.
- **Chosen Approach (Flat `static/` CSS + Classic Modules):** Follow the repo's established flat `static/` convention. Zero backend routing/packaging changes needed; full compatibility with existing scripts and `ExclusiveServer.ui_assets`.

---

## 3. Target File Decomposition

- `index.html`: Pure semantic document structure (`<head>`, `<nav>`, `<header>`, `<div id="modal">`, `<aside id="side">`, `<div id="feed">`, `<div id="toc">`, `<div id="viewer">`, `<div id="jump">`, `<div id="status">`, `<footer>`) plus `<link rel="stylesheet">` and `<script src="/static/...">` tags. Zero inline `<style>` or `<script>` code blocks. Keeps `__RT_TOKEN__`, `/manifest.webmanifest`, `/static/icon-192.png?v=cojam-262`, and script ordering (`qrcode.min.js` before `connections.js`).
- `static/app.css`: All ~450 lines of core layout, dark/light theme base variables, message stream, modals, side drawer, viewer, and responsive breakpoints extracted from `index.html`, linked first before `workspace.css` and `studio.css`.
- `static/app-core.js`: `X-RT-Token` fetch wrapper, `ownerTabId` / `ownerInstance` / `/api/ui/session` lifecycle + `quitApp`, shared state globals (`feed`, `ta`, `st`, `touch`, `since`, `curMeeting`, `S`, `msgById`, `RID`, `api`), service worker registration, `esc`, `seenMap` / `markSeen`, modal management (`modal`, `mbox`, `showModal`, `hideModal`), `apiError`, `post`, and clipboard helpers (`fallbackCopy`, `copyText`).
- `static/app-chat.js`: Markdown rendering (`render`, `mdInline`, `mdBlock`), attachment chips & uploads (`fmtSize`, `attHtml`, `pend`, `drawPend`, `upload`, paste/drag-drop/file picker), quotes / selection tools / context menu (`setQuote`, `selIn`, `copyMessageText`, `placeMessageTools`, `updateSelectionTools`, `cmenu`), `send`, jump navigation (`jumpEl`, `holdable`, `syncJump`), and my-messages TOC (`tocEl`, `drawToc`, `openToc`, `closeToc`).
- `static/app-viewer.js`: Lightbox state & swipe navigation (`openViewer`, `closeViewer`, `showImg`, `step`) and canvas annotation/crop editor (`startEdit`, `drawArrow`, `finishDrag`, `undoEdit`, `vSave`, `vDone`).
- `static/app-meeting.js`: Status indicator (`lastRun`, `drawStatus`), toolbar & details side panel (`bar`, `meetingToolsButton`, `meetingSide`, `setMeetingSide`, `drawMeetingDetails`), goal & Kanban board (`ann*`, `drawBoard`, `boardPost`), file claims (`claimList`, `drawClaims`), participant capsules/quick-mentions/metadata (`AG_DRV`, `agCat`, `agentMeta`, `isAgent`, `drawCaps`, `drawQuick`, `drawStops`, `stopAi`, `drawState`, `syncUndo`, `undoStep`, `toggleMode`), and modals (`openList`, `openAi`, `loadTools`), ending with initial `drawQuick()`.
- `static/app-runtime.js`: Room polling & lifecycle (`polling`, `roomViewGeneration`, `poll`, `loadState`, `roomList`, `ROOMS`, `roomBadge`, `resetRoomView`, `switchRoom`, `popstate`, `roomGone`, `pickRoom`), `visibilitychange` listener, interval loops (`poll`, `pollRooms`, `refreshContacts`), and startup boot (`refreshContacts()`, `if (RID) switchRoom(RID, true); else pickRoom();`).

---

## 4. Test & Verification Plan

1. **Test migration (`tests/test_frontend_runtime.py`, `tests/test_meeting_navigation.py`):**
   - Point code-slice checks from `index.html` to the owning `static/app-*.js` module.
2. **New regression guards:**
   - Verify `index.html` contains no inline `<style>` or inline `<script>` body blocks, preserves stylesheet cascade order (`app.css` -> `workspace.css` -> `studio.css`), references only existing `/static/*` files, and maintains classic `<script>` order.
   - Load all 5 `static/app-*.js` modules sequentially into one shared Node `vm.createContext` with DOM/browser stubs to assert zero duplicate `let`/`const` redeclarations (`SyntaxError`) or boot-time `ReferenceError`s.
   - Verify `bridge.web.ExclusiveServer` preloads all extracted `app.css` and `app-*.js` assets in `ui_assets` and serves `GET /static/<file>` (`200`).
3. **Suite checks:** `tests/test_frontend_runtime.py`, `tests/test_meeting_navigation.py`, `tests/test_icons.py`, `tests/test_server_runtime.py`, `python -m mypy bridge`, `ruff check`, and full `python tests/run_all.py`.
