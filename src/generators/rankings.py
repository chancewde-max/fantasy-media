"""Power-ranking graphic with up/down movement arrows + a Claude blurb."""
from __future__ import annotations

from typing import Any

from ..graphics.render import render_rankings_card
from .claude_client import ClaudeClient

SYSTEM = (
    "You write a one-line power-rankings summary for a fantasy football "
    "league. Mention the team on top and the biggest riser. One sentence."
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
    biggest = max(risers, key=lambda r: r["delta"], default=None)
    riser_txt = f", biggest riser {biggest['team']} (+{biggest['delta']})" if biggest else ""
    blurb = claude.generate(
        SYSTEM,
        f"Week {week} power rankings. Top team: {top}{riser_txt}. Write the summary.",
        tone,
        max_tokens=120,
    )
    image_path = render_rankings_card(
        out_dir=out_dir, name=f"rankings_w{week}", week=week, rows=rows
    )
    return {"blurb": blurb, "image_path": image_path}
