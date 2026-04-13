from __future__ import annotations

import re
from pathlib import Path


def get_web_temp_dir(session_id: str) -> Path:
    """Return the session-scoped temp directory, creating it if needed."""
    tmp = Path(f"/tmp/codepi-{session_id}")
    tmp.mkdir(parents=True, exist_ok=True)
    return tmp


def url_to_slug(url: str, max_length: int = 80) -> str:
    """Convert a URL to a filesystem-safe slug."""
    slug = re.sub(r"^https?://", "", url)
    slug = slug.rstrip("/")
    slug = re.sub(r"[^a-zA-Z0-9]", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    slug = slug.strip("-")
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
    return slug


def save_content(
    session_id: str, subdir: str, slug: str, content: str, extension: str
) -> Path:
    """Save content to a session-scoped temp subdirectory and return the file path."""
    tmp = get_web_temp_dir(session_id) / subdir
    tmp.mkdir(parents=True, exist_ok=True)
    path = tmp / f"{slug}.{extension}"
    path.write_text(content, encoding="utf-8")
    return path
