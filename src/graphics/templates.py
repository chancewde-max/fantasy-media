"""HTML templates for the sports-graphic look (rendered by html_render).

Design language modeled on real gameday / record / stat-leader graphics:
moody team-colored gradients, a big ghosted numeral or wordmark behind the
subject, gold accents, film grain, and clean condensed type. Every template
themes to the team's real colors and drops in the team's logo when available,
falling back to a strong monogram badge.
"""
from __future__ import annotations

import hashlib

from .html_render import font_faces

# Curated team colors (primary, secondary) keyed by normalized current name.
# Chosen to read as intentional brand colors in the color-split / gradient bg.
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


def theme(team: str) -> tuple[str, str]:
    key = (team or "").strip().lower()
    if key in _THEME:
        return _THEME[key]
    h = int(hashlib.md5(key.encode()).hexdigest(), 16)
    return _FALLBACK[h % len(_FALLBACK)]


def initials(name: str) -> str:
    words = [w for w in "".join(c if c.isalnum() or c.isspace() else " " for c in (name or "")).split() if w]
    if not words:
        return "?"
    if len(words) == 1:
        return words[0][:2].upper()
    return (words[0][0] + words[1][0]).upper()


_GRAIN = ("background-image:repeating-linear-gradient(115deg,rgba(255,255,255,.028) 0 2px,"
          "transparent 2px 7px),radial-gradient(circle at 30% 0%,rgba(255,255,255,.06),transparent 60%);")


def _base_css() -> str:
    return (font_faces() +
            "*{margin:0;padding:0;box-sizing:border-box}"
            "body{margin:0}"
            ".num{font-family:'Anton',sans-serif}"
            ".cond{font-family:'Barlow Condensed',sans-serif}"
            ".body{font-family:'Barlow',sans-serif}")


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


def _doc(inner: str, css: str) -> str:
    return f"<!doctype html><html><head><meta charset=utf8><style>{_base_css()}{css}</style></head><body>{inner}</body></html>"


# ---------------------------------------------------------------------------
def matchup_html(team_a, team_b, sub_a, sub_b, week_label, lore,
                 logo_a=None, logo_b=None) -> str:
    pa, sa = theme(team_a)
    pb, sb = theme(team_b)
    css = f"""
    #card{{width:1080px;height:1080px;position:relative;overflow:hidden;color:#fff;
      background:linear-gradient(115deg,{sa} 0%,#0a0f1a 42%,#0a0f1a 58%,{sb} 100%);}}
    .split{{position:absolute;inset:0;{_GRAIN}}}
    .sheen{{position:absolute;top:-20%;left:38%;width:24%;height:140%;transform:rotate(12deg);
      background:linear-gradient(90deg,transparent,rgba(255,255,255,.06),transparent);}}
    .top{{position:absolute;top:52px;width:100%;text-align:center;z-index:3}}
    .kick{{font-size:50px;letter-spacing:3px;color:#ffce4d;text-shadow:0 3px 20px rgba(255,180,0,.4)}}
    .wk{{font-size:30px;font-weight:700;letter-spacing:8px;color:#c9d6f2;margin-top:4px}}
    .row{{position:absolute;left:64px;right:64px;display:flex;align-items:center;gap:34px;z-index:3}}
    .rowA{{top:292px}} .rowB{{top:660px}}
    .tname{{font-size:86px;line-height:.9;text-transform:uppercase;text-shadow:0 5px 22px rgba(0,0,0,.6)}}
    .tsub{{font-size:33px;font-weight:600;color:#cbd6ef;margin-top:12px;letter-spacing:1px}}
    .vs{{position:absolute;top:506px;left:50%;transform:translateX(-50%);width:128px;height:128px;
      border-radius:50%;background:linear-gradient(145deg,#ff5252,#b3121a);display:flex;align-items:center;
      justify-content:center;font-size:56px;z-index:5;
      box-shadow:0 14px 36px rgba(220,20,20,.55),inset 0 3px 0 rgba(255,255,255,.35)}}
    .dvline{{position:absolute;top:569px;left:64px;right:64px;height:2px;
      background:linear-gradient(90deg,transparent,rgba(255,255,255,.35),transparent);z-index:2}}
    .foot{{position:absolute;bottom:52px;left:64px;right:64px;text-align:center;font-size:34px;font-weight:600;
      color:#e7edfb;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);
      padding:20px 26px;border-radius:18px;z-index:3;backdrop-filter:blur(2px)}}
    """
    foot = f"<div class='foot cond'>{lore}</div>" if lore else ""
    inner = f"""<div id=card><div class=split></div><div class=sheen></div>
      <div class=top><div class='kick num'>GAME OF THE WEEK</div><div class='wk cond'>{week_label}</div></div>
      <div class='row rowA'>{_crest(team_a,logo_a)}<div><div class='tname num'>{team_a}</div><div class='tsub cond'>{sub_a}</div></div></div>
      <div class=dvline></div><div class='vs num'>VS</div>
      <div class='row rowB'>{_crest(team_b,logo_b)}<div><div class='tname num'>{team_b}</div><div class='tsub cond'>{sub_b}</div></div></div>
      {foot}</div>"""
    return _doc(inner, css)


def final_score_html(winner, w_score, loser, l_score, badge, note, week_label,
                     logo_w=None, logo_l=None) -> str:
    pw, sw = theme(winner)
    css = f"""
    #card{{width:1080px;height:1080px;position:relative;overflow:hidden;color:#fff;
      background:radial-gradient(circle at 50% 12%,{sw} 0%,#0a0f1a 55%,#070b13 100%);}}
    .g{{position:absolute;inset:0;{_GRAIN}}}
    .top{{position:absolute;top:54px;width:100%;text-align:center;z-index:3}}
    .final{{font-size:58px;letter-spacing:8px;color:#fff}}
    .wk{{font-size:26px;font-weight:700;letter-spacing:6px;color:#9fb4e6;margin-top:2px}}
    .badge{{display:inline-block;margin-top:18px;font-size:28px;font-weight:700;letter-spacing:4px;
      color:#0b1220;background:#ffce4d;padding:9px 30px;border-radius:30px}}
    .row{{position:absolute;left:64px;right:64px;display:flex;align-items:center;gap:30px;z-index:3}}
    .rowW{{top:360px}} .rowL{{top:680px}}
    .nm{{font-size:70px;text-transform:uppercase;line-height:.9;flex:1}}
    .sc{{font-size:150px;line-height:.8}}
    .win .sc{{color:#ffce4d;text-shadow:0 6px 26px rgba(255,190,0,.35)}}
    .lose{{opacity:.66}}
    .dvline{{position:absolute;top:560px;left:64px;right:64px;height:2px;
      background:linear-gradient(90deg,transparent,rgba(255,255,255,.3),transparent);z-index:2}}
    .note{{position:absolute;bottom:56px;left:64px;right:64px;text-align:center;font-size:33px;font-weight:600;
      color:#dfe6f7;z-index:3}}
    """
    badge_html = f"<div class='badge cond'>{badge}</div>" if badge else ""
    note_html = f"<div class='note cond'>{note}</div>" if note else ""

    def row(cls, team, score, logo):
        return (f"<div class='row {cls['pos']} {cls['w']}'>{_crest(team,logo,150,22)}"
                f"<div class='nm num'>{team}</div><div class='sc num'>{score:g}</div></div>")
    inner = f"""<div id=card><div class=g></div>
      <div class=top><div class='final num'>FINAL</div><div class='wk cond'>{week_label}</div>{badge_html}</div>
      {row({'pos':'rowW','w':'win'}, winner, w_score, logo_w)}
      <div class=dvline></div>
      {row({'pos':'rowL','w':'lose'}, loser, l_score, logo_l)}
      {note_html}</div>"""
    return _doc(inner, css)


def record_html(kicker, big, sub, team, ghost="", logo=None) -> str:
    p, s = theme(team)
    ghost = ghost or "".join(ch for ch in big if ch.isdigit())[:3]
    css = f"""
    #card{{width:1080px;height:1080px;position:relative;overflow:hidden;color:#fff;
      background:radial-gradient(circle at 50% 40%,{p}33 0%,{s} 30%,#070b13 78%);}}
    .g{{position:absolute;inset:0;{_GRAIN}}}
    .ghost{{position:absolute;top:2%;left:50%;transform:translateX(-50%);font-size:640px;line-height:1;
      color:rgba(255,255,255,.08);z-index:1;white-space:nowrap}}
    .crest{{position:absolute;top:300px;left:50%;transform:translateX(-50%);z-index:2;opacity:.9}}
    .kick{{position:absolute;top:96px;width:100%;text-align:center;font-size:44px;letter-spacing:4px;
      color:#ffce4d;z-index:3;text-shadow:0 3px 18px rgba(255,180,0,.4)}}
    .big{{position:absolute;bottom:250px;left:60px;right:60px;text-align:center;font-size:110px;
      line-height:.92;text-transform:uppercase;z-index:3;text-shadow:0 6px 30px rgba(0,0,0,.6)}}
    .sub{{position:absolute;bottom:150px;left:80px;right:80px;text-align:center;font-size:38px;font-weight:600;
      letter-spacing:1px;color:#dfe6f7;z-index:3}}
    .team{{position:absolute;bottom:70px;width:100%;text-align:center;font-size:30px;font-weight:700;
      letter-spacing:6px;color:#9fb4e6;z-index:3;text-transform:uppercase}}
    """
    crest = f"<div class=crest>{_crest(team,logo,300,40)}</div>"
    inner = f"""<div id=card><div class=g></div><div class='ghost num'>{ghost}</div>{crest}
      <div class='kick num'>{kicker}</div>
      <div class='big num'>{big}</div>
      <div class='sub cond'>{sub}</div>
      <div class='team cond'>{team}</div></div>"""
    return _doc(inner, css)


def stat_leader_html(kicker, team, value, label, sub, ghost="MVP", logo=None) -> str:
    p, s = theme(team)
    css = f"""
    #card{{width:1080px;height:1080px;position:relative;overflow:hidden;color:#fff;
      background:radial-gradient(circle at 50% 20%,{s} 0%,#0a0f1a 60%,#070b13 100%);}}
    .g{{position:absolute;inset:0;{_GRAIN}}}
    .ghost{{position:absolute;top:120px;left:50%;transform:translateX(-50%);font-size:520px;line-height:1;
      color:{p}2e;z-index:1;white-space:nowrap}}
    .kick{{position:absolute;top:92px;width:100%;text-align:center;font-size:46px;letter-spacing:4px;
      color:#ffce4d;z-index:3}}
    .crest{{position:absolute;top:270px;left:50%;transform:translateX(-50%);z-index:2}}
    .team{{position:absolute;top:600px;width:100%;text-align:center;font-size:64px;text-transform:uppercase;z-index:3}}
    .val{{position:absolute;top:690px;width:100%;text-align:center;font-size:190px;line-height:.85;
      color:#ffce4d;z-index:3;text-shadow:0 6px 30px rgba(255,190,0,.35)}}
    .label{{position:absolute;bottom:118px;width:100%;text-align:center;font-size:36px;letter-spacing:5px;
      color:#cdd8f2;z-index:3;text-transform:uppercase}}
    .sub{{position:absolute;bottom:62px;width:100%;text-align:center;font-size:30px;font-weight:600;
      color:#9fb4e6;z-index:3}}
    """
    inner = f"""<div id=card><div class=g></div><div class='ghost num'>{ghost}</div>
      <div class='kick num'>{kicker}</div>
      <div class=crest>{_crest(team,logo,240,32)}</div>
      <div class='team num'>{team}</div>
      <div class='val num'>{value}</div>
      <div class='label cond'>{label}</div>
      <div class='sub cond'>{sub}</div></div>"""
    return _doc(inner, css)


def meme_html(top_text, bottom_text, team="") -> str:
    p, s = theme(team or top_text)
    css = f"""
    #card{{width:1080px;height:1080px;position:relative;overflow:hidden;color:#fff;
      background:linear-gradient(160deg,{p},{s});}}
    .g{{position:absolute;inset:0;{_GRAIN}}}
    .t{{position:absolute;left:50px;right:50px;text-align:center;text-transform:uppercase;
      font-size:88px;line-height:1.02;color:#fff;z-index:3;
      -webkit-text-stroke:5px #000;paint-order:stroke fill;text-shadow:0 6px 20px rgba(0,0,0,.5)}}
    .top{{top:70px}} .bot{{bottom:80px}}
    """
    top = f"<div class='t top num'>{top_text}</div>" if top_text else ""
    bot = f"<div class='t bot num'>{bottom_text}</div>" if bottom_text else ""
    return _doc(f"<div id=card><div class=g></div>{top}{bot}</div>", css)
