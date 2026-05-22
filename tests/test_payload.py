"""Payload-mapping + cost tests using fake SDK clients. No real API calls, no cost.

Verifies that:
  - OpenAI requests carry prompt_cache_key + prompt_cache_retention in extra_body and
    a leading system message.
  - Anthropic requests carry an ephemeral cache_control breakpoint on the system block
    AND on the last message.
  - The provider usage objects are normalized correctly and priced correctly.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from benchmark.clients import call_anthropic, call_openai  # noqa: E402
from benchmark.pricing import (  # noqa: E402
    cost_usd, usage_from_anthropic, usage_from_openai,
)


# ---- fake OpenAI client ----
class _FakeOAIResp:
    def __init__(self, content, usage):
        self._content = content
        self._usage = usage

        class _Msg:
            def __init__(s, c):
                s.content = c

        class _Choice:
            def __init__(s, c):
                s.message = _Msg(c)

        self.choices = [_Choice(content)]

    def model_dump(self):
        return {"choices": [{"message": {"content": self._content}}], "usage": self._usage}


class _FakeOAIClient:
    def __init__(self):
        self.captured = {}
        outer = self

        class _Completions:
            def create(self, **kwargs):
                outer.captured = kwargs
                return _FakeOAIResp(
                    "Q1: Where did you grow up?",
                    {"prompt_tokens": 1300, "completion_tokens": 10,
                     "prompt_tokens_details": {"cached_tokens": 1024}},
                )

        class _Chat:
            def __init__(self):
                self.completions = _Completions()

        self.chat = _Chat()


# ---- fake Anthropic client ----
class _FakeBlock:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class _FakeAnthResp:
    def __init__(self, text, usage):
        self.content = [_FakeBlock(text)]
        self._usage = usage

    def model_dump(self):
        return {"content": [{"type": "text", "text": self.content[0].text}], "usage": self._usage}


class _FakeAnthClient:
    def __init__(self):
        self.captured = {}
        outer = self

        class _Messages:
            def create(self, **kwargs):
                outer.captured = kwargs
                return _FakeAnthResp(
                    "Q1: Where did you grow up?",
                    {"input_tokens": 50, "cache_read_input_tokens": 4273,
                     "cache_creation_input_tokens": 0, "output_tokens": 10},
                )

        self.messages = _Messages()


def test_openai_payload_has_cache_key_and_retention():
    client = _FakeOAIClient()
    res = call_openai(
        client, model="gpt-4o", system="SYSTEM PROMPT",
        messages=[{"role": "user", "content": "ready"}],
        max_tokens=50, prompt_cache_key="kvbench-gpt-4o-A-n10",
    )
    kw = client.captured
    assert kw["messages"][0] == {"role": "system", "content": "SYSTEM PROMPT"}
    assert kw["extra_body"]["prompt_cache_key"] == "kvbench-gpt-4o-A-n10"
    assert kw["extra_body"]["prompt_cache_retention"] == "24h"
    assert res.text.startswith("Q1:")
    print("PASS test_openai_payload_has_cache_key_and_retention")


def test_anthropic_payload_has_cache_control_breakpoints():
    client = _FakeAnthClient()
    res = call_anthropic(
        client, model="claude-haiku-4-5", system="SYSTEM PROMPT",
        messages=[{"role": "user", "content": "u1"}, {"role": "assistant", "content": "a1"},
                  {"role": "user", "content": "u2"}],
        max_tokens=50, cache=True,
    )
    kw = client.captured
    # system must be a list whose block carries an ephemeral cache_control breakpoint
    assert isinstance(kw["system"], list)
    assert kw["system"][0]["cache_control"] == {"type": "ephemeral"}
    # the last message must carry the incremental cache breakpoint
    last = kw["messages"][-1]
    assert isinstance(last["content"], list)
    assert last["content"][0]["cache_control"] == {"type": "ephemeral"}
    # earlier messages must remain plain strings (only the last gets a breakpoint)
    assert isinstance(kw["messages"][0]["content"], str)
    assert res.text.startswith("Q1:")
    print("PASS test_anthropic_payload_has_cache_control_breakpoints")


def test_usage_normalization_and_cost():
    # OpenAI: prompt_tokens includes cached; uncached = 1300 - 1024 = 276
    ou = usage_from_openai({"prompt_tokens": 1300, "completion_tokens": 10,
                            "prompt_tokens_details": {"cached_tokens": 1024}})
    assert (ou.input_tokens, ou.cached_tokens, ou.cache_write_tokens, ou.output_tokens) == (276, 1024, 0, 10)
    oc = cost_usd("gpt-4o", ou)
    expected_oc = (276 * 2.50 + 1024 * 1.25 + 10 * 10.00) / 1_000_000
    assert abs(oc - expected_oc) < 1e-12, (oc, expected_oc)

    # Anthropic: input_tokens is already the uncached remainder
    au = usage_from_anthropic({"input_tokens": 50, "cache_read_input_tokens": 4273,
                               "cache_creation_input_tokens": 0, "output_tokens": 10})
    assert (au.input_tokens, au.cached_tokens, au.cache_write_tokens, au.output_tokens) == (50, 4273, 0, 10)
    ac = cost_usd("claude-haiku-4-5", au)
    expected_ac = (50 * 1.00 + 4273 * 0.10 + 0 * 1.25 + 10 * 5.00) / 1_000_000
    assert abs(ac - expected_ac) < 1e-12, (ac, expected_ac)
    print("PASS test_usage_normalization_and_cost")


if __name__ == "__main__":
    test_openai_payload_has_cache_key_and_retention()
    test_anthropic_payload_has_cache_control_breakpoints()
    test_usage_normalization_and_cost()
    print("\nALL PAYLOAD TESTS PASSED")
