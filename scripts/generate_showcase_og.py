"""Generate the 1200×630 social card used by the public showcase.

The output is deterministic and intentionally uses the same warm paper,
coral accent, grid, and system-path language as the homepage.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "og-os-review.png"
WIDTH, HEIGHT = 1200, 630


def first_font(candidates: list[str], size: int, index: int = 0) -> ImageFont.FreeTypeFont:
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size, index=index)
    raise RuntimeError("No CJK font found. Install Noto Sans/Serif CJK or run on macOS.")


SANS_CANDIDATES = [
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
]
SERIF_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSerifCJK-Regular.ttc",
]


def draw_card() -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), "#faf6f0")
    draw = ImageDraw.Draw(image)
    ink = "#1a1a1a"
    muted = "#6b6862"
    coral = "#c4452d"
    rule = "#d8d0c6"
    surface = "#ffffff"

    sans_22 = first_font(SANS_CANDIDATES, 22)
    sans_26 = first_font(SANS_CANDIDATES, 26)
    sans_24 = first_font(SANS_CANDIDATES, 24)
    serif_74 = first_font(SERIF_CANDIDATES, 74)

    for x in range(40, WIDTH, 40):
        draw.line((x, 0, x, HEIGHT), fill="#eee8df", width=1)
    for y in range(40, HEIGHT, 40):
        draw.line((0, y, WIDTH, y), fill="#eee8df", width=1)

    draw.rounded_rectangle((54, 44, 1146, 586), radius=14, fill=surface, outline=rule, width=2)
    draw.rectangle((54, 44, 72, 586), fill=coral)
    draw.text((108, 82), "JASON / PRODUCT SYSTEMS", font=sans_22, fill=coral)
    draw.text((854, 82), "HUST EIC · OS REVIEW", font=sans_22, fill=muted)
    draw.line((108, 126, 1092, 126), fill=rule, width=2)

    draw.text((108, 176), "操作系统复习，", font=serif_74, fill=ink)
    draw.text((108, 262), "做成一套学习系统", font=serif_74, fill=ink)
    draw.text(
        (112, 374),
        "概念阅读、引导实践与考前复核，沿同一条可重建路径推进。",
        font=sans_26,
        fill=muted,
    )

    paths = [("01", "理解 / UNDERSTAND"), ("02", "实践 / PRACTICE"), ("03", "复核 / RECALL")]
    x = 108
    for number, label in paths:
        draw.rounded_rectangle((x, 452, x + 286, 526), radius=8, fill="#f1ece4", outline=rule)
        draw.text((x + 18, 470), number, font=sans_22, fill=coral)
        draw.text((x + 66, 468), label, font=sans_24, fill=ink)
        x += 316

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, "PNG", optimize=True)
    print(f"generated {OUTPUT.relative_to(ROOT)} ({WIDTH}x{HEIGHT})")


if __name__ == "__main__":
    draw_card()
