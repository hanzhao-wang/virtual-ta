from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from lib.common import read_jsonl, relative_to_repo, repo_path, resolve_config, write_text
from lib.memory import mistake_form_path, record_attempt, render_mistake_form


REQUIRED_MODULES = {
    "pypdf": "pypdf",
    "pptx": "python-pptx",
    "docx": "python-docx",
    "bs4": "beautifulsoup4",
    "openpyxl": "openpyxl",
}


def run_python_script(script: str, args: list[str]) -> int:
    command = [sys.executable, script, *args]
    return subprocess.run(command, cwd=repo_path("."), check=False).returncode


def check_module(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def doctor(args: argparse.Namespace) -> int:
    _, config = resolve_config(args.config)
    cache_cfg = config["cache"]
    failures = 0

    print("# Virtual TA doctor")
    print("")
    print("## Python packages")
    for module, package in REQUIRED_MODULES.items():
        ok = check_module(module)
        print(f"- {package}: {'ok' if ok else 'missing'}")
        if not ok:
            failures += 1

    print("")
    print("## External tools")
    codex_ok = shutil.which("codex") is not None
    print(f"- codex: {'ok' if codex_ok else 'missing'}")
    if not codex_ok:
        failures += 1
    compiler = config.get("latex", {}).get("compiler", "pdflatex")
    print(f"- {compiler}: {'ok' if shutil.which(compiler) else 'missing (needed only for PDF practice)'}")
    print(f"- LibreOffice: {'ok' if (shutil.which('libreoffice') or shutil.which('soffice')) else 'missing (needed only for .ppt/.doc/.xls conversion)'}")

    print("")
    print("## Material roots")
    material_files = 0
    for category, roots in config.get("materials", {}).items():
        for root_str in roots:
            root = repo_path(root_str)
            count = sum(1 for path in root.rglob("*") if path.is_file()) if root.exists() else 0
            material_files += count
            print(f"- {category}: `{root_str}` - {'ok' if root.exists() else 'missing'} ({count} files)")
    if material_files == 0:
        failures += 1

    print("")
    print("## Cache")
    cache_paths = [
        cache_cfg["manifest"],
        cache_cfg["chunks"],
        cache_cfg["sqlite_index"],
        cache_cfg["catalog_markdown"],
        cache_cfg["outline_seed_json"],
    ]
    for cache_path in cache_paths:
        path = repo_path(cache_path)
        print(f"- `{cache_path}`: {'ok' if path.exists() else 'missing'}")

    manifest = read_jsonl(repo_path(cache_cfg["manifest"]))
    attention = [row for row in manifest if row.get("extraction_status") in {"caption_needed", "partial", "unsupported", "failed"}]
    print("")
    print("## Files needing attention")
    if attention:
        for row in attention[:25]:
            print(f"- `{row.get('source_path', '')}`: {row.get('extraction_status', '')}")
        if len(attention) > 25:
            print(f"- ... {len(attention) - 25} more")
    else:
        print("- None")

    if failures:
        print("")
        print("Install missing Python packages with: python -m pip install -r requirements.txt")
        return 1
    return 0


def index(args: argparse.Namespace) -> int:
    if args.auto_caption:
        caption_code = run_python_script("tools/caption_images_with_codex.py", ["--config", args.config])
        if caption_code != 0:
            return caption_code
    command = ["--config", args.config]
    if args.polish:
        command.append("--polish")
    return run_python_script("tools/refresh_course_knowledge.py", command)


def ask(args: argparse.Namespace) -> int:
    command = ["--config", args.config, "--question", args.question]
    if args.top_k:
        command.extend(["--top-k", str(args.top_k)])
    if args.live_search:
        command.append("--live-search")
    if args.out:
        command.extend(["--out", args.out])
    return run_python_script("tools/run_answer.py", command)


def practice(args: argparse.Namespace) -> int:
    command = [
        "--config",
        args.config,
        "--topic",
        args.topic,
        "--kind",
        args.kind,
        "--difficulty",
        args.difficulty,
        "--num-questions",
        str(args.num_questions),
    ]
    if args.output_format:
        command.extend(["--format", args.output_format])
    if args.out:
        command.extend(["--out", args.out])
    return run_python_script("tools/generate_practice.py", command)


def mistakes(args: argparse.Namespace) -> int:
    _, config = resolve_config(args.config)
    content = render_mistake_form(config, args.profile)
    out_path = repo_path(args.out) if args.out else mistake_form_path(config, args.profile)
    write_text(out_path, content)
    print(f"Wrote mistake review form to {relative_to_repo(out_path)}")
    return 0


def parse_source_refs(source_ref_json: str | None) -> list[dict[str, Any]]:
    if not source_ref_json:
        return []
    value = json.loads(source_ref_json)
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    raise SystemExit("--source-ref-json must be a JSON object or array")


def record(args: argparse.Namespace) -> int:
    _, config = resolve_config(args.config)
    result = record_attempt(
        config,
        profile=args.profile,
        question=args.question,
        student_answer=args.student_answer,
        score=args.score,
        feedback=args.feedback,
        concepts=args.concept,
        source_refs=parse_source_refs(args.source_ref_json),
        question_id=args.question_id or "",
    )
    concepts = ", ".join(result["attempt"]["concepts"])
    print(f"Recorded attempt for: {concepts}")
    return 0


def caption_images(args: argparse.Namespace) -> int:
    command = ["--config", args.config]
    if args.overwrite:
        command.append("--overwrite")
    if args.dry_run:
        command.append("--dry-run")
    if args.limit:
        command.extend(["--limit", str(args.limit)])
    return run_python_script("tools/caption_images_with_codex.py", command)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Student Virtual TA command wrapper.")
    parser.add_argument("--config", default="config/virtual_ta.toml", help="Path to config TOML file.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser("doctor", help="Check dependencies, materials, cache, and caption tasks.")
    doctor_parser.set_defaults(func=doctor)

    index_parser = subparsers.add_parser("index", help="Refresh extraction, retrieval, and outline caches.")
    index_parser.add_argument("--polish", action="store_true", help="Also polish the outline with Codex.")
    index_parser.add_argument("--auto-caption", action="store_true", help="Generate missing image captions with Codex vision before indexing.")
    index_parser.set_defaults(func=index)

    caption_parser = subparsers.add_parser("caption-images", help="Generate missing image captions with Codex vision.")
    caption_parser.add_argument("--overwrite", action="store_true", help="Regenerate existing captions.")
    caption_parser.add_argument("--dry-run", action="store_true", help="List images that would be captioned.")
    caption_parser.add_argument("--limit", type=int, help="Maximum number of images to caption.")
    caption_parser.set_defaults(func=caption_images)

    ask_parser = subparsers.add_parser("ask", help="Answer a question from local course material first.")
    ask_parser.add_argument("question", help="Student question.")
    ask_parser.add_argument("--top-k", type=int, help="Number of retrieval chunks to pass to Codex.")
    ask_parser.add_argument("--live-search", action="store_true", help="Allow live search after local retrieval.")
    ask_parser.add_argument("--out", help="Output path (.md or .json).")
    ask_parser.set_defaults(func=ask)

    practice_parser = subparsers.add_parser("practice", help="Generate an exercise set.")
    practice_parser.add_argument("topic", help="Topic or practice request.")
    practice_parser.add_argument("--difficulty", default="mixed", help="Difficulty level.")
    practice_parser.add_argument("--num-questions", type=int, default=5, help="Number of questions.")
    practice_parser.add_argument("--format", dest="output_format", choices=["markdown", "tex", "pdf"], help="Rendered output format.")
    practice_parser.add_argument("--out", help="Output path (.md, .json, .tex, or .pdf).")
    practice_parser.set_defaults(func=practice, kind="exercise_set")

    mock_parser = subparsers.add_parser("mock", help="Generate a mock exam.")
    mock_parser.add_argument("topic", help="Topic or exam coverage request.")
    mock_parser.add_argument("--difficulty", default="mixed", help="Difficulty level.")
    mock_parser.add_argument("--num-questions", type=int, default=6, help="Number of questions.")
    mock_parser.add_argument("--format", dest="output_format", choices=["markdown", "tex", "pdf"], default="pdf", help="Rendered output format.")
    mock_parser.add_argument("--out", help="Output path (.md, .json, .tex, or .pdf).")
    mock_parser.set_defaults(func=practice, kind="mock_exam")

    mistakes_parser = subparsers.add_parser("mistakes", help="Write a mistake review form from local memory.")
    mistakes_parser.add_argument("--profile", help="Student profile name.")
    mistakes_parser.add_argument("--out", help="Output Markdown path.")
    mistakes_parser.set_defaults(func=mistakes)

    record_parser = subparsers.add_parser("record-attempt", help="Record a graded practice attempt into local memory.")
    record_parser.add_argument("--profile", help="Student profile name.")
    record_parser.add_argument("--question", required=True, help="Question attempted.")
    record_parser.add_argument("--student-answer", required=True, help="Student answer.")
    record_parser.add_argument("--score", required=True, type=float, help="Score from 0 to 1.")
    record_parser.add_argument("--feedback", required=True, help="Brief feedback or common error.")
    record_parser.add_argument("--concept", action="append", required=True, help="Concept tag. Repeat for multiple concepts.")
    record_parser.add_argument("--question-id", help="Optional generated question id.")
    record_parser.add_argument("--source-ref-json", help="Optional JSON source ref object or array.")
    record_parser.set_defaults(func=record)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
