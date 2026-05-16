# Install And Setup

This repo is designed for students to use inside Codex with local course files.

## Codex Setup Prompt

Paste this directly into Codex:

```text
Please install this repo https://github.com/hanzhao-wang/virtual-ta and set up the Student Virtual TA. Put my course files under resources, run the setup doctor, index the materials with automatic image captioning, and explain the commands I can use.
```

Codex should clone the repository if needed, install dependencies, run `python tools/ta.py doctor`, and run `python tools/ta.py index --auto-caption --polish` after materials are present.

## Manual Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python tools/ta.py doctor
```

If `doctor` reports missing Python packages, rerun:

```bash
python -m pip install -r requirements.txt
```

Optional external tools:

- `codex`: required for answering and generation wrappers
- `pdflatex` or `xelatex`: needed for PDF practice/mock exams
- LibreOffice (`soffice` or `libreoffice`): needed for `.ppt`, `.doc`, and `.xls` conversion

## Add Course Materials

Place files under `resources/`:

- `resources/Lectures`
- `resources/Question Books`
- `resources/Exercises`
- `resources/Quizzes`
- `resources/Assignment`

The legacy `course_materials/` folders still work if you prefer that layout.

## Index Materials

```bash
python tools/ta.py index --auto-caption --polish
```

After indexing, check:

```bash
cache/material_catalog.md
```

This catalog lists indexed files, partial extractions, unsupported files, legacy conversion needs, and image caption tasks.

## Caption Image-Only Materials

If the catalog reports image files, generate captions with Codex vision:

```bash
python tools/ta.py caption-images
python tools/ta.py index
```

You can also caption during indexing:

```bash
python tools/ta.py index --auto-caption
```

Captions are stored under `cache/image_captions/`. If Codex vision is unavailable, the TA falls back to caption stubs that can be filled manually.
