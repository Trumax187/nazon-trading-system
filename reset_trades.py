# reset_trades.py — wipe old trade outcomes so nazon_results.py re-scores
# every approved signal fresh, using the FIXED outcome_resolver.py.
#
# Safe to run: this only clears the `trades` table (derived outcomes).
# Your `signals` table (every signal NAZON ever logged) is untouched, so
# nothing is lost — everything just gets re-resolved correctly next time
# you run nazon_results.py.
#
# Run this from the same folder as nazon_demo.py:
#   python reset_trades.py

from nazon.journal import trade_logger as J
from nazon import config

conn = J.connect(config.JOURNAL_DB)

before = conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
conn.execute("DELETE FROM trades")
conn.commit()
after = conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]

print(f"Cleared {before - after} old trade row(s). Trades table now has {after} rows.")
print("Signals table untouched — run nazon_results.py now to re-score everything.")

conn.close()
