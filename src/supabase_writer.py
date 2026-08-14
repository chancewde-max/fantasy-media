"""Writes generated content into Supabase as feed posts.

Talks to Supabase's REST + Storage HTTP APIs directly (no SDK needed) using
the SERVICE ROLE key, which bypasses row-level security so the backend can
insert. Images are uploaded to a public Storage bucket and their public URL is
stored on the post.

The engine's own SQLite de-dup already prevents re-posting the same event; the
posts(league_id, event_key) unique index is a second line of defense, and a
409 from it is treated as "already posted" rather than an error.
"""
from __future__ import annotations

import logging
import os

import requests

log = logging.getLogger(__name__)

TIMEOUT = 20


class SupabaseError(RuntimeError):
    pass


class SupabaseWriter:
    def __init__(self, url: str, service_key: str, league_id: str, bucket: str = "media"):
        self._base = url.rstrip("/")
        self._key = service_key
        self._league_id = league_id
        self._bucket = bucket
        self._bucket_ready = False

    @property
    def _rest_headers(self) -> dict:
        return {
            "apikey": self._key,
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
        }

    # ---------------------------------------------------------------- posts
    def insert_post(
        self,
        post_type: str,
        body: str,
        author_handle: str | None = None,
        image_path: str | None = None,
        event_key: str | None = None,
        metadata: dict | None = None,
    ) -> str | None:
        """Insert one feed post. Returns the new post id, or None if a duplicate.

        Raises SupabaseError on real failures (auth, network, bad request).
        """
        image_url = None
        if image_path:
            try:
                image_url = self._upload_image(image_path)
            except SupabaseError as exc:
                # A missing image shouldn't block the text post.
                log.warning("Image upload failed, posting without it: %s", exc)

        row = {
            "league_id": self._league_id,
            "type": post_type,
            "author_handle": author_handle,
            "body": body,
            "image_url": image_url,
            "event_key": event_key,
            "metadata": metadata or {},
        }
        resp = requests.post(
            f"{self._base}/rest/v1/posts",
            headers={**self._rest_headers, "Prefer": "return=representation"},
            json=row,
            timeout=TIMEOUT,
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            return data[0]["id"] if isinstance(data, list) and data else None
        if resp.status_code == 409:
            # Unique violation on (league_id, event_key) -> already posted.
            log.info("Post already exists (event_key=%s), skipping.", event_key)
            return None
        if resp.status_code in (401, 403):
            raise SupabaseError(
                "Supabase rejected the write — check SUPABASE_SERVICE_KEY "
                f"({resp.status_code})."
            )
        raise SupabaseError(f"Insert failed {resp.status_code}: {resp.text[:200]}")

    def insert_fan_comment(self, post_id: str, handle: str, body: str) -> None:
        """Insert an AI-generated fan comment on a post (service role)."""
        resp = requests.post(
            f"{self._base}/rest/v1/comments",
            headers={**self._rest_headers, "Prefer": "return=minimal"},
            json={
                "post_id": post_id,
                "author_handle": handle,
                "body": body,
                "is_ai": True,
            },
            timeout=TIMEOUT,
        )
        if resp.status_code not in (200, 201, 204):
            raise SupabaseError(
                f"Fan comment insert failed {resp.status_code}: {resp.text[:200]}"
            )

    # -------------------------------------------------------------- storage
    def _ensure_bucket(self) -> None:
        if self._bucket_ready:
            return
        # Create the bucket (idempotent-ish: 200 created, 400/409 already exists).
        resp = requests.post(
            f"{self._base}/storage/v1/bucket",
            headers=self._rest_headers,
            json={"id": self._bucket, "name": self._bucket, "public": True},
            timeout=TIMEOUT,
        )
        if resp.status_code in (200, 201) or resp.status_code in (400, 409):
            self._bucket_ready = True
            return
        raise SupabaseError(
            f"Could not ensure storage bucket {self._bucket!r}: "
            f"{resp.status_code} {resp.text[:200]}"
        )

    def _upload_image(self, image_path: str) -> str:
        if not os.path.exists(image_path):
            raise SupabaseError(f"Image not found: {image_path}")
        self._ensure_bucket()
        object_path = os.path.basename(image_path)
        with open(image_path, "rb") as fh:
            data = fh.read()
        resp = requests.post(
            f"{self._base}/storage/v1/object/{self._bucket}/{object_path}",
            headers={
                "apikey": self._key,
                "Authorization": f"Bearer {self._key}",
                "Content-Type": "image/png",
                # Overwrite if the same object name comes back around.
                "x-upsert": "true",
            },
            data=data,
            timeout=TIMEOUT,
        )
        if resp.status_code not in (200, 201):
            raise SupabaseError(
                f"Image upload failed {resp.status_code}: {resp.text[:200]}"
            )
        return f"{self._base}/storage/v1/object/public/{self._bucket}/{object_path}"

    # ----------------------------------------------------------------- tips
    def fetch_pending_tips(self) -> list[dict]:
        """Pull manager-submitted tips awaiting the Insider treatment."""
        resp = requests.get(
            f"{self._base}/rest/v1/tips",
            headers=self._rest_headers,
            params={
                "league_id": f"eq.{self._league_id}",
                "status": "eq.pending",
                "select": "id,raw_text,created_at",
                "order": "created_at.asc",
            },
            timeout=TIMEOUT,
        )
        if resp.status_code != 200:
            raise SupabaseError(f"Fetch tips failed {resp.status_code}: {resp.text[:200]}")
        return resp.json()

    def mark_tip(self, tip_id: str, status: str, post_id: str | None = None) -> None:
        payload = {"status": status}
        if post_id:
            payload["post_id"] = post_id
        resp = requests.patch(
            f"{self._base}/rest/v1/tips",
            headers={**self._rest_headers, "Prefer": "return=minimal"},
            params={"id": f"eq.{tip_id}"},
            json=payload,
            timeout=TIMEOUT,
        )
        if resp.status_code not in (200, 204):
            raise SupabaseError(f"Update tip failed {resp.status_code}: {resp.text[:200]}")
