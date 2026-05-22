# Chat-History Compacting Experiment

A reproducible benchmark measuring the **cost / cache-hit / accuracy trade-offs** of three
chat-history management strategies under each provider's prompt-caching regime, on
`gpt-4o` (OpenAI) and `claude-haiku-4-5` (Anthropic).

When an LLM agent holds a long conversation, the growing history is re-sent on every turn.
How you manage that history controls three things at once: **how much you pay**, **how well
prompt caching works**, and **how much the model remembers**. This experiment quantifies that
three-way trade-off with a controlled, end-to-end simulation.

## The three strategies

| Strategy | Behaviour | Intent |
|---|---|---|
| **A — Append-only** | Never prune; every turn is appended. | Stable prefix → high cache-hit rate, but context (and cost) grow linearly. |
| **B — Front-slash** | Keep at most `n` messages; drop the oldest when the cap is exceeded. | Bounds context, but the sliding window changes the cache prefix every turn → breaks caching of the conversation tail and forgets early/middle facts. |
| **C — Compaction** | Let history grow to `n` messages, then summarise it with a fast model and replace the raw block with the dense summary. | Bounds context **and** preserves facts, re-establishing a stable cache baseline. |

The static system prompt (a 100-question interviewer brief) is never pruned, so the model can
always continue the interview; only the conversation turns are managed.

## Experiment design

1. **Setup** — a large static system prompt (sized > 4096 tokens so Anthropic's Haiku cache
   engages from turn one) instructs the model to interview a candidate, asking 100 questions
   one at a time.
2. **Interview** — the script plays a fixed fictional persona, answering all 100 questions.
   Each answer carries one unique, quizzable fact. The history strategy processes the
   conversation on every turn.
3. **Exam** — a 12-question multiple-choice memory test probes facts from across the sequence
   (weighted to the beginning/middle — exactly the turns that pruning/compaction puts at risk).
   The model answers in strict JSON; grading is an exact letter match (no LLM judge).

**Caching:** OpenAI uses automatic prefix caching with `prompt_cache_key` + `prompt_cache_retention`;
Anthropic uses explicit `cache_control` breakpoints on the system block and the last message.
Every API call's full token breakdown, computed cost, and complete request/response payload is
logged to SQLite.

## Results

Complete sweep on `claude-haiku-4-5` (100-turn interview, 12-question exam):

| Strategy | n | Cache Hit % | Accuracy | Total Cost |
|---|---:|---:|---:|---:|
| A append-only | – | 98.5% | **100%** | $0.097 |
| B front-slash | 10 | 94.0% | 0% | $0.098 |
| B front-slash | 40 | 86.1% | 0% | $0.158 |
| B front-slash | 100 | 80.7% | 17% | $0.220 |
| C compaction | 10 | 95.6% | 33% | $0.228 |
| **C compaction** | **40** | **98.2%** | **100%** | **$0.123** |
| C compaction | 100 | 98.7% | 83% | $0.105 |

`gpt-4o` confirms the endpoints — A: 100% @ $0.894, B/n=10: 0% @ $0.750 — but its full C/B
sweep is incomplete (the OpenAI account hit its quota mid-run; see *Reproducing*).

### Takeaways

- **A (append-only) is the accuracy ceiling** and, at this 100-turn scale, also among the
  cheapest — context hasn't grown enough for compaction overhead to pay off yet. Its cost grows
  linearly, so it loses on long-horizon conversations.
- **C (compaction) at a moderate `n` is the long-conversation answer**: `n=40` *ties* append-only
  at 100% accuracy while keeping context bounded. Too-aggressive `n=10` degrades to 33% via
  repeated lossy re-summarisation.
- **B (front-slash) is dominated**: it forgets early/middle facts (0–17%) without being cheaper.
  Note the 0% rows are *honest abstention* (the model picks "none of the above" when the fact was
  pruned), not random guessing — so they sit below the ~25% chance baseline.
- **Bottom line:** A for short chats, C at a moderate `n` for long ones, never B.

Full table + analysis: [`results/report.md`](results/report.md).

## Repo layout

```
benchmark/
  pricing.py     # 2026 price table + provider-normalized token→cost
  logger.py      # SQLite tracer (full payloads) + hard cost-cap circuit breaker
  history.py     # the three strategies (A/B/C) — pure logic
  data.py        # static system prompt, 100 Q&A persona, 12-question MCQ exam
  clients.py     # native OpenAI/Anthropic wrappers with prompt caching + retry
  runner.py      # one config end-to-end: setup → 100 turns → exam
run_matrix.py    # full matrix runner (sequential / --parallel N / --resume)
report.py        # Phase 5: aggregate the log into results/report.md
dashboard.py     # live FastAPI observability dashboard (read-only over the DB)
status.py        # quick CLI progress readout
tests/           # unit + payload-mapping tests, and a live mini-integration test
```

## Setup

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt   # *nix
export ANTHROPIC_API_KEY=...    # set OPENAI_API_KEY too
```

## Usage

```bash
# Offline tests (no API calls, no cost)
python tests/test_history.py
python tests/test_payload.py

# Live mini-integration (small spend) — validates the full pipeline
python tests/test_live_mini.py

# Full matrix: 2 models × {A,B,C} × n∈{10,40,100}, A once per model
python run_matrix.py                 # sequential
python run_matrix.py --parallel 4    # 4-worker pool (watch provider rate limits)
python run_matrix.py --resume        # skip completed configs, fill the rest

# Aggregate the results
python report.py                     # writes results/report.md

# Live dashboard while a run is in progress
python dashboard.py                  # http://localhost:8000
```

A **$25 hard cost cap** is enforced by the logger before every call; the matrix aborts cleanly
if cumulative spend crosses it.

## Methodology notes & caveats

- **Cache-hit %** = cached prompt tokens / total prompt tokens, for the benchmark model's own
  calls (Strategy C's summarisation calls run on Haiku and are excluded from cache stats but
  included in cost).
- Accuracy is the model's *retrieval* success, not a deterministic quantity — `temperature` is
  not pinned, and the exam is 12 questions, so small differences are noise.
- Some configs were measured under varying API concurrency, which adds noise to cache-hit %.
- The SQLite log (`results/benchmark.sqlite`) is git-ignored — it's a large, regenerable binary.
  Re-run `run_matrix.py` to reproduce it; `report.md` is the committed summary.

## Reproducing the full matrix

The `gpt-4o` half is partial because the OpenAI account ran out of quota mid-run (its 30k TPM
tier also made high parallelism counterproductive — Anthropic parallelised cleanly). To complete
it: top up OpenAI credits, then `python run_matrix.py --resume && python report.py` — `--resume`
keeps every completed config and fills only the missing `gpt-4o` ones.
