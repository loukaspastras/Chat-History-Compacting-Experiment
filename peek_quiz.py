"""Diagnostic: dump the MCQ exam selections for one config (read-only)."""
import json
import sqlite3
import sys
from collections import Counter

db = "results/benchmark.sqlite"
model = sys.argv[1] if len(sys.argv) > 1 else "gpt-4o"
strat = sys.argv[2] if len(sys.argv) > 2 else "B"
n = sys.argv[3] if len(sys.argv) > 3 else "10"

c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
q = ("SELECT turn_index, extra_json, response_json FROM calls "
     "WHERE bench_model=? AND strategy=? AND phase='quiz'")
params = [model, strat]
if n.lower() != "none":
    q += " AND n=?"
    params.append(int(n))
q += " ORDER BY id"
rows = c.execute(q, params).fetchall()

print(f"{model} / {strat} / n={n} : {len(rows)} quiz rows")
sel = Counter()
for tn, ex, resp in rows:
    e = json.loads(ex) if ex else {}
    sel[e.get("selected_option")] += 1
    print(f"  qid={str(tn):>3}  selected={e.get('selected_option')}  "
          f"correct={e.get('correct_option')}  ok={e.get('is_correct')}")
print("selection distribution:", dict(sel))

# one sample of the model's actual reasoning
if rows:
    r = json.loads(rows[0][2])
    if "choices" in r:
        txt = r["choices"][0]["message"]["content"]
    else:
        txt = "".join(b.get("text", "") for b in r.get("content", []) if b.get("type") == "text")
    print("\nsample response (qid", rows[0][0], "):", (txt or "")[:400])
