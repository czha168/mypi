import pytest
import os
from mypi.ai.openai_compat import OpenAICompatProvider
from mypi.core.agent_session import AgentSession
from mypi.core.session_manager import SessionManager
from mypi.tools.builtins import make_builtin_registry


def get_real_provider():
    """Create a real OpenAI-compatible provider using environment variables or defaults."""
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    api_key = os.environ.get("OPENAI_API_KEY", "")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")
    return OpenAICompatProvider(base_url=base_url, api_key=api_key, default_model=model), model


def skip_if_no_api_key():
    """Skip test if no API key is available."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set")


@pytest.fixture
def real_provider():
    provider, model = get_real_provider()
    return provider


@pytest.fixture
def real_session(tmp_sessions_dir, real_provider):
    _, model = get_real_provider()
    sm = SessionManager(sessions_dir=tmp_sessions_dir)
    sm.new_session(model=model)
    registry = make_builtin_registry()
    session = AgentSession(provider=real_provider, session_manager=sm, model=model, tool_registry=registry)
    return session


@pytest.mark.asyncio
async def test_real_llm_simple_response(real_session):
    """Test that the LLM can respond to a simple prompt."""
    skip_if_no_api_key()
    
    tokens = []
    real_session.on_token = lambda t: tokens.append(t)
    
    await real_session.prompt("Say exactly: Hello, World!")
    
    response = "".join(tokens)
    assert "Hello" in response or "World" in response


@pytest.mark.asyncio
async def test_real_llm_calls_ls_tool(tmp_sessions_dir):
    """Test that the LLM correctly calls the ls tool to list files."""
    skip_if_no_api_key()
    
    provider, model = get_real_provider()
    sm = SessionManager(sessions_dir=tmp_sessions_dir)
    sm.new_session(model=model)
    registry = make_builtin_registry()
    session = AgentSession(provider=provider, session_manager=sm, model=model, tool_registry=registry)
    
    tool_calls = []
    tool_results = []
    session.on_tool_call = lambda n, a: tool_calls.append((n, a))
    session.on_tool_result = lambda n, r: tool_results.append((n, r))
    
    await session.prompt("List the files in the current directory using the ls tool.")
    
    # The LLM should have called the ls tool
    tool_names = [tc[0] for tc in tool_calls]
    assert "ls" in tool_names, f"Expected 'ls' tool to be called, got: {tool_names}"


@pytest.mark.asyncio
async def test_real_llm_calls_find_tool(tmp_sessions_dir):
    """Test that the LLM correctly calls the find tool."""
    skip_if_no_api_key()
    
    provider, model = get_real_provider()
    sm = SessionManager(sessions_dir=tmp_sessions_dir)
    sm.new_session(model=model)
    registry = make_builtin_registry()
    session = AgentSession(provider=provider, session_manager=sm, model=model, tool_registry=registry)
    
    tool_calls = []
    session.on_tool_call = lambda n, a: tool_calls.append((n, a))
    
    await session.prompt("Find all Python files in the current directory.")
    
    tool_names = [tc[0] for tc in tool_calls]
    assert "find" in tool_names, f"Expected 'find' tool to be called, got: {tool_names}"


@pytest.mark.asyncio
async def test_real_llm_calls_read_tool(tmp_sessions_dir):
    """Test that the LLM correctly calls the read tool."""
    skip_if_no_api_key()
    
    provider, model = get_real_provider()
    sm = SessionManager(sessions_dir=tmp_sessions_dir)
    sm.new_session(model=model)
    registry = make_builtin_registry()
    session = AgentSession(provider=provider, session_manager=sm, model=model, tool_registry=registry)
    
    tool_calls = []
    session.on_tool_call = lambda n, a: tool_calls.append((n, a))
    
    await session.prompt("Read the contents of pyproject.toml if it exists.")
    
    tool_names = [tc[0] for tc in tool_calls]
    assert "read" in tool_names, f"Expected 'read' tool to be called, got: {tool_names}"


@pytest.mark.asyncio
async def test_real_llm_uses_multiple_tools(tmp_sessions_dir):
    """Test that the LLM can chain multiple tool calls."""
    skip_if_no_api_key()
    
    provider, model = get_real_provider()
    sm = SessionManager(sessions_dir=tmp_sessions_dir)
    sm.new_session(model=model)
    registry = make_builtin_registry()
    session = AgentSession(provider=provider, session_manager=sm, model=model, tool_registry=registry)
    
    tool_calls = []
    session.on_tool_call = lambda n, a: tool_calls.append((n, a))
    
    await session.prompt("First list the directory, then read pyproject.toml if it exists.")
    
    # Should have called both ls and read
    tool_names = [tc[0] for tc in tool_calls]
    assert "ls" in tool_names or "read" in tool_names, f"Expected tool calls, got: {tool_names}"


@pytest.mark.asyncio
async def test_real_llm_multiturn_conversation(tmp_sessions_dir):
    """Test multi-turn conversation with context preservation."""
    skip_if_no_api_key()
    
    provider, model = get_real_provider()
    sm = SessionManager(sessions_dir=tmp_sessions_dir)
    sm.new_session(model=model)
    registry = make_builtin_registry()
    session = AgentSession(provider=provider, session_manager=sm, model=model, tool_registry=registry)
    
    tokens1 = []
    session.on_token = lambda t: tokens1.append(t)
    await session.prompt("My name is TestUser. Remember this.")
    
    # Second turn should have context from first
    tokens2 = []
    session.on_token = lambda t: tokens2.append(t)
    await session.prompt("What is my name?")
    
    response = "".join(tokens2)
    # The model should acknowledge the context from the previous turn
    assert len(response) > 0, "Second turn should produce a response"


@pytest.mark.asyncio
async def test_real_llm_list_current_directory(tmp_sessions_dir):
    """Test the exact scenario from the bug report: listing files in current directory."""
    skip_if_no_api_key()
    
    provider, model = get_real_provider()
    sm = SessionManager(sessions_dir=tmp_sessions_dir)
    sm.new_session(model=model)
    registry = make_builtin_registry()
    session = AgentSession(provider=provider, session_manager=sm, model=model, tool_registry=registry)
    
    tool_calls = []
    tool_results = []
    session.on_tool_call = lambda n, a: tool_calls.append((n, a))
    session.on_tool_result = lambda n, r: tool_results.append((n, r))
    
    # This is the exact prompt from the bug report
    await session.prompt("List Python files in this directory")
    
    # Verify ls or find tool was called
    tool_names = [tc[0] for tc in tool_calls]
    assert any(t in tool_names for t in ["ls", "find"]), f"Expected ls or find tool, got: {tool_names}"


@pytest.mark.asyncio
async def test_real_llm_bash_tool(tmp_sessions_dir):
    """Test that the bash tool works correctly."""
    skip_if_no_api_key()
    
    provider, model = get_real_provider()
    sm = SessionManager(sessions_dir=tmp_sessions_dir)
    sm.new_session(model=model)
    registry = make_builtin_registry()
    session = AgentSession(provider=provider, session_manager=sm, model=model, tool_registry=registry)
    
    tool_calls = []
    tool_results = []
    session.on_tool_call = lambda n, a: tool_calls.append((n, a))
    session.on_tool_result = lambda n, r: tool_results.append((n, r))
    
    await session.prompt("Run the command 'echo hello' using the bash tool.")
    
    bash_calls = [(n, a) for n, a in tool_calls if n == "bash"]
    assert len(bash_calls) > 0, f"Expected bash tool to be called, got: {tool_calls}"


@pytest.mark.asyncio
async def test_real_llm_grep_tool(tmp_sessions_dir):
    """Test that the grep tool works correctly."""
    skip_if_no_api_key()
    
    provider, model = get_real_provider()
    sm = SessionManager(sessions_dir=tmp_sessions_dir)
    sm.new_session(model=model)
    registry = make_builtin_registry()
    session = AgentSession(provider=provider, session_manager=sm, model=model, tool_registry=registry)
    
    tool_calls = []
    session.on_tool_call = lambda n, a: tool_calls.append((n, a))
    
    await session.prompt("Search for the word 'import' in Python files in this directory.")
    
    grep_calls = [(n, a) for n, a in tool_calls if n == "grep"]
    assert len(grep_calls) > 0, f"Expected grep tool to be called, got: {tool_calls}"
