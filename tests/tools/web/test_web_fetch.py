import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from codepi.tools.web.web_fetch import WebFetchTool


@pytest.fixture
def tool():
    return WebFetchTool()


class TestWebFetchTool:
    def test_name_and_schema(self, tool):
        assert tool.name == "web_fetch"
        assert "url" in tool.input_schema["properties"]
        assert "max_length" in tool.input_schema["properties"]
        assert tool.input_schema["required"] == ["url"]

    @pytest.mark.asyncio
    async def test_missing_dependency(self, tool):
        with patch.dict("sys.modules", {"httpx": None, "trafilatura": None}):
            result = await tool.execute(url="https://example.com")
            assert result.error is not None
            assert "httpx" in result.error
            assert "codepi[web]" in result.error

    @pytest.mark.asyncio
    async def test_successful_fetch(self, tool):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><p>Hello world article content that is long enough to not trigger js detection</p></body></html>"
        mock_response.headers = {"content-type": "text/html"}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        mock_httpx = MagicMock()
        mock_httpx.AsyncClient = MagicMock(return_value=mock_client)

        mock_trafilatura = MagicMock()
        mock_trafilatura.extract.return_value = "Hello world article content that is long enough to not trigger js detection"
        mock_trafilatura.bare_extraction.return_value = {"title": "Test Page", "author": "Author", "sitename": "example.com", "date": "2026-01-01"}

        with patch.dict("sys.modules", {"httpx": mock_httpx, "trafilatura": mock_trafilatura}):
            import importlib
            import codepi.tools.web.web_fetch as mod
            importlib.reload(mod)
            t = mod.WebFetchTool()
            result = await t.execute(url="https://example.com/page")

        assert result.error is None
        assert "Saved to" in result.output
        assert "Test Page" in result.output

    @pytest.mark.asyncio
    async def test_js_only_detection(self, tool):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><body><div id="root"></div></body></html>'
        mock_response.headers = {}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        mock_httpx = MagicMock()
        mock_httpx.AsyncClient = MagicMock(return_value=mock_client)

        mock_trafilatura = MagicMock()
        mock_trafilatura.extract.return_value = ""
        mock_trafilatura.bare_extraction.return_value = {}

        with patch.dict("sys.modules", {"httpx": mock_httpx, "trafilatura": mock_trafilatura}):
            import importlib
            import codepi.tools.web.web_fetch as mod
            importlib.reload(mod)
            t = mod.WebFetchTool()
            result = await t.execute(url="https://spa-app.example.com")

        assert result.error is not None
        assert "site_scrap" in result.error

    @pytest.mark.asyncio
    async def test_bot_block_detection(self, tool):
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "<html>Just a moment...</html>"
        mock_response.headers = {"cf-mitigated": "challenge"}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        mock_httpx = MagicMock()
        mock_httpx.AsyncClient = MagicMock(return_value=mock_client)

        mock_trafilatura = MagicMock()

        with patch.dict("sys.modules", {"httpx": mock_httpx, "trafilatura": mock_trafilatura}):
            import importlib
            import codepi.tools.web.web_fetch as mod
            importlib.reload(mod)
            t = mod.WebFetchTool()
            result = await t.execute(url="https://protected.example.com")

        assert result.error is not None
        assert "anti-bot" in result.error
        assert "site_scrap" in result.error

    @pytest.mark.asyncio
    async def test_content_truncation(self, tool):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><p>content</p></body></html>"
        mock_response.headers = {}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        mock_httpx = MagicMock()
        mock_httpx.AsyncClient = MagicMock(return_value=mock_client)

        long_content = "x" * 20000
        mock_trafilatura = MagicMock()
        mock_trafilatura.extract.return_value = long_content
        mock_trafilatura.bare_extraction.return_value = {"title": "Long Page"}

        with patch.dict("sys.modules", {"httpx": mock_httpx, "trafilatura": mock_trafilatura}):
            import importlib
            import codepi.tools.web.web_fetch as mod
            importlib.reload(mod)
            t = mod.WebFetchTool()
            result = await t.execute(url="https://example.com/long", max_length=100)

        assert result.error is None
        # The file should have been saved with truncated content
        assert "Saved to" in result.output
