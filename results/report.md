# KV-Caching Benchmark Report

Cost / cache / accuracy trade-offs across three chat-history strategies, measured on `gpt-4o` and `claude-haiku-4-5`.

- **Total Cost** includes every call for the config (Strategy C includes its Haiku compaction calls).
- **Cache Hit %** = cached prompt tokens / total prompt tokens, for the benchmark model's own calls (compaction excluded).
- **Accuracy %** = fraction of the multiple-choice memory exam answered correctly.

| Model | Strategy | n | Cache Hit % | Accuracy % | Total Cost $ | Compaction $ | Calls |
|---|---|---|---:|---:|---:|---:|---:|
| claude-haiku-4-5 | A (append-only) | - | 98.5% | 100.0% (12/12) | $0.0973 | $0.0000 | 112 |
| claude-haiku-4-5 | B (front-slash) | 10 | 94.0% | 0.0% (0/12) | $0.0978 | $0.0000 | 112 |
| claude-haiku-4-5 | B (front-slash) | 40 | 86.1% | 0.0% (0/12) | $0.1581 | $0.0000 | 112 |
| claude-haiku-4-5 | B (front-slash) | 100 | 80.7% | 16.7% (2/12) | $0.2201 | $0.0000 | 112 |
| claude-haiku-4-5 | C (compaction) | 10 | 95.6% | 33.3% (4/12) | $0.2277 | $0.1249 | 134 |
| claude-haiku-4-5 | C (compaction) | 40 | 98.2% | 100.0% (12/12) | $0.1232 | $0.0348 | 117 |
| claude-haiku-4-5 | C (compaction) | 100 | 98.7% | 83.3% (10/12) | $0.1046 | $0.0172 | 114 |
| gpt-4o | A (append-only) | - | 96.9% | 100.0% (12/12) | $0.8941 | $0.0000 | 112 |
| gpt-4o | B (front-slash) | 10 | 73.9% | 0.0% (0/12) | $0.7503 | $0.0000 | 112 |

_9 complete config(s) shown (full 12-question exam)._
_Excluded as incomplete/failed: gpt-4o/C/n=10 (0/12 exam)._

## Analysis

**claude-haiku-4-5** — accuracy ceiling: A (append-only) n=- at 100.0% ($0.0973); cheapest: A (append-only) n=- ($0.0973, 100.0%). Pareto frontier (cost vs accuracy): A (append-only) n=-. Best bounded-context option: C (compaction) n=40 at 100.0% for $0.1232.

**gpt-4o** — accuracy ceiling: A (append-only) n=- at 100.0% ($0.8941); cheapest: B (front-slash) n=10 ($0.7503, 0.0%). Pareto frontier (cost vs accuracy): B (front-slash) n=10, A (append-only) n=-. Best bounded-context option: B (front-slash) n=10 at 0.0% for $0.7503.


**Interpretation.** Append-only (A) is the accuracy ceiling and, at this 100-turn scale, also among the cheapest -- the context simply hasn't grown enough for compaction's overhead to pay off, so A sits on the Pareto frontier here. But A's cost grows linearly with conversation length, so for long-horizon chats it eventually loses. Front-slash (B) is dominated: it forgets early/middle facts (accuracy near zero at small n, climbing only as the window covers more recent turns) without being any cheaper. Compaction (C) is the long-horizon answer -- at a well-chosen n it matches append-only's accuracy while keeping context bounded (e.g. Haiku C/n=40 ties A at 100% for ~$0.12), whereas an over-aggressive n=10 degrades through repeated lossy re-summarization. **Bottom line:** use **A for short conversations** (simplest, cheapest, perfect recall), **C at a moderate n for long ones** (bounded cost/context at near-A accuracy), and **avoid B** -- it pays the forgetting penalty with no cost saving.