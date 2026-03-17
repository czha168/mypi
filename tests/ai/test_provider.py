import pytest
from mypi.ai.provider import LLMProvider, TokenEvent, LLMToolCallEvent, DoneEvent, TokenUsage


def test_provider_event_types():
    tok = TokenEvent(text="hello")
    tool = LLMToolCallEvent(id="c1", name="read", arguments={"path": "x"})
    done = DoneEvent(usage=TokenUsage(input_tokens=100, output_tokens=50))
    assert tok.text == "hello"
    assert tool.name == "read"
    assert done.usage.input_tokens == 100


def test_llm_provider_is_abstract():
    import inspect
    assert inspect.isabstract(LLMProvider)
