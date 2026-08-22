"""Tests for the new graphics renderers, GIF helper, and graphic post generators."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from src import gifs
from src.events import Event
from src.generators import graphics
from src.graphics import render, templates


@pytest.fixture(autouse=True)
def _force_pillow_fallback(monkeypatch):
    """Keep generator tests fast + deterministic by skipping real Chromium and
    exercising the Pillow fallback path (which still returns a valid PNG)."""
    monkeypatch.setattr(graphics.html_render, "render_html", lambda *a, **k: None)
    monkeypatch.setattr(graphics, "_logo", lambda team: None)
    monkeypatch.setattr(graphics, "_hero", lambda team: (None, ""))


class FakeClaude:
    def __init__(self, text="a caption", json_reply=None):
        self._text = text
        self._json = json_reply if json_reply is not None else {"top": "TOP", "bottom": "BOTTOM"}

    def generate(self, system, prompt, tone, max_tokens=300):
        return self._text

    def generate_json(self, system, prompt, tone, max_tokens=600):
        return self._json


def _is_png(path):
    return path and os.path.exists(path) and os.path.getsize(path) > 0


def test_renderers_produce_images(tmp_path):
    out = str(tmp_path)
    assert _is_png(render.render_gameday_matchup(out, "gd", "A team", "B team", "sub a", "sub b", "Week 1", "lore"))
    assert _is_png(render.render_final_score(out, "fs", "A team", 120.5, "B team", 88.0, "Blowout", "note"))
    assert _is_png(render.render_record_card(out, "rc", "Milestone", "Back-to-Back Champ", "sub"))
    assert _is_png(render.render_stat_leader(out, "sl", "Team of the Week", "A team", "188.4", "points", "sub"))
    assert _is_png(render.render_meme(out, "mm", "top text", "bottom text"))


def test_gifs_disabled_without_key(monkeypatch):
    monkeypatch.delenv("GIPHY_API_KEY", raising=False)
    assert gifs.gifs_enabled() is False
    assert gifs.search_gif("celebration") is None
    assert gifs.search_gif("") is None


def test_gameday_post(tmp_path):
    ev = Event(kind="game_of_the_week", key="w1:gotw",
               title="GOTW", data={"week": 1, "team_a": "The Island boys", "team_b": "Back to back", "lore": "rivalry"})
    post = graphics.gameday_post(FakeClaude(), ev, "roast", str(tmp_path))
    assert post["caption"]
    assert _is_png(post["image_path"])


def test_final_score_post_from_blowout(tmp_path):
    ev = Event(kind="blowout", key="w1:blowout",
               title="Blowout", data={"week": 1, "winner": "A", "loser": "B", "margin": 44.2})
    post = graphics.final_score_post(FakeClaude(), ev, "roast", str(tmp_path))
    assert _is_png(post["image_path"])
    # gif_url key present (None without a Tenor key), never raises
    assert "gif_url" in post


def test_stat_leader_post(tmp_path):
    ev = Event(kind="high", key="w1:high", title="Highest scorer",
               data={"week": 1, "team": "A team", "score": 188.4})
    post = graphics.stat_leader_post(FakeClaude(), ev, "roast", str(tmp_path))
    assert _is_png(post["image_path"])


def test_meme_post(tmp_path):
    post = graphics.meme_post(FakeClaude(), "A benched a 30 burger", "roast", str(tmp_path), "k1")
    assert _is_png(post["image_path"])


def test_meme_post_empty_when_no_text(tmp_path):
    post = graphics.meme_post(FakeClaude(json_reply={"top": "", "bottom": ""}), "ctx", "roast", str(tmp_path), "k2")
    assert post == {}


def test_templates_render_html_strings():
    m = templates.matchup_html("A", "B", "sa", "sb", "WEEK 1", "lore")
    assert "<!doctype html>" in m and "GAME OF THE WEEK" in m and "font-face" in m
    f = templates.final_score_html("A", 120.0, "B", 88.0, "BLOWOUT", "", "WEEK 2")
    assert "FINAL" in f and "BLOWOUT" in f
    r = templates.record_html("MILESTONE", "Back-to-Back Champ", "sub", "Back to back", ghost="2x")
    assert "MILESTONE" in r
    s = templates.stat_leader_html("TEAM OF THE WEEK", "A", "188.4", "POINTS", "sub")
    assert "188.4" in s
    assert "<div" in templates.meme_html("TOP", "BOTTOM", "A")


def test_theme_is_deterministic():
    assert templates.theme("Back to back") == templates.theme("BACK TO BACK")
    assert templates.initials("The Island Boys") == "TI"
