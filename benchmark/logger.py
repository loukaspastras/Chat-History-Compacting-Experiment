"""SQLite tracing logger -- one row per API interaction.

Captures everything the benchmark needs for analysis: timestamp, model,
strategy, n, the full token breakdown, the computed cost, and the complete
request/response payloads. Also enforces the hard cumulative-cost cap: call
`check_cap()` before each paid API call and it raises `CostCapExceeded` the
moment running spend crosses the limit.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path

from .pricing import Usage, cost_usd

SCHEMA = """
CREATE TABLE IF NOT EXISTS calls (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    ts                 REAL    NOT NULL,
    run_id             TEXT    NOT NULL,
    bench_model        TEXT    NOT NULL,   -- the config's model (grouping key)
    provider           TEXT    NOT NULL,
    model              TEXT    NOT NULL,   -- model that made THIS call (=bench_model except for compaction)
    strategy           TEXT    NOT NULL,
    n                  INTEGER,
    phase              TEXT    NOT NULL,   -- setup | turn | compaction | quiz
    turn_index         INTEGER,
    input_tokens       INTEGER NOT NULL,
    cached_tokens      INTEGER NOT NULL,
    cache_write_tokens INTEGER NOT NULL,
    output_tokens      INTEGER NOT NULL,
    cost_usd           REAL    NOT NULL,
    request_json       TEXT,
    response_json      TEXT,
    extra_json         TEXT
);
CREATE INDEX IF NOT EXISTS idx_calls_run ON calls(run_id);
"""


class CostCapExceeded(Exception):
    """Raised when cumulative logged cost meets or exceeds the configured cap."""


class TraceLogger:
    def __init__(self, db_path, cap_usd: float | None = None):
        self.db_path = str(db_path)
        self.cap_usd = cap_usd
        self._lock = threading.Lock()
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def log(
        self,
        *,
        run_id: str,
        bench_model: str,
        provider: str,
        model: str,
        strategy: str,
        n: int | None,
        phase: str,
        turn_index: int | None,
        usage: Usage,
        request,
        response,
        extra=None,
    ) -> float:
        """Insert one call row. Returns the computed cost for this call."""
        c = cost_usd(model, usage)
        with self._lock:
            self.conn.execute(
                "INSERT INTO calls (ts,run_id,bench_model,provider,model,strategy,n,phase,turn_index,"
                "input_tokens,cached_tokens,cache_write_tokens,output_tokens,cost_usd,"
                "request_json,response_json,extra_json) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    time.time(), run_id, bench_model, provider, model, strategy, n, phase, turn_index,
                    usage.input_tokens, usage.cached_tokens, usage.cache_write_tokens,
                    usage.output_tokens, c,
                    json.dumps(request, default=str),
                    json.dumps(response, default=str),
                    json.dumps(extra, default=str) if extra is not None else None,
                ),
            )
            self.conn.commit()
        return c

    def total_cost(self) -> float:
        with self._lock:
            (total,) = self.conn.execute(
                "SELECT COALESCE(SUM(cost_usd), 0) FROM calls"
            ).fetchone()
        return total

    def run_cost(self, run_id: str) -> float:
        with self._lock:
            (total,) = self.conn.execute(
                "SELECT COALESCE(SUM(cost_usd), 0) FROM calls WHERE run_id = ?", (run_id,)
            ).fetchone()
        return total

    def completed_configs(self, quiz_total: int) -> set[tuple]:
        """Return {(bench_model, strategy, n)} that have a run with >= quiz_total quiz rows."""
        with self._lock:
            rows = self.conn.execute(
                "SELECT bench_model, strategy, n, "
                "SUM(CASE WHEN phase='quiz' THEN 1 ELSE 0 END) AS qc "
                "FROM calls GROUP BY run_id"
            ).fetchall()
        return {(bm, strat, n) for bm, strat, n, qc in rows if qc >= quiz_total}

    def purge_config(self, bench_model: str, strategy: str, n: int | None) -> int:
        """Delete all rows for a config (used to clear stale/partial runs before re-running)."""
        with self._lock:
            if n is None:
                cur = self.conn.execute(
                    "DELETE FROM calls WHERE bench_model=? AND strategy=? AND n IS NULL",
                    (bench_model, strategy),
                )
            else:
                cur = self.conn.execute(
                    "DELETE FROM calls WHERE bench_model=? AND strategy=? AND n=?",
                    (bench_model, strategy, n),
                )
            self.conn.commit()
            return cur.rowcount

    def check_cap(self) -> None:
        """Raise CostCapExceeded if cumulative spend has crossed the cap."""
        if self.cap_usd is None:
            return
        total = self.total_cost()
        if total >= self.cap_usd:
            raise CostCapExceeded(
                f"Cumulative cost ${total:.4f} >= cap ${self.cap_usd:.2f}"
            )

    def close(self) -> None:
        self.conn.close()
