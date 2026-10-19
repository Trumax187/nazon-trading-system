import sqlite3
from collections import defaultdict
from pathlib import Path

DB = Path(__file__).resolve().parent / "nazon_journal.db"
if not DB.exists():
    raise SystemExit(f"No journal at {DB}")

c = sqlite3.connect(DB)
c.row_factory = sqlite3.Row

rows = c.execute("""
    SELECT t.id, t.direction, t.opened_ts, t.closed_ts, t.outcome,
           t.r_multiple, t.strategies, s.regime
    FROM trades t
    LEFT JOIN signals s ON s.id = t.signal_id
    WHERE t.closed_ts IS NOT NULL AND t.r_multiple IS NOT NULL
    ORDER BY t.opened_ts, t.id
""").fetchall()


def line(label, grp):
    n = len(grp)
    wins = sum(1 for r in grp if r["outcome"] == "win")
    tot = sum(r["r_multiple"] for r in grp)
    print(f"  {label:<24} n={n:<3} win={wins / n:>4.0%}  "
          f"avg={tot / n:+.2f}R  total={tot:+.1f}R")


def section(title, keyfn):
    print(f"\n{title}")
    groups = defaultdict(list)
    for r in rows:
        groups[keyfn(r)].append(r)
    for k in sorted(groups, key=str):
        line(str(k), groups[k])


print(f"Closed trades: {len(rows)}")
section("By month opened", lambda r: (r["opened_ts"] or "")[:7])
section("By direction", lambda r: r["direction"])
section("By regime", lambda r: r["regime"] or "unknown")
section("By strategy", lambda r: r["strategies"] or "unknown")

print("\nChronological split")
line("first 31", rows[:31])
if len(rows) > 31:
    line("after 31", rows[31:])

longest = cur = 0
for r in rows:
    cur = cur + 1 if r["outcome"] == "loss" else 0
    longest = max(longest, cur)
print(f"\nLongest loss streak: {longest} | current streak: {cur}")

# Assumes opened_ts and closed_ts use the same timestamp format
events = []
for r in rows:
    events.append((r["opened_ts"], 1))
    events.append((r["closed_ts"], -1))
events.sort()
open_now = peak = 0
for _, d in events:
    open_now += d
    peak = max(peak, open_now)
print(f"Peak simultaneous open trades: {peak}")

pending = c.execute("""
    SELECT ts, symbol, direction FROM signals s
    WHERE approved = 1
      AND NOT EXISTS (SELECT 1 FROM trades t WHERE t.signal_id = s.id)
    ORDER BY ts
""").fetchall()
print(f"\nApproved signals with no trade row: {len(pending)}")
for p in pending:
    print(" ", p["ts"], p["symbol"], p["direction"])