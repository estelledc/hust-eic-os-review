# Practice Content First Principles Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 从第一性原理重构实践模块内容，让零基础用户先理解每个实验要改变什么系统状态，再通过站内交互逐步完成题目路径。

**Architecture:** 保留现有静态站点和 Lab Studio 工作台架构，主要改造 `content/practice-labs.json`。每个 Lab 用“驱动问题 -> 心智模型 -> 状态流 -> 可观察证据 -> 典型误解 -> 迁移到真实实验”的内容骨架组织；每个 Step 必须对应一个具体认知动作，而不是泛化的“做题/补全/解释”。

**Tech Stack:** 静态 HTML 生成器 `build.py`、JSON 内容数据 `content/practice-labs.json`、原生 JavaScript 渲染 `assets/app.js`、CSS `assets/style.css`、Python `unittest` 数据质量测试。

---

## 背景与边界

### 外部题目边界

本项目使用 HIT-OSlab 的题目路线，但不照搬答案和讲解。根据 Joker001014/HIT-OSlab README，该仓库提供 Lab1 到 Lab9 的实验入口；根据 HIT-OSLAB-MANUAL，核心实验覆盖引导、系统调用、进程轨迹、信号量、地址映射、终端控制、proc 文件系统等操作系统基本主题。

参考来源：
- `https://github.com/Joker001014/HIT-OSlab`
- `https://hoverwinter.gitbooks.io/hit-oslab-manual/content/overview.html`
- `https://hoverwinter.gitbooks.io/hit-oslab-manual/content/environment.html`

### 站内实现边界

这次不真正编译或运行 Linux 0.11。实践模式仍然是 GitHub Pages 友好的交互式学习版：用户在浏览器里完成选择、填空、排序、代码片段编辑、命令模拟、结果检查、错因修正和学习档案保存。

### 现状诊断

当前实践模块已经有 `starter / quick / full / exam` 四条路径，也已经有 `phases`、`steps`、`coach`、`mentalModel` 等字段。但内容层面仍有三个问题：

1. 很多 Step 是模板化生成的，提示语类似“按顺序输入命令模拟本 Lab 的关键动作”“补全或改写片段，让它体现本 Lab 的关键机制”，对零基础用户帮助有限。
2. `coach.why / observe / act / check / repair` 已有字段，但不少内容只是把 `prompt/context/success` 重新包装，没有真正解释“为什么这一步现在出现”。
3. 每个 Lab 的学习结构还不够像真实认知路径。用户需要先建立对象边界、状态变化、证据链，再去看命令、代码和报告。

---

## 第一性原理

实践模块不是“把实验指导书变成题库”，而是帮助用户建立操作系统实验的基本推理能力。

每个 Lab 都必须回答 6 个基础问题：

1. **谁在行动？** 是 BIOS、bootsect、用户程序、内核、进程、终端驱动，还是文件系统入口？
2. **状态在哪里？** 是寄存器、栈、系统调用表、进程状态、信号量计数、页表、缓冲区，还是内核数据结构？
3. **边界在哪里？** 是用户态/内核态、逻辑地址/物理地址、宿主机/Bochs、真实文件/虚拟文件，还是中断上下文/进程上下文？
4. **动作改变了什么？** 一条命令、一段汇编、一个系统调用或一个回调函数到底让哪个状态发生变化？
5. **证据怎么观察？** 用户能从输出、日志、状态表、模拟终端、排序结果、报告文字中看到什么？
6. **错了怎么定位？** 如果结果不对，应先怀疑层次混淆、顺序混淆、状态没更新、入口没接上，还是证据不充分？

这 6 个问题必须进入每个 Lab 的内容，而不是只在总说明里出现。

---

## 内容模型

### Lab 级字段

保留现有字段，并把内容质量提高到可教学：

```json
{
  "drivingQuestion": "这一关真正要解释的系统问题",
  "plainLanguageGoal": "给零基础用户的一句话目标",
  "mentalModel": {
    "title": "心智模型名称",
    "explanation": "不依赖代码细节的机制解释",
    "flow": ["入口", "状态变化", "可观察结果"],
    "checkpoints": ["最容易混淆的边界"]
  },
  "firstPrinciples": {
    "actors": ["谁在行动"],
    "state": ["状态在哪里"],
    "boundary": ["关键边界"],
    "transition": ["动作怎样改变状态"],
    "evidence": ["用户应观察什么"],
    "failureModes": ["典型失败路径"]
  },
  "transferChecklist": ["迁移到真实 Linux 0.11 实验前要检查什么"]
}
```

### Step 级字段

保留现有渲染字段，重写内容语义：

```json
{
  "title": "一个具体认知动作，而不是泛化标题",
  "goal": "完成后用户能掌握的最小能力",
  "context": "为什么这个动作现在出现",
  "prompt": "用户要完成的具体输入/选择/排序/编辑",
  "coach": {
    "why": "本步的学习理由",
    "observe": "先观察哪条状态线索",
    "act": "现在做什么",
    "check": "做对后应理解什么",
    "repair": "做错后回到哪个概念边界"
  },
  "misconceptions": [
    {
      "id": "稳定错因 id",
      "feedback": "指出具体误解，不泛泛说错"
    }
  ]
}
```

---

## Lab 内容重构路线

### Lab1 熟悉实验环境

核心问题：我改的是源码，但 Bochs 跑的是 Image，怎么确认修改真的进入运行结果？

内容路径：
1. 区分宿主机、源码目录、`Image`、Bochs、磁盘镜像。
2. 排列“改源码 -> 编译 -> 启动 -> 观察”的证据链。
3. 模拟一次“忘记重新编译”的错因诊断。
4. 用命令模拟表达构建与运行边界。
5. 复盘“我看到的输出来自哪个产物”。

### Lab2 操作系统的引导

核心问题：控制权怎样从 BIOS 一棒一棒交给 Linux 0.11 内核？

内容路径：
1. 把 BIOS、bootsect、setup、head、main 作为接力链。
2. 区分“加载代码”和“跳转执行”。
3. 排序启动阶段，解释为什么不能跳步。
4. 通过模拟输出判断早期代码到底跑到哪里。
5. 复盘“控制权”和“内存位置”的关系。

### Lab3 系统调用

核心问题：用户程序不能直接进入内核，为什么系统调用能让它安全请求内核服务？

内容路径：
1. 区分普通函数调用和陷入内核。
2. 建立“用户 stub -> 中断/陷入 -> 系统调用号 -> 系统调用表 -> 内核实现”的路径。
3. 模拟 `whoami` 需要接上的几个入口。
4. 诊断“用户程序能编译，但调用失败”的错因。
5. 复盘用户态/内核态边界。

### Lab4 进程运行轨迹的跟踪与统计

核心问题：进程状态变化看不见，怎样记录并从日志里看懂调度？

内容路径：
1. 认识进程状态不是文字标签，而是调度器改变的状态。
2. 设计最小日志字段：时间、pid、旧状态、新状态、原因。
3. 排序 fork、ready、running、blocked、exit 的轨迹。
4. 用站内日志片段计算等待时间或周转时间。
5. 复盘“记录点放在哪里”会改变结论。

### Lab5 基于内核栈切换的进程切换

核心问题：进程切换不是只换 pid，而是保存旧现场、恢复新现场。

内容路径：
1. 区分用户栈、内核栈、寄存器现场。
2. 建立“保存当前 esp/eip -> 切换栈 -> 恢复下个进程现场”的状态流。
3. 模拟一次缺少保存现场导致返回位置错误。
4. 用代码片段识别哪些值必须跨切换保存。
5. 复盘为什么内核栈能代表进程在内核里的暂停点。

### Lab6 信号量的实现与应用

核心问题：多个进程抢同一资源时，信号量怎样决定谁继续、谁等待、谁被唤醒？

内容路径：
1. 把信号量拆成“计数 + 等待队列”，而不是只看整数。
2. 区分 P 操作的申请/阻塞和 V 操作的释放/唤醒。
3. 用生产者-消费者模拟缓冲区空/满状态。
4. 诊断 P/V 顺序放错导致的互斥失败。
5. 复盘临界区、阻塞、唤醒三者关系。

### Lab7 地址映射与共享

核心问题：程序看到的地址不是物理地址，两个进程怎样通过映射共享同一页？

内容路径：
1. 区分逻辑地址、线性地址、物理地址。
2. 建立“段基址 + 偏移 -> 线性地址 -> 页表 -> 物理页”的路径。
3. 模拟同一物理页被两个进程不同线性地址指向。
4. 诊断“两个进程地址值一样/不一样”和“是否共享”的误解。
5. 复盘地址翻译和共享页的关系。

### Lab8 终端设备的控制

核心问题：按键和屏幕输出为什么要经过中断、缓冲区和终端驱动？

内容路径：
1. 区分键盘中断、扫描码、输入队列、读终端。
2. 建立“按键 -> 中断处理 -> 缓冲 -> 用户读/屏幕写”的状态流。
3. 模拟 F12 开关怎样改变输出转换规则。
4. 诊断把用户程序输出和终端驱动转换混为一谈的问题。
5. 复盘设备管理的入口和状态保存位置。

### Lab9 proc 文件系统的实现

核心问题：`/proc` 看起来像文件，为什么内容可以来自内核实时状态？

内容路径：
1. 区分普通磁盘文件和虚拟文件。
2. 建立“路径查找 -> inode/file 操作 -> read 回调 -> 生成文本”的路径。
3. 模拟一个 proc 节点怎样把进程表或内存状态转成输出。
4. 诊断写死字符串和动态读取内核状态的差别。
5. 复盘文件系统接口如何包装内核数据。

---

## 执行任务

### Task 1: 写内容质量测试

**Files:**
- Modify: `tests/test_practice_data_quality.py`

**Steps:**
1. 增加 `test_every_lab_has_first_principles_fields`，要求每个 Lab 有 `firstPrinciples.actors/state/boundary/transition/evidence/failureModes`。
2. 增加 `test_step_copy_is_lab_specific`，禁止高频模板句，例如“本 Lab 的关键机制”“按顺序输入命令模拟本 Lab 的关键动作”“补全或改写片段，让它体现本 Lab 的关键机制”。
3. 增加 `test_each_lab_has_evidence_oriented_steps`，要求每个 Lab 至少有 3 个 Step 的 `coach.observe` 明确指向可观察证据。
4. 运行测试并确认失败，因为当前内容还没有完成重构。

**Verification:**

```bash
/tmp/hust-eic-os-review-venv/bin/python -m unittest tests/test_practice_data_quality.py
```

### Task 2: 重写 Lab1-Lab3

**Files:**
- Modify: `content/practice-labs.json`

**Steps:**
1. 为 Lab1-Lab3 添加 `firstPrinciples`。
2. 重写 `beginner.story/why/analogy/firstGoal/glossary`，确保是零基础可读的白话解释。
3. 重写所有 Step 的 `title/goal/context/prompt/coach/hints/misconceptions/feedback/success`。
4. 保持现有 `interaction` 类型和 `checks` 机制，不引入前端不可识别的新题型。

**Verification:**

```bash
/tmp/hust-eic-os-review-venv/bin/python -m unittest tests/test_practice_data_quality.py
```

### Task 3: 重写 Lab4-Lab6

**Files:**
- Modify: `content/practice-labs.json`

**Steps:**
1. 为进程轨迹、进程切换、信号量分别建立状态流和证据链。
2. 增强 `trace/diagnose/fill/code/command/reflection` 的题目内容，让每一步都对应具体机制。
3. 确保复杂 Lab 的 `starter` 路径不会被过度压缩：Lab6 必须比 Lab1 有更多可见步骤。

**Verification:**

```bash
/tmp/hust-eic-os-review-venv/bin/python -m unittest tests/test_practice_data_quality.py
```

### Task 4: 重写 Lab7-Lab9

**Files:**
- Modify: `content/practice-labs.json`

**Steps:**
1. 为地址映射、终端设备、proc 文件系统分别建立“边界 -> 状态 -> 证据”内容。
2. 重写典型误解反馈，重点覆盖“地址相同不等于共享”“用户输出不等于设备驱动”“proc 文件不等于磁盘文件”。
3. 确保 `transferChecklist` 指向真实实验检查步骤，但不提供答案代码。

**Verification:**

```bash
/tmp/hust-eic-os-review-venv/bin/python -m unittest tests/test_practice_data_quality.py
```

### Task 5: 构建与页面回归

**Files:**
- Modify if needed: `assets/app.js`
- Modify if needed: `assets/style.css`
- Generated: `practice.html`

**Steps:**
1. 如果前端需要展示 `firstPrinciples`，只做最小适配，把它并入机制画板，不改变导航结构。
2. 运行 JS 语法检查。
3. 重新构建静态页面。
4. 用浏览器检查桌面和移动端实践页。

**Verification:**

```bash
node --check assets/app.js
/tmp/hust-eic-os-review-venv/bin/python -m unittest tests/test_practice_mode.py tests/test_practice_data_quality.py
/tmp/hust-eic-os-review-venv/bin/python -m compileall -q build.py tests
/tmp/hust-eic-os-review-venv/bin/python build.py
```

Browser checks:
- 默认零基础路径的第一步能用白话讲清当前 Lab。
- 机制画板能显示对象、状态、边界、证据。
- 错误反馈不只是“错了”，而是指出具体概念混淆。
- 每个 Lab 的步骤数量仍随复杂度变化。
- 390px 移动端无横向溢出。

---

## 需要确认的变更范围

这是一次大范围内容重构，预计会重写 `content/practice-labs.json` 中大部分教学文本，并可能小幅更新 `tests/test_practice_data_quality.py`、`assets/app.js` 和 `practice.html`。

确认后再进入代码模式执行；未确认前不批量改写 JSON 内容。
