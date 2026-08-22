"""HTML templates for the sports-graphic look (rendered by html_render).

Design language modeled on real gameday / record / stat-leader graphics:
moody team-colored gradients, a big ghosted numeral or wordmark behind the
subject, gold foil accents, film grain, angled light shards, a spotlight
behind the hero, and clean condensed type. Every template themes to the
team's real colors, drops in the team's real logo, and — when we have it — a
real player headshot as the hero image.
"""
from __future__ import annotations

import hashlib

from .html_render import font_faces

# Curated team colors (primary, secondary) keyed by normalized current name.
_THEME = {
    "the island boys": ("#12b5a6", "#0a3d3a"),
    "i chase white kids": ("#7c3aed", "#2e1065"),
    "patrick's team": ("#2563eb", "#0b1e4d"),
    "flaccid winners": ("#d21e3c", "#6b0f1c"),
    "jabawockeez": ("#e0b310", "#2a2100"),
    "team of collusion": ("#10b981", "#064e3b"),
    "back to back": ("#3b56d6", "#1a2680"),
    "b50beast": ("#e02424", "#5c0f0f"),
    "tha hoodie gang": ("#16a34a", "#064e2b"),
    "need more beers": ("#e0870f", "#5c3608"),
}
_FALLBACK = [
    ("#c81e33", "#7a0f1f"), ("#0069aa", "#003f66"), ("#0e9b6b", "#065c3f"),
    ("#e0740f", "#8a4708"), ("#7b2dd6", "#4a1a80"), ("#0f9a9a", "#075c5c"),
    ("#c81478", "#7a0c48"), ("#3341c8", "#1f2880"),
]

GOLD = "#ffce4d"


def theme(team: str) -> tuple[str, str]:
    key = (team or "").strip().lower()
    if key in _THEME:
        return _THEME[key]
    h = int(hashlib.md5(key.encode()).hexdigest(), 16)
    return _FALLBACK[h % len(_FALLBACK)]


def _fit(text: str, big: int, mid: int, small: int, tiny: int) -> int:
    """Pick a font size from text length so headlines never overflow or get
    visually truncated."""
    n = len(text or "")
    if n <= 22:
        return big
    if n <= 40:
        return mid
    if n <= 62:
        return small
    return tiny


def initials(name: str) -> str:
    words = [w for w in "".join(c if c.isalnum() or c.isspace() else " " for c in (name or "")).split() if w]
    if not words:
        return "?"
    if len(words) == 1:
        return words[0][:2].upper()
    return (words[0][0] + words[1][0]).upper()


# --- shared FX -------------------------------------------------------------
_GRAIN = ("background-image:repeating-linear-gradient(115deg,rgba(255,255,255,.03) 0 2px,"
          "transparent 2px 7px);opacity:.7;")


def _fx_css() -> str:
    return """
    .grain{position:absolute;inset:0;""" + _GRAIN + """z-index:1;pointer-events:none}
    .vig{position:absolute;inset:0;z-index:1;pointer-events:none;
      background:radial-gradient(circle at 50% 42%,transparent 40%,rgba(0,0,0,.55) 100%)}
    .shards{position:absolute;inset:0;z-index:1;overflow:hidden;pointer-events:none}
    .shard{position:absolute;top:-30%;height:160%;width:130px;transform:rotate(14deg);filter:blur(2px)}
    .spot{position:absolute;border-radius:50%;filter:blur(70px);z-index:1;pointer-events:none}
    .foil{background:linear-gradient(180deg,#fff 0%,#ffe9a8 42%,#f2b632 60%,#fff6d6 100%);
      -webkit-background-clip:text;background-clip:text;color:transparent}
    .wm{position:absolute;opacity:.10;z-index:1;filter:grayscale(.2)}
    """


def _base_css() -> str:
    return (font_faces() +
            "*{margin:0;padding:0;box-sizing:border-box}body{margin:0}"
            ".num{font-family:'Anton',sans-serif}"
            ".cond{font-family:'Barlow Condensed',sans-serif}"
            ".body{font-family:'Barlow',sans-serif}" + _fx_css())


def _shards(a: str, b: str) -> str:
    return (f"<div class=shards>"
            f"<div class=shard style='left:24%;background:linear-gradient(90deg,transparent,{a}55,transparent)'></div>"
            f"<div class=shard style='left:60%;background:linear-gradient(90deg,transparent,{b}55,transparent)'></div>"
            f"<div class=shard style='left:78%;width:60px;background:linear-gradient(90deg,transparent,#ffffff22,transparent)'></div>"
            f"</div>")


def _crest(team: str, logo: str | None, size: int = 190, radius: int = 26) -> str:
    p, s = theme(team)
    if logo:
        return (f"<div style=\"width:{size}px;height:{size}px;border-radius:{radius}px;flex:0 0 auto;"
                f"background:#0a0f1a center/cover no-repeat url('{logo}');"
                "box-shadow:0 18px 40px rgba(0,0,0,.55),inset 0 0 0 3px rgba(255,255,255,.15)\"></div>")
    fs = int(size * 0.5)
    return (f"<div class=num style=\"width:{size}px;height:{size}px;border-radius:{radius}px;flex:0 0 auto;"
            f"display:flex;align-items:center;justify-content:center;font-size:{fs}px;color:#fff;"
            f"background:linear-gradient(145deg,{p},{s});"
            "box-shadow:0 18px 40px rgba(0,0,0,.5),inset 0 3px 0 rgba(255,255,255,.25),"
            "inset 0 0 0 3px rgba(255,255,255,.14)\">" + initials(team) + "</div>")


def _hero(img: str | None, css_pos: str) -> str:
    """A player-headshot hero image, with a consistent drop shadow and a soft
    bottom fade so every headshot blends into the card the same way (uniform
    look, not a pasted-on rectangle). Empty string when there's no image."""
    if not img:
        return ""
    return (f"<img src='{img}' style=\"position:absolute;{css_pos};z-index:2;"
            "object-fit:contain;object-position:bottom center;"
            "filter:drop-shadow(0 18px 26px rgba(0,0,0,.55));"
            "-webkit-mask-image:linear-gradient(to bottom,#000 76%,transparent 98%);"
            "mask-image:linear-gradient(to bottom,#000 76%,transparent 98%)\">")


def _doc(inner: str, css: str) -> str:
    return f"<!doctype html><html><head><meta charset=utf8><style>{_base_css()}{css}</style></head><body>{inner}</body></html>"


# ---------------------------------------------------------------------------
def matchup_html(team_a, team_b, sub_a, sub_b, week_label, lore,
                 logo_a=None, logo_b=None, hero_a=None, hero_b=None) -> str:
    pa, sa = theme(team_a)
    pb, sb = theme(team_b)
    css = f"""
    #card{{width:1080px;height:1080px;position:relative;overflow:hidden;color:#fff;
      background:linear-gradient(115deg,{sa} 0%,#090e18 42%,#090e18 58%,{sb} 100%)}}
    .top{{position:absolute;top:50px;width:100%;text-align:center;z-index:4}}
    .kick{{font-size:52px;letter-spacing:3px}}
    .wk{{font-size:30px;font-weight:700;letter-spacing:8px;color:#c9d6f2;margin-top:2px}}
    /* crest + name on the LEFT; hero sits in a fixed right-hand zone, never
       crossing center — both halves laid out identically. */
    .row{{position:absolute;left:60px;right:430px;display:flex;align-items:center;gap:30px;z-index:4}}
    .rowA{{top:172px;height:300px}} .rowB{{top:608px;height:300px}}
    .tname{{font-size:74px;line-height:.9;text-transform:uppercase;text-shadow:0 5px 24px rgba(0,0,0,.75)}}
    .tsub{{font-size:33px;font-weight:600;color:#e6ecfb;margin-top:12px;letter-spacing:1px}}
    .vs{{position:absolute;top:474px;left:50%;transform:translateX(-50%);width:132px;height:132px;
      border-radius:50%;background:linear-gradient(145deg,#ff5a5a,#a80f16);display:flex;align-items:center;
      justify-content:center;font-size:58px;z-index:6;
      box-shadow:0 0 0 8px rgba(255,255,255,.06),0 16px 40px rgba(220,20,20,.6),inset 0 3px 0 rgba(255,255,255,.4)}}
    .dvline{{position:absolute;top:540px;left:60px;right:60px;height:2px;
      background:linear-gradient(90deg,transparent,rgba(255,255,255,.4),transparent);z-index:3}}
    .foot{{position:absolute;bottom:50px;left:60px;right:60px;text-align:center;font-size:32px;font-weight:600;
      color:#fff;background:rgba(0,0,0,.32);border:1px solid rgba(255,255,255,.14);
      padding:20px 26px;border-radius:18px;z-index:4}}
    """
    foot = f"<div class='foot cond'>{lore}</div>" if lore else ""
    # identical hero zones: both faces in a fixed right-hand column, clear of
    # the names and the center VS badge
    heroes = (_hero(hero_a, "right:40px;top:60px;height:372px;width:360px") +
              _hero(hero_b, "right:40px;top:600px;height:372px;width:360px"))
    inner = f"""<div id=card>
      <div class=spot style="left:-140px;top:120px;width:420px;height:420px;background:{pa}66"></div>
      <div class=spot style="right:-140px;bottom:120px;width:420px;height:420px;background:{pb}66"></div>
      {_shards(pa,pb)}{heroes}<div class=grain></div><div class=vig></div>
      <div class=top><div class='kick num foil'>GAME OF THE WEEK</div><div class='wk cond'>{week_label}</div></div>
      <div class='row rowA'>{_crest(team_a,logo_a,150,24)}<div><div class='tname num'>{team_a}</div><div class='tsub cond'>{sub_a}</div></div></div>
      <div class=dvline></div><div class='vs num'>VS</div>
      <div class='row rowB'>{_crest(team_b,logo_b,150,24)}<div><div class='tname num'>{team_b}</div><div class='tsub cond'>{sub_b}</div></div></div>
      {foot}</div>"""
    return _doc(inner, css)


def final_score_html(winner, w_score, loser, l_score, badge, note, week_label,
                     logo_w=None, logo_l=None) -> str:
    pw, sw = theme(winner)
    css = f"""
    #card{{width:1080px;height:1080px;position:relative;overflow:hidden;color:#fff;
      background:radial-gradient(circle at 50% 8%,{sw} 0%,#090e18 55%,#05080f 100%)}}
    .top{{position:absolute;top:52px;width:100%;text-align:center;z-index:4}}
    .final{{font-size:60px;letter-spacing:10px}}
    .wk{{font-size:26px;font-weight:700;letter-spacing:6px;color:#9fb4e6;margin-top:2px}}
    .badge{{display:inline-block;margin-top:18px;font-size:28px;font-weight:700;letter-spacing:4px;
      color:#0b1220;background:linear-gradient(180deg,#ffe08a,#f0b022);padding:9px 32px;border-radius:30px;
      box-shadow:0 8px 24px rgba(240,176,34,.4)}}
    .row{{position:absolute;left:60px;right:60px;display:flex;align-items:center;gap:28px;z-index:4}}
    .rowW{{top:372px}} .rowL{{top:690px}}
    .nm{{font-size:72px;text-transform:uppercase;line-height:.88;flex:1}}
    .sc{{font-size:158px;line-height:.78}}
    .lose{{opacity:.62}}
    .dvline{{position:absolute;top:566px;left:60px;right:60px;height:2px;
      background:linear-gradient(90deg,transparent,rgba(255,255,255,.32),transparent);z-index:3}}
    .note{{position:absolute;bottom:56px;left:60px;right:60px;text-align:center;font-size:33px;font-weight:600;
      color:#eef2fb;z-index:4}}
    """
    badge_html = f"<div class='badge cond'>{badge}</div>" if badge else ""
    note_html = f"<div class='note cond'>{note}</div>" if note else ""
    win_sc = f"<div class='sc num foil'>{w_score:g}</div>"
    lose_sc = f"<div class='sc num'>{l_score:g}</div>"
    inner = f"""<div id=card>
      <div class=spot style="left:50%;top:-60px;transform:translateX(-50%);width:640px;height:360px;background:{pw}55"></div>
      {_shards(pw,sw)}<div class=grain></div><div class=vig></div>
      <div class=top><div class='final num'>FINAL</div><div class='wk cond'>{week_label}</div>{badge_html}</div>
      <div class='row rowW'>{_crest(winner,logo_w,150,22)}<div class='nm num'>{winner}</div>{win_sc}</div>
      <div class=dvline></div>
      <div class='row rowL lose'>{_crest(loser,logo_l,150,22)}<div class='nm num'>{loser}</div>{lose_sc}</div>
      {note_html}</div>"""
    return _doc(inner, css)


def record_html(kicker, big, sub, team, ghost="", logo=None, hero=None) -> str:
    p, s = theme(team)
    ghost = ghost or "".join(ch for ch in big if ch.isdigit())[:3] or initials(team)
    hero_html = _hero(hero, "left:50%;transform:translateX(-50%);bottom:210px;height:640px") if hero \
        else f"<div class=crest style='position:absolute;top:330px;left:50%;transform:translateX(-50%);z-index:3'>{_crest(team,logo,300,40)}</div>"
    css = f"""
    #card{{width:1080px;height:1080px;position:relative;overflow:hidden;color:#fff;
      background:radial-gradient(circle at 50% 42%,{p}40 0%,{s} 32%,#05080f 80%)}}
    .ghost{{position:absolute;top:0;left:50%;transform:translateX(-50%);font-size:660px;line-height:1;
      z-index:2;white-space:nowrap;opacity:.14}}
    .kick{{position:absolute;top:92px;width:100%;text-align:center;font-size:46px;letter-spacing:5px;z-index:4}}
    .big{{position:absolute;bottom:246px;left:56px;right:56px;text-align:center;font-size:112px;
      line-height:.9;text-transform:uppercase;z-index:4;text-shadow:0 6px 30px rgba(0,0,0,.7)}}
    .sub{{position:absolute;bottom:150px;left:80px;right:80px;text-align:center;font-size:38px;font-weight:600;
      color:#eef2fb;z-index:4}}
    .team{{position:absolute;bottom:72px;width:100%;text-align:center;font-size:30px;font-weight:700;
      letter-spacing:6px;color:#a9bbe6;z-index:4;text-transform:uppercase}}
    """
    inner = f"""<div id=card>
      <div class=spot style="left:50%;top:220px;transform:translateX(-50%);width:620px;height:620px;background:{p}66"></div>
      <div class='ghost num foil'>{ghost}</div>{hero_html}
      <div class=grain></div><div class=vig></div>
      <div class='kick num foil'>{kicker}</div>
      <div class='big num'>{big}</div><div class='sub cond'>{sub}</div><div class='team cond'>{team}</div></div>"""
    return _doc(inner, css)


def stat_leader_html(kicker, team, value, label, sub, ghost="MVP", logo=None, hero=None, player_name="") -> str:
    p, s = theme(team)
    hero_html = _hero(hero, "left:50%;transform:translateX(-50%);top:158px;height:430px") if hero \
        else f"<div style='position:absolute;top:236px;left:50%;transform:translateX(-50%);z-index:3'>{_crest(team,logo,240,32)}</div>"
    name_html = f"<div class='pname cond'>{player_name}</div>" if player_name else ""
    css = f"""
    #card{{width:1080px;height:1080px;position:relative;overflow:hidden;color:#fff;
      background:radial-gradient(circle at 50% 18%,{s} 0%,#090e18 60%,#05080f 100%)}}
    .ghost{{position:absolute;top:150px;left:50%;transform:translateX(-50%);font-size:520px;line-height:1;
      z-index:2;white-space:nowrap;color:{p}40}}
    .kick{{position:absolute;top:84px;width:100%;text-align:center;font-size:48px;letter-spacing:5px;z-index:4}}
    .pname{{position:absolute;top:636px;width:100%;text-align:center;font-size:40px;font-weight:700;
      letter-spacing:3px;color:{GOLD};z-index:4;text-transform:uppercase}}
    .team{{position:absolute;top:690px;width:100%;text-align:center;font-size:44px;text-transform:uppercase;
      color:#cdd8f2;z-index:4}}
    .val{{position:absolute;top:748px;width:100%;text-align:center;font-size:210px;line-height:.8;z-index:4}}
    .label{{position:absolute;top:960px;width:100%;text-align:center;font-size:36px;letter-spacing:6px;
      color:#cdd8f2;z-index:4;text-transform:uppercase}}
    .sub{{position:absolute;top:1016px;width:100%;text-align:center;font-size:28px;font-weight:600;
      color:#9fb4e6;z-index:4}}
    """
    inner = f"""<div id=card>
      <div class=spot style="left:50%;top:110px;transform:translateX(-50%);width:560px;height:500px;background:{p}55"></div>
      <div class='ghost num'>{ghost}</div>{_shards(p,s)}{hero_html}
      <div class=grain></div><div class=vig></div>
      <div class='kick num foil'>{kicker}</div>
      {name_html}<div class='team cond'>{team}</div>
      <div class='val num foil'>{value}</div>
      <div class='label cond'>{label}</div><div class='sub cond'>{sub}</div></div>"""
    return _doc(inner, css)


def breaking_html(headline, team="", logo=None, hero=None) -> str:
    """An Insider 'breaking news' poster: red BREAKING flag, an auto-fit
    headline in a fixed upper band, a centered player hero, a small team crest,
    and a grounding scrim + byline. Balanced and consistent every time."""
    p, s = theme(team) if team else ("#c81e33", "#4a0c14")
    fs = _fit(headline, 78, 64, 52, 44)
    crest = (f"<div style='position:absolute;top:64px;right:56px;z-index:6'>{_crest(team,logo,120,20)}</div>"
             if team else "")
    subject = _hero(hero, "left:50%;transform:translateX(-50%);bottom:0;height:660px") if hero else ""
    css = f"""
    #card{{width:1080px;height:1080px;position:relative;overflow:hidden;color:#fff;
      background:linear-gradient(150deg,{s} 0%,#090e18 55%,#05080f 100%)}}
    .flag{{position:absolute;top:66px;left:60px;background:linear-gradient(180deg,#ff3b3b,#b3121a);
      font-size:36px;letter-spacing:4px;padding:12px 30px;border-radius:10px;z-index:6;
      box-shadow:0 10px 30px rgba(220,20,20,.5)}}
    .src{{position:absolute;top:146px;left:64px;font-size:28px;letter-spacing:5px;color:{GOLD};z-index:6}}
    .hl{{position:absolute;left:60px;right:60px;top:250px;height:250px;display:flex;align-items:flex-start;
      font-size:{fs}px;line-height:1.0;text-transform:uppercase;z-index:6;text-shadow:0 6px 30px rgba(0,0,0,.9)}}
    .scrim{{position:absolute;left:0;right:0;bottom:0;height:260px;z-index:5;
      background:linear-gradient(to top,#05080f 8%,transparent)}}
    .by{{position:absolute;bottom:52px;left:64px;font-size:30px;font-weight:600;color:#dfe6f7;z-index:6}}
    """
    inner = f"""<div id=card>
      <div class=spot style="left:-120px;top:-80px;width:520px;height:520px;background:{p}66"></div>
      {_shards(p,s)}{subject}<div class=grain></div><div class=vig></div><div class=scrim></div>{crest}
      <div class='flag num'>BREAKING</div><div class='src cond'>THE INSIDER</div>
      <div class='hl num'>{headline}</div>
      <div class='by cond'>Dianna Russinni · @DiannaRussinni</div></div>"""
    return _doc(inner, css)


def standings_html(title, subtitle, rows) -> str:
    """A professional standings / power-rankings board: header + a clean column
    of team rows (rank, crest, name, record, points), team-colored accents,
    medals for the top three. rows: [{rank, team, wins, losses, points,
    logo?, arrow?}]."""
    n = max(len(rows), 1)
    row_h, gap, top = 104, 14, 300
    height = top + n * (row_h + gap) + 60
    medal = {1: "#ffce4d", 2: "#cfd6e6", 3: "#e0904d"}

    row_html = []
    for r in rows:
        p, s = theme(r["team"])
        rc = medal.get(r["rank"], "#8fa0c4")
        logo = r.get("logo")
        crest = (f"<div style=\"width:60px;height:60px;border-radius:12px;flex:0 0 auto;"
                 f"background:#0a0f1a center/cover no-repeat url('{logo}')\"></div>" if logo else
                 f"<div class=num style=\"width:60px;height:60px;border-radius:12px;flex:0 0 auto;display:flex;"
                 f"align-items:center;justify-content:center;font-size:26px;background:linear-gradient(145deg,{p},{s})\">"
                 f"{initials(r['team'])}</div>")
        arrow = ""
        a = r.get("arrow")
        if a == "up":
            arrow = "<span style='color:#33d17a;font-size:26px;margin-left:10px'>&#9650;</span>"
        elif a == "down":
            arrow = "<span style='color:#e0533d;font-size:26px;margin-left:10px'>&#9660;</span>"
        row_html.append(
            f"<div class=r style='border-left:9px solid {p}'>"
            f"<div class='rk num' style='color:{rc}'>{r['rank']}</div>{crest}"
            f"<div class='nm cond'>{r['team']}{arrow}</div>"
            f"<div class='rec cond'>{r.get('wins',0)}-{r.get('losses',0)}</div>"
            f"<div class='pf num'>{r.get('points','')}</div></div>"
        )

    css = f"""
    #card{{width:1080px;height:{height}px;position:relative;overflow:hidden;color:#fff;
      background:radial-gradient(circle at 50% 0%,#16224a 0%,#0a0f1a 55%,#05080f 100%)}}
    .head{{position:absolute;top:56px;width:100%;text-align:center;z-index:4}}
    .kick{{font-size:26px;letter-spacing:5px;color:#8fa0c4}}
    .title{{font-size:76px;letter-spacing:1px;margin-top:2px}}
    .sub{{font-size:30px;font-weight:700;letter-spacing:6px;color:{GOLD};margin-top:4px}}
    .list{{position:absolute;top:{top}px;left:56px;right:56px;z-index:4}}
    .r{{display:flex;align-items:center;gap:22px;height:{row_h}px;margin-bottom:{gap}px;padding:0 26px;
      background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.08);border-radius:16px}}
    .rk{{width:56px;font-size:44px;text-align:center;flex:0 0 auto}}
    .nm{{flex:1;font-size:40px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;
      white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
    .rec{{font-size:32px;font-weight:600;color:#9fb4e6;flex:0 0 auto;width:120px;text-align:right}}
    .pf{{font-size:38px;color:{GOLD};flex:0 0 auto;width:150px;text-align:right}}
    """
    inner = (f"<div id=card><div class=grain></div>"
             f"<div class=head><div class='kick cond'>FANTASY MEDIA RESEARCH</div>"
             f"<div class='title num'>{title}</div><div class='sub cond'>{subtitle}</div></div>"
             f"<div class=list>{''.join(row_html)}</div></div>")
    return _doc(inner, css)


def meme_html(top_text, bottom_text, team="") -> str:
    p, s = theme(team or top_text)
    css = f"""
    #card{{width:1080px;height:1080px;position:relative;overflow:hidden;color:#fff;
      background:linear-gradient(160deg,{p},{s})}}
    .t{{position:absolute;left:48px;right:48px;text-align:center;text-transform:uppercase;
      font-size:90px;line-height:1.02;color:#fff;z-index:4;
      -webkit-text-stroke:6px #000;paint-order:stroke fill;text-shadow:0 6px 22px rgba(0,0,0,.6)}}
    .top{{top:64px}} .bot{{bottom:76px}}
    """
    top = f"<div class='t top num'>{top_text}</div>" if top_text else ""
    bot = f"<div class='t bot num'>{bottom_text}</div>" if bottom_text else ""
    return _doc(f"<div id=card>{_shards(p,s)}<div class=grain></div><div class=vig></div>{top}{bot}</div>", css)
