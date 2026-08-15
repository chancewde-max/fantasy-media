"""Tests for the Insider fabrication scheduling helper (no network)."""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pipeline import _previous_checkpoint

HOURS = [7, 12, 18]


def test_checkpoint_same_day_after_first_slot():
    now = datetime(2026, 8, 15, 9, 30, tzinfo=timezone.utc)
    assert _previous_checkpoint(HOURS, now) == datetime(2026, 8, 15, 7, 0, tzinfo=timezone.utc)


def test_checkpoint_same_day_after_last_slot():
    now = datetime(2026, 8, 15, 20, 0, tzinfo=timezone.utc)
    assert _previous_checkpoint(HOURS, now) == datetime(2026, 8, 15, 18, 0, tzinfo=timezone.utc)


def test_checkpoint_before_first_slot_falls_back_to_yesterday():
    now = datetime(2026, 8, 15, 3, 0, tzinfo=timezone.utc)
    assert _previous_checkpoint(HOURS, now) == datetime(2026, 8, 14, 18, 0, tzinfo=timezone.utc)


def test_checkpoint_exactly_on_a_slot_counts_as_that_slot():
    now = datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc)
    assert _previous_checkpoint(HOURS, now) == datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc)
