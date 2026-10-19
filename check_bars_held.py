# check_bars_held.py — is MAX_BARS_OPEN=60 cutting live winners short?
#
# The backtester lets a trade run until it resolves; outcome_resolver.py
# force-closes at MAX_BARS_OPEN bars and books whatever R is on the table.
# If live wins cluster at the cap, the live-vs-backtest gap (+0.86R avg win
# vs +1.66R) is a measurement artifact, not a real difference in edge.
#
# Run from the NAZON folder:
#   python check_bars_held.py

import re

from nazon.journal import trade_logger as J
from nazon.journal.outcome_resolver import MAX_BARS_OPEN
from nazon import config

conn = J.connect(config.JOURNAL_DB)

rows = conn.execute("""
    SELECT outcome, r_multiple, notes
    FROM trades
    WHERE closed_ts IS NOT NULL
    ORDER BY r_multiple DESC
""").fetchall()

print("=" * 62)
print(f"BARS-HELD CHECK   (MAX_BARS_OPEN = {MAX_BARS_OPEN})")
print("=" * 62)

if not rows:
    print("No closed trades in the journal.")
    conn.close()
    raise SystemExit

parsed = []
for r in rows:
    notes = r["notes"] or ""
    m = re.search(r"(\d+)\s+bars", notes)
    bars = int(m.group(1)) if m else None
    parsed.append((r["outcome"], r["r_multiple"], bars))

print(f"\n{'outcome':<12}{'R':>8}   bars_held")
print("-" * 40)
for outcome, r, bars in parsed:
    flag = "  <-- HIT CAP" if bars is not None and bars >= MAX_BARS_OPEN else ""
    bars_str = str(bars) if bars is not None else "?"
    print(f"{outcome:<12}{r:>+8.2f}   {bars_str}{flag}")

# ── The number that decides it ───────────────────────────────────────
wins = [(r, b) for o, r, b in parsed if o == "win" and b is not None]
losses = [(r, b) for o, r, b in parsed if o == "loss" and b is not None]
capped_wins = [(r, b) for r, b in wins if b >= MAX_BARS_OPEN]

print("\n" + "=" * 62)
print("SUMMARY")
print("=" * 62)
if wins:
    avg_bars_win = sum(b for _, b in wins) / len(wins)
    print(f"Wins:   {len(wins):>3}   avg bars held: {avg_bars_win:.1f}")
    print(f"  ...of which hit the {MAX_BARS_OPEN}-bar cap: {len(capped_wins)} "
          f"({len(capped_wins)/len(wins):.0%})")
if losses:
    avg_bars_loss = sum(b for _, b in losses) / len(losses)
    print(f"Losses: {len(losses):>3}   avg bars held: {avg_bars_loss:.1f}")

print()
if wins and len(capped_wins) / len(wins) >= 0.25:
    print("VERDICT: a large share of winners are being FORCE-CLOSED at the cap.")
    print("  Their true R is unknown -- they were still open when the resolver")
    print("  gave up. This alone could explain the live-vs-backtest win gap.")
    print(f"  Next step: raise MAX_BARS_OPEN in outcome_resolver.py and re-run")
    print("  reset_trades.py + nazon_results.py to rescore.")
elif wins:
    print("VERDICT: few or no winners are hitting the cap. MAX_BARS_OPEN is")
    print("  NOT the cause of the live-vs-backtest gap. The difference is")
    print("  either genuine market conditions or variance across a small sample.")

conn.close()
