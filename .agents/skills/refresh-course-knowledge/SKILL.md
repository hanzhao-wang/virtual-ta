---
name: refresh-course-knowledge
description: Refresh the local extraction cache, retrieval index, and lecture outline cache for the student virtual TA.
---

Use this skill when course materials change or the retrieval/outline cache is missing.

## Process

1. Read `config/virtual_ta.toml` if present; otherwise use `config/virtual_ta.example.toml`.

2. Prefer the convenience wrapper:
   - `python tools/ta.py index`
   - with outline polish: `python tools/ta.py index --polish`
   - with automatic image captions: `python tools/ta.py index --auto-caption --polish`

3. If the wrapper is unavailable, run:
   - `python tools/refresh_course_knowledge.py --config config/virtual_ta.toml`

4. If asked for a cleaner outline, or if the deterministic outline is poor, run:
   - `python tools/refresh_course_knowledge.py --config config/virtual_ta.toml --polish`

5. If the refresh wrapper is unavailable, run the steps directly:
   - `python tools/prepare_course_materials.py --config config/virtual_ta.toml`
   - `python tools/build_outline_cache.py --config config/virtual_ta.toml`
   - optional: `python tools/polish_outline_with_codex.py --config config/virtual_ta.toml`

6. Keep all outputs under:
   - `cache/`
   - `answers/`
   - `practice/`

7. Do not modify files under `course_materials/`.

8. Summarize what changed:
   - number of indexed files
   - file types found
   - files auto-captioned, still needing captions, or needing conversion
   - outline files written
   - warnings or skipped files
