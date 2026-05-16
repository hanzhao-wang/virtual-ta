# Student Virtual TA

A local, student-side virtual teaching assistant for Codex. It indexes course materials, answers questions with source citations, generates practice and mock exams, and tracks mistakes privately on the student's machine.

The default workflow is local-first and Codex-command based. There is no web app, shared class database, or required live web search.

## What It Handles

Put course files under `resources/`. That folder is ignored by git by default so the open-source starter does not publish course PDFs, assignment data, or student-specific materials. The indexer handles:

- Slides and documents: `.pdf`, `.pptx`, `.docx`, `.ppt`, `.doc`
- Data and notebooks: `.csv`, `.xlsx`, `.xls`, `.ipynb`, `.py`
- Text and web exports: `.txt`, `.md`, `.rst`, `.tex`, `.json`, `.yaml`, `.html`
- Images: `.png`, `.jpg`, `.jpeg`, `.webp` through automatic Codex vision captions or caption files
- Archives: `.zip` with a safe manifest plus supported files inside

Every file is either indexed, converted, auto-captioned, marked as needing attention, or listed with an actionable warning in `cache/material_catalog.md`.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python tools/ta.py doctor
python tools/ta.py index --auto-caption --polish
```

Ask a question:

```bash
python tools/ta.py ask "What is overfitting and how do we detect it?"
```

Generate practice:

```bash
python tools/ta.py practice "decision trees and random forests" --num-questions 5
```

Generate a mock exam PDF:

```bash
python tools/ta.py mock "model evaluation and tree-based methods" --num-questions 6 --format pdf
```

Review mistake memory:

```bash
python tools/ta.py mistakes
```

## Codex Install Prompt

Students can paste this directly into Codex without opening GitHub first:

```text
Please install this repo https://github.com/hanzhao-wang/virtual-ta and set up the Student Virtual TA. Put my course files under resources, run the setup doctor, index the materials with automatic image captioning, and explain the commands I can use.
```

Codex should clone the repo if needed, follow `INSTALL.md`, run `python tools/ta.py doctor`, install missing Python packages, then run `python tools/ta.py index --auto-caption --polish` after materials are present.

## Source Citations

Answers use local retrieval first. When supported by local material, citations include:

- file path
- file type
- locator type, such as page, slide, sheet, cell, question, or caption
- locator value
- extraction status
- short excerpt

If local material is insufficient, answers must label the support level as `general_reasoning_only` or `local_plus_general_reasoning`.

## Images And Scanned Material

Image files can be captioned automatically with Codex vision:

```bash
python tools/ta.py caption-images
python tools/ta.py index
```

Or do both in one command:

```bash
python tools/ta.py index --auto-caption
```

Captions are stored under `cache/image_captions/` and become citeable local evidence. If Codex vision is unavailable, the indexer still creates caption stubs that can be filled manually.

Scanned PDFs are detected when little or no text can be extracted. V1 reports those files clearly; automatic page-level vision captioning for scanned PDFs can be added later by rendering pages to images before captioning.

## Mistake Memory

Mistake memory is local and private. Attempts are stored under `memory/profiles/default/`, which is ignored by git.

Codex can record interactive practice attempts with:

```bash
python tools/ta.py record-attempt \
  --concept "overfitting" \
  --score 0.5 \
  --question "Why is this model overfitting?" \
  --student-answer "Because training accuracy is low." \
  --feedback "Confused training fit with generalization gap."
```

Concept status updates automatically:

- below `0.6`: `needs_review`
- `0.6` to below `0.8`: `improving`
- two later attempts at `0.8` or higher: `mastered`
- a later weak attempt demotes the concept

## Main Files

- `tools/ta.py`: student-facing command wrapper
- `tools/prepare_course_materials.py`: robust ingestion and locator-aware indexing
- `tools/run_answer.py`: local-first answers through Codex
- `tools/generate_practice.py`: exercise/mock generation with Markdown, TeX, and PDF rendering
- `tools/lib/memory.py`: local adaptive mistake memory
- `config/virtual_ta.toml`: material roots and behavior settings
