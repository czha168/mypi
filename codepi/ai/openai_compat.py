from __future__ import annotations
import json
from typing import AsyncGenerator
import openai
from codepi.ai.provider import LLMProvider, ProviderEvent, TokenEvent, LLMToolCallEvent, DoneEvent, TokenUsage


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
    ) -> AsyncGenerator[ProviderEvent, None]:
        full_messages = ([{"role": "system", "content": system}] if system else []) + messages
        create_kwargs = dict(model=model, messages=full_messages, stream=True, **kwargs)
        if tools:
            create_kwargs["tools"] = tools

        # Accumulate streaming tool call arguments (may arrive in multiple chunks)
        pending_tool_calls: dict[int, dict] = {}

        result = self._client.chat.completions.create(**create_kwargs)  # type: ignore[reportCallIssue]
        response = await result if hasattr(result, '__await__') else result
        async for chunk in response:
            choice = chunk.choices[0] if chunk.choices else None
            if choice is None:
                usage = getattr(chunk, "usage", None)
                if usage:
                    yield DoneEvent(usage=TokenUsage(
                        input_tokens=usage.prompt_tokens,
                        output_tokens=usage.completion_tokens,
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

            usage = getattr(chunk, "usage", None)
            if usage:
                yield DoneEvent(usage=TokenUsage(
                    input_tokens=usage.prompt_tokens,
                    output_tokens=usage.completion_tokens,
                ))
