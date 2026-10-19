import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent / "nazon_journal.db"
print("DB:", DB, "| exists:", DB.exists())
if not DB.exists():
    raise SystemExit("No journal here - wrong folder (ghost DB risk).")

c = sqlite3.connect(DB)
c.row_factory = sqlite3.Row

sig = c.execute("SELECT COUNT(*) n, SUM(approved) a, MIN(ts) first, MAX(ts) last FROM signals").fetchone()
print(f"\nSignals: {sig['n']} | approved: {sig['a']} | {sig['first']} -> {sig['last']}")

rows = c.execute("SELECT outcome, r_multiple FROM trades WHERE closed_ts IS NOT NULL AND r_multiple IS NOT NULL").fetchall()
open_n = c.execute("SELECT COUNT(*) FROM trades WHERE closed_ts IS NULL").fetchone()[0]
n = len(rows)
print(f"Closed trades: {n} | still open/unscored: {open_n}")

if n:
    wins = [r["r_multiple"] for r in rows if r["outcome"] == "win"]
    loss = [r["r_multiple"] for r in rows if r["outcome"] == "loss"]
    wr = len(wins) / n
    aw = sum(wins) / len(wins) if wins else 0
    al = abs(sum(loss) / len(loss)) if loss else 0
    exp = wr * aw - (len(loss) / n) * al
    print(f"Wins {len(wins)} / Losses {len(loss)} / BE {n - len(wins) - len(loss)}")
    print(f"Win rate {wr:.0%} | avg win {aw:+.2f}R | avg loss -{al:.2f}R")
    print(f"Expectancy {exp:+.3f}R | total {sum(r['r_multiple'] for r in rows):+.1f}R")
    print("Sample:", "OK (>=30)" if n >= 30 else "too small", "| target 60-100")

print("\nLast 5 signals:")
for r in c.execute("SELECT ts, symbol, direction, approved, reject_reason FROM signals ORDER BY id DESC LIMIT 5"):
    print(" ", dict(r))