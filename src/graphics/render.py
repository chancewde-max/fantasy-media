"""Pillow-based graphic rendering.

Card styles: a generic post card (Instagram), and a FanDuel-style power-
rankings board (two columns, colored team rows, movement arrows).
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

# Power-rankings board: deep-blue gradient background + a bright color per row
# (standing in for team branding since we don't have real team logos).
BOARD_TOP = (8, 20, 56)
BOARD_BOTTOM = (16, 40, 96)
BOARD_BORDER = (90, 140, 230)
ROW_PALETTE = [
    (198, 30, 51), (0, 105, 170), (0, 143, 91), (235, 115, 15),
    (110, 45, 180), (0, 150, 150), (190, 20, 120), (120, 110, 30),
    (55, 65, 180), (190, 90, 20), (30, 130, 190), (150, 30, 30),
]


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


def _save(img: Image.Image, path: str) -> None:
    """Palette-quantize before saving — these are flat-color graphics, so this
    cuts file size dramatically with no visible quality loss."""
    img.convert("P", palette=Image.ADAPTIVE, colors=64).save(path, optimize=True)


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
    _save(img, path)
    return path


def render_rankings_card(out_dir: str, name: str, week: int, rows: list[dict]) -> str:
    return render_power_rankings(
        out_dir, name,
        title="POWER RANKINGS", subtitle=f"WEEK {week}", rows=rows,
    )


def render_standings_card(out_dir: str, name: str, season_label: str, rows: list[dict]) -> str:
    """Final-standings board for a past season — same look, no movement arrows."""
    return render_power_rankings(
        out_dir, name,
        title="FINAL STANDINGS", subtitle=season_label, rows=rows, show_arrows=False,
    )


def render_champion_card(
    out_dir: str, name: str, season_label: str, champion: str, score_line: str = "",
) -> str:
    """Championship announcement card — same navy-board family as the rankings."""
    _ensure_dir(out_dir)
    W, H = 1080, 760
    img = _vgradient(W, H, BOARD_TOP, BOARD_BOTTOM)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([6, 6, W - 6, H - 6], radius=28, outline=BOARD_BORDER, width=4)

    tag_font = _load_font(30)
    label_font = _load_font(38)
    team_font = _load_font(60)
    score_font = _load_font(32)

    d.text((W / 2, 70), "FANTASY MEDIA RESEARCH", font=tag_font, fill=(160, 190, 240), anchor="ma")
    _trophy(d, W / 2, 195, 65)
    d.text((W / 2, 310), f"{season_label} CHAMPION", font=label_font, fill=(190, 210, 245), anchor="ma")

    d.rounded_rectangle([90, 385, W - 90, 385 + 210], radius=20, fill=ROW_PALETTE[0])
    _wrapped_text_centered(d, W / 2, 385 + 105, champion.upper(), team_font, (255, 255, 255), max_width=W - 180)

    if score_line:
        d.text((W / 2, 650), score_line, font=score_font, fill=(220, 230, 250), anchor="ma")

    path = os.path.join(out_dir, _safe_name(name) + ".png")
    _save(img, path)
    return path


def _trophy(d: ImageDraw.ImageDraw, cx: float, cy: float, s: float) -> None:
    gold = (230, 180, 40)
    cup_w, cup_h = s * 0.9, s * 0.7
    d.rounded_rectangle(
        [cx - cup_w / 2, cy - cup_h / 2, cx + cup_w / 2, cy + cup_h / 2],
        radius=cup_w * 0.25, fill=gold,
    )
    hr = s * 0.28
    d.arc([cx - cup_w / 2 - hr * 1.4, cy - hr, cx - cup_w / 2 + hr * 0.4, cy + hr],
          start=90, end=270, fill=gold, width=8)
    d.arc([cx + cup_w / 2 - hr * 0.4, cy - hr, cx + cup_w / 2 + hr * 1.4, cy + hr],
          start=270, end=90, fill=gold, width=8)
    stem_w = s * 0.16
    d.rectangle([cx - stem_w / 2, cy + cup_h / 2, cx + stem_w / 2, cy + cup_h / 2 + s * 0.28], fill=gold)
    base_w = s * 0.6
    by = cy + cup_h / 2 + s * 0.28
    d.rounded_rectangle([cx - base_w / 2, by, cx + base_w / 2, by + s * 0.16], radius=6, fill=gold)


def _wrapped_text_centered(d, cx, cy, text, font, fill, max_width):
    words = text.split()
    lines, line = [], ""
    for word in words:
        trial = f"{line} {word}".strip()
        if d.textlength(trial, font=font) > max_width and line:
            lines.append(line)
            line = word
        else:
            line = trial
    if line:
        lines.append(line)
    lh = _line_height(font) + 6
    total_h = lh * len(lines)
    y = cy - total_h / 2
    for ln in lines:
        d.text((cx, y), ln, font=font, fill=fill, anchor="ma")
        y += lh


def _vgradient(w: int, h: int, top: tuple, bottom: tuple, step: int = 6) -> Image.Image:
    """Banded vertical gradient — coarser steps keep the palette (and file
    size) small with no visible banding at these dimensions."""
    img = Image.new("RGB", (w, h), top)
    d = ImageDraw.Draw(img)
    for y0 in range(0, h, step):
        t = y0 / max(h - 1, 1)
        c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        d.rectangle([0, y0, w, min(y0 + step, h)], fill=c)
    return img


def render_power_rankings(
    out_dir: str, name: str, title: str, subtitle: str, rows: list[dict],
    show_arrows: bool = True,
) -> str:
    """FanDuel-style board: two columns of colored, per-team rows."""
    _ensure_dir(out_dir)
    W = 1320
    n = max(len(rows), 1)
    left_n = (n + 1) // 2
    right_n = n - left_n
    col_rows = max(left_n, right_n)

    header_h = 260
    row_h = 80
    row_gap = 10
    margin = 32
    H = header_h + col_rows * (row_h + row_gap) + margin

    img = _vgradient(W, H, BOARD_TOP, BOARD_BOTTOM)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([6, 6, W - 6, H - 6], radius=28, outline=BOARD_BORDER, width=4)

    tag_font = _load_font(30)
    title_font = _load_font(64)
    sub_font = _load_font(34)

    d.text((W / 2, 60), "FANTASY MEDIA RESEARCH", font=tag_font, fill=(160, 190, 240), anchor="ma")
    d.text((W / 2, 100), title, font=title_font, fill=FG, anchor="ma")
    d.text((W / 2, 178), subtitle, font=sub_font, fill=(190, 210, 245), anchor="ma")
    d.line([(80, 226), (W - 80, 226)], fill=BOARD_BORDER, width=2)

    col_w = (W - margin * 3) // 2
    rank_font = _load_font(34)
    name_font = _load_font(29)
    badge_font = _load_font(22)

    for i, r in enumerate(rows):
        col = 0 if i < left_n else 1
        row_i = i if col == 0 else i - left_n
        x0 = margin + col * (col_w + margin)
        y0 = header_h + row_i * (row_h + row_gap)
        x1 = x0 + col_w
        y1 = y0 + row_h

        color = ROW_PALETTE[i % len(ROW_PALETTE)]
        d.rounded_rectangle([x0, y0, x1, y1], radius=12, fill=color)

        cy = (y0 + y1) / 2
        cx = x0 + 28

        if show_arrows:
            _mini_arrow(d, cx, cy, r.get("arrow", "same"))
            cx += 30

        d.text((cx, cy), str(r.get("rank", i + 1)), font=rank_font, fill=(255, 255, 255), anchor="lm")
        cx += 46 if r.get("rank", i + 1) < 10 else 62

        badge_r = 17
        badge_color = _shade(color, 0.55)
        d.ellipse([cx, cy - badge_r, cx + badge_r * 2, cy + badge_r], fill=(255, 255, 255))
        initial = (r["team"][:1] or "?").upper()
        d.text((cx + badge_r, cy), initial, font=badge_font, fill=badge_color, anchor="mm")
        cx += badge_r * 2 + 12

        name_max = x1 - cx - 16
        team = _fit_text(d, r["team"].upper(), name_font, name_max)
        d.text((cx, cy), team, font=name_font, fill=(255, 255, 255), anchor="lm")

    path = os.path.join(out_dir, _safe_name(name) + ".png")
    _save(img, path)
    return path


def _shade(color: tuple, factor: float) -> tuple:
    return tuple(max(0, int(c * factor)) for c in color)


def _fit_text(d, text: str, font, max_width: int) -> str:
    if d.textlength(text, font=font) <= max_width:
        return text
    while text and d.textlength(text + "…", font=font) > max_width:
        text = text[:-1]
    return text + "…" if text else "…"


def _mini_arrow(d: ImageDraw.ImageDraw, cx: float, cy: float, arrow: str) -> None:
    s = 9
    if arrow == "up":
        d.polygon([(cx, cy - s), (cx - s, cy + s * 0.7), (cx + s, cy + s * 0.7)], fill=(80, 230, 140))
    elif arrow == "down":
        d.polygon([(cx, cy + s), (cx - s, cy - s * 0.7), (cx + s, cy - s * 0.7)], fill=(255, 90, 90))
    elif arrow == "new":
        d.ellipse([cx - s, cy - s, cx + s, cy + s], outline=(255, 210, 60), width=3)
    else:
        d.rectangle([cx - s, cy - 2, cx + s, cy + 2], fill=(190, 200, 220))


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
