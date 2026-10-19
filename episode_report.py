import math
import sqlite3
from datetime import datetime
from pathlib import Path

GAP_H = 72  # same symbol + same direction + gap <= this -> same episode

DB = Path(__file__).resolve().parent / "nazon_journal.db"
if not DB.exists():
    raise SystemExit(f"No journal at {DB}")

c = sqlite3.connect(DB)
c.row_factory = sqlite3.Row
rows = c.execute("""
    SELECT id, symbol, direction, opened_ts, outcome, r_multiple
    FROM trades
    WHERE closed_ts IS NOT NULL AND r_multiple IS NOT NULL
    ORDER BY symbol, opened_ts, id
""").fetchall()

episodes, prev = [], None
for r in rows:
    t = datetime.fromisoformat(str(r["opened_ts"]))
    new = (
        prev is None
        or r["symbol"] != prev["symbol"]
        or r["direction"] != prev["direction"]
        or (t - prev["t"]).total_seconds() / 3600 > GAP_H
    )
    if new:
        episodes.append([])
    episodes[-1].append(r)
    prev = {"symbol": r["symbol"], "direction": r["direction"], "t": t}

print(f"Episode rule: same symbol+direction, gap <= {GAP_H} h\n")
print(f"{'#':>2} {'symbol':<8} {'dir':<5} {'first opened':<19} {'n':>3} {'W':>3} {'L':>3} {'R':>7}")
ep_r = []
for i, ep in enumerate(episodes, 1):
    R = sum(x["r_multiple"] for x in ep)
    ep_r.append(R)
    w = sum(1 for x in ep if x["outcome"] == "win")
    l = sum(1 for x in ep if x["outcome"] == "loss")
    print(f"{i:>2} {ep[0]['symbol']:<8} {ep[0]['direction']:<5} "
          f"{str(ep[0]['opened_ts'])[:19]:<19} {len(ep):>3} {w:>3} {l:>3} {R:>+7.2f}")

n = len(ep_r)
pos = sum(1 for x in ep_r if x > 0)
mean = sum(ep_r) / n
print(f"\nEpisodes: {n} | positive: {pos} | mean R/episode: {mean:+.2f}")
if n > 1:
    sd = math.sqrt(sum((x - mean) ** 2 for x in ep_r) / (n - 1))
    se = sd / math.sqrt(n)
    print(f"SD {sd:.2f} | SE {se:.2f} | t = {mean / se:+.2f} (df {n - 1})")
    p_le = sum(math.comb(n, k) for k in range(pos + 1)) / 2 ** n
    print(f"Sign test: P(<= {pos} positive of {n}, p=0.5) = {p_le:.3f} (one-sided)")

first = [ep[0]["r_multiple"] for ep in episodes]
later = [x["r_multiple"] for ep in episodes for x in ep[1:]]
avg = lambda v: sum(v) / len(v) if v else float("nan")
print(f"\nFirst entry in episode: n={len(first)}  avg {avg(first):+.2f}R")
print(f"Later entries:          n={len(later)}  avg {avg(later):+.2f}R")