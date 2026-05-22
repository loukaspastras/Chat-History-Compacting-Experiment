"""Live observability dashboard for the running benchmark matrix.

Read-only viewer over results/benchmark.sqlite. Opens the DB in mode=ro with a busy
timeout, on a fresh connection per request, so it can never lock or interfere with the
matrix writer. Serves an auto-refreshing page at / and a JSON feed at /api/status.

Run:
  python dashboard.py            # serves http://localhost:8000
  (or)  uvicorn dashboard:app --port 8000
Config via env: BENCH_DB, BENCH_CAP, BENCH_TURNS, BENCH_PORT.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

DB = os.environ.get("BENCH_DB", "results/benchmark.sqlite")
CAP = float(os.environ.get("BENCH_CAP", "25"))
MAX_TURNS = int(os.environ.get("BENCH_TURNS", "100"))
QUIZ_TOTAL = 12  # number of items in the MCQ exam

MODELS = [("openai", "gpt-4o"), ("anthropic", "claude-haiku-4-5")]
N_VALUES = [10, 40, 100]

app = FastAPI(title="KV-Caching Benchmark Live")


def _expected_configs() -> list[tuple]:
    out = []
    for _provider, model in MODELS:
        out.append((model, "A", None))      # A is n-independent -> one run
        for n in N_VALUES:
            out.append((model, "B", n))
            out.append((model, "C", n))
    return out


def _read_rows():
    if not os.path.exists(DB):
        return []
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=5)
    con.row_factory = sqlite3.Row
    try:
        return con.execute(
            "SELECT bench_model, strategy, n, phase, model, turn_index, "
            "input_tokens, cached_tokens, cache_write_tokens, output_tokens, "
            "cost_usd, ts, extra_json FROM calls"
        ).fetchall()
    finally:
        con.close()


def compute_status() -> dict:
    rows = _read_rows()
    groups: dict[tuple, dict] = {}
    total_cost = 0.0
    last_ts = 0.0
    first_ts = None

    for r in rows:
        key = (r["bench_model"], r["strategy"], r["n"])
        g = groups.setdefault(key, {
            "cost": 0.0, "cached": 0, "input": 0, "cw": 0, "out": 0,
            "calls": 0, "turn": 0, "qc": 0, "qt": 0, "comp": 0, "last_ts": 0.0,
        })
        g["cost"] += r["cost_usd"]
        g["calls"] += 1
        g["last_ts"] = max(g["last_ts"], r["ts"] or 0.0)
        total_cost += r["cost_usd"]
        last_ts = max(last_ts, r["ts"] or 0.0)
        first_ts = r["ts"] if first_ts is None else min(first_ts, r["ts"] or first_ts)

        if r["phase"] == "compaction":
            g["comp"] += 1
            continue
        g["cached"] += r["cached_tokens"]
        g["input"] += r["input_tokens"]
        g["cw"] += r["cache_write_tokens"]
        g["out"] += r["output_tokens"]
        if r["phase"] in ("setup", "turn") and r["turn_index"]:
            g["turn"] = max(g["turn"], r["turn_index"])
        if r["phase"] == "quiz" and r["extra_json"]:
            try:
                e = json.loads(r["extra_json"])
                g["qt"] += 1
                g["qc"] += int(bool(e.get("is_correct")))
            except Exception:
                pass

    configs = []
    finished = 0
    current = None
    for (model, strat, n) in _expected_configs():
        g = groups.get((model, strat, n))
        if g is None:
            configs.append({
                "model": model, "strategy": strat, "n": n, "state": "pending",
                "turn": 0, "max_turns": MAX_TURNS, "calls": 0, "cost_usd": 0.0,
                "cache_hit": None, "quiz_correct": 0, "quiz_total": 0,
                "accuracy": None, "compactions": 0,
            })
            continue
        prompt = g["cached"] + g["input"] + g["cw"]
        cache_hit = (g["cached"] / prompt) if prompt else None
        accuracy = (g["qc"] / g["qt"]) if g["qt"] else None
        if g["qt"] >= QUIZ_TOTAL:
            state = "done"
            finished += 1
        elif g["calls"] > 0:
            state = "running"
        else:
            state = "pending"
        entry = {
            "model": model, "strategy": strat, "n": n, "state": state,
            "turn": g["turn"], "max_turns": MAX_TURNS, "calls": g["calls"],
            "cost_usd": round(g["cost"], 4), "cache_hit": cache_hit,
            "quiz_correct": g["qc"], "quiz_total": g["qt"],
            "accuracy": accuracy, "compactions": g["comp"],
        }
        configs.append(entry)
        if state == "running" and (current is None or g["last_ts"] > current[1]):
            current = (entry, g["last_ts"])

    now = time.time()
    if total_cost == 0:
        overall_state = "WAITING"
    elif now - last_ts < 30:
        overall_state = "RUNNING"
    elif finished >= len(_expected_configs()):
        overall_state = "COMPLETE"
    else:
        overall_state = "IDLE"

    return {
        "overall": {
            "status": overall_state,
            "total_calls": len(rows),
            "cumulative_usd": round(total_cost, 4),
            "cap_usd": CAP,
            "cap_pct": round(100 * total_cost / CAP, 2) if CAP else 0,
            "configs_finished": finished,
            "configs_total": len(_expected_configs()),
            "elapsed_sec": round(last_ts - first_ts) if first_ts else 0,
            "current": current[0] if current else None,
        },
        "configs": configs,
    }


@app.get("/api/status")
def api_status():
    return JSONResponse(compute_status())


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML_PAGE


HTML_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>KV-Caching Benchmark — Live</title>
<style>
  :root { --bg:#0f1419; --panel:#171d26; --line:#273141; --txt:#d7e0ea;
          --dim:#7d8aa0; --accent:#46c1a6; --warn:#e0a64b; --run:#5aa9ff;
          --done:#46c1a6; --pend:#4a5568; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--txt);
         font:14px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }
  .wrap { max-width:1000px; margin:0 auto; padding:28px 22px; }
  h1 { font-size:18px; letter-spacing:.04em; margin:0 0 4px; font-weight:600; }
  .sub { color:var(--dim); font-size:12px; margin-bottom:20px; }
  .pill { display:inline-block; padding:2px 10px; border-radius:999px; font-size:12px;
          font-weight:600; letter-spacing:.05em; }
  .RUNNING { background:rgba(90,169,255,.16); color:var(--run); }
  .COMPLETE { background:rgba(70,193,166,.16); color:var(--done); }
  .IDLE,.WAITING { background:rgba(125,138,160,.16); color:var(--dim); }
  .grid { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin:18px 0; }
  .card { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:14px 16px; }
  .card .k { color:var(--dim); font-size:11px; text-transform:uppercase; letter-spacing:.06em; }
  .card .v { font-size:22px; font-weight:600; margin-top:4px; }
  .bar { height:8px; background:#0b0f15; border:1px solid var(--line); border-radius:6px; overflow:hidden; margin-top:8px; }
  .bar > div { height:100%; background:linear-gradient(90deg,var(--accent),var(--run)); width:0%; transition:width .4s; }
  table { width:100%; border-collapse:collapse; margin-top:8px; }
  th,td { text-align:left; padding:8px 10px; border-bottom:1px solid var(--line); font-variant-numeric:tabular-nums; }
  th { color:var(--dim); font-size:11px; text-transform:uppercase; letter-spacing:.05em; font-weight:600; }
  td.num { text-align:right; }
  .st { font-size:11px; font-weight:600; padding:1px 8px; border-radius:6px; }
  .st.done { background:rgba(70,193,166,.16); color:var(--done); }
  .st.running { background:rgba(90,169,255,.16); color:var(--run); }
  .st.pending { background:rgba(74,85,104,.22); color:var(--pend); }
  .minibar { display:inline-block; width:64px; height:6px; background:#0b0f15; border:1px solid var(--line);
             border-radius:4px; overflow:hidden; vertical-align:middle; margin-left:8px; }
  .minibar > div { height:100%; background:var(--run); }
  .dim { color:var(--dim); }
  .foot { color:var(--dim); font-size:11px; margin-top:16px; }
</style>
</head>
<body>
<div class="wrap">
  <h1>KV-Caching Benchmark <span class="pill" id="status">…</span></h1>
  <div class="sub" id="sub">connecting…</div>

  <div class="grid">
    <div class="card"><div class="k">Cumulative cost</div><div class="v" id="cost">—</div>
      <div class="bar"><div id="costbar"></div></div>
      <div class="dim" id="capnote" style="font-size:11px;margin-top:6px"></div></div>
    <div class="card"><div class="k">Configs finished</div><div class="v" id="cfg">—</div></div>
    <div class="card"><div class="k">Total API calls</div><div class="v" id="calls">—</div></div>
  </div>

  <table>
    <thead><tr>
      <th>Model</th><th>Strat</th><th>n</th><th>State</th><th>Turns</th>
      <th class="num">Cost $</th><th class="num">Cache hit</th><th class="num">Accuracy</th>
    </tr></thead>
    <tbody id="rows"></tbody>
  </table>
  <div class="foot" id="foot"></div>
</div>

<script>
const pct = x => x===null||x===undefined ? '<span class="dim">—</span>' : (x*100).toFixed(1)+'%';
const fmtT = s => { s=Math.max(0,s||0); const m=Math.floor(s/60); return m+'m'+String(s%60).padStart(2,'0')+'s'; };

async function tick() {
  let d;
  try { d = await (await fetch('/api/status',{cache:'no-store'})).json(); }
  catch(e) { document.getElementById('sub').textContent='waiting for data…'; return; }
  const o = d.overall;
  const st = document.getElementById('status');
  st.textContent = o.status; st.className = 'pill ' + o.status;
  let curTxt = o.current ? `now: ${o.current.model} / ${o.current.strategy} / n=${o.current.n??'-'} — turn ${o.current.turn}/${o.current.max_turns}` : '—';
  document.getElementById('sub').textContent = `${curTxt}   ·   elapsed ${fmtT(o.elapsed_sec)}`;
  document.getElementById('cost').textContent = '$'+o.cumulative_usd.toFixed(4);
  document.getElementById('costbar').style.width = Math.min(100,o.cap_pct)+'%';
  document.getElementById('capnote').textContent = o.cap_pct.toFixed(1)+'% of $'+o.cap_usd.toFixed(0)+' cap';
  document.getElementById('cfg').textContent = o.configs_finished+' / '+o.configs_total;
  document.getElementById('calls').textContent = o.total_calls;

  const rows = d.configs.map(c => {
    const tb = Math.round(100*c.turn/c.max_turns);
    const turns = c.state==='pending' ? '<span class="dim">—</span>'
      : `${c.turn}/${c.max_turns}<span class="minibar"><div style="width:${tb}%"></div></span>`;
    const acc = c.accuracy===null ? '<span class="dim">—</span>'
      : `${(c.accuracy*100).toFixed(0)}% <span class="dim">(${c.quiz_correct}/${c.quiz_total})</span>`;
    return `<tr>
      <td>${c.model}</td><td>${c.strategy}</td><td>${c.n??'-'}</td>
      <td><span class="st ${c.state}">${c.state}</span></td>
      <td>${turns}</td>
      <td class="num">${c.cost_usd.toFixed(4)}</td>
      <td class="num">${pct(c.cache_hit)}</td>
      <td class="num">${acc}</td></tr>`;
  }).join('');
  document.getElementById('rows').innerHTML = rows;
  document.getElementById('foot').textContent = 'auto-refreshes every 2s · read-only view of '+'results/benchmark.sqlite';
}
tick(); setInterval(tick, 2000);
</script>
</body>
</html>"""


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("BENCH_PORT", "8000"))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
