from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lsp_client import Client

NO_SERVER_ERROR = """No Python LSP server found. Install one of:
  - pyright:      pip install pyright
  - pylsp:        pip install python-lsp-server
  - jedi-language-server: pip install jedi-language-server

Then restart codepi."""


class LSPClientManager:
    _instance: LSPClientManager | None = None
    _client: Client | None = None
    _workspace_root: Path | None = None
    _server_type: str | None = None

    SERVER_PRIORITY = ["pyright", "pylsp", "jedi-language-server"]
    SERVER_COMMANDS = {
        "pyright": ["pyright-langserver", "--stdio"],
        "pylsp": ["pylsp"],
        "jedi-language-server": ["jedi-language-server"],
    }

    def __new__(cls) -> "LSPClientManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def detect_server(cls) -> str | None:
        for server in cls.SERVER_PRIORITY:
            cmd = cls.SERVER_COMMANDS.get(server, [])
            if cmd and shutil.which(cmd[0]):
                return server
        return None

    @classmethod
    async def get_client(
        cls, workspace_root: str | Path, server_override: str | None = None
    ) -> "Client":
        workspace = Path(workspace_root).resolve()

        if cls._client is not None and cls._workspace_root == workspace:
            return cls._client

        if cls._client is not None:
            await cls.shutdown()

        server_type = server_override or cls.detect_server()
        if not server_type:
            raise RuntimeError(NO_SERVER_ERROR)

        cls._client = await cls._start_server(server_type, workspace)
        cls._workspace_root = workspace
        cls._server_type = server_type
        return cls._client

    @classmethod
    async def _start_server(cls, server_type: str, workspace: Path) -> "Client":
        from attrs import define
        from lsp_client import Client
        from lsp_client.capability.request import (
            WithRequestDefinition,
            WithRequestReferences,
            WithRequestRename,
            WithRequestHover,
        )
        from lsp_client.capability.notification import WithReceivePublishDiagnostics
        from lsp_client.server import LocalServer

        cmd = cls.SERVER_COMMANDS.get(server_type, [])
        if not cmd:
            raise ValueError(f"Unknown server type: {server_type}")

        @define
        class MypiLSPClient(
            Client,
            WithRequestDefinition,
            WithRequestReferences,
            WithRequestRename,
            WithRequestHover,
            WithReceivePublishDiagnostics,
        ):
            _diagnostics: dict[str, list] = {}

            def create_default_servers(self):
                return LocalServer(program=cmd[0], args=cmd[1:] if len(cmd) > 1 else [])

            async def handle_publish_diagnostics(
                self, uri: str, diagnostics: list, version: int | None = None
            ) -> None:
                file_path = self.from_uri(uri)
                self._diagnostics[str(file_path)] = diagnostics

            def get_diagnostics(self, file_path: str) -> list:
                return self._diagnostics.get(file_path, [])

        client = MypiLSPClient(workspace=workspace)
        await client.__aenter__()
        return client

    @classmethod
    async def shutdown(cls) -> None:
        if cls._client is not None:
            try:
                await cls._client.__aexit__(None, None, None)
            except Exception:
                pass
            cls._client = None
        cls._workspace_root = None
        cls._server_type = None

    @classmethod
    def is_running(cls) -> bool:
        return cls._client is not None

    @classmethod
    def get_server_type(cls) -> str | None:
        return cls._server_type
