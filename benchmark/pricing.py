"""Pricing model and per-call token-cost computation.

Prices are USD per 1,000,000 tokens, verified 2026-05-21:
  - gpt-4o (gpt-4o-2024-08-06) -- https://openai.com/api/pricing/
        input $2.50, cached input $1.25, output $10.00
        (OpenAI does not charge a cache-write premium; the first request pays
         the normal input rate, so cache_write rate == input rate and
         cache_write_tokens is always 0 for OpenAI.)
  - claude-haiku-4-5 -- Anthropic published pricing
        input $1.00, cache-read $0.10 (0.1x), cache-write $1.25 (1.25x, 5-min
        ephemeral), output $5.00
  - gpt-4o-mini / fast models included for completeness.
"""
from __future__ import annotations

from dataclasses import dataclass

PER_MILLION = 1_000_000

# USD per 1M tokens.
PRICING = {
    "gpt-4o": {"input": 2.50, "cached": 1.25, "cache_write": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "cached": 0.075, "cache_write": 0.15, "output": 0.60},
    "claude-haiku-4-5": {"input": 1.00, "cached": 0.10, "cache_write": 1.25, "output": 5.00},
}


@dataclass
class Usage:
    """Provider-normalized token usage for a single API call.

    All four buckets are mutually exclusive so cost is a clean dot product
    with the rate table:
      input_tokens        uncached input, billed at the full input rate
      cached_tokens       cache reads, billed at the cheap cached rate
      cache_write_tokens  cache creation (Anthropic only); 0 for OpenAI
      output_tokens       completion tokens
    """

    input_tokens: int = 0
    cached_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_input(self) -> int:
        return self.input_tokens + self.cached_tokens + self.cache_write_tokens


def cost_usd(model: str, usage: Usage) -> float:
    """Cost of one call in USD, given the model and its normalized usage."""
    p = PRICING[model]
    return (
        usage.input_tokens * p["input"]
        + usage.cached_tokens * p["cached"]
        + usage.cache_write_tokens * p["cache_write"]
        + usage.output_tokens * p["output"]
    ) / PER_MILLION


def usage_from_openai(resp_usage: dict) -> Usage:
    """Normalize an OpenAI chat.completions `usage` object.

    OpenAI's `prompt_tokens` includes the cached portion, so the uncached
    remainder is `prompt_tokens - cached_tokens`.
    """
    prompt = resp_usage.get("prompt_tokens", 0) or 0
    details = resp_usage.get("prompt_tokens_details") or {}
    cached = details.get("cached_tokens", 0) or 0
    return Usage(
        input_tokens=prompt - cached,
        cached_tokens=cached,
        cache_write_tokens=0,
        output_tokens=resp_usage.get("completion_tokens", 0) or 0,
    )


def usage_from_anthropic(resp_usage: dict) -> Usage:
    """Normalize an Anthropic messages `usage` object.

    Anthropic's `input_tokens` is already the uncached remainder; cache reads
    and cache writes are reported separately.
    """
    return Usage(
        input_tokens=resp_usage.get("input_tokens", 0) or 0,
        cached_tokens=resp_usage.get("cache_read_input_tokens", 0) or 0,
        cache_write_tokens=resp_usage.get("cache_creation_input_tokens", 0) or 0,
        output_tokens=resp_usage.get("output_tokens", 0) or 0,
    )
