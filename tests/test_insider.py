"""Tests for insider report generation + reaction cleaning (no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.generators.insider import generate_fabricated_rumor, generate_insider_report
from src.generators.reactions import _clean


class FakeClaude:
    """Stub Claude that records the prompt and returns a canned reply."""
    def __init__(self, reply="the report"):
        self._reply = reply
        self.last_system = None
        self.last_prompt = None

    def generate(self, system, prompt, tone, max_tokens=300):
        self.last_system = system
        self.last_prompt = prompt
        return self._reply


def test_insider_report_uses_the_tip_text():
    claude = FakeClaude()
    generate_insider_report(claude, "Team A is shopping their RB1", "roast")
    assert "Team A is shopping their RB1" in claude.last_prompt


def test_insider_report_returns_claude_output():
    claude = FakeClaude(reply="Sources say Team A is moving their RB1 👀")
    result = generate_insider_report(claude, "Team A is shopping their RB1", "roast")
    assert result == "Sources say Team A is moving their RB1 👀"


def test_fabricated_rumor_does_not_reference_a_real_tip():
    claude = FakeClaude()
    generate_fabricated_rumor(claude, "roast")
    assert "No tips" in claude.last_prompt


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
