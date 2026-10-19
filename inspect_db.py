import sqlite3, os
db = r"C:\Users\TRUEMAX KATEMA\Desktop\NAZON\nazon_journal.db"
con = sqlite3.connect(db)

# list tables
tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
print("TABLES:", tables)

# for each table, show columns + all rows
for t in tables:
    print("\n=== TABLE:", t, "===")
    cols = [c[1] for c in con.execute(f"PRAGMA table_info({t})")]
    print("COLUMNS:", cols)
    for row in con.execute(f"SELECT * FROM {t}"):
        print(dict(zip(cols, row)))

con.close()
