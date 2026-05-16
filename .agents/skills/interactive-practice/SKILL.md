---
name: interactive-practice
description: Run one-by-one adaptive practice with grading, feedback, and local mistake-memory updates.
---

Use this skill when a student wants interactive practice, one question at a time.

## Process

1. Confirm the topic, difficulty, and number of questions if the student did not provide them.

2. Generate the next question internally:
   - Prefer `python tools/ta.py next-question "<topic>"`.
   - Use `--focus` when retrying a known mistake or varying a prior question.
   - Show only the question, marks, concept, and answer instructions to the student.
   - Do not show terminal commands, JSON, expected answers, rubrics, or file paths unless the student asks.

3. Ask exactly one new question at a time.
   - Keep the question aligned with local course material.
   - Include marks and the concept being tested.
   - Do not show the answer until the student responds.
   - If the tool output includes an internal question record path, keep it for grading.

4. After the student answers:
   - If the student uploads a file, use it as the answer file.
   - Run `python tools/ta.py grade-answer --question-json <path> --answer "<answer>"` or `--answer-file <path>`.
   - The grading tool records mistake memory automatically.
   - Explain the score and main correction in simple language.
   - Cite source refs from retrieved local context when available.
   - If local material is insufficient, label the feedback as general reasoning.

5. Adapt the next question:
   - If the score is below 0.6, ask the same concept from a simpler or different business scenario.
   - If the score is 0.6 to below 0.8, ask a near variant with changed numbers, data distribution, or wording.
   - If the score is 0.8 or above, increase difficulty or move to the next concept.
   - Ask whether the student wants another question. If yes, run `next-question` again with an adaptation-focused `--focus`.

6. At the end:
   - Run `python tools/ta.py mistakes` to update the review form.
   - Summarize mastered, improving, and needs-review concepts.

## Student-facing style

Use pure text interaction:
- Ask the question directly in Codex chat.
- Wait for the student's typed or uploaded answer.
- Give feedback directly in Codex chat.
- Never tell students to run commands unless they explicitly ask.
