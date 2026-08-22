"""Tests for the Dan Orlovsky / Stephen A. Smith pundit reactions (no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.generators.pundits import generate_pundit_takes


class FakeClaude:
    def __init__(self, json_reply=None):
        self._json_reply = json_reply
        self.last_prompt = None

    def generate_json(self, system, prompt, tone, max_tokens=600):
        self.last_prompt = prompt
        return self._json_reply


def test_returns_both_fixed_personas_in_order():
    claude = FakeClaude(json_reply=[
        {"handle": "@danorlovsky7", "text": "Breaking down the tape on this one..."},
        {"handle": "@stephenasmith", "text": "Let me tell you something, brother..."},
    ])
    takes = generate_pundit_takes(claude, "some report", "roast")
    assert [t["handle"] for t in takes] == ["@danorlovsky7", "@stephenasmith"]


def test_report_body_is_in_the_prompt():
    claude = FakeClaude(json_reply=[])
    generate_pundit_takes(claude, "Team A is shopping their RB1", "roast")
    assert "Team A is shopping their RB1" in claude.last_prompt


def test_drops_an_invented_third_persona():
    claude = FakeClaude(json_reply=[
        {"handle": "@danorlovsky7", "text": "take one"},
        {"handle": "@some_random_fan", "text": "should be dropped"},
    ])
    takes = generate_pundit_takes(claude, "report", "roast")
    assert len(takes) == 1
    assert takes[0]["handle"] == "@danorlovsky7"


def test_normalizes_missing_at_sign():
    claude = FakeClaude(json_reply=[{"handle": "stephenasmith", "text": "take"}])
    takes = generate_pundit_takes(claude, "report", "roast")
    assert takes[0]["handle"] == "@stephenasmith"


def test_non_list_reply_returns_empty():
    claude = FakeClaude(json_reply=None)
    assert generate_pundit_takes(claude, "report", "roast") == []


def test_never_returns_more_than_two():
    claude = FakeClaude(json_reply=[
        {"handle": "@danorlovsky7", "text": "a"},
        {"handle": "@stephenasmith", "text": "b"},
        {"handle": "@danorlovsky7", "text": "c"},
    ])
    assert len(generate_pundit_takes(claude, "report", "roast")) == 2
