from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from lib.render import render_answer_markdown, render_practice_tex  # noqa: E402
from lib.retrieval import retrieve_with_fallback  # noqa: E402


def test_answer_markdown_renders_locator_metadata() -> None:
    payload = {
        "question": "What is a validation set?",
        "direct_answer": "A validation set tunes model choices.",
        "simple_example": "Try several tree depths and choose using validation error.",
        "support_level": "local_materials",
        "local_sources": [
            {
                "path": "resources/Lectures/02 Machine Learning Fundamentals.pdf",
                "title": "Page 4",
                "reason": "Defines validation data.",
                "file_type": ".pdf",
                "locator_type": "page",
                "locator": "4",
                "excerpt": "Validation data is used for model selection.",
                "confidence": 0.9,
                "extraction_status": "indexed",
            }
        ],
        "web_sources": [],
        "notes": "",
        "follow_up_suggestions": [],
    }

    markdown = render_answer_markdown(payload)

    assert "page 4" in markdown
    assert "Validation data is used" in markdown


def test_practice_tex_escapes_special_characters() -> None:
    payload = {
        "kind": "exercise_set",
        "topic_request": "R^2 and train_test split",
        "difficulty": "mixed",
        "instructions": "Answer all questions.",
        "questions": [
            {
                "id": "Q1",
                "marks": 2,
                "concepts": ["R^2"],
                "question": "What does R^2 mean when error_rate < 5%?",
                "answer": "It measures explained variance.",
                "explanation": "Higher is usually better for this metric.",
            }
        ],
    }

    tex = render_practice_tex(payload)

    assert r"R\textasciicircum{}2" in tex
    assert r"error\_rate" in tex
    assert r"5\%" in tex


def test_fallback_retrieval_preserves_locator_fields(tmp_path: Path) -> None:
    chunks_path = tmp_path / "chunks.jsonl"
    row = {
        "chunk_id": "c1",
        "doc_id": "d1",
        "category": "lectures",
        "source_path": "resources/Lectures/example.pdf",
        "file_type": ".pdf",
        "title": "Page 3",
        "chunk_index": 0,
        "locator_type": "page",
        "locator": "3",
        "extraction_status": "indexed",
        "text": "Validation sets are used to choose model hyperparameters.",
    }
    chunks_path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    results = retrieve_with_fallback(chunks_path, "validation hyperparameters", top_k=1)

    assert results[0]["locator_type"] == "page"
    assert results[0]["locator"] == "3"
