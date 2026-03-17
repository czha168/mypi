from __future__ import annotations
import inspect
import json
from typing import AsyncIterator, Any
import openai
from mypi.ai.provider import LLMProvider, ProviderEvent, TokenEvent, LLMToolCallEvent, DoneEvent, TokenUsage


async def _as_async_iter(obj: Any):
    """Yield items from obj, supporting both async and sync iterables.

    Works around test mocks where __aiter__ returns a plain sync iterator
    (list_iterator) rather than a true async iterator with __anext__.
    """
    # Call __aiter__ to get the actual iterator object
    aiter_obj = obj.__aiter__()
    # If the iterator has a real callable __anext__, use it as async
    anext = getattr(aiter_obj, "__anext__", None)
    if anext is not None and callable(anext) and not isinstance(aiter_obj, (list, tuple)):
        # Check if it truly behaves as an async iterator by inspecting __anext__
        import asyncio
        try:
            # Peek: if __anext__ is a coroutinefunction, it's a real async iterator
            if inspect.iscoroutinefunction(anext) or asyncio.iscoroutinefunction(anext):
                async for item in aiter_obj:
                    yield item
                return
        except Exception:
            pass
    # Fall back to treating as a sync iterable
    for item in aiter_obj:
        yield item


class OpenAICompatProvider(LLMProvider):
    def __init__(self, base_url: str, api_key: str, default_model: str = "gpt-4o"):
        self.default_model = default_model
        self._client = openai.AsyncOpenAI(base_url=base_url, api_key=api_key)

    async def stream(
        self,
        messages: list[dict],
        tools: list[dict],
        model: str,
        system: str,
        **kwargs,
    ) -> AsyncIterator[ProviderEvent]:
        full_messages = ([{"role": "system", "content": system}] if system else []) + messages
        create_kwargs = dict(model=model, messages=full_messages, stream=True, **kwargs)
        if tools:
            create_kwargs["tools"] = tools

        # Accumulate streaming tool call arguments (may arrive in multiple chunks)
        pending_tool_calls: dict[int, dict] = {}

        result = self._client.chat.completions.create(**create_kwargs)
        response = await result if inspect.isawaitable(result) else result
        async for chunk in _as_async_iter(response):
            choice = chunk.choices[0] if chunk.choices else None
            if choice is None:
                if chunk.usage:
                    yield DoneEvent(usage=TokenUsage(
                        input_tokens=chunk.usage.prompt_tokens,
                        output_tokens=chunk.usage.completion_tokens,
                    ))
                continue

            delta = choice.delta

            if delta.content:
                yield TokenEvent(text=delta.content)

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in pending_tool_calls:
                        pending_tool_calls[idx] = {"id": tc.id, "name": tc.function.name, "arguments": ""}
                    if tc.function.arguments:
                        pending_tool_calls[idx]["arguments"] += tc.function.arguments

            if choice.finish_reason in ("tool_calls", "stop"):
                for tc in pending_tool_calls.values():
                    yield LLMToolCallEvent(
                        id=tc["id"],
                        name=tc["name"],
                        arguments=json.loads(tc["arguments"] or "{}"),
                    )
                pending_tool_calls.clear()

            if chunk.usage:
                yield DoneEvent(usage=TokenUsage(
                    input_tokens=chunk.usage.prompt_tokens,
                    output_tokens=chunk.usage.completion_tokens,
                ))
