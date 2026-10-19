# show_losses.py
import sqlite3

conn = sqlite3.connect('nazon_journal.db')
conn.row_factory = sqlite3.Row

# Check if trades table has data
cursor = conn.execute("SELECT COUNT(*) FROM trades")
count = cursor.fetchone()[0]
print(f"Trades in database: {count}")

if count > 0:
    cursor = conn.execute("SELECT opened_ts, symbol, direction, entry, outcome, r_multiple FROM trades WHERE outcome='loss' ORDER BY opened_ts")
    rows = cursor.fetchall()
    
    print("\n" + "=" * 50)
    print(f"LOSSING TRADES ({len(rows)} found)")
    print("=" * 50)
    
    for r in rows:
        print(f"\nTime: {r['opened_ts']}")
        print(f"  Symbol: {r['symbol']}")
        print(f"  Direction: {r['direction']}")
        print(f"  Entry: {r['entry']}")
        print(f"  Loss: {r['r_multiple']}R")
else:
    print("\nNo trades in database yet.")

conn.close()