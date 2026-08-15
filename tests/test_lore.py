"""Tests for league lore: head-to-head, pattern detection, and the
current-season-team-name -> owner resolution that makes it all work despite
team names changing every year."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.lore import (
    _owner_for,
    head_to_head,
    late_collapse_note,
    memory_snippet,
    rivalry_note,
    select_game_of_the_week,
)


def test_owner_resolves_from_current_season_team_name():
    assert _owner_for("JABAWOCKEEZ", 2026) == "jake"
    assert _owner_for("So good that it Hurts", 2026) == "ethan"


def test_owner_resolves_2026_rename():
    assert _owner_for("The Island Boys", 2026) == "chance"


def test_unknown_team_name_resolves_to_none():
    assert _owner_for("Not A Real Team", 2026) is None


def test_head_to_head_is_symmetric():
    h1 = head_to_head("jake", "josh")
    h2 = head_to_head("josh", "jake")
    assert h1["wins"] == h2["losses"]
    assert h1["losses"] == h2["wins"]
    assert len(h1["games"]) == len(h2["games"]) > 0


def test_rivalry_note_names_the_leader():
    note = rivalry_note("jake", "josh")
    assert note is not None
    assert "Jake" in note and "Josh" in note


def test_rivalry_note_none_below_min_games():
    # ethan and josh have only met twice in the recorded data.
    assert rivalry_note("ethan", "josh") is None


def test_late_collapse_note_flags_a_real_pattern():
    # cameron (Flaccid Winners) is a known real fade: strong through Week 9,
    # weak from Week 10 on, across both recorded seasons.
    note = late_collapse_note("cameron")
    assert note is not None
    assert "fade late" in note


def test_memory_snippet_empty_when_nothing_notable():
    assert memory_snippet(["Not A Real Team"]) == ""


def test_memory_snippet_combines_rivalry_and_pattern():
    snippet = memory_snippet(["So good that it Hurts", "FLACCID WINNERS"])
    assert snippet  # non-empty: cameron has a flagged late-season pattern


def test_gotw_picks_the_rivalry_matchup_over_a_random_one():
    matchups = [
        {"home": "JABAWOCKEEZ", "away": "Need More Beers", "final": False},
        {"home": "Patrick's Team", "away": "Team of Collusion", "final": False},
    ]
    standings = [
        {"team": "JABAWOCKEEZ", "rank": 3},
        {"team": "Need More Beers", "rank": 4},
        {"team": "Patrick's Team", "rank": 9},
        {"team": "Team of Collusion", "rank": 10},
    ]
    pick = select_game_of_the_week(matchups, standings)
    assert {pick["team_a"], pick["team_b"]} == {"JABAWOCKEEZ", "Need More Beers"}
    assert pick["lore"]


def test_gotw_none_with_no_matchups():
    assert select_game_of_the_week([], []) is None
