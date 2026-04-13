import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from codepi.tools.web.site_scrap import SiteScrapTool


@pytest.fixture
def tool():
    return SiteScrapTool()


class TestSiteScrapTool:
    def test_name_and_schema(self, tool):
        assert tool.name == "site_scrap"
        props = tool.input_schema["properties"]
        assert "url" in props
        assert "start_urls" in props
        assert "selector" in props
        assert "fetcher" in props

    @pytest.mark.asyncio
    async def test_missing_dependency(self, tool):
        with patch.dict("sys.modules", {"scrapling": None}):
            result = await tool.execute(url="https://example.com")
            assert result.error is not None
            assert "scrapling" in result.error
            assert "codepi[web]" in result.error

    @pytest.mark.asyncio
    async def test_no_url_or_start_urls(self, tool):
        mock_scrapling = MagicMock()
        with patch.dict("sys.modules", {"scrapling": mock_scrapling}):
            import importlib
            import codepi.tools.web.site_scrap as mod
            importlib.reload(mod)
            t = mod.SiteScrapTool()
            result = await t.execute()
        assert result.error is not None
        assert "url" in result.error.lower() or "start_urls" in result.error.lower()

    @pytest.mark.asyncio
    async def test_stealthy_fetcher_missing(self, tool):
        mock_scrapling = MagicMock()
        mock_scrapling.Fetcher = MagicMock()
        mock_scrapling.StealthyFetcher = None
        del mock_scrapling.StealthyFetcher

        with patch.dict("sys.modules", {"scrapling": mock_scrapling}):
            import importlib
            import codepi.tools.web.site_scrap as mod
            importlib.reload(mod)
            t = mod.SiteScrapTool()
            result = await t.execute(url="https://example.com", fetcher="stealthy")
        assert result.error is not None
        assert "web-full" in result.error


class TestGitHubMode:
    @pytest.mark.asyncio
    async def test_github_url_detection(self, tool):
        mock_scrapling = MagicMock()
        with patch.dict("sys.modules", {"scrapling": mock_scrapling}):
            import importlib
            import codepi.tools.web.site_scrap as mod
            importlib.reload(mod)
            t = mod.SiteScrapTool()

            mock_proc = AsyncMock()
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_proc.returncode = 0

            with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
                with patch("asyncio.wait_for", return_value=(b"", b"")):
                    result = await t.execute(url="https://github.com/user/repo")




class TestSelectorExtraction:
    def test_css_text_extraction(self, tool):
        mock_page = MagicMock()
        mock_el = MagicMock()
        mock_el.get_text.return_value = "Hello"
        mock_page.css.return_value = [mock_el]
        result = tool._extract_with_selector(mock_page, ".title::text", "css")
        assert result == ["Hello"]

    def test_css_attr_extraction(self, tool):
        mock_page = MagicMock()
        mock_el = MagicMock()
        mock_el.get.return_value = "https://link"
        mock_page.css.return_value = [mock_el]
        result = tool._extract_with_selector(mock_page, "a::attr(href)", "css")
        assert result == ["https://link"]

    def test_xpath_extraction(self, tool):
        mock_page = MagicMock()
        mock_el = MagicMock()
        mock_el.get_text.return_value = "XPath result"
        mock_page.xpath.return_value = [mock_el]
        result = tool._extract_with_selector(mock_page, "//div/text()", "xpath")
        assert result == ["XPath result"]
