# Handoff for Codex: student-side virtual TA

You are working on a local-only student-facing virtual TA repository.

## Product goal

Build a dependable local virtual TA that:
- answers student questions from local course files first,
- cites the source file paths that support the answer,
- includes a simple illustrative example,
- can optionally use live web search for out-of-scope or current general questions,
- can generate exercises and mock exams with answers,
- avoids rescanning all course files by relying on cached extraction + retrieval + outline files.

## Existing architecture

- `tools/prepare_course_materials.py`
  - scans configured material folders,
  - extracts text from multiple file types,
  - creates locator-aware segments for pages, slides, sheets, cells, TeX questions, captions, and archive members,
  - writes `cache/manifest.jsonl`, `cache/chunks.jsonl`, and `cache/index.db`.
- `tools/build_outline_cache.py`
  - builds a deterministic lecture outline seed from lecture materials.
- `tools/refresh_course_knowledge.py`
  - runs the local refresh pipeline end-to-end.
- `tools/polish_outline_with_codex.py`
  - optionally converts the seed outline into a cleaner structured outline via `codex exec`.
- `tools/run_answer.py`
  - retrieves relevant local chunks,
  - calls `codex exec` with the `student-answer` skill,
  - writes structured JSON plus reviewable Markdown.
- `tools/generate_practice.py`
  - retrieves relevant local chunks,
  - calls `codex exec` with the `generate-practice` skill,
  - writes structured JSON plus Markdown, and can render TeX/PDF.
- `tools/ta.py`
  - provides the student-facing `doctor`, `index`, `ask`, `practice`, `mock`, `mistakes`, and `record-attempt` commands.
- `tools/lib/memory.py`
  - stores private local mistake memory under `memory/profiles/`.

## Constraints

- Stay local to the repository.
- Never require network access except when the user explicitly enables `--live-search`.
- Prefer the cached outline and retrieval results over rescanning raw files.
- Preserve source traceability.
- Preserve locator traceability; never invent page, slide, sheet, cell, question, or caption locators.
- Do not fabricate citations, section names, or file paths.
- If local materials are insufficient and live search is disabled, answer carefully from general reasoning and label that clearly.

## Priority improvements

1. Improve extraction quality for tricky PDFs and slide decks.
2. Improve lecture grouping and week detection from file names and folder structure.
3. Improve retrieval ranking:
   - hybrid lexical + metadata boosts,
   - better phrase matching,
   - optional embeddings later.
4. Improve practice generation:
   - difficulty control,
   - balanced topic coverage,
   - solution quality,
   - clear mark allocation for mock exams.
5. Add regression tests with small fixture materials.
6. Add a lightweight local UI later if useful, but keep the local-file pipeline intact.

## Acceptance criteria

- A user can place files under `resources/` or `course_materials/` and run the indexing pipeline.
- A user can ask a question and receive:
  - a direct answer,
  - a simple example,
  - a clear `support_level`,
  - source paths for local evidence.
- source locators for local evidence when available.
- A user can generate:
  - a practice exercise set with answers,
  - a mock exam with answers and coverage notes.
- A user can render practice as Markdown, TeX, or PDF when LaTeX is installed.
- Cached outline and retrieval artifacts are reused across answers.
- A user can review local mistake memory and generate adaptive retry practice.

## When making changes

- Keep the repo readable.
- Prefer small composable helpers under `tools/lib/`.
- Update `README.md` if commands or config change.
- Add or update schemas when outputs change.
