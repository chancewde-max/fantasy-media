"""Tests for tip clustering + reaction cleaning (no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.generators.insider import cluster_tips
from src.generators.reactions import _clean


class FakeClaude:
    """Stub Claude that returns a preset JSON payload (or None)."""
    def __init__(self, json_payload=None):
        self._payload = json_payload

    def generate_json(self, system, prompt, tone, max_tokens=600):
        return self._payload


def test_cluster_requires_min_corroboration():
    tips = [{"id": "1", "raw_text": "team A shopping their RB"}]
    # Only one tip -> nothing can corroborate.
    assert cluster_tips(FakeClaude([]), tips, 2) == []


def test_cluster_uses_model_grouping():
    tips = [
        {"id": "1", "raw_text": "A is shopping their RB1"},
        {"id": "2", "raw_text": "heard team A wants to move a running back"},
        {"id": "3", "raw_text": "B is tanking"},
    ]
    payload = [{"tip_ids": ["1", "2"], "summary": "Team A shopping RB1"}]
    clusters = cluster_tips(FakeClaude(payload), tips, 2)
    assert len(clusters) == 1
    assert set(clusters[0]["tip_ids"]) == {"1", "2"}


def test_cluster_drops_undersized_model_groups():
    tips = [
        {"id": "1", "raw_text": "x"},
        {"id": "2", "raw_text": "y"},
    ]
    # Model returns a singleton group -> dropped by threshold.
    payload = [{"tip_ids": ["1"], "summary": "solo"}]
    assert cluster_tips(FakeClaude(payload), tips, 2) == []


def test_cluster_fallback_exact_match_when_model_fails():
    tips = [
        {"id": "1", "raw_text": "Team A shopping RB1"},
        {"id": "2", "raw_text": "team a  shopping rb1"},  # same after normalize
        {"id": "3", "raw_text": "unrelated"},
    ]
    clusters = cluster_tips(FakeClaude(None), tips, 2)  # None -> fallback
    assert len(clusters) == 1
    assert set(clusters[0]["tip_ids"]) == {"1", "2"}


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
