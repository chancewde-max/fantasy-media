"""League memory: real head-to-head history and patterns from past seasons.

Team NAMES change year to year, but the person behind them doesn't — so
everything here is keyed to an owner (their real first name), with a map of
which team name that owner used in which season. Generators call
memory_snippet() with the CURRENT season's team name(s) involved in an event;
it resolves the owner(s), looks up real history, and returns a short line of
context an actual longtime fan would drop in passing — or an empty string if
there's nothing notable, so it never gets forced into every post.

All of the underlying data — the owner->team-name mapping, the weekly
results, and the playoff facts — now comes straight from the real ESPN league
export (see league_history.py), instead of being transcribed from
screenshots. That keeps renames (e.g. an owner rebranding their team each
year) and results authoritative and self-updating: drop in a fresh export and
the memory follows.
"""
from __future__ import annotations

from . import league_history

CURRENT_YEAR = league_history.current_year()

# owner_key (first name) -> {year: team_name_that_year}, straight from the
# export. First names match the league's own commissioner-note voice
# (e.g. "Juan's squad"). Renames across seasons are followed automatically
# because the export keys everything to a stable per-owner ID.
OWNER_TEAMS: dict[str, dict[int, str]] = league_history.owner_teams()

# Regular-season weekly results and playoff facts, both derived from the
# real export (team names exactly as they appeared that season).
# SEASON_RESULTS: {year: {week: [(team_a, score_a, team_b, score_b), ...]}}
SEASON_RESULTS: dict[int, dict[int, list[tuple[str, float, str, float]]]] = (
    league_history.season_results()
)

# Playoff facts (champion, #1-seed chokes, round-one upsets) — short flavor
# lines, generated from final ranks + playoff-week matchups, not fed into the
# regular-season head-to-head math above.
PLAYOFF_FACTS: dict[int, list[str]] = league_history.playoff_facts()


def _norm(name: str) -> str:
    return name.strip().lower()


def _owner_for(team_name: str, year: int) -> str | None:
    n = _norm(team_name)
    for owner, years in OWNER_TEAMS.items():
        if _norm(years.get(year, "")) == n:
            return owner
    return None


def _owner_all_names(owner: str) -> set[str]:
    return {_norm(name) for name in OWNER_TEAMS.get(owner, {}).values()}


def _owner_games(owner: str) -> list[dict]:
    """Every regular-season game this owner (under any of their team names,
    any season) has played, from the owner's perspective."""
    names = _owner_all_names(owner)
    games = []
    for year, weeks in SEASON_RESULTS.items():
        for week, matchups in weeks.items():
            for a, a_score, b, b_score in matchups:
                if _norm(a) in names:
                    me, opp, my_score, opp_score = a, b, a_score, b_score
                elif _norm(b) in names:
                    me, opp, my_score, opp_score = b, a, b_score, a_score
                else:
                    continue
                games.append({
                    "year": year, "week": week, "opponent": opp,
                    "opponent_owner": _owner_for(opp, year),
                    "my_score": my_score, "opp_score": opp_score,
                    "won": my_score > opp_score,
                })
    return games


def head_to_head(owner_a: str, owner_b: str) -> dict:
    games = [g for g in _owner_games(owner_a) if g["opponent_owner"] == owner_b]
    wins = sum(1 for g in games if g["won"])
    return {"games": games, "wins": wins, "losses": len(games) - wins}


def _split_record(games: list[dict], week_min: int, week_max: int) -> tuple[int, int]:
    subset = [g for g in games if week_min <= g["week"] <= week_max]
    wins = sum(1 for g in subset if g["won"])
    return wins, len(subset) - wins


def late_collapse_note(owner: str, early_end: int = 9, min_games: int = 6) -> str | None:
    """Early-season win rate vs Week 10+ win rate, combined across seasons.
    Flags a real, sizeable drop-off — not noise."""
    games = _owner_games(owner)
    early_w, early_l = _split_record(games, 1, early_end)
    late_w, late_l = _split_record(games, early_end + 1, 99)
    if early_w + early_l < 3 or late_w + late_l < 3 or early_w + early_l + late_w + late_l < min_games:
        return None
    early_rate = early_w / (early_w + early_l)
    late_rate = late_w / (late_w + late_l)
    if early_rate - late_rate >= 0.35:
        name = owner.capitalize()
        return (
            f"{name}'s teams historically fade late — {early_w}-{early_l} through "
            f"Week {early_end} but {late_w}-{late_l} from Week {early_end + 1} on, "
            "across the last two seasons."
        )
    if late_rate - early_rate >= 0.35:
        name = owner.capitalize()
        return (
            f"{name}'s teams historically turn it on late — {early_w}-{early_l} "
            f"through Week {early_end} but {late_w}-{late_l} from Week {early_end + 1} "
            "on, across the last two seasons."
        )
    return None


def rivalry_note(owner_a: str, owner_b: str, min_games: int = 3) -> str | None:
    h2h = head_to_head(owner_a, owner_b)
    if len(h2h["games"]) < min_games:
        return None
    a, b = owner_a.capitalize(), owner_b.capitalize()
    w, l = h2h["wins"], h2h["losses"]
    if w == l:
        return f"{a} and {b} are dead even all-time, {w}-{l}."
    leader, trailer, lw, ll = (a, b, w, l) if w > l else (b, a, l, w)
    return f"{leader} leads the all-time series over {trailer} {lw}-{ll}."


def memory_snippet(team_names: list[str], year: int = CURRENT_YEAR) -> str:
    """Short league-memory context for the given (current-season) team
    name(s), for a generator to weave into a post naturally. Empty string if
    nothing notable is on record — never force lore into every post."""
    owners = []
    for name in team_names:
        owner = _owner_for(name, year)
        if owner and owner not in owners:
            owners.append(owner)

    notes: list[str] = []
    if len(owners) == 2:
        note = rivalry_note(*owners)
        if note:
            notes.append(note)
    for owner in owners:
        note = late_collapse_note(owner)
        if note:
            notes.append(note)

    return " ".join(notes)


def select_game_of_the_week(
    matchups: list[dict], standings: list[dict], year: int = CURRENT_YEAR,
) -> dict | None:
    """Pick the week's marquee matchup — a real rivalry first, then a team on
    a known pattern, then falling back to whichever pairing is closest in
    the current standings. Works on matchups before they're final, so this
    is a preview pick, not a recap of who already won.

    Returns {"team_a", "team_b", "lore"} (lore may be "") or None if there
    are no matchups this week.
    """
    if not matchups:
        return None

    rank_by_team = {s["team"]: s["rank"] for s in standings}
    best: dict | None = None
    best_score = -1.0

    for m in matchups:
        a, b = m.get("home"), m.get("away")
        if not a or not b:
            continue
        owner_a, owner_b = _owner_for(a, year), _owner_for(b, year)
        lore = ""
        score = 0.0

        if owner_a and owner_b:
            note = rivalry_note(owner_a, owner_b)
            if note:
                h2h = head_to_head(owner_a, owner_b)
                lore = note
                score = 100 - abs(h2h["wins"] - h2h["losses"])
            else:
                pattern_notes = [
                    n for n in (late_collapse_note(owner_a), late_collapse_note(owner_b)) if n
                ]
                if pattern_notes:
                    lore = " ".join(pattern_notes)
                    score = 50

        if not lore:
            ra, rb = rank_by_team.get(a), rank_by_team.get(b)
            if ra and rb:
                score = max(0, 30 - abs(ra - rb) * 3)

        if score > best_score:
            best_score = score
            best = {"team_a": a, "team_b": b, "lore": lore}

    return best
