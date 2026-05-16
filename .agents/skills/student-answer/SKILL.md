---
name: student-answer
description: Answer a student question from local course materials first, cite source file paths, include a simple example, and optionally use live web search when local evidence is insufficient.
---

Use this skill when answering a student question about course content, code, notebooks, lecture material, assignments, quizzes, or nearby general concepts.

## Process

1. Read the cached outline first:
   - `cache/outlines/course_outline.json`
   - `cache/outlines/course_outline.md`
   - if missing, fall back to `cache/outlines/course_outline_seed.json` or `.md`

2. Read the retrieval payload prepared for the question, if one is provided.
   Typical path:
   - `cache/retrieval/*.json`

3. Use course materials first.
   - Prefer the retrieved excerpts and the outline cache.
   - Only inspect larger extracted files if the retrieved excerpts are ambiguous.

4. Answer clearly and directly.
   - Start with the direct answer.
   - Include a simple example whenever it helps.
   - Keep the explanation concrete and student-friendly.

5. Source traceability:
   - If local materials support the answer, cite the local file paths and locators from retrieval.
   - Prefer page, slide, sheet, cell, question, and caption locators when available.
   - Never invent a path, locator, section name, or quote.
   - If the answer goes beyond what the local materials say, state that explicitly.

6. Out-of-scope or general questions:
   - If live web search is available and needed, use it only after checking local material.
   - If live web search is not enabled, answer from general reasoning only when necessary and label it clearly.

7. Output expectations:
   - If a JSON schema is supplied, return JSON only.
   - Otherwise use Markdown with these sections:
     - Direct answer
     - Simple example
     - Support level
     - Local sources
     - Web sources
     - Notes

## Local source fields

When a JSON schema requests local source metadata, fill:
- `path`
- `title`
- `reason`
- `file_type`
- `locator_type`
- `locator`
- `excerpt`
- `confidence`
- `extraction_status`

Copy these values from the retrieval payload when available.

## Support level labels

Use one of:
- `local_materials`
- `local_plus_general_reasoning`
- `general_reasoning_only`
- `live_web_search`
