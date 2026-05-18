# Practice 模式最终整合计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 把 practice 模式从「结构合规但内容模板化」推到「9 个 Lab 各有真实教学差异、交互梯度可见、加载性能可承载」。

**Architecture:** 保留现有 v2 数据模型（lab → phases → steps、4 tracks、8 interactions、coach + firstPrinciples + mentalModel）。重构集中在三处：① 内容层去模板化；② 渲染层拆 inline JSON、删 v1 死代码；③ 交互层让 simulator/trace/hints 真正有差异。

**Tech Stack:** Python static generator `build.py` · vanilla JavaScript `assets/app.js` · CSS `assets/style.css` · JSON 数据 `content/practice-labs.json` · `unittest`。

---

## 0. 本计划取代的旧 plan

下列 4 份 plan 描述的是同一套系统的演进切面，结构层目标已全部落地，剩余项合并到本计划。后续不再开新 plan，只在本文件追加 Task。

| 旧 plan | 状态 | 已落地 | 未落地（迁移到本计划） |
|---|---|---|---|
| `2026-05-17-interactive-practice-mode.md` | ✅ 完成 | v1 数据模型、9 Lab、5 交互类型、`__PRACTICE_LABS__` 注入、`localStorage` 进度 | — |
| `2026-05-17-lab-studio-practice-redesign.md` | ✅ 完成 | v2 模型、4 phases、4 tracks、8 交互、Lab Studio UI、学习档案 | 内容质量验收（每个失败反馈都指出具体学习方向）未达成 |
| `2026-05-17-practice-coach-redesign.md` | ⚠️ 结构合规 / 内容空 | `coach` 字段、`renderCoachStep` / `renderMechanismBoard` / `renderRepairFeedback` / `renderLearningRoute`、单步教练卡 | coach 5 维**60% 字段是 context/prompt/success 的复制**——脚手架在数据层是空的 |
| `2026-05-17-practice-content-first-principles-redesign.md` | ⚠️ 结构合规 / 模板未除 | `firstPrinciples`、`mentalModel`、`transferChecklist`、3 条旧模板词被禁 | 9 lab 步骤分布完全相同；新模板句（"先回到右侧术语卡"、"把题目翻成日常语言"、"已经抓住入口问题"）各出现 9 次 |

---

## 1. 现状证据快照（2026-05-18）

```
total: 9 lab × 4 phase × 92 step × 4 track
tests:        22 passed
practice.html: 257 KB（其中 inline JSON ≈ 248 KB）
app.js:       1209 lines
style.css:    1994 lines, 79 个 .practice-* 类
```

**质量诊断（需重构的根因）：**

1. **coach 字段 60% 重复**：92 step × 5 coach 字段 = 460 字段位，其中 276 次（60%）`coach.{why|act|check}` 直接 = `context | prompt | success`。
2. **9 lab 步骤分布完全相同**：`choice×2 / trace×1 / diagnose×1 / fill×1 / command×1 / code×1 / explain×1-3 / reflection×1`，9 个 lab 一个模子。
3. **跨 lab 模板句重复**：`证据会帮助你判断` / `先回到右侧术语卡` / `把题目翻成日常语言` / `已经抓住入口问题` 各出现 9 次（每 lab 一次）。
4. **第三层 hint 平均 30 字**：太短，不可能"接近答案但不直接给"。
5. **simulator 7 种 kind 但只有 2 个渲染分支**：`terminal` 渲染 `<pre>`、其余一律 chip 列表；29 个 step 没有 simulator。
6. **测试钉死字面量**：`test_practice_data_quality.py:109` `assertEqual("先用白话认出这关", ...)` 让内容只能续写模板。
7. **practice.html 248KB inline JSON**：每次内容改全站构建无缓存。
8. **`normalizeLabs` 死代码**：`app.js:237-269` 还在兼容 v1 `tasks` 数组，但 v1 数据已不存在。
9. **多层 fallback 掩盖数据缺失**：`step.coach?.why || step.context || lab.drivingQuestion` 让 coach 缺失看不见。
10. **机制画板信息过载**：右侧同屏 6 张 side-card + 2 按钮，一屏滚不完。

---

## 2. 不做的事

- ❌ **不再加新 plan**——本文件即终点。新需求作为 Task 追加。
- ❌ **不加新数据字段**——v2 schema 已经覆盖教学需要，问题是字段没填满。
- ❌ **不加新轨道 / 新 phase / 新交互类型**——8 种交互够，问题是没差异。
- ❌ **不在浏览器里跑 Bochs/Linux 0.11**——保持静态部署边界。

---

## 3. 执行路线（4 个 Phase，A 阻塞 B/C/D，B/C/D 可并行）

### Phase A — 解锁内容（去模板化）

#### Task A1: 解开测试对内容字面量的钉住

**Files:**
- Modify: `tests/test_practice_data_quality.py`

**Steps:**
1. 删除 `assertEqual("先用白话认出这关", starter_steps[0]["title"])`。
2. 改为结构断言：starter 首步 `interaction in {"choice", "diagnose"}` 且 `prompt` 包含 `lab["title"]` 的关键词（取 `lab["title"]` 中 ≥ 2 字的子串）。
3. 新增 `test_coach_fields_are_not_field_copies`：对每个 step，禁止 `coach.why == context`、`coach.act == prompt`、`coach.check == success` 这三种完全相等。允许"基于扩写"，所以条件是**字符串完全相等**，不查相似度。
4. 新增 `test_template_phrases_are_not_repeated_across_labs`：检测以下短语在 ≥ 5 个 lab 中重复出现 → fail。短语列表（动态可加）：
   - `"证据会帮助你判断"`
   - `"先回到右侧术语卡"`
   - `"把题目翻成日常语言"`
   - `"已经抓住入口问题"`
5. 跑测试，确认全部 fail（这是 TDD 里的红色）。

**Verification:**
```bash
/tmp/hust-eic-os-review-venv/bin/python -m unittest tests.test_practice_data_quality
```
Expected: ≥ 3 项 fail（A1 的目的是让模板化的内容暴露出来）。

---

#### Task A2: 把 Lab1 重写成内容标杆

**Files:**
- Modify: `content/practice-labs.json`（仅 lab1）

**Steps:**
1. 重写 lab1 的 9 个 step 的 `coach.{why, observe, act, check, repair}`，5 段话各说一件事：
   - `why`：为什么是**这一步**，不是 lab 整体的为什么
   - `observe`：先**指向**哪条具体证据（构建日志的某行 / `Image` 的 mtime / Bochs 控制台第几行）
   - `act`：当前要点击/输入/排序的**具体动作**，不复制 prompt
   - `check`：通过后用户能**重新表述**的一句话
   - `repair`：如果错了，**回到哪个概念边界**重做，不只说"再试"
2. 把第三层 hint 拉到 60-100 字，写法："如果你还在 X 和 Y 之间犹豫，注意 Z 这个差别——但答案要靠 你自己 的话表达"。
3. 重写 starter 首步标题（不再是「先用白话认出这关」），用 lab1 自己的语境，例：「为什么改了源码 Bochs 还是老样子」。
4. 删除 lab1 全部 4 句通用模板（参见 A1 步骤 4 列表）。

**Verification:**
```bash
/tmp/hust-eic-os-review-venv/bin/python -m unittest tests.test_practice_data_quality
```
Expected: lab1 相关断言全部通过；lab2-9 仍 fail（这是预期，A3 修）。

---

#### Task A3: 用 Lab1 模式横扫 Lab2-Lab9

**Files:**
- Modify: `content/practice-labs.json`（lab2-lab9）

**Steps:**
按下表为每个 lab 定一句**驱动问题**和一组**关键证据**，再按 A2 的 4 个动作改写：

| Lab | 驱动问题 | 关键证据 |
|---|---|---|
| lab2 引导 | 控制权怎样从 BIOS 一棒一棒交给内核 main？ | 启动各阶段的串口/屏幕输出 |
| lab3 系统调用 | `int 0x80` 之前的代码和之后的代码是不是同一个进程？ | `current` 进程切换前后的特权级 |
| lab4 进程轨迹 | 如何把"调度器决策"变成可读的日志？ | log 行的 pid + 状态 + 时间戳 |
| lab5 内核栈切换 | 切换前后内核栈里的什么必须一致？ | TSS / esp / eip 的保存与恢复 |
| lab6 信号量 | 为什么"信号量 = 计数器"是错的？ | 等待队列在 P/V 操作前后的变化 |
| lab7 地址映射 | 两个进程"地址相同"和"共享同一物理页"是不同问题吗？ | 页表项的物理帧号 |
| lab8 终端 | 用户写字符到屏幕和驱动转换字符是同一件事吗？ | 输入队列在按键和读取之间的状态 |
| lab9 proc | `/proc/X` 的内容是从磁盘读的吗？ | read 回调的调用栈 |

**Verification:**
```bash
/tmp/hust-eic-os-review-venv/bin/python -m unittest tests.test_practice_data_quality tests.test_practice_mode
```
Expected: 全绿。

**Strategy:** 一 lab 一个 commit，先跑 A1 的 anti-template 测试，红 → 改 → 绿 → commit。

---

### Phase B — 解锁渲染（拆 JSON、删死代码）

#### Task B1: 把 inline JSON 拆成按需加载

**Files:**
- Modify: `build.py`
- Modify: `assets/app.js`
- Modify: `content/practice.md`
- Create: `content/practice-labs/index.json`、`content/practice-labs/lab-{1..9}.json`

**Steps:**
1. 在 `build.py` 加 helper：把 `content/practice-labs.json` 拆为 `content/practice-labs/index.json`（含 `version` / `tracks` / `labs[].{id,title,focus,estimatedMinutes,concepts}`）+ 9 个 `lab-N.json`（每 lab 完整 step 数据）。
2. 构建时把拆分后的 JSON 文件复制到站点根目录（GitHub Pages 直读）。
3. `practice.html` 只内联 `index.json`（约 5 KB），不再内联 9 lab 的全部 step。
4. `app.js` 在用户点开某 lab 时 `fetch('content/practice-labs/lab-N.json')`，缓存到内存。
5. 保留 `__PRACTICE_LABS__` 全局给测试钩子，但只挂 index 数据。

**Verification:**
```bash
/tmp/hust-eic-os-review-venv/bin/python build.py
ls -la content/practice-labs/
# practice.html 从 ~257KB 应降到 < 15KB
wc -c practice.html
/tmp/hust-eic-os-review-venv/bin/python -m unittest tests/test_practice_mode.py
```

测试需相应调整：`__PRACTICE_LABS__` 只查 `version` 和 `labs[].id`，详细字段断言改为读 `content/practice-labs/lab-{N}.json`。

---

#### Task B2: 删 v1 兼容死代码 + 收敛 fallback

**Files:**
- Modify: `assets/app.js`

**Steps:**
1. 删除 `normalizeLabs` 函数体里 `if (Array.isArray(lab.phases)) return lab;` 之后的整段 v1 转换逻辑（行 240-269）。直接 `return lab`。
2. 把 `step.coach?.why || step.context || lab.drivingQuestion` 这类 3 层 fallback 收成 `step.coach.why`——配合 A 阶段 coach 必填。在开发环境 `console.warn` 缺失字段，便于发现新 step 漏写。
3. `renderCoachStep` 里 `if (!step) return empty card` 删除——starter 路径覆盖完整，不会触发；保留只会掩盖 bug。

**Verification:**
```bash
node --check assets/app.js
/tmp/hust-eic-os-review-venv/bin/python -m unittest tests/test_practice_mode.py
```

---

### Phase C — 解锁交互（让差异看得见）

#### Task C1: simulator 按 kind 真正分流渲染

**Files:**
- Modify: `assets/app.js`（`renderSimulator`）
- Modify: `assets/style.css`

**Steps:**
为 7 种 kind 分别写渲染：
- `concept-map`：节点 + 边对照框（HTML/CSS 网格，不引入 mermaid 重渲染开销）
- `state-flow`：节点 + 箭头横排
- `state-note`：键值对表
- `terminal`：保留 `<pre>`（已对）
- `code-context`：`<pre><code>` + 行号
- `failure-card`：红框 + "现象 / 根因 / 修复路径" 三栏
- 默认（未声明 kind）：不渲染（不是 fallback chip）

**Verification:**
人工浏览 lab1-9 各 phase 第一步，每种 kind 出现至少 1 次且视觉不同。

---

#### Task C2: trace 交互升级

**Files:**
- Modify: `assets/app.js`（`renderTrace` + `data-practice-trace-move` handler）
- Modify: `assets/style.css`

**Steps:**
1. 把 ↑↓ 按钮改成「点击候选项 → 添加到答案区 / 点击答案项 → 移回候选区」的两区模式。
2. 答案区内仍可拖（用 HTML5 drag 或键盘左右）。移动端用左右按钮代替拖。
3. 检查器 `validateCheck({kind: "orderedItems"})` 不变。

**Verification:**
- 桌面端键盘可完成排序（无鼠标）
- 移动 390px 视口下可完成排序
- 测试 `tests.test_practice_mode.test_practice_engine_hooks_are_present` 中的 `data-practice-trace-move` 仍存在

---

#### Task C3: 收敛右侧机制画板

**Files:**
- Modify: `assets/app.js`（`renderMechanismBoard`）
- Modify: `assets/style.css`

**Steps:**
1. 当前 step 默认只渲染 3 张卡：① 驱动问题 + 心智模型 ② 第一性原理（只显示当前 step 高亮的 1-2 维，不是全 6 维）③ 当前观察点。
2. 把术语 / 迁移清单 / 错因统计 / 学习档案按钮 折到底部 `<details>`。
3. 顶部 header 已有「学习档案」按钮，机制画板里的同名按钮删除（避免重复）。

**Verification:**
- 桌面 1280×800 下右侧画板不滚条
- 390px 视口画板移到底部，三张卡可单独折叠

---

### Phase D — 收敛样式（最后做，不阻塞功能）

#### Task D1: 抽象通用 card 块

**Files:**
- Modify: `assets/style.css`
- Modify: `assets/app.js`（class name 替换）

**Steps:**
1. 提取 `.practice-card` + `.practice-card-section` 通用块。
2. 把 `.practice-coach-{card,head,why,observe,action}` / `.practice-side-card` 全部改成 `.practice-card.is-coach` / `.practice-card.is-side` + 内部 section 用 data-attr 区分。
3. 79 个 `.practice-*` 类预期收敛到 ~30 个。

**Verification:**
- `tests.test_practice_mode.test_practice_frontend_uses_one_current_workspace_model` 列出的 6 个"必须存在"选择器（`.practice-coach-card` 等）需在测试里改成新名字。

#### Task D2: tokens

**Files:**
- Modify: `assets/style.css`

**Steps:**
1. 把 `.practice-*` 共用的 padding / border-radius / gap 抽成 `--practice-card-pad: 1rem;` 等 CSS 变量。
2. 后续新加交互类型不必加新类，只调 token。

---

## 4. 验收标准

**功能验收（保持不破）:**
- 22 个测试 + 新增 anti-template 测试全绿
- 9 lab × 4 phase × 92 step 数量不变
- localStorage 旧版进度 `os-review-practice-workbench` v3 数据可继续读
- 移动 390px 无横向溢出

**质量验收（这次要达成）:**
- coach 字段冗余度（act=prompt / check=success / why=context）从 276 次降到 < 10 次
- 跨 lab 模板句重复（≥ 5 lab 出现）从 4 句降到 0 句
- 第三层 hint 平均长度从 30 字升到 60+ 字
- `practice.html` 体积从 257KB 降到 < 15KB
- simulator 7 种 kind 视觉可分辨

**学习体验验收（这次要达成）:**
- 9 个 lab 的 starter 首步标题各不相同，且明显呼应该 lab 主题
- 任意 lab 的失败反馈（`coach.repair`）能指出**具体概念边界**，不是"再试一次"
- 任意 step 的 5 段 coach 内容互不重复，单独读每段都能成立

---

## 5. 实施顺序与节奏

```
A1 (解锁测试，0.5h)
 └─ A2 (lab1 标杆，2h)
     └─ A3 × 8 (lab2-9 横扫，每 lab ~1h，可拆 commit)

B1 (拆 JSON，1.5h) ─┐
B2 (删死代码，0.5h) ┤  并行
                   ├─→ 验证 ─→ 合入
C1 (simulator，2h) ┤
C2 (trace，1h)     ┤
C3 (右侧收敛，1h)  ┘

D1 / D2（最后做，可推迟到下次迭代）
```

**第一个 PR 范围建议：** A1 + A2 + lab1 标杆。让 A3 的 8 个 lab 各自一个 PR，便于内容审查。

**第二个 PR 范围建议：** B1 + B2，纯技术重构，不动内容。

**第三个 PR 范围建议：** C1 / C2 / C3 各一个 PR，便于回滚单点交互问题。

**D 阶段：** 在 A/B/C 都完成后再考虑，否则 class name 变动会和内容/交互改动相互冲突。

---

## 6. 需要确认的产品决策

实施前请确认：
1. **是否同意"不再开新 plan，所有新需求追加为本文件 Task"** —— 否则收敛失效。
2. **A2/A3 内容标杆是否由人工写**（建议人工，AI 续写会再生模板） vs **由 AI 写但人工校 1 lab**。
3. **B1 拆 JSON 后 GitHub Pages 是否能正确处理嵌套目录的 `Content-Type`** —— 99% 可以，本地 verify 一次即可。
