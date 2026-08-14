"""Event detection.

Turns a LeagueSnapshot into a list of Event objects. Each Event has a stable
`key` used for de-duplication so re-detecting the same thing is a no-op.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .espn_client import LeagueSnapshot


@dataclass
class Event:
    kind: str            # matchup_final | blowout | nailbiter | high | low | transaction | standings
    key: str             # stable de-dup key
    title: str           # short human summary
    data: dict[str, Any] = field(default_factory=dict)


def _final_matchups(snap: LeagueSnapshot) -> list[dict[str, Any]]:
    return [m for m in snap.matchups if m.get("final")]


def detect_events(snap: LeagueSnapshot) -> list[Event]:
    events: list[Event] = []
    week = snap.week
    finals = _final_matchups(snap)

    # Per-matchup results
    for m in finals:
        winner = m["home"] if m["home_score"] >= m["away_score"] else m["away"]
        loser = m["away"] if winner == m["home"] else m["home"]
        w_score = max(m["home_score"], m["away_score"])
        l_score = min(m["home_score"], m["away_score"])
        margin = round(w_score - l_score, 2)
        key = f"w{week}:matchup:{'|'.join(sorted([m['home'], m['away']]))}"
        events.append(
            Event(
                kind="matchup_final",
                key=key,
                title=f"{winner} def. {loser} {w_score}-{l_score}",
                data={
                    "week": week,
                    "winner": winner,
                    "loser": loser,
                    "winner_score": w_score,
                    "loser_score": l_score,
                    "margin": margin,
                },
            )
        )

    # Week-level superlatives (only meaningful once games are final)
    if finals:
        margins = []
        scores = []  # (team, score)
        for m in finals:
            margins.append((abs(m["home_score"] - m["away_score"]), m))
            scores.append((m["home"], m["home_score"]))
            scores.append((m["away"], m["away_score"]))

        blowout = max(margins, key=lambda x: x[0])[1]
        events.append(
            Event(
                kind="blowout",
                key=f"w{week}:blowout",
                title="Blowout of the week",
                data={
                    "week": week,
                    "winner": blowout["home"] if blowout["home_score"] >= blowout["away_score"] else blowout["away"],
                    "loser": blowout["away"] if blowout["home_score"] >= blowout["away_score"] else blowout["home"],
                    "margin": round(abs(blowout["home_score"] - blowout["away_score"]), 2),
                },
            )
        )

        nailbiter = min(margins, key=lambda x: x[0])[1]
        events.append(
            Event(
                kind="nailbiter",
                key=f"w{week}:nailbiter",
                title="Closest game of the week",
                data={
                    "week": week,
                    "teams": [nailbiter["home"], nailbiter["away"]],
                    "margin": round(abs(nailbiter["home_score"] - nailbiter["away_score"]), 2),
                },
            )
        )

        high = max(scores, key=lambda x: x[1])
        low = min(scores, key=lambda x: x[1])
        events.append(
            Event(
                kind="high",
                key=f"w{week}:high",
                title="Highest scorer",
                data={"week": week, "team": high[0], "score": high[1]},
            )
        )
        events.append(
            Event(
                kind="low",
                key=f"w{week}:low",
                title="Lowest scorer",
                data={"week": week, "team": low[0], "score": low[1]},
            )
        )

    # Transactions
    for t in snap.transactions:
        events.append(
            Event(
                kind="transaction",
                key=f"txn:{t['id']}",
                title=t["summary"],
                data={"summary": t["summary"], "date": t.get("date")},
            )
        )

    return events


def build_ranking_movement(
    current: list[dict[str, Any]], previous: list[dict[str, Any]] | None
) -> list[dict[str, Any]]:
    """Annotate current standings with movement vs previous standings.

    Returns rows: {rank, team, wins, losses, points_for, arrow, delta}.
    arrow is one of 'up' | 'down' | 'same' | 'new'.
    """
    prev_rank = {r["team"]: r["rank"] for r in (previous or [])}
    rows = []
    for r in current:
        old = prev_rank.get(r["team"])
        if old is None:
            arrow, delta = "new", 0
        elif old > r["rank"]:
            arrow, delta = "up", old - r["rank"]
        elif old < r["rank"]:
            arrow, delta = "down", r["rank"] - old
        else:
            arrow, delta = "same", 0
        rows.append({**r, "arrow": arrow, "delta": delta})
    return rows
