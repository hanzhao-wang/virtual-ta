# Student Virtual TA

A local, student-side virtual teaching assistant for Codex. It indexes course materials, answers questions with source citations, generates practice and mock exams, and tracks mistakes privately on the student's machine.

The default student workflow is plain-text chat in Codex. Students do not need to type terminal commands; Codex runs the local tools for them. There is no web app, shared class database, or required live web search.

## What It Handles

Put course files under `resources/`. That folder is ignored by git by default so the open-source starter does not publish course PDFs, assignment data, or student-specific materials. The indexer handles:

- Slides and documents: `.pdf`, `.pptx`, `.docx`, `.ppt`, `.doc`
- Data and notebooks: `.csv`, `.xlsx`, `.xls`, `.ipynb`, `.py`
- Text and web exports: `.txt`, `.md`, `.rst`, `.tex`, `.json`, `.yaml`, `.html`
- Images: `.png`, `.jpg`, `.jpeg`, `.webp` through automatic Codex vision captions or caption files
- Archives: `.zip` with a safe manifest plus supported files inside

Every file is either indexed, converted, auto-captioned, marked as needing attention, or listed with an actionable warning in `cache/material_catalog.md`.

## Student Quick Start

After setup, students can talk to Codex in plain English.

Ask a question:

```text
What is overfitting and how do we detect it? Please answer from my course materials first and cite the exact slide/page if available.
```

Generate practice:

```text
Quiz me one question at a time on decision trees and random forests. Wait for my answer, then grade it, explain the correction, and remember any mistakes.
```

Generate a mock exam:

```text
Create an 8-question mock exam on weeks 2 to 8. Include marks, answers, explanations, and source coverage.
```

Review mistake memory:

```text
Show my mistake review form and tell me which concepts I should retry next.
```

## Codex Install Prompt

Students can choose **Start from scratch** in Codex, then paste this directly without opening GitHub first:

```text
Please install this repo https://github.com/hanzhao-wang/virtual-ta into ~/Desktop/virtual-ta and set up the Student Virtual TA. Clone the repo if needed, create a Python environment, install the requirements, and run the setup doctor. Explain that I should manually put my course files into ~/Desktop/virtual-ta/resources before indexing. Do not index yet unless course files are already present. When explaining how to use the TA, give me plain-English Codex prompts only, not terminal commands, unless I ask for commands.
```

After students manually add course files under `resources/`, they can paste:

```text
I have added my course files under resources. Please index them with automatic image captioning. After indexing, explain how I can use this virtual TA using plain-English Codex prompts only. Do not give me terminal commands unless I ask for them.
```

Codex should clone the repo if needed, follow `INSTALL.md`, run the local setup/indexing tools internally, and only index after materials are present.

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

Image files can be captioned automatically with Codex vision during indexing.

Captions are stored under `cache/image_captions/` and become citeable local evidence. If Codex vision is unavailable, the indexer still creates caption stubs that can be filled manually.

Scanned PDFs are detected when little or no text can be extracted. V1 reports those files clearly; automatic page-level vision captioning for scanned PDFs can be added later by rendering pages to images before captioning.

## Mistake Memory

Mistake memory is local and private. Attempts are stored under `memory/profiles/default/`, which is ignored by git.

During interactive practice, Codex shows one question directly in chat, waits for the student's typed or uploaded answer, gives feedback, and records mistakes automatically after grading.

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
- `tools/interactive_practice.py`: one-question-at-a-time practice, grading, and memory updates
- `tools/lib/memory.py`: local adaptive mistake memory
- `config/virtual_ta.toml`: material roots and behavior settings
