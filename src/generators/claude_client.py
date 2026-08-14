"""Shared Claude text-generation helper.

Centralizes the Anthropic call + tone handling so each generator is a thin
prompt. Falls back to a plain deterministic string if the API is unreachable,
so a Claude outage never blocks the pipeline.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)

TONE_GUIDE = {
    "hype": (
        "Voice: a hyped-up broadcast anchor. Big energy, dramatic, "
        "celebratory. Take it seriously like it's the Super Bowl."
    ),
    "roast": (
        "Voice: a savage group-chat trash-talker. Funny, cutting, roasting "
        "the losers. Keep it playful, never genuinely mean or offensive."
    ),
}


class ClaudeClient:
    def __init__(self, api_key: str, model: str):
        self._model = model
        self._client = None
        try:
            import anthropic

            self._client = anthropic.Anthropic(api_key=api_key)
        except Exception as exc:  # noqa: BLE001
            log.warning("Anthropic client unavailable, will use fallbacks: %s", exc)

    def generate(self, system: str, prompt: str, tone: str, max_tokens: int = 300) -> str:
        tone_text = TONE_GUIDE.get(tone, TONE_GUIDE["roast"])
        full_system = f"{system}\n\n{tone_text}"
        if self._client is None:
            return _fallback(prompt)
        try:
            msg = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                system=full_system,
                messages=[{"role": "user", "content": prompt}],
            )
            parts = [b.text for b in msg.content if getattr(b, "type", "") == "text"]
            text = "".join(parts).strip()
            return text or _fallback(prompt)
        except Exception as exc:  # noqa: BLE001
            log.warning("Claude generation failed, using fallback: %s", exc)
            return _fallback(prompt)


    def generate_json(self, system: str, prompt: str, tone: str, max_tokens: int = 600):
        """Like generate(), but expects JSON back. Returns parsed data or None.

        Never raises — on any parse/API failure returns None so callers can
        fall back gracefully.
        """
        raw = self.generate(
            system + "\n\nRespond with ONLY valid JSON, no prose, no code fences.",
            prompt, tone, max_tokens=max_tokens,
        )
        return _parse_json(raw)


def _parse_json(raw: str):
    import json
    import re

    if not raw:
        return None
    # Strip code fences if the model added them anyway.
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Last resort: grab the first {...} or [...] block.
        match = re.search(r"(\[.*\]|\{.*\})", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                return None
        return None


def _fallback(prompt: str) -> str:
    # Deterministic, never-crashes fallback: just echo the key facts.
    first_line = prompt.strip().splitlines()[0] if prompt.strip() else "Fantasy update"
    return first_line[:280]
