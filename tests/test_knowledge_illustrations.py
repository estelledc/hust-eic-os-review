from __future__ import annotations

import json
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.knowledge_illustrations import (  # noqa: E402
    MANIFEST_PATH,
    collect_rebuild_batch_status,
    extract_knowledge_points,
    print_builtin_next_prompts,
    print_commands,
    print_rebuild_commands,
    print_rebuild_status,
    promote_accepted_rebuilds,
    rebuild_jsonl_paths,
    select_rebuild_items_missing_staged,
    select_rebuild_paths_missing_staged,
    stage_built_in_output,
    validate_rebuild_queue,
    validate_staged_rebuild_item,
    validate_staged_rebuild_outputs,
    write_rebuild_review_board,
)
from build import inject_knowledge_illustrations  # noqa: E402


class KnowledgeIllustrationsTest(unittest.TestCase):
    def test_extracts_every_h2_to_h4_heading_as_a_knowledge_point(self) -> None:
        points = extract_knowledge_points(ROOT)

        self.assertEqual(614, len(points))
        self.assertEqual(len(points), len({point.id for point in points}))
        self.assertTrue(all(2 <= point.level <= 4 for point in points))
        self.assertTrue(all(point.source.startswith("content/") for point in points))

    def test_manifest_covers_all_h2_to_h4_knowledge_points(self) -> None:
        points = extract_knowledge_points(ROOT)
        expected_ids = {point.id for point in points}

        manifest = json.loads((ROOT / MANIFEST_PATH).read_text(encoding="utf-8"))
        entries = manifest["entries"]
        actual_ids = {entry["id"] for entry in entries}

        self.assertEqual(expected_ids, actual_ids)
        self.assertEqual("gpt-image-2", manifest["model"])
        self.assertEqual("scientific-educational", manifest["use_case"])
        self.assertEqual("high", manifest["quality"])
        self.assertEqual("text-v2", manifest["prompt_version"])
        self.assertIs(True, manifest["requires_in_image_text"])

        for entry in entries:
            with self.subTest(entry=entry["id"]):
                self.assertEqual("gpt-image-2", entry["model"])
                self.assertEqual("text-v2", entry["prompt_version"])
                self.assertIs(True, entry["requires_in_image_text"])
                self.assertTrue(entry["image"].startswith("content/images/knowledge/"))
                self.assertTrue(entry["image"].endswith(".webp"))
                self.assertIn(entry["title"], entry["prompt"])
                self.assertIn("In-image text:", entry["prompt"])
                self.assertIn("Simplified Chinese", entry["prompt"])
                self.assertNotIn("No embedded text", entry["prompt"])
                self.assertNotIn("no labels", entry["prompt"])
                self.assertNotIn("no Chinese characters", entry["prompt"])

    def test_gpt_image_2_rebuild_queue_is_complete_and_readable(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / MANIFEST_PATH
            manifest.parent.mkdir(parents=True)
            manifest.write_text(
                json.dumps(
                    {
                        "entries": [
                            {"id": "demo-k001"},
                            {"id": "demo-k002"},
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            prompt = (
                "Required exact visible Chinese text: “标题”, “入口”, “队列”, “完成”. "
                "Composition: clean infographic diagram. "
                "Style: polished educational diagram. "
                "Constraints: Simplified Chinese only."
            )
            queue = root / "tmp" / "imagegen" / "gpt-image2-rebuild-demo-k001-k002.jsonl"
            queue.parent.mkdir(parents=True)
            queue.write_text(
                "\n".join(
                    [
                        json.dumps({"out": "demo-k001.webp", "prompt": prompt}, ensure_ascii=False),
                        json.dumps({"out": "demo-k002.webp", "prompt": prompt}, ensure_ascii=False),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            errors = validate_rebuild_queue(root)

        self.assertEqual([], errors)

    def test_rebuild_queue_glob_excludes_accepted_list(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue = root / "tmp" / "imagegen" / "gpt-image2-rebuild-demo-k001.jsonl"
            accepted = root / "tmp" / "imagegen" / "gpt-image2-rebuild-accepted.jsonl"
            queue.parent.mkdir(parents=True)
            queue.write_text(json.dumps({"out": "demo-k001.webp", "prompt": "demo"}) + "\n", encoding="utf-8")
            accepted.write_text(
                json.dumps({"id": "demo-k001", "accepted": True}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            paths = rebuild_jsonl_paths(root)

        self.assertEqual([queue], paths)

    def test_rebuild_queue_rejects_non_explanatory_prompt_shape(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "content" / "knowledge-illustrations.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(
                json.dumps({"entries": [{"id": "demo-k001"}]}, ensure_ascii=False),
                encoding="utf-8",
            )
            queue = root / "tmp" / "imagegen" / "gpt-image2-rebuild-demo-k001.jsonl"
            queue.parent.mkdir(parents=True)
            prompt = (
                "Use case: scientific-educational. "
                "Required exact visible Chinese text: “标题”, “标签一”, “标签二”. "
                "Composition: layered stack. Style: clear. Constraints: Simplified Chinese only."
            )
            queue.write_text(
                json.dumps({"out": "demo-k001.webp", "prompt": prompt}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            errors = validate_rebuild_queue(root)

        self.assertTrue(any("prompt must specify infographic format" in error for error in errors))
        self.assertTrue(any("prompt must specify diagram format" in error for error in errors))
        self.assertTrue(any("too few visible labels" in error for error in errors))

    def test_generation_commands_stage_outputs_before_promotion(self) -> None:
        buffer = StringIO()

        with redirect_stdout(buffer):
            print_commands([Path("tmp/imagegen/example.jsonl")])

        command = buffer.getvalue()
        self.assertIn("--out-dir output/imagegen/knowledge-illustrations", command)
        self.assertIn("--quality high", command)
        self.assertIn("--no-augment", command)
        self.assertIn("--concurrency 1", command)
        self.assertNotIn("--out-dir content/images/knowledge", command)

    def test_rebuild_commands_keep_recoverable_batch_staging(self) -> None:
        buffer = StringIO()

        with redirect_stdout(buffer):
            print_rebuild_commands([Path("tmp/imagegen/gpt-image2-rebuild-ch1-k001-k004.jsonl")])

        command = buffer.getvalue()
        self.assertIn("--out-dir output/imagegen/rebuild-ch1-k001-k004", command)
        self.assertIn("--quality high", command)
        self.assertIn("--no-augment", command)
        self.assertIn("--concurrency 1", command)
        self.assertIn("--fail-fast", command)
        self.assertNotIn("--out-dir content/images/knowledge", command)

    def test_rebuild_dry_run_commands_do_not_generate_files(self) -> None:
        buffer = StringIO()

        with redirect_stdout(buffer):
            print_rebuild_commands(
                [Path("tmp/imagegen/gpt-image2-rebuild-ch1-k001-k004.jsonl")],
                dry_run=True,
            )

        command = buffer.getvalue()
        self.assertIn("--dry-run", command)
        self.assertNotIn("--fail-fast", command)

    def test_pending_rebuild_paths_skip_fully_staged_batches(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            complete = root / "tmp" / "imagegen" / "gpt-image2-rebuild-complete-k001-k002.jsonl"
            pending = root / "tmp" / "imagegen" / "gpt-image2-rebuild-pending-k001-k002.jsonl"
            complete.parent.mkdir(parents=True)
            complete.write_text(
                "\n".join(
                    [
                        json.dumps({"out": "complete-k001.webp"}),
                        json.dumps({"out": "complete-k002.webp"}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            pending.write_text(
                "\n".join(
                    [
                        json.dumps({"out": "pending-k001.webp"}),
                        json.dumps({"out": "pending-k002.webp"}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            complete_dir = root / "output" / "imagegen" / "rebuild-complete-k001-k002"
            complete_dir.mkdir(parents=True)
            (complete_dir / "complete-k001.webp").write_bytes(self._fake_vp8x_webp(1536, 1024))
            (complete_dir / "complete-k002.webp").write_bytes(self._fake_vp8x_webp(1536, 1024))
            pending_dir = root / "output" / "imagegen" / "rebuild-pending-k001-k002"
            pending_dir.mkdir(parents=True)
            (pending_dir / "pending-k001.webp").write_bytes(self._fake_vp8x_webp(1536, 1024))

            paths = select_rebuild_paths_missing_staged(root, [complete, pending])

        self.assertEqual([pending], paths)

    def test_builtin_next_prompt_selects_one_missing_staged_item(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue = root / "tmp" / "imagegen" / "gpt-image2-rebuild-demo-k001-k002.jsonl"
            queue.parent.mkdir(parents=True)
            queue.write_text(
                "\n".join(
                    [
                        json.dumps({"out": "demo-k001.webp", "prompt": "already staged"}),
                        json.dumps({"out": "demo-k002.webp", "prompt": "generate this one"}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            staged = root / "output" / "imagegen" / "rebuild-demo-k001-k002" / "demo-k001.webp"
            staged.parent.mkdir(parents=True)
            staged.write_bytes(self._fake_vp8x_webp(1536, 1024))

            items = select_rebuild_items_missing_staged(root, limit=1)

            self.assertEqual(1, len(items))
            self.assertEqual("demo-k002", items[0].image_id)
            self.assertEqual("output/imagegen/rebuild-demo-k001-k002/demo-k002.webp", items[0].staged_output)

            buffer = StringIO()
            with redirect_stdout(buffer):
                print_builtin_next_prompts(items)

            output = buffer.getvalue()
            self.assertIn("mode=built-in image_gen one image only", output)
            self.assertIn("valid 1536x1024 WebP", output)
            self.assertIn("staged_output=output/imagegen/rebuild-demo-k001-k002/demo-k002.webp", output)
            self.assertIn("generate this one", output)
            self.assertNotIn("already staged", output)

    def test_stage_built_in_output_copies_valid_webp_to_expected_staged_path(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue = root / "tmp" / "imagegen" / "gpt-image2-rebuild-demo-k001.jsonl"
            queue.parent.mkdir(parents=True)
            queue.write_text(json.dumps({"out": "demo-k001.webp", "prompt": "demo"}) + "\n", encoding="utf-8")
            source = root / "generated.webp"
            source.write_bytes(self._fake_vp8x_webp(1536, 1024))

            destination, errors = stage_built_in_output(root, image_id="demo-k001", source=source)

            expected = root / "output" / "imagegen" / "rebuild-demo-k001" / "demo-k001.webp"
            self.assertEqual([], errors)
            self.assertEqual(expected, destination)
            self.assertEqual(source.read_bytes(), expected.read_bytes())

    def test_stage_built_in_output_rejects_non_webp_source(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue = root / "tmp" / "imagegen" / "gpt-image2-rebuild-demo-k001.jsonl"
            queue.parent.mkdir(parents=True)
            queue.write_text(json.dumps({"out": "demo-k001.webp", "prompt": "demo"}) + "\n", encoding="utf-8")
            source = root / "generated.png"
            source.write_bytes(b"not a webp")

            destination, errors = stage_built_in_output(root, image_id="demo-k001", source=source)

            self.assertIsNone(destination)
            self.assertTrue(any("source must already be .webp" in error for error in errors))
            self.assertFalse((root / "output" / "imagegen" / "rebuild-demo-k001" / "demo-k001.webp").exists())

    def test_stage_built_in_output_rejects_wrong_dimensions(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue = root / "tmp" / "imagegen" / "gpt-image2-rebuild-demo-k001.jsonl"
            queue.parent.mkdir(parents=True)
            queue.write_text(json.dumps({"out": "demo-k001.webp", "prompt": "demo"}) + "\n", encoding="utf-8")
            source = root / "generated.webp"
            source.write_bytes(self._fake_vp8x_webp(1024, 1024))

            destination, errors = stage_built_in_output(root, image_id="demo-k001", source=source)

            self.assertIsNone(destination)
            self.assertEqual(1, len(errors))
            self.assertIn("expected 1536x1024", errors[0])

    def test_single_staged_item_check_accepts_valid_webp(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_rebuild_fixture(root, "demo-k001", 1536, 1024)

            errors = validate_staged_rebuild_item(root, image_id="demo-k001")

            self.assertEqual([], errors)

    def test_single_staged_item_check_reports_missing_image(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue = root / "tmp" / "imagegen" / "gpt-image2-rebuild-demo-k001.jsonl"
            queue.parent.mkdir(parents=True)
            queue.write_text(json.dumps({"out": "demo-k001.webp", "prompt": "demo"}) + "\n", encoding="utf-8")

            errors = validate_staged_rebuild_item(root, image_id="demo-k001")

            self.assertEqual(1, len(errors))
            self.assertIn("missing staged output", errors[0])

    def test_staged_rebuild_output_check_accepts_expected_webp_dimensions(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue = root / "tmp" / "imagegen" / "gpt-image2-rebuild-demo-k001.jsonl"
            queue.parent.mkdir(parents=True)
            queue.write_text(json.dumps({"out": "demo-k001.webp"}) + "\n", encoding="utf-8")
            image = root / "output" / "imagegen" / "rebuild-demo-k001" / "demo-k001.webp"
            image.parent.mkdir(parents=True)
            image.write_bytes(self._fake_vp8x_webp(1536, 1024))

            self.assertEqual([], validate_staged_rebuild_outputs(root, [queue]))

    def test_staged_rebuild_output_check_reports_missing_outputs(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue = root / "tmp" / "imagegen" / "gpt-image2-rebuild-demo-k001.jsonl"
            queue.parent.mkdir(parents=True)
            queue.write_text(json.dumps({"out": "demo-k001.webp"}) + "\n", encoding="utf-8")

            errors = validate_staged_rebuild_outputs(root, [queue])

        self.assertEqual(1, len(errors))
        self.assertIn("missing staged output", errors[0])

    def test_staged_rebuild_output_check_reports_wrong_dimensions(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue = root / "tmp" / "imagegen" / "gpt-image2-rebuild-demo-k001.jsonl"
            queue.parent.mkdir(parents=True)
            queue.write_text(json.dumps({"out": "demo-k001.webp"}) + "\n", encoding="utf-8")
            image = root / "output" / "imagegen" / "rebuild-demo-k001" / "demo-k001.webp"
            image.parent.mkdir(parents=True)
            image.write_bytes(self._fake_vp8x_webp(1024, 1024))

            errors = validate_staged_rebuild_outputs(root, [queue])

        self.assertEqual(1, len(errors))
        self.assertIn("expected 1536x1024", errors[0])

    def test_rebuild_review_board_references_local_images_and_required_text(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue = root / "tmp" / "imagegen" / "gpt-image2-rebuild-demo-k001.jsonl"
            queue.parent.mkdir(parents=True)
            prompt = (
                "Required exact visible Chinese text: “标题”, “标签 A”. "
                "Composition: demo. Style: demo. Constraints: Simplified Chinese only."
            )
            queue.write_text(json.dumps({"out": "demo-k001.webp", "prompt": prompt}) + "\n", encoding="utf-8")

            board = write_rebuild_review_board(root, [queue])
            html = board.read_text(encoding="utf-8")

        self.assertIn("../rebuild-demo-k001/demo-k001.webp", html)
        self.assertIn("标题", html)
        self.assertIn("标签 A", html)
        self.assertIn("缺失", html)
        self.assertIn("accepted", html)
        self.assertIn("text and formula checked", html)
        self.assertNotIn("data:image", html)
        self.assertNotIn("base64", html)

    def test_rebuild_status_summarizes_recoverable_progress(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue = root / "tmp" / "imagegen" / "gpt-image2-rebuild-demo-k001-k002.jsonl"
            queue.parent.mkdir(parents=True)
            queue.write_text(
                "\n".join(
                    [
                        json.dumps({"out": "demo-k001.webp"}),
                        json.dumps({"out": "demo-k002.webp"}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            staged = root / "output" / "imagegen" / "rebuild-demo-k001-k002" / "demo-k001.webp"
            staged.parent.mkdir(parents=True)
            staged.write_bytes(self._fake_vp8x_webp(1536, 1024))
            promoted = root / "content" / "images" / "knowledge" / "demo-k001.webp"
            promoted.parent.mkdir(parents=True)
            promoted.write_bytes(self._fake_vp8x_webp(1536, 1024))
            accepted = self._write_accepted_fixture(root, "demo-k001", True)

            statuses, errors, accepted_list_exists = collect_rebuild_batch_status(
                root,
                accepted_path=accepted,
            )

            self.assertEqual([], errors)
            self.assertTrue(accepted_list_exists)
            self.assertEqual(1, len(statuses))
            self.assertEqual(2, statuses[0].total)
            self.assertEqual(1, statuses[0].staged)
            self.assertEqual(1, statuses[0].missing)
            self.assertEqual(1, statuses[0].accepted)
            self.assertEqual(1, statuses[0].site_files)

            buffer = StringIO()
            with redirect_stdout(buffer):
                print_rebuild_status(statuses, accepted_list_exists=accepted_list_exists, limit=1)

            output = buffer.getvalue()
            self.assertIn("missing_staged=1", output)
            self.assertIn("accepted=1", output)
            self.assertIn("site_files=1", output)
            self.assertIn("next_generation_batch=tmp/imagegen/gpt-image2-rebuild-demo-k001-k002.jsonl", output)

    def test_promote_accepted_rebuilds_dry_run_does_not_write_final_image(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_rebuild_fixture(root, "demo-k001", 1536, 1024)
            accepted = self._write_accepted_fixture(root, "demo-k001", True)

            actions, errors = promote_accepted_rebuilds(root, accepted_path=accepted, dry_run=True)

            self.assertEqual([], errors)
            self.assertEqual(1, len(actions))
            self.assertFalse((root / "content" / "images" / "knowledge" / "demo-k001.webp").exists())

    def test_promote_accepted_rebuilds_ignores_unaccepted_items(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_rebuild_fixture(root, "demo-k001", 1536, 1024)
            accepted = self._write_accepted_fixture(root, "demo-k001", False)

            actions, errors = promote_accepted_rebuilds(root, accepted_path=accepted, dry_run=False)

            self.assertEqual([], errors)
            self.assertEqual([], actions)
            self.assertFalse((root / "content" / "images" / "knowledge" / "demo-k001.webp").exists())

    def test_promote_accepted_rebuilds_rejects_wrong_dimensions(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_rebuild_fixture(root, "demo-k001", 1024, 1024)
            accepted = self._write_accepted_fixture(root, "demo-k001", True)

            actions, errors = promote_accepted_rebuilds(root, accepted_path=accepted, dry_run=False)

            self.assertEqual([], actions)
            self.assertEqual(1, len(errors))
            self.assertIn("expected 1536x1024", errors[0])
            self.assertFalse((root / "content" / "images" / "knowledge" / "demo-k001.webp").exists())

    def test_promote_accepted_rebuilds_copies_reviewed_valid_image(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_rebuild_fixture(root, "demo-k001", 1536, 1024)
            accepted = self._write_accepted_fixture(root, "demo-k001", True)

            actions, errors = promote_accepted_rebuilds(root, accepted_path=accepted, dry_run=False)

            destination = root / "content" / "images" / "knowledge" / "demo-k001.webp"
            self.assertEqual([], errors)
            self.assertEqual(1, len(actions))
            self.assertTrue(destination.exists())
            self.assertEqual(self._fake_vp8x_webp(1536, 1024), destination.read_bytes())

    def test_promote_accepted_rebuilds_can_target_one_accepted_image(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_rebuild_fixture(root, "demo-k001", 1536, 1024)
            self._write_rebuild_fixture(root, "demo-k002", 1536, 1024)
            accepted = root / "tmp" / "imagegen" / "accepted.jsonl"
            accepted.write_text(
                "\n".join(
                    [
                        json.dumps({"id": "demo-k001", "accepted": True}, ensure_ascii=False),
                        json.dumps({"id": "demo-k002", "accepted": True}, ensure_ascii=False),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            actions, errors = promote_accepted_rebuilds(
                root,
                accepted_path=accepted,
                dry_run=False,
                image_id="demo-k002",
            )

            self.assertEqual([], errors)
            self.assertEqual(["demo-k002"], [action[0] for action in actions])
            self.assertFalse((root / "content" / "images" / "knowledge" / "demo-k001.webp").exists())
            self.assertTrue((root / "content" / "images" / "knowledge" / "demo-k002.webp").exists())

    def test_promote_accepted_rebuilds_rejects_unaccepted_target_image(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_rebuild_fixture(root, "demo-k001", 1536, 1024)
            accepted = self._write_accepted_fixture(root, "demo-k001", False)

            actions, errors = promote_accepted_rebuilds(
                root,
                accepted_path=accepted,
                dry_run=True,
                image_id="demo-k001",
            )

            self.assertEqual([], actions)
            self.assertEqual(1, len(errors))
            self.assertIn("not marked accepted", errors[0])

    def test_build_injects_existing_knowledge_figure_after_matching_heading(self) -> None:
        entry = {
            "id": "demo-k001",
            "source": "content/demo.md",
            "ordinal": 1,
            "title": "演示知识点",
            "image": "content/images/knowledge/demo-k001.webp",
            "alt": "知识点插图：演示知识点",
            "model": "gpt-image-2",
        }
        md_text = "## 演示知识点\n\n正文\n\n### 第二个知识点\n"

        injected = inject_knowledge_illustrations(
            md_text,
            "demo.md",
            {("content/demo.md", 1): entry},
            image_exists=lambda _image: True,
        )

        self.assertIn('class="knowledge-figure"', injected)
        self.assertIn('data-knowledge-id="demo-k001"', injected)
        self.assertIn('src="content/images/knowledge/demo-k001.webp"', injected)
        self.assertEqual(1, injected.count('class="knowledge-figure"'))

    def test_styles_define_knowledge_figure_card(self) -> None:
        css = (ROOT / "assets" / "style.css").read_text(encoding="utf-8")

        self.assertIn(".knowledge-figure", css)
        self.assertIn(".knowledge-figure img", css)
        self.assertIn(".knowledge-figure figcaption", css)

    @staticmethod
    def _fake_vp8x_webp(width: int, height: int) -> bytes:
        canvas = (
            b"\x00\x00\x00\x00"
            + (width - 1).to_bytes(3, "little")
            + (height - 1).to_bytes(3, "little")
        )
        body = b"WEBP" + b"VP8X" + len(canvas).to_bytes(4, "little") + canvas
        return b"RIFF" + len(body).to_bytes(4, "little") + body

    def _write_rebuild_fixture(self, root: Path, image_id: str, width: int, height: int) -> None:
        queue = root / "tmp" / "imagegen" / f"gpt-image2-rebuild-{image_id}.jsonl"
        queue.parent.mkdir(parents=True, exist_ok=True)
        queue.write_text(json.dumps({"out": f"{image_id}.webp"}) + "\n", encoding="utf-8")
        image = root / "output" / "imagegen" / f"rebuild-{image_id}" / f"{image_id}.webp"
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(self._fake_vp8x_webp(width, height))

    @staticmethod
    def _write_accepted_fixture(root: Path, image_id: str, accepted: bool) -> Path:
        path = root / "tmp" / "imagegen" / "accepted.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"id": image_id, "accepted": accepted}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return path


if __name__ == "__main__":
    unittest.main()
