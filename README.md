# 操作系统复习系统

一套面向华中科技大学电信本科操作系统课程的静态学习系统。它把章节笔记、考前材料和 HIT-OSlab 的引导式实践组织成“理解 → 实践 → 复核”三条相互连接的路径，而不是只提供一份长目录。

> **English summary:** A static operating-systems review system that connects concept reading, guided lab practice, and exam recall in one rebuildable, evidence-oriented learning path.

[在线阅读](https://estelledc.github.io/hust-eic-os-review/) · [Jason Hub](https://estelledc.github.io/) · [About](https://estelledc.github.io/about/) · [Resume](https://estelledc.github.io/resume/)

## 公开案例

### Problem

课程材料不缺，但章节、作业、考试重点和实验通常分散在不同文件里。项目要解决的是学习路径和信息架构问题：让学习者能从机制理解推进到动手检查，再回到题型复核。

### Role

Jason 负责产品目标、信息架构、内容整合决策、前端实现与验收。AI 工具辅助代码生成、内容结构化和知识插图生产；所有对外数据均由仓库输入和自动化检查核验。

### System

- **理解**：第 1–5 章组成操作系统机制主线。
- **实践**：Lab Studio 将 Lab1–Lab9 拆为目标、行动、检查和证据步骤。
- **复核**：总复习、作业、笔试速练和默写清单支持考前回看。

### Evidence

| 可核验事实 | 仓库依据 |
|---|---|
| 5 章概念主线 | `build.py` 的章节页面配置 |
| 9 个引导式 Lab | `content/practice-labs.json` |
| 614 张在库知识插图 | `content/knowledge-illustrations.json` 与对应 WebP 文件 |
| 71 套阅读主题 | `themes/themes.json` |
| 15 个生成路由 | 13 条内容路线、首页和主题画廊 |

这些数字描述系统规模，不代表成绩提升或学习效果。

### Limitations

- 这是个人课程复习系统，不是官方教材。
- Lab Studio 是引导式推理界面，不执行真实内核编译。
- 进度只存于浏览器 `localStorage`，没有账号、云同步或学习分析。
- 内容仅供学习交流；教材与课程材料版权归原作者和权利人。

## 站点内容

- 第 1–5 章章节笔记，包含 Mermaid 结构图和经过清单管理的知识插图。
- 总复习提纲、作业明细、考前 P0 默写清单和笔试速练。
- HIT-OSlab Lab1–Lab9 的站内引导式学习版。
- 教程笔记 Part 1–3。
- 71 套可切换阅读主题。

## 本地运行

仓库包含已经生成的 HTML，使用任意静态服务器即可预览：

```sh
python3 -m http.server 8000
```

打开 `http://localhost:8000/`。不建议直接双击 HTML，因为浏览器通常会阻止 `file://` 页面读取相邻 SVG sprite。

## 重新构建与验证

```sh
python3 -m pip install -r requirements-dev.txt
python3 build.py
python3 -m unittest discover -s tests -v
python3 scripts/audit_showcase.py
git diff --exit-code -- '*.html' 'practice-labs/*.json'
```

`build.py` 以 `content/*.md` 和结构化 JSON 为输入，生成根目录 HTML 与 `practice-labs/*.json`。`audit_showcase.py` 会重新构建并检查 15 个路由、站内链接、分享元数据、JSON-LD、证据数字、Jason DS 版本和 1200×630 分享图。

需要重做分享图时运行：

```sh
python3 scripts/generate_showcase_og.py
```

## 目录

```text
.
├── index.html                 # 公开案例 + 课程地图
├── ch1.html … ch5.html        # 五章内容
├── review.html                # 总复习提纲
├── practice.html              # Lab Studio
├── cheatsheet.html            # P0 默写清单
├── quiz.html                  # 笔试速练
├── content/                   # Markdown 与结构化内容源
├── practice-labs/             # 构建后按需加载的 Lab 数据
├── assets/                    # CSS、JS、图标、Jason DS 与分享图
├── themes/                    # 主题数据与样式
├── tests/                     # 内容、交互与展示契约测试
└── build.py                   # 静态生成器
```

## 设计与技术取舍

- **静态优先**：无服务端和追踪脚本，GitHub Pages 可直接托管。
- **内容源与产物分离**：Markdown / JSON 是源，HTML 是可重复生成的展示产物。
- **阅读个性保留**：默认沿用 Editorial Monocle 的纸张与珊瑚色语言，公共组件接入 Jason DS v2。
- **渐进增强**：主题切换、目录跟随和 Lab 工作台由原生 JavaScript 提供；核心阅读链接不依赖框架。
- **本地隐私**：实践进度不上传，只写入当前浏览器。

## 许可与来源边界

站点样式和代码按仓库既有 MIT 约定使用；原始课程材料与教材版权归各自权利人。不得将课程材料内容用于商业用途。
