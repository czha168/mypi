from __future__ import annotations
import asyncio
import json
import re
import time
from pathlib import Path
from codepi.tools.base import Tool, ToolResult
from codepi.tools.web.storage import url_to_slug, save_content, get_web_temp_dir


class SiteScrapTool(Tool):
    name = "site_scrap"
    description = (
        "Scrape websites with progressive fetcher tiers. Supports single page scraping, "
        "site-wide crawling (when start_urls provided), and GitHub repo cloning. Basic HTTP "
        "fetcher works out of the box; stealthy/dynamic fetchers require pip install codepi[web-full]."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL for single page scraping or GitHub repo"},
            "start_urls": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Starting URLs for site-wide crawling",
            },
            "selector": {"type": "string", "description": "CSS or XPath selector for element extraction"},
            "selector_type": {"type": "string", "description": "Selector type: 'css' or 'xpath' (default 'css')"},
            "fetcher": {"type": "string", "description": "Fetcher tier: 'auto', 'basic', 'stealthy', or 'dynamic' (default 'auto')"},
            "headless": {"type": "boolean", "description": "Run browser in headless mode (default true)"},
            "max_pages": {"type": "integer", "description": "Maximum pages for crawling (default 50)"},
            "max_depth": {"type": "integer", "description": "Maximum crawl depth (default 3)"},
            "allowed_domains": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Domains to restrict crawling to",
            },
            "download_delay": {"type": "number", "description": "Seconds between requests (default 1.0)"},
        },
    }

    # type: ignore[reportIncompatibleMethodOverride]
    async def execute(self, **kwargs) -> ToolResult:
        # Lazy import to avoid heavy dependency unless used
        try:
            from scrapling import Fetcher  # type: ignore[import]
        except ImportError:
            return ToolResult(error="site_scrap requires scrapling. Install with: pip install codepi[web]")

        # Extract params
        url = kwargs.get("url")
        start_urls = kwargs.get("start_urls")
        selector = kwargs.get("selector")
        selector_type = kwargs.get("selector_type", "css")
        fetcher_type = kwargs.get("fetcher", "auto")
        headless = kwargs.get("headless", True)
        max_pages = kwargs.get("max_pages", 50)
        max_depth = kwargs.get("max_depth", 3)
        allowed_domains = kwargs.get("allowed_domains")
        download_delay = kwargs.get("download_delay", 1.0)

        try:
            # Routing logic
            if url and "github.com" in url:
                return await self._handle_github(url)
            if start_urls:
                return await self._handle_crawl(
                    start_urls,
                    selector,
                    selector_type,
                    fetcher_type,
                    headless,
                    max_pages,
                    max_depth,
                    allowed_domains,
                    download_delay,
                )
            if url:
                return await self._handle_single_page(url, selector, selector_type, fetcher_type, headless)
            return ToolResult(error="At least one of 'url' or 'start_urls' must be provided")
        except Exception as e:
            return ToolResult(error=str(e))

    async def _handle_github(self, url: str) -> ToolResult:
        # Parse GitHub URL
        match = re.match(r"github\.com/([^/]+)/([^/]+)(?:/tree/([^/]+)(?:/(.*))?)?", url)
        if not match:
            return ToolResult(error=f"Not a valid GitHub repo URL: {url}")
        owner, repo, branch, subpath = match.groups()
        branch = branch or "main"
        clone_url = f"https://github.com/{owner}/{repo}.git"

        # Clone to temp dir
        clone_dir = get_web_temp_dir("default") / "scrap" / f"{owner}-{repo}"
        if not clone_dir.exists():
            proc = await asyncio.create_subprocess_exec(
                "git",
                "clone",
                "--depth",
                "1",
                "-b",
                branch,
                clone_url,
                str(clone_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                _, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            except asyncio.TimeoutError:
                proc.kill()
                return ToolResult(error="git clone timed out after 120s")
            if proc.returncode != 0:
                return ToolResult(error=f"git clone failed: {stderr.decode(errors='replace')[:500]}")

        target = clone_dir / subpath if subpath else clone_dir
        # Build a simple tree listing
        entries: list[str] = []
        if target.is_dir():
            for i, p in enumerate(sorted(target.rglob("*"))):
                if i >= 200:
                    entries.append("... (truncated at 200 entries)")
                    break
                rel = p.relative_to(clone_dir)
                kind = "/" if p.is_dir() else ""
                entries.append(f"  {rel}{kind}")
        tree = "\n".join(entries)
        explore_path = target if subpath else clone_dir
        return ToolResult(
            output=f"**Cloned to**: {clone_dir}\n**Branch**: {branch}\n\n{tree}\n\nUse the `read` tool to explore files in: {explore_path}"
        )

    async def _handle_single_page(self, url: str, selector: str | None, selector_type: str, fetcher_type: str, headless: bool) -> ToolResult:
        page = await self._fetch_page(url, fetcher_type, headless)
        if isinstance(page, ToolResult):
            return page
        # If a selector is provided, extract
        if selector:
            results = self._extract_with_selector(page, selector, selector_type)
            slug = url_to_slug(url)
            content = json.dumps(results, indent=2, ensure_ascii=False)
            path = save_content("default", "scrap", slug, content, "json")
            preview = json.dumps(results[:5] if isinstance(results, list) else results, indent=2, ensure_ascii=False)
            return ToolResult(output=f"**Saved to**: {path}\n**Matched**: {len(results) if isinstance(results, list) else '1'} elements\n\n{preview}")
        # Else fetch full text/page content
        text = page.get_all_text() if hasattr(page, "get_all_text") else str(page)
        slug = url_to_slug(url)
        path = save_content("default", "scrap", slug, text, "md")
        preview = text[:500]
        return ToolResult(output=f"**Saved to**: {path}\n\n{preview}")

    async def _fetch_page(self, url: str, fetcher_type: str, headless: bool):
        # Lazy import of scrapling fetchers
        from scrapling import Fetcher  # type: ignore[import]
        # Basic fetcher
        if fetcher_type == "basic":
            try:
                return Fetcher.get(url)
            except Exception as e:
                return ToolResult(error=f"Basic fetcher failed: {e}")
        # Stealthy/dynamic fetchers
        elif fetcher_type == "stealthy":
            try:
                from scrapling import StealthyFetcher  # type: ignore[import]
            except ImportError:
                return ToolResult(error="Stealthy/Dynamic fetchers require scrapling[fetchers]. Install with: pip install codepi[web-full]")
            try:
                return await asyncio.to_thread(StealthyFetcher.fetch, url, headless=headless, solve_cloudflare=True)
            except Exception as e:
                return ToolResult(error=f"Stealthy fetcher failed: {e}")
        elif fetcher_type == "dynamic":
            try:
                from scrapling import DynamicFetcher  # type: ignore[import]
            except ImportError:
                return ToolResult(error="Stealthy/Dynamic fetchers require scrapling[fetchers]. Install with: pip install codepi[web-full]")
            try:
                return await asyncio.to_thread(DynamicFetcher.fetch, url, headless=headless)
            except Exception as e:
                return ToolResult(error=f"Dynamic fetcher failed: {e}")
        else:  # auto
            # Try basic first
            try:
                page = Fetcher.get(url)
                text = page.get_all_text() if hasattr(page, "get_all_text") else str(page)
                if text and len(text.strip()) > 50:
                    return page
            except Exception:
                pass
            # Try stealthy
            try:
                from scrapling import StealthyFetcher  # type: ignore[import]
                page = await asyncio.to_thread(StealthyFetcher.fetch, url, headless=headless, solve_cloudflare=True)
                text = page.get_all_text() if hasattr(page, "get_all_text") else str(page)
                if text and len(text.strip()) > 50:
                    return page
            except (ImportError, Exception):
                pass
            # Try dynamic
            try:
                from scrapling import DynamicFetcher  # type: ignore[import]
                page = await asyncio.to_thread(DynamicFetcher.fetch, url, headless=headless)
                text = page.get_all_text() if hasattr(page, "get_all_text") else str(page)
                if text and len(text.strip()) > 50:
                    return page
            except (ImportError, Exception):
                pass
            return ToolResult(error="All fetcher tiers failed. The page may be unreachable or heavily protected.")

    def _extract_with_selector(self, page, selector: str, selector_type: str):
        results: list[str] = []
        if selector_type == "xpath":
            elements = page.xpath(selector)
        else:
            # Support simple special syntax for text/attribute extraction
            text_match = re.match(r"^(.*?)::text$", selector)
            attr_match = re.match(r"^(.*?)::attr\(([^)]+)\)$", selector)
            if text_match:
                base_sel = text_match.group(1)
                elements = page.css(base_sel)
                return [el.get_text(strip=True) for el in elements]
            elif attr_match:
                base_sel = attr_match.group(1)
                attr_name = attr_match.group(2)
                elements = page.css(base_sel)
                return [el.get(attr_name, "") for el in elements]
            else:
                elements = page.css(selector)
        for el in elements:
            if hasattr(el, "get_text"):
                results.append(el.get_text(strip=True))
            else:
                results.append(str(el))
        return results

    async def _handle_crawl(
        self,
        start_urls: list[str],
        selector: str | None,
        selector_type: str,
        fetcher_type: str,
        headless: bool,
        max_pages: int,
        max_depth: int,
        allowed_domains: list[str] | None,
        download_delay: float,
    ) -> ToolResult:
        from scrapling import Fetcher  # type: ignore[import]
        from urllib.parse import urlparse, urljoin

        if not start_urls:
            return ToolResult(output="No start_urls provided for crawl.")

        if not allowed_domains:
            allowed_domains = [urlparse(u).netloc for u in start_urls]
        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(u, 0) for u in start_urls]
        all_results: list[dict[str, object]] = []
        start_t = time.time()
        total_requests = 0
        successful = 0

        while queue and len(visited) < max_pages:
            current_url, depth = queue.pop(0)
            if current_url in visited or depth > max_depth:
                continue
            domain = urlparse(current_url).netloc
            if allowed_domains and domain not in allowed_domains:
                continue
            visited.add(current_url)
            total_requests += 1
            try:
                page = Fetcher.get(current_url)
                successful += 1
                if selector:
                    items = self._extract_with_selector(page, selector, selector_type)
                    all_results.append({"url": current_url, "depth": depth, "items": items})
                else:
                    text = page.get_all_text() if hasattr(page, "get_all_text") else str(page)
                    all_results.append({"url": current_url, "depth": depth, "content": text[:5000]})
                if depth < max_depth:
                    for a in page.css("a[href]"):
                        href = a.get("href", "")
                        if not href:
                            continue
                        abs_url = href if href.startswith("http") else urljoin(current_url, href)
                        if abs_url not in visited:
                            queue.append((abs_url, depth + 1))
            except Exception:
                pass
            await asyncio.sleep(download_delay)

        elapsed = time.time() - start_t
        success_rate = (successful / total_requests * 100) if total_requests else 0
        slug = url_to_slug(start_urls[0])
        content = json.dumps(all_results, indent=2, ensure_ascii=False)
        path = save_content("default", "scrap", slug, content, "json")
        return ToolResult(
            output=(
                f"Pages scraped: {len(visited)}\n"
                f"Total requests: {total_requests}\n"
                f"Success rate: {success_rate:.1f}%\n"
                f"Elapsed: {elapsed:.1f}s\n"
                f"Results saved to: {path}"
            )
        )
