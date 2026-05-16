from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .common import ensure_dir, read_json, repo_path, utc_now_iso, write_json


def profile_dir(config: dict[str, Any], profile: str | None = None) -> Path:
    memory_cfg = config.get("memory", {})
    root = repo_path(memory_cfg.get("root", "memory/profiles"))
    profile_name = profile or memory_cfg.get("default_profile", "default")
    return ensure_dir(root / profile_name)


def attempts_path(config: dict[str, Any], profile: str | None = None) -> Path:
    return profile_dir(config, profile) / "attempts.jsonl"


def concepts_path(config: dict[str, Any], profile: str | None = None) -> Path:
    return profile_dir(config, profile) / "concepts.json"


def mistake_form_path(config: dict[str, Any], profile: str | None = None) -> Path:
    return profile_dir(config, profile) / "mistake_review.md"


def load_concepts(config: dict[str, Any], profile: str | None = None) -> dict[str, Any]:
    path = concepts_path(config, profile)
    if not path.exists():
        return {}
    return read_json(path)


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalize_concept(value: str) -> str:
    return " ".join(value.strip().lower().split())


def update_concept_state(
    state: dict[str, Any],
    *,
    score: float,
    feedback: str,
    source_refs: list[dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    memory_cfg = config.get("memory", {})
    needs_review_below = float(memory_cfg.get("needs_review_below", 0.6))
    mastery_threshold = float(memory_cfg.get("mastery_threshold", 0.8))
    mastery_streak = int(memory_cfg.get("mastery_streak", 2))

    attempts = int(state.get("attempts", 0)) + 1
    high_streak = int(state.get("high_streak", 0))
    weak_attempts = int(state.get("weak_attempts", 0))

    if score < needs_review_below:
        status = "needs_review"
        high_streak = 0
        weak_attempts += 1
    elif score < mastery_threshold:
        status = "improving"
        high_streak = 0
    else:
        high_streak += 1
        status = "mastered" if high_streak >= mastery_streak else "improving"

    common_errors = list(state.get("common_errors", []))
    if score < mastery_threshold and feedback and feedback not in common_errors:
        common_errors.insert(0, feedback)
    common_errors = common_errors[:5]

    merged_refs = list(state.get("source_refs", []))
    seen = {(ref.get("path"), ref.get("locator_type"), ref.get("locator")) for ref in merged_refs}
    for ref in source_refs:
        key = (ref.get("path"), ref.get("locator_type"), ref.get("locator"))
        if key not in seen:
            merged_refs.append(ref)
            seen.add(key)

    return {
        **state,
        "status": status,
        "attempts": attempts,
        "high_streak": high_streak,
        "weak_attempts": weak_attempts,
        "last_score": score,
        "last_feedback": feedback,
        "last_attempt_at": utc_now_iso(),
        "common_errors": common_errors,
        "source_refs": merged_refs[:12],
    }


def record_attempt(
    config: dict[str, Any],
    *,
    profile: str | None,
    question: str,
    student_answer: str,
    score: float,
    feedback: str,
    concepts: list[str],
    source_refs: list[dict[str, Any]] | None = None,
    question_id: str = "",
) -> dict[str, Any]:
    source_refs = source_refs or []
    score = max(0.0, min(1.0, score))
    normalized_concepts = [normalize_concept(concept) for concept in concepts if concept.strip()]
    if not normalized_concepts:
        normalized_concepts = ["uncategorized"]

    attempt = {
        "question_id": question_id,
        "question": question,
        "student_answer": student_answer,
        "score": score,
        "feedback": feedback,
        "concepts": normalized_concepts,
        "source_refs": source_refs,
        "recorded_at": utc_now_iso(),
    }
    append_jsonl(attempts_path(config, profile), attempt)

    concept_states = load_concepts(config, profile)
    for concept in normalized_concepts:
        state = concept_states.get(concept, {"concept": concept})
        concept_states[concept] = update_concept_state(
            state,
            score=score,
            feedback=feedback,
            source_refs=source_refs,
            config=config,
        )
    write_json(concepts_path(config, profile), concept_states)
    return {"attempt": attempt, "concepts": concept_states}


def render_mistake_form(config: dict[str, Any], profile: str | None = None) -> str:
    concepts = load_concepts(config, profile)
    profile_name = profile or config.get("memory", {}).get("default_profile", "default")
    lines = [
        f"# Mistake Review - {profile_name}",
        "",
        "Use this form to decide what to retry next. Concepts move to `mastered` after repeated strong attempts and move back when later attempts are weak.",
        "",
    ]

    if not concepts:
        lines.append("No attempts recorded yet.")
        return "\n".join(lines).strip() + "\n"

    ordered = sorted(
        concepts.values(),
        key=lambda item: (
            {"needs_review": 0, "improving": 1, "mastered": 2}.get(item.get("status", ""), 3),
            item.get("concept", ""),
        ),
    )

    for state in ordered:
        concept = state.get("concept", "")
        lines.extend(
            [
                f"## {concept}",
                "",
                f"- Status: `{state.get('status', 'needs_review')}`",
                f"- Last score: `{state.get('last_score', '')}`",
                f"- Attempts: `{state.get('attempts', 0)}`",
                f"- Strong-attempt streak: `{state.get('high_streak', 0)}`",
                f"- Last feedback: {state.get('last_feedback', '') or 'None'}",
                "- Common errors:",
            ]
        )
        common_errors = state.get("common_errors", [])
        lines.extend([f"  - {error}" for error in common_errors] or ["  - None"])
        lines.append("- Source references:")
        refs = state.get("source_refs", [])
        if refs:
            for ref in refs:
                locator = f", {ref.get('locator_type')} {ref.get('locator')}" if ref.get("locator_type") else ""
                lines.append(f"  - `{ref.get('path', '')}`{locator}")
        else:
            lines.append("  - None")
        lines.extend(
            [
                "- Retry plan:",
                "  - Ask for the same concept from a different business scenario.",
                "  - Ask for one small numerical or distributional change.",
                "  - Explain the final answer in one sentence before checking the solution.",
                "",
            ]
        )

    return "\n".join(lines).strip() + "\n"
