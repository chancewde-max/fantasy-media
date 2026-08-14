"""Pillow-based graphic rendering.

Two card styles: a generic post card (Instagram) and a power-rankings card.
Styling constants live at the top so templates are easy to restyle. We rely
only on Pillow's default bitmap font so there are no font-file dependencies
to ship; swap in a TTF via _load_font for sharper output.
"""
from __future__ import annotations

import logging
import os

from PIL import Image, ImageDraw, ImageFont

log = logging.getLogger(__name__)

# --- restyle here ---
BG = (11, 18, 32)          # deep navy
ACCENT = (255, 66, 66)     # ESPN-ish red
FG = (240, 244, 248)
MUTED = (150, 160, 175)
UP = (46, 204, 113)
DOWN = (231, 76, 60)
SAME = (150, 160, 175)
CARD = (18, 27, 45)


def _load_font(size: int) -> ImageFont.ImageFont:
    """Try a few common TTFs; fall back to Pillow's built-in bitmap font."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:  # noqa: BLE001
            continue
    return ImageFont.load_default()


def _ensure_dir(out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)


def _safe_name(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)


def render_post_card(out_dir: str, name: str, headline: str, subtext: str = "") -> str:
    _ensure_dir(out_dir)
    W = H = 1080
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # accent bar
    d.rectangle([0, 0, W, 24], fill=ACCENT)

    title_font = _load_font(64)
    sub_font = _load_font(120)
    tag_font = _load_font(36)

    d.text((80, 120), "LEAGUE MEDIA", font=tag_font, fill=ACCENT)

    _wrapped_text(d, (80, 220), headline.upper(), title_font, FG, max_width=W - 160, line_gap=14)

    if subtext:
        d.text((80, H - 260), subtext, font=sub_font, fill=FG)

    d.text((80, H - 90), "@LeagueInsider", font=tag_font, fill=MUTED)

    path = os.path.join(out_dir, _safe_name(name) + ".png")
    img.save(path)
    return path


def render_rankings_card(out_dir: str, name: str, week: int, rows: list[dict]) -> str:
    _ensure_dir(out_dir)
    W = 1080
    header_h = 200
    row_h = 92
    H = header_h + row_h * max(len(rows), 1) + 60
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    d.rectangle([0, 0, W, 24], fill=ACCENT)
    d.text((80, 70), f"POWER RANKINGS — WEEK {week}", font=_load_font(52), fill=FG)

    rank_font = _load_font(46)
    team_font = _load_font(40)
    rec_font = _load_font(30)

    y = header_h
    for r in rows:
        d.rounded_rectangle([60, y, W - 60, y + row_h - 14], radius=14, fill=CARD)
        d.text((90, y + 22), f"{r['rank']}", font=rank_font, fill=ACCENT)
        d.text((180, y + 24), r["team"], font=team_font, fill=FG)
        rec = f"{r.get('wins', 0)}-{r.get('losses', 0)}  ·  {r.get('points_for', 0)} PF"
        d.text((180, y + 24 + 44), rec, font=rec_font, fill=MUTED)
        _arrow(d, W - 150, y + 30, r.get("arrow", "same"), r.get("delta", 0))
        y += row_h

    path = os.path.join(out_dir, _safe_name(name) + ".png")
    img.save(path)
    return path


def _arrow(d: ImageDraw.ImageDraw, x: int, y: int, arrow: str, delta: int) -> None:
    font = _load_font(38)
    if arrow == "up":
        d.text((x, y), f"▲ {delta}", font=font, fill=UP)
    elif arrow == "down":
        d.text((x, y), f"▼ {delta}", font=font, fill=DOWN)
    elif arrow == "new":
        d.text((x, y), "NEW", font=font, fill=ACCENT)
    else:
        d.text((x, y), "–", font=font, fill=SAME)


def _wrapped_text(d, xy, text, font, fill, max_width, line_gap=8):
    x, y = xy
    words = text.split()
    line = ""
    for word in words:
        trial = f"{line} {word}".strip()
        w = d.textlength(trial, font=font)
        if w > max_width and line:
            d.text((x, y), line, font=font, fill=fill)
            y += _line_height(font) + line_gap
            line = word
        else:
            line = trial
    if line:
        d.text((x, y), line, font=font, fill=fill)


def _line_height(font) -> int:
    try:
        ascent, descent = font.getmetrics()
        return ascent + descent
    except Exception:  # noqa: BLE001
        return 40
