"""Render HTML/CSS to PNG with headless Chromium.

This is the engine behind the "real sports graphic" look — proper web fonts,
gradients, shadows, grain, big ghosted numerals — none of which flat Pillow
drawing can match. Fonts are embedded as data URIs so rendering needs no
network at runtime.

If Chromium or Playwright isn't available, render_html() returns None and the
caller falls back to the Pillow renderers, so the feed never breaks.
"""
from __future__ import annotations

import base64
import glob
import logging
import os
from functools import lru_cache

log = logging.getLogger(__name__)

_FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")


@lru_cache(maxsize=1)
def font_faces() -> str:
    """@font-face CSS with every bundled TTF embedded as a data URI."""
    specs = [
        ("Anton", "Anton.ttf", "400"),
        ("Barlow Condensed", "BarlowCondensed_700.ttf", "700"),
        ("Barlow Condensed", "BarlowCondensed_600.ttf", "600"),
        ("Barlow", "Barlow_500.ttf", "500"),
    ]
    out = []
    for family, fn, weight in specs:
        path = os.path.join(_FONT_DIR, fn)
        try:
            b64 = base64.b64encode(open(path, "rb").read()).decode()
        except OSError:
            continue
        out.append(
            f"@font-face{{font-family:'{family}';font-weight:{weight};font-style:normal;"
            f"src:url(data:font/ttf;base64,{b64}) format('truetype');}}"
        )
    return "".join(out)


@lru_cache(maxsize=1)
def _chromium_path() -> str | None:
    # Explicit override wins.
    for env in ("CHROMIUM_PATH", "PLAYWRIGHT_CHROMIUM_EXECUTABLE"):
        p = os.environ.get(env)
        if p and os.path.exists(p):
            return p
    # Playwright's managed browsers (local dev + our Railway build install these).
    roots = [os.environ.get("PLAYWRIGHT_BROWSERS_PATH", ""), "/opt/pw-browsers",
             os.path.expanduser("~/.cache/ms-playwright")]
    for root in roots:
        if not root:
            continue
        for pat in ("chromium-*/chrome-linux/chrome", "chromium_headless_shell-*/chrome-linux/headless_shell"):
            hits = sorted(glob.glob(os.path.join(root, pat)))
            if hits:
                return hits[-1]
    # System chromium.
    for p in ("/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome"):
        if os.path.exists(p):
            return p
    return None


def available() -> bool:
    try:
        import playwright  # noqa: F401
    except ImportError:
        return False
    return True


def render_html(html: str, out_path: str, width: int = 1080, height: int = 1080,
                scale: int = 2, selector: str = "#card") -> str | None:
    """Render an HTML string to a PNG at out_path. Returns the path, or None if
    Chromium/Playwright isn't available or rendering failed."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.warning("HTML render skipped: playwright not installed.")
        return None

    args = ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage",
            "--force-color-profile=srgb"]
    exe = _chromium_path()
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    try:
        with sync_playwright() as p:
            # Prefer Playwright's own managed browser (it knows where it
            # installed it); fall back to an explicitly-discovered binary.
            try:
                browser = p.chromium.launch(args=args)
            except Exception as launch_exc:  # noqa: BLE001
                if not exe:
                    raise
                log.warning("Default chromium launch failed (%s); trying %s", launch_exc, exe)
                browser = p.chromium.launch(executable_path=exe, args=args)
            page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=scale)
            page.set_content(html, wait_until="load")
            target = page.locator(selector)
            (target if target.count() else page).screenshot(path=out_path)
            browser.close()
        return out_path
    except Exception as exc:  # noqa: BLE001
        log.warning("HTML render failed (chromium_path=%s): %s", exe, exc)
        return None
