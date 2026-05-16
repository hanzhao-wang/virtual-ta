---
name: interactive-practice
description: Run one-by-one adaptive practice with grading, feedback, and local mistake-memory updates.
---

Use this skill when a student wants interactive practice, one question at a time.

## Process

1. Confirm the topic, difficulty, and number of questions if the student did not provide them.

2. Retrieve local course context first:
   - Prefer `python tools/query_course_context.py --question "<topic>"`.
   - Read the cached outline before using large extracted files.

3. Ask exactly one new question at a time.
   - Keep the question aligned with local course material.
   - Include marks and the concept being tested.
   - Do not show the answer until the student responds.

4. After the student answers:
   - Grade on a 0 to 1 scale.
   - Explain the main correction in simple language.
   - Cite source refs from retrieved local context when available.
   - If local material is insufficient, label the feedback as general reasoning.

5. Record the attempt:
   - Use `python tools/ta.py record-attempt`.
   - Pass `--concept` for each tested concept.
   - Pass `--score`, `--question`, `--student-answer`, and concise `--feedback`.
   - Pass `--source-ref-json` when source refs are available.

6. Adapt the next question:
   - If the score is below 0.6, ask the same concept from a simpler or different business scenario.
   - If the score is 0.6 to below 0.8, ask a near variant with changed numbers, data distribution, or wording.
   - If the score is 0.8 or above, increase difficulty or move to the next concept.

7. At the end:
   - Run `python tools/ta.py mistakes` to update the review form.
   - Summarize mastered, improving, and needs-review concepts.
