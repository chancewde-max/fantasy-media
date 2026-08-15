"""Power-ranking graphic with up/down movement arrows + a Claude blurb."""
from __future__ import annotations

from typing import Any

from ..graphics.render import render_rankings_card
from ..lore import memory_snippet
from .claude_client import ClaudeClient

SYSTEM = (
    "You write a one-line power-rankings summary for a fantasy football "
    "league. Mention the team on top and the biggest riser. One sentence. "
    "You may be given 'League memory' — real history about these teams. "
    "Only work it in when it actually fits, like a fan who's followed the "
    "league for years — don't force it."
)


def generate_rankings(
    claude: ClaudeClient,
    rows: list[dict[str, Any]],
    week: int,
    tone: str,
    out_dir: str,
) -> dict:
    top = rows[0]["team"] if rows else "?"
    risers = [r for r in rows if r["arrow"] == "up"]
    fallers = [r for r in rows if r["arrow"] == "down"]
    biggest = max(risers, key=lambda r: r["delta"], default=None)
    biggest_faller = max(fallers, key=lambda r: r["delta"], default=None)
    riser_txt = f", biggest riser {biggest['team']} (+{biggest['delta']})" if biggest else ""
    faller_txt = f", biggest faller {biggest_faller['team']} (-{biggest_faller['delta']})" if biggest_faller else ""

    lore_teams = [t for t in (rows[0]["team"] if rows else None, biggest_faller and biggest_faller["team"]) if t]
    lore = memory_snippet(lore_teams)
    lore_txt = f" League memory: {lore}" if lore else ""

    blurb = claude.generate(
        SYSTEM,
        f"Week {week} power rankings. Top team: {top}{riser_txt}{faller_txt}. "
        f"Write the summary.{lore_txt}",
        tone,
        max_tokens=120,
    )
    image_path = render_rankings_card(
        out_dir=out_dir, name=f"rankings_w{week}", week=week, rows=rows
    )
    return {"blurb": blurb, "image_path": image_path}
