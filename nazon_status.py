# nazon_status.py — one command, full picture of where NAZON actually stands.
# Combines signal activity, rejection reasons, trade performance, and a check
# on whether the post-bugfix rescore has actually been run yet.
#
# Run from the NAZON folder:
#   python nazon_status.py

from datetime import datetime

from nazon.journal import trade_logger as J
from nazon.journal import analytics as A
from nazon import config

conn = J.connect(config.JOURNAL_DB)

print("=" * 62)
print(f"NAZON STATUS  —  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"Journal: {config.JOURNAL_DB}")
print("=" * 62)

# ── 1. Is it scanning? ───────────────────────────────────────────────
total = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
approved = conn.execute("SELECT COUNT(*) FROM signals WHERE approved=1").fetchone()[0]
first = conn.execute("SELECT MIN(ts) FROM signals").fetchone()[0]
last = conn.execute("SELECT MAX(ts) FROM signals").fetchone()[0]

print(f"\n[1] SCANNING")
print(f"  Signals logged:  {total}   (approved: {approved} | rejected: {total - approved})")
if first:
    print(f"  First scan:      {first}")
    print(f"  Latest scan:     {last}")
if total:
    print(f"  Approval rate:   {approved/total:.1%}")

# ── 2. Rejections by regime (the open question) ──────────────────────
print(f"\n[2] REJECTIONS BY REGIME")
rows = conn.execute("""
    SELECT COALESCE(regime,'unknown') AS regime, COUNT(*) AS n
    FROM signals WHERE approved=0 GROUP BY regime ORDER BY n DESC
""").fetchall()
if not rows:
    print("  (none)")
for r in rows:
    print(f"  {r['regime']:>12}: {r['n']}")

print(f"\n[3] REJECTION REASONS")
breakdown = A.rejection_breakdown(conn)
if not breakdown:
    print("  (none)")
for reason, count in breakdown.items():
    print(f"  {count:>5}x  {reason}")

# ── 4. Signals in a TRENDING regime specifically ─────────────────────
# This is the number that decides "small sample" vs "something still wrong":
# the historical audit says strategies fire on ~78% of trending bars.
trend_total = conn.execute(
    "SELECT COUNT(*) FROM signals WHERE regime='trending'").fetchone()[0]
trend_approved = conn.execute(
    "SELECT COUNT(*) FROM signals WHERE regime='trending' AND approved=1").fetchone()[0]
print(f"\n[4] TRENDING-REGIME SCANS  (historical audit baseline: ~78% fire)")
print(f"  Trending signals logged: {trend_total}")
print(f"  ...of which approved:    {trend_approved}", end="")
if trend_total:
    print(f"  ({trend_approved/trend_total:.1%})")
    if trend_total < 30:
        print(f"  NOTE: {trend_total} trending scans is a small sample -- a live rate")
        print(f"        well below 78% here is not yet meaningful on its own.")
else:
    print()

# ── 5. Trade performance ─────────────────────────────────────────────
print(f"\n[5] FORWARD PERFORMANCE")
perf = A.overall(conn)
if perf.n == 0:
    print("  No closed trades in the journal.")
    print("  (If you just ran reset_trades.py, run nazon_results.py to rescore.)")
else:
    print(perf.summary())

# ── 6. Has the post-bugfix rescore actually happened? ────────────────
print(f"\n[6] RESCORE CHECK")
stale = conn.execute(
    "SELECT COUNT(*) FROM trades WHERE notes LIKE '%auto-resolved%'").fetchone()[0]
oldest_trade = conn.execute("SELECT MIN(closed_ts) FROM trades").fetchone()[0]
print(f"  Trades in journal: {perf.n}")
if oldest_trade:
    print(f"  Oldest closed_ts:  {oldest_trade}")
    print(f"  If that timestamp predates the fill-price fix, these trades were")
    print(f"  scored with the OLD buggy logic -- run reset_trades.py, then")
    print(f"  nazon_results.py, before trusting any number above.")

# ── 7. Kill-switch day state ─────────────────────────────────────────
print(f"\n[7] DAY STATE / HALTS")
days = conn.execute("SELECT * FROM days ORDER BY trading_day DESC LIMIT 5").fetchall()
if not days:
    print("  No day rows recorded.")
for d in days:
    halt = d["halted_reason"] or "-"
    print(f"  {d['trading_day']}  bal={d['starting_balance']:.2f}  "
          f"pnl={d['realized_pnl']:+.2f}  losses={d['consecutive_losses']}  halt: {halt}")

conn.close()
print("\n" + "=" * 62)
