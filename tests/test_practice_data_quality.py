from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_PHASES = {"prepare", "observe", "operate", "reflect"}
REQUIRED_TRACKS = {"starter", "quick", "full", "exam"}
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
BLOCKED_PHRASES = ("实验答案", "详细注释")
BLOCKED_TEMPLATE_PHRASES = (
    "本 Lab 的关键机制",
    "按顺序输入命令模拟本 Lab 的关键动作",
    "补全或改写片段，让它体现本 Lab 的关键机制",
    "如果这一步没有得到预期现象，最应该检查什么，为什么？",
)
FIRST_PRINCIPLES_FIELDS = (
    "actors",
    "state",
    "boundary",
    "transition",
    "evidence",
    "failureModes",
)
EVIDENCE_WORDS = (
    "证据",
    "观察",
    "输出",
    "日志",
    "状态",
    "现象",
    "结果",
    "轨迹",
    "读到",
    "看到",
)


class PracticeDataQualityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads((ROOT / "content" / "practice-labs.json").read_text(encoding="utf-8"))
        cls.track_ids = {track["id"] for track in cls.data["tracks"]}

    def test_beginner_track_is_available(self) -> None:
        self.assertTrue(REQUIRED_TRACKS.issubset(self.track_ids))

    def test_every_lab_has_four_phase_studio_flow(self) -> None:
        for lab in self.data["labs"]:
            phase_ids = {phase["id"] for phase in lab["phases"]}
            self.assertEqual(REQUIRED_PHASES, phase_ids, lab["id"])
            for phase in lab["phases"]:
                self.assertGreaterEqual(len(phase["steps"]), 1, f"{lab['id']} {phase['id']}")

    def test_step_ids_are_unique_and_tracks_are_valid(self) -> None:
        seen: set[str] = set()
        for lab in self.data["labs"]:
            for phase in lab["phases"]:
                for step in phase["steps"]:
                    self.assertNotIn(step["id"], seen)
                    seen.add(step["id"])
                    self.assertTrue(set(step["tracks"]).issubset(self.track_ids), step["id"])
                    self.assertTrue(step["tracks"], step["id"])

    def test_interactions_hints_and_misconceptions_are_teaching_ready(self) -> None:
        seen_interactions: set[str] = set()
        for lab in self.data["labs"]:
            misconception_count = 0
            for phase in lab["phases"]:
                for step in phase["steps"]:
                    seen_interactions.add(step["interaction"])
                    self.assertIn("checks", step, step["id"])
                    self.assertGreaterEqual(len(step["hints"]), 3, step["id"])
                    if step.get("misconceptions"):
                        misconception_count += len(step["misconceptions"])
                        for item in step["misconceptions"]:
                            self.assertIn("detect", item, step["id"])
                            self.assertGreater(len(item["feedback"]), 12, step["id"])
            self.assertGreaterEqual(misconception_count, 2, lab["id"])
        self.assertTrue(REQUIRED_INTERACTIONS.issubset(seen_interactions))

    def test_every_lab_has_beginner_onboarding(self) -> None:
        starter_counts: dict[str, int] = {}
        for lab in self.data["labs"]:
            beginner = lab.get("beginner")
            self.assertIsInstance(beginner, dict, lab["id"])
            for field in ("story", "why", "analogy", "firstGoal", "reassurance", "glossary"):
                self.assertIn(field, beginner, lab["id"])
            self.assertGreaterEqual(len(beginner["glossary"]), 3, lab["id"])
            starter_steps = [
                step
                for phase in lab["phases"]
                for step in phase["steps"]
                if "starter" in step["tracks"]
            ]
            starter_counts[lab["id"]] = len(starter_steps)
            self.assertGreaterEqual(len(starter_steps), 4, lab["id"])
            self.assertEqual("先用白话认出这关", starter_steps[0]["title"])
            self.assertTrue(any(step["interaction"] == "reflection" for step in starter_steps), lab["id"])
        self.assertGreater(len(set(starter_counts.values())), 1)
        self.assertLess(starter_counts["lab1"], starter_counts["lab6"])
        self.assertLess(starter_counts["lab2"], starter_counts["lab7"])
        self.assertGreaterEqual(max(starter_counts.values()) - min(starter_counts.values()), 3)

    def test_every_lab_has_first_principles_coach_model(self) -> None:
        for lab in self.data["labs"]:
            for field in ("drivingQuestion", "plainLanguageGoal", "mentalModel", "transferChecklist"):
                self.assertIn(field, lab, lab["id"])
            self.assertGreater(len(lab["drivingQuestion"]), 16, lab["id"])
            self.assertGreater(len(lab["plainLanguageGoal"]), 16, lab["id"])
            self.assertIsInstance(lab["mentalModel"], dict, lab["id"])
            self.assertGreater(len(lab["mentalModel"].get("explanation", "")), 20, lab["id"])
            self.assertGreaterEqual(len(lab["mentalModel"].get("flow", [])), 3, lab["id"])
            self.assertGreaterEqual(len(lab["transferChecklist"]), 3, lab["id"])

    def test_every_lab_has_first_principles_fields(self) -> None:
        for lab in self.data["labs"]:
            first_principles = lab.get("firstPrinciples")
            self.assertIsInstance(first_principles, dict, lab["id"])
            for field in FIRST_PRINCIPLES_FIELDS:
                self.assertIn(field, first_principles, lab["id"])
                self.assertIsInstance(first_principles[field], list, f"{lab['id']} {field}")
                self.assertGreaterEqual(len(first_principles[field]), 2, f"{lab['id']} {field}")
                for item in first_principles[field]:
                    self.assertGreater(len(item), 8, f"{lab['id']} {field}")

    def test_every_step_has_coach_scaffolding(self) -> None:
        for lab in self.data["labs"]:
            for phase in lab["phases"]:
                for step in phase["steps"]:
                    coach = step.get("coach")
                    self.assertIsInstance(coach, dict, step["id"])
                    for field in ("why", "observe", "act", "check", "repair"):
                        self.assertIn(field, coach, step["id"])
                        self.assertGreater(len(coach[field]), 10, f"{step['id']} {field}")

    def test_step_copy_is_lab_specific(self) -> None:
        for lab in self.data["labs"]:
            for phase in lab["phases"]:
                for step in phase["steps"]:
                    serialized = json.dumps(step, ensure_ascii=False)
                    for phrase in BLOCKED_TEMPLATE_PHRASES:
                        self.assertNotIn(phrase, serialized, step["id"])

    def test_each_lab_has_evidence_oriented_steps(self) -> None:
        for lab in self.data["labs"]:
            evidence_steps = []
            for phase in lab["phases"]:
                for step in phase["steps"]:
                    observe = step.get("coach", {}).get("observe", "")
                    if any(word in observe for word in EVIDENCE_WORDS):
                        evidence_steps.append(step["id"])
            self.assertGreaterEqual(len(evidence_steps), 3, lab["id"])

    def test_track_lengths_follow_lab_complexity(self) -> None:
        for track in ("starter", "quick", "exam"):
            counts = {
                lab["id"]: sum(
                    1
                    for phase in lab["phases"]
                    for step in phase["steps"]
                    if track in step["tracks"]
                )
                for lab in self.data["labs"]
            }
            self.assertGreater(len(set(counts.values())), 1, track)
            self.assertLess(counts["lab1"], counts["lab6"], track)

        full_counts = {
            lab["id"]: sum(1 for phase in lab["phases"] for _ in phase["steps"])
            for lab in self.data["labs"]
        }
        self.assertGreater(len(set(full_counts.values())), 1)
        self.assertLess(full_counts["lab1"], full_counts["lab6"])

    def test_learning_boundary_phrases_are_not_used(self) -> None:
        serialized = json.dumps(self.data, ensure_ascii=False)
        for phrase in BLOCKED_PHRASES:
            self.assertNotIn(phrase, serialized)


if __name__ == "__main__":
    unittest.main()
