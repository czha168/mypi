import pytest
from codepi.tools.web.detection import detect_bot_block, detect_js_only_page, needs_fallback


class TestDetectBotBlock:
    def test_rate_limited(self):
        assert detect_bot_block(429, {}, "") == "rate-limited"

    def test_cloudflare_header(self):
        result = detect_bot_block(403, {"cf-mitigated": "challenge"}, "")
        assert result == "bot-block:cloudflare"

    def test_cloudflare_html_marker(self):
        result = detect_bot_block(503, {}, "<html>Just a moment...</html>")
        assert result == "bot-block:cloudflare"

    def test_cloudflare_checking_browser(self):
        result = detect_bot_block(403, {}, "<html>Checking your browser</html>")
        assert result == "bot-block:cloudflare"

    def test_akamai_header(self):
        result = detect_bot_block(403, {"x-akamai-transformed": "1"}, "<html>ok</html>")
        assert result == "bot-block:akamai"

    def test_datadome_html(self):
        result = detect_bot_block(403, {}, "<html>DataDome challenge</html>")
        assert result == "bot-block:datadome"

    def test_generic_403(self):
        result = detect_bot_block(403, {}, "<html>Forbidden</html>")
        assert result == "bot-block:unknown"

    def test_clean_response(self):
        assert detect_bot_block(200, {}, "<html>ok</html>") is None

    def test_404_not_a_block(self):
        assert detect_bot_block(404, {}, "<html>Not Found</html>") is None

    def test_case_insensitive_headers(self):
        result = detect_bot_block(403, {"CF-Mitigated": "challenge"}, "")
        assert result == "bot-block:cloudflare"


class TestDetectJsOnlyPage:
    def test_react_root(self):
        html = '<html><body><div id="root"></div></body></html>'
        assert detect_js_only_page(html, "") == "js-only-page"

    def test_vue_app(self):
        html = '<html><body><div id="app"></div></body></html>'
        assert detect_js_only_page(html, "") == "js-only-page"

    def test_noscript_javascript(self):
        html = '<html><body><noscript>Please enable JavaScript</noscript></body></html>'
        assert detect_js_only_page(html, "") == "js-only-page"

    def test_large_html_tiny_text(self):
        html = "x" * 30_000
        assert detect_js_only_page(html, "hi") == "js-only-page"

    def test_normal_page(self):
        html = "<html><body><p>Hello world this is a normal page with content</p></body></html>"
        assert detect_js_only_page(html, "Hello world this is a normal page with content") is None


class TestNeedsFallback:
    def test_bot_block_first(self):
        result = needs_fallback(403, {"cf-mitigated": "challenge"}, "<html>blocked</html>", "")
        assert result == "bot-block:cloudflare"

    def test_extraction_failed(self):
        result = needs_fallback(200, {}, "<html>ok</html>", None)  # type: ignore[arg-type]
        assert result == "extraction-failed"

    def test_empty_extracted_text(self):
        result = needs_fallback(200, {}, "<html>ok</html>", "   ")
        assert result == "extraction-failed"

    def test_js_only_detected(self):
        html = '<html><body><div id="root"></div></body></html>'
        result = needs_fallback(200, {}, html, "")
        assert result == "extraction-failed"  # extraction failure checked before js-only

    def test_no_fallback_needed(self):
        html = "<html><body><p>Content</p></body></html>"
        result = needs_fallback(200, {}, html, "Content paragraph with enough text to pass checks")
        assert result is None
