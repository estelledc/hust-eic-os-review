# Lab Studio Practice Mode Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将现有“实践模式”从题目列表式交互升级为 Lab Studio：用户可以在本站内按实验路线完成观察、操作、检查、复盘，并在每一步理解背后的操作系统机制。

**Architecture:** 保留 GitHub Pages 友好的静态架构：`build.py` 继续把结构化实验数据注入 `practice.html`，`assets/app.js` 继续承担浏览器端交互、验证、进度保存和报告生成。核心变化是把 `content/practice-labs.json` 从“lab -> tasks”升级为“lab -> phases -> steps/checkpoints/simulators”，并把 UI 从任务卡片列表改为阶段式实验工作台。

**Tech Stack:** Python static generator, Markdown, vanilla JavaScript, CSS, `localStorage`, `unittest`, Playwright browser verification.

---

## 1. 背景与边界

### 当前基线

当前实践模式已经具备：

- `content/practice.md`：实践模式说明和 `data-practice-workbench` 挂载点。
- `content/practice-labs.json`：9 个 Lab、45 个任务，任务类型覆盖 `choice`、`text`、`fill`、`code`、`command`。
- `build.py`：通过 `window.__PRACTICE_LABS__` 注入实验数据。
- `assets/app.js`：渲染 Lab 列表、任务卡片、答案检查、提示、报告草稿、本地进度保存。
- `tests/test_practice_mode.py`：验证实践页面生成、数据完整性和引擎钩子。

当前主要问题：

- 用户看到的是“做题列表”，不是“实验旅程”。
- 任务由控件类型驱动，而不是由学习目标驱动。
- 命令模拟器和代码区只是输入控件，缺少系统状态可视化。
- 失败反馈偏泛化，不能指出用户错在什么机制。
- 报告草稿只在末尾生成，没有贯穿学习过程收集用户理解。

### 内容边界

- 只采用 HIT-OSlab 的 Lab1-Lab9 题目路线，不照搬源码、答案或讲解。
- 不在浏览器中真实编译或运行 Linux 0.11。
- 不引入后端，不上传用户答案。
- 不要求用户安装 Bochs、GDB 或 Linux 0.11 环境。
- 所有交互、状态和报告继续保存在浏览器 `localStorage`。

### 调研依据

- HIT-OSlab 路线：[Joker001014/HIT-OSlab](https://github.com/Joker001014/HIT-OSlab)、[HIT 操作系统实验指导书](https://deathking.github.io/hit-oslab/)
- OS 实验课程形态：[MIT 6.1810](https://pdos.csail.mit.edu/6.1810/2025/schedule.html)、[OSTEP Projects](https://github.com/remzi-arpacidusseau/ostep-projects)、[Stanford CS140 Pintos](https://web.stanford.edu/class/archive/cs/cs140/cs140.1088/projects/)
- 交互式学习形态：[Codecademy](https://www.codecademy.com/)、[freeCodeCamp](https://github.com/freeCodeCamp/freeCodeCamp)、[Exercism](https://exercism.org/docs/using/solving-exercises/working-locally)
- UX 与学习原则：[NNGroup 10 Usability Heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/)、[Progressive Disclosure](https://www.nngroup.com/articles/progressive-disclosure/)、[Response Times](https://www.nngroup.com/articles/response-times-3-important-limits/)、[WCAG Error Identification](https://www.w3.org/WAI/WCAG22/Understanding/error-identification)、[CAST UDL Guidelines](https://udlguidelines.cast.org/)

---

## 2. 产品设计目标

### 一句话定位

实践模式是一个浏览器内 OS 实验工作台：用户不用配置真实环境，也能按 HIT-OSlab 路线一步步观察机制、完成关键操作、理解错误原因、形成实验报告骨架。

### 用户体验目标

1. 用户进入实践模式后，能先选择学习路径，而不是直接面对 9 个 Lab。
2. 用户进入某个 Lab 后，先知道这个实验解决什么问题、会学到什么、预计用多久。
3. 用户每一步都能看到“为什么做这一步”和“系统状态发生了什么变化”。
4. 用户提交错误答案时，能收到诊断反馈，而不是简单的失败提示。
5. 用户完成 Lab 后，能得到一份可继续完善的学习档案。

### 推荐学习路径

入口页提供三个路径：

- `快速体验`：每个 Lab 只做核心 3-5 步，适合第一次了解全局。
- `完整实践`：按 Lab1 到 Lab9 推进，保存完整进度。
- `考前重点`：按机制主题组织，例如引导、系统调用、进程、同步、内存、设备、文件系统。

实现上不需要三套内容。数据层给每个 step 增加 `tracks` 字段：

```json
{
  "tracks": ["quick", "full", "exam"]
}
```

UI 根据当前路径过滤或标记重点步骤。

---

## 3. 信息架构

### 实践首页

页面结构：

1. 顶部状态条
   - 总进度
   - 最近继续的 Lab
   - 当前学习路径
   - 本地保存状态

2. 路径选择区
   - 快速体验
   - 完整实践
   - 考前重点

3. Lab 地图
   - Lab1 熟悉实验环境
   - Lab2 操作系统的引导
   - Lab3 系统调用
   - Lab4 进程运行轨迹的跟踪与统计
   - Lab5 基于内核栈切换的进程切换
   - Lab6 信号量的实现与应用
   - Lab7 地址映射与共享
   - Lab8 终端设备的控制
   - Lab9 proc 文件系统的实现

4. 学习档案入口
   - 已掌握概念
   - 常见错因
   - 报告草稿
   - 待复习步骤

### Lab 工作台

推荐布局：桌面端使用左右分栏，移动端改为单列。

左侧任务区：

- Lab 标题、目标、预计时间。
- 四阶段 timeline：预备、观察、操作、复盘。
- 当前 step 的题目、输入控件、提示、检查按钮。

右侧理解区：

- 机制图或状态图。
- 命令模拟输出。
- 代码片段上下文。
- 错因诊断。
- 当前步骤和真实实验的关系。

底部/侧边学习档案：

- 当前 Lab 已记录的解释。
- 用户答错过的概念。
- 报告段落草稿。

---

## 4. 每个 Lab 的阶段模型

每个 Lab 固定分为 4 个阶段，但每个阶段的 step 数量可以不同。

### Phase 1: 预备

目的：降低进入成本，建立 mental model。

包含：

- 本 Lab 要解决的真实问题。
- 涉及的关键文件、函数、概念。
- 完成后用户应该能解释什么。
- 前置知识检查。

适合交互：

- 概念匹配。
- 关键路径排序。
- 小型选择题。

### Phase 2: 观察

目的：先看机制运行，再要求用户操作。

包含：

- 状态流图。
- 时间线。
- 关键数据结构变化。
- 用户态/内核态、进程状态、页表、缓冲区等可视状态。

适合交互：

- trace 路径选择。
- 状态拖拽或排序。
- 根据模拟输出判断下一步。

### Phase 3: 操作

目的：完成实验中的关键动作，但不真实运行 Linux 0.11。

包含：

- 命令模拟。
- 代码片段补全。
- 参数选择。
- 输出解释。
- 边界条件判断。

适合交互：

- `command`
- `code`
- `fill`
- `choice`
- `explain`

### Phase 4: 复盘

目的：把操作变成可迁移的理解。

包含：

- 本 Lab 的核心机制总结。
- 用户自己的解释。
- 常见错因回顾。
- 真实 Linux 0.11 实验迁移提醒。
- 报告段落生成。

适合交互：

- 简答。
- 错因选择。
- 反思填空。
- 报告片段确认。

---

## 5. 数据模型设计

### 新顶层结构

目标文件：`content/practice-labs.json`

```json
{
  "version": 2,
  "tracks": [
    {
      "id": "quick",
      "title": "快速体验",
      "description": "每个 Lab 只完成核心步骤，先建立全局认识。"
    },
    {
      "id": "full",
      "title": "完整实践",
      "description": "按 Lab1 到 Lab9 完成全部阶段和检查点。"
    },
    {
      "id": "exam",
      "title": "考前重点",
      "description": "按高频机制和易错点组织任务。"
    }
  ],
  "labs": []
}
```

### Lab 结构

```json
{
  "id": "lab3",
  "title": "系统调用",
  "focus": "理解用户态如何通过系统调用进入内核态",
  "estimatedMinutes": 35,
  "difficulty": "medium",
  "concepts": ["用户态", "内核态", "int 0x80", "system_call", "sys_call_table"],
  "sourceRoute": {
    "name": "HIT-OSlab Lab3",
    "url": "https://github.com/Joker001014/HIT-OSlab"
  },
  "outcomes": [
    "能解释系统调用和普通函数调用的区别",
    "能描述系统调用号如何找到内核函数",
    "能说明为什么需要从用户态切换到内核态"
  ],
  "phases": []
}
```

### Phase 结构

```json
{
  "id": "observe",
  "title": "观察路径",
  "purpose": "先看一次系统调用从用户态进入内核态的完整状态流。",
  "steps": []
}
```

### Step 结构

```json
{
  "id": "lab3-observe-trace",
  "title": "追踪系统调用路径",
  "goal": "识别用户态到内核态的关键跳转点",
  "tracks": ["quick", "full", "exam"],
  "interaction": "trace",
  "prompt": "把系统调用路径按发生顺序排列。",
  "context": "用户程序不会直接调用内核函数，而是通过约定入口进入内核。",
  "simulator": {
    "kind": "state-flow",
    "nodes": ["user program", "libc wrapper", "int 0x80", "system_call", "sys_call_table", "sys_xxx", "return"],
    "highlightOnPass": ["int 0x80", "system_call", "sys_call_table"]
  },
  "starter": null,
  "checks": [
    {
      "kind": "orderedItems",
      "answer": ["user program", "libc wrapper", "int 0x80", "system_call", "sys_call_table", "sys_xxx", "return"]
    }
  ],
  "hints": [
    {
      "level": 1,
      "text": "先区分用户态封装和真正进入内核的入口。"
    },
    {
      "level": 2,
      "text": "`int 0x80` 是 Linux 0.11 中进入系统调用处理流程的关键入口。"
    },
    {
      "level": 3,
      "text": "`system_call` 会根据系统调用号去 `sys_call_table` 找到具体处理函数。"
    }
  ],
  "misconceptions": [
    {
      "id": "libc-is-kernel",
      "detect": {
        "kind": "orderedBefore",
        "item": "sys_xxx",
        "before": "int 0x80"
      },
      "feedback": "这里把用户态封装和内核函数混在一起了。用户代码必须先通过陷入入口进入内核。"
    }
  ],
  "success": "路径正确。你已经抓住了系统调用的本质：用户程序通过受控入口请求内核代办特权操作。",
  "reflectionPrompt": "用一句话说明系统调用为什么不能只是普通函数调用。"
}
```

### 交互类型枚举

第一轮建议支持以下交互：

- `choice`：单选或多选。
- `fill`：填空。
- `explain`：简答解释，关键词 + 最短长度检查。
- `code`：代码片段编辑，关键词、顺序或结构检查。
- `command`：命令模拟器，按序命令检查。
- `trace`：路径排序或状态流选择。
- `diagnose`：错因诊断题。
- `reflection`：复盘文本，进入学习档案。

不建议第一轮引入拖拽库。`trace` 可以用按钮上移/下移实现，降低依赖和移动端风险。

---

## 6. Lab1 样例流程

Lab1 目标：用户理解实验环境链路，不需要真实安装环境，也能说清楚源码、编译产物、镜像、Bochs、挂载目录之间的关系。

### Phase 1: 预备

Step 1：识别实验对象

- `interaction`: `choice`
- 用户要区分：宿主系统、Linux 0.11 源码、`Image`、Bochs、磁盘镜像。
- 错因反馈：
  - 如果选择“在 Bochs 里改源码”，提示“Bochs 是模拟运行环境，不是宿主源码编辑器”。
  - 如果选择“挂载状态运行 Bochs”，提示“镜像被宿主挂载和被 Bochs 使用不能混为一谈”。

Step 2：实验链路排序

- `interaction`: `trace`
- 正确路径：修改源码 -> 编译 Image -> 准备镜像文件交换 -> 启动 Bochs -> 在 Linux 0.11 中验证。
- 右侧状态图展示每一步产物。

### Phase 2: 观察

Step 3：观察 Image 的角色

- `interaction`: `diagnose`
- 给出三段模拟描述，让用户判断哪一段混淆了 `Image` 和磁盘镜像。
- 通过后解释：`Image` 是启动内核映像，磁盘镜像用于模拟硬盘内容。

Step 4：观察文件交换边界

- `interaction`: `choice`
- 题目围绕“为什么不能一边挂载镜像，一边让 Bochs 使用它”。
- 成功反馈强调资源占用和一致性风险。

### Phase 3: 操作

Step 5：命令模拟

- `interaction`: `command`
- 用户输入：

```bash
cd oslab/linux-0.11
make
cd ..
./run
```

- 检查重点不是命令是否绝对真实，而是顺序是否表达“改源码、编译、启动模拟器”。

Step 6：解释一次失败

- `interaction`: `explain`
- 模拟输出：`Image` 没有变化，Bochs 启动后看不到修改效果。
- 用户需要解释可能原因：没有重新编译、启动的不是新的镜像、修改位置不在被编译路径中。

### Phase 4: 复盘

Step 7：生成 Lab1 学习档案

- `interaction`: `reflection`
- 用户回答：
  - 我理解的实验链路是：
  - 我最容易混淆的是：
  - 真实环境中我会先检查：

学习档案收集：

- 用户写出的实验链路。
- 用户错过的概念。
- 可迁移到真实实验的检查清单。

---

## 7. 9 个 Lab 的重设计重点

| Lab | 机制主题 | 重点模拟/状态图 | 最重要的诊断反馈 |
| --- | --- | --- | --- |
| Lab1 熟悉实验环境 | 实验链路和文件边界 | 源码 -> Image -> Bochs -> Linux 0.11 | 混淆宿主环境、模拟器和镜像 |
| Lab2 操作系统的引导 | BIOS、bootsect、setup、head | 启动阶段 timeline | 把引导加载和内核运行混为一谈 |
| Lab3 系统调用 | 用户态到内核态入口 | system call trace | 把库函数、陷入入口、内核函数混淆 |
| Lab4 进程运行轨迹 | 进程状态与日志统计 | 进程状态 timeline | 只看日志文本，不理解状态转换 |
| Lab5 内核栈切换 | 进程切换与栈帧 | 内核栈 frame diagram | 把用户栈、内核栈、TSS/调度切换混淆 |
| Lab6 信号量 | P/V、阻塞队列、临界区 | semaphore counter + wait queue | 把忙等、阻塞、唤醒顺序混淆 |
| Lab7 地址映射与共享 | 逻辑地址、线性地址、物理地址 | 页表映射图 | 把地址名词当成同一层地址 |
| Lab8 终端设备 | 键盘输入、缓冲区、TTY | 输入队列和回显状态 | 把设备中断、缓冲区、进程读取混淆 |
| Lab9 proc 文件系统 | 虚拟文件和内核状态导出 | read path + generated content | 把真实磁盘文件和虚拟文件混淆 |

---

## 8. 反馈规则

### 提示分层

每个可检查 step 至少提供三层提示：

1. 方向提示：提醒用户应该关注哪类机制。
2. 概念提示：点出关键概念或关键文件名。
3. 接近答案提示：指出下一步如何判断，但不直接给完整答案。

UI 行为：

- 默认只显示“提示 1”按钮。
- 用户再次点击后显示“提示 2”。
- 第三次显示“提示 3”。
- 保存用户使用过的提示层级，学习档案里可以记录“依赖提示完成”。

### 错因诊断

每个重点 step 提供 `misconceptions`。

诊断优先级：

1. 命中特定错因时，显示对应反馈。
2. 未命中特定错因但验证失败时，显示通用反馈。
3. 验证通过时，显示成功解释和下一步建议。

示例：

```json
{
  "misconceptions": [
    {
      "id": "physical-vs-linear-address",
      "feedback": "这里混淆了线性地址和物理地址。分页机制生效后，CPU 看到的线性地址还需要经过页表转换。"
    }
  ]
}
```

### 反馈文案要求

- 不只说“错误”。
- 必须指出用户当前思路的问题。
- 必须回到本 Lab 的核心机制。
- 不直接给完整答案，除非已经是复盘阶段。

---

## 9. 状态与进度保存

建议将 `localStorage` key 从当前 `os-review-practice-workbench` 升级为版本化结构：

```json
{
  "version": 2,
  "activeTrack": "full",
  "activeLabId": "lab1",
  "activePhaseId": "operate",
  "answers": {},
  "passed": {},
  "feedback": {},
  "hintLevels": {},
  "reflections": {},
  "misconceptions": {},
  "report": {}
}
```

迁移规则：

- 如果读到旧版数据，保留已通过 step 的状态。
- 如果旧 task id 无法映射到新 step id，不删除，放入 `legacy` 字段。
- UI 提示“已保留旧版进度，可重新完成新版阶段”。

---

## 10. 实施任务

### Task 1: 写失败测试，锁定新版数据模型

**Files:**

- Modify: `tests/test_practice_mode.py`

**Steps:**

1. 增加测试：`content/practice-labs.json` 顶层必须包含 `version: 2`。
2. 增加测试：必须包含 `tracks`，且 id 包含 `quick`、`full`、`exam`。
3. 增加测试：每个 lab 必须包含 `estimatedMinutes`、`concepts`、`outcomes`、`phases`。
4. 增加测试：每个 lab 必须有 `prepare`、`observe`、`operate`、`reflect` 四个 phase。
5. 增加测试：每个 step 必须包含 `goal`、`tracks`、`interaction`、`prompt`、`hints`、`success`。
6. 增加测试：至少出现 `choice`、`fill`、`explain`、`code`、`command`、`trace`、`diagnose`、`reflection`。
7. 运行：

```bash
/tmp/hust-eic-os-review-venv/bin/python -m unittest tests/test_practice_mode.py
```

Expected: FAIL，因为当前数据模型仍是 v1。

### Task 2: 设计并迁移 `content/practice-labs.json`

**Files:**

- Modify: `content/practice-labs.json`

**Steps:**

1. 将顶层结构升级为 `version: 2`。
2. 添加三个 `tracks`。
3. 把每个 Lab 的原 `tasks` 拆入四个 phase。
4. 每个 Lab 至少保留 7 个 step：
   - 预备 1-2 个。
   - 观察 1-2 个。
   - 操作 2-3 个。
   - 复盘 1 个。
5. 给每个重点 step 添加三层 `hints`。
6. 给每个 Lab 至少 2 个 step 添加 `misconceptions`。
7. 为 Lab1 写完整高质量样例，后续 Lab 可以先达到结构完整，再逐步精修文案。
8. 保留 HIT-OSlab attribution 和学习边界说明，不加入可直接提交的完整答案。

### Task 3: 更新实践入口文案

**Files:**

- Modify: `content/practice.md`

**Steps:**

1. 将“交互式学习”文案改成“Lab Studio 实验工作台”。
2. 明确三条路径：快速体验、完整实践、考前重点。
3. 明确学习边界：不真实编译运行 Linux 0.11，不提供可提交答案。
4. 保留 `data-practice-workbench` 挂载点。
5. 保留 `data-practice-report`，但文案从“生成报告草稿”调整为“查看学习档案”。

### Task 4: 改造实践引擎的数据读取层

**Files:**

- Modify: `assets/app.js`

**Steps:**

1. 在 `setupPracticeWorkbench()` 内识别 `window.__PRACTICE_LABS__.version`。
2. 为 v2 数据实现 `labs -> phases -> steps` 的扁平化辅助函数。
3. 保留 v1 数据兼容渲染，直到 v2 页面通过测试。
4. 新增 `activeTrack`、`activePhaseId`、`hintLevels`、`reflections`、`misconceptions` 状态字段。
5. 写旧进度迁移函数，不删除用户旧进度。

### Task 5: 实现路径选择和 Lab 地图

**Files:**

- Modify: `assets/app.js`
- Modify: `assets/style.css`

**Steps:**

1. 在 workbench 顶部渲染路径 segmented control。
2. 点击路径后保存 `activeTrack`。
3. Lab tabs 改为 Lab 地图，展示：
   - Lab 标题。
   - 机制主题。
   - 完成度。
   - 当前路径下的重点 step 数。
4. 移动端改成横向可滚动或折叠选择器。

### Task 6: 实现阶段式 Lab 工作台

**Files:**

- Modify: `assets/app.js`
- Modify: `assets/style.css`

**Steps:**

1. Lab 页头展示 `focus`、`estimatedMinutes`、`concepts`、`outcomes`。
2. 渲染四阶段 timeline：预备、观察、操作、复盘。
3. 点击 phase 切换当前阶段。
4. 当前阶段只展示对应 steps。
5. 右侧理解区展示当前 step 的 `context`、`simulator`、错因诊断和报告收集状态。

### Task 7: 实现新交互类型

**Files:**

- Modify: `assets/app.js`
- Modify: `assets/style.css`

**Steps:**

1. 将旧 `text` 迁移为新 `explain`，保留兼容。
2. 实现 `trace`：
   - 用按钮列表展示条目。
   - 每项有上移/下移按钮。
   - 检查顺序是否匹配。
3. 实现 `diagnose`：
   - 展示模拟错误场景。
   - 用户选择错因。
   - 通过后显示诊断解释。
4. 实现 `reflection`：
   - 文本输入。
   - 不做严格答案检查，只检查最短长度。
   - 保存到 `state.reflections` 和报告。
5. 保留 `choice`、`fill`、`code`、`command`。

### Task 8: 实现分层提示与诊断反馈

**Files:**

- Modify: `assets/app.js`
- Modify: `assets/style.css`

**Steps:**

1. 把提示状态从 boolean 改成数字层级。
2. 点击提示按钮时逐层显示。
3. 检查失败时先运行 `misconceptions` 检测。
4. 命中特定错因时显示对应反馈。
5. 保存错因 id 到 `state.misconceptions`。
6. 学习档案里统计错因类型。

### Task 9: 将报告草稿升级为学习档案

**Files:**

- Modify: `assets/app.js`
- Modify: `assets/style.css`

**Steps:**

1. 将 `renderReport()` 改为 `renderLearningPortfolio()`。
2. 学习档案包含：
   - 每个 Lab 完成度。
   - 用户写过的 reflection。
   - 命中过的 misconceptions。
   - 使用过三层提示的 step。
   - 可继续完善的报告段落。
3. 报告内容使用 Markdown textarea 保持静态部署简单。
4. 按 Lab 分段，便于用户后续整理。

### Task 10: 更新样式和响应式体验

**Files:**

- Modify: `assets/style.css`

**Steps:**

1. 用工作台布局替代当前“rail + task list + side card”的题库感。
2. 桌面端：左侧任务、右侧理解区。
3. 移动端：Lab 信息、phase tabs、step、理解区顺序堆叠。
4. 所有按钮、输入框、代码框、命令框设置稳定尺寸和可换行策略。
5. 不使用大面积单一色系，不引入装饰性渐变球。
6. 保证 390px 宽度无横向滚动。

### Task 11: 更新测试覆盖

**Files:**

- Modify: `tests/test_practice_mode.py`
- Create: `tests/test_practice_data_quality.py`

**Steps:**

1. `tests/test_practice_mode.py` 继续覆盖页面生成和引擎钩子。
2. 新增 `tests/test_practice_data_quality.py` 覆盖：
   - 所有 Lab 都有四阶段。
   - 所有 step 的 id 唯一。
   - 所有 step 的 `tracks` 都引用合法 track。
   - 所有 hints 至少 3 层。
   - 所有重点 Lab 至少 2 个 misconceptions。
   - 文案中不出现“实验答案”“详细注释”等边界外词汇。
3. 运行：

```bash
/tmp/hust-eic-os-review-venv/bin/python -m unittest tests/test_practice_mode.py tests/test_practice_data_quality.py
```

Expected: PASS。

### Task 12: 生成与浏览器验证

**Files:**

- Generated: `practice.html`
- Generated: `index.html`

**Steps:**

1. 运行：

```bash
/tmp/hust-eic-os-review-venv/bin/python -m compileall -q build.py tests
/tmp/hust-eic-os-review-venv/bin/python build.py
```

Expected: both commands PASS。

2. 启动本地服务：

```bash
python3 -m http.server 8020
```

3. 用浏览器验证：

- `http://127.0.0.1:8020/practice.html` 可以打开。
- 三条路径可以切换并持久保存。
- Lab1 四阶段可以切换。
- `trace` 可以调整顺序并检查。
- `command` 可以输入命令并检查。
- `diagnose` 可以显示错因反馈。
- `reflection` 可以进入学习档案。
- 刷新后进度保留。
- 390px 移动端没有横向溢出。

---

## 11. 验收标准

功能验收：

- 用户能在站内完成每个 Lab 的预备、观察、操作、复盘。
- 每个 Lab 至少包含一个观察型 step 和一个复盘型 step。
- 用户可以选择快速体验、完整实践、考前重点。
- 用户答案、提示层级、错因、反思都能保存。
- 学习档案能汇总用户的进度、解释和错因。

学习体验验收：

- 每个 Lab 都先解释目标，再要求用户操作。
- 每个失败反馈都指出一个具体学习方向。
- 每个重点机制都有状态图、路径图或模拟输出辅助理解。
- 没有直接搬运 HIT-OSlab 成品答案。

技术验收：

- 静态部署可用。
- 不引入后端服务。
- 不引入大型前端框架。
- 不破坏现有主题、导航、TOC 和 Mermaid 行为。
- 测试通过。
- 移动端无横向溢出。

---

## 12. 实施顺序建议

推荐按以下顺序做，降低返工：

1. 先完成 Task 1 和 Task 2，让数据模型稳定。
2. 再完成 Task 4，保证引擎能读 v2 数据。
3. 然后完成 Task 5 和 Task 6，把整体 UI 改成 Lab Studio。
4. 接着完成 Task 7 和 Task 8，补齐教学型交互。
5. 最后完成 Task 9 到 Task 12，补学习档案、样式和验证。

第一轮实现时，Lab1 文案做到完整标杆；Lab2-Lab9 先完成结构和关键反馈。第二轮再逐个精修每个 Lab 的模拟器和错因诊断。

---

## 13. 需要确认的产品决策

实施前建议确认三点：

1. 是否采用 `快速体验 / 完整实践 / 考前重点` 三路径。
2. 是否允许第一轮只把 Lab1 打磨成完整样例，Lab2-Lab9 先达到结构完整。
3. 是否把当前已有 v1 进度做兼容迁移，而不是清空重来。
