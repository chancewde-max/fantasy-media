"""Tests for the export-backed league history layer."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import league_history as lh


def test_current_year_is_latest_season():
    assert lh.current_year() == 2026


def test_owner_teams_follows_renames():
    teams = lh.owner_teams()
    # Ethan went back-to-back champ then renamed to "Back to back" for 2026.
    assert teams["ethan"][2024] == "Njigbas in Paris"
    assert teams["ethan"][2026] == "Back to back"
    assert teams["chance"][2026] == "The Island boys"


def test_season_results_are_regular_season_only_no_preseason():
    sr = lh.season_results()
    # 2024 + 2025 are complete; 2026 is preseason (all 0-0) and must be excluded.
    assert set(sr) == {2024, 2025}
    total = sum(len(games) for weeks in sr.values() for games in weeks.values())
    assert total == 140  # 2 seasons * 14 weeks * 5 games


def test_playoff_facts_name_the_champion():
    facts = lh.playoff_facts()
    assert any("championship" in f.lower() for f in facts[2024])
    assert any("championship" in f.lower() for f in facts[2025])


def test_manager_profile_counts_championships():
    profiles = lh.manager_profiles()
    assert profiles["ethan"]["championships"] == [2024, 2025]
    assert profiles["ethan"]["current_team"] == "Back to back"


def test_league_brief_excludes_departed_managers():
    brief = lh.league_brief()
    assert "Ethan" in brief and "2x champ" in brief
    # Garren left after 2024 (no current team) — no dangling line for him.
    assert "Garren" not in brief
    # every line should name a current team owner
    assert all(" is run by " in line for line in brief.splitlines() if line)


def test_league_brief_targets_named_teams():
    brief = lh.league_brief(["The Island boys", "Back to back"])
    assert "Chance" in brief and "Ethan" in brief
    assert "Patrick" not in brief  # not one of the two named teams
