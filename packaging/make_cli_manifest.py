"""Generate website/cli-release.json metadata from bridge/version.py CLI_VERSION."""
import argparse
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read_cli_version(version_file: Path) -> str:
    tree = ast.parse(version_file.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "CLI_VERSION":
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        return node.value.value
    raise RuntimeError("CLI_VERSION not found in bridge/version.py")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--notes", default="改进终端协作体验并修复问题。")
    args = parser.parse_args()
    cli_version = _read_cli_version(ROOT / "bridge" / "version.py")
    output = ROOT / "website" / "cli-release.json"
    result = {
        "app": "AnY-CLI",
        "version": cli_version,
        "notes": args.notes[:1000],
    }
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
