"""Generate the static site from content/*.md.

Run:  python3 build.py

Inputs:
    content/*.md          — chapter notes, review, homework, tutorial parts
    content/images/*      — referenced figures (chapter-prefixed names)
    assets/*              — shared CSS / JS / SVG sprite

Outputs:
    *.html (one per page) at the repo root, plus index.html (course map).
    Re-run safely; idempotent.
"""
from __future__ import annotations

import html as html_mod
import json
import re
import shutil
from pathlib import Path
from typing import Callable, Iterable

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
ASSETS_REL = "assets"
IMAGES_REL = "content/images"
KNOWLEDGE_MANIFEST_REL = "content/knowledge-illustrations.json"

# slug, source md (str or tuple of merged parts), display title, group, intro
PAGES = [
    ("ch1", "ch1.md", "第 1 章 操作系统概论", "chapter",
     "并发 / 共享 / 虚拟 / 异步四大特性，分时与多道架构。"),
    ("ch2", "ch2.md", "第 2 章 处理器管理", "chapter",
     "进程与线程、状态转换、七种调度算法与计算模板。"),
    ("ch3", ("ch3-part1.md", "ch3-part2.md"), "第 3 章 同步互斥与死锁", "chapter",
     "PV 三铁律、生产者-消费者、读者写者、哲学家与银行家算法。"),
    ("ch4", "ch4.md", "第 4 章 存储管理", "chapter",
     "地址转换、四种页面置换、工作集与虚拟内存。"),
    ("ch5", "ch5.md", "第 5 章 设备管理", "chapter",
     "六种磁盘调度算法、SPOOLing、I/O 软件分层。"),
    ("review", "review.md", "总复习提纲", "exam",
     "20 页考前总图，按章节列考点。"),
    ("homework", "homework.md", "作业明细", "exam",
     "5 章作业题号 + 教材原题完整文字。"),
    ("practice", "practice.md", "实践模式", "practice",
     "HIT-OSlab Lab1-Lab9 的站内交互式学习版。"),
    ("cheatsheet", "cheatsheet.md", "考前 P0 必默写清单", "exam",
     "10 道大题完整推演 + D-3/D-2/D-1 默写计划。"),
    ("quiz", "quiz.md", "笔试速练", "exam",
     "30+ 题分类练习，含答案+易错点。"),
    ("tutorial-1", "tutorial-1.md", "教程笔记 · Part 1", "tutorial",
     "OS 概述 · 处理器管理 · 存储管理（前段）。"),
    ("tutorial-2", "tutorial-2.md", "教程笔记 · Part 2", "tutorial",
     "存储 · 设备 · 文件系统 · 并发（前段）。"),
    ("tutorial-3", "tutorial-3.md", "教程笔记 · Part 3", "tutorial",
     "死锁 · 网络 / 分布式 / 云。"),
]

GROUPS = [
    ("chapter",  "课程章节",     "📖"),
    ("exam",     "考前材料",     "📝"),
    ("practice", "实践模式",     "🧪"),
    ("tutorial", "教程笔记",     "📚"),
]

# --------- text scrubbing ---------

# Replace prior school references with the current school name.
SCRUB_PATTERNS: list[tuple[str, str]] = [
    (r"北邮电信本科生", "华中科技大学电信本科生"),
    (r"北邮《操作系统》", "课程《操作系统》"),
    (r"北邮 OS 教材", "课程 OS 教材"),
    (r"北邮", "华中科技大学"),
]

FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
LEADING_H1_RE = re.compile(r"\A\s*#[^\n]*\n+", re.MULTILINE)
KNOWLEDGE_HEADING_RE = re.compile(r"^(#{2,4})\s+(.+?)\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")

def scrub(text: str) -> str:
    text = FRONTMATTER_RE.sub("", text, count=1)
    # Drop the leading H1 — the page header already shows the chapter title.
    text = LEADING_H1_RE.sub("", text, count=1)
    for pat, rep in SCRUB_PATTERNS:
        text = re.sub(pat, rep, text)
    return text

def load_knowledge_entries() -> dict[tuple[str, int], dict]:
    path = ROOT / KNOWLEDGE_MANIFEST_REL
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    entries: dict[tuple[str, int], dict] = {}
    for entry in data.get("entries", []):
        source = str(entry.get("source", ""))
        ordinal = int(entry.get("ordinal", 0))
        if source and ordinal:
            entries[(source, ordinal)] = entry
    return entries

def knowledge_figure_html(entry: dict) -> str:
    image = html_mod.escape(str(entry.get("image", "")), quote=True)
    alt = html_mod.escape(str(entry.get("alt", "")), quote=True)
    title = html_mod.escape(str(entry.get("title", "")))
    point_id = html_mod.escape(str(entry.get("id", "")), quote=True)
    return (
        f'<figure class="knowledge-figure" data-knowledge-id="{point_id}">\n'
        f'  <img src="{image}" alt="{alt}" loading="lazy">\n'
        f'  <figcaption>插图：{title}</figcaption>\n'
        f'</figure>'
    )

def inject_knowledge_illustrations(
    md_text: str,
    source_name: str,
    entries: dict[tuple[str, int], dict] | None = None,
    image_exists: Callable[[str], bool] | None = None,
) -> str:
    entries = entries if entries is not None else load_knowledge_entries()
    if not entries:
        return md_text
    image_exists = image_exists or (lambda image: (ROOT / image).exists())
    source_rel = source_name if source_name.startswith("content/") else f"content/{source_name}"
    ordinal = 0
    in_fence = False
    output: list[str] = []
    for line in md_text.splitlines():
        output.append(line)
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not KNOWLEDGE_HEADING_RE.match(line):
            continue
        ordinal += 1
        entry = entries.get((source_rel, ordinal))
        if not entry:
            continue
        image = str(entry.get("image", ""))
        if image and image_exists(image):
            output.append("")
            output.append(knowledge_figure_html(entry))
    trailing_newline = "\n" if md_text.endswith("\n") else ""
    return "\n".join(output) + trailing_newline

def load_source(name) -> str:
    if isinstance(name, tuple):
        chunks = []
        for n in name:
            text = scrub((CONTENT / n).read_text(encoding="utf-8"))
            chunks.append(inject_knowledge_illustrations(text, n))
        # Keep two newlines between merged parts so heading structure stays intact.
        return "\n\n".join(chunks)
    text = scrub((CONTENT / name).read_text(encoding="utf-8"))
    return inject_knowledge_illustrations(text, name)

# --------- mermaid post-process ---------

MERMAID_BLOCK_RE = re.compile(
    r'<pre><code class="language-mermaid">(.*?)</code></pre>',
    re.DOTALL,
)

def fix_mermaid(html: str) -> str:
    def _sub(m: re.Match) -> str:
        body = m.group(1)
        body = html_mod.unescape(body)
        return f'<pre class="mermaid">{body}</pre>'
    return MERMAID_BLOCK_RE.sub(_sub, html)

# --------- image path rewrite ---------

# Inside merged content/*.md, image refs still say "images/<name>".
# Resolve them to "content/images/<chapter>-<name>" using a small mapping;
# unmapped names stay as "content/images/<name>" (so future additions work).
IMAGE_REWRITES: dict[str, str] = {
    "images/slide-123-img-1.jpg":      "content/images/ch1-cpu-utilization.jpg",
    "images/img-133-099.png":           "content/images/ch3-deadlock-spacetime.png",
    "images/img-166-479.png":           "content/images/ch3-bankers-matrix.png",
}

IMG_HTML_RE = re.compile(r'<img([^>]*?)src="(images/[^"]+)"([^>]*)>')

def fix_images(html: str) -> str:
    def _sub(m: re.Match) -> str:
        before, src, after = m.group(1), m.group(2), m.group(3)
        new_src = IMAGE_REWRITES.get(src, f"content/{src}")
        # add lazy loading + clean alt fallback
        if "loading=" not in (before + after):
            after += ' loading="lazy"'
        return f'<img{before}src="{new_src}"{after}>'
    return IMG_HTML_RE.sub(_sub, html)

# --------- rendering ---------

def render(md_text: str) -> tuple[str, str]:
    import markdown
    from markdown.extensions.toc import TocExtension

    md_extensions = [
        "extra",        # tables, fenced_code, attr_list, footnotes, abbr, def_list
        "md_in_html",   # 让 <details markdown="1"> 内部的 markdown 被渲染
        "sane_lists",
        "smarty",
        TocExtension(toc_depth="2-3", anchorlink=True, permalink=False),
    ]
    md = markdown.Markdown(extensions=md_extensions, output_format="html5")
    html = md.convert(md_text)
    html = fix_mermaid(html)
    html = fix_images(html)
    toc = getattr(md, "toc", "")
    return html, toc

# --------- templates ---------

SITE_TITLE = "操作系统复习系统"
SITE_URL = "https://estelledc.github.io/hust-eic-os-review/"
REPO_URL = "https://github.com/estelledc/hust-eic-os-review"
HUB_URL = "https://estelledc.github.io/"
ABOUT_URL = "https://estelledc.github.io/about/"
RESUME_URL = "https://estelledc.github.io/resume/"
OG_IMAGE_URL = f"{SITE_URL}assets/og-os-review.png"


def public_url(slug: str) -> str:
    return SITE_URL if slug == "__home__" else f"{SITE_URL}{slug}.html"


def structured_data(page_title: str, page_desc: str, slug: str) -> str:
    page_url = public_url(slug)
    graph = [
        {
            "@type": "WebSite",
            "@id": f"{SITE_URL}#website",
            "url": SITE_URL,
            "name": SITE_TITLE,
            "description": "面向操作系统课程复习的静态学习系统：概念阅读、考前材料与 Lab Studio。",
            "inLanguage": ["zh-Hans", "en"],
            "author": {"@id": f"{HUB_URL}#jason"},
        },
        {
            "@type": "Person",
            "@id": f"{HUB_URL}#jason",
            "name": "Jason",
            "url": HUB_URL,
            "sameAs": ["https://github.com/estelledc"],
        },
        {
            "@type": "LearningResource" if slug != "__home__" else "CreativeWork",
            "@id": f"{page_url}#resource",
            "url": page_url,
            "name": page_title,
            "description": page_desc,
            "inLanguage": "zh-Hans",
            "isPartOf": {"@id": f"{SITE_URL}#website"},
            "author": {"@id": f"{HUB_URL}#jason"},
        },
    ]
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)


def head_html(page_title: str, page_desc: str, slug: str) -> str:
    desc = html_mod.escape(page_desc)
    page_url = html_mod.escape(public_url(slug), quote=True)
    full_title = SITE_TITLE if page_title == SITE_TITLE else f"{page_title} — {SITE_TITLE}"
    share_title = html_mod.escape(full_title, quote=True)
    json_ld = structured_data(page_title, page_desc, slug).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="zh-Hans">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{desc}">
<meta name="author" content="Jason">
<meta name="color-scheme" content="light dark">
<title>{html_mod.escape(full_title)}</title>
<link rel="canonical" href="{page_url}">
<meta property="og:type" content="website">
<meta property="og:locale" content="zh_CN">
<meta property="og:site_name" content="{SITE_TITLE}">
<meta property="og:title" content="{share_title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{page_url}">
<meta property="og:image" content="{OG_IMAGE_URL}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="操作系统复习系统：阅读、实践、复核三条学习路径">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{share_title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{OG_IMAGE_URL}">
<link rel="stylesheet" href="{ASSETS_REL}/jx/tokens.css">
<link rel="stylesheet" href="{ASSETS_REL}/jx/base.css">
<link rel="stylesheet" href="{ASSETS_REL}/jx/components.css">
<link rel="stylesheet" href="{ASSETS_REL}/style.css">
<link rel="stylesheet" href="themes/themes.css">
<link rel="icon" type="image/svg+xml" href="{ASSETS_REL}/favicon.svg">
<script type="application/ld+json">{json_ld}</script>
<script>(function(){{try{{var t=localStorage.getItem("os-review-theme");if(t)document.documentElement.setAttribute("data-theme",t);}}catch(e){{}}}})();</script>
</head>
<body>
<a class="jx-skip-link" href="#main">跳到主要内容</a>
"""

def topbar_html(active_slug: str) -> str:
    def is_active(kind: str) -> bool:
        if kind == "home":
            return active_slug == "__home__"
        if kind == "read":
            return any(slug == active_slug and group == "chapter" for slug, _, _, group, _ in PAGES)
        if kind == "practice":
            return active_slug == "practice"
        if kind == "review":
            return active_slug == "review"
        if kind == "homework":
            return active_slug == "homework"
        if kind == "tutorial":
            return any(slug == active_slug and group == "tutorial" for slug, _, _, group, _ in PAGES)
        if kind == "themes":
            return active_slug == "__gallery__"
        return False

    links = [
        ("home", "课程地图", "index.html"),
        ("read", "阅读", "ch1.html"),
        ("practice", "实践", "practice.html"),
        ("review", "总复习", "review.html"),
        ("homework", "作业", "homework.html"),
        ("tutorial", "教程", "tutorial-1.html"),
        ("themes", "主题", "themes-gallery.html"),
    ]
    nav_items = []
    for kind, label, href in links:
        active = is_active(kind)
        current = ' aria-current="page"' if active else ""
        nav_items.append(
            f'<a class="site-nav-link{" is-active" if active else ""}" href="{href}"{current}>{label}</a>'
        )
    nav_html = "\n      ".join(nav_items)
    return f"""<header class="topbar site-topbar" role="banner">
  <div class="topbar-inner">
    <a class="brand" href="index.html" aria-label="返回首页">
      <svg class="brand-icon" viewBox="0 0 24 24" aria-hidden="true"><use href="{ASSETS_REL}/icons.svg#book"/></svg>
      <span><strong>OS Review</strong><small>HUST EIC · 学习系统</small></span>
    </a>
    <button class="site-nav-toggle" type="button" aria-expanded="false" aria-controls="site-nav" data-site-nav-toggle>导航</button>
    <nav class="site-nav" id="site-nav" aria-label="站点主导航">
      {nav_html}
      <span class="site-nav-global" role="group" aria-label="Jason 作品集导航">
        <a class="site-nav-link" href="{HUB_URL}">Hub</a>
        <a class="site-nav-link" href="{ABOUT_URL}">About</a>
        <a class="site-nav-link" href="{RESUME_URL}">Resume</a>
        <a class="site-nav-link" href="{REPO_URL}">GitHub</a>
      </span>
    </nav>
    <div class="topbar-actions">
      <nav class="portfolio-links" aria-label="Jason 作品集导航">
        <a class="jx-return-to-hub" href="{HUB_URL}" rel="home">Hub</a>
        <a href="{ABOUT_URL}">About</a>
        <a href="{RESUME_URL}">Resume</a>
      </nav>
      <button class="theme-toggle" type="button" aria-label="切换深浅色" data-theme-toggle title="切换深浅色">
        <svg class="i" viewBox="0 0 24 24" aria-hidden="true"><use href="{ASSETS_REL}/icons.svg#sun"/></svg>
      </button>
      <button class="theme-toggle theme-picker-btn" type="button" aria-label="选择主题" data-theme-picker title="选择主题（71 套）">
        <svg class="i" viewBox="0 0 24 24" aria-hidden="true"><use href="{ASSETS_REL}/icons.svg#palette"/></svg>
      </button>
      <a class="theme-toggle" href="{REPO_URL}" target="_blank" rel="noopener" aria-label="在 GitHub 查看源码" title="在 GitHub 查看源码">
        <svg class="i" viewBox="0 0 24 24" aria-hidden="true"><use href="{ASSETS_REL}/icons.svg#github"/></svg>
      </a>
    </div>
  </div>
</header>
"""

def sidebar_html(active_slug: str) -> str:
    sections = []
    for grp_id, grp_label, _grp_icon in GROUPS:
        items = []
        for slug, src, title, group, intro in PAGES:
            if group != grp_id:
                continue
            cls = "nav-link" + (" nav-link-active" if slug == active_slug else "")
            items.append(
                f'<li><a class="{cls}" href="{slug}.html">'
                f'<span class="nav-link-title">{html_mod.escape(title)}</span>'
                f'<span class="nav-link-desc">{html_mod.escape(intro)}</span>'
                f"</a></li>"
            )
        sections.append(
            f'<section class="nav-group" aria-labelledby="grp-{grp_id}">'
            f'<p id="grp-{grp_id}" class="nav-group-title">{html_mod.escape(grp_label)}</p>'
            f'<ul class="nav-list">{"".join(items)}</ul>'
            f"</section>"
        )
    return f"""<aside class="sidebar" aria-label="站点导航">
  <a class="home-link" href="index.html">
    <svg class="i" viewBox="0 0 24 24" aria-hidden="true"><use href="{ASSETS_REL}/icons.svg#home"/></svg>
    <span>课程地图</span>
  </a>
  {''.join(sections)}
  <div class="sidebar-footer">
    <a class="ghost" href="themes-gallery.html">
      <svg class="i" viewBox="0 0 24 24" aria-hidden="true"><use href="{ASSETS_REL}/icons.svg#palette"/></svg>
      <span>主题画廊（71 套）</span>
    </a>
    <p class="ghost sidebar-note">本站源代码以 markdown 编写、build.py 重新生成。</p>
  </div>
</aside>
"""

FOOTER_HTML = f"""<footer class="jx-footer">
  <div class="jx-footer__colophon">
    <strong>OS Review</strong>
    <span lang="en">A Jason product system · MMXXVI</span>
  </div>
  <nav class="jx-footer__index">
    <a href="index.html">course map</a>
    <a href="review.html">复习提纲</a>
    <a href="practice.html">lab studio</a>
    <a href="{HUB_URL}">hub</a>
    <a href="{ABOUT_URL}">about</a>
    <a href="{RESUME_URL}">resume</a>
    <a href="{REPO_URL}">github</a>
  </nav>
  <time class="jx-footer__stamp" datetime="2026-07-11" lang="en">Updated 2026·07·11</time>
</footer>
"""

PICKER_HTML = f"""<aside class="theme-picker" data-theme-panel hidden aria-label="主题选择器">
  <div class="theme-picker-head">
    <h3 class="theme-picker-title">选择主题</h3>
    <p class="theme-picker-sub">71 套来自 <a href="https://github.com/VoltAgent/awesome-design-md" target="_blank" rel="noopener">awesome-design-md</a> 的设计系统</p>
    <button class="theme-picker-close" type="button" aria-label="关闭" data-theme-panel-close>×</button>
  </div>
  <div class="theme-picker-actions">
    <button type="button" class="btn btn-mini" data-theme-set="">默认（跟随系统）</button>
    <a class="btn btn-mini" href="themes-gallery.html">画廊页 →</a>
  </div>
  <div class="theme-picker-grid" data-theme-grid></div>
</aside>
<div class="theme-picker-backdrop" data-theme-panel-backdrop hidden></div>
"""

def themes_inline_script() -> str:
    p = ROOT / "themes" / "themes.json"
    if not p.exists():
        return '<script>window.__THEMES__=[];</script>'
    obj = json.loads(p.read_text(encoding="utf-8"))
    arr = obj.get("themes", [])
    return f'<script id="themes-data">window.__THEMES__={json.dumps(arr, ensure_ascii=False)};</script>'

PRACTICE_LABS_OUT_DIR = ROOT / "practice-labs"

# 索引时保留的 lab 元数据字段（不含 phases / beginner / firstPrinciples 等大字段）
PRACTICE_INDEX_LAB_FIELDS = (
    "id",
    "title",
    "focus",
    "estimatedMinutes",
    "difficulty",
    "concepts",
    "sourceRoute",
    "outcomes",
    "drivingQuestion",
    "plainLanguageGoal",
)

def emit_practice_lab_files() -> dict:
    """把 content/practice-labs.json 拆为根目录 practice-labs/{index,lab-N}.json。

    返回 index 对象，供 inline 注入。
    """
    src = CONTENT / "practice-labs.json"
    if not src.exists():
        return {"version": 2, "tracks": [], "labs": []}
    data = json.loads(src.read_text(encoding="utf-8"))
    PRACTICE_LABS_OUT_DIR.mkdir(parents=True, exist_ok=True)
    # 写每 lab 全量 json
    for lab in data.get("labs", []):
        lab_path = PRACTICE_LABS_OUT_DIR / f"{lab['id']}.json"
        lab_path.write_text(
            json.dumps(lab, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    # 索引：tracks + 每 lab 的轻量元数据（不含 phases / beginner / firstPrinciples）
    index_labs = []
    for lab in data.get("labs", []):
        meta = {k: lab[k] for k in PRACTICE_INDEX_LAB_FIELDS if k in lab}
        # 给前端一个能算 phase 数量的快照
        meta["phaseIds"] = [phase["id"] for phase in lab.get("phases", [])]
        index_labs.append(meta)
    index_obj = {
        "version": data.get("version", 2),
        "tracks": data.get("tracks", []),
        "labs": index_labs,
    }
    (PRACTICE_LABS_OUT_DIR / "index.json").write_text(
        json.dumps(index_obj, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return index_obj

def practice_inline_script() -> str:
    """页面内联仅 index——完整 lab 数据在 practice-labs/lab-N.json 按需 fetch。"""
    index_obj = emit_practice_lab_files()
    return (
        '<script id="practice-data">'
        f'window.__PRACTICE_LABS__={json.dumps(index_obj, ensure_ascii=False)};'
        '</script>'
    )

SCRIPTS_HTML = f"""
{themes_inline_script()}
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js" defer></script>
<script src="{ASSETS_REL}/app.js" defer></script>
"""

def page_html(slug: str, title: str, intro: str, body: str, toc: str) -> str:
    title_esc = html_mod.escape(title)
    intro_esc = html_mod.escape(intro)
    has_toc_links = bool(toc and "<a " in toc)
    layout_class = "layout layout-practice layout-practice-focused" if slug == "practice" else "layout"
    prose_class = "prose prose-practice" if slug == "practice" else "prose"
    sidebar_block = "" if slug == "practice" else sidebar_html(slug)
    toc_block = (
        f'<aside class="page-toc" aria-label="本页目录"><h3 class="page-toc-title">本页目录</h3>{toc}</aside>'
        if has_toc_links else ""
    )
    return (
        head_html(title, intro, slug)
        + topbar_html(slug)
        + f'<div class="{layout_class}">\n'
        + sidebar_block
        + '<main class="main" id="main">\n'
        + f'  <article class="{prose_class}">\n'
        + f'    <header class="page-head">\n'
        + f'      <h1>{title_esc}</h1>\n'
        + (f'      <p class="page-lede">{intro_esc}</p>\n' if intro else "")
        + f'    </header>\n'
        + f'    {body}\n'
        + f'  </article>\n'
        + '</main>\n'
        + toc_block
        + '</div>\n'
        + '<a class="back-to-top" href="#main" aria-label="返回顶部">'
        + f'<svg class="i" viewBox="0 0 24 24" aria-hidden="true"><use href="{ASSETS_REL}/icons.svg#up"/></svg></a>\n'
        + FOOTER_HTML
        + PICKER_HTML
        + (practice_inline_script() if slug == "practice" else "")
        + SCRIPTS_HTML
        + "</body></html>\n"
    )

# --------- index page ---------

INDEX_TEMPLATE = """<main class="main main-home" id="main">
  <article class="home home-dashboard">
    <header class="showcase-hero" aria-labelledby="showcase-title">
      <div class="showcase-hero__copy">
        <div class="showcase-hero__meta">
          <span class="jx-chip" data-state="maintained">Maintained</span>
          <span class="jx-eyebrow"><span class="jx-eyebrow__rule"></span>Public learning system</span>
        </div>
        <p class="kicker">华中科技大学 · 电信本科 · 操作系统</p>
        <h1 class="hero-title" id="showcase-title">把散落的课程材料，组织成一套能走、能练、能复核的学习系统</h1>
        <p class="hero-lede">我把章节笔记、考前材料与 9 个 Lab 的引导式实践统一到三条清晰路径里，让学习者先建立机制地图，再动手验证，最后回到题型复核。</p>
        <p class="showcase-hero__en" lang="en">A static operating-systems review system that turns fragmented notes, exam material, and guided labs into one evidence-oriented learning path.</p>
        <div class="hero-actions">
          <a class="btn btn-primary" href="#system">查看系统设计</a>
          <a class="btn btn-secondary" href="practice.html">进入 Lab Studio</a>
          <a class="btn btn-ghost" href="https://github.com/estelledc/hust-eic-os-review">查看源码 ↗</a>
        </div>
      </div>
      <div class="os-stack" role="img" aria-label="学习系统的三层结构：概念、实践、复核">
        <div class="os-stack__label"><span>OS REVIEW / SYSTEM MAP</span><span>03 PATHS</span></div>
        <ol>
          <li><span>01</span><strong>概念阅读</strong><small>5 章机制主线</small></li>
          <li><span>02</span><strong>引导实践</strong><small>Lab1—Lab9</small></li>
          <li><span>03</span><strong>考前复核</strong><small>提纲 · 题型 · 默写</small></li>
        </ol>
      </div>
    </header>

    <section class="jx-proof showcase-proof" aria-labelledby="problem-title">
      <div>
        <p class="jx-case-section__heading">Problem / 问题</p>
        <h2 id="problem-title">课程内容不缺，缺的是一条能持续推进的路径</h2>
        <p class="jx-proof__summary">章节、作业、考试重点和实验往往分散在不同材料里。这个项目的核心不是再堆一份笔记，而是把“理解—练习—复核”做成同一个可导航、可重建的静态系统。</p>
        <p class="jx-proof__summary-en" lang="en">The product problem was information architecture: connect reading, guided practice, and exam recall without claiming to replace the course or a real OS lab.</p>
        <div class="jx-proof__metrics" aria-label="可核验项目数据">
          <div class="jx-proof__metric"><strong>5</strong><span>章概念主线</span></div>
          <div class="jx-proof__metric"><strong>9</strong><span>个引导式 Lab</span></div>
          <div class="jx-proof__metric"><strong>614</strong><span>张在库知识插图</span></div>
        </div>
      </div>
      <dl class="jx-proof__meta">
        <div><dt>Role / 角色</dt><dd>产品定义、信息架构、内容整合、前端实现与验收</dd></div>
        <div><dt>Audience / 用户</dt><dd>正在建立操作系统知识框架的课程学习者</dd></div>
        <div><dt>Stack / 实现</dt><dd>Python 静态生成器 · Markdown · Vanilla JS · CSS</dd></div>
        <div><dt>Boundary / 协作</dt><dd>Jason 决定目标、结构与验收；AI 工具辅助代码、内容结构化和插图生产</dd></div>
      </dl>
    </section>

    <section class="jx-case-section showcase-system" id="system" aria-labelledby="system-title">
      <div class="jx-case-section__grid">
        <h2 class="jx-case-section__heading" id="system-title">System / 系统</h2>
        <div class="jx-case-section__body system-paths">
          <a href="ch1.html"><span>01 · Understand</span><strong>沿 5 章机制主线建立概念地图</strong><small>概论 → 处理器 → 同步与死锁 → 存储 → 设备</small></a>
          <a href="practice.html"><span>02 · Practice</span><strong>用分阶段提示推进 Lab1—Lab9</strong><small>目标、行动、检查和证据留在同一个工作台</small></a>
          <a href="review.html"><span>03 · Recall</span><strong>用提纲、速练与默写清单复核</strong><small>从长内容切换到高频考点与可回看的题型</small></a>
        </div>
      </div>
    </section>

    <section class="jx-case-section" aria-labelledby="evidence-title">
      <div class="jx-case-section__grid">
        <h2 class="jx-case-section__heading" id="evidence-title">Evidence / 证据</h2>
        <div class="jx-case-section__body">
          <p>所有数字都来自仓库内可重复运行的构建输入，不把“内容数量”包装成学习效果。</p>
          <ul class="jx-evidence-list">
            <li><a href="index.html#course-map"><span class="evidence-copy"><strong>13 条内容路线</strong><small>5 章、复习材料、实践与三段教程</small></span></a></li>
            <li><a href="practice.html"><span class="evidence-copy"><strong>9 个 Lab 数据包</strong><small>由构建脚本拆分并按需加载</small></span></a></li>
            <li><a href="themes-gallery.html"><span class="evidence-copy"><strong>71 套可切换主题</strong><small>保留课程站的个性化阅读体验</small></span></a></li>
            <li><a href="https://github.com/estelledc/hust-eic-os-review"><span class="evidence-copy"><strong>可重建与可测试</strong><small>Markdown 源内容、Python 生成器与自动化检查</small></span></a></li>
          </ul>
        </div>
      </div>
    </section>

    <section class="jx-case-section" aria-labelledby="limitations-title">
      <div class="jx-case-section__grid">
        <h2 class="jx-case-section__heading" id="limitations-title">Limitations / 边界</h2>
        <div class="jx-case-section__body jx-case-limit">
          <p><strong>这是一套个人课程复习系统，不是官方教材或真实实验环境。</strong>Lab Studio 提供引导式推理和本地进度记录，不执行内核编译；站点不含账号、云同步或学习分析，也不声称提高成绩。教材与课程材料版权归原作者和权利人。</p>
        </div>
      </div>
    </section>

    <section class="map learning-section" id="course-map">
      <header class="section-head">
        <p class="kicker">Course map / 阅读模式</p>
        <h2>从这里进入学习系统</h2>
        <p>按操作系统的主线推进：概论、处理器、同步互斥、存储、设备。</p>
      </header>
      <ol class="cards">
        {chapter_cards}
      </ol>
    </section>

    <section class="map learning-section">
      <header class="section-head">
        <p class="kicker">考前材料</p>
        <h2>复习与作业</h2>
        <p>把高频考点、老师布置的题号和完整题面放在一起查。</p>
      </header>
      <ol class="cards cards-2">
        {exam_cards}
      </ol>
    </section>

    <section class="map learning-section">
      <header class="section-head">
        <p class="kicker">实践模式</p>
        <h2>站内 Lab Studio</h2>
        <p>用一步一检查的方式理解 HIT-OSlab 题目，不依赖真实编译环境。</p>
      </header>
      <ol class="cards cards-2">
        {practice_cards}
      </ol>
    </section>

    <section class="map learning-section">
      <header class="section-head">
        <p class="kicker">教程笔记</p>
        <h2>教材补充路径</h2>
        <p>当课程笔记不够细时，用三段教程笔记补定义、例题和原书脉络。</p>
      </header>
      <ol class="cards cards-2">
        {tutorial_cards}
      </ol>
    </section>

    <section class="tips surface">
      <header class="section-head">
        <p class="kicker">学习策略</p>
        <h2>怎么用这套笔记</h2>
      </header>
      <ul class="bullets">
        <li><strong>第一遍系统过</strong>：按 ch1 → ch5 顺序，每章先读章末小结，再回头补细节。</li>
        <li><strong>动手补强</strong>：进入「实践模式」，按 Lab1 → Lab9 的检查点逐步推进。</li>
        <li><strong>考前冲刺</strong>：直接读「总复习提纲」，再用「作业明细」对照真题题型。</li>
        <li><strong>遇到不熟的概念</strong>：右栏目录可定位到具体小节；mermaid 图鼠标悬停可放大。</li>
        <li><strong>移动端</strong>：顶部「导航」按钮会展开同一套站点入口。</li>
      </ul>
    </section>
  </article>
</main>
"""

def card_html(slug: str, title: str, intro: str, badge: str = "") -> str:
    badge_html = f'<span class="card-badge">{html_mod.escape(badge)}</span>' if badge else ""
    return (
        f'<li class="card"><a class="card-link" href="{slug}.html">'
        f'  <div class="card-top">{badge_html}<svg class="card-arrow" viewBox="0 0 24 24" aria-hidden="true"><use href="{ASSETS_REL}/icons.svg#arrow"/></svg></div>'
        f'  <h3 class="card-title">{html_mod.escape(title)}</h3>'
        f'  <p class="card-desc">{html_mod.escape(intro)}</p>'
        f'</a></li>'
    )

def index_page() -> str:
    chapter_cards = "\n        ".join(
        card_html(slug, title, intro, badge=f"CH {i+1}")
        for i, (slug, _, title, group, intro) in enumerate(p for p in PAGES if p[3] == "chapter")
    )
    exam_cards = "\n        ".join(
        card_html(slug, title, intro)
        for (slug, _, title, group, intro) in PAGES if group == "exam"
    )
    practice_cards = "\n        ".join(
        card_html(slug, title, intro)
        for (slug, _, title, group, intro) in PAGES if group == "practice"
    )
    tutorial_cards = "\n        ".join(
        card_html(slug, title, intro, badge=f"P{i+1}")
        for i, (slug, _, title, group, intro) in enumerate(p for p in PAGES if p[3] == "tutorial")
    )
    body = INDEX_TEMPLATE.format(
        chapter_cards=chapter_cards,
        exam_cards=exam_cards,
        practice_cards=practice_cards,
        tutorial_cards=tutorial_cards,
    )
    return (
        head_html(
            "操作系统复习系统",
            "把 5 章概念、考前材料与 9 个引导式 Lab 组织成能走、能练、能复核的静态学习系统。",
            "__home__",
        )
        + topbar_html("__home__")
        + '<div class="layout layout-home">\n'
        + sidebar_html("__home__")
        + body
        + '</div>\n'
        + FOOTER_HTML
        + PICKER_HTML
        + SCRIPTS_HTML
        + "</body></html>\n"
    )

# --------- main ---------

def gallery_page() -> str:
    import json as _json
    p = ROOT / "themes" / "themes.json"
    themes = _json.loads(p.read_text(encoding="utf-8")).get("themes", []) if p.exists() else []

    cards = []
    for t in themes:
        sw = "".join(f'<span style="background:{c}"></span>' for c in (t.get("swatch") or [])[:4])
        mode = "DARK" if t.get("is_dark") else "LIGHT"
        slug = html_mod.escape(t.get("slug", ""))
        name = html_mod.escape(t.get("name", slug))
        desc = html_mod.escape(t.get("description", ""))
        cards.append(
            f'<article class="gallery-card" data-theme-card="{slug}" data-mode="{mode.lower()}">'
            f'<div class="swatch-row">{sw}</div>'
            f'<div class="gallery-card-body">'
            f'<div class="gallery-card-head">'
            f'<span class="gallery-card-name">{name}</span>'
            f'<span class="gallery-card-mode">{mode}</span>'
            f'</div>'
            f'<p class="gallery-card-desc">{desc}</p>'
            f'<div class="gallery-card-actions">'
            f'<button class="btn btn-mini btn-primary" type="button" data-theme-set="{slug}" data-gallery-apply>应用主题</button>'
            f'<a class="btn btn-mini btn-secondary" href="ch1.html" data-preview-link="{slug}">在 ch1 中预览</a>'
            f'</div></div></article>'
        )
    body = (
        f'<main class="main main-home" id="main">'
        f'<article class="home gallery-page">'
        f'<header class="hero home-hero surface">'
        f'<p class="kicker">主题画廊</p>'
        f'<h1 class="hero-title">71 套设计系统主题</h1>'
        f'<p class="hero-lede">来自开源仓库 <a href="https://github.com/VoltAgent/awesome-design-md" target="_blank" rel="noopener">awesome-design-md</a> 的主题色板，已经映射到本站 CSS 变量。切换主题后，全站阅读页和实践页会一起变化。</p>'
        f'<div class="hero-actions">'
        f'<button class="btn btn-primary" type="button" data-theme-set="">默认（跟随系统）</button>'
        f'<a class="btn btn-secondary" href="index.html">返回课程地图</a>'
        f'</div>'
        f'</header>'
        f'<section class="gallery-browser">'
        f'<header class="section-head">'
        f'<p class="kicker">外观设置</p>'
        f'<h2>选择主题</h2>'
        f'<p>搜索品牌名或按明暗筛选，再直接应用到当前站点。</p>'
        f'</header>'
        f'<div class="site-toolbar">'
        f'<input class="gallery-search" type="search" placeholder="搜索主题名（apple / spotify / claude ...）" data-gallery-search aria-label="搜索主题">'
        f'<div class="site-segmented" role="group" aria-label="按明暗筛选">'
        f'<button type="button" class="site-segment is-active" data-gallery-filter="all">全部</button>'
        f'<button type="button" class="site-segment" data-gallery-filter="light">浅色</button>'
        f'<button type="button" class="site-segment" data-gallery-filter="dark">深色</button>'
        f'</div>'
        f'<span class="gallery-meta" data-gallery-meta>{len(themes)} 套主题</span>'
        f'</div>'
        f'<div class="gallery-grid" data-gallery-grid>'
        + "".join(cards) +
        f'</div></section>'
        f'</article>'
        f'</main>'
    )
    inline_script = """
<script>
(function(){
  var grid = document.querySelector('[data-gallery-grid]');
  var meta = document.querySelector('[data-gallery-meta]');
  var input = document.querySelector('[data-gallery-search]');
  var filters = document.querySelectorAll('[data-gallery-filter]');
  if (!grid) return;
  var state = { q: '', mode: 'all' };
  function apply(){
    var q = state.q.trim().toLowerCase();
    var visible = 0;
    grid.querySelectorAll('[data-theme-card]').forEach(function(card){
      var slug = card.getAttribute('data-theme-card');
      var name = (card.querySelector('.gallery-card-name')?.textContent || '').toLowerCase();
      var desc = (card.querySelector('.gallery-card-desc')?.textContent || '').toLowerCase();
      var mode = card.getAttribute('data-mode');
      var qok = !q || slug.includes(q) || name.includes(q) || desc.includes(q);
      var mok = state.mode === 'all' || mode === state.mode;
      var show = qok && mok;
      card.style.display = show ? '' : 'none';
      if (show) visible++;
    });
    if (meta) meta.textContent = visible + ' / ' + document.querySelectorAll('[data-theme-card]').length + ' 套';
  }
  input?.addEventListener('input', function(){ state.q = input.value; apply(); });
  filters.forEach(function(b){
    b.addEventListener('click', function(){
      filters.forEach(function(x){ x.classList.toggle('is-active', x === b); });
      state.mode = b.getAttribute('data-gallery-filter');
      apply();
    });
  });
  // Reflect active theme on the apply button
  function refresh(){
    var cur = document.documentElement.getAttribute('data-theme') || '';
    grid.querySelectorAll('[data-theme-set]').forEach(function(el){
      el.classList.toggle('is-active', el.getAttribute('data-theme-set') === cur);
      if (el.getAttribute('data-theme-set') === cur) el.textContent = '✓ 已应用';
      else if (el.hasAttribute('data-gallery-apply')) el.textContent = '应用主题';
    });
  }
  refresh();
  document.documentElement.addEventListener('DOMSubtreeModified', function(){}, true);
  // Listen to attribute change via MutationObserver
  new MutationObserver(refresh).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
})();
</script>
"""
    return (
        head_html("主题画廊", "71 套来自 awesome-design-md 的 design-md 主题。", "themes-gallery")
        + topbar_html("__gallery__")
        + '<div class="layout layout-home">\n'
        + sidebar_html("__gallery__")
        + body
        + '</div>\n'
        + FOOTER_HTML
        + PICKER_HTML
        + SCRIPTS_HTML
        + inline_script
        + "</body></html>\n"
    )

def build() -> None:
    # Render content pages
    for slug, src, title, group, intro in PAGES:
        md_text = load_source(src)
        body, toc = render(md_text)
        out = ROOT / f"{slug}.html"
        out.write_text(page_html(slug, title, intro, body, toc), encoding="utf-8")
        print(f"  build  {out.name}")

    # Render index + gallery
    (ROOT / "index.html").write_text(index_page(), encoding="utf-8")
    print("  build  index.html")
    (ROOT / "themes-gallery.html").write_text(gallery_page(), encoding="utf-8")
    print("  build  themes-gallery.html")

    print(f"\nDone. Output: {ROOT}/")

if __name__ == "__main__":
    build()
