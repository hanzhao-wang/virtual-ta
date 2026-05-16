from __future__ import annotations

import argparse
import subprocess
import sys

from lib.common import repo_path


def run_step(command: list[str]) -> None:
    subprocess.run(command, cwd=repo_path("."), check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh the local course cache and outline.")
    parser.add_argument("--config", default="config/virtual_ta.toml", help="Path to config TOML file.")
    parser.add_argument("--polish", action="store_true", help="Also run the Codex outline-polish step.")
    args = parser.parse_args()

    run_step([sys.executable, "tools/prepare_course_materials.py", "--config", args.config])
    run_step([sys.executable, "tools/build_outline_cache.py", "--config", args.config])

    if args.polish:
        run_step([sys.executable, "tools/polish_outline_with_codex.py", "--config", args.config])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
