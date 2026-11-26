"""Package the existing stdio bridge as a standalone Python zipapp."""

import argparse
import io
from pathlib import Path
import tomllib
import zipfile


ROOT = Path(__file__).resolve().parents[1]
BRIDGE_SOURCES = (
    "bridge/__init__.py",
    "bridge/mcp_stdio.py",
    "bridge/common.py",
    "bridge/pal/__init__.py",
    "bridge/pal/_shared.py",
    "bridge/pal/_posix.py",
    "bridge/pal/_win32.py",
)


def build(output_dir: Path) -> Path:
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    executable = io.BytesIO()
    with zipfile.ZipFile(executable, "w", zipfile.ZIP_DEFLATED) as app:
        app.writestr("__main__.py", "from bridge.mcp_stdio import main\nraise SystemExit(main())\n")
        for source in BRIDGE_SOURCES:
            app.write(ROOT / source, source)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"AnY-MCP-{version}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("any-mcp.pyz", executable.getvalue())
        bundle.write(ROOT / "website" / "mcp-setup.md", "README.md")
        bundle.write(ROOT / "LICENSE", "LICENSE")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    print(build(parser.parse_args().output_dir))
