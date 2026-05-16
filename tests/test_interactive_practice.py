from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from interactive_practice import read_answer, render_feedback_for_chat, render_question_for_chat  # noqa: E402


def test_render_question_for_chat_hides_expected_answer(tmp_path: Path) -> None:
    question_path = tmp_path / "question.json"
    payload = {
        "id": "Q1",
        "difficulty": "mixed",
        "marks": 3,
        "concepts": ["overfitting"],
        "instructions": "Answer in 2-3 sentences.",
        "question": "A model has low training error and high test error. What is happening?",
        "expected_answer": "The model is overfitting.",
    }

    rendered = render_question_for_chat(payload, question_path)

    assert "A model has low training error" in rendered
    assert "overfitting" in rendered
    assert "expected_answer" not in rendered
    assert "The model is overfitting." not in rendered


def test_read_answer_supports_uploaded_file(tmp_path: Path) -> None:
    answer_path = tmp_path / "answer.txt"
    answer_path.write_text("The model is overfitting because it fails to generalize.", encoding="utf-8")
    args = argparse.Namespace(answer=None, answer_file=str(answer_path))

    assert "fails to generalize" in read_answer(args)


def test_render_feedback_for_chat_includes_memory_update_paths(tmp_path: Path) -> None:
    payload = {
        "score": 0.5,
        "direct_feedback": "You identified the error pattern but missed the generalization point.",
        "strengths": ["Mentioned train/test error."],
        "corrections": ["Explain why high test error matters."],
        "model_answer": "This is overfitting: low training error but high test error.",
        "next_step": "Try a similar question with a new business scenario.",
    }

    rendered = render_feedback_for_chat(payload, tmp_path / "feedback.json", tmp_path / "mistakes.md")

    assert "Score: 0.50" in rendered
    assert "Mistake review updated" in rendered
    assert "This is overfitting" in rendered
