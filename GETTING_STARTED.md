# Getting Started For Students

This virtual TA is designed to be used through plain English in Codex. You do not need coding or terminal experience.

## 0. Install From A Blank Codex Project

Choose **Start from scratch** in Codex, then paste:

```text
Please install this repo https://github.com/hanzhao-wang/virtual-ta into ~/Desktop/virtual-ta and set up the Student Virtual TA. Clone the repo if needed, create a Python environment, install the requirements, and run the setup doctor. Explain that I should manually put my course files into ~/Desktop/virtual-ta/resources before indexing. Do not index yet unless course files are already present. When explaining how to use the TA, give me plain-English Codex prompts only, not terminal commands, unless I ask for commands.
```

## 1. Add Course Files

After setup, manually put slides, tutorials, exercises, assignment guides, data dictionaries, and quizzes into:

```text
~/Desktop/virtual-ta/resources
```

Suggested folders:

- `Lectures`
- `Question Books`
- `Exercises`
- `Quizzes`
- `Assignment`

## 2. Index The Course

After adding files, paste this into Codex:

```text
I have added my course files under resources. Please index them with automatic image captioning. After indexing, explain how I can use this virtual TA using plain-English Codex prompts only. Do not give me terminal commands unless I ask for them.
```

## 3. Ask Course Questions

Paste prompts like:

```text
What is overfitting and how do we detect it? Please answer from my course materials first and cite the exact slide/page if available.
```

```text
Explain the difference between validation error and test error using a simple business example.
```

```text
Is model stacking covered in this course? If yes, point me to the relevant file and page/slide.
```

## 4. Generate Practice

Paste prompts like:

```text
Quiz me one question at a time on decision trees and random forests. Wait for my answer, then grade it, explain the correction, and remember any mistakes.
```

```text
I uploaded my answer. Please grade it, explain what I missed, and update my mistake memory.
```

```text
Give me another question testing the same concept I got wrong, but change the business scenario and numbers.
```

For a non-interactive practice sheet, ask:

```text
Create a 5-question practice sheet on gradient boosting with answers and explanations.
```

## 5. Generate Mock Exams

Paste prompts like:

```text
Create an 8-question mock exam covering weeks 2 to 8. Include marks, answers, explanations, and source coverage.
```

```text
Create a PDF mock exam on model evaluation and tree-based methods.
```

## 6. Review Mistakes

Paste prompts like:

```text
Show my mistake review form and tell me which concepts I should retry next.
```

```text
Based on my previous mistakes, create a short targeted practice session.
```

Codex will run the local TA tools internally and summarize the result for you.
