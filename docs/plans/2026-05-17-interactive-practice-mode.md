# Interactive Practice Mode Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Upgrade practice mode from a guided checklist into a fully static, browser-only interactive learning workspace where users can complete every Lab1-Lab9 practice step inside the site while learning the operating-system concept behind each action.

**Architecture:** Store all Lab content and validation metadata in `content/practice-labs.json`. `build.py` injects this data into `practice.html` and renders a shell. `assets/app.js` owns the client-side practice engine: task rendering, answer validation, command simulation, code/fill/input/choice controls, progress persistence, and report draft generation.

**Tech Stack:** Python static generator, Markdown, vanilla JavaScript, CSS, `localStorage`, `unittest`, Playwright browser verification.

---

### Task 1: Test the Interactive Contract

**Files:**
- Modify: `tests/test_practice_mode.py`

**Steps:**
1. Add tests requiring `content/practice-labs.json` to contain 9 labs.
2. Require every lab to expose interactive tasks.
3. Require task types to cover `choice`, `text`, `fill`, `code`, and `command`.
4. Require every task to include `lesson`, `hint`, `feedback`, and `success` copy so the interaction teaches, not just grades.
5. Require generated `practice.html` to include `window.__PRACTICE_LABS__`, `data-practice-workbench`, and report controls.
6. Run `/tmp/hust-eic-os-review-venv/bin/python -m unittest tests/test_practice_mode.py` and confirm failure before implementation.

### Task 2: Add Structured Lab Data

**Files:**
- Create: `content/practice-labs.json`

**Steps:**
1. Define Lab1-Lab9 metadata: id, title, focus, goal, steps.
2. For each lab, include at least five browser-completable tasks except Lab8 where four is acceptable.
3. Use validation rules that are educational, not answer dumps: exact options, keyword checks, ordered command simulation, code keyword checks, and fill blanks.
4. For every task, write the learning intent (`lesson`), a non-answer hint (`hint`), failure feedback, and success explanation.
5. Include report prompts per lab.

### Task 3: Render the Workbench Shell

**Files:**
- Modify: `build.py`
- Modify: `content/practice.md`

**Steps:**
1. Add a helper that reads `content/practice-labs.json`.
2. Inject JSON into `practice.html` as `window.__PRACTICE_LABS__`.
3. Replace the long static Lab cards with a compact workbench shell in `content/practice.md`.
4. Keep the source boundary and HIT-OSlab attribution.

### Task 4: Implement the Browser Practice Engine

**Files:**
- Modify: `assets/app.js`

**Steps:**
1. Render lab tabs and task cards from `window.__PRACTICE_LABS__`.
2. Render controls for `choice`, `text`, `fill`, `code`, and `command`.
3. Implement validators for each type.
4. Save answers, pass/fail status, active lab, and progress to `localStorage`.
5. Show task-level lesson text before input, hint on demand, targeted failure feedback, and success explanations after passing.
6. Generate a report draft from completed labs and user answers.
7. Keep existing theme picker, chipbar, TOC, and Mermaid behavior intact.

### Task 5: Style the Interactive Workspace

**Files:**
- Modify: `assets/style.css`

**Steps:**
1. Add workbench layout: lab rail, task pane, status/report panel.
2. Add compact form controls, code editor textarea, command terminal simulator, validation feedback, and progress chips.
3. Preserve mobile usability with no horizontal overflow.

### Task 6: Verify

**Files:**
- Run generated outputs

**Steps:**
1. Run `/tmp/hust-eic-os-review-venv/bin/python -m unittest tests/test_practice_mode.py`.
2. Run `/tmp/hust-eic-os-review-venv/bin/python -m compileall -q build.py tests`.
3. Run `/tmp/hust-eic-os-review-venv/bin/python build.py`.
4. Start `python3 -m http.server <free-port>`.
5. Use Playwright to verify:
   - `practice.html` loads.
   - 9 labs render.
   - all required task control types exist.
   - a choice task can be completed.
   - a command task can be simulated and completed.
   - progress persists after reload.
   - report draft opens.
   - mobile viewport has no horizontal overflow.
