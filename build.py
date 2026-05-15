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
import re
import shutil
from pathlib import Path
from typing import Iterable

import markdown
from markdown.extensions.toc import TocExtension

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
ASSETS_REL = "assets"
IMAGES_REL = "content/images"

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

def scrub(text: str) -> str:
    text = FRONTMATTER_RE.sub("", text, count=1)
    # Drop the leading H1 — the page header already shows the chapter title.
    text = LEADING_H1_RE.sub("", text, count=1)
    for pat, rep in SCRUB_PATTERNS:
        text = re.sub(pat, rep, text)
    return text

def load_source(name) -> str:
    if isinstance(name, tuple):
        chunks = []
        for n in name:
            chunks.append(scrub((CONTENT / n).read_text(encoding="utf-8")))
        # Keep two newlines between merged parts so heading structure stays intact.
        return "\n\n".join(chunks)
    return scrub((CONTENT / name).read_text(encoding="utf-8"))

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

MD_EXTENSIONS = [
    "extra",        # tables, fenced_code, attr_list, footnotes, abbr, def_list
    "sane_lists",
    "smarty",
    TocExtension(toc_depth="2-3", anchorlink=True, permalink=False),
]

def render(md_text: str) -> tuple[str, str]:
    md = markdown.Markdown(extensions=MD_EXTENSIONS, output_format="html5")
    html = md.convert(md_text)
    html = fix_mermaid(html)
    html = fix_images(html)
    toc = getattr(md, "toc", "")
    return html, toc

# --------- templates ---------

SITE_TITLE = "华中科技大学电信本科 · 操作系统复习笔记"
SITE_TAG   = "Operating Systems · Self-Study Notes"

def head_html(page_title: str, page_desc: str) -> str:
    desc = html_mod.escape(page_desc)
    title = html_mod.escape(page_title)
    return f"""<!doctype html>
<html lang="zh-Hans">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{desc}">
<meta name="color-scheme" content="light dark">
<title>{title} — {SITE_TITLE}</title>
<link rel="stylesheet" href="{ASSETS_REL}/style.css">
<link rel="stylesheet" href="themes/themes.css">
<link rel="icon" type="image/svg+xml" href="{ASSETS_REL}/favicon.svg">
<script>(function(){{try{{var t=localStorage.getItem("os-review-theme");if(t)document.documentElement.setAttribute("data-theme",t);}}catch(e){{}}}})();</script>
</head>
<body>
"""

def topbar_html(active_slug: str) -> str:
    chips = []
    for slug, src, title, group, _ in PAGES:
        cls = "chip" + (" chip-active" if slug == active_slug else "")
        chips.append(f'<a class="{cls}" href="{slug}.html">{html_mod.escape(title)}</a>')
    chip_html = "\n        ".join(chips)
    return f"""<header class="topbar" role="banner">
  <div class="topbar-inner">
    <a class="brand" href="index.html" aria-label="返回首页">
      <svg class="brand-icon" viewBox="0 0 24 24" aria-hidden="true"><use href="{ASSETS_REL}/icons.svg#book"/></svg>
      <span>{SITE_TITLE}</span>
    </a>
    <div class="topbar-actions">
      <button class="theme-toggle" type="button" aria-label="切换深浅色" data-theme-toggle title="切换深浅色">
        <svg class="i" viewBox="0 0 24 24" aria-hidden="true"><use href="{ASSETS_REL}/icons.svg#sun"/></svg>
      </button>
      <button class="theme-toggle theme-picker-btn" type="button" aria-label="选择主题" data-theme-picker title="选择主题（71 套）">
        <svg class="i" viewBox="0 0 24 24" aria-hidden="true"><use href="{ASSETS_REL}/icons.svg#palette"/></svg>
      </button>
    </div>
  </div>
  <nav class="chipbar" aria-label="章节快速导航">
    <button class="chipbar-toggle" type="button" aria-expanded="false" data-chipbar-toggle>章节目录</button>
    <div class="chipbar-track">
        {chip_html}
    </div>
  </nav>
</header>
"""

def sidebar_html(active_slug: str) -> str:
    sections = []
    for grp_id, grp_label, grp_icon in GROUPS:
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
            f'<h3 id="grp-{grp_id}" class="nav-group-title"><span class="nav-group-icon">{grp_icon}</span>{html_mod.escape(grp_label)}</h3>'
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
    <p class="ghost" style="margin-top:.6rem">本站源代码以 markdown 编写、build.py 重新生成。</p>
  </div>
</aside>
"""

FOOTER_HTML = """<footer class="page-footer">
  <p>本站为操作系统课程的复习整理。内容仅供学习交流使用；版权归原始教材作者及课程材料的版权所有人所有。</p>
  <p class="meta">Built with Python · Markdown · Mermaid · 无第三方追踪脚本</p>
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
    import json as _json
    p = ROOT / "themes" / "themes.json"
    if not p.exists():
        return '<script>window.__THEMES__=[];</script>'
    obj = _json.loads(p.read_text(encoding="utf-8"))
    arr = obj.get("themes", [])
    return f'<script id="themes-data">window.__THEMES__={_json.dumps(arr, ensure_ascii=False)};</script>'

SCRIPTS_HTML = f"""
{themes_inline_script()}
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js" defer></script>
<script src="{ASSETS_REL}/app.js" defer></script>
"""

def page_html(slug: str, title: str, intro: str, body: str, toc: str) -> str:
    title_esc = html_mod.escape(title)
    intro_esc = html_mod.escape(intro)
    toc_block = (
        f'<aside class="page-toc" aria-label="本页目录"><h3 class="page-toc-title">本页目录</h3>{toc}</aside>'
        if toc else ""
    )
    return (
        head_html(title, intro)
        + topbar_html(slug)
        + '<div class="layout">\n'
        + sidebar_html(slug)
        + '<main class="main" id="main">\n'
        + f'  <article class="prose">\n'
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
        + SCRIPTS_HTML
        + "</body></html>\n"
    )

# --------- index page ---------

INDEX_TEMPLATE = """<main class="main main-home" id="main">
  <article class="home">
    <header class="hero">
      <p class="hero-eyebrow">华中科技大学 · 电信本科</p>
      <h1 class="hero-title">操作系统复习笔记</h1>
      <p class="hero-lede">5 章 + 总复习提纲 + 作业明细 + 教程三部分。围绕考点与求职面试主题做了图文融合，含 mermaid 结构图。</p>
      <div class="hero-actions">
        <a class="btn btn-primary" href="ch1.html">从第 1 章开始 →</a>
        <a class="btn" href="review.html">直达总复习提纲</a>
      </div>
    </header>

    <section class="map">
      <h2 class="map-title"><span class="map-icon">📖</span>章节路径</h2>
      <ol class="cards">
        {chapter_cards}
      </ol>
    </section>

    <section class="map">
      <h2 class="map-title"><span class="map-icon">📝</span>考前材料</h2>
      <ol class="cards cards-2">
        {exam_cards}
      </ol>
    </section>

    <section class="map">
      <h2 class="map-title"><span class="map-icon">📚</span>教程笔记</h2>
      <ol class="cards cards-2">
        {tutorial_cards}
      </ol>
    </section>

    <section class="tips">
      <h2 class="map-title"><span class="map-icon">💡</span>怎么用这套笔记</h2>
      <ul class="bullets">
        <li><strong>第一遍系统过</strong>：按 ch1 → ch5 顺序，每章先读章末小结，再回头补细节。</li>
        <li><strong>考前冲刺</strong>：直接读「总复习提纲」，再用「作业明细」对照真题题型。</li>
        <li><strong>遇到不熟的概念</strong>：右栏目录可定位到具体小节；mermaid 图鼠标悬停可放大。</li>
        <li><strong>移动端</strong>：左侧导航折叠在顶部「章节目录」按钮内。</li>
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
    tutorial_cards = "\n        ".join(
        card_html(slug, title, intro, badge=f"P{i+1}")
        for i, (slug, _, title, group, intro) in enumerate(p for p in PAGES if p[3] == "tutorial")
    )
    body = INDEX_TEMPLATE.format(
        chapter_cards=chapter_cards,
        exam_cards=exam_cards,
        tutorial_cards=tutorial_cards,
    )
    return (
        head_html("课程地图", "5 章 + 复习提纲 + 作业 + 教程三部分。")
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
            f'<button class="gallery-apply" type="button" data-theme-set="{slug}">应用主题</button>'
            f'<a class="gallery-preview-link" href="ch1.html" data-preview-link="{slug}">在 ch1 中预览 →</a>'
            f'</div></div></article>'
        )
    body = (
        f'<main class="main main-home" id="main">'
        f'<article class="home">'
        f'<header class="hero">'
        f'<p class="hero-eyebrow">主题画廊</p>'
        f'<h1 class="hero-title">71 套设计系统主题</h1>'
        f'<p class="hero-lede">来自开源仓库 <a href="https://github.com/VoltAgent/awesome-design-md" target="_blank" rel="noopener">awesome-design-md</a> 的 <strong>71</strong> 个 design-md 主题色板，已映射到本站的 CSS 变量。点击「应用主题」全站立即生效；选择跟随系统则恢复默认。</p>'
        f'<div class="hero-actions">'
        f'<button class="btn btn-primary" type="button" data-theme-set="">默认（跟随系统）</button>'
        f'<a class="btn" href="index.html">返回首页</a>'
        f'</div>'
        f'</header>'
        f'<div class="gallery-toolbar">'
        f'<input class="gallery-search" type="search" placeholder="搜索主题名（apple / spotify / claude ...）" data-gallery-search aria-label="搜索主题">'
        f'<div class="gallery-filters" role="group" aria-label="按明暗筛选">'
        f'<button type="button" class="gallery-filter is-active" data-gallery-filter="all">全部</button>'
        f'<button type="button" class="gallery-filter" data-gallery-filter="light">浅色</button>'
        f'<button type="button" class="gallery-filter" data-gallery-filter="dark">深色</button>'
        f'</div>'
        f'<span class="gallery-meta" data-gallery-meta>{len(themes)} 套主题</span>'
        f'</div>'
        f'<div class="gallery-grid" data-gallery-grid>'
        + "".join(cards) +
        f'</div>'
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
      else if (el.classList.contains('gallery-apply')) el.textContent = '应用主题';
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
        head_html("主题画廊", "71 套来自 awesome-design-md 的 design-md 主题。")
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
