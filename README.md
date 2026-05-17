# 操作系统复习笔记 · 静态站点

华中科技大学电信本科操作系统课程复习笔记，按章节整理为可在线阅读的静态网页书。
内容仅供学习交流使用；版权归原始教材作者及课程材料的版权所有人所有。

## 包含内容

- 第 1–5 章 章节笔记（已做图文融合，含 mermaid 结构图）
- 总复习提纲（按章节列考点）
- 作业明细（题号 + 教材原题完整文字）
- 实践模式（基于 HIT-OSlab 题目路线的 Lab1–Lab9 站内交互式学习版）
- 教程笔记 Part 1–3（教材重点章节抄读）

## 在线阅读

部署在 GitHub Pages（仓库 Settings → Pages → 选择 `main` 分支）。

## 本地阅读

仓库内已有生成好的 `*.html`，任意静态服务器即可：

```sh
# 任选一种
python3 -m http.server 8000
# 或
npx --yes http-server -p 8000 .
```

然后浏览器打开 `http://localhost:8000/`。

> 直接双击 `index.html` 也能打开，但浏览器默认不允许 `file://` 协议加载相邻 SVG `<use>`，
> 部分图标显示会缺失；推荐用本地服务器。

## 重新生成 HTML

修改 `content/*.md` 后跑：

```sh
python3 -m pip install --user markdown
python3 build.py
```

`build.py` 把 `content/` 下的 markdown 渲染成相邻的 `*.html`。它幂等，可重复运行。

### 目录约定

```
.
├── index.html              # 课程地图
├── ch1.html ... ch5.html   # 五章
├── review.html             # 总复习提纲
├── homework.html           # 作业明细
├── practice.html           # 实践模式
├── tutorial-1..3.html      # 教程三部分
├── content/
│   ├── *.md                # markdown 源
│   └── images/             # 引用到的关键图（其余装饰图已清理）
├── assets/
│   ├── style.css
│   ├── app.js
│   └── icons.svg
└── build.py                # 生成器
```

## 设计取舍

- **行宽 ~72ch**：对长段中文阅读友好。
- **mermaid 客户端渲染**：跟随主题色自动切深浅。
- **实践模式本地进度**：只用 `localStorage` 保存交互任务答案、检查结果和报告草稿状态，不上传数据。
- **轻动画**：仅 150–300ms 过渡 / 折叠 / 滚动跟随，不干扰阅读。
- **无构建步骤**：不依赖 Node 工具链；Python + 标准 markdown 库即可。
- **无第三方追踪脚本**：仅 mermaid 来自 jsDelivr CDN。

## 许可

笔记整理风格与代码 MIT；原始课程材料与教材版权归各自著作权人。
不得将本仓库内容用于商业用途。
