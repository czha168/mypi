"""Lazy imports for web tooling.

This module exposes WebSearchTool, WebFetchTool, and SiteScrapTool lazily.
If the respective optional dependencies are not installed, these names will
be present but set to None to avoid import-time crashes.
"""

__all__ = ["WebSearchTool", "WebFetchTool", "SiteScrapTool"]

# Lazy import WebSearchTool
try:
    from .web_search import WebSearchTool  # type: ignore
except ImportError:
    WebSearchTool = None  # type: ignore

# Lazy import WebFetchTool
try:
    from .web_fetch import WebFetchTool  # type: ignore
except ImportError:
    WebFetchTool = None  # type: ignore

# Lazy import SiteScrapTool
try:
    from .site_scrap import SiteScrapTool  # type: ignore
except ImportError:
    SiteScrapTool = None  # type: ignore
