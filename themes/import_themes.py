"""Import all themes from VoltAgent/awesome-design-md.

Parses each theme's DESIGN.md frontmatter and emits:
  themes/themes.css  — one CSS rule block per theme keyed on data-theme
  themes/themes.json — picker metadata (slug, name, description, palette swatch)

Rerun safe; designed to be idempotent.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = Path("/tmp/awesome-design-md/VoltAgent-awesome-design-md-f2d6b17/design-md")
OUT_CSS = ROOT / "themes" / "themes.css"
OUT_JSON = ROOT / "themes" / "themes.json"

FM_RE = re.compile(r"\A---\n(.*?)\n---", re.DOTALL)
LINE_RE = re.compile(r'^\s{2,}([\w.\-]+)\s*:\s*"([^"]+)"\s*$')

def parse_frontmatter(text: str) -> dict:
    m = FM_RE.match(text)
    if not m:
        return {}
    body = m.group(1)
    out: dict = {}
    section = None
    for raw in body.splitlines():
        if raw.startswith("name:"):
            out["name"] = raw.split(":", 1)[1].strip()
        elif raw.startswith("description:"):
            out["description"] = raw.split(":", 1)[1].strip()
        elif raw.startswith("colors:"):
            section = "colors"
            out["colors"] = {}
        elif raw.startswith("typography:") or raw.startswith("spacing:") or raw.startswith("radius:") or raw.startswith("shadows:") or raw.startswith("breakpoints:") or raw.startswith("components:"):
            section = None
        elif section == "colors":
            mm = LINE_RE.match(raw)
            if mm:
                out["colors"][mm.group(1).lower()] = mm.group(2)
    return out

# Schema: pick the first matching token name (case-insensitive) for each css var.
# Fallbacks ensure every theme yields a complete palette.
PICK = {
    "bg":          ["canvas", "canvas-parchment", "background", "bg", "surface", "surface-default", "page", "paper", "off-white"],
    "bg_elev":     ["surface", "surface-pearl", "surface-elev", "surface-elevated", "card", "panel", "surface-default", "tile"],
    "bg_soft":     ["surface-pearl", "surface-tile-1", "muted-soft", "border-light", "panel-soft", "subtle", "tint"],
    "fg":          ["ink", "body", "text", "text-primary", "primary-text", "foreground"],
    "fg_soft":     ["body", "ink-muted-80", "body-strong", "text-secondary", "muted", "muted-strong"],
    "fg_mute":     ["muted", "ink-muted-48", "body-muted", "text-tertiary", "muted-soft"],
    "fg_faint":    ["muted-soft", "body-muted", "muted", "hairline"],
    "accent":      ["primary", "accent", "brand", "highlight", "interactive"],
    "accent_focus":["primary-focus", "primary-active", "primary-on-dark", "accent-hover", "accent-focus", "primary"],
    "accent_fg":   ["on-primary", "on-accent", "primary-on", "on-dark"],
    "border":      ["hairline", "divider", "divider-soft", "border", "border-strong", "stroke"],
    "border_soft": ["divider-soft", "hairline", "border-light", "border", "stroke"],
    "code_bg":     ["surface-pearl", "canvas-parchment", "tile", "surface", "surface-tile-1", "code-bg", "panel"],
    "quote_bg":    ["canvas-parchment", "surface-pearl", "tile", "highlight-soft", "panel"],
}

def hex_to_rgb(hx: str):
    hx = hx.lstrip('#')
    if len(hx) == 3:
        hx = "".join(ch*2 for ch in hx)
    return int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)

def luminance(hx: str) -> float:
    try:
        r, g, b = hex_to_rgb(hx)
    except Exception:
        return 0.5
    def chan(c):
        c /= 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)

def is_dark_palette(colors: dict) -> bool:
    bg = pick(colors, PICK["bg"], "#ffffff")
    return luminance(bg) < 0.5

def pick(colors: dict, candidates: list[str], fallback: str) -> str:
    for c in candidates:
        if c in colors:
            return colors[c]
    # try prefix match (e.g., "primary-500")
    for c in candidates:
        for k, v in colors.items():
            if k.startswith(c + "-") or k.startswith(c + "_"):
                return v
    return fallback

def derive(colors: dict) -> dict:
    is_dark = is_dark_palette(colors)
    default_bg = "#0d1117" if is_dark else "#ffffff"
    default_fg = "#e6e6e6" if is_dark else "#1c1c1e"
    default_accent = "#5aa8ee" if is_dark else "#0f6cbf"
    default_border = "#2a2d33" if is_dark else "#e2e2df"

    bg = pick(colors, PICK["bg"], default_bg)
    fg = pick(colors, PICK["fg"], default_fg)
    accent = pick(colors, PICK["accent"], default_accent)
    border = pick(colors, PICK["border"], default_border)

    # Avoid identical bg/fg fallbacks for monochrome themes:
    if bg.lower() == fg.lower():
        fg = default_fg

    bg_elev = pick(colors, PICK["bg_elev"], bg)
    bg_soft = pick(colors, PICK["bg_soft"], shift_color(bg, 4 if is_dark else -4))
    fg_soft = pick(colors, PICK["fg_soft"], fg)
    fg_mute = pick(colors, PICK["fg_mute"], shift_color(fg, 30 if is_dark else -30))
    fg_faint = pick(colors, PICK["fg_faint"], shift_color(fg, 60 if is_dark else -60))

    accent_focus = pick(colors, PICK["accent_focus"], accent)
    accent_fg = pick(colors, PICK["accent_fg"], "#ffffff" if luminance(accent) < 0.5 else "#000000")
    accent_soft = mix_with_bg(accent, bg, 0.18 if is_dark else 0.86)

    border_soft = pick(colors, PICK["border_soft"], border)
    code_bg = pick(colors, PICK["code_bg"], shift_color(bg, 4 if is_dark else -4))
    quote_bg = pick(colors, PICK["quote_bg"], shift_color(bg, 6 if is_dark else -3))
    quote_bd = accent

    table_stripe = shift_color(bg, 4 if is_dark else -3)
    swatch = [bg, fg, accent, border]

    return {
        "is_dark": is_dark,
        "bg": bg, "bg_elev": bg_elev, "bg_soft": bg_soft,
        "fg": fg, "fg_soft": fg_soft, "fg_mute": fg_mute, "fg_faint": fg_faint,
        "accent": accent, "accent_focus": accent_focus, "accent_fg": accent_fg, "accent_soft": accent_soft,
        "border": border, "border_soft": border_soft,
        "code_bg": code_bg, "quote_bg": quote_bg, "quote_bd": quote_bd,
        "table_stripe": table_stripe,
        "swatch": swatch,
    }

def shift_color(hx: str, amount: int) -> str:
    """Lighten (positive) or darken (negative) hex by amount per channel."""
    try:
        r, g, b = hex_to_rgb(hx)
    except Exception:
        return hx
    r = max(0, min(255, r + amount))
    g = max(0, min(255, g + amount))
    b = max(0, min(255, b + amount))
    return f"#{r:02x}{g:02x}{b:02x}"

def mix_with_bg(fg_hex: str, bg_hex: str, t: float) -> str:
    """Mix fg into bg by ratio t (0..1). t=0.86 means mostly bg."""
    try:
        r1, g1, b1 = hex_to_rgb(fg_hex)
        r2, g2, b2 = hex_to_rgb(bg_hex)
    except Exception:
        return fg_hex
    r = int(r1 * (1 - t) + r2 * t)
    g = int(g1 * (1 - t) + g2 * t)
    b = int(b1 * (1 - t) + b2 * t)
    return f"#{r:02x}{g:02x}{b:02x}"

def make_block(slug: str, vars_: dict) -> str:
    return f"""[data-theme="{slug}"] {{
  --bg: {vars_['bg']};
  --bg-elev: {vars_['bg_elev']};
  --bg-soft: {vars_['bg_soft']};
  --fg: {vars_['fg']};
  --fg-soft: {vars_['fg_soft']};
  --fg-mute: {vars_['fg_mute']};
  --fg-faint: {vars_['fg_faint']};
  --accent: {vars_['accent']};
  --accent-soft: {vars_['accent_soft']};
  --accent-fg: {vars_['accent_fg']};
  --border: {vars_['border']};
  --border-soft: {vars_['border_soft']};
  --code-bg: {vars_['code_bg']};
  --quote-bg: {vars_['quote_bg']};
  --quote-bd: {vars_['quote_bd']};
  --table-stripe: {vars_['table_stripe']};
  color-scheme: {'dark' if vars_['is_dark'] else 'light'};
}}"""

# Manual fallback for themes whose DESIGN.md is prose-only (no YAML colors block).
# Each entry is a flat color map keyed by names that PICK[] knows about.
MANUAL_FALLBACKS: dict[str, dict] = {
    "kraken":      {"canvas": "#ffffff", "ink": "#101114", "body": "#484b5e", "muted": "#686b82", "muted-soft": "#9497a9", "primary": "#7132f5", "primary-focus": "#5b1ecf", "hairline": "#dedee5", "on-primary": "#ffffff"},
    "lamborghini": {"canvas": "#000000", "ink": "#ffffff", "body": "#dddddd", "muted": "#9c9c9c", "muted-soft": "#666666", "primary": "#FFC000", "primary-focus": "#e0a500", "hairline": "#202020", "surface": "#181818", "on-primary": "#000000"},
    "lovable":     {"canvas": "#f7f4ed", "ink": "#1c1c1c", "body": "#3d3d3a", "muted": "#5f5f5d", "muted-soft": "#8e8b82", "primary": "#3b82f6", "primary-focus": "#1d4ed8", "hairline": "#eceae4", "surface": "#fcfbf8", "on-primary": "#ffffff"},
    "mastercard":  {"canvas": "#F3F0EE", "ink": "#141413", "body": "#2B2B2B", "muted": "#565656", "muted-soft": "#9c9c9c", "primary": "#CF4500", "primary-focus": "#9A3A0A", "hairline": "#e3dfdb", "surface": "#ffffff", "on-primary": "#ffffff"},
    "runwayml":    {"canvas": "#0c0c0c", "ink": "#fafafa", "body": "#d4d4d4", "muted": "#9aa1ac", "muted-soft": "#6b7280", "primary": "#ffffff", "primary-focus": "#dadada", "hairline": "#27272a", "surface": "#1a1a1a", "on-primary": "#0c0c0c"},
    "sanity":      {"canvas": "#0b0b0b", "ink": "#ededed", "body": "#b9b9b9", "muted": "#797979", "muted-soft": "#535353", "primary": "#0052ef", "primary-focus": "#55beff", "hairline": "#212121", "surface": "#212121", "on-primary": "#ffffff"},
    "spotify":     {"canvas": "#121212", "ink": "#ffffff", "body": "#d4d4d4", "muted": "#a7a7a7", "muted-soft": "#727272", "primary": "#1db954", "primary-focus": "#1ed760", "hairline": "#272727", "surface": "#181818", "on-primary": "#000000"},
    "starbucks":   {"canvas": "#ffffff", "ink": "#1E3932", "body": "#2b5148", "muted": "#33433d", "muted-soft": "#7d8d88", "primary": "#006241", "primary-focus": "#00754A", "hairline": "#d4e9e2", "surface": "#f1f8f5", "on-primary": "#ffffff"},
    "tesla":       {"canvas": "#ffffff", "ink": "#171A20", "body": "#393C41", "muted": "#5C5E62", "muted-soft": "#8E8E8E", "primary": "#3E6AE1", "primary-focus": "#2754d6", "hairline": "#D0D1D2", "surface": "#F4F4F4", "on-primary": "#ffffff"},
    "theverge":    {"canvas": "#131313", "ink": "#ffffff", "body": "#dcdcdc", "muted": "#9c9c9c", "muted-soft": "#6f6f6f", "primary": "#3cffd0", "primary-focus": "#5200ff", "hairline": "#2d2d2d", "surface": "#1f1f1f", "on-primary": "#131313"},
}

# Pretty names + descriptions for manual themes (kept short, neutral)
MANUAL_META: dict[str, dict] = {
    "kraken":      {"name": "Kraken", "description": "Kraken-style purple-on-white crypto exchange aesthetic."},
    "lamborghini": {"name": "Lamborghini", "description": "Cinematic black canvas with gold accent — nocturnal luxury."},
    "lovable":     {"name": "Lovable", "description": "Warm cream parchment background with friendly tone."},
    "mastercard":  {"name": "Mastercard", "description": "Editorial putty-cream canvas, signal-orange CTAs, pill shapes."},
    "runwayml":    {"name": "RunwayML", "description": "Cinematic dark editorial — black canvas, white type, full-bleed."},
    "sanity":      {"name": "Sanity", "description": "Near-black command-center palette with electric-blue accent."},
    "spotify":     {"name": "Spotify", "description": "Iconic dark surface with Spotify Green primary."},
    "starbucks":   {"name": "Starbucks", "description": "Heritage green editorial palette on white canvas."},
    "tesla":       {"name": "Tesla", "description": "Ascetic white canvas with electric-blue CTA, photography-led."},
    "theverge":    {"name": "The Verge", "description": "Dark editorial chip palette — mint and ultraviolet accents."},
}

def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"Source not found: {SRC}")
    themes_meta = []
    css_blocks = []
    for d in sorted(SRC.iterdir()):
        if not d.is_dir():
            continue
        f = d / "DESIGN.md"
        if not f.exists():
            continue
        slug = d.name
        meta = parse_frontmatter(f.read_text(encoding="utf-8"))
        colors = meta.get("colors", {})
        if not colors and slug in MANUAL_FALLBACKS:
            colors = MANUAL_FALLBACKS[slug]
            meta = {**MANUAL_META.get(slug, {}), "colors": colors}
        if not colors:
            print(f"  skip   {slug} (no colors)")
            continue
        derived = derive(colors)
        css_blocks.append(make_block(slug, derived))
        themes_meta.append({
            "slug": slug,
            "name": meta.get("name", slug.title()),
            "description": meta.get("description", "")[:240],
            "is_dark": derived["is_dark"],
            "swatch": derived["swatch"],
        })

    OUT_CSS.parent.mkdir(parents=True, exist_ok=True)
    OUT_CSS.write_text(
        "/* Auto-generated by themes/import_themes.py — DO NOT EDIT BY HAND. */\n"
        "/* Source: github.com/VoltAgent/awesome-design-md (design-md/) */\n\n"
        + "\n\n".join(css_blocks) + "\n",
        encoding="utf-8",
    )
    OUT_JSON.write_text(
        json.dumps({"themes": themes_meta}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(themes_meta)} themes")
    print(f"  {OUT_CSS}")
    print(f"  {OUT_JSON}")

if __name__ == "__main__":
    main()
