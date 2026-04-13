import pytest
from unittest.mock import patch, MagicMock
from codepi.tools.web.web_search import WebSearchTool


@pytest.fixture
def tool():
    return WebSearchTool()


def _make_ddgs_mock(results):
    mock_instance = MagicMock()
    mock_instance.text.return_value = results
    return mock_instance


class TestWebSearchTool:
    def test_name_and_schema(self, tool):
        assert tool.name == "web_search"
        assert "query" in tool.input_schema["properties"]
        assert "max_results" in tool.input_schema["properties"]
        assert tool.input_schema["required"] == ["query"]

    @pytest.mark.asyncio
    async def test_missing_dependency(self, tool):
        with patch.dict("sys.modules", {"ddgs": None}):
            result = await tool.execute(query="test")
            assert result.error is not None
            assert "ddgs" in result.error
            assert "codepi[web]" in result.error

    @pytest.mark.asyncio
    async def test_search_returns_results(self, tool):
        mock = _make_ddgs_mock([
            {"title": "Result 1", "href": "https://example.com/1", "body": "Snippet 1"},
            {"title": "Result 2", "href": "https://example.com/2", "body": "Snippet 2"},
        ])
        with patch("ddgs.DDGS", return_value=mock):
            result = await tool.execute(query="test")
        assert result.error is None
        assert "Result 1" in result.output
        assert "https://example.com/1" in result.output
        assert "Snippet 1" in result.output

    @pytest.mark.asyncio
    async def test_search_no_results(self, tool):
        mock = _make_ddgs_mock([])
        with patch("ddgs.DDGS", return_value=mock):
            result = await tool.execute(query="obscure query xyz")
        assert "No results found" in result.output

    @pytest.mark.asyncio
    async def test_clamps_max_results_high(self, tool):
        mock = _make_ddgs_mock([{"title": f"R{i}", "href": f"http://x/{i}", "body": f"B{i}"} for i in range(20)])
        with patch("ddgs.DDGS", return_value=mock) as ddgs_cls:
            await tool.execute(query="test", max_results=50)
        ddgs_cls.return_value.text.assert_called_once_with("test", max_results=20)

    @pytest.mark.asyncio
    async def test_clamps_max_results_low(self, tool):
        mock = _make_ddgs_mock([{"title": "R", "href": "http://x", "body": "B"}])
        with patch("ddgs.DDGS", return_value=mock) as ddgs_cls:
            await tool.execute(query="test", max_results=0)
        ddgs_cls.return_value.text.assert_called_once_with("test", max_results=1)
