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

    d.text((80, H - 90), "@DiannaRussinni", font=tag_font, fill=MUTED)

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
    W, H = 1080, 800
    img = _vgradient(W, H, BOARD_TOP, BOARD_BOTTOM)
    _radial_glow(img, W / 2, 210, 260, (255, 210, 90))
    d = ImageDraw.Draw(img)
    _confetti(d, W, H)
    d.rounded_rectangle([6, 6, W - 6, H - 6], radius=28, outline=BOARD_BORDER, width=4)

    tag_font = _load_font(30)
    label_font = _load_font(38)
    team_font = _load_font(58)
    score_font = _load_font(34)

    d.text((W / 2, 70), "FANTASY MEDIA RESEARCH", font=tag_font, fill=(160, 190, 240), anchor="ma")
    _trophy(d, W / 2, 210, 92)
    d.text((W / 2, 340), f"{season_label} CHAMPION", font=label_font, fill=(190, 210, 245), anchor="ma")

    _ribbon(d, W / 2, 415 + 105, W - 180, 210, ROW_PALETTE[0])
    _wrapped_text_centered(d, W / 2, 415 + 105, champion.upper(), team_font, (255, 255, 255), max_width=W - 240)

    if score_line:
        d.line([(W / 2 - 60, 690), (W / 2 + 60, 690)], fill=(120, 150, 210), width=2)
        d.text((W / 2, 710), score_line, font=score_font, fill=(220, 230, 250), anchor="ma")

    path = os.path.join(out_dir, _safe_name(name) + ".png")
    _save(img, path)
    return path


def _radial_glow(img: Image.Image, cx: float, cy: float, radius: float, color: tuple) -> None:
    """Soft radial highlight behind the trophy — cheap glow via banded circles."""
    d = ImageDraw.Draw(img, "RGBA")
    steps = 24
    for i in range(steps, 0, -1):
        r = radius * i / steps
        alpha = int(45 * (1 - i / steps) ** 2)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*color, alpha))


def _confetti(d: ImageDraw.ImageDraw, w: int, h: int) -> None:
    """Scattered celebratory dots, kept to the top/bottom edges so the
    headline, trophy, and team ribbon stay clean and readable."""
    import random
    rng = random.Random(7)  # fixed seed: deterministic, stable output
    colors = [(255, 210, 90), (255, 255, 255), (120, 190, 255), (255, 130, 160)]
    bands = [(24, 56), (h - 70, h - 30)]
    for y0, y1 in bands:
        for _ in range(18):
            x = rng.uniform(24, w - 24)
            y = rng.uniform(y0, y1)
            s = rng.uniform(3, 7)
            c = rng.choice(colors)
            if rng.random() < 0.5:
                d.ellipse([x, y, x + s, y + s], fill=c)
            else:
                d.rectangle([x, y, x + s, y + s * 0.5], fill=c)


def _ribbon(d: ImageDraw.ImageDraw, cx: float, cy: float, w: float, h: float, color: tuple) -> None:
    """A banner with notched ends and a drop shadow, instead of a plain box."""
    x0, x1 = cx - w / 2, cx + w / 2
    y0, y1 = cy - h / 2, cy + h / 2
    notch = h * 0.28

    shadow = _shade(color, 0.4)
    d.rounded_rectangle([x0 + 10, y0 + 12, x1 + 10, y1 + 12], radius=18, fill=shadow)

    d.rounded_rectangle([x0, y0, x1, y1], radius=18, fill=color)
    d.polygon([(x0 - 26, y0 + notch), (x0 + 4, cy), (x0 - 26, y1 - notch)], fill=_shade(color, 0.75))
    d.polygon([(x1 + 26, y0 + notch), (x1 - 4, cy), (x1 + 26, y1 - notch)], fill=_shade(color, 0.75))


def _trophy(d: ImageDraw.ImageDraw, cx: float, cy: float, s: float) -> None:
    gold_dark = (170, 125, 20)
    gold = (230, 180, 40)
    gold_light = (255, 222, 120)

    cup_w, cup_h = s * 0.9, s * 0.7
    top, bot = cy - cup_h / 2, cy + cup_h / 2

    # cup: base gold, lighter wash on the upper-left third for a lit-metal look
    d.rounded_rectangle([cx - cup_w / 2, top, cx + cup_w / 2, bot], radius=cup_w * 0.25, fill=gold)
    d.pieslice([cx - cup_w / 2, top, cx - cup_w / 2 + cup_w * 0.7, top + cup_h * 0.9],
               start=180, end=300, fill=gold_light)
    d.rounded_rectangle([cx - cup_w / 2, bot - cup_h * 0.22, cx + cup_w / 2, bot],
                         radius=cup_w * 0.2, fill=gold_dark)

    # a star engraved on the cup face
    _star(d, cx, cy - cup_h * 0.05, s * 0.16, gold_dark)

    hr = s * 0.28
    d.arc([cx - cup_w / 2 - hr * 1.4, cy - hr, cx - cup_w / 2 + hr * 0.4, cy + hr],
          start=90, end=270, fill=gold, width=9)
    d.arc([cx + cup_w / 2 - hr * 0.4, cy - hr, cx + cup_w / 2 + hr * 1.4, cy + hr],
          start=270, end=90, fill=gold, width=9)

    stem_w = s * 0.16
    d.rectangle([cx - stem_w / 2, bot, cx + stem_w / 2, bot + s * 0.28], fill=gold)
    base_w = s * 0.62
    by = bot + s * 0.28
    d.rounded_rectangle([cx - base_w / 2, by, cx + base_w / 2, by + s * 0.16], radius=6, fill=gold_dark)
    plinth_w = s * 0.8
    d.rounded_rectangle([cx - plinth_w / 2, by + s * 0.16, cx + plinth_w / 2, by + s * 0.28],
                         radius=6, fill=gold)


def _star(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float, color: tuple) -> None:
    import math
    pts = []
    for i in range(10):
        angle = math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.42
        pts.append((cx + rad * math.cos(angle), cy - rad * math.sin(angle)))
    d.polygon(pts, fill=color)


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


# ===========================================================================
# Real "sports app" graphics: gameday matchup, final score, record, stat
# leader, and a meme card. All square-ish, self-contained (no external assets),
# and built from the same navy-board family so the feed reads as one brand.
# ===========================================================================
def _team_color(name: str) -> tuple:
    """Deterministic team color from the name, so a team looks the same every
    time it appears (stand-in for real logos)."""
    h = 0
    for ch in name or "?":
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return ROW_PALETTE[h % len(ROW_PALETTE)]


def _initials(name: str) -> str:
    words = [w for w in "".join(c if c.isalnum() or c.isspace() else " " for c in (name or "")).split() if w]
    if not words:
        return "?"
    if len(words) == 1:
        return words[0][:2].upper()
    return (words[0][0] + words[1][0]).upper()


def _crest(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float, name: str) -> None:
    """A simple circular team crest with initials — a lightweight logo."""
    color = _team_color(name)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color, outline=(255, 255, 255), width=4)
    f = _load_font(int(r))
    d.text((cx, cy), _initials(name), font=f, fill=(255, 255, 255), anchor="mm")


def render_gameday_matchup(
    out_dir: str, name: str, team_a: str, team_b: str,
    sub_a: str = "", sub_b: str = "", week_label: str = "", lore: str = "",
) -> str:
    """Pre-game 'A vs B' poster with crests, records, and a lore/rivalry line."""
    _ensure_dir(out_dir)
    W, H = 1080, 1080
    img = _vgradient(W, H, BOARD_TOP, BOARD_BOTTOM)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([6, 6, W - 6, H - 6], radius=28, outline=BOARD_BORDER, width=4)

    d.text((W / 2, 60), "GAME OF THE WEEK", font=_load_font(40), fill=(255, 210, 90), anchor="ma")
    if week_label:
        d.text((W / 2, 120), week_label.upper(), font=_load_font(32), fill=(170, 195, 240), anchor="ma")

    def team_row(y, team, sub):
        _crest(d, 150, y, 84, team)
        _wrapped_text(d, (270, y - 56), team.upper(), _load_font(48), FG, max_width=W - 320, line_gap=6)
        if sub:
            d.text((270, y + 66), sub, font=_load_font(30), fill=MUTED)

    team_row(330, team_a, sub_a)

    # center VS divider
    d.line([(90, 540), (W / 2 - 80, 540)], fill=(80, 110, 170), width=2)
    d.line([(W / 2 + 80, 540), (W - 90, 540)], fill=(80, 110, 170), width=2)
    d.ellipse([W / 2 - 62, 478, W / 2 + 62, 602], fill=ACCENT, outline=(255, 255, 255), width=4)
    d.text((W / 2, 540), "VS", font=_load_font(52), fill=(255, 255, 255), anchor="mm")

    team_row(750, team_b, sub_b)

    if lore:
        _wrapped_text_centered(d, W / 2, 1000, lore, _load_font(26), (200, 215, 245), max_width=W - 140)

    path = os.path.join(out_dir, _safe_name(name) + ".png")
    _save(img, path)
    return path


def render_final_score(
    out_dir: str, name: str, winner: str, winner_score: float,
    loser: str, loser_score: float, badge: str = "", note: str = "",
) -> str:
    """Post-game scoreboard: FINAL, both teams + scores, winner highlighted."""
    _ensure_dir(out_dir)
    W, H = 1080, 1080
    img = _vgradient(W, H, BOARD_TOP, BOARD_BOTTOM)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([6, 6, W - 6, H - 6], radius=28, outline=BOARD_BORDER, width=4)

    d.text((W / 2, 70), "FINAL", font=_load_font(44), fill=ACCENT, anchor="ma")
    if badge:
        bw = 460
        d.rounded_rectangle([W / 2 - bw / 2, 140, W / 2 + bw / 2, 196], radius=28, fill=(255, 210, 90))
        d.text((W / 2, 168), badge.upper(), font=_load_font(30), fill=(20, 20, 20), anchor="mm")

    def team_row(y, team, score, win):
        _crest(d, 150, y, 78, team)
        col = FG if win else MUTED
        _wrapped_text(d, (260, y - 52), team.upper(), _load_font(42), col, max_width=470, line_gap=4)
        d.text((W - 70, y), f"{score:g}", font=_load_font(74), fill=col, anchor="rm")
        if win:
            d.polygon([(W - 46, y - 12), (W - 46, y + 12), (W - 28, y)], fill=ACCENT)

    team_row(340, winner, winner_score, True)
    d.line([(90, 540), (W - 90, 540)], fill=(80, 110, 170), width=2)
    team_row(720, loser, loser_score, False)

    if note:
        _wrapped_text_centered(d, W / 2, 960, note, _load_font(30), (200, 215, 245), max_width=W - 160)

    path = os.path.join(out_dir, _safe_name(name) + ".png")
    _save(img, path)
    return path


def render_record_card(
    out_dir: str, name: str, kicker: str, big_line: str, sub: str = "",
) -> str:
    """A milestone / record graphic: small kicker, huge headline stat, subtitle."""
    _ensure_dir(out_dir)
    W, H = 1080, 1080
    img = _vgradient(W, H, BOARD_TOP, BOARD_BOTTOM)
    _radial_glow(img, W / 2, H / 2, 340, (255, 210, 90))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([6, 6, W - 6, H - 6], radius=28, outline=BOARD_BORDER, width=4)

    d.text((W / 2, 120), kicker.upper(), font=_load_font(40), fill=(255, 210, 90), anchor="ma")
    _wrapped_text_centered(d, W / 2, H / 2, big_line.upper(), _load_font(92), FG, max_width=W - 160)
    if sub:
        _wrapped_text_centered(d, W / 2, H - 170, sub, _load_font(34), (200, 215, 245), max_width=W - 200)

    path = os.path.join(out_dir, _safe_name(name) + ".png")
    _save(img, path)
    return path


def render_stat_leader(
    out_dir: str, name: str, kicker: str, team: str,
    stat_value: str, stat_label: str, sub: str = "",
) -> str:
    """Player/team-of-the-week style graphic: a crest, a big stat, a label."""
    _ensure_dir(out_dir)
    W, H = 1080, 1080
    img = _vgradient(W, H, BOARD_TOP, BOARD_BOTTOM)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([6, 6, W - 6, H - 6], radius=28, outline=BOARD_BORDER, width=4)

    d.text((W / 2, 90), kicker.upper(), font=_load_font(40), fill=ACCENT, anchor="ma")
    _crest(d, W / 2, 340, 140, team)
    _wrapped_text_centered(d, W / 2, 560, team.upper(), _load_font(52), FG, max_width=W - 160)
    d.text((W / 2, 720), str(stat_value), font=_load_font(150), fill=(255, 210, 90), anchor="ma")
    d.text((W / 2, 910), stat_label.upper(), font=_load_font(36), fill=(200, 215, 245), anchor="ma")
    if sub:
        _wrapped_text_centered(d, W / 2, 985, sub, _load_font(28), MUTED, max_width=W - 200)

    path = os.path.join(out_dir, _safe_name(name) + ".png")
    _save(img, path)
    return path


def render_meme(out_dir: str, name: str, top_text: str, bottom_text: str = "") -> str:
    """Impact-font style meme card — bold white text with a heavy outline on a
    colored panel. Not a stolen template; an original league meme graphic."""
    _ensure_dir(out_dir)
    W, H = 1080, 1080
    base = _team_color(top_text + bottom_text)
    img = _vgradient(W, H, _shade(base, 0.5), _shade(base, 0.9))
    d = ImageDraw.Draw(img)

    def impact(text, cy):
        if not text:
            return
        font = _load_font(78)
        # crude outline: draw text offset in black around white fill
        for dx in (-3, 0, 3):
            for dy in (-3, 0, 3):
                if dx or dy:
                    _wrapped_text_centered(d, W / 2 + dx, cy + dy, text.upper(), font, (0, 0, 0), max_width=W - 120)
        _wrapped_text_centered(d, W / 2, cy, text.upper(), font, (255, 255, 255), max_width=W - 120)

    impact(top_text, 150)
    impact(bottom_text, H - 170)

    path = os.path.join(out_dir, _safe_name(name) + ".png")
    _save(img, path)
    return path
