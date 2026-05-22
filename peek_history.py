"""Confirm full chat-history persistence and surface any config errors (read-only)."""
import json
import os
import sqlite3
from collections import defaultdict

db = "results/benchmark.sqlite"
c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
rows = c.execute(
    "SELECT bench_model, strategy, n, phase, turn_index, request_json, response_json FROM calls"
).fetchall()

have_req = sum(1 for r in rows if r[5])
have_resp = sum(1 for r in rows if r[6])
print(f"rows={len(rows)}  with_request_json={have_req}  with_response_json={have_resp}")

# messages-per-call by strategy: proves the managed history is captured and that
# A grows while B/C stay bounded. (OpenAI includes the system msg in 'messages';
# Anthropic keeps system separate -- so counts differ by provider, that's expected.)
mc = defaultdict(list)
for bm, s, n, ph, ti, rq, rp in rows:
    if ph in ("setup", "turn") and rq:
        try:
            mc[(bm, s, n)].append(len(json.loads(rq)["messages"]))
        except Exception:
            pass
print("\nmessages per call (first -> last, max):")
for k in sorted(mc, key=lambda x: str(x)):
    v = mc[k]
    print(f"  {k[0]:<16} strat {k[1]} n={str(k[2]):<4} : {v[0]} -> {v[-1]}  (max {max(v)}, calls {len(v)})")

# show a real persisted history snippet from a deep Strategy A turn
for bm, s, n, ph, ti, rq, rp in rows:
    if s == "A" and ph == "turn" and ti and ti >= 60 and rq:
        msgs = json.loads(rq)["messages"]
        resp = json.loads(rp) if rp else {}
        print(f"\nSAMPLE persisted turn: {bm} / A / turn {ti} -> {len(msgs)} messages in request_json")
        print("   first msg:", msgs[0]["role"], "|", str(msgs[0]["content"])[:55])
        print("   last  msg:", msgs[-1]["role"], "|", str(msgs[-1]["content"])[:55])
        print("   response_json present:", bool(rp), "(", len(rp or ""), "chars )")
        break

# errors recorded so far?
sf = "results/summaries.json"
if os.path.exists(sf):
    summ = json.load(open(sf))
    errs = [x for x in summ if "error" in x]
    print(f"\nsummaries.json: {len(summ)} configs recorded, {len(errs)} with errors")
    for e in errs:
        print("   ERROR:", e.get("model"), e.get("strategy_name"), "->", e.get("error"))
else:
    print("\n(summaries.json not written yet)")
