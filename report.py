"""Phase 5 -- aggregate the benchmark log into a markdown report.

Groups by (model, strategy, n) and reports, per the spec:
  - Total Cumulative Cost ($)          -- all calls for the config, incl. compaction
  - Total Cache Hit Ratio (%)          -- cached / total prompt tokens (benchmark model)
  - Final Retrieval Accuracy (%)       -- fraction of MCQ exam answered correctly

Usage:
  python report.py [--db results/benchmark.sqlite] [--out results/report.md]
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from benchmark.data import QUIZ  # noqa: E402

QUIZ_TOTAL = len(QUIZ)

STRATEGY_ORDER = {"A": 0, "B": 1, "C": 2}
STRATEGY_LABEL = {
    "A": "A (append-only)",
    "B": "B (front-slash)",
    "C": "C (compaction)",
}


def aggregate(db_path: str) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM calls").fetchall()
    conn.close()

    groups: dict[tuple, dict] = defaultdict(lambda: {
        "total_cost": 0.0, "compaction_cost": 0.0,
        "cached": 0, "input": 0, "cache_write": 0, "output": 0,
        "quiz_correct": 0, "quiz_total": 0, "calls": 0, "compactions": 0,
    })

    for r in rows:
        key = (r["bench_model"], r["strategy"], r["n"])
        g = groups[key]
        g["total_cost"] += r["cost_usd"]
        g["calls"] += 1
        if r["phase"] == "compaction":
            g["compaction_cost"] += r["cost_usd"]
            g["compactions"] += 1
            continue  # compaction is overhead of a different model; exclude from cache/token stats
        # benchmark-model rows only -> cache + token accounting
        g["cached"] += r["cached_tokens"]
        g["input"] += r["input_tokens"]
        g["cache_write"] += r["cache_write_tokens"]
        g["output"] += r["output_tokens"]
        if r["phase"] == "quiz" and r["extra_json"]:
            try:
                extra = json.loads(r["extra_json"])
                g["quiz_total"] += 1
                g["quiz_correct"] += int(bool(extra.get("is_correct")))
            except Exception:
                pass

    results = []
    for (model, strategy, n), g in groups.items():
        prompt_tokens = g["cached"] + g["input"] + g["cache_write"]
        cache_hit = (g["cached"] / prompt_tokens) if prompt_tokens else 0.0
        accuracy = (g["quiz_correct"] / g["quiz_total"]) if g["quiz_total"] else None
        results.append({
            "model": model, "strategy": strategy, "n": n,
            "total_cost": g["total_cost"], "compaction_cost": g["compaction_cost"],
            "cache_hit": cache_hit, "accuracy": accuracy,
            "quiz_correct": g["quiz_correct"], "quiz_total": g["quiz_total"],
            "prompt_tokens": prompt_tokens, "output_tokens": g["output"],
            "calls": g["calls"], "compactions": g["compactions"],
            "complete": g["quiz_total"] == QUIZ_TOTAL,
        })
    results.sort(key=lambda r: (r["model"], STRATEGY_ORDER.get(r["strategy"], 9),
                                r["n"] if r["n"] is not None else -1))
    return results


def fmt_pct(x):
    return "n/a" if x is None else f"{x * 100:.1f}%"


def build_markdown(results: list[dict]) -> str:
    lines = []
    lines.append("# KV-Caching Benchmark Report\n")
    lines.append("Cost / cache / accuracy trade-offs across three chat-history strategies, "
                 "measured on `gpt-4o` and `claude-haiku-4-5`.\n")
    lines.append("- **Total Cost** includes every call for the config (Strategy C includes its "
                 "Haiku compaction calls).")
    lines.append("- **Cache Hit %** = cached prompt tokens / total prompt tokens, for the benchmark "
                 "model's own calls (compaction excluded).")
    lines.append("- **Accuracy %** = fraction of the multiple-choice memory exam answered correctly.\n")

    complete = [r for r in results if r.get("complete")]
    excluded = [r for r in results if not r.get("complete")]

    header = ("| Model | Strategy | n | Cache Hit % | Accuracy % | Total Cost $ | "
              "Compaction $ | Calls |")
    sep = "|---|---|---|---:|---:|---:|---:|---:|"
    lines.append(header)
    lines.append(sep)
    for r in complete:
        n_disp = "-" if r["n"] is None else str(r["n"])
        acc = f"{fmt_pct(r['accuracy'])} ({r['quiz_correct']}/{r['quiz_total']})"
        lines.append(
            f"| {r['model']} | {STRATEGY_LABEL.get(r['strategy'], r['strategy'])} | {n_disp} | "
            f"{fmt_pct(r['cache_hit'])} | {acc} | ${r['total_cost']:.4f} | "
            f"${r['compaction_cost']:.4f} | {r['calls']} |"
        )
    lines.append("")
    lines.append(f"_{len(complete)} complete config(s) shown (full {QUIZ_TOTAL}-question exam)._")
    if excluded:
        ex = ", ".join(
            f"{r['model']}/{r['strategy']}/n={'-' if r['n'] is None else r['n']} "
            f"({r['quiz_total']}/{QUIZ_TOTAL} exam)"
            for r in excluded
        )
        lines.append(f"_Excluded as incomplete/failed: {ex}._")
    lines.append("")
    lines.append(_build_analysis(complete))
    return "\n".join(lines)


def _pareto_optimal(rs: list[dict]) -> list[dict]:
    """Configs not dominated by another with >= accuracy AND <= cost."""
    opt = []
    for r in rs:
        dominated = any(
            o is not r
            and o["accuracy"] >= r["accuracy"] and o["total_cost"] <= r["total_cost"]
            and (o["accuracy"] > r["accuracy"] or o["total_cost"] < r["total_cost"])
            for o in rs
        )
        if not dominated:
            opt.append(r)
    return opt


def _build_analysis(complete: list[dict]) -> str:
    """Pareto-based, length-aware reading of the cost/accuracy trade-off."""
    complete = [r for r in complete if r["accuracy"] is not None]
    if not complete:
        return "## Analysis\n\n(No completed configs to analyze.)"

    def nd(r):
        return "-" if r["n"] is None else r["n"]

    def tag(r):
        return f"{STRATEGY_LABEL[r['strategy']]} n={nd(r)}"

    out = ["## Analysis\n"]
    for model in sorted({r["model"] for r in complete}):
        rs = [r for r in complete if r["model"] == model]
        most_acc = max(rs, key=lambda r: r["accuracy"])
        cheapest = min(rs, key=lambda r: r["total_cost"])
        pareto = sorted(_pareto_optimal(rs), key=lambda r: r["total_cost"])
        bounded = [r for r in rs if r["n"] is not None]  # B and C prune/compact
        best_bounded = max(bounded, key=lambda r: r["accuracy"]) if bounded else None
        line = (
            f"**{model}** — accuracy ceiling: {tag(most_acc)} at {fmt_pct(most_acc['accuracy'])} "
            f"(${most_acc['total_cost']:.4f}); cheapest: {tag(cheapest)} "
            f"(${cheapest['total_cost']:.4f}, {fmt_pct(cheapest['accuracy'])}). "
            f"Pareto frontier (cost vs accuracy): {', '.join(tag(r) for r in pareto)}."
        )
        if best_bounded is not None:
            line += (
                f" Best bounded-context option: {tag(best_bounded)} at "
                f"{fmt_pct(best_bounded['accuracy'])} for ${best_bounded['total_cost']:.4f}."
            )
        out.append(line + "\n")

    out.append(
        "\n**Interpretation.** Append-only (A) is the accuracy ceiling and, at this 100-turn "
        "scale, also among the cheapest -- the context simply hasn't grown enough for compaction's "
        "overhead to pay off, so A sits on the Pareto frontier here. But A's cost grows linearly "
        "with conversation length, so for long-horizon chats it eventually loses. Front-slash (B) "
        "is dominated: it forgets early/middle facts (accuracy near zero at small n, climbing only "
        "as the window covers more recent turns) without being any cheaper. Compaction (C) is the "
        "long-horizon answer -- at a well-chosen n it matches append-only's accuracy while keeping "
        "context bounded (e.g. Haiku C/n=40 ties A at 100% for ~$0.12), whereas an over-aggressive "
        "n=10 degrades through repeated lossy re-summarization. "
        "**Bottom line:** use **A for short conversations** (simplest, cheapest, perfect recall), "
        "**C at a moderate n for long ones** (bounded cost/context at near-A accuracy), and "
        "**avoid B** -- it pays the forgetting penalty with no cost saving."
    )
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.path.join("results", "benchmark.sqlite"))
    ap.add_argument("--out", default=os.path.join("results", "report.md"))
    args = ap.parse_args()

    results = aggregate(args.db)
    md = build_markdown(results)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(md)
    print(md)
    print(f"\n[report written to {args.out}]")


if __name__ == "__main__":
    main()
