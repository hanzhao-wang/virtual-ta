---
name: generate-practice
description: Generate local practice exercises or mock exams with answers, explanations, and source file traceability from course materials.
---

Use this skill when generating:
- practice exercises,
- revision questions,
- mini quizzes,
- mock exams.

## Process

1. Read the cached outline first:
   - `cache/outlines/course_outline.json`
   - `cache/outlines/course_outline.md`
   - if missing, use the seed outline.

2. Read the retrieval payload prepared for the requested topic.

3. Align generation with the requested:
   - topic(s)
   - format
   - number of questions
   - difficulty

4. Create **new** questions inspired by the material.
   - Do not reproduce large chunks of existing assessment text verbatim.
   - Keep the style close to the course where possible.

5. Include:
   - answer key
   - short explanation for each answer
   - source paths and source refs used for each question
   - concepts tested by each question
   - a concise rubric for grading
   - a variant seed for later adaptive retry questions
   - coverage notes describing which topics are covered

6. For mock exams:
   - include marks for each question
   - make the coverage balanced
   - keep instructions concise

7. If a topic is outside the course scope:
   - either avoid it, or
   - label it clearly as a stretch question

8. Output expectations:
   - If a JSON schema is supplied, return JSON only.
   - Otherwise return well-structured Markdown.

## Source refs

When retrieval provides locator metadata, preserve it in `source_refs`:
- `path`
- `file_type`
- `locator_type`
- `locator`
- `reason`

Use page, slide, sheet, cell, question, or caption locators exactly as provided. Do not invent locators.
