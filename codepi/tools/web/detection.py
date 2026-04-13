from __future__ import annotations

import re


def detect_bot_block(
    status_code: int, headers: dict[str, str], html_content: str
) -> str | None:
    """Detect anti-bot blocking from HTTP response signals.

    Returns a string describing the block type, or None if no block detected.
    """
    # Rate limiting
    if status_code == 429:
        return "rate-limited"

    # Only check 403/503 for bot blocks
    if status_code not in (403, 503):
        return None

    # Lowercase headers for case-insensitive comparison
    lower_headers = {k.lower(): v.lower() for k, v in headers.items()}

    # Cloudflare detection
    cf_mitigated = lower_headers.get("cf-mitigated", "")
    if "challenge" in cf_mitigated:
        return "bot-block:cloudflare"

    html_lower = html_content.lower()
    if "just a moment" in html_lower or "checking your browser" in html_lower:
        return "bot-block:cloudflare"

    # Akamai detection
    if "x-akamai-transformed" in lower_headers:
        return "bot-block:akamai"

    # DataDome detection
    if "datadome" in html_lower:
        return "bot-block:datadome"

    # Generic bot block (403/503 with no specific markers)
    return "bot-block:unknown"


def detect_js_only_page(html_content: str, extracted_text: str | None) -> str | None:
    """Detect pages that likely require JavaScript rendering.

    Returns "js-only-page" if detected, or None for normal pages.
    """
    html_lower = html_content.lower()

    # SPA framework mount points
    if '<div id="root">' in html_lower or '<div id="app">' in html_lower:
        return "js-only-page"

    # Noscript with JS requirement message
    if "<noscript>" in html_lower and "javascript" in html_lower:
        return "js-only-page"

    # Content ratio: large HTML + tiny extracted text
    html_size = len(html_content)
    text_len = len(extracted_text) if extracted_text else 0
    if html_size > 20_000 and text_len < 300:
        return "js-only-page"

    return None


def needs_fallback(
    status_code: int,
    headers: dict[str, str],
    html_content: str,
    extracted_text: str | None,
) -> str | None:
    """Combined fallback detection pipeline.

    Checks bot blocking, extraction failure, and JS-only pages in order.
    Returns the reason string if fallback to site_scrap is needed, or None.
    """
    # 1. Bot block detection
    block = detect_bot_block(status_code, headers, html_content)
    if block:
        return block

    # 2. Extraction failure
    if extracted_text is None or extracted_text.strip() == "":
        return "extraction-failed"

    # 3. JS-only page detection
    js = detect_js_only_page(html_content, extracted_text)
    if js:
        return js

    return None
