import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path

DB = Path(__file__).resolve().parent / "nazon_journal.db"
if not DB.exists():
    raise SystemExit(f"No journal at {DB}")

c = sqlite3.connect(DB)
c.row_factory = sqlite3.Row
rows = c.execute("""
    SELECT id, direction, opened_ts, closed_ts, outcome, r_multiple
    FROM trades
    WHERE closed_ts IS NOT NULL AND r_multiple IS NOT NULL
    ORDER BY opened_ts, id
""").fetchall()


def parse(s):
    return datetime.fromisoformat(str(s)).replace(tzinfo=None)


print(f"{'id':>4} {'dir':<5} {'opened':<19} {'closed':<19} {'held_h':>7} {'out':<5} {'R':>6}")
holds = []
for r in rows:
    o, k = parse(r["opened_ts"]), parse(r["closed_ts"])
    h = (k - o).total_seconds() / 3600
    holds.append(h)
    print(f"{r['id']:>4} {r['direction']:<5} {str(o):<19} {str(k):<19} "
          f"{h:>7.1f} {r['outcome']:<5} {r['r_multiple']:>+6.2f}")

print("\nMost common closed_ts values (a big count = batch-stamped):")
for ts, n in Counter(r["closed_ts"] for r in rows).most_common(5):
    print(f"  {n:>3} trades  closed_ts = {ts}")

print(f"\nNegative hold times: {sum(1 for h in holds if h < 0)}")

events = []
for r in rows:
    events.append((parse(r["opened_ts"]), 1))
    events.append((parse(r["closed_ts"]), -1))
events.sort(key=lambda e: (e[0], e[1]))  # closes before opens at equal times
open_now = peak = 0
for _, d in events:
    open_now += d
    peak = max(peak, open_now)
print(f"Peak simultaneous open trades: {peak}")