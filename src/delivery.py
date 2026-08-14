"""Webhook delivery to Discord / Slack / GroupMe.

Each provider takes text and optionally one or more image files. Images are
uploaded where the provider supports it; otherwise we post text only and log
a warning (GroupMe image posting requires its image service, kept simple here).
"""
from __future__ import annotations

import logging

import requests

log = logging.getLogger(__name__)

TIMEOUT = 20


class DeliveryError(RuntimeError):
    pass


class Delivery:
    def __init__(self, provider: str, webhook_url: str = "", groupme_bot_id: str = ""):
        self._provider = provider
        self._webhook_url = webhook_url
        self._groupme_bot_id = groupme_bot_id

    def send(self, text: str, image_paths: list[str] | None = None) -> None:
        image_paths = image_paths or []
        try:
            if self._provider == "discord":
                self._send_discord(text, image_paths)
            elif self._provider == "slack":
                self._send_slack(text, image_paths)
            elif self._provider == "groupme":
                self._send_groupme(text, image_paths)
            else:
                raise DeliveryError(f"Unknown provider {self._provider}")
        except requests.RequestException as exc:
            raise DeliveryError(f"Webhook delivery failed: {exc}") from exc

    # --- Discord: supports multipart file upload ---
    def _send_discord(self, text: str, image_paths: list[str]) -> None:
        if image_paths:
            files = {
                f"file{i}": (path.split("/")[-1], open(path, "rb"), "image/png")
                for i, path in enumerate(image_paths)
            }
            try:
                resp = requests.post(
                    self._webhook_url, data={"content": text}, files=files, timeout=TIMEOUT
                )
            finally:
                for _, (_, fh, _) in files.items():
                    fh.close()
        else:
            resp = requests.post(self._webhook_url, json={"content": text}, timeout=TIMEOUT)
        _raise_for_status(resp)

    # --- Slack: incoming webhooks are text/blocks only (no direct upload) ---
    def _send_slack(self, text: str, image_paths: list[str]) -> None:
        if image_paths:
            text = f"{text}\n(_image generated — attach via a hosted URL for Slack_)"
        resp = requests.post(self._webhook_url, json={"text": text}, timeout=TIMEOUT)
        _raise_for_status(resp)

    # --- GroupMe: bot post endpoint, text only in this simple build ---
    def _send_groupme(self, text: str, image_paths: list[str]) -> None:
        if image_paths:
            text = f"{text}\n(image generated)"
        resp = requests.post(
            "https://api.groupme.com/v3/bots/post",
            json={"bot_id": self._groupme_bot_id, "text": text},
            timeout=TIMEOUT,
        )
        _raise_for_status(resp)


def _raise_for_status(resp: requests.Response) -> None:
    if resp.status_code >= 300:
        raise DeliveryError(f"Webhook returned {resp.status_code}: {resp.text[:200]}")
