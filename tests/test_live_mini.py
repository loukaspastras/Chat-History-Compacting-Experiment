"""Live mini-integration: 3 interview turns, n=2, across both providers + compaction.

Spends a small amount of real money (tens of API calls, tiny payloads). Validates the
full pipeline end-to-end and inspects the actual log rows to confirm:
  - token fields are parsed and populated for both providers,
  - Strategy C produces compaction rows,
  - Anthropic prompt caching actually engages (cache_read > 0 on later turns),
  - cost is computed and the accuracy plumbing works.
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anthropic  # noqa: E402
import openai  # noqa: E402

from benchmark.logger import TraceLogger  # noqa: E402
from benchmark.runner import run_config  # noqa: E402

DB = os.path.join(os.path.dirname(__file__), "..", "results", "test_mini.sqlite")

# 5 questions about Q1-Q3 (the only interview questions asked in a 3-turn run).
# With n=2 this guarantees compaction fires *during* the exam -> exercises the
# bug fix (quiz question must stay in the request and not be compacted away).
MINI_QUIZ = [
    {"question_id": 1, "prompt": "What town did the candidate grow up in?",
     "options": {"a": "Marisol Bay", "b": "Portland", "c": "Asheville", "d": "None of the above"},
     "correct": "a"},
    {"question_id": 2, "prompt": "What city does the candidate live in now?",
     "options": {"a": "Portland", "b": "Asheville", "c": "Marisol Bay", "d": "None of the above"},
     "correct": "b"},
    {"question_id": 3, "prompt": "What is the candidate's current job title?",
     "options": {"a": "Staff Reliability Engineer", "b": "Software Architect", "c": "Product Manager", "d": "None of the above"},
     "correct": "a"},
    {"question_id": 1, "prompt": "Which region is the candidate's hometown in?",
     "options": {"a": "southern California", "b": "northern Oregon", "c": "western Washington", "d": "None of the above"},
     "correct": "b"},
    {"question_id": 2, "prompt": "What kind of home does the candidate live in?",
     "options": {"a": "a converted downtown loft", "b": "a suburban house", "c": "a lakeside cabin", "d": "None of the above"},
     "correct": "a"},
]


def main():
    if os.path.exists(DB):
        os.remove(DB)
    logger = TraceLogger(DB, cap_usd=2.00)  # generous cap for a tiny smoke test
    oai = openai.OpenAI()
    ant = anthropic.Anthropic()

    configs = [
        dict(provider="openai", model="gpt-4o", strategy_name="B", n=2),
        dict(provider="openai", model="gpt-4o", strategy_name="C", n=2),
        dict(provider="anthropic", model="claude-haiku-4-5", strategy_name="A", n=None),
        dict(provider="anthropic", model="claude-haiku-4-5", strategy_name="C", n=2),
    ]

    summaries = []
    for cfg in configs:
        print(f"\n--- running {cfg['provider']} {cfg['model']} strat={cfg['strategy_name']} n={cfg['n']}")
        s = run_config(
            logger=logger, openai_client=oai, anthropic_client=ant,
            num_turns=3, quiz=MINI_QUIZ, verbose=True, **cfg,
        )
        summaries.append(s)

    logger.close()

    # ---- inspect the log rows ----
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    print("\n==== LOG INSPECTION ====")
    rows = conn.execute(
        "SELECT bench_model, strategy, phase, model, input_tokens, cached_tokens, "
        "cache_write_tokens, output_tokens, cost_usd FROM calls ORDER BY id"
    ).fetchall()
    for r in rows:
        print(f"{r['bench_model']:<18} {r['strategy']} {r['phase']:<11} "
              f"in={r['input_tokens']:<6} cached={r['cached_tokens']:<6} "
              f"cw={r['cache_write_tokens']:<5} out={r['output_tokens']:<4} ${r['cost_usd']:.5f}")

    failures = []

    # every row must have output tokens and nonneg token fields and a cost
    for r in rows:
        if r["output_tokens"] <= 0:
            failures.append(f"row {r['phase']} has no output tokens")
        if r["cost_usd"] <= 0:
            failures.append(f"row {r['phase']} has zero cost")
        for f in ("input_tokens", "cached_tokens", "cache_write_tokens"):
            if r[f] < 0:
                failures.append(f"row {r['phase']} negative {f}")

    # Strategy C runs must have compaction rows on Haiku
    comp = conn.execute(
        "SELECT COUNT(*) FROM calls WHERE phase='compaction' AND model='claude-haiku-4-5'"
    ).fetchone()[0]
    if comp == 0:
        failures.append("expected compaction rows for Strategy C runs, found none")
    else:
        print(f"\ncompaction rows: {comp}")

    # Anthropic Strategy A run must show cache reads on later turns (caching engaged)
    cache_reads = conn.execute(
        "SELECT MAX(cached_tokens) FROM calls WHERE provider='anthropic' AND strategy='A'"
    ).fetchone()[0] or 0
    print(f"max anthropic cache_read (strat A): {cache_reads}")
    if cache_reads <= 0:
        failures.append("Anthropic Strategy A showed NO cache reads -- system block not caching")

    # OpenAI cache hits (informational; OpenAI caching is best-effort, may be 0 on tiny runs)
    oai_cached = conn.execute(
        "SELECT MAX(cached_tokens) FROM calls WHERE provider='openai'"
    ).fetchone()[0] or 0
    print(f"max openai cached_tokens: {oai_cached}")

    conn.close()

    # every config must grade ALL quiz items -- a mid-exam crash (the bug) would
    # leave fewer graded, or run_config would have raised before reaching here.
    for s in summaries:
        if s.get("graded") != len(MINI_QUIZ):
            failures.append(
                f"{s['run_id']} graded {s.get('graded')} of {len(MINI_QUIZ)} -- exam crashed mid-way?"
            )

    print("\n==== SUMMARIES ====")
    for s in summaries:
        print(s)
    print(f"\nTOTAL MINI-TEST COST: ${sum(s['cost_usd'] for s in summaries):.4f}")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("\nALL LIVE MINI-INTEGRATION CHECKS PASSED")


if __name__ == "__main__":
    main()
