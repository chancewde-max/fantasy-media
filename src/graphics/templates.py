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
    """A player-headshot hero image (transparent PNG), with a soft drop shadow.
    Empty string when we have no player image (templates then lean on crest)."""
    if not img:
        return ""
    return (f"<img src='{img}' style=\"position:absolute;{css_pos};z-index:2;"
            "filter:drop-shadow(0 24px 40px rgba(0,0,0,.6));object-fit:contain\">")


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
    .row{{position:absolute;left:60px;right:60px;display:flex;align-items:center;gap:32px;z-index:4}}
    .rowA{{top:300px}} .rowB{{top:668px}}
    .tname{{font-size:88px;line-height:.88;text-transform:uppercase;text-shadow:0 5px 24px rgba(0,0,0,.7)}}
    .tsub{{font-size:33px;font-weight:600;color:#e6ecfb;margin-top:12px;letter-spacing:1px}}
    .vs{{position:absolute;top:500px;left:50%;transform:translateX(-50%);width:132px;height:132px;
      border-radius:50%;background:linear-gradient(145deg,#ff5a5a,#a80f16);display:flex;align-items:center;
      justify-content:center;font-size:58px;z-index:6;
      box-shadow:0 0 0 8px rgba(255,255,255,.06),0 16px 40px rgba(220,20,20,.6),inset 0 3px 0 rgba(255,255,255,.4)}}
    .dvline{{position:absolute;top:566px;left:60px;right:60px;height:2px;
      background:linear-gradient(90deg,transparent,rgba(255,255,255,.4),transparent);z-index:3}}
    .foot{{position:absolute;bottom:50px;left:60px;right:60px;text-align:center;font-size:34px;font-weight:600;
      color:#fff;background:rgba(0,0,0,.32);border:1px solid rgba(255,255,255,.14);
      padding:20px 26px;border-radius:18px;z-index:4}}
    """
    foot = f"<div class='foot cond'>{lore}</div>" if lore else ""
    # heroes flank the outer edges, bleeding off-frame like a real matchup poster
    heroes = (_hero(hero_a, "left:-40px;top:150px;height:520px") +
              _hero(hero_b, "right:-40px;bottom:150px;height:520px;transform:scaleX(-1)"))
    inner = f"""<div id=card>
      <div class=spot style="left:-140px;top:120px;width:420px;height:420px;background:{pa}66"></div>
      <div class=spot style="right:-140px;bottom:120px;width:420px;height:420px;background:{pb}66"></div>
      {_shards(pa,pb)}{heroes}<div class=grain></div><div class=vig></div>
      <div class=top><div class='kick num foil'>GAME OF THE WEEK</div><div class='wk cond'>{week_label}</div></div>
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
