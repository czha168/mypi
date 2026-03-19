import asyncio
from pathlib import Path
from mypi.config import load_config
from mypi.ai.openai_compat import OpenAICompatProvider
from mypi.core.session_manager import SessionManager
from mypi.tools.builtins import make_builtin_registry
from mypi.modes.sdk import SDK
   
config = load_config()

provider = OpenAICompatProvider(
    base_url=config.provider.base_url,
    api_key=config.provider.api_key,
    default_model=config.provider.model,
)

sm = SessionManager(sessions_dir=config.paths.sessions_dir)
sm.new_session(model=config.provider.model)

sdk = SDK(
    provider=provider,
    session_manager=sm,
    model=config.provider.model,
    tool_registry=make_builtin_registry(),
    system_prompt="You are a code review assistant.",  # optional
)

async def main():
    response = await sdk.prompt("Write a Python bubble sort function for integer array.")
    print(response)

asyncio.run(main())
