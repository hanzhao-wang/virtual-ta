from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path

from lib.common import (
    first_heading,
    read_jsonl,
    read_text,
    relative_to_repo,
    repo_path,
    resolve_config,
    slugify,
    summarize_terms,
    utc_now_iso,
    write_json,
    write_text,
)
from lib.render import render_outline_markdown


def choose_outline_records(manifest_rows: list[dict]) -> list[dict]:
    lecture_rows = [row for row in manifest_rows if row.get("category") == "lectures"]
    return lecture_rows or manifest_rows


def sort_key(row: dict) -> tuple:
    source = row.get("source_path", "")
    digits = [int(match) for match in re.findall(r"\d+", source)]
    return (digits or [10**9], source)


def detect_headings(text: str, limit: int = 6) -> list[str]:
    headings: list[str] = []
    seen: set[str] = set()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        candidate = line.lstrip("#").strip()
        if len(candidate) < 4 or len(candidate) > 120:
            continue

        if raw_line.startswith("#"):
            if candidate not in seen:
                headings.append(candidate)
                seen.add(candidate)
            continue

        letters = sum(char.isalpha() for char in candidate)
        punctuation = sum(char in ":;,.!?/\\|" for char in candidate)
        if letters >= 4 and punctuation <= max(1, letters // 12):
            if candidate.istitle() or candidate.isupper():
                if candidate not in seen:
                    headings.append(candidate)
                    seen.add(candidate)

        if len(headings) >= limit:
            break

    return headings[:limit]


def summary_from_text(text: str, max_chars: int = 500) -> str:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return ""
    summary = " ".join(paragraphs[:3])
    return summary[:max_chars].strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a deterministic lecture-outline cache.")
    parser.add_argument("--config", help="Path to config TOML file.")
    args = parser.parse_args()

    _, config = resolve_config(args.config)
    cache_cfg = config["cache"]
    manifest_path = repo_path(cache_cfg["manifest"])
    outline_seed_json = repo_path(cache_cfg["outline_seed_json"])
    outline_seed_markdown = repo_path(cache_cfg["outline_seed_markdown"])

    manifest_rows = read_jsonl(manifest_path)
    if not manifest_rows:
        raise SystemExit(
            f"Missing or empty manifest at {manifest_path}. Run tools/prepare_course_materials.py first."
        )

    lecture_rows = choose_outline_records(manifest_rows)
    lecture_rows = sorted(lecture_rows, key=sort_key)

    lectures = []
    topic_sources: dict[str, set[str]] = defaultdict(set)

    for row in lecture_rows:
        text_path = repo_path(row["normalized_text_path"])
        if not text_path.exists():
            continue

        text = read_text(text_path)
        title = row.get("title") or first_heading(text) or Path(row["source_path"]).stem
        headings = detect_headings(text)
        key_topics = headings[:4] or summarize_terms(text, limit=8)
        summary = summary_from_text(text)
        source_path = row["source_path"]

        lecture_id = slugify(Path(source_path).stem)
        lectures.append(
            {
                "lecture_id": lecture_id,
                "title": title,
                "summary": summary,
                "key_topics": key_topics,
                "source_paths": [source_path],
            }
        )

        for topic in key_topics:
            topic_sources[topic].add(source_path)

    course_title = "Course lecture outline"
    if lectures:
        course_title = lectures[0]["title"].split(" - ")[0].strip() or course_title

    high_level_summary = (
        f"Deterministic outline built from {len(lectures)} indexed lecture files. "
        "Use this cache before reading larger source files."
    )

    payload = {
        "course_title": course_title,
        "high_level_summary": high_level_summary,
        "lectures": lectures,
        "topic_index": [
            {"topic": topic, "source_paths": sorted(paths)}
            for topic, paths in sorted(topic_sources.items())
        ],
        "generated_at": utc_now_iso(),
        "generator": "tools/build_outline_cache.py",
        "notes": "This is a deterministic seed outline. Optionally polish it with Codex.",
    }

    write_json(outline_seed_json, payload)
    write_text(outline_seed_markdown, render_outline_markdown(payload))

    print(f"Wrote seed outline JSON to {relative_to_repo(outline_seed_json)}")
    print(f"Wrote seed outline Markdown to {relative_to_repo(outline_seed_markdown)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
