"""Native-SDK wrappers for OpenAI and Anthropic with prompt caching + retry.

Both wrappers return a uniform CallResult (text, normalized Usage, and the full
request/response payloads for logging). Caching is configured per the providers'
native mechanisms:

  OpenAI    -- automatic prefix caching on prefixes >= 1024 tokens. We pass
               prompt_cache_key (stabilizes routing) and prompt_cache_retention
               ("24h", maximizes cross-round retention) via extra_body so they
               reach the wire regardless of the installed SDK's typed signature.
  Anthropic -- explicit cache_control. We attach an ephemeral breakpoint to the
               static system block (the 100-question prompt) and a second
               incremental breakpoint to the last message, so a stable prefix
               (Strategy A / C) is read from cache on subsequent turns.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass

import anthropic
import openai

from .pricing import Usage, usage_from_anthropic, usage_from_openai

# Transient errors worth retrying with backoff (the SDKs also retry internally,
# but we add an outer loop so a config can survive a longer rate-limit window).
_RETRYABLE = (
    openai.RateLimitError,
    openai.APIConnectionError,
    openai.APITimeoutError,
    openai.InternalServerError,
    anthropic.RateLimitError,
    anthropic.APIConnectionError,
    anthropic.APITimeoutError,
    anthropic.InternalServerError,
)


@dataclass
class CallResult:
    text: str
    usage: Usage
    request: dict
    response: dict


def with_retry(fn, *, max_attempts: int = 6, base: float = 1.0, max_delay: float = 45.0):
    """Call `fn` with exponential backoff on transient API errors."""
    last_exc = None
    for attempt in range(max_attempts):
        try:
            return fn()
        except _RETRYABLE as exc:
            last_exc = exc
            if attempt == max_attempts - 1:
                break
            delay = min(base * (2 ** attempt) + random.uniform(0, 0.5), max_delay)
            time.sleep(delay)
    raise last_exc


def call_openai(
    client: "openai.OpenAI",
    *,
    model: str,
    system: str,
    messages: list[dict],
    max_tokens: int,
    prompt_cache_key: str,
    response_format: dict | None = None,
) -> CallResult:
    full_messages = [{"role": "system", "content": system}, *messages]
    extra_body = {
        "prompt_cache_key": prompt_cache_key,
        "prompt_cache_retention": "24h",
    }
    kwargs = dict(
        model=model,
        max_tokens=max_tokens,
        messages=full_messages,
        extra_body=extra_body,
    )
    if response_format is not None:
        kwargs["response_format"] = response_format

    resp = with_retry(lambda: client.chat.completions.create(**kwargs))
    resp_dict = resp.model_dump()
    text = resp.choices[0].message.content or ""
    usage = usage_from_openai(resp_dict.get("usage") or {})
    request = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": full_messages,
        **extra_body,
    }
    if response_format is not None:
        request["response_format"] = response_format
    return CallResult(text=text, usage=usage, request=request, response=resp_dict)


def _anthropic_messages_with_cache(messages: list[dict]) -> list[dict]:
    """Copy messages, attaching an ephemeral cache breakpoint to the last one."""
    out = [dict(m) for m in messages]
    if out:
        last = out[-1]
        last["content"] = [
            {
                "type": "text",
                "text": last["content"],
                "cache_control": {"type": "ephemeral"},
            }
        ]
    return out


def call_anthropic(
    client: "anthropic.Anthropic",
    *,
    model: str,
    system: str,
    messages: list[dict],
    max_tokens: int,
    cache: bool = True,
) -> CallResult:
    if cache:
        system_param = [
            {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
        ]
        msg_param = _anthropic_messages_with_cache(messages)
    else:
        system_param = system
        msg_param = [dict(m) for m in messages]

    resp = with_retry(
        lambda: client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_param,
            messages=msg_param,
        )
    )
    resp_dict = resp.model_dump()
    text = "".join(b.text for b in resp.content if b.type == "text")
    usage = usage_from_anthropic(resp_dict.get("usage") or {})
    request = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system_param,
        "messages": msg_param,
    }
    return CallResult(text=text, usage=usage, request=request, response=resp_dict)
