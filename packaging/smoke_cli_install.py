"""Install via the published bootstrap commands with a fresh managed Python."""
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from threading import Thread

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ("bridge", "static", "index.html", "roundtable.py", "pyproject.toml", "README.md", "LICENSE",
           "docs/CLI.md", "packaging/member-readme.md", "packaging/start-member.bat", "packaging/start-member.command")


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".ps1": "text/plain; charset=utf-8"}


def main():
    with tempfile.TemporaryDirectory(prefix="any-cli-smoke-") as work:
        root = Path(work)
        site = root / "site"
        (site / "cli").mkdir(parents=True)
        for wrapper in ("install-cli.ps1", "install-cli.sh", "install-cli.py"):
            shutil.copyfile(ROOT / "website" / wrapper, site / wrapper)
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        archive = site / "cli" / f"any-cli-{commit}.tar.gz"
        subprocess.run(["git", "archive", "--format=tar.gz", "--prefix=AnY-CLI/", f"--output={archive}",
                        "HEAD", "--", *SOURCES], cwd=ROOT, check=True)
        payload = archive.read_bytes()
        (site / "cli" / "current.json").write_text(json.dumps({
            "commit": commit, "sha256": hashlib.sha256(payload).hexdigest(), "size": len(payload)
        }), encoding="utf-8")

        home = root / "home"
        home.mkdir()
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=site))
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}/"
            env = dict(os.environ, HOME=str(home), USERPROFILE=str(home), APPDATA=str(home), LOCALAPPDATA=str(home),
                       XDG_DATA_HOME=str(home), UV_CACHE_DIR=str(root / "uv-cache"),
                       UV_PYTHON_INSTALL_DIR=str(root / "managed-python"), ANY_CLI_TEST_SOURCE=base,
                       ANY_CLI_MANAGED_PYTHON="1", ANY_CLI_INSTALL_DIR=str(root / "cli"), PYTHONUTF8="1")
            if sys.platform == "win32":
                env = {key: value for key, value in env.items() if key.upper() != "PSMODULEPATH"}
                # WinPS must rebuild its own module path when launched from PowerShell 7.
                command = f'irm {base}install-cli.ps1 | iex; if (-not $?) {{ exit 1 }}; any --help; exit $LASTEXITCODE'
                args = ["powershell.exe", "-NoProfile", "-Command", command]
            else:
                command = f'curl -fsSL {base}install-cli.sh | bash -s -- --install-only && "$HOME/.local/bin/any" --help'
                args = ["bash", "-o", "pipefail", "-c", command]
            output = subprocess.check_output(args, env=env, stdin=subprocess.DEVNULL)
            if b"usage:" not in output.lower() or not list((root / "managed-python").glob("cpython-3.12*")):
                raise SystemExit("Managed Python or any --help output missing")
            print(output.decode("utf-8", errors="replace"))
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    main()
