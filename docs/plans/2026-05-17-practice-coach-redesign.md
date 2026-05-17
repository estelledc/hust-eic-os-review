# Practice Coach Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 把实践模式从题单式任务页重构为单步教练式学习工作台，让零基础用户能在站内逐步理解、练习、检查和修正。

**Architecture:** 实践数据层新增 Lab 级驱动问题、白话目标、心智模型和真实实验迁移清单；Step 级新增 `coach` 脚手架，统一承载 why/observe/act/check/repair。前端只突出当前步骤，通过教练卡、机制画板、学习路线和错因修正形成闭环。

**Tech Stack:** 静态 HTML 生成器 `build.py`、原生 JavaScript `assets/app.js`、CSS `assets/style.css`、JSON 数据 `content/practice-labs.json`、`unittest` 数据质量测试。

---

### Task 1: 教学数据模型

**Files:**
- Modify: `content/practice-labs.json`
- Test: `tests/test_practice_data_quality.py`

**Steps:**
1. 为每个 Lab 添加 `drivingQuestion`、`plainLanguageGoal`、`mentalModel`、`transferChecklist`。
2. 为每个 Step 添加 `coach.why`、`coach.observe`、`coach.act`、`coach.check`、`coach.repair`。
3. 运行定向测试，确认数据不是空字段。

**Verification:**

```bash
/tmp/hust-eic-os-review-venv/bin/python -m unittest \
  tests.test_practice_data_quality.PracticeDataQualityTest.test_every_lab_has_first_principles_coach_model \
  tests.test_practice_data_quality.PracticeDataQualityTest.test_every_step_has_coach_scaffolding
```

### Task 2: 单步教练式前端

**Files:**
- Modify: `assets/app.js`
- Test: `tests/test_practice_mode.py`

**Steps:**
1. 新增 `renderCoachStep`，替代当前阶段内铺开所有任务卡的呈现方式。
2. 新增 `renderLearningRoute`，保留路线可见性，但不抢当前步骤注意力。
3. 新增 `renderMechanismBoard`，把 Lab 级心智模型、状态流、迁移清单放到右侧理解区。
4. 新增 `renderRepairFeedback`，让错误反馈指向概念混淆和补救练习。
5. 新增 `data-practice-next-step` 和 `data-practice-route-step` 交互。

**Verification:**

```bash
node --check assets/app.js
/tmp/hust-eic-os-review-venv/bin/python -m unittest \
  tests.test_practice_mode.PracticeModeBuildTest.test_practice_engine_hooks_are_present
```

### Task 3: 教练式布局

**Files:**
- Modify: `assets/style.css`
- Modify: `content/practice.md`

**Steps:**
1. 为教练卡、路线、机制画板、补救反馈增加样式。
2. 入口文案说明“单步教练卡 + 机制画板”的学习方式。
3. 桌面端保持当前步骤主导，移动端改为单列但不隐藏核心学习功能。

**Verification:**

```bash
/tmp/hust-eic-os-review-venv/bin/python build.py
```

### Task 4: 浏览器验收

**Checks:**
- 默认零基础路径只突出一个 `.practice-coach-card`。
- 旧 `.practice-task` 不再作为主任务卡铺开。
- 机制画板显示 Lab 心智模型、状态流和迁移清单。
- 选择错误答案后出现 `.practice-coach-result.is-repair`。
- 选择正确答案后出现 `.practice-coach-result.is-ok`，并能通过 `data-practice-next-step` 进入下一步。
- 390px 移动视口无横向溢出。

**Verification Commands:**

```bash
node --check assets/app.js
/tmp/hust-eic-os-review-venv/bin/python -m unittest tests/test_practice_mode.py tests/test_practice_data_quality.py
/tmp/hust-eic-os-review-venv/bin/python -m compileall -q build.py tests
/tmp/hust-eic-os-review-venv/bin/python build.py
```
