"""Quick live-progress readout for the running benchmark matrix."""
import sqlite3
import sys

db = sys.argv[1] if len(sys.argv) > 1 else "results/benchmark.sqlite"
c = sqlite3.connect(db)
n, tot = c.execute("SELECT COUNT(*), COALESCE(SUM(cost_usd), 0) FROM calls").fetchone()
done = c.execute("SELECT COUNT(DISTINCT run_id) FROM calls WHERE phase = 'quiz'").fetchone()[0]
cur = c.execute(
    "SELECT bench_model, strategy, n, COUNT(*), MAX(turn_index) "
    "FROM calls GROUP BY run_id ORDER BY MAX(id) DESC LIMIT 1"
).fetchone()
print("total_calls      ", n)
print("cumulative_usd   ", round(tot, 4))
print("configs_finished ", done, "of 14")
if cur:
    print("current_config   ", cur[0], "strat", cur[1], "n", cur[2],
          "| calls", cur[3], "| last_turn", cur[4])
c.close()
