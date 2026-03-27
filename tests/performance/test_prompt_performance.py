"""Performance tests for prompt composition overhead."""

import pytest
import time
from codepi.prompts.composer import PromptComposer, PromptConfig
from codepi.prompts.components import persona, tools, constraints, efficiency, modes


class TestPromptCompositionPerformance:
    def test_composer_compose_performance(self):
        composer = PromptComposer()
        config = PromptConfig()
        
        start = time.perf_counter()
        for _ in range(100):
            composer.compose(config)
        elapsed = time.perf_counter() - start
        
        avg_ms = (elapsed / 100) * 1000
        assert avg_ms < 10, f"Prompt composition too slow: {avg_ms:.2f}ms avg"
        print(f"\nPrompt composition: {avg_ms:.3f}ms avg over 100 iterations")

    def test_component_generation_performance(self):
        components = [
            lambda: persona.PERSONA_BASE,
            lambda: tools.TOOL_USAGE_RULES,
            lambda: constraints.SAFETY_CONSTRAINTS,
            lambda: efficiency.OUTPUT_EFFICIENCY,
        ]
        
        start = time.perf_counter()
        for _ in range(100):
            for comp in components:
                comp()
        elapsed = time.perf_counter() - start
        
        avg_ms = (elapsed / 400) * 1000
        assert avg_ms < 1, f"Component generation too slow: {avg_ms:.2f}ms avg"
        print(f"\nComponent generation: {avg_ms:.3f}ms avg over 400 calls")

    def test_mode_prompt_performance(self):
        start = time.perf_counter()
        for _ in range(100):
            for phase in range(1, 6):
                modes.get_plan_mode_prompt(phase=phase)
        elapsed = time.perf_counter() - start
        
        avg_ms = (elapsed / 500) * 1000
        assert avg_ms < 1, f"Mode prompt generation too slow: {avg_ms:.2f}ms avg"
        print(f"\nMode prompt generation: {avg_ms:.3f}ms avg over 500 calls")

    def test_auto_mode_prompt_performance(self):
        start = time.perf_counter()
        for _ in range(100):
            modes.get_auto_mode_prompt(max_iterations=100, require_approval_for=["push", "pr"])
        elapsed = time.perf_counter() - start
        
        avg_ms = (elapsed / 100) * 1000
        assert avg_ms < 1, f"Auto mode prompt too slow: {avg_ms:.2f}ms avg"
        print(f"\nAuto mode prompt: {avg_ms:.3f}ms avg over 100 calls")

    def test_full_system_prompt_composition(self):
        composer = PromptComposer()
        
        start = time.perf_counter()
        for _ in range(50):
            config = PromptConfig(
                mode_constraints=modes.get_plan_mode_prompt(phase=1),
            )
            composer.compose(config)
        elapsed = time.perf_counter() - start
        
        avg_ms = (elapsed / 50) * 1000
        assert avg_ms < 20, f"Full prompt composition too slow: {avg_ms:.2f}ms avg"
        print(f"\nFull system prompt: {avg_ms:.3f}ms avg over 50 iterations")

    def test_template_caching_effectiveness(self):
        composer = PromptComposer()
        
        start = time.perf_counter()
        composer.compose(PromptConfig())
        first_render = time.perf_counter() - start
        
        start = time.perf_counter()
        for _ in range(100):
            composer.compose(PromptConfig())
        cached_renders = (time.perf_counter() - start) / 100
        
        print(f"\nFirst render: {first_render*1000:.3f}ms, Cached avg: {cached_renders*1000:.3f}ms")


class TestMemoryOverhead:
    def test_prompt_composer_memory_efficiency(self):
        import sys
        
        composer = PromptComposer()
        base_size = sys.getsizeof(composer)
        
        for i in range(10):
            composer.compose(PromptConfig())
        
        final_size = sys.getsizeof(composer)
        assert final_size < base_size + 10000, "Memory leak in composer"
        print(f"\nComposer memory: base={base_size}, final={final_size}")
