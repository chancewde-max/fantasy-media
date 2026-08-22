"""Authoritative league history, loaded from the real ESPN export.

`data/league_history.json` is a full multi-season export of the league
(identity, users, rosters, weekly matchups, standings, drafts). This module
parses it once and exposes the pieces the rest of the bot needs:

  * OWNER_TEAMS   — {first_name: {year: team_name}}, the owner->team mapping
                    the commissioner voice uses, built from the export's
                    stable per-owner IDs (so a rename is followed correctly).
  * SEASON_RESULTS — {year: {week: [(team_a, score_a, team_b, score_b)]}}
                    regular-season games only (weeks before playoffs).
  * PLAYOFF_FACTS — {year: [str]} short factual playoff lines.
  * manager_profiles() / league_brief() — grounded, factual context about
    each manager's real record and tendencies, so the Insider can write
    rumors that fit the actual league instead of generic filler.

The only thing that can't come from the export is the managers' real first
names (ESPN only stores handles), so OWNER_FIRST_NAMES maps the stable owner
IDs to first names — confirmed directly by the league. Everything else is
derived from the data, so a fresh export just needs to be dropped in.

Defensive by design: if the export file is missing or unreadable, every
accessor returns empty structures and the bot simply runs without history
rather than crashing.
"""
from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path

log = logging.getLogger(__name__)

# Stable ESPN owner IDs -> real first names (the one hand-maintained bit;
# names aren't in the export). Confirmed by the league's owners.
OWNER_FIRST_NAMES: dict[str, str] = {
    "espn_user:{21807BDB-1128-4350-807B-DB1128C3507D}": "chance",
    "espn_user:{39282AA0-BD00-4B70-A82A-A0BD008B70C3}": "miles",
    "espn_user:{5B2A51DB-DD76-4225-A278-6AB3B297EA8A}": "garren",
    "espn_user:{9A37A6F4-8125-4F0A-ADC8-AC644457E469}": "patrick",
    "espn_user:{1C7BBEED-61A2-4E76-BBBE-ED61A21E76A0}": "cameron",
    "espn_user:{1A03CB64-FDB7-4199-A19F-5C1B6AE24F27}": "jake",
    "espn_user:{15056095-7AC0-4D0F-8560-957AC08D0FF4}": "bode",
    "espn_user:{89FD777E-04FF-484F-AFC1-DBFF12D21B8B}": "ethan",
    "espn_user:{696653FC-53AB-47FB-A653-FC53AB57FB17}": "jacob",
    "espn_user:{7FD95749-F488-4A2C-9709-0E50CE33D5CB}": "juan",
    "espn_user:{62BCA7DA-0F36-4B27-A309-1E5C200D238B}": "josh",
}


def _export_path() -> Path:
    override = os.environ.get("LEAGUE_HISTORY_PATH")
    if override:
        return Path(override)
    # repo_root/data/league_history.json  (this file is repo_root/src/…)
    return Path(__file__).resolve().parents[1] / "data" / "league_history.json"


@lru_cache(maxsize=1)
def _load() -> dict:
    path = _export_path()
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        log.warning("League history export not found at %s — running without history.", path)
        return {}
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Could not read league history export (%s) — running without history.", exc)
        return {}


def _clean_name(name: str) -> str:
    """Tidy a team name for display: trim and drop stray decoration."""
    return (name or "").replace("☝\U0001f3fc", "").strip()  # ☝🏼 seen in one name


def _seasons() -> dict:
    return _load().get("seasons", {}) or {}


def current_year() -> int:
    years = [int(y) for y in _seasons()]
    return max(years) if years else 2026


# ---------------------------------------------------------------------------
# Core per-season extraction
# ---------------------------------------------------------------------------
def _roster_index(season: dict) -> dict[int, dict]:
    """roster_id -> {team, owner_id, first_name, wins, losses, ties, points,
    points_against, final_rank, seed}."""
    idx: dict[int, dict] = {}
    for r in season.get("rosters", []):
        meta = r.get("metadata", {})
        st = r.get("settings", {})
        oid = r.get("owner_id")
        idx[r["roster_id"]] = {
            "team": _clean_name(meta.get("team_name", "")),
            "owner_id": oid,
            "first_name": OWNER_FIRST_NAMES.get(oid),
            "wins": st.get("wins", 0),
            "losses": st.get("losses", 0),
            "ties": st.get("ties", 0),
            "points": st.get("fpts", 0.0),
            "points_against": st.get("fpts_against", 0.0),
            "final_rank": _to_int(meta.get("final_rank")),
            "seed": _to_int(meta.get("playoff_seed")),
            "total_moves": st.get("total_moves", 0),
        }
    return idx


def _to_int(v):
    try:
        n = int(v)
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def _playoff_week_start(season: dict) -> int:
    return season.get("league", {}).get("settings", {}).get("playoff_week_start", 15)


def _grouped_week(entries: list[dict]) -> list[tuple[dict, dict]]:
    """Pair up a week's per-roster entries by matchup_id."""
    by_mid: dict = {}
    for e in entries:
        by_mid.setdefault(e.get("matchup_id"), []).append(e)
    return [(p[0], p[1]) for p in by_mid.values() if len(p) == 2]


def _score(entry: dict) -> float:
    pts = entry.get("points")
    if pts is None:
        pts = entry.get("custom_points") or 0.0
    return round(float(pts), 2)


# ---------------------------------------------------------------------------
# Public data structures (mirrors what lore.py used to hardcode)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def owner_teams() -> dict[str, dict[int, str]]:
    """{first_name: {year: team_name}} across every season in the export."""
    out: dict[str, dict[int, str]] = {}
    for yr, season in _seasons().items():
        year = int(yr)
        for r in _roster_index(season).values():
            fn = r["first_name"]
            if not fn:
                continue
            out.setdefault(fn, {})[year] = r["team"]
    return out


@lru_cache(maxsize=1)
def season_results() -> dict[int, dict[int, list[tuple[str, float, str, float]]]]:
    """Regular-season results only (weeks before playoffs), team names as they
    appeared that season."""
    out: dict[int, dict[int, list]] = {}
    for yr, season in _seasons().items():
        year = int(yr)
        pw = _playoff_week_start(season)
        ridx = _roster_index(season)
        weeks: dict[int, list] = {}
        for wk, entries in season.get("matchups_by_week", {}).items():
            w = int(wk)
            if w >= pw:
                continue
            games = []
            for a, b in _grouped_week(entries):
                ta = ridx.get(a["roster_id"], {}).get("team")
                tb = ridx.get(b["roster_id"], {}).get("team")
                sa, sb = _score(a), _score(b)
                # Skip unplayed games (both 0) — e.g. the current season's
                # not-yet-played weeks in a preseason export — so they don't
                # count as real results in head-to-head math.
                if ta and tb and not (sa == 0 and sb == 0):
                    games.append((ta, sa, tb, sb))
            if games:
                weeks[w] = games
        if weeks:
            out[year] = weeks
    return out


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


@lru_cache(maxsize=1)
def playoff_facts() -> dict[int, list[str]]:
    """Short factual playoff lines per season, derived from final ranks and
    the playoff-week matchups."""
    out: dict[int, list[str]] = {}
    for yr, season in _seasons().items():
        year = int(yr)
        pw = _playoff_week_start(season)
        ridx = _roster_index(season)
        weeks = {int(w): e for w, e in season.get("matchups_by_week", {}).items() if int(w) >= pw}
        if not weeks:
            continue
        facts: list[str] = []
        champ = next((r for r in ridx.values() if r["final_rank"] == 1), None)
        runner = next((r for r in ridx.values() if r["final_rank"] == 2), None)

        # Championship game = last playoff week, the matchup with the champion.
        final_week = max(weeks)
        champ_game = None
        for a, b in _grouped_week(weeks[final_week]):
            ra, rb = ridx.get(a["roster_id"]), ridx.get(b["roster_id"])
            if champ and ra and rb and champ["team"] in (ra["team"], rb["team"]) \
                    and runner and runner["team"] in (ra["team"], rb["team"]):
                champ_game = (a, b, ra, rb)
                break
        if champ and champ_game:
            a, b, ra, rb = champ_game
            cs = _score(a) if ra["team"] == champ["team"] else _score(b)
            rs = _score(b) if ra["team"] == champ["team"] else _score(a)
            facts.append(
                f"{champ['team']} won the {year} championship over {runner['team']}, {cs}-{rs}."
            )
        elif champ:
            facts.append(f"{champ['team']} won the {year} championship.")

        # #1 overall seed that didn't win it all — the classic choke storyline.
        top_seed = next((r for r in ridx.values() if r["seed"] == 1), None)
        if top_seed and top_seed.get("final_rank") and top_seed["final_rank"] > 1:
            facts.append(
                f"{top_seed['team']} earned the #1 seed in {year} but finished "
                f"{_ordinal(top_seed['final_rank'])}."
            )

        # Biggest round-one upset (lowest seed beating a higher seed by the
        # largest seed gap) in the first playoff week.
        first_week = min(weeks)
        best_gap = 0
        upset = None
        for a, b in _grouped_week(weeks[first_week]):
            ra, rb = ridx.get(a["roster_id"]), ridx.get(b["roster_id"])
            if not (ra and rb and ra["seed"] and rb["seed"]):
                continue
            wa = _score(a) > _score(b)
            win, lose = (ra, rb) if wa else (rb, ra)
            gap = win["seed"] - lose["seed"]  # positive => lower seed won
            if gap > best_gap:
                best_gap = gap
                ws = _score(a) if wa else _score(b)
                ls = _score(b) if wa else _score(a)
                upset = (win, lose, ws, ls)
        if upset:
            win, lose, ws, ls = upset
            facts.append(
                f"In the {year} playoffs, {win['team']} (#{win['seed']} seed) upset "
                f"{lose['team']} (#{lose['seed']} seed) {ws}-{ls} in round one."
            )

        if facts:
            out[year] = facts
    return out


# ---------------------------------------------------------------------------
# Manager tendencies + league brief (for the Insider)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def manager_profiles() -> dict[str, dict]:
    """{first_name: profile} — a factual summary of each manager's real
    league record, for grounding Insider rumors in reality."""
    cy = current_year()
    profiles: dict[str, dict] = {}
    for fn, teams in owner_teams().items():
        profiles[fn] = {
            "first_name": fn,
            "current_team": teams.get(cy),
            "team_names": teams,
            "seasons_played": sorted(teams.keys()),
            "championships": [],
            "finishes": {},          # year -> final_rank
            "career_wins": 0,
            "career_losses": 0,
        }

    for yr, season in _seasons().items():
        year = int(yr)
        for r in _roster_index(season).values():
            fn = r["first_name"]
            if not fn or fn not in profiles:
                continue
            p = profiles[fn]
            p["career_wins"] += r["wins"]
            p["career_losses"] += r["losses"]
            if r["final_rank"]:
                p["finishes"][year] = r["final_rank"]
                if r["final_rank"] == 1:
                    p["championships"].append(year)
    return profiles


def _record_str(w: int, l: int) -> str:
    return f"{w}-{l}"


def manager_brief(first_name: str, year: int | None = None) -> str:
    """One-line factual dossier on a single manager, current-team framed."""
    p = manager_profiles().get(first_name)
    if not p:
        return ""
    year = year or current_year()
    team = p["team_names"].get(year) or p.get("current_team")
    if not team:
        return ""  # not in the league this season — no current-team framing
    bits: list[str] = [f"{team} is run by {first_name.capitalize()}"]
    if p["championships"]:
        chips = ", ".join(str(y) for y in sorted(p["championships"]))
        bits.append(f"{len(p['championships'])}x champ ({chips})")
    # last completed season's finish
    past = {y: r for y, r in p["finishes"].items() if y < year}
    if past:
        ly = max(past)
        bits.append(f"finished {_ordinal(past[ly])} in {ly}")
    if p["career_wins"] or p["career_losses"]:
        bits.append(f"career {_record_str(p['career_wins'], p['career_losses'])}")
    return "; ".join(bits) + "." if bits else ""


def league_brief(team_names: list[str] | None = None, year: int | None = None) -> str:
    """Factual context block for the Insider: dossiers on the managers
    involved (or the whole league if none given), so rumors sound like they
    come from someone who actually follows this league."""
    year = year or current_year()
    name_to_owner = {}
    for fn, teams in owner_teams().items():
        t = teams.get(year)
        if t:
            name_to_owner[t.strip().lower()] = fn

    owners: list[str] = []
    if team_names:
        for t in team_names:
            fn = name_to_owner.get((t or "").strip().lower())
            if fn and fn not in owners:
                owners.append(fn)
    if not owners:
        owners = list(manager_profiles().keys())

    lines = [manager_brief(fn, year) for fn in owners]
    return "\n".join(l for l in lines if l)
