from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

from lib.common import (
    ensure_dir,
    read_json,
    relative_to_repo,
    repo_path,
    resolve_config,
    slugify,
    utc_now_iso,
    write_json,
)
from lib.render import render_answer_markdown, write_markdown
from lib.retrieval import retrieve


def choose_outline_path(cache_cfg: dict) -> Path | None:
    preferred = [
        repo_path(cache_cfg["outline_json"]),
        repo_path(cache_cfg["outline_markdown"]),
        repo_path(cache_cfg["outline_seed_json"]),
        repo_path(cache_cfg["outline_seed_markdown"]),
    ]
    for path in preferred:
        if path.exists():
            return path
    return None


def compute_output_paths(out_arg: str | None, question: str) -> tuple[Path, Path]:
    if out_arg:
        out_path = repo_path(out_arg)
        if out_path.suffix.lower() == ".json":
            return out_path, out_path.with_suffix(".md")
        if out_path.suffix.lower() == ".md":
            return out_path.with_suffix(".json"), out_path
        return out_path.with_suffix(".json"), out_path.with_suffix(".md")

    slug = slugify(question)[:60]
    stem = f"{utc_now_iso().replace(':', '-')}--{slug}"
    return repo_path(f"answers/{stem}.json"), repo_path(f"answers/{stem}.md")


def main() -> int:
    parser = argparse.ArgumentParser(description="Answer a student question using local course materials and Codex.")
    parser.add_argument("--config", help="Path to config TOML file.")
    parser.add_argument("--question", required=True, help="Student question.")
    parser.add_argument("--top-k", type=int, help="Number of retrieved chunks to pass into Codex.")
    parser.add_argument("--live-search", action="store_true", help="Allow Codex live web search for out-of-scope/current questions.")
    parser.add_argument("--out", help="Output path (.md or .json).")
    args = parser.parse_args()

    codex_bin = shutil.which("codex")
    if codex_bin is None:
        raise SystemExit("Could not find `codex` on PATH.")

    _, config = resolve_config(args.config)
    cache_cfg = config["cache"]
    retrieval_cfg = config["retrieval"]

    db_path = repo_path(cache_cfg["sqlite_index"])
    chunks_path = repo_path(cache_cfg["chunks"])
    retrieval_root = ensure_dir(repo_path(cache_cfg["retrieval_root"]))
    schema_path = repo_path("config/answer_output.schema.json")
    repo_root = repo_path(".")

    top_k = args.top_k or int(retrieval_cfg.get("default_top_k", 8))
    retrieval_payload = retrieve(args.question, db_path=db_path, chunks_path=chunks_path, top_k=top_k)

    retrieval_path = retrieval_root / f"{utc_now_iso().replace(':', '-')}-{slugify(args.question)[:40]}.json"
    write_json(retrieval_path, retrieval_payload)

    outline_path = choose_outline_path(cache_cfg)
    if outline_path is None:
        raise SystemExit(
            "No outline cache found. Run tools/build_outline_cache.py (and optionally tools/polish_outline_with_codex.py) first."
        )

    out_json, out_md = compute_output_paths(args.out, args.question)

    web_line = (
        "If local material is insufficient, you may use live web search. "
        "If you do, set support_level to `live_web_search` or `local_plus_general_reasoning` as appropriate and fill `web_sources`."
        if args.live_search
        else
        "Do not use live web search. If local material is insufficient, answer from careful general reasoning only and label that clearly."
    )

    prompt = f"""    $student-answer

Answer the student's question using the local outline cache and the prepared retrieval payload.

Read these files first:
- `{relative_to_repo(outline_path)}`
- `{relative_to_repo(retrieval_path)}`

Question:
{args.question}

Requirements:
- Use local course material first.
- Start with a direct answer.
- Include a simple example.
- Cite local file paths and locators in `local_sources` when the answer is supported by local materials.
- For each local source, copy `file_type`, `locator_type`, `locator`, `extraction_status`, and a short `excerpt` from the retrieval payload when available.
- Use page/slide/sheet/cell/question/caption locators exactly as provided; do not invent locators.
- If the answer goes beyond the course materials, say so clearly.
- {web_line}
- Return JSON only matching the provided schema.
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
        str(out_json),
    ]
    if args.live_search:
        command.extend(["-c", 'web_search="enabled"'])
    command.append(prompt)

    subprocess.run(command, cwd=repo_root, check=True, stdin=subprocess.DEVNULL)

    payload = read_json(out_json)
    write_markdown(out_md, render_answer_markdown(payload))

    print(f"Wrote answer JSON to {relative_to_repo(out_json)}")
    print(f"Wrote answer Markdown to {relative_to_repo(out_md)}")
    print(f"Retrieval payload: {relative_to_repo(retrieval_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
