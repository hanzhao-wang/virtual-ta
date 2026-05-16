from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .common import ensure_dir, write_text


def format_source_ref(source: dict[str, Any]) -> str:
    path = source.get("path", "")
    locator_type = source.get("locator_type", "")
    locator = source.get("locator", "")
    title = source.get("title", "")
    reason = source.get("reason", "")
    file_type = source.get("file_type", "")
    status = source.get("extraction_status", "")
    locator_text = f", {locator_type} {locator}" if locator_type and locator else ""
    details = " ".join(part for part in [title, file_type, status] if part)
    suffix = f" - {details}: {reason}" if details or reason else ""
    return f"`{path}`{locator_text}{suffix}".strip()


def render_answer_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Question",
        payload.get("question", "").strip(),
        "",
        "## Direct answer",
        payload.get("direct_answer", "").strip(),
        "",
        "## Simple example",
        payload.get("simple_example", "").strip() or "_No example provided._",
        "",
        "## Support level",
        payload.get("support_level", "").strip(),
        "",
        "## Local sources",
    ]

    local_sources = payload.get("local_sources", [])
    if local_sources:
        for source in local_sources:
            lines.append(f"- {format_source_ref(source)}")
            excerpt = source.get("excerpt", "").strip()
            if excerpt:
                lines.append(f"  Excerpt: {excerpt[:300]}")
    else:
        lines.append("- None")

    lines.extend(["", "## Web sources"])
    web_sources = payload.get("web_sources", [])
    if web_sources:
        for source in web_sources:
            lines.append(
                f"- {source.get('title', '')} ({source.get('domain', '')}) - {source.get('reason', '')}"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Notes", payload.get("notes", "").strip() or "None", "", "## Follow-up suggestions"])
    follow_ups = payload.get("follow_up_suggestions", [])
    if follow_ups:
        for item in follow_ups:
            lines.append(f"- {item}")
    else:
        lines.append("- None")

    return "\n".join(lines).strip() + "\n"


def render_source_refs_markdown(refs: list[dict[str, Any]], fallback_paths: list[str] | None = None) -> list[str]:
    lines: list[str] = []
    if refs:
        for ref in refs:
            lines.append(f"- {format_source_ref(ref)}")
    else:
        for path in fallback_paths or []:
            lines.append(f"- `{path}`")
    if not lines:
        lines.append("- None")
    return lines


def render_practice_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# {payload.get('kind', 'practice').replace('_', ' ').title()}",
        "",
        "## Topic request",
        payload.get("topic_request", "").strip(),
        "",
        "## Difficulty",
        payload.get("difficulty", "").strip(),
        "",
        "## Instructions",
        payload.get("instructions", "").strip(),
        "",
        "## Concepts",
    ]

    concepts = payload.get("concepts", [])
    lines.extend([f"- {concept}" for concept in concepts] or ["- None"])
    lines.extend(
        [
            "",
            "## Rubric",
            payload.get("rubric", "").strip() or "None",
            "",
            "## Coverage notes",
            payload.get("coverage_notes", "").strip(),
            "",
            "## Source references",
        ]
    )
    lines.extend(render_source_refs_markdown(payload.get("source_refs", []), payload.get("source_paths", [])))

    lines.append("")
    lines.append("## Questions")

    for question in payload.get("questions", []):
        lines.extend(
            [
                f"### {question.get('id', 'Q')} ({question.get('marks', 0)} marks)",
                "",
                f"**Type:** {question.get('question_type', '')}",
                "",
                f"**Concepts:** {', '.join(question.get('concepts', [])) or 'None'}",
                "",
                question.get("question", "").strip(),
                "",
                "**Answer**",
                question.get("answer", "").strip(),
                "",
                "**Explanation**",
                question.get("explanation", "").strip(),
                "",
                "**Rubric**",
                question.get("rubric", "").strip() or "None",
                "",
                "**Source references**",
            ]
        )
        lines.extend(render_source_refs_markdown(question.get("source_refs", []), question.get("source_paths", [])))
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def latex_escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    escaped = "".join(replacements.get(char, char) for char in value)
    escaped = re.sub(r"\n{3,}", "\n\n", escaped)
    return escaped.replace("\n\n", "\n\\par\n").replace("\n", "\\\\\n")


def render_practice_tex(payload: dict[str, Any]) -> str:
    title = payload.get("kind", "practice").replace("_", " ").title()
    lines = [
        r"\documentclass[11pt]{article}",
        r"\usepackage[margin=1in]{geometry}",
        r"\usepackage{enumitem}",
        r"\setlength{\parindent}{0pt}",
        r"\setlength{\parskip}{0.5em}",
        r"\begin{document}",
        rf"\section*{{{latex_escape(title)}}}",
        rf"\textbf{{Topic:}} {latex_escape(payload.get('topic_request', ''))}",
        "",
        rf"\textbf{{Difficulty:}} {latex_escape(payload.get('difficulty', ''))}",
        "",
        rf"\textbf{{Instructions:}} {latex_escape(payload.get('instructions', ''))}",
        "",
        r"\section*{Questions}",
        r"\begin{enumerate}[leftmargin=*]",
    ]

    for question in payload.get("questions", []):
        marks = question.get("marks", 0)
        concepts = ", ".join(question.get("concepts", []))
        lines.extend(
            [
                rf"\item \textbf{{{latex_escape(question.get('id', 'Q'))}}} ({marks} marks)\\",
                latex_escape(question.get("question", "")),
            ]
        )
        if concepts:
            lines.append(rf"\\\textit{{Concepts:}} {latex_escape(concepts)}")
        lines.append("")

    lines.extend(
        [
            r"\end{enumerate}",
            r"\newpage",
            r"\section*{Answer Key}",
            r"\begin{enumerate}[leftmargin=*]",
        ]
    )

    for question in payload.get("questions", []):
        lines.extend(
            [
                rf"\item \textbf{{{latex_escape(question.get('id', 'Q'))}}}\\",
                rf"\textbf{{Answer:}} {latex_escape(question.get('answer', ''))}",
                "",
                rf"\textbf{{Explanation:}} {latex_escape(question.get('explanation', ''))}",
                "",
            ]
        )

    lines.extend([r"\end{enumerate}", r"\end{document}", ""])
    return "\n".join(lines)


def render_outline_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# {payload.get('course_title', 'Course outline')}",
        "",
        "## High-level summary",
        payload.get("high_level_summary", "").strip(),
        "",
        "## Lectures",
    ]

    for lecture in payload.get("lectures", []):
        lines.extend(
            [
                f"### {lecture.get('lecture_id', '')}: {lecture.get('title', '')}",
                "",
                lecture.get("summary", "").strip(),
                "",
                "**Key topics**",
            ]
        )
        for topic in lecture.get("key_topics", []):
            lines.append(f"- {topic}")
        if not lecture.get("key_topics"):
            lines.append("- None")
        lines.append("")
        lines.append("**Source paths**")
        for path in lecture.get("source_paths", []):
            lines.append(f"- `{path}`")
        if not lecture.get("source_paths"):
            lines.append("- None")
        lines.append("")

    lines.extend(["## Topic index"])
    for row in payload.get("topic_index", []):
        topic = row.get("topic", "")
        sources = ", ".join(f"`{path}`" for path in row.get("source_paths", [])) or "None"
        lines.append(f"- **{topic}**: {sources}")

    return "\n".join(lines).strip() + "\n"


def write_markdown(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    write_text(path, content)
