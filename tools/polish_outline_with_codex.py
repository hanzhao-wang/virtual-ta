from __future__ import annotations

import argparse
import shutil
import subprocess
from lib.common import read_json, relative_to_repo, repo_path, resolve_config
from lib.render import render_outline_markdown, write_markdown


def main() -> int:
    parser = argparse.ArgumentParser(description="Use Codex to polish the cached lecture outline.")
    parser.add_argument("--config", help="Path to config TOML file.")
    args = parser.parse_args()

    codex_bin = shutil.which("codex")
    if codex_bin is None:
        raise SystemExit("Could not find `codex` on PATH.")

    _, config = resolve_config(args.config)
    cache_cfg = config["cache"]

    seed_json = repo_path(cache_cfg["outline_seed_json"])
    outline_json = repo_path(cache_cfg["outline_json"])
    outline_md = repo_path(cache_cfg["outline_markdown"])
    schema_path = repo_path("config/course_outline_output.schema.json")
    repo_root = repo_path(".")

    if not seed_json.exists():
        raise SystemExit(
            f"Seed outline missing at {seed_json}. Run tools/build_outline_cache.py first."
        )

    prompt = f"""\
Read `{relative_to_repo(seed_json)}` and produce a cleaner structured course outline for a student-facing virtual TA.

Requirements:
- Keep the outline concise and useful for future question answering.
- Merge obviously duplicate topics.
- Preserve source file path traceability.
- Do not invent lectures, topics, or source paths.
- Return JSON only matching the supplied schema.
"""

    command = [
        codex_bin,
        "exec",
        "--sandbox",
        "read-only",
        "--skip-git-repo-check",
        "--output-schema",
        str(schema_path),
        "-o",
        str(outline_json),
        prompt,
    ]
    subprocess.run(command, cwd=repo_root, check=True, stdin=subprocess.DEVNULL)

    payload = read_json(outline_json)
    write_markdown(outline_md, render_outline_markdown(payload))

    print(f"Wrote polished outline JSON to {relative_to_repo(outline_json)}")
    print(f"Wrote polished outline Markdown to {relative_to_repo(outline_md)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
