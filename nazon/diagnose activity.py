# diagnose_activity.py — is NAZON actually scanning, and why aren't signals
# turning into trades? Run this from the same folder as nazon_demo.py:
#   python diagnose_activity.py

from nazon.journal import trade_logger as J
from nazon.journal import analytics as A
from nazon import config

conn = J.connect(config.JOURNAL_DB)

total_signals = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
approved = conn.execute("SELECT COUNT(*) FROM signals WHERE approved=1").fetchone()[0]
rejected = total_signals - approved

print("=" * 60)
print("SIGNAL ACTIVITY (proves whether NAZON is actually scanning)")
print("=" * 60)
print(f"Total signals logged: {total_signals}")
print(f"  Approved:  {approved}")
print(f"  Rejected:  {rejected}")

print("\nMost recent 10 signals (newest first):")
rows = conn.execute(
    "SELECT ts, symbol, direction, regime, approved, reject_reason "
    "FROM signals ORDER BY ts DESC LIMIT 10"
).fetchall()
for r in rows:
    status = "APPROVED" if r["approved"] else f"rejected: {r['reject_reason']}"
    print(f"  {r['ts']}  {r['symbol']}  {r['direction'] or '-'}  "
          f"regime={r['regime']}  -> {status}")

print("\n" + "=" * 60)
print("WHY signals are getting rejected (breakdown across ALL history)")
print("=" * 60)
breakdown = A.rejection_breakdown(conn)
if not breakdown:
    print("No rejections recorded — either everything's being approved, "
          "or reject_reason isn't being written.")
else:
    for reason, count in breakdown.items():
        print(f"  {count:>4}x  {reason}")

conn.close()
