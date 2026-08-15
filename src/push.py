"""Web Push notifications — pings subscribed devices when a new post lands.

Silently a no-op if VAPID_PRIVATE_KEY isn't configured (Push is optional).
"""
from __future__ import annotations

import json
import logging

log = logging.getLogger(__name__)

try:
    from pywebpush import WebPushException, webpush
except ImportError:  # pragma: no cover - only hit if requirements.txt drifts
    WebPushException = None
    webpush = None


def send_to_subscriptions(
    subscriptions: list[dict], title: str, body: str, private_key: str, subject: str,
) -> list[str]:
    """Push one notification to every subscription.

    Returns the endpoints of subscriptions that are dead (device unsubscribed
    or the push service returned 404/410) so the caller can delete them.
    """
    if webpush is None:
        log.warning("pywebpush not installed — skipping push send.")
        return []

    dead: list[str] = []
    payload = json.dumps({"title": title, "body": body, "url": "/"})

    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub["endpoint"],
                    "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
                },
                data=payload,
                vapid_private_key=private_key,
                vapid_claims={"sub": subject},
                timeout=10,
            )
        except WebPushException as exc:
            status = getattr(exc.response, "status_code", None)
            if status in (404, 410):
                dead.append(sub["endpoint"])
            else:
                log.warning("Push failed for %s: %s", sub["endpoint"][:60], exc)
        except Exception as exc:  # noqa: BLE001
            log.warning("Push failed for %s: %s", sub["endpoint"][:60], exc)

    return dead


def notification_for(post_type: str, author_handle: str, body: str) -> tuple[str, str]:
    """A short (title, body) pair for the notification tray, per post type."""
    snippet = body if len(body) <= 120 else body[:117] + "…"
    titles = {
        "instagram": "📸 New post",
        "espn_notification": "🚨 ESPN alert",
        "tweet": f"🐦 {author_handle or 'New tweet'}",
        "insider_report": "🕵️ Insider report",
    }
    return titles.get(post_type, "Fantasy Media"), snippet
