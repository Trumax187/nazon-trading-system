# init_trades_table.py
import sqlite3

conn = sqlite3.connect('nazon_journal.db')
cursor = conn.cursor()

# Create trades table if it doesn't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        signal_id INTEGER,
        symbol TEXT NOT NULL,
        direction TEXT NOT NULL,
        strategies TEXT,
        opened_ts TEXT NOT NULL,
        entry REAL NOT NULL,
        stop REAL NOT NULL,
        lots REAL NOT NULL,
        closed_ts TEXT,
        exit_price REAL,
        pnl REAL,
        r_multiple REAL,
        outcome TEXT,
        notes TEXT
    )
''')

conn.commit()
print("✅ trades table created (if it didn't exist)")

# Check current tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print(f"Tables in database: {tables}")

conn.close()