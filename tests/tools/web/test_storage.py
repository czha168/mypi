import pytest
from codepi.tools.web.storage import url_to_slug, save_content, get_web_temp_dir


class TestUrlToSlug:
    def test_normal_url(self):
        assert url_to_slug("https://docs.python.org/3/library/asyncio.html") == "docs-python-org-3-library-asyncio-html"

    def test_url_with_trailing_slash(self):
        result = url_to_slug("https://example.com/path/")
        assert result == "example-com-path"

    def test_long_url_truncated(self):
        long_url = "https://example.com/" + "a" * 200
        result = url_to_slug(long_url)
        assert len(result) <= 80

    def test_special_characters(self):
        result = url_to_slug("https://example.com/path?q=1&b=2#section")
        assert result == "example-com-path-q-1-b-2-section"

    def test_github_url(self):
        result = url_to_slug("https://github.com/user/repo/tree/main/src")
        assert result == "github-com-user-repo-tree-main-src"

    def test_no_leading_trailing_hyphens(self):
        result = url_to_slug("https://example.com///path///")
        assert not result.startswith("-")
        assert not result.endswith("-")

    def test_http_scheme(self):
        result = url_to_slug("http://example.com/page")
        assert result == "example-com-page"
        assert "http" not in result


class TestGetWebTempDir:
    def test_creates_directory(self, tmp_path, monkeypatch):
        monkeypatch.setattr("codepi.tools.web.storage.Path", lambda p: tmp_path / p.lstrip("/tmp/"))
        result = get_web_temp_dir("test-session")
        assert result.exists()

    def test_idempotent(self):
        result1 = get_web_temp_dir("test-session-2")
        result2 = get_web_temp_dir("test-session-2")
        assert result1 == result2


class TestSaveContent:
    def test_saves_file(self):
        path = save_content("test-sess", "web", "test-slug", "hello world", "md")
        assert path.exists()
        assert path.read_text() == "hello world"
        assert path.name == "test-slug.md"

    def test_creates_subdirectory(self):
        path = save_content("test-sess-sd", "scrap", "slug2", "data", "json")
        assert path.exists()
        assert "scrap" in str(path)
