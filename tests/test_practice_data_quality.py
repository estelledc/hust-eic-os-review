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
# 跨 lab 模板句：任意短语在 ≥ CROSS_LAB_LIMIT 个 lab 中重复出现即视为模板化
CROSS_LAB_TEMPLATE_PHRASES = (
    "证据会帮助你判断",
    "先回到右侧术语卡",
    "把题目翻成日常语言",
    "已经抓住入口问题",
)
CROSS_LAB_LIMIT = 5
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
            # starter 首步必须是 choice 或 diagnose，让用户先认出题目
            self.assertIn(
                starter_steps[0]["interaction"],
                {"choice", "diagnose"},
                f"{lab['id']} starter 首步必须是 choice 或 diagnose",
            )
            # starter 首步标题不允许跨 lab 雷同（在 test_starter_step_titles_are_lab_specific 里强校验）
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

    def test_coach_fields_are_not_field_copies(self) -> None:
        """coach.{why|act|check} 不允许直接复制 context|prompt|success。"""
        violations: list[str] = []
        for lab in self.data["labs"]:
            for phase in lab["phases"]:
                for step in phase["steps"]:
                    coach = step.get("coach", {})
                    if coach.get("why") and coach["why"] == step.get("context"):
                        violations.append(f"{step['id']} coach.why == context")
                    if coach.get("act") and coach["act"] == step.get("prompt"):
                        violations.append(f"{step['id']} coach.act == prompt")
                    if coach.get("check") and coach["check"] == step.get("success"):
                        violations.append(f"{step['id']} coach.check == success")
        self.assertEqual(
            violations,
            [],
            f"\n共 {len(violations)} 处 coach 字段是复制而非教学扩写：\n  "
            + "\n  ".join(violations[:20])
            + ("\n  ..." if len(violations) > 20 else ""),
        )

    def test_template_phrases_are_not_repeated_across_labs(self) -> None:
        """已知模板短语不允许在 ≥ CROSS_LAB_LIMIT 个 lab 中重复出现。"""
        for phrase in CROSS_LAB_TEMPLATE_PHRASES:
            hit_labs = []
            for lab in self.data["labs"]:
                serialized = json.dumps(lab, ensure_ascii=False)
                if phrase in serialized:
                    hit_labs.append(lab["id"])
            self.assertLess(
                len(hit_labs),
                CROSS_LAB_LIMIT,
                f'模板短语 "{phrase}" 在 {len(hit_labs)} 个 lab 中出现：{hit_labs}',
            )

    def test_starter_step_titles_are_lab_specific(self) -> None:
        """9 个 lab 的 starter 首步标题不能完全相同。"""
        first_titles: list[str] = []
        for lab in self.data["labs"]:
            starter_steps = [
                step
                for phase in lab["phases"]
                for step in phase["steps"]
                if "starter" in step["tracks"]
            ]
            if starter_steps:
                first_titles.append(starter_steps[0]["title"])
        # 至少 7 个 lab 的首步标题不同（允许 2 个偶然撞名）
        self.assertGreaterEqual(
            len(set(first_titles)),
            max(7, len(first_titles) - 1),
            f"starter 首步标题过于雷同：{first_titles}",
        )

    def test_third_level_hints_are_substantive(self) -> None:
        """第三层 hint 应能指向具体差别，平均长度 ≥ 50 字。"""
        h3_lengths: list[int] = []
        short_h3: list[str] = []
        for lab in self.data["labs"]:
            for phase in lab["phases"]:
                for step in phase["steps"]:
                    for hint in step.get("hints", []):
                        if hint.get("level") == 3:
                            text = hint.get("text", "")
                            h3_lengths.append(len(text))
                            if len(text) < 30:
                                short_h3.append(f"{step['id']}: {text}")
        self.assertTrue(h3_lengths, "未发现第三层 hint")
        avg = sum(h3_lengths) / len(h3_lengths)
        self.assertGreaterEqual(
            avg,
            50,
            f"第三层 hint 平均长度 {avg:.0f} 字，过短无法接近答案。"
            + (f"\n过短示例：\n  " + "\n  ".join(short_h3[:5]) if short_h3 else ""),
        )


if __name__ == "__main__":
    unittest.main()
