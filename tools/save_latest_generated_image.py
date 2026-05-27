from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


GENERATED_BASE = Path.home() / ".codex/generated_images"
OUTPUT_ROOT = Path("content/images/knowledge")


def _latest_png(generated_root: Path | None = None) -> Path:
    search_root = generated_root or GENERATED_BASE
    pattern = "*.png" if generated_root else "*/*.png"
    pngs = list(search_root.glob(pattern))
    if not pngs:
        raise SystemExit(f"No generated PNG files found in {search_root}")
    return max(pngs, key=lambda path: path.stat().st_mtime)


def save_latest(point_id: str, *, generated_root: Path | None = None) -> Path:
    latest = _latest_png(generated_root)
    out = OUTPUT_ROOT / f"{point_id}.webp"
    out.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(latest) as img:
        img.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
        img.save(out, "WEBP", quality=82, method=6)
    print(latest)
    print(out)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Save the latest Codex-generated PNG as a knowledge WebP.")
    parser.add_argument("point_id")
    parser.add_argument(
        "--generated-root",
        type=Path,
        help="Optional specific ~/.codex/generated_images/<thread-id> directory. Defaults to the newest PNG under all generated_images threads.",
    )
    args = parser.parse_args()
    save_latest(args.point_id, generated_root=args.generated_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
