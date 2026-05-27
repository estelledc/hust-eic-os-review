from __future__ import annotations

import argparse
import os
import json
import re
import shutil
from dataclasses import asdict, dataclass
from html import escape
from pathlib import Path
from typing import Iterable


MANIFEST_PATH = Path("content/knowledge-illustrations.json")
OUTPUT_DIR = Path("content/images/knowledge")
STAGING_DIR = Path("output/imagegen/knowledge-illustrations")
REVIEW_BOARD_PATH = Path("output/imagegen/rebuild-review/index.html")
ACCEPTED_REBUILD_PATH = Path("tmp/imagegen/gpt-image2-rebuild-accepted.jsonl")
JSONL_DIR = Path("tmp/imagegen")
JSONL_BASENAME = "knowledge-illustrations"
MISSING_JSONL_BASENAME = "knowledge-illustrations-missing"
REBUILD_JSONL_PREFIX = "gpt-image2-rebuild-"
MODEL = "gpt-image-2"
USE_CASE = "scientific-educational"
SIZE = "1536x1024"
QUALITY = "high"
OUTPUT_FORMAT = "webp"
BATCH_SIZE = 500
PROMPT_VERSION = "text-v2"
REQUIRES_IN_IMAGE_TEXT = True
EXPECTED_WIDTH, EXPECTED_HEIGHT = (int(part) for part in SIZE.split("x", 1))
MAX_REBUILD_VISIBLE_LABELS = 8
MIN_REBUILD_VISIBLE_LABELS = 4
MAX_REBUILD_LABEL_CHARS = 34
MAX_REBUILD_VISIBLE_CHARS = 130
REBUILD_REQUIRED_QUALITY_TERMS = ("infographic", "diagram")

HEADING_RE = re.compile(r"^(#{2,4})\s+(.+?)\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")

SOURCE_TO_PAGE = {
    "ch1.md": "ch1",
    "ch2.md": "ch2",
    "ch3-part1.md": "ch3",
    "ch3-part2.md": "ch3",
    "ch4.md": "ch4",
    "ch5.md": "ch5",
    "homework.md": "homework",
    "practice.md": "practice",
    "review.md": "review",
    "tutorial-1.md": "tutorial-1",
    "tutorial-2.md": "tutorial-2",
    "tutorial-3.md": "tutorial-3",
}


@dataclass(frozen=True)
class KnowledgePoint:
    id: str
    source: str
    page_slug: str
    ordinal: int
    line: int
    level: int
    title: str
    context: str
    image: str
    alt: str
    model: str
    prompt_version: str
    requires_in_image_text: bool
    prompt: str


@dataclass(frozen=True)
class RebuildBatchStatus:
    input: str
    out_dir: str
    ids: tuple[str, ...]
    total: int
    staged: int
    missing: int
    accepted: int
    site_files: int


@dataclass(frozen=True)
class RebuildPromptItem:
    image_id: str
    queue: str
    line: int
    staged_output: str
    prompt: str


def _content_files(root: Path) -> list[Path]:
    return sorted((root / "content").glob("*.md"))


def _source_rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _source_slug(path: Path) -> str:
    return re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-")


def _clean_title(raw: str) -> str:
    title = raw.strip()
    title = re.sub(r"\{#[^}]+\}\s*$", "", title).strip()
    title = title.replace("**", "").replace("__", "")
    title = title.replace("`", "")
    return title


def _plain_text(raw: str) -> str:
    text = raw.strip()
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = text.replace("**", "").replace("__", "")
    text = text.replace("|", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _context_after_heading(lines: list[str], start_index: int) -> str:
    chunks: list[str] = []
    in_fence = False
    for line in lines[start_index + 1 :]:
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if HEADING_RE.match(line):
            break
        clean = _plain_text(line)
        if not clean or clean in {"---"}:
            continue
        chunks.append(clean)
        if len(" ".join(chunks)) >= 420 or len(chunks) >= 5:
            break
    context = " ".join(chunks)
    return context[:520]


def _iter_headings(path: Path, root: Path) -> Iterable[tuple[int, int, str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    in_fence = False
    for index, line in enumerate(lines):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING_RE.match(line)
        if not match:
            continue
        level = len(match.group(1))
        title = _clean_title(match.group(2))
        context = _context_after_heading(lines, index)
        yield index + 1, level, title, context


def build_prompt(title: str, context: str) -> str:
    context_line = context if context else "This section title is the complete available context."
    return "\n".join(
        [
            "Use case: scientific-educational",
            "Asset type: web illustration for an operating systems study note",
            f'Primary request: Create one original educational illustration for the knowledge point "{title}".',
            f"Context from notes: {context_line}",
            "Scene/backdrop: clean desktop study-note composition with abstract CPU, memory, process, device, lock, queue, file, or network elements chosen to match the concept.",
            "Subject: visualize the operating-system idea as a clear conceptual diagram or metaphor, not as a literal textbook page.",
            "Style/medium: cohesive polished raster illustration, flat-isometric educational style, crisp geometry, soft neutral background, restrained blue teal and amber accents.",
            "Composition/framing: landscape 3:2, one central idea, generous margins, high contrast, readable when displayed around 720px wide.",
            f'In-image text: include a clear Simplified Chinese title "{title}" and 2-4 short Chinese explanatory callouts based on the context. Keep text large, sparse, and readable.',
            "Text accuracy: prefer short labels and plain Chinese phrases; do not invent formulas, numbers, brands, or source citations.",
            "Constraints: accurate computer-science learning visual, no logos, no brand names, no screenshots, no textbook scans, no watermark.",
            "Avoid: decorative gradients as the main subject, photorealistic people, clutter, memes, unrelated classroom scenes, tiny unreadable UI writing.",
        ]
    )


def extract_knowledge_points(root: Path | str = Path.cwd()) -> list[KnowledgePoint]:
    root = Path(root)
    points: list[KnowledgePoint] = []
    for source_path in _content_files(root):
        source_name = source_path.name
        source_rel = _source_rel(source_path, root)
        page_slug = SOURCE_TO_PAGE.get(source_name, source_path.stem)
        slug = _source_slug(source_path)
        ordinal = 0
        for line, level, title, context in _iter_headings(source_path, root):
            ordinal += 1
            point_id = f"{slug}-k{ordinal:03d}"
            image = OUTPUT_DIR / f"{point_id}.webp"
            prompt = build_prompt(title, context)
            points.append(
                KnowledgePoint(
                    id=point_id,
                    source=source_rel,
                    page_slug=page_slug,
                    ordinal=ordinal,
                    line=line,
                    level=level,
                    title=title,
                    context=context,
                    image=image.as_posix(),
                    alt=f"知识点插图：{title}",
                    model=MODEL,
                    prompt_version=PROMPT_VERSION,
                    requires_in_image_text=REQUIRES_IN_IMAGE_TEXT,
                    prompt=prompt,
                )
            )
    return points


def build_manifest(root: Path | str = Path.cwd()) -> dict:
    entries = [asdict(point) for point in extract_knowledge_points(root)]
    return {
        "schema_version": 1,
        "model": MODEL,
        "use_case": USE_CASE,
        "size": SIZE,
        "quality": QUALITY,
        "output_format": OUTPUT_FORMAT,
        "prompt_version": PROMPT_VERSION,
        "requires_in_image_text": REQUIRES_IN_IMAGE_TEXT,
        "output_dir": OUTPUT_DIR.as_posix(),
        "entries": entries,
    }


def write_manifest(root: Path | str = Path.cwd()) -> dict:
    root = Path(root)
    manifest = build_manifest(root)
    out = root / MANIFEST_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def _jsonl_paths(root: Path, total: int) -> list[Path]:
    count = max(1, (total + BATCH_SIZE - 1) // BATCH_SIZE)
    return [root / JSONL_DIR / f"{JSONL_BASENAME}-{index:03d}.jsonl" for index in range(1, count + 1)]


def rebuild_jsonl_paths(root: Path | str = Path.cwd()) -> list[Path]:
    root = Path(root)
    accepted = (root / ACCEPTED_REBUILD_PATH).resolve()
    return [
        path
        for path in sorted((root / JSONL_DIR).glob(f"{REBUILD_JSONL_PREFIX}*.jsonl"))
        if path.resolve() != accepted
    ]


def rebuild_output_dir(path: Path) -> Path:
    stem = path.name.removeprefix(REBUILD_JSONL_PREFIX).removesuffix(".jsonl")
    return Path("output/imagegen") / f"rebuild-{stem}"


def _read_uint24_le(data: bytes) -> int:
    return data[0] | (data[1] << 8) | (data[2] << 16)


def read_webp_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if len(data) < 30 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise ValueError("not a WebP RIFF container")

    offset = 12
    while offset + 8 <= len(data):
        chunk_type = data[offset : offset + 4]
        chunk_size = int.from_bytes(data[offset + 4 : offset + 8], "little")
        chunk_start = offset + 8
        chunk_end = chunk_start + chunk_size
        if chunk_end > len(data):
            raise ValueError(f"truncated {chunk_type.decode('ascii', errors='replace')} chunk")
        chunk = data[chunk_start:chunk_end]

        if chunk_type == b"VP8X":
            if len(chunk) < 10:
                raise ValueError("truncated VP8X chunk")
            return _read_uint24_le(chunk[4:7]) + 1, _read_uint24_le(chunk[7:10]) + 1
        if chunk_type == b"VP8L":
            if len(chunk) < 5 or chunk[0] != 0x2F:
                raise ValueError("invalid VP8L chunk")
            width = 1 + (((chunk[2] & 0x3F) << 8) | chunk[1])
            height = 1 + (((chunk[4] & 0x0F) << 10) | (chunk[3] << 2) | ((chunk[2] & 0xC0) >> 6))
            return width, height
        if chunk_type == b"VP8 ":
            if len(chunk) < 10 or chunk[3:6] != b"\x9d\x01\x2a":
                raise ValueError("invalid VP8 chunk")
            width = int.from_bytes(chunk[6:8], "little") & 0x3FFF
            height = int.from_bytes(chunk[8:10], "little") & 0x3FFF
            return width, height

        offset = chunk_end + (chunk_size % 2)

    raise ValueError("missing WebP image chunk")


def write_jsonl_batches(root: Path | str = Path.cwd(), manifest: dict | None = None) -> list[Path]:
    root = Path(root)
    manifest = manifest or build_manifest(root)
    entries = manifest["entries"]
    paths = _jsonl_paths(root, len(entries))
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    for batch_index, path in enumerate(paths):
        start = batch_index * BATCH_SIZE
        batch = entries[start : start + BATCH_SIZE]
        lines = []
        for entry in batch:
            lines.append(
                json.dumps(
                    {
                        "prompt": entry["prompt"],
                        "model": MODEL,
                        "size": SIZE,
                        "quality": QUALITY,
                        "output_format": OUTPUT_FORMAT,
                        "out": Path(entry["image"]).name,
                    },
                    ensure_ascii=False,
                )
            )
        path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return paths


def _entry_has_image(root: Path, entry: dict) -> bool:
    image = entry.get("image")
    return bool(image) and (root / str(image)).exists()


def write_missing_jsonl_batches(
    root: Path | str = Path.cwd(),
    manifest: dict | None = None,
    *,
    limit: int | None = None,
) -> list[Path]:
    root = Path(root)
    manifest = manifest or build_manifest(root)
    missing_entries = [entry for entry in manifest["entries"] if not _entry_has_image(root, entry)]
    if limit is not None:
        missing_entries = missing_entries[:limit]
    count = max(1, (len(missing_entries) + BATCH_SIZE - 1) // BATCH_SIZE)
    paths = [root / JSONL_DIR / f"{MISSING_JSONL_BASENAME}-{index:03d}.jsonl" for index in range(1, count + 1)]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    for batch_index, path in enumerate(paths):
        start = batch_index * BATCH_SIZE
        batch = missing_entries[start : start + BATCH_SIZE]
        lines = []
        for entry in batch:
            lines.append(
                json.dumps(
                    {
                        "prompt": entry["prompt"],
                        "model": MODEL,
                        "size": SIZE,
                        "quality": QUALITY,
                        "output_format": OUTPUT_FORMAT,
                        "out": Path(entry["image"]).name,
                    },
                    ensure_ascii=False,
                )
            )
        path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return paths


def validate_manifest(root: Path | str = Path.cwd(), *, require_images: bool = False) -> list[str]:
    root = Path(root)
    errors: list[str] = []
    expected = {point.id: point for point in extract_knowledge_points(root)}
    manifest_path = root / MANIFEST_PATH
    if not manifest_path.exists():
        return [f"missing manifest: {MANIFEST_PATH}"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("quality") != QUALITY:
        errors.append(f"manifest quality must be {QUALITY}")
    if manifest.get("prompt_version") != PROMPT_VERSION:
        errors.append(f"manifest prompt_version must be {PROMPT_VERSION}")
    if manifest.get("requires_in_image_text") is not REQUIRES_IN_IMAGE_TEXT:
        errors.append("manifest requires_in_image_text must be true")
    entries = manifest.get("entries", [])
    actual = {entry.get("id"): entry for entry in entries}
    if set(expected) != set(actual):
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        errors.append(f"manifest coverage mismatch: missing={len(missing)} extra={len(extra)}")
    for entry in entries:
        image = entry.get("image", "")
        prompt = entry.get("prompt", "")
        if entry.get("model") != MODEL:
            errors.append(f"{entry.get('id')}: model must be {MODEL}")
        if entry.get("prompt_version") != PROMPT_VERSION:
            errors.append(f"{entry.get('id')}: prompt_version must be {PROMPT_VERSION}")
        if entry.get("requires_in_image_text") is not REQUIRES_IN_IMAGE_TEXT:
            errors.append(f"{entry.get('id')}: requires_in_image_text must be true")
        if "In-image text:" not in prompt:
            errors.append(f"{entry.get('id')}: prompt must require in-image text")
        if "No embedded text" in prompt or "no labels" in prompt or "no Chinese characters" in prompt:
            errors.append(f"{entry.get('id')}: prompt contains old no-text constraint")
        if not str(image).startswith(f"{OUTPUT_DIR.as_posix()}/") or not str(image).endswith(f".{OUTPUT_FORMAT}"):
            errors.append(f"{entry.get('id')}: invalid image path {image}")
        if require_images and not (root / image).exists():
            errors.append(f"{entry.get('id')}: missing image {image}")
    return errors


def extract_required_visible_text(prompt: str) -> list[str]:
    marker = "Required exact visible Chinese text:"
    if marker not in prompt:
        return []
    text_block = prompt.split(marker, 1)[1].split("Composition:", 1)[0]
    return re.findall(r"“([^”]+)”", text_block)


def validate_rebuild_queue(root: Path | str = Path.cwd()) -> list[str]:
    root = Path(root)
    errors: list[str] = []
    manifest_path = root / MANIFEST_PATH
    if not manifest_path.exists():
        return [f"missing manifest: {MANIFEST_PATH}"]

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_ids = {entry["id"] for entry in manifest.get("entries", [])}
    queue_paths = rebuild_jsonl_paths(root)
    if not queue_paths:
        return [f"missing rebuild queue files: {JSONL_DIR}/{REBUILD_JSONL_PREFIX}*.jsonl"]

    seen: dict[str, str] = {}
    for path in queue_paths:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            location = f"{path.relative_to(root)}:{line_number}"
            try:
                item = json.loads(line)
            except json.JSONDecodeError as error:
                errors.append(f"{location}: invalid JSONL: {error}")
                continue

            out = item.get("out")
            prompt = item.get("prompt")
            if not isinstance(out, str) or not out.endswith(f".{OUTPUT_FORMAT}"):
                errors.append(f"{location}: out must be a .{OUTPUT_FORMAT} file")
                continue
            image_id = Path(out).stem
            if image_id in seen:
                errors.append(f"{location}: duplicate image id {image_id}; first seen at {seen[image_id]}")
            seen[image_id] = location

            if not isinstance(prompt, str) or not prompt.strip():
                errors.append(f"{location}: prompt must be a non-empty string")
                continue
            for required in [
                "Required exact visible Chinese text:",
                "Composition:",
                "Style:",
                "Constraints:",
                "Simplified Chinese",
            ]:
                if required not in prompt:
                    errors.append(f"{location}: prompt missing {required}")
            prompt_lower = prompt.lower()
            for term in REBUILD_REQUIRED_QUALITY_TERMS:
                if term not in prompt_lower:
                    errors.append(f"{location}: prompt must specify {term} format")
            if "No embedded text" in prompt or "no labels" in prompt or "no Chinese characters" in prompt:
                errors.append(f"{location}: prompt contains old no-text constraint")

            visible = extract_required_visible_text(prompt)
            if not visible:
                errors.append(f"{location}: prompt must include required visible text labels")
                continue
            if len(visible) < MIN_REBUILD_VISIBLE_LABELS:
                errors.append(
                    f"{location}: too few visible labels: {len(visible)} < {MIN_REBUILD_VISIBLE_LABELS}"
                )
            if len(visible) > MAX_REBUILD_VISIBLE_LABELS:
                errors.append(
                    f"{location}: too many visible labels: {len(visible)} > {MAX_REBUILD_VISIBLE_LABELS}"
                )
            longest = max(len(label) for label in visible)
            if longest > MAX_REBUILD_LABEL_CHARS:
                errors.append(
                    f"{location}: visible label too long: {longest} > {MAX_REBUILD_LABEL_CHARS}"
                )
            total = sum(len(label) for label in visible)
            if total > MAX_REBUILD_VISIBLE_CHARS:
                errors.append(
                    f"{location}: visible text too dense: {total} > {MAX_REBUILD_VISIBLE_CHARS}"
                )

    if set(seen) != expected_ids:
        missing = sorted(expected_ids - set(seen))
        extra = sorted(set(seen) - expected_ids)
        errors.append(f"rebuild queue coverage mismatch: missing={len(missing)} extra={len(extra)}")
        if missing:
            errors.append(f"missing rebuild sample: {', '.join(missing[:10])}")
        if extra:
            errors.append(f"extra rebuild sample: {', '.join(extra[:10])}")
    return errors


def validate_staged_rebuild_outputs(
    root: Path | str = Path.cwd(),
    jsonl_paths: list[Path] | None = None,
) -> list[str]:
    root = Path(root)
    errors: list[str] = []
    paths = jsonl_paths if jsonl_paths is not None else rebuild_jsonl_paths(root)
    for path in paths:
        path = Path(path)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            errors.append(f"missing rebuild queue file: {path}")
            continue

        out_dir = root / rebuild_output_dir(path)
        for line_number, line in enumerate(lines, 1):
            location = f"{path.relative_to(root) if path.is_relative_to(root) else path}:{line_number}"
            try:
                item = json.loads(line)
            except json.JSONDecodeError as error:
                errors.append(f"{location}: invalid JSONL: {error}")
                continue
            out = item.get("out")
            if not isinstance(out, str):
                errors.append(f"{location}: missing output file name")
                continue

            image_path = out_dir / out
            if not image_path.exists():
                errors.append(f"{location}: missing staged output {image_path.relative_to(root)}")
                continue
            if image_path.suffix.lower() != f".{OUTPUT_FORMAT}":
                errors.append(f"{location}: staged output must be .{OUTPUT_FORMAT}: {image_path}")
                continue
            try:
                width, height = read_webp_dimensions(image_path)
            except ValueError as error:
                errors.append(f"{location}: invalid staged WebP {image_path.relative_to(root)}: {error}")
                continue
            if (width, height) != (EXPECTED_WIDTH, EXPECTED_HEIGHT):
                errors.append(
                    f"{location}: staged output has {width}x{height}, expected {EXPECTED_WIDTH}x{EXPECTED_HEIGHT}"
                )
    return errors


def collect_rebuild_batch_status(
    root: Path | str = Path.cwd(),
    *,
    accepted_path: Path | None = None,
) -> tuple[list[RebuildBatchStatus], list[str], bool]:
    root = Path(root)
    accepted_file = root / (accepted_path or ACCEPTED_REBUILD_PATH)
    accepted_list_exists = accepted_file.exists()
    accepted_ids: set[str] = set()
    errors: list[str] = []

    if accepted_list_exists:
        accepted, accepted_errors = read_accepted_rebuild_ids(root, accepted_path)
        accepted_ids = set(accepted)
        errors.extend(accepted_errors)

    statuses: list[RebuildBatchStatus] = []
    for path in rebuild_jsonl_paths(root):
        out_dir = root / rebuild_output_dir(path)
        ids: list[str] = []
        staged = 0
        site_files = 0
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            try:
                item = json.loads(line)
            except json.JSONDecodeError as error:
                errors.append(f"{_location(path, root, line_number)}: invalid JSONL: {error}")
                continue
            out = item.get("out")
            if not isinstance(out, str):
                errors.append(f"{_location(path, root, line_number)}: missing output file name")
                continue
            image_id = Path(out).stem
            ids.append(image_id)
            if (out_dir / out).exists():
                staged += 1
            if (root / OUTPUT_DIR / f"{image_id}.{OUTPUT_FORMAT}").exists():
                site_files += 1

        statuses.append(
            RebuildBatchStatus(
                input=path.relative_to(root).as_posix(),
                out_dir=rebuild_output_dir(path).as_posix(),
                ids=tuple(ids),
                total=len(ids),
                staged=staged,
                missing=len(ids) - staged,
                accepted=sum(1 for image_id in ids if image_id in accepted_ids),
                site_files=site_files,
            )
        )

    return statuses, errors, accepted_list_exists


def rebuild_path_has_missing_staged_output(root: Path | str, path: Path) -> bool:
    root = Path(root)
    path = Path(path)
    out_dir = root / rebuild_output_dir(path)
    for line in path.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        out = item.get("out")
        if isinstance(out, str) and not (out_dir / out).exists():
            return True
    return False


def select_rebuild_paths_missing_staged(
    root: Path | str,
    jsonl_paths: list[Path],
) -> list[Path]:
    return [path for path in jsonl_paths if rebuild_path_has_missing_staged_output(root, path)]


def select_rebuild_items_missing_staged(
    root: Path | str = Path.cwd(),
    *,
    limit: int | None = None,
) -> list[RebuildPromptItem]:
    root = Path(root)
    items: list[RebuildPromptItem] = []
    for path in rebuild_jsonl_paths(root):
        out_dir = root / rebuild_output_dir(path)
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            item = json.loads(line)
            out = item.get("out")
            prompt = item.get("prompt")
            if not isinstance(out, str) or not isinstance(prompt, str):
                continue
            staged = out_dir / out
            if staged.exists():
                continue
            items.append(
                RebuildPromptItem(
                    image_id=Path(out).stem,
                    queue=path.relative_to(root).as_posix(),
                    line=line_number,
                    staged_output=staged.relative_to(root).as_posix(),
                    prompt=prompt,
                )
            )
            if limit is not None and len(items) >= limit:
                return items
    return items


def _rebuild_output_map(
    root: Path | str = Path.cwd(),
    jsonl_paths: list[Path] | None = None,
) -> dict[str, Path]:
    root = Path(root)
    mapping: dict[str, Path] = {}
    paths = jsonl_paths if jsonl_paths is not None else rebuild_jsonl_paths(root)
    for path in paths:
        path = Path(path)
        out_dir = root / rebuild_output_dir(path)
        for line in path.read_text(encoding="utf-8").splitlines():
            item = json.loads(line)
            out = str(item.get("out", ""))
            if out:
                mapping[Path(out).stem] = out_dir / out
    return mapping


def read_accepted_rebuild_ids(
    root: Path | str = Path.cwd(),
    accepted_path: Path | None = None,
) -> tuple[list[str], list[str]]:
    root = Path(root)
    path = root / (accepted_path or ACCEPTED_REBUILD_PATH)
    if not path.exists():
        return [], [f"missing accepted rebuild list: {path.relative_to(root)}"]

    accepted: list[str] = []
    errors: list[str] = []
    seen: set[str] = set()
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        location = f"{path.relative_to(root)}:{line_number}"
        try:
            item = json.loads(line)
        except json.JSONDecodeError as error:
            errors.append(f"{location}: invalid JSONL: {error}")
            continue
        if item.get("accepted") is not True:
            continue
        image_id = item.get("id") or Path(str(item.get("out", ""))).stem
        if not image_id:
            errors.append(f"{location}: accepted item must include id or out")
            continue
        if image_id in seen:
            errors.append(f"{location}: duplicate accepted id {image_id}")
            continue
        seen.add(str(image_id))
        accepted.append(str(image_id))
    return accepted, errors


def promote_accepted_rebuilds(
    root: Path | str = Path.cwd(),
    *,
    accepted_path: Path | None = None,
    dry_run: bool = True,
    force: bool = False,
    limit: int | None = None,
    image_id: str | None = None,
) -> tuple[list[tuple[str, Path, Path]], list[str]]:
    root = Path(root)
    accepted_ids, errors = read_accepted_rebuild_ids(root, accepted_path)
    if image_id is not None:
        if image_id not in accepted_ids:
            errors.append(f"{image_id}: not marked accepted in {(accepted_path or ACCEPTED_REBUILD_PATH)}")
        accepted_ids = [image_id] if image_id in accepted_ids else []
    if limit is not None:
        accepted_ids = accepted_ids[:limit]
    output_map = _rebuild_output_map(root)
    actions: list[tuple[str, Path, Path]] = []

    for image_id in accepted_ids:
        staged = output_map.get(image_id)
        if staged is None:
            errors.append(f"{image_id}: no staged rebuild queue output")
            continue
        destination = root / OUTPUT_DIR / f"{image_id}.{OUTPUT_FORMAT}"
        if not staged.exists():
            errors.append(f"{image_id}: missing staged output {staged.relative_to(root)}")
            continue
        try:
            width, height = read_webp_dimensions(staged)
        except ValueError as error:
            errors.append(f"{image_id}: invalid staged WebP {staged.relative_to(root)}: {error}")
            continue
        if (width, height) != (EXPECTED_WIDTH, EXPECTED_HEIGHT):
            errors.append(
                f"{image_id}: staged output has {width}x{height}, expected {EXPECTED_WIDTH}x{EXPECTED_HEIGHT}"
            )
            continue
        if destination.exists() and not force:
            errors.append(f"{image_id}: destination exists; pass --force after review to overwrite")
            continue
        actions.append((image_id, staged, destination))

    if errors or dry_run:
        return actions, errors

    for _, staged, destination in actions:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(staged, destination)
    return actions, errors


def stage_built_in_output(
    root: Path | str = Path.cwd(),
    *,
    image_id: str,
    source: Path,
    force: bool = False,
) -> tuple[Path | None, list[str]]:
    root = Path(root)
    errors: list[str] = []
    output_map = _rebuild_output_map(root)
    destination = output_map.get(image_id)
    if destination is None:
        return None, [f"{image_id}: no rebuild queue output"]

    source_path = source if source.is_absolute() else root / source
    if not source_path.exists():
        return None, [f"{image_id}: missing source image {source}"]
    if source_path.suffix.lower() != f".{OUTPUT_FORMAT}":
        errors.append(f"{image_id}: source must already be .{OUTPUT_FORMAT}: {source}")
    try:
        width, height = read_webp_dimensions(source_path)
    except ValueError as error:
        errors.append(f"{image_id}: invalid source WebP {source}: {error}")
    else:
        if (width, height) != (EXPECTED_WIDTH, EXPECTED_HEIGHT):
            errors.append(
                f"{image_id}: source has {width}x{height}, expected {EXPECTED_WIDTH}x{EXPECTED_HEIGHT}"
            )
    if destination.exists() and not force:
        errors.append(f"{image_id}: staged output exists; pass --force to overwrite after review")
    if errors:
        return None, errors

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, destination)
    return destination, []


def validate_staged_rebuild_item(
    root: Path | str = Path.cwd(),
    *,
    image_id: str,
) -> list[str]:
    root = Path(root)
    output_map = _rebuild_output_map(root)
    staged = output_map.get(image_id)
    if staged is None:
        return [f"{image_id}: no rebuild queue output"]
    if not staged.exists():
        return [f"{image_id}: missing staged output {staged.relative_to(root)}"]
    if staged.suffix.lower() != f".{OUTPUT_FORMAT}":
        return [f"{image_id}: staged output must be .{OUTPUT_FORMAT}: {staged.relative_to(root)}"]
    try:
        width, height = read_webp_dimensions(staged)
    except ValueError as error:
        return [f"{image_id}: invalid staged WebP {staged.relative_to(root)}: {error}"]
    if (width, height) != (EXPECTED_WIDTH, EXPECTED_HEIGHT):
        return [
            f"{image_id}: staged output has {width}x{height}, expected {EXPECTED_WIDTH}x{EXPECTED_HEIGHT}"
        ]
    return []


def _location(path: Path, root: Path, line_number: int) -> str:
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    return f"{rel}:{line_number}"


def write_rebuild_review_board(
    root: Path | str = Path.cwd(),
    jsonl_paths: list[Path] | None = None,
) -> Path:
    root = Path(root)
    paths = jsonl_paths if jsonl_paths is not None else rebuild_jsonl_paths(root)
    board_path = root / REVIEW_BOARD_PATH
    board_dir = board_path.parent
    board_dir.mkdir(parents=True, exist_ok=True)

    cards: list[str] = []
    item_count = 0
    missing_count = 0
    for path in paths:
        path = Path(path)
        out_dir = root / rebuild_output_dir(path)
        lines = path.read_text(encoding="utf-8").splitlines()
        for line_number, line in enumerate(lines, 1):
            item = json.loads(line)
            out = str(item.get("out", ""))
            image_id = Path(out).stem
            image_path = out_dir / out
            image_src = Path(os.path.relpath(image_path, board_dir)).as_posix()
            visible = extract_required_visible_text(str(item.get("prompt", "")))
            status = "已生成" if image_path.exists() else "缺失"
            if not image_path.exists():
                missing_count += 1
            item_count += 1
            labels = "\n".join(f"<li>{escape(label)}</li>" for label in visible)
            accepted_jsonl = json.dumps(
                {"id": image_id, "accepted": True, "notes": "text and formula checked"},
                ensure_ascii=False,
            )
            cards.append(
                "\n".join(
                    [
                        '<article class="card">',
                        f'  <div class="meta"><strong>{escape(image_id)}</strong><span>{escape(status)}</span></div>',
                        f'  <img src="{escape(image_src)}" alt="{escape(image_id)} staged rebuild output" loading="lazy">',
                        f'  <p class="path">{escape(image_src)}</p>',
                        '  <h2>必须核对的图中文字</h2>',
                        f"  <ol>{labels}</ol>",
                        "  <h2>验收通过后追加到 accepted JSONL</h2>",
                        f"  <pre>{escape(accepted_jsonl)}</pre>",
                        f'  <p class="source">{escape(_location(path, root, line_number))}</p>',
                        "</article>",
                    ]
                )
            )

    html = "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            "<head>",
            '  <meta charset="utf-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1">',
            "  <title>gpt-image-2 rebuild review board</title>",
            "  <style>",
            "    :root { color-scheme: light; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }",
            "    body { margin: 0; background: #f6f7f9; color: #17202a; }",
            "    header { position: sticky; top: 0; z-index: 1; padding: 18px 24px; background: #ffffff; border-bottom: 1px solid #d9dee7; }",
            "    h1 { margin: 0 0 6px; font-size: 20px; }",
            "    header p { margin: 0; color: #526071; font-size: 14px; }",
            "    main { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 16px; padding: 16px; }",
            "    .card { background: #ffffff; border: 1px solid #d9dee7; border-radius: 8px; padding: 12px; }",
            "    .meta { display: flex; justify-content: space-between; gap: 12px; align-items: center; margin-bottom: 10px; font-size: 14px; }",
            "    .meta span { padding: 2px 8px; border-radius: 999px; background: #eef2f7; color: #334155; }",
            "    img { width: 100%; aspect-ratio: 3 / 2; object-fit: contain; background: #eef2f7; border: 1px solid #d9dee7; border-radius: 6px; }",
            "    .path, .source { color: #64748b; font-size: 12px; word-break: break-all; }",
            "    h2 { margin: 12px 0 8px; font-size: 14px; }",
            "    ol { margin: 0; padding-left: 22px; }",
            "    li { margin: 4px 0; font-size: 14px; line-height: 1.35; }",
            "    pre { margin: 0; padding: 8px; overflow: auto; border-radius: 6px; background: #f8fafc; color: #334155; font-size: 12px; line-height: 1.4; }",
            "  </style>",
            "</head>",
            "<body>",
            "  <header>",
            "    <h1>gpt-image-2 rebuild review board</h1>",
            f"    <p>{item_count} 张待验收；{missing_count} 张 staged 文件缺失。图片仅通过本地相对路径引用，不内嵌图片数据。</p>",
            "  </header>",
            "  <main>",
            *cards,
            "  </main>",
            "</body>",
            "</html>",
        ]
    )
    board_path.write_text(html + "\n", encoding="utf-8")
    return board_path


def print_commands(jsonl_paths: list[Path]) -> None:
    image_gen = '${CODEX_HOME:-$HOME/.codex}/skills/.system/imagegen/scripts/image_gen.py'
    for path in jsonl_paths:
        print(
            "python "
            f'"{image_gen}" generate-batch '
            f"--input {path.as_posix()} "
            f"--out-dir {STAGING_DIR.as_posix()} "
            f"--model {MODEL} --size {SIZE} --quality {QUALITY} "
            f"--output-format {OUTPUT_FORMAT} --no-augment --concurrency 1"
        )


def print_rebuild_commands(jsonl_paths: list[Path], *, dry_run: bool = False) -> None:
    image_gen = '${CODEX_HOME:-$HOME/.codex}/skills/.system/imagegen/scripts/image_gen.py'
    terminal_flag = "--dry-run" if dry_run else "--fail-fast"
    for path in jsonl_paths:
        print(
            "python "
            f'"{image_gen}" generate-batch '
            f"--input {path.as_posix()} "
            f"--out-dir {rebuild_output_dir(path).as_posix()} "
            f"--model {MODEL} --size {SIZE} --quality {QUALITY} "
            f"--output-format {OUTPUT_FORMAT} --no-augment --concurrency 1 "
            f"{terminal_flag}"
        )


def print_rebuild_status(
    statuses: list[RebuildBatchStatus],
    *,
    accepted_list_exists: bool,
    limit: int | None = None,
) -> None:
    total_batches = len(statuses)
    total_entries = sum(status.total for status in statuses)
    total_staged = sum(status.staged for status in statuses)
    total_accepted = sum(status.accepted for status in statuses)
    total_site_files = sum(status.site_files for status in statuses)
    next_generation = next((status for status in statuses if status.missing), None)
    next_review = next(
        (
            status
            for status in statuses
            if status.staged and status.accepted < status.staged
        ),
        None,
    )

    print("gpt-image-2 rebuild status")
    print(f"batches={total_batches}")
    print(f"entries={total_entries}")
    print(f"staged={total_staged}")
    print(f"missing_staged={total_entries - total_staged}")
    print(f"accepted={total_accepted}")
    print(f"site_files={total_site_files}")
    print(f"accepted_list={'present' if accepted_list_exists else 'missing'}")
    if next_generation:
        print(
            "next_generation_batch="
            f"{next_generation.input} -> {next_generation.out_dir} "
            f"({next_generation.missing}/{next_generation.total} missing)"
        )
    else:
        print("next_generation_batch=none")
    if next_review:
        print(
            "next_review_batch="
            f"{next_review.input} -> {next_review.out_dir} "
            f"({next_review.staged - next_review.accepted}/{next_review.staged} staged unaccepted)"
        )
    else:
        print("next_review_batch=none")

    shown = statuses[:limit] if limit is not None else statuses
    if shown:
        print("batch_rows=input|staged|accepted|site_files|ids")
    for status in shown:
        first = status.ids[0] if status.ids else "none"
        last = status.ids[-1] if status.ids else "none"
        print(
            f"{status.input}|{status.staged}/{status.total}|"
            f"{status.accepted}/{status.total}|{status.site_files}/{status.total}|"
            f"{first}..{last}"
        )


def print_builtin_next_prompts(items: list[RebuildPromptItem]) -> None:
    if not items:
        print("No missing staged rebuild prompts.")
        return
    for index, item in enumerate(items, 1):
        print(f"item={index}")
        print(f"id={item.image_id}")
        print(f"queue={item.queue}:{item.line}")
        print(f"staged_output={item.staged_output}")
        print("mode=built-in image_gen one image only; do not batch this into the thread")
        print("after_generation=place a valid 1536x1024 WebP at staged_output, then run check-staged-rebuild")
        print("prompt<<'PROMPT'")
        print(item.prompt)
        print("PROMPT")


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare OS knowledge-point illustration assets.")
    parser.add_argument(
        "command",
        choices=[
            "build",
            "check",
            "check-rebuild",
            "commands",
            "missing",
            "missing-commands",
            "rebuild-commands",
            "rebuild-dry-run-commands",
            "rebuild-pending-commands",
            "rebuild-pending-dry-run-commands",
            "built-in-next-prompt",
            "stage-built-in-output",
            "check-staged-item",
            "check-staged-rebuild",
            "rebuild-status",
            "review-board",
            "promote-accepted",
        ],
    )
    parser.add_argument("--require-images", action="store_true")
    parser.add_argument("--limit", type=int, help="Limit missing JSONL output to the next N missing entries.")
    parser.add_argument("--accepted", type=Path, default=ACCEPTED_REBUILD_PATH)
    parser.add_argument("--image-id", help="Knowledge illustration id for a single staged output operation.")
    parser.add_argument("--source", type=Path, help="Source WebP produced by a single built-in image generation.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    if args.command == "build":
        manifest = write_manifest(root)
        paths = write_jsonl_batches(root, manifest)
        print(f"Wrote {MANIFEST_PATH} with {len(manifest['entries'])} entries.")
        for path in paths:
            print(f"Wrote {path.relative_to(root)}")
        return 0
    if args.command == "check":
        errors = validate_manifest(root, require_images=args.require_images)
        if errors:
            for error in errors:
                print(error)
            return 1
        print("knowledge illustration manifest is valid.")
        return 0
    if args.command == "check-rebuild":
        errors = validate_rebuild_queue(root)
        if errors:
            for error in errors:
                print(error)
            return 1
        print("gpt-image-2 rebuild queue is valid.")
        return 0
    if args.command == "commands":
        manifest = build_manifest(root)
        print_commands(_jsonl_paths(root, len(manifest["entries"])))
        return 0
    if args.command in {
        "rebuild-commands",
        "rebuild-dry-run-commands",
        "rebuild-pending-commands",
        "rebuild-pending-dry-run-commands",
    }:
        errors = validate_rebuild_queue(root)
        if errors:
            for error in errors:
                print(error)
            return 1
        paths = rebuild_jsonl_paths(root)
        if args.command in {"rebuild-pending-commands", "rebuild-pending-dry-run-commands"}:
            paths = select_rebuild_paths_missing_staged(root, paths)
        if args.limit is not None:
            paths = paths[: args.limit]
        print_rebuild_commands(
            paths,
            dry_run=args.command in {"rebuild-dry-run-commands", "rebuild-pending-dry-run-commands"},
        )
        return 0
    if args.command == "built-in-next-prompt":
        errors = validate_rebuild_queue(root)
        if errors:
            for error in errors:
                print(error)
            return 1
        limit = args.limit if args.limit is not None else 1
        print_builtin_next_prompts(select_rebuild_items_missing_staged(root, limit=limit))
        return 0
    if args.command == "stage-built-in-output":
        if not args.image_id:
            print("stage-built-in-output requires --image-id")
            return 1
        if args.source is None:
            print("stage-built-in-output requires --source")
            return 1
        errors = validate_rebuild_queue(root)
        if errors:
            for error in errors:
                print(error)
            return 1
        destination, errors = stage_built_in_output(
            root,
            image_id=args.image_id,
            source=args.source,
            force=args.force,
        )
        if errors:
            for error in errors:
                print(error)
            return 1
        assert destination is not None
        print(f"Staged {args.image_id}: {destination.relative_to(root)}")
        return 0
    if args.command == "check-staged-item":
        if not args.image_id:
            print("check-staged-item requires --image-id")
            return 1
        errors = validate_rebuild_queue(root)
        if errors:
            for error in errors:
                print(error)
            return 1
        errors = validate_staged_rebuild_item(root, image_id=args.image_id)
        if errors:
            for error in errors:
                print(error)
            return 1
        print(f"staged gpt-image-2 rebuild output is valid: {args.image_id}")
        return 0
    if args.command == "check-staged-rebuild":
        errors = validate_rebuild_queue(root)
        paths = rebuild_jsonl_paths(root)
        if args.limit is not None:
            paths = paths[: args.limit]
        errors.extend(validate_staged_rebuild_outputs(root, paths))
        if errors:
            for error in errors:
                print(error)
            return 1
        print("staged gpt-image-2 rebuild outputs are valid.")
        return 0
    if args.command == "rebuild-status":
        errors = validate_rebuild_queue(root)
        statuses, status_errors, accepted_list_exists = collect_rebuild_batch_status(
            root,
            accepted_path=args.accepted,
        )
        errors.extend(status_errors)
        if errors:
            for error in errors:
                print(error)
            return 1
        print_rebuild_status(statuses, accepted_list_exists=accepted_list_exists, limit=args.limit)
        return 0
    if args.command == "review-board":
        errors = validate_rebuild_queue(root)
        if errors:
            for error in errors:
                print(error)
            return 1
        paths = rebuild_jsonl_paths(root)
        if args.limit is not None:
            paths = paths[: args.limit]
        board = write_rebuild_review_board(root, paths)
        print(f"Wrote {board.relative_to(root)}")
        return 0
    if args.command == "promote-accepted":
        actions, errors = promote_accepted_rebuilds(
            root,
            accepted_path=args.accepted,
            dry_run=args.dry_run,
            force=args.force,
            limit=args.limit,
            image_id=args.image_id,
        )
        if errors:
            for error in errors:
                print(error)
            return 1
        verb = "Would promote" if args.dry_run else "Promoted"
        for image_id, staged, destination in actions:
            print(f"{verb} {image_id}: {staged.relative_to(root)} -> {destination.relative_to(root)}")
        if not actions:
            print("No accepted rebuilds to promote.")
        return 0
    if args.command == "missing":
        manifest = build_manifest(root)
        paths = write_missing_jsonl_batches(root, manifest, limit=args.limit)
        missing_count = sum(
            1 for entry in manifest["entries"] if not _entry_has_image(root, entry)
        )
        selected_count = min(missing_count, args.limit) if args.limit is not None else missing_count
        print(f"Wrote missing-image JSONL for {selected_count} of {missing_count} missing entries.")
        for path in paths:
            print(f"Wrote {path.relative_to(root)}")
        return 0
    if args.command == "missing-commands":
        manifest = build_manifest(root)
        paths = write_missing_jsonl_batches(root, manifest, limit=args.limit)
        print_commands(paths)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
