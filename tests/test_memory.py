from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from lib.memory import load_concepts, record_attempt, render_mistake_form  # noqa: E402


def test_memory_transitions_from_review_to_mastered_and_back(tmp_path: Path) -> None:
    config = {
        "memory": {
            "root": str(tmp_path / "profiles"),
            "default_profile": "default",
            "needs_review_below": 0.6,
            "mastery_threshold": 0.8,
            "mastery_streak": 2,
        }
    }

    record_attempt(
        config,
        profile=None,
        question="What is overfitting?",
        student_answer="Not sure",
        score=0.3,
        feedback="Confused training fit with generalization.",
        concepts=["Overfitting"],
    )
    assert load_concepts(config)["overfitting"]["status"] == "needs_review"

    record_attempt(
        config,
        profile=None,
        question="Explain overfitting again.",
        student_answer="High train accuracy, weak test accuracy.",
        score=0.9,
        feedback="Good.",
        concepts=["Overfitting"],
    )
    assert load_concepts(config)["overfitting"]["status"] == "improving"

    record_attempt(
        config,
        profile=None,
        question="Identify overfitting in a scenario.",
        student_answer="The model memorized training data.",
        score=0.85,
        feedback="Good.",
        concepts=["Overfitting"],
    )
    assert load_concepts(config)["overfitting"]["status"] == "mastered"

    record_attempt(
        config,
        profile=None,
        question="Does this model overfit?",
        student_answer="No",
        score=0.4,
        feedback="Missed the validation error gap.",
        concepts=["Overfitting"],
    )
    concepts = load_concepts(config)
    assert concepts["overfitting"]["status"] == "needs_review"
    assert "Missed the validation error gap." in concepts["overfitting"]["common_errors"]


def test_mistake_form_renders_empty_state(tmp_path: Path) -> None:
    config = {"memory": {"root": str(tmp_path / "profiles"), "default_profile": "default"}}

    content = render_mistake_form(config)

    assert "No attempts recorded yet." in content
