# Getting Started For Students

## 0. Install From A Blank Codex Project

Choose **Start from scratch** in Codex, then paste:

```text
Please install this repo https://github.com/hanzhao-wang/virtual-ta into ~/Desktop/virtual-ta and set up the Student Virtual TA. Clone the repo if needed, create a Python environment, install the requirements, run the setup doctor, and explain that I should manually put my course files into ~/Desktop/virtual-ta/resources before indexing. Do not index yet unless course files are already present.
```

## 1. Put Files In Resources

Add slides, tutorials, exercises, assignment guides, data dictionaries, and quizzes under `resources/`.

Supported examples:

- `resources/Lectures/week_01.pdf`
- `resources/Lectures/week_02.pptx`
- `resources/Exercises/mock_exam.tex`
- `resources/Assignment/data_dictionary.xlsx`
- `resources/Quizzes/tree_diagram.png`

## 2. Check Setup

```bash
python tools/ta.py doctor
```

Fix anything marked missing if it is needed for your files.

## 3. Index The Course

```bash
python tools/ta.py index --auto-caption --polish
```

The TA builds:

- `cache/manifest.jsonl`
- `cache/chunks.jsonl`
- `cache/index.db`
- `cache/outlines/course_outline_seed.json`
- `cache/outlines/course_outline.json` when polished

## 4. Ask Questions

```bash
python tools/ta.py ask "How do validation and test sets differ?"
```

The answer starts directly, includes a simple example, and labels its support level:

- `local_materials`
- `local_plus_general_reasoning`
- `general_reasoning_only`
- `live_web_search`

## 5. Generate Practice

```bash
python tools/ta.py practice "gradient boosting" --difficulty mixed --num-questions 5
```

Practice includes questions, answers, explanations, concepts, marks, and source references.

## 6. Generate A Mock Exam

```bash
python tools/ta.py mock "weeks 2 to 8" --num-questions 8 --format pdf
```

If LaTeX is unavailable, use:

```bash
python tools/ta.py mock "weeks 2 to 8" --num-questions 8 --format markdown
```

## 7. Practice One Question At A Time In Codex

Ask Codex:

```text
Use the interactive-practice skill. Quiz me one question at a time on decision trees. After each answer, grade me, explain the correction, and update my mistake memory.
```

Codex records attempts locally with `python tools/ta.py record-attempt`.

## 8. Review Mistakes

```bash
python tools/ta.py mistakes
```

This writes `memory/profiles/default/mistake_review.md`, showing weak concepts, common errors, source references, and retry plans.
