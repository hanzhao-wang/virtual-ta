from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path
from typing import Any

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
from lib.render import render_practice_markdown, render_practice_tex, write_markdown
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


def compute_output_paths(out_arg: str | None, topic: str, kind: str) -> dict[str, Path]:
    if out_arg:
        out_path = repo_path(out_arg)
        if out_path.suffix.lower() == ".json":
            return {"json": out_path, "md": out_path.with_suffix(".md"), "tex": out_path.with_suffix(".tex"), "pdf": out_path.with_suffix(".pdf")}
        if out_path.suffix.lower() == ".md":
            return {"json": out_path.with_suffix(".json"), "md": out_path, "tex": out_path.with_suffix(".tex"), "pdf": out_path.with_suffix(".pdf")}
        if out_path.suffix.lower() == ".tex":
            return {"json": out_path.with_suffix(".json"), "md": out_path.with_suffix(".md"), "tex": out_path, "pdf": out_path.with_suffix(".pdf")}
        if out_path.suffix.lower() == ".pdf":
            return {"json": out_path.with_suffix(".json"), "md": out_path.with_suffix(".md"), "tex": out_path.with_suffix(".tex"), "pdf": out_path}
        return {"json": out_path.with_suffix(".json"), "md": out_path.with_suffix(".md"), "tex": out_path.with_suffix(".tex"), "pdf": out_path.with_suffix(".pdf")}

    slug = slugify(topic)[:60]
    stem = f"{utc_now_iso().replace(':', '-')}--{kind}--{slug}"
    base = repo_path(f"practice/{stem}")
    return {"json": base.with_suffix(".json"), "md": base.with_suffix(".md"), "tex": base.with_suffix(".tex"), "pdf": base.with_suffix(".pdf")}


def compile_tex(tex_path: Path, *, compiler: str) -> Path | None:
    compiler_bin = shutil.which(compiler)
    if compiler_bin is None:
        print(f"Could not find LaTeX compiler `{compiler}`. Wrote TeX only: {relative_to_repo(tex_path)}")
        return None

    command = [
        compiler_bin,
        "-interaction=nonstopmode",
        "-halt-on-error",
        tex_path.name,
    ]
    result = subprocess.run(command, cwd=tex_path.parent, capture_output=True, text=True)
    if result.returncode != 0:
        log_path = tex_path.with_suffix(".compile.log")
        log_path.write_text(result.stdout + "\n" + result.stderr, encoding="utf-8")
        print(f"LaTeX compilation failed. Wrote log to {relative_to_repo(log_path)}")
        return None
    pdf_path = tex_path.with_suffix(".pdf")
    return pdf_path if pdf_path.exists() else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate local practice exercises or a mock exam with Codex.")
    parser.add_argument("--config", help="Path to config TOML file.")
    parser.add_argument("--topic", required=True, help="Topic or topic request.")
    parser.add_argument(
        "--kind",
        choices=["exercise_set", "mock_exam"],
        default="exercise_set",
        help="Type of practice to generate.",
    )
    parser.add_argument("--difficulty", default="mixed", help="Difficulty level.")
    parser.add_argument("--num-questions", type=int, default=5, help="Number of questions.")
    parser.add_argument("--format", choices=["markdown", "tex", "pdf"], help="Rendered output format.")
    parser.add_argument("--out", help="Output path (.md, .json, .tex, or .pdf).")
    args = parser.parse_args()

    codex_bin = shutil.which("codex")
    if codex_bin is None:
        raise SystemExit("Could not find `codex` on PATH.")

    _, config = resolve_config(args.config)
    cache_cfg = config["cache"]
    retrieval_cfg = config["retrieval"]
    practice_cfg = config.get("practice", {})
    latex_cfg = config.get("latex", {})
    output_format = args.format or practice_cfg.get("default_format", "markdown")

    db_path = repo_path(cache_cfg["sqlite_index"])
    chunks_path = repo_path(cache_cfg["chunks"])
    retrieval_root = ensure_dir(repo_path(cache_cfg["retrieval_root"]))
    schema_path = repo_path("config/practice_output.schema.json")
    repo_root = repo_path(".")

    retrieval_payload = retrieve(
        args.topic,
        db_path=db_path,
        chunks_path=chunks_path,
        top_k=int(retrieval_cfg.get("default_top_k", 8)),
    )
    retrieval_path = retrieval_root / f"{utc_now_iso().replace(':', '-')}-{slugify(args.topic)[:40]}-practice.json"
    write_json(retrieval_path, retrieval_payload)

    outline_path = choose_outline_path(cache_cfg)
    if outline_path is None:
        raise SystemExit(
            "No outline cache found. Run tools/build_outline_cache.py (and optionally tools/polish_outline_with_codex.py) first."
        )

    out_paths = compute_output_paths(args.out, args.topic, args.kind)
    out_json = out_paths["json"]
    out_md = out_paths["md"]

    prompt = f"""    $generate-practice

Generate a {args.kind.replace('_', ' ')} from the course materials.

Read these files first:
- `{relative_to_repo(outline_path)}`
- `{relative_to_repo(retrieval_path)}`

Topic request:
{args.topic}

Requirements:
- Create {args.num_questions} questions.
- Difficulty: {args.difficulty}.
- Use course materials first.
- Create new questions inspired by the material rather than copying large chunks verbatim.
- Include answers and short explanations.
- Include source paths and source refs for each question. Use locator metadata from the retrieval payload when available.
- Include concepts, a concise rubric, and a variant seed for adaptive retry generation.
- Provide concise instructions and coverage notes.
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
        str(out_json),
        prompt,
    ]

    subprocess.run(command, cwd=repo_root, check=True, stdin=subprocess.DEVNULL)

    payload: dict[str, Any] = read_json(out_json)
    write_markdown(out_md, render_practice_markdown(payload))
    rendered_tex = False
    rendered_pdf = False
    if output_format in {"tex", "pdf"}:
        tex_path = out_paths["tex"]
        ensure_dir(tex_path.parent)
        tex_path.write_text(render_practice_tex(payload), encoding="utf-8")
        payload["tex_source_path"] = relative_to_repo(tex_path)
        rendered_tex = True
        if output_format == "pdf":
            pdf_path = compile_tex(tex_path, compiler=latex_cfg.get("compiler", "pdflatex"))
            if pdf_path is not None:
                payload["pdf_path"] = relative_to_repo(pdf_path)
                rendered_pdf = True
        write_json(out_json, payload)

    print(f"Wrote practice JSON to {relative_to_repo(out_json)}")
    print(f"Wrote practice Markdown to {relative_to_repo(out_md)}")
    if rendered_tex:
        print(f"Wrote practice TeX to {relative_to_repo(out_paths['tex'])}")
    if rendered_pdf:
        print(f"Wrote practice PDF to {relative_to_repo(out_paths['pdf'])}")
    print(f"Retrieval payload: {relative_to_repo(retrieval_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
