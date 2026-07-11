from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATED_PAGES = [
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


class SiteConsistencyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run(
            [sys.executable, "build.py"],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def read_page(self, page: str) -> str:
        return (ROOT / page).read_text(encoding="utf-8")

    def test_all_pages_use_one_site_topbar_model(self) -> None:
        for page in GENERATED_PAGES:
            html = self.read_page(page)
            self.assertIn('class="topbar site-topbar"', html, page)
            self.assertIn('class="site-nav"', html, page)
            self.assertIn("data-site-nav-toggle", html, page)
            self.assertNotIn("topbar-practice", html, page)
            self.assertNotIn("practice-site-shortcuts", html, page)
            self.assertNotIn("chipbar", html, page)
            self.assertNotIn("data-chipbar-toggle", html, page)
            self.assertNotIn('aria-label="章节快速导航"', html, page)

    def test_sidebar_does_not_pollute_document_headings(self) -> None:
        for page in GENERATED_PAGES:
            html = self.read_page(page)
            self.assertNotIn("<h3 id=\"grp-", html, page)
            if '<aside class="sidebar"' in html:
                sidebar = html.split('<aside class="sidebar"', 1)[1].split("</aside>", 1)[0]
                self.assertNotIn("<h1", sidebar, page)
                self.assertNotIn("<h2", sidebar, page)
                self.assertNotIn("<h3", sidebar, page)

    def test_home_and_gallery_share_site_components(self) -> None:
        index_html = self.read_page("index.html")
        gallery_html = self.read_page("themes-gallery.html")
        style_css = (ROOT / "assets" / "style.css").read_text(encoding="utf-8")

        self.assertIn("home-dashboard", index_html)
        self.assertIn("section-head", index_html)
        self.assertIn("section-head", gallery_html)
        self.assertIn("site-toolbar", gallery_html)

        for old_selector in (
            ".chipbar",
            ".practice-site-shortcuts",
            ".topbar-practice",
            ".gallery-apply {",
            ".gallery-preview-link {",
            ".map-icon",
        ):
            self.assertNotIn(old_selector, style_css)

        for shared_selector in (
            ".site-nav",
            ".site-nav-toggle",
            ".section-head",
            ".surface",
            ".site-toolbar",
            ".btn-ghost",
            ".btn-secondary",
        ):
            self.assertIn(shared_selector, style_css)

    def test_public_homepage_explains_the_case_and_its_boundary(self) -> None:
        html = self.read_page("index.html")

        for label in (
            "Problem / 问题",
            "Role / 角色",
            "System / 系统",
            "Evidence / 证据",
            "Limitations / 边界",
            "Jason 决定目标、结构与验收",
            "不声称提高成绩",
        ):
            self.assertIn(label, html)

        for destination in (
            "https://estelledc.github.io/",
            "https://estelledc.github.io/about/",
            "https://estelledc.github.io/resume/",
            "https://github.com/estelledc/hust-eic-os-review",
        ):
            self.assertIn(destination, html)

    def test_every_page_has_share_and_structured_metadata(self) -> None:
        for page in GENERATED_PAGES:
            html = self.read_page(page)
            self.assertIn('<link rel="canonical" href="https://estelledc.github.io/hust-eic-os-review/', html, page)
            self.assertIn('property="og:image"', html, page)
            self.assertIn('name="twitter:card" content="summary_large_image"', html, page)
            self.assertIn('type="application/ld+json"', html, page)
            self.assertIn('class="jx-skip-link"', html, page)


if __name__ == "__main__":
    unittest.main()
