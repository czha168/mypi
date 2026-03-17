from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, Union


@dataclass
class TokenEvent:
    text: str


@dataclass
class LLMToolCallEvent:
    """Emitted by provider when LLM requests a tool. Distinct from core ToolCallEvent."""
    id: str
    name: str
    arguments: dict


@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int


@dataclass
class DoneEvent:
    usage: TokenUsage


ProviderEvent = Union[TokenEvent, LLMToolCallEvent, DoneEvent]


class LLMProvider(ABC):
    @abstractmethod
    async def stream(
        self,
        messages: list[dict],
        tools: list[dict],
        model: str,
        system: str,
        **kwargs,
    ) -> AsyncIterator[ProviderEvent]: ...
