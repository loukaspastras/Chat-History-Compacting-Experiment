"""Phase 4 -- run the full benchmark matrix (sequential or parallel).

Matrix:
  models      : gpt-4o, claude-haiku-4-5
  strategies  : A (append-only), B (front-slash), C (compaction)
  n           : 10, 40, 100      (Strategy A is n-independent -> run once per model)
  => 2 * (1 + 3 + 3) = 14 configs.

Each config is independent, so they can run concurrently. `--parallel N` runs N
configs at a time via a thread pool (the configs' turns are still sequential within
each config). The work queue is interleaved by provider so the pool tends to mix
OpenAI and Anthropic work rather than hammering one provider's rate limit.

The TraceLogger shares ONE SQLite connection guarded by a lock, so concurrent threads
serialize their writes safely (no multi-process locking). The $25 cap is checked
before every call; under parallelism it can overshoot by up to ~N in-flight calls,
and cache-hit numbers are noisier (concurrent same-prefix requests miss the cache).

Usage:
  python run_matrix.py [--turns 100] [--cap 25] [--parallel 4] [--resume]
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

import anthropic
import openai

from benchmark.data import QUIZ
from benchmark.logger import CostCapExceeded, TraceLogger
from benchmark.runner import run_config

MODELS = [("openai", "gpt-4o"), ("anthropic", "claude-haiku-4-5")]
N_VALUES = [10, 40, 100]


def build_configs() -> list[dict]:
    configs = []
    for provider, model in MODELS:
        configs.append(dict(provider=provider, model=model, strategy_name="A", n=None))
        for n in N_VALUES:
            configs.append(dict(provider=provider, model=model, strategy_name="B", n=n))
            configs.append(dict(provider=provider, model=model, strategy_name="C", n=n))
    return configs


def label_of(cfg: dict) -> str:
    return f"{cfg['provider']}/{cfg['model']}/{cfg['strategy_name']}/n={cfg['n']}"


def resume_filter(logger: TraceLogger, configs: list[dict], resume: bool) -> list[dict]:
    """Drop already-complete configs; purge stale rows for incomplete-but-present ones.

    Done sequentially BEFORE the pool starts so purges never race with running workers.
    """
    if not resume:
        return list(configs)
    completed = logger.completed_configs(len(QUIZ))
    keep = ", ".join(f"{m}/{s}/n={n}" for (m, s, n) in sorted(completed, key=str)) or "(none)"
    print(f"[resume] keeping {len(completed)} complete config(s): {keep}", flush=True)
    to_run = []
    for cfg in configs:
        key = (cfg["model"], cfg["strategy_name"], cfg["n"])
        if key in completed:
            print(f"[resume] SKIP (complete): {label_of(cfg)}", flush=True)
            continue
        purged = logger.purge_config(*key)
        if purged:
            print(f"[resume] purged {purged} stale rows for {label_of(cfg)}", flush=True)
        to_run.append(cfg)
    return to_run


def interleave_by_provider(configs: list[dict]) -> list[dict]:
    """Alternate providers so a worker pool mixes OpenAI/Anthropic load."""
    by_provider: dict[str, list[dict]] = {}
    for c in configs:
        by_provider.setdefault(c["provider"], []).append(c)
    out = []
    for group in itertools.zip_longest(*by_provider.values()):
        out.extend(c for c in group if c is not None)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--turns", type=int, default=100)
    ap.add_argument("--cap", type=float, default=25.0)
    ap.add_argument("--parallel", type=int, default=1, help="configs to run concurrently")
    ap.add_argument("--db", default=os.path.join("results", "benchmark.sqlite"))
    ap.add_argument("--summaries", default=os.path.join("results", "summaries.json"))
    ap.add_argument("--resume", action="store_true",
                    help="Skip configs already complete in the DB; purge+rerun incomplete ones.")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.db), exist_ok=True)
    logger = TraceLogger(args.db, cap_usd=args.cap)
    oai = openai.OpenAI()
    ant = anthropic.Anthropic()

    all_configs = build_configs()
    to_run = interleave_by_provider(resume_filter(logger, all_configs, args.resume))

    print(f"=== MATRIX START: {len(to_run)} configs to run, parallel={args.parallel}, "
          f"{args.turns} turns each, cap=${args.cap:.2f}, db={args.db} ===", flush=True)

    summaries: list[dict] = []
    sum_lock = threading.Lock()
    stop_flag = threading.Event()
    t0 = time.time()

    def record(entry):
        with sum_lock:
            summaries.append(entry)
            with open(args.summaries, "w") as f:
                json.dump(summaries, f, indent=2)

    def worker(cfg):
        if stop_flag.is_set():
            return
        label = label_of(cfg)
        print(f"[start] {label}  (cum=${logger.total_cost():.4f})", flush=True)
        try:
            s = run_config(
                logger=logger, openai_client=oai, anthropic_client=ant,
                num_turns=args.turns, verbose=True, **cfg,
            )
            record(s)
        except CostCapExceeded as e:
            stop_flag.set()
            print(f"\n!!! COST CAP HIT during {label}: {e}\n!!! No new configs will start.", flush=True)
        except Exception as e:  # noqa: BLE001 -- one bad config must not kill the matrix
            print(f"\n!!! CONFIG FAILED [{label}]: {e!r}", flush=True)
            traceback.print_exc()
            record({**cfg, "error": repr(e)})

    if args.parallel > 1:
        with ThreadPoolExecutor(max_workers=args.parallel) as ex:
            list(ex.map(worker, to_run))
    else:
        for cfg in to_run:
            worker(cfg)

    total = logger.total_cost()
    elapsed = time.time() - t0
    ok = len([s for s in summaries if "accuracy" in s])
    status = "MATRIX ABORTED (cost cap)" if stop_flag.is_set() else "MATRIX COMPLETE"
    logger.close()
    print(f"\n=== {status} ===", flush=True)
    print(f"configs completed this run: {ok}/{len(to_run)}", flush=True)
    print(f"total cost (DB): ${total:.4f}   elapsed: {elapsed/60:.1f} min", flush=True)
    print(f"db: {args.db}   summaries: {args.summaries}", flush=True)


if __name__ == "__main__":
    main()
