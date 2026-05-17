from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_TRACKS = {"starter", "quick", "full", "exam"}
REQUIRED_PHASES = {"prepare", "observe", "operate", "reflect"}
REQUIRED_INTERACTIONS = {
    "choice",
    "fill",
    "explain",
    "code",
    "command",
    "trace",
    "diagnose",
    "reflection",
}


class PracticeModeBuildTest(unittest.TestCase):
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

    def test_practice_page_is_generated_and_linked(self) -> None:
        practice_html = (ROOT / "practice.html").read_text(encoding="utf-8")
        index_html = (ROOT / "index.html").read_text(encoding="utf-8")

        self.assertIn("实践模式", practice_html)
        self.assertIn("Lab 6 信号量的实现与应用", practice_html)
        self.assertIn("practice.html", index_html)

    def test_practice_content_uses_guided_boundary(self) -> None:
        practice_html = (ROOT / "practice.html").read_text(encoding="utf-8")

        self.assertIn("交互式学习", practice_html)
        self.assertIn("data-practice-workbench", practice_html)
        self.assertIn("window.__PRACTICE_LABS__", practice_html)
        self.assertIn("data-practice-report", practice_html)
        self.assertNotIn("详细注释", practice_html)
        self.assertNotIn("实验答案", practice_html)

    def test_practice_page_uses_focused_workspace_navigation(self) -> None:
        practice_html = (ROOT / "practice.html").read_text(encoding="utf-8")

        self.assertIn("site-topbar", practice_html)
        self.assertIn("site-nav", practice_html)
        self.assertNotIn("chipbar-track", practice_html)
        self.assertNotIn('aria-label="章节快速导航"', practice_html)

    def test_practice_labs_define_complete_interactive_learning_path(self) -> None:
        data = json.loads((ROOT / "content" / "practice-labs.json").read_text(encoding="utf-8"))
        labs = data["labs"]
        self.assertEqual(len(labs), 9)

        seen_interactions: set[str] = set()
        for lab in labs:
            self.assertRegex(lab["id"], r"^lab[1-9]$")
            self.assertTrue(lab.get("reportPrompts"))
            steps = [step for phase in lab["phases"] for step in phase["steps"]]
            self.assertGreaterEqual(len(steps), 7)
            lab_interactions = {step["interaction"] for step in steps}
            self.assertIn("reflection", lab_interactions)
            self.assertTrue({"choice", "command"}.issubset(lab_interactions))
            for step in steps:
                seen_interactions.add(step["interaction"])
                for field in ("context", "hints", "feedback", "success"):
                    self.assertIn(field, step)
                    self.assertGreater(len(step[field]), 0)
                self.assertIn("checks", step)

        self.assertTrue(REQUIRED_INTERACTIONS.issubset(seen_interactions))

    def test_practice_labs_define_lab_studio_model(self) -> None:
        data = json.loads((ROOT / "content" / "practice-labs.json").read_text(encoding="utf-8"))
        self.assertEqual(data["version"], 2)

        track_ids = {track["id"] for track in data["tracks"]}
        self.assertTrue(REQUIRED_TRACKS.issubset(track_ids))

        seen_interactions: set[str] = set()
        for lab in data["labs"]:
            for field in ("estimatedMinutes", "concepts", "outcomes", "phases"):
                self.assertIn(field, lab)
            self.assertGreaterEqual(lab["estimatedMinutes"], 20)
            self.assertGreaterEqual(len(lab["concepts"]), 3)
            self.assertGreaterEqual(len(lab["outcomes"]), 2)

            phase_ids = {phase["id"] for phase in lab["phases"]}
            self.assertEqual(REQUIRED_PHASES, phase_ids)

            steps = [step for phase in lab["phases"] for step in phase["steps"]]
            self.assertGreaterEqual(len(steps), 7)
            for step in steps:
                for field in ("goal", "tracks", "interaction", "prompt", "hints", "success"):
                    self.assertIn(field, step)
                self.assertTrue(set(step["tracks"]).issubset(track_ids))
                self.assertGreaterEqual(len(step["hints"]), 3)
                seen_interactions.add(step["interaction"])

        self.assertTrue(REQUIRED_INTERACTIONS.issubset(seen_interactions))

    def test_practice_engine_hooks_are_present(self) -> None:
        app_js = (ROOT / "assets" / "app.js").read_text(encoding="utf-8")

        self.assertIn("setupPracticeWorkbench", app_js)
        self.assertIn("data-practice-task", app_js)
        self.assertIn("data-practice-track", app_js)
        self.assertIn("data-practice-open-phase", app_js)
        self.assertIn("data-practice-trace-move", app_js)
        self.assertIn("renderLearningPortfolio", app_js)
        self.assertIn("starterTrackId", app_js)
        self.assertIn("activeTrack: starterTrackId", app_js)
        self.assertIn("renderBeginnerGuide", app_js)
        self.assertIn("renderPracticeHeader", app_js)
        self.assertIn("renderLabJourney", app_js)
        self.assertIn("renderPhaseProgress", app_js)
        self.assertIn("renderCoachStep", app_js)
        self.assertIn("renderMechanismBoard", app_js)
        self.assertIn("renderRepairFeedback", app_js)
        self.assertIn("renderLearningRoute", app_js)
        self.assertIn("firstPrinciples", app_js)
        self.assertIn("第一性原理", app_js)
        self.assertIn("data-practice-open-track-menu", app_js)
        self.assertIn("data-practice-prev-lab", app_js)
        self.assertIn("data-practice-next-lab", app_js)
        self.assertIn("data-practice-next-step", app_js)
        self.assertIn("data-practice-route-step", app_js)
        self.assertIn("os-review-practice-workbench", app_js)

    def test_practice_frontend_uses_one_current_workspace_model(self) -> None:
        app_js = (ROOT / "assets" / "app.js").read_text(encoding="utf-8")
        style_css = (ROOT / "assets" / "style.css").read_text(encoding="utf-8")

        self.assertIn("renderCoachStep", app_js)
        self.assertIn("renderMechanismBoard", app_js)
        self.assertIn("renderLearningRoute", app_js)

        for obsolete_function in (
            "function renderTask",
            "function renderInsightPanel",
            "function renderPhaseCoach",
        ):
            self.assertNotIn(obsolete_function, app_js)

        for obsolete_selector in (
            ".practice-studio-status",
            ".practice-track-switch",
            ".practice-track {",
            ".practice-phase-tabs",
            ".practice-phase {",
            ".practice-insight",
            ".practice-rail",
            ".practice-lab-map",
            ".practice-task-list",
            ".practice-task {",
            ".practice-task-index",
            ".practice-task-top",
            ".practice-feedback",
            ".practice-concepts",
        ):
            self.assertNotIn(obsolete_selector, style_css)

        self.assertNotIn("linear-gradient", style_css)
        self.assertNotIn("#d94c3d", style_css)
        self.assertIn("--danger:", style_css)
        self.assertIn("--danger-soft:", style_css)

        for current_selector in (
            ".practice-workspace-head",
            ".practice-lab-journey",
            ".practice-phase-progress",
            ".practice-coach-card",
            ".practice-learning-route",
            ".practice-mechanism-board",
        ):
            self.assertIn(current_selector, style_css)


if __name__ == "__main__":
    unittest.main()
