"""Pure-logic tests for event detection and ranking movement (no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.espn_client import LeagueSnapshot
from src.events import build_ranking_movement, detect_events


def _snap():
    return LeagueSnapshot(
        week=3,
        matchups=[
            {"week": 3, "home": "A", "away": "B", "home_score": 148.6, "away_score": 90.1, "final": True},
            {"week": 3, "home": "C", "away": "D", "home_score": 101.0, "away_score": 100.5, "final": True},
        ],
        standings=[
            {"rank": 1, "team": "A", "wins": 3, "losses": 0, "points_for": 400.0},
            {"rank": 2, "team": "C", "wins": 2, "losses": 1, "points_for": 350.0},
        ],
        transactions=[{"id": "x1", "date": 1, "summary": "A added Player"}],
    )


def test_detects_superlatives():
    events = detect_events(_snap())
    kinds = {e.kind for e in events}
    assert {"matchup_final", "blowout", "nailbiter", "high", "low", "transaction"} <= kinds


def test_blowout_is_biggest_margin():
    events = detect_events(_snap())
    blowout = next(e for e in events if e.kind == "blowout")
    assert blowout.data["winner"] == "A"
    assert blowout.data["margin"] == 58.5


def test_nailbiter_is_smallest_margin():
    events = detect_events(_snap())
    nb = next(e for e in events if e.kind == "nailbiter")
    assert set(nb.data["teams"]) == {"C", "D"}
    assert nb.data["margin"] == 0.5


def test_high_and_low():
    events = detect_events(_snap())
    high = next(e for e in events if e.kind == "high")
    low = next(e for e in events if e.kind == "low")
    assert high.data["team"] == "A" and high.data["score"] == 148.6
    assert low.data["team"] == "B" and low.data["score"] == 90.1


def test_dedup_keys_are_stable():
    a = detect_events(_snap())
    b = detect_events(_snap())
    assert [e.key for e in a] == [e.key for e in b]


def test_ranking_movement_arrows():
    prev = [
        {"rank": 1, "team": "C"},
        {"rank": 2, "team": "A"},
    ]
    current = [
        {"rank": 1, "team": "A", "wins": 3, "losses": 0, "points_for": 400.0},
        {"rank": 2, "team": "C", "wins": 2, "losses": 1, "points_for": 350.0},
    ]
    rows = build_ranking_movement(current, prev)
    assert rows[0]["arrow"] == "up" and rows[0]["delta"] == 1
    assert rows[1]["arrow"] == "down" and rows[1]["delta"] == 1


def test_ranking_movement_new_team():
    rows = build_ranking_movement(
        [{"rank": 1, "team": "Z", "wins": 1, "losses": 0, "points_for": 100.0}], None
    )
    assert rows[0]["arrow"] == "new"
