"""Audit the generated public showcase and its evidence claims."""

from __future__ import annotations

import json
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
]


class DocumentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: list[tuple[str, str]] = []
        self.h1_count = 0
        self.missing_image_alt: list[str] = []
        self._json_ld_depth = 0
        self._json_ld_chunks: list[str] = []
        self.json_ld: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "h1":
            self.h1_count += 1
        if tag == "img" and not (values.get("alt") or "").strip():
            self.missing_image_alt.append(values.get("src") or "<unknown>")
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
        '<a class="jx-skip-link" href="#main">',
    ]
    for marker in required:
        if marker not in html:
            errors.append(f"{page_name}: missing {marker}")

    if parser.h1_count != 1:
        errors.append(f"{page_name}: expected one h1, found {parser.h1_count}")
    if parser.missing_image_alt:
        errors.append(f"{page_name}: images missing alt: {parser.missing_image_alt[:3]}")
    if len(parser.json_ld) != 1:
        errors.append(f"{page_name}: expected one JSON-LD block, found {len(parser.json_ld)}")
    else:
        try:
            data = json.loads(parser.json_ld[0])
            if data.get("@context") != "https://schema.org":
                errors.append(f"{page_name}: unexpected JSON-LD context")
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
    ]
    for marker in required_copy:
        if marker not in homepage:
            errors.append(f"index.html: missing public case marker {marker}")

    labs = json.loads((ROOT / "content" / "practice-labs.json").read_text(encoding="utf-8"))["labs"]
    themes = json.loads((ROOT / "themes" / "themes.json").read_text(encoding="utf-8"))["themes"]
    manifest = json.loads(
        (ROOT / "content" / "knowledge-illustrations.json").read_text(encoding="utf-8")
    )["entries"]
    facts = {"9": len(labs), "71": len(themes), "614": len(manifest)}
    for claimed, actual in facts.items():
        if int(claimed) != actual:
            errors.append(f"claim drift: homepage says {claimed}, source has {actual}")
        if f">{claimed}<" not in homepage and f">{claimed} " not in homepage:
            errors.append(f"index.html: evidence number {claimed} is not rendered")
    for entry in manifest:
        image = ROOT / entry["image"]
        if not image.is_file():
            errors.append(f"manifest image missing: {entry['image']}")

    version = (ROOT / "assets" / "jx" / "VERSION").read_text(encoding="utf-8").strip()
    if version != "2.0.0":
        errors.append(f"Jason DS version is {version}, expected 2.0.0")

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
