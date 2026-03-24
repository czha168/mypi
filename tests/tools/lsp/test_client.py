from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from mypi.tools.lsp.client import LSPClientManager, NO_SERVER_ERROR


class TestLSPClientManager:
    def setup_method(self):
        LSPClientManager._instance = None
        LSPClientManager._client = None
        LSPClientManager._workspace_root = None
        LSPClientManager._server_type = None

    def test_singleton_pattern(self):
        manager1 = LSPClientManager()
        manager2 = LSPClientManager()
        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_no_server_available_raises_error(self, tmp_path):
        with patch.object(LSPClientManager, "detect_server", return_value=None):
            with pytest.raises(RuntimeError) as exc_info:
                await LSPClientManager.get_client(tmp_path)
            assert "No Python LSP server found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_detect_server_priority(self):
        with patch("mypi.tools.lsp.client.shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: cmd == "pyright-langserver"

            result = LSPClientManager.detect_server()
            assert result == "pyright"

    @pytest.mark.asyncio
    async def test_detect_server_falls_back_to_pylsp(self):
        with patch("mypi.tools.lsp.client.shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: cmd == "pylsp"

            result = LSPClientManager.detect_server()
            assert result == "pylsp"

    @pytest.mark.asyncio
    async def test_detect_server_falls_back_to_jedi(self):
        with patch("mypi.tools.lsp.client.shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: cmd == "jedi-language-server"

            result = LSPClientManager.detect_server()
            assert result == "jedi-language-server"

    @pytest.mark.asyncio
    async def test_detect_server_returns_none_when_nothing_available(self):
        with patch("mypi.tools.lsp.client.shutil.which", return_value=None):
            result = LSPClientManager.detect_server()
            assert result is None

    @pytest.mark.asyncio
    async def test_get_client_returns_same_instance_for_same_workspace(self, tmp_path):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch.object(LSPClientManager, "detect_server", return_value="pyright"):
            with patch.object(
                LSPClientManager, "_start_server", return_value=mock_client
            ):
                client1 = await LSPClientManager.get_client(tmp_path)
                client2 = await LSPClientManager.get_client(tmp_path)
                assert client1 is client2

    @pytest.mark.asyncio
    async def test_shutdown_clears_state(self, tmp_path):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch.object(LSPClientManager, "detect_server", return_value="pyright"):
            with patch.object(
                LSPClientManager, "_start_server", return_value=mock_client
            ):
                await LSPClientManager.get_client(tmp_path)
                await LSPClientManager.shutdown()

                assert LSPClientManager._client is None
                assert LSPClientManager._workspace_root is None
                assert LSPClientManager._server_type is None

    @pytest.mark.asyncio
    async def test_is_running(self, tmp_path):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        assert not LSPClientManager.is_running()

        with patch.object(LSPClientManager, "detect_server", return_value="pyright"):
            with patch.object(
                LSPClientManager, "_start_server", return_value=mock_client
            ):
                await LSPClientManager.get_client(tmp_path)
                assert LSPClientManager.is_running()

    @pytest.mark.asyncio
    async def test_get_server_type(self, tmp_path):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        assert LSPClientManager.get_server_type() is None

        with patch.object(LSPClientManager, "detect_server", return_value="pylsp"):
            with patch.object(
                LSPClientManager, "_start_server", return_value=mock_client
            ):
                await LSPClientManager.get_client(tmp_path)
                assert LSPClientManager.get_server_type() == "pylsp"
