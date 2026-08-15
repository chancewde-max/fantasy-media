"""League memory: real head-to-head history and patterns from past seasons.

Team NAMES change year to year, but the person behind them doesn't — so
everything here is keyed to an owner (their real first name), with a map of
which team name that owner used in which season. Generators call
memory_snippet() with the CURRENT season's team name(s) involved in an event;
it resolves the owner(s), looks up real history, and returns a short line of
context an actual longtime fan would drop in passing — or an empty string if
there's nothing notable, so it never gets forced into every post.

Data entered from league history screenshots (2024, 2025 seasons) + the
existing historical-backfill playoff record. Team-name continuity across
2025->2026 was used to resolve owners for 9 of this season's 10 teams; one
2026 team ("The Island Boys") was inferred from the single unmatched 2025
name ("The Flee The Scenes") by elimination. Five 2024-only team names
(the league had 11 teams in 2024, 10 from 2025 on) couldn't be confidently
tied to a specific owner and are left out of the owner-keyed lore — they
still appear in SEASON_RESULTS for reference, just not in pattern lookups.
"""
from __future__ import annotations

CURRENT_YEAR = 2026

# ---------------------------------------------------------------------------
# owner_key -> {year: team_name_that_year}. First names only (matches the
# league's own commissioner-note voice, e.g. "Juan's squad").
# ---------------------------------------------------------------------------
OWNER_TEAMS: dict[str, dict[int, str]] = {
    "ethan": {2025: "So Good That It Hurts", 2026: "So good that it Hurts"},
    "cameron": {2025: "Flaccid Winners", 2026: "FLACCID WINNERS"},
    "josh": {2024: "Need More Beers", 2025: "Need More Beers", 2026: "Need More Beers"},
    "chance": {2025: "The Flee The Scenes", 2026: "The Island Boys"},
    "juan": {2024: "Tha Hoodie Gang", 2025: "Tha Hoodie Gang", 2026: "Tha Hoodie Gang"},
    "jacob": {2024: "B50Beast", 2025: "B50Beast", 2026: "B50Beast"},
    "jake": {2024: "Jabawockeez", 2025: "Jabawockeez", 2026: "JABAWOCKEEZ"},
    "patrick": {2024: "Patrick's Team", 2025: "Patrick's Team", 2026: "Patrick's Team"},
    "bode": {2024: "Team of Collusion", 2025: "Team of Collusion", 2026: "Team of Collusion"},
    "miles": {2025: "I Chase White Kids", 2026: "I Chase White Kids"},
}

# 2024-only teams with no confirmed owner link — kept for historical facts,
# excluded from head-to-head/pattern lookups.
UNLINKED_2024_TEAMS = {
    "The Juice is Loose in Hell", "MEAT ON MEAT", "White Diggs",
    "Njigbas in Paris", "Garren's Great Team",
}

# ---------------------------------------------------------------------------
# Regular-season weekly results, team names as they appeared THAT season.
# {year: {week: [(team_a, score_a, team_b, score_b), ...]}}
# ---------------------------------------------------------------------------
SEASON_RESULTS: dict[int, dict[int, list[tuple[str, float, str, float]]]] = {
    2024: {
        1: [("The Juice is Loose in Hell", 120.38, "B50Beast", 113.28),
            ("MEAT ON MEAT", 126.36, "Patrick's Team", 94.48),
            ("Need More Beers", 123.84, "White Diggs", 125.32),
            ("Njigbas in Paris", 103.22, "Team of Collusion", 86.86),
            ("Garren's Great Team", 165.08, "Tha Hoodie Gang", 108.66)],
        2: [("Patrick's Team", 126.54, "The Juice is Loose in Hell", 68.16),
            ("Jabawockeez", 139.28, "Need More Beers", 125.24),
            ("White Diggs", 83.98, "Njigbas in Paris", 118.22),
            ("B50Beast", 200.84, "Garren's Great Team", 110.46),
            ("Team of Collusion", 137.42, "Tha Hoodie Gang", 85.6)],
        3: [("The Juice is Loose in Hell", 109.52, "MEAT ON MEAT", 75.46),
            ("Njigbas in Paris", 128.14, "Jabawockeez", 142.76),
            ("Garren's Great Team", 99.28, "Patrick's Team", 121.64),
            ("Tha Hoodie Gang", 133.12, "White Diggs", 104.9),
            ("Team of Collusion", 125.96, "B50Beast", 92.68)],
        4: [("Need More Beers", 148.58, "Njigbas in Paris", 135.02),
            ("MEAT ON MEAT", 103.92, "Garren's Great Team", 98.94),
            ("Jabawockeez", 111.1, "Tha Hoodie Gang", 118.2),
            ("Patrick's Team", 90.1, "Team of Collusion", 140.34),
            ("White Diggs", 126.14, "B50Beast", 76.78)],
        5: [("Garren's Great Team", 112.7, "The Juice is Loose in Hell", 115.14),
            ("Tha Hoodie Gang", 154.64, "Need More Beers", 102.04),
            ("Team of Collusion", 170.78, "MEAT ON MEAT", 88.92),
            ("B50Beast", 106.3, "Jabawockeez", 96.76),
            ("White Diggs", 102.32, "Patrick's Team", 120.74)],
        6: [("The Juice is Loose in Hell", 135.8, "Team of Collusion", 112.52),
            ("Njigbas in Paris", 105.16, "Tha Hoodie Gang", 115.58),
            ("Need More Beers", 115.4, "B50Beast", 126.76),
            ("MEAT ON MEAT", 152.32, "White Diggs", 93.12),
            ("Jabawockeez", 135.12, "Patrick's Team", 104.6)],
        7: [("White Diggs", 140.04, "The Juice is Loose in Hell", 106.02),
            ("Team of Collusion", 90.56, "Garren's Great Team", 112.08),
            ("B50Beast", 93.6, "Njigbas in Paris", 137.76),
            ("Patrick's Team", 91.54, "Need More Beers", 117.46),
            ("Jabawockeez", 110.5, "MEAT ON MEAT", 117.94)],
        8: [("The Juice is Loose in Hell", 96.12, "Jabawockeez", 135.14),
            ("Tha Hoodie Gang", 129.5, "B50Beast", 124.98),
            ("Garren's Great Team", 125.94, "White Diggs", 106.86),
            ("Njigbas in Paris", 153.54, "Patrick's Team", 113.72),
            ("Need More Beers", 134.78, "MEAT ON MEAT", 120.06)],
        9: [("Need More Beers", 138.04, "The Juice is Loose in Hell", 130.9),
            ("White Diggs", 85.4, "Team of Collusion", 119.92),
            ("Patrick's Team", 105.22, "Tha Hoodie Gang", 134.6),
            ("Jabawockeez", 132.72, "Garren's Great Team", 162.88),
            ("MEAT ON MEAT", 133.84, "Njigbas in Paris", 147.1)],
        10: [("Njigbas in Paris", 121.28, "The Juice is Loose in Hell", 111.5),
             ("B50Beast", 141.14, "Patrick's Team", 73.64),
             ("Team of Collusion", 104.3, "Jabawockeez", 101.3),
             ("Tha Hoodie Gang", 149.94, "MEAT ON MEAT", 94.58),
             ("Garren's Great Team", 102.54, "Need More Beers", 97.7)],
        11: [("The Juice is Loose in Hell", 111.28, "Tha Hoodie Gang", 114.58),
             ("Jabawockeez", 114.94, "White Diggs", 95.08),
             ("MEAT ON MEAT", 90.74, "B50Beast", 129.16),
             ("Need More Beers", 188.4, "Team of Collusion", 140.78),
             ("Njigbas in Paris", 117.04, "Garren's Great Team", 130.62)],
        12: [("B50Beast", 122.4, "The Juice is Loose in Hell", 139.78),
             ("Patrick's Team", 115.06, "MEAT ON MEAT", 150.5),
             ("White Diggs", 121.88, "Need More Beers", 133.36),
             ("Team of Collusion", 129.42, "Njigbas in Paris", 92.26),
             ("Tha Hoodie Gang", 75.46, "Garren's Great Team", 126.82)],
        13: [("The Juice is Loose in Hell", 107.02, "Patrick's Team", 112.8),
             ("Need More Beers", 137.94, "Jabawockeez", 130.86),
             ("Njigbas in Paris", 132.42, "White Diggs", 90.18),
             ("Garren's Great Team", 132.82, "B50Beast", 116.5),
             ("Tha Hoodie Gang", 100.3, "Team of Collusion", 108.56)],
        14: [("MEAT ON MEAT", 92.86, "The Juice is Loose in Hell", 194.18),
             ("Jabawockeez", 105.74, "Njigbas in Paris", 118.02),
             ("Patrick's Team", 129.32, "Garren's Great Team", 112.1),
             ("White Diggs", 161.18, "Tha Hoodie Gang", 124.9),
             ("B50Beast", 92.86, "Team of Collusion", 119.52)],
    },
    2025: {
        1: [("The Flee The Scenes", 116.96, "Tha Hoodie Gang", 87.92),
            ("So Good That It Hurts", 123.28, "Team of Collusion", 95.42),
            ("B50Beast", 138.22, "Need More Beers", 109.12),
            ("Patrick's Team", 123.56, "I Chase White Kids", 122.58),
            ("Flaccid Winners", 126.22, "Jabawockeez", 110.74)],
        2: [("I Chase White Kids", 157.6, "The Flee The Scenes", 172.5),
            ("B50Beast", 116.48, "So Good That It Hurts", 129.14),
            ("Team of Collusion", 104.7, "Patrick's Team", 125.02),
            ("Need More Beers", 120.6, "Flaccid Winners", 126.1),
            ("Jabawockeez", 95.28, "Tha Hoodie Gang", 106.54)],
        3: [("The Flee The Scenes", 132.02, "Team of Collusion", 130.72),
            ("So Good That It Hurts", 141.54, "Patrick's Team", 117.22),
            ("Flaccid Winners", 104.3, "B50Beast", 97.16),
            ("Tha Hoodie Gang", 101.38, "Need More Beers", 139.14),
            ("Jabawockeez", 114.02, "I Chase White Kids", 111.72)],
        4: [("Patrick's Team", 121.26, "The Flee The Scenes", 138.68),
            ("Flaccid Winners", 151.52, "So Good That It Hurts", 112.5),
            ("B50Beast", 157.9, "Tha Hoodie Gang", 130.82),
            ("Team of Collusion", 162.88, "Jabawockeez", 125.74),
            ("Need More Beers", 96.32, "I Chase White Kids", 94.32)],
        5: [("So Good That It Hurts", 107.9, "The Flee The Scenes", 145.08),
            ("Tha Hoodie Gang", 139.92, "Flaccid Winners", 140.74),
            ("Jabawockeez", 122.72, "Patrick's Team", 112.82),
            ("I Chase White Kids", 138.84, "B50Beast", 105.02),
            ("Need More Beers", 153.02, "Team of Collusion", 131.2)],
        6: [("The Flee The Scenes", 128.7, "Jabawockeez", 170.46),
            ("Tha Hoodie Gang", 116.24, "So Good That It Hurts", 120.52),
            ("Flaccid Winners", 99.34, "I Chase White Kids", 96.08),
            ("Patrick's Team", 70.3, "Need More Beers", 154.04),
            ("B50Beast", 165.68, "Team of Collusion", 112.08)],
        7: [("Need More Beers", 140.06, "The Flee The Scenes", 165.96),
            ("So Good That It Hurts", 111.94, "Jabawockeez", 164.26),
            ("I Chase White Kids", 100.22, "Tha Hoodie Gang", 134.14),
            ("Team of Collusion", 93.48, "Flaccid Winners", 96.34),
            ("B50Beast", 139.24, "Patrick's Team", 106.94)],
        8: [("The Flee The Scenes", 141.42, "B50Beast", 90.76),
            ("I Chase White Kids", 67.88, "So Good That It Hurts", 185.32),
            ("Jabawockeez", 132.38, "Need More Beers", 131.92),
            ("Tha Hoodie Gang", 123.06, "Team of Collusion", 109.0),
            ("Flaccid Winners", 106.52, "Patrick's Team", 134.52)],
        9: [("Flaccid Winners", 168.7, "The Flee The Scenes", 157.66),
            ("So Good That It Hurts", 94.68, "Need More Beers", 100.86),
            ("Team of Collusion", 123.8, "I Chase White Kids", 129.0),
            ("B50Beast", 131.48, "Jabawockeez", 129.82),
            ("Patrick's Team", 89.22, "Tha Hoodie Gang", 116.24)],
        10: [("Tha Hoodie Gang", 179.0, "The Flee The Scenes", 79.94),
             ("Team of Collusion", 119.78, "So Good That It Hurts", 131.32),
             ("Need More Beers", 174.5, "B50Beast", 89.84),
             ("I Chase White Kids", 119.9, "Patrick's Team", 95.64),
             ("Jabawockeez", 111.1, "Flaccid Winners", 102.22)],
        11: [("The Flee The Scenes", 68.12, "I Chase White Kids", 88.24),
             ("So Good That It Hurts", 143.0, "B50Beast", 93.54),
             ("Patrick's Team", 132.78, "Team of Collusion", 115.72),
             ("Flaccid Winners", 110.36, "Need More Beers", 114.64),
             ("Tha Hoodie Gang", 108.4, "Jabawockeez", 106.3)],
        12: [("Team of Collusion", 135.32, "The Flee The Scenes", 106.72),
             ("Patrick's Team", 102.72, "So Good That It Hurts", 167.36),
             ("B50Beast", 104.68, "Flaccid Winners", 126.56),
             ("Need More Beers", 101.76, "Tha Hoodie Gang", 164.72),
             ("I Chase White Kids", 103.14, "Jabawockeez", 108.38)],
        13: [("The Flee The Scenes", 106.74, "Patrick's Team", 91.22),
             ("So Good That It Hurts", 121.3, "Flaccid Winners", 82.62),
             ("Tha Hoodie Gang", 114.62, "B50Beast", 137.24),
             ("Jabawockeez", 117.44, "Team of Collusion", 88.26),
             ("I Chase White Kids", 120.44, "Need More Beers", 124.18)],
        14: [("The Flee The Scenes", 102.46, "So Good That It Hurts", 82.9),
             ("Flaccid Winners", 142.56, "Tha Hoodie Gang", 183.64),
             ("Patrick's Team", 153.84, "Jabawockeez", 138.74),
             ("B50Beast", 57.6, "I Chase White Kids", 113.56),
             ("Team of Collusion", 51.6, "Need More Beers", 116.44)],
    },
}

# Playoff facts (from the historical backfill's own data) — short flavor
# lines, not fed into head-to-head math since playoffs aren't in
# SEASON_RESULTS above.
PLAYOFF_FACTS: dict[int, list[str]] = {
    2024: [
        "In the 2024 playoffs, MEAT ON MEAT upset the #1 seed Team of Collusion 148.24-102.50 in round one.",
        "Njigbas in Paris won the 2024 championship over Need More Beers, 249.28-232.56.",
    ],
    2025: [
        "So Good That It Hurts needed a nail-biter to survive B50Beast in the 2025 playoffs, 156.90-154.86.",
        "Flaccid Winners upset the #1 seed Need More Beers 150.30-135.80 in the 2025 semifinals.",
        "So Good That It Hurts won the 2025 championship over Flaccid Winners, 257.42-212.70.",
    ],
}


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
