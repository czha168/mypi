import asyncio
import json
import sys

import pytest


@pytest.mark.asyncio
async def test_initialize_handshake_subprocess():
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "codepi", "--rpc",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    init_req = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": 1,
            "clientCapabilities": {},
            "clientInfo": {"name": "test", "title": "Test", "version": "0.1.0"},
        },
    }) + "\n"
    proc.stdin.write(init_req.encode())
    await proc.stdin.drain()

    resp_line = await asyncio.wait_for(proc.stdout.readline(), timeout=5)
    resp = json.loads(resp_line)

    assert resp["id"] == 1
    assert resp["result"]["protocolVersion"] == 1
    assert resp["result"]["agentInfo"]["name"] == "codepi"
    assert resp["result"]["agentCapabilities"]["loadSession"] is True
    assert resp["result"]["agentCapabilities"]["promptCapabilities"]["embeddedContext"] is True
    assert resp["result"]["authMethods"] == []

    proc.stdin.close()
    await proc.wait()


@pytest.mark.asyncio
async def test_initialize_then_new_session_subprocess():
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "codepi", "--rpc",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    init_req = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": 1,
            "clientCapabilities": {},
            "clientInfo": {"name": "test", "title": "Test", "version": "0.1.0"},
        },
    }) + "\n"
    proc.stdin.write(init_req.encode())
    await proc.stdin.drain()
    await asyncio.wait_for(proc.stdout.readline(), timeout=5)

    session_req = json.dumps({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "session/new",
        "params": {"cwd": "/tmp", "mcpServers": []},
    }) + "\n"
    proc.stdin.write(session_req.encode())
    await proc.stdin.drain()

    resp_line = await asyncio.wait_for(proc.stdout.readline(), timeout=5)
    resp = json.loads(resp_line)

    assert resp["id"] == 2
    assert "sessionId" in resp["result"]
    mode_ids = [m["id"] for m in resp["result"]["modes"]["availableModes"]]
    assert "code" in mode_ids
    assert resp["result"]["modes"]["currentModeId"] == "code"

    proc.stdin.close()
    await proc.wait()


@pytest.mark.asyncio
async def test_clean_exit_on_eof():
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "codepi", "--rpc",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    proc.stdin.close()
    await asyncio.wait_for(proc.wait(), timeout=5)
    assert proc.returncode == 0
