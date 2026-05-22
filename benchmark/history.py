"""Chat-history management strategies.

Three strategies, one interface. Each manages only the *conversation turns*
(the user/assistant messages after the system prompt). The system prompt -- which
holds the 100-question block and the interviewer instructions -- lives outside the
strategy and is never pruned, so the model can always continue the interview even
when early turns are dropped or compacted.

  Strategy A -- Pristine / append-only. History grows unbounded. Stable prefix =>
                high cache hit rate, linearly growing context.
  Strategy B -- Naive front-slash. Keeps at most `n` messages; when message n+1
                arrives, the earliest (index 0) is dropped. Bounded context, but the
                sliding window changes the cache prefix every turn => caching breaks.
  Strategy C -- Summarization / compaction. History grows until it hits `n` messages,
                then a fast model condenses it into a dense summary that replaces the
                raw block, re-establishing a stable cache baseline.

`messages()` returns an API-ready list, normalized so it starts with a `user`
message and never has two consecutive same-role messages (required by Anthropic;
harmless for OpenAI).
"""
from __future__ import annotations

from typing import Callable

# The specialized compaction instruction, verbatim from the benchmark spec.
COMPACTION_SYSTEM_PROMPT = (
    "Summarize the core facts, answers, and context established in the following "
    "conversation history into a dense, highly structured bulleted summary. Preserve "
    "all unique identifiers, user opinions, and specific question answers."
)

SUMMARY_PREFIX = "[SUMMARY OF EARLIER CONVERSATION -- treat as established context]\n"


def normalize(messages: list[dict]) -> list[dict]:
    """Make a message list valid for both OpenAI and Anthropic.

    1. Drop leading messages until the first one is a `user` message.
    2. Merge consecutive same-role messages (concatenating their text).
    """
    out: list[dict] = []
    started = False
    for m in messages:
        if not started:
            if m["role"] != "user":
                continue  # drop a leading assistant message (e.g. a sliced window)
            started = True
        if out and out[-1]["role"] == m["role"]:
            out[-1]["content"] = out[-1]["content"] + "\n\n" + m["content"]
        else:
            out.append({"role": m["role"], "content": m["content"]})
    return out


def render_for_summary(messages: list[dict]) -> str:
    """Flatten a message list into plain text for the compaction prompt."""
    lines = []
    for m in messages:
        role = "Interviewer" if m["role"] == "assistant" else "Candidate"
        lines.append(f"{role}: {m['content']}")
    return "\n".join(lines)


class StrategyA:
    """Append-only baseline. `n` is accepted but ignored."""

    name = "A"

    def __init__(self, n: int | None = None, **_):
        self.n = n
        self.history: list[dict] = []

    def append(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})

    def messages(self) -> list[dict]:
        return normalize(self.history)


class StrategyB:
    """Front-slash window: keep at most `n` messages, drop from the front."""

    name = "B"

    def __init__(self, n: int, **_):
        if n is None or n < 1:
            raise ValueError("Strategy B requires n >= 1")
        self.n = n
        self.history: list[dict] = []

    def append(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})
        while len(self.history) > self.n:
            self.history.pop(0)  # drop the earliest message

    def messages(self) -> list[dict]:
        return normalize(self.history)


class StrategyC:
    """Compaction: at `n` messages, summarize-and-replace via a fast model.

    `compactor` is a callable `(text: str) -> summary: str`. It is invoked with the
    prior running summary (if any) plus the raw recent turns, and must return a fresh
    dense summary. The benchmark wires this to a logged Haiku call.
    """

    name = "C"

    def __init__(self, n: int, compactor: Callable[[str], str], **_):
        if n is None or n < 1:
            raise ValueError("Strategy C requires n >= 1")
        if compactor is None:
            raise ValueError("Strategy C requires a compactor callable")
        self.n = n
        self.compactor = compactor
        self.summary: str | None = None
        self.history: list[dict] = []
        self.compaction_count = 0

    def append(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})
        if len(self.history) >= self.n:
            self._compact()

    def _compact(self) -> None:
        parts = []
        if self.summary:
            parts.append("PREVIOUS SUMMARY:\n" + self.summary)
        parts.append("RECENT CONVERSATION:\n" + render_for_summary(self.history))
        self.summary = self.compactor("\n\n".join(parts))
        self.compaction_count += 1
        self.history = []

    def messages(self) -> list[dict]:
        msgs: list[dict] = []
        if self.summary:
            msgs.append({"role": "user", "content": SUMMARY_PREFIX + self.summary})
        msgs.extend(self.history)
        return normalize(msgs)


def make_strategy(name: str, n: int | None = None, compactor=None):
    name = name.upper()
    if name == "A":
        return StrategyA(n=n)
    if name == "B":
        return StrategyB(n=n)
    if name == "C":
        return StrategyC(n=n, compactor=compactor)
    raise ValueError(f"Unknown strategy: {name!r}")
