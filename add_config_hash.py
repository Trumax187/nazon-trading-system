import sqlite3

conn = sqlite3.connect("nazon_journal.db")
cursor = conn.cursor()

# Check if column exists
cursor.execute("PRAGMA table_info(signals)")
columns = [row[1] for row in cursor.fetchall()]

if "config_hash" in columns:
    print("config_hash column already exists")
else:
    cursor.execute("ALTER TABLE signals ADD COLUMN config_hash TEXT DEFAULT ''")
    conn.commit()
    print("config_hash column added")

conn.close()