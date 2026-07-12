"""Audit the generated public showcase and its evidence claims."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SITE_URL = "https://estelledc.github.io/hust-eic-os-review/"
PAGES = [
    "index.html",
    "ch1.html",
    "ch2.html",
    "ch3.html",
    "ch4.html",
    "ch5.html",
    "review.html",
    "homework.html",
    "practice.html",
    "cheatsheet.html",
    "quiz.html",
    "tutorial-1.html",
    "tutorial-2.html",
    "tutorial-3.html",
    "themes-gallery.html",
    "404.html",
]


class DocumentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: list[tuple[str, str]] = []
        self.h1_count = 0
        self.missing_image_alt: list[str] = []
        self.incomplete_image_contract: list[str] = []
        self._json_ld_depth = 0
        self._json_ld_chunks: list[str] = []
        self.json_ld: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "h1":
            self.h1_count += 1
        if tag == "img":
            src = values.get("src") or "<unknown>"
            if not (values.get("alt") or "").strip():
                self.missing_image_alt.append(src)
            required = ("width", "height", "loading", "decoding")
            if any(not values.get(attribute) for attribute in required):
                self.incomplete_image_contract.append(src)
        for attribute in ("href", "src"):
            if values.get(attribute):
                self.references.append((attribute, values[attribute] or ""))
        if tag == "script" and values.get("type") == "application/ld+json":
            self._json_ld_depth = 1
            self._json_ld_chunks = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._json_ld_depth:
            self.json_ld.append("".join(self._json_ld_chunks))
            self._json_ld_depth = 0

    def handle_data(self, data: str) -> None:
        if self._json_ld_depth:
            self._json_ld_chunks.append(data)


def canonical_for(page: str) -> str:
    return SITE_URL if page == "index.html" else f"{SITE_URL}{page}"


def resolve_local_reference(page: Path, raw: str) -> Path | None:
    parsed = urlsplit(raw)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    path = unquote(parsed.path)
    if path.startswith("/"):
        return None
    return (page.parent / path).resolve()


def audit_page(page_name: str, errors: list[str]) -> None:
    page = ROOT / page_name
    if not page.is_file():
        errors.append(f"missing generated page: {page_name}")
        return
    html = page.read_text(encoding="utf-8")
    parser = DocumentParser()
    parser.feed(html)

    required = [
        f'<link rel="canonical" href="{canonical_for(page_name)}">',
        '<meta property="og:image" content="https://estelledc.github.io/hust-eic-os-review/assets/og-os-review.png">',
        '<meta name="twitter:card" content="summary_large_image">',
        '<meta name="author" content="Jason Xun">',
        '<a class="jx-skip-link" href="#main">',
    ]
    for marker in required:
        if marker not in html:
            errors.append(f"{page_name}: missing {marker}")
    if page_name == "404.html" and '<meta name="robots" content="noindex,follow">' not in html:
        errors.append("404.html: missing noindex directive")

    if parser.h1_count != 1:
        errors.append(f"{page_name}: expected one h1, found {parser.h1_count}")
    if parser.missing_image_alt:
        errors.append(f"{page_name}: images missing alt: {parser.missing_image_alt[:3]}")
    if parser.incomplete_image_contract:
        errors.append(
            f"{page_name}: images missing width/height/loading/decoding: "
            f"{parser.incomplete_image_contract[:3]}"
        )
    if len(parser.json_ld) != 1:
        errors.append(f"{page_name}: expected one JSON-LD block, found {len(parser.json_ld)}")
    else:
        try:
            data = json.loads(parser.json_ld[0])
            if data.get("@context") != "https://schema.org":
                errors.append(f"{page_name}: unexpected JSON-LD context")
            graph = data.get("@graph", [])
            person = next((node for node in graph if node.get("@type") == "Person"), {})
            if person.get("name") != "Jason Xun" or person.get("@id") != "https://estelledc.github.io/#person":
                errors.append(f"{page_name}: JSON-LD Person identity mismatch")
        except json.JSONDecodeError as error:
            errors.append(f"{page_name}: invalid JSON-LD: {error}")

    for _, raw in parser.references:
        target = resolve_local_reference(page, raw)
        if target is not None and not target.is_file():
            errors.append(f"{page_name}: broken local reference {raw}")


def audit_claims(errors: list[str]) -> None:
    homepage = (ROOT / "index.html").read_text(encoding="utf-8")
    required_copy = [
        "Problem / 问题",
        "Role / 角色",
        "System / 系统",
        "Evidence / 证据",
        "Limitations / 边界",
        "Jason 决定目标、结构与验收",
        "AI 工具辅助代码、内容结构化和插图生产",
        "不声称提高成绩",
        "用 3 步进入一次 OS 机制实验",
        "3 种可访问阅读模式",
    ]
    for marker in required_copy:
        if marker not in homepage:
            errors.append(f"index.html: missing public case marker {marker}")

    labs = json.loads((ROOT / "content" / "practice-labs.json").read_text(encoding="utf-8"))["labs"]
    themes = json.loads((ROOT / "themes" / "themes.json").read_text(encoding="utf-8"))["themes"]
    manifest = json.loads(
        (ROOT / "content" / "knowledge-illustrations.json").read_text(encoding="utf-8")
    )["entries"]
    facts = {"9": len(labs), "614": len(manifest)}
    for claimed, actual in facts.items():
        if int(claimed) != actual:
            errors.append(f"claim drift: homepage says {claimed}, source has {actual}")
        if f">{claimed}<" not in homepage and f">{claimed} " not in homepage:
            errors.append(f"index.html: evidence number {claimed} is not rendered")
    if homepage.count('class="access-mode-card"') != 3:
        errors.append("index.html: expected exactly 3 accessibility mode controls")
    if "window.__THEMES__" in homepage or "themes/themes.css" in homepage:
        errors.append("index.html: legacy 71-theme payload still ships on the homepage")
    gallery = (ROOT / "themes-gallery.html").read_text(encoding="utf-8")
    if gallery.count('class="gallery-card"') != len(themes):
        errors.append("themes-gallery.html: archive count drift")
    for entry in manifest:
        image = ROOT / entry["image"]
        if not image.is_file():
            errors.append(f"manifest image missing: {entry['image']}")

    version = (ROOT / "assets" / "jx" / "VERSION").read_text(encoding="utf-8").strip()
    if version != "2.2.0":
        errors.append(f"Jason DS version is {version}, expected 2.2.0")

    style_css = (ROOT / "assets" / "style.css").read_text(encoding="utf-8")
    if re.search(r"transition\s*:[^;]*\ball\b", style_css):
        errors.append("assets/style.css: transition: all is not allowed")
    if "0.01ms" in style_css:
        errors.append("assets/style.css: reduced motion still uses the 0.01ms global override")
    if ".main, .home, .sidebar { animation" in style_css or ".cards .card { animation" in style_css:
        errors.append("assets/style.css: global page/card reveal animation remains")
    if "var(--jx-ease-drawer)" not in style_css:
        errors.append("assets/style.css: theme picker does not use the DS drawer easing")
    for selector in (".card:hover {", ".gallery-card:hover {", ".system-paths a:hover {"):
        block = style_css.split(selector, 1)[1].split("}", 1)[0]
        if "transform:" in block:
            errors.append(f"assets/style.css: card lift remains in {selector}")
    if 'securityLevel: "strict"' not in (ROOT / "assets" / "app.js").read_text(encoding="utf-8"):
        errors.append("Mermaid must use strict security mode")

    share_image = ROOT / "assets" / "og-os-review.png"
    if not share_image.is_file():
        errors.append("missing assets/og-os-review.png")
    else:
        with Image.open(share_image) as image:
            if image.size != (1200, 630):
                errors.append(f"share image is {image.size}, expected 1200x630")


def main() -> int:
    subprocess.run([sys.executable, "build.py"], cwd=ROOT, check=True)
    errors: list[str] = []
    for page in PAGES:
        audit_page(page, errors)
    audit_claims(errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"OK: {len(PAGES)} routes, metadata, local links, evidence, and share image verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
