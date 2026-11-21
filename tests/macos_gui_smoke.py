"""Exercise the packaged AppKit/WKWebView window on a macOS Actions runner."""

import argparse
import io
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import time
import urllib.request
import zipfile


def wait_until(description, predicate, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(0.3)
    raise RuntimeError(f"Timed out waiting for {description}")


def apple_script(source, *args):
    result = subprocess.run(
        ["/usr/bin/osascript", "-e", source, *map(str, args)], text=True,
        capture_output=True, timeout=40,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def activate(pid):
    return apple_script("""
on run argv
    set targetPID to item 1 of argv as integer
    tell application "System Events"
        set targetApp to first application process whose unix id is targetPID
        if not (exists window 1 of targetApp) then return ""
        set frontmost of targetApp to true
        return name of window 1 of targetApp
    end tell
end run
""", pid)


def web_button(pid, label, press=True):
    return apple_script("""
on run argv
    set targetPID to item 1 of argv as integer
    set targetLabel to item 2 of argv
    set shouldPress to item 3 of argv is "press"
    tell application "System Events"
        tell (first application process whose unix id is targetPID)
            set primaryWindow to first window whose name is "合拍 Cojam"
            set windowElements to entire contents of primaryWindow
            repeat with elementRef in windowElements
                set candidate to contents of elementRef
                if role of candidate is "AXButton" then
                    if (name of candidate is targetLabel) or (description of candidate is targetLabel) then
                        if enabled of candidate then
                            if shouldPress then perform action "AXPress" of candidate
                            return "found"
                        end if
                    end if
                end if
            end repeat
        end tell
    end tell
    return ""
end run
""", pid, label, "press" if press else "check")


def paste_text(text):
    subprocess.run(["/usr/bin/pbcopy"], input=text.encode("utf-8"), check=True, timeout=5)
    apple_script('tell application "System Events" to keystroke "v" using command down')


def capture(output, name):
    subprocess.run(["/usr/sbin/screencapture", "-x", str(output / f"{name}.png")],
                   check=False, timeout=10)


def request(base, path, token=None):
    headers = {"X-RT-Token": token} if token else {}
    req = urllib.request.Request(base + path, headers=headers)
    with urllib.request.urlopen(req, timeout=3) as response:
        return response.read()


def ready(base):
    try:
        return json.loads(request(base, "/api/server/info"))
    except OSError:
        return None


def close_window(pid):
    apple_script("""
on run argv
    set targetPID to item 1 of argv as integer
    tell application "System Events"
        tell (first application process whose unix id is targetPID)
            set closeButton to value of attribute "AXCloseButton" of window "合拍 Cojam"
            perform action "AXPress" of closeButton
        end tell
    end tell
end run
""", pid)


def verify_gui(app, output):
    output.mkdir(parents=True, exist_ok=True)
    workdir = output / "Selected project folder"
    workdir.mkdir()
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    env = dict(os.environ, ROUNDTABLE_PORT=str(port), ROUNDTABLE_LOG_DIR=str(output / "data"),
               ROUNDTABLE_DEFAULT_DIR=str(output), ROUNDTABLE_NO_PRESETS="1", PYTHONUNBUFFERED="1")
    with (output / "desktop.log").open("wb") as log:
        app_process = subprocess.Popen([str(app / "Contents/MacOS/Cojam")], env=env,
                                       stdout=log, stderr=log)
        try:
            wait_until("packaged Cojam backend", lambda: ready(base), timeout=50)
            page = request(base, "/").decode("utf-8")
            token = re.search(r'name="rt-token" content="([^"]+)"', page)[1]
            if b"/api/projects/choose-workdir" not in request(base, "/static/workspace.js"):
                raise RuntimeError("Packaged front end is missing the folder picker")
            with zipfile.ZipFile(io.BytesIO(request(base, "/static/member-connector.zip", token))) as archive:
                if archive.testzip() is not None:
                    raise RuntimeError("Packaged member connector is corrupt")
            title = wait_until("Cojam AppKit window", lambda: activate(app_process.pid))
            if title != "合拍 Cojam":
                raise RuntimeError(f"Unexpected native window title: {title}")
            wait_until("New Project button", lambda: web_button(app_process.pid, "新建项目", press=False))
            capture(output, "01-desktop")
            print("The packaged native window is visible.", flush=True)

            wait_until("New Project button", lambda: web_button(app_process.pid, "新建项目"))
            wait_until("folder picker button", lambda: web_button(app_process.pid, "选择文件夹"))
            time.sleep(1)
            capture(output, "02-folder-picker")
            apple_script('tell application "System Events" to key code 53')
            time.sleep(1)
            print("Opened and cancelled the native folder panel.", flush=True)

            # Reopening the form focuses its project-name input.
            wait_until("project cancel button", lambda: web_button(app_process.pid, "取消"))
            wait_until("New Project button", lambda: web_button(app_process.pid, "新建项目"))
            time.sleep(0.5)
            paste_text("Cojam GUI verification")
            wait_until("folder picker button after cancel", lambda: web_button(app_process.pid, "选择文件夹"))
            time.sleep(1)
            apple_script('tell application "System Events" to keystroke "g" using {command down, shift down}')
            time.sleep(0.7)
            paste_text(str(workdir))
            time.sleep(0.7)
            apple_script('tell application "System Events" to key code 36')
            time.sleep(0.8)
            apple_script('tell application "System Events" to key code 36')
            wait_until("Create Project button", lambda: web_button(app_process.pid, "创建项目"))

            def selected_project():
                projects = json.loads(request(base, "/api/rooms", token))["projects"]
                return any(project["name"] == "Cojam GUI verification"
                           and Path(project["workdir"]).resolve() == workdir.resolve()
                           for project in projects)

            wait_until("project with selected local folder", selected_project)
            capture(output, "03-project-created")
            print("Project saved with the folder selected in the native panel.", flush=True)
            close_window(app_process.pid)
            if app_process.wait(timeout=20):
                raise RuntimeError("Desktop app did not exit successfully")
            wait_until("backend shutdown after closing the native window", lambda: ready(base) is None)
            print("Closing the window stopped the packaged backend.", flush=True)
        except Exception:
            capture(output, "failure")
            raise
        finally:
            if app_process.poll() is None:
                app_process.terminate()
                app_process.wait(timeout=10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    verify_gui(args.app, args.output)
