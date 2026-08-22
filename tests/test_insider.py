"""Tests for insider report generation + reaction cleaning (no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.generators.insider import generate_fabricated_rumor, generate_insider_report
from src.generators.reactions import _clean


class FakeClaude:
    """Stub Claude that records the prompt and returns canned replies.

    json_reply may be a single value (returned every call) or a list, in
    which case each successive generate_json() call pops the next one — used
    to simulate a first attempt failing and a fallback succeeding.
    """
    def __init__(self, reply="the report", json_reply=None):
        self._reply = reply
        self._json_replies = json_reply if isinstance(json_reply, list) else [json_reply]
        self.last_system = None
        self.last_prompt = None
        self.json_calls = 0

    def generate(self, system, prompt, tone, max_tokens=300):
        self.last_system = system
        self.last_prompt = prompt
        return self._reply

    def generate_json(self, system, prompt, tone, max_tokens=600):
        self.last_system = system
        self.last_prompt = prompt
        idx = min(self.json_calls, len(self._json_replies) - 1)
        self.json_calls += 1
        return self._json_replies[idx]


def test_insider_report_uses_the_tip_text():
    claude = FakeClaude(json_reply={"headline": "Big moves 👀", "body": "the report"})
    generate_insider_report(claude, "Team A is shopping their RB1", "roast")
    assert "Team A is shopping their RB1" in claude.last_prompt


def test_insider_report_returns_headline_and_body():
    claude = FakeClaude(json_reply={
        "headline": "Team A shopping RB1 👀",
        "body": "Sources say Team A is quietly moving their RB1. The league is buzzing.",
    })
    result = generate_insider_report(claude, "Team A is shopping their RB1", "roast")
    assert result["headline"] == "Team A shopping RB1 👀"
    assert result["body"].startswith("Sources say Team A")


def test_insider_report_synthesizes_headline_when_missing():
    claude = FakeClaude(json_reply={
        "body": "Word around the league is that a blockbuster trade is brewing behind closed doors.",
    })
    result = generate_insider_report(claude, "a tip", "roast")
    # headline is derived from the body's opening, not left blank
    assert result["headline"]
    assert len(result["headline"].split()) <= 11  # max_words (10) + trailing ellipsis token


def test_insider_report_falls_back_when_first_attempt_refuses():
    claude = FakeClaude(json_reply=[
        {"headline": "No comment", "body": "I can't help with this request."},
        {"headline": "Shady trade brewing 👀", "body": "Word around the league: a shady trade is brewing."},
    ])
    result = generate_insider_report(claude, "a real-person claim", "roast")
    assert result["headline"] == "Shady trade brewing 👀"
    assert claude.json_calls == 2


def test_insider_report_final_fallback_never_leaks_a_refusal():
    claude = FakeClaude(json_reply=[None, None])
    result = generate_insider_report(claude, "a real-person claim", "roast")
    assert result["headline"] and result["body"]
    assert "can't" not in f"{result['headline']} {result['body']}".lower()


def test_fabricated_rumor_returns_headline_and_body():
    claude = FakeClaude(json_reply={"headline": "Waiver heist 👀", "body": "Sources say a waiver war is coming."})
    result = generate_fabricated_rumor(claude, "roast")
    assert result["headline"] == "Waiver heist 👀"
    assert result["body"]


def test_fabricated_rumor_does_not_reference_a_real_tip():
    claude = FakeClaude()
    generate_fabricated_rumor(claude, "roast")
    assert "No tips" in claude.last_prompt


def test_report_with_no_storyline_fields_defaults_to_none():
    claude = FakeClaude(json_reply={"headline": "h", "body": "b"})
    result = generate_insider_report(claude, "a tip", "roast")
    assert result["storyline"] == {"action": "none"}


def test_report_starting_a_new_storyline():
    claude = FakeClaude(json_reply={
        "headline": "h", "body": "b",
        "storyline_action": "new",
        "storyline_title": "The Josh Benching Scandal",
        "canon_note": "Josh benched his own RB1 in a big week.",
    })
    result = generate_insider_report(claude, "a tip", "roast")
    assert result["storyline"] == {
        "action": "new",
        "title": "The Josh Benching Scandal",
        "canon_note": "Josh benched his own RB1 in a big week.",
    }


def test_report_continuing_a_storyline():
    claude = FakeClaude(json_reply={
        "headline": "h", "body": "b",
        "storyline_action": "continue",
        "storyline_key": "the-josh-benching-scandal",
        "canon_note": "Josh's benched RB1 went off for 30 points on the bench.",
    })
    result = generate_insider_report(claude, "a tip", "roast")
    assert result["storyline"] == {
        "action": "continue",
        "key": "the-josh-benching-scandal",
        "canon_note": "Josh's benched RB1 went off for 30 points on the bench.",
    }


def test_storyline_new_without_title_is_dropped():
    claude = FakeClaude(json_reply={
        "headline": "h", "body": "b",
        "storyline_action": "new", "canon_note": "x",
    })
    result = generate_insider_report(claude, "a tip", "roast")
    assert result["storyline"] == {"action": "none"}


def test_storyline_continue_without_key_is_dropped():
    claude = FakeClaude(json_reply={
        "headline": "h", "body": "b",
        "storyline_action": "continue", "canon_note": "x",
    })
    result = generate_insider_report(claude, "a tip", "roast")
    assert result["storyline"] == {"action": "none"}


def test_clean_reactions_normalizes_handles():
    data = [
        {"handle": "degen_dan", "text": "no way"},
        {"handle": "@stan", "text": "called it"},
        {"text": "no handle still ok"},
        {"bad": "ignored"},
    ]
    out = _clean(data, 5)
    assert out[0]["handle"] == "@degen_dan"
    assert out[1]["handle"] == "@stan"
    assert out[2]["handle"] == "@fan"
    assert len(out) == 3  # the dict with no text is dropped


def test_clean_respects_limit():
    data = [{"handle": f"@f{i}", "text": str(i)} for i in range(10)]
    assert len(_clean(data, 3)) == 3
