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
    read_jsonl,
    slugify,
    utc_now_iso,
    write_json,
)
from lib.memory import load_concepts, record_attempt, render_mistake_form, mistake_form_path
from lib.retrieval import retrieve


def choose_outline_path(cache_cfg: dict[str, Any]) -> Path | None:
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


def output_stem(topic: str, label: str) -> Path:
    slug = slugify(topic)[:50]
    stamp = utc_now_iso().replace(":", "-")
    return repo_path(f"practice/sessions/{stamp}--{label}--{slug}")


def source_ref_from_result(result: dict[str, Any]) -> dict[str, str]:
    return {
        "path": result.get("source_path", ""),
        "file_type": result.get("file_type", ""),
        "locator_type": result.get("locator_type", ""),
        "locator": str(result.get("locator", "")),
        "reason": result.get("title", "") or "Retrieved local course evidence.",
    }


def memory_summary(config: dict[str, Any], profile: str | None) -> str:
    concepts = load_concepts(config, profile)
    if not concepts:
        return "No mistake memory yet."
    ordered = sorted(
        concepts.values(),
        key=lambda item: (
            {"needs_review": 0, "improving": 1, "mastered": 2}.get(item.get("status", ""), 3),
            item.get("concept", ""),
        ),
    )
    lines = []
    for state in ordered[:8]:
        errors = "; ".join(state.get("common_errors", [])[:2]) or "none recorded"
        lines.append(
            f"- {state.get('concept', '')}: {state.get('status', '')}, "
            f"last score {state.get('last_score', '')}, common errors: {errors}"
        )
    return "\n".join(lines)


def run_codex(command: list[str]) -> None:
    subprocess.run(command, cwd=repo_path("."), check=True, stdin=subprocess.DEVNULL)


def generate_question(args: argparse.Namespace) -> int:
    codex_bin = shutil.which("codex")
    if codex_bin is None:
        raise SystemExit("Could not find `codex` on PATH.")

    _, config = resolve_config(args.config)
    cache_cfg = config["cache"]
    retrieval_cfg = config["retrieval"]
    retrieval_root = ensure_dir(repo_path(cache_cfg["retrieval_root"]))
    db_path = repo_path(cache_cfg["sqlite_index"])
    chunks_path = repo_path(cache_cfg["chunks"])
    outline_path = choose_outline_path(cache_cfg)
    if outline_path is None:
        manifest_rows = read_jsonl(repo_path(cache_cfg["manifest"]))
        if manifest_rows:
            outline_note = "No outline cache is available; rely on the retrieval payload and manifest."
            outline_read_line = ""
        else:
            raise SystemExit("No outline cache found. Ask Codex to index the course materials first.")
    else:
        outline_note = f"Use outline cache `{relative_to_repo(outline_path)}`."
        outline_read_line = f"- `{relative_to_repo(outline_path)}`"

    retrieval_payload = retrieve(
        args.topic,
        db_path=db_path,
        chunks_path=chunks_path,
        top_k=args.top_k or int(retrieval_cfg.get("default_top_k", 8)),
    )
    retrieval_path = retrieval_root / f"{utc_now_iso().replace(':', '-')}-{slugify(args.topic)[:40]}-interactive.json"
    write_json(retrieval_path, retrieval_payload)

    stem = output_stem(args.topic, "question")
    out_json = repo_path(args.out) if args.out else stem.with_suffix(".json")
    schema_path = repo_path("config/interactive_question.schema.json")

    focus = args.focus or "Use the student's mistake memory when it is relevant; otherwise test the requested topic."
    files_to_read = "\n".join(line for line in [outline_read_line, f"- `{relative_to_repo(retrieval_path)}`"] if line)
    prompt = f"""\
Generate exactly one interactive practice question for a business student.

Read these files first:
{files_to_read}

Outline note:
{outline_note}

Topic request:
{args.topic}

Difficulty:
{args.difficulty}

Mistake memory summary for this student:
{memory_summary(config, args.profile)}

Focus instruction:
{focus}

Requirements:
- Return JSON only matching the supplied schema.
- Ask one new question only.
- Do not reveal the expected answer in the `question` field.
- Keep the question self-contained so Codex can show it directly in chat.
- Use local course material first and preserve source refs from retrieval.
- Include `expected_answer` and `rubric` for later grading.
- If this is a retry, vary the scenario, numbers, distribution, or wording while testing the same concept.
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
    run_codex(command)
    payload = read_json(out_json)
    print(render_question_for_chat(payload, out_json))
    return 0


def render_question_for_chat(payload: dict[str, Any], path: Path) -> str:
    concepts = ", ".join(payload.get("concepts", [])) or "not specified"
    lines = [
        f"Question ID: {payload.get('id', '')}",
        f"Difficulty: {payload.get('difficulty', '')}",
        f"Marks: {payload.get('marks', '')}",
        f"Concepts: {concepts}",
        "",
        payload.get("instructions", "").strip(),
        "",
        payload.get("question", "").strip(),
        "",
        f"Internal question record: {relative_to_repo(path)}",
        "Reply with your answer, or upload a file containing your answer.",
    ]
    return "\n".join(line for line in lines if line is not None).strip()


def read_answer(args: argparse.Namespace) -> str:
    if args.answer_file:
        return repo_path(args.answer_file).read_text(encoding="utf-8", errors="ignore").strip()
    if args.answer:
        return args.answer.strip()
    raise SystemExit("Provide --answer or --answer-file.")


def grade_answer(args: argparse.Namespace) -> int:
    codex_bin = shutil.which("codex")
    if codex_bin is None:
        raise SystemExit("Could not find `codex` on PATH.")

    _, config = resolve_config(args.config)
    question_path = repo_path(args.question_json)
    question_payload = read_json(question_path)
    student_answer = read_answer(args)
    schema_path = repo_path("config/interactive_feedback.schema.json")
    stem = output_stem(question_payload.get("topic_request", "interactive"), "feedback")
    out_json = repo_path(args.out) if args.out else stem.with_suffix(".json")

    prompt = f"""\
Grade this student's interactive practice answer.

Question JSON:
{question_payload}

Student answer:
{student_answer}

Requirements:
- Return JSON only matching the supplied schema.
- Score from 0 to 1 using the rubric.
- Be direct and supportive, but precise.
- Keep `direct_feedback` concise enough to show in Codex chat.
- Include the correct model answer.
- Preserve source refs from the question when they support the feedback.
- Set `memory_note` to the mistake pattern that should be remembered if score is below 0.8; otherwise record what improved.
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
    run_codex(command)
    feedback = read_json(out_json)

    concepts = feedback.get("concepts") or question_payload.get("concepts", [])
    source_refs = feedback.get("source_refs") or question_payload.get("source_refs", [])
    record_attempt(
        config,
        profile=args.profile,
        question=question_payload.get("question", ""),
        student_answer=student_answer,
        score=float(feedback.get("score", 0)),
        feedback=feedback.get("memory_note") or feedback.get("direct_feedback", ""),
        concepts=concepts,
        source_refs=source_refs,
        question_id=feedback.get("question_id") or question_payload.get("id", ""),
    )

    review_path = mistake_form_path(config, args.profile)
    ensure_dir(review_path.parent)
    review_path.write_text(render_mistake_form(config, args.profile), encoding="utf-8")

    print(render_feedback_for_chat(feedback, out_json, review_path))
    return 0


def render_feedback_for_chat(payload: dict[str, Any], path: Path, review_path: Path) -> str:
    lines = [
        f"Score: {payload.get('score', 0):.2f}",
        "",
        payload.get("direct_feedback", "").strip(),
        "",
        "What was good:",
    ]
    strengths = payload.get("strengths", [])
    lines.extend([f"- {item}" for item in strengths] or ["- Nothing specific recorded."])
    lines.append("")
    lines.append("Corrections:")
    corrections = payload.get("corrections", [])
    lines.extend([f"- {item}" for item in corrections] or ["- None."])
    lines.extend(
        [
            "",
            "Model answer:",
            payload.get("model_answer", "").strip(),
            "",
            "Next step:",
            payload.get("next_step", "").strip(),
            "",
            f"Internal feedback record: {relative_to_repo(path)}",
            f"Mistake review updated: {relative_to_repo(review_path)}",
        ]
    )
    return "\n".join(lines).strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Internal one-question interactive practice workflow.")
    parser.add_argument("--config", default="config/virtual_ta.toml", help="Path to config TOML file.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    question_parser = subparsers.add_parser("question", help="Generate one question for Codex to show in chat.")
    question_parser.add_argument("--topic", required=True, help="Topic or retry request.")
    question_parser.add_argument("--difficulty", default="mixed", help="Difficulty level.")
    question_parser.add_argument("--profile", help="Student profile name.")
    question_parser.add_argument("--focus", help="Optional adaptation instruction.")
    question_parser.add_argument("--top-k", type=int, help="Retrieval chunks to use.")
    question_parser.add_argument("--out", help="Output JSON path.")
    question_parser.set_defaults(func=generate_question)

    grade_parser = subparsers.add_parser("grade", help="Grade a submitted answer and update memory.")
    grade_parser.add_argument("--question-json", required=True, help="Question JSON file from the question step.")
    grade_parser.add_argument("--answer", help="Student answer text.")
    grade_parser.add_argument("--answer-file", help="Path to an uploaded answer file.")
    grade_parser.add_argument("--profile", help="Student profile name.")
    grade_parser.add_argument("--out", help="Output JSON path.")
    grade_parser.set_defaults(func=grade_answer)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
