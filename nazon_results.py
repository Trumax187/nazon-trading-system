# nazon_results.py — resolve closed signals and show live forward expectancy
from nazon.core.mt5_connector import MT5Connector
from nazon.journal import trade_logger as J
from nazon.journal import analytics as A
from nazon.journal.outcome_resolver import resolve_open_signals
from nazon import config

nazon = MT5Connector()
if not nazon.connect():
    print("Could not connect."); exit()

conn = J.connect(config.JOURNAL_DB)

# Score any approved signals that have now resolved
scored = resolve_open_signals(conn)
print(f"Resolved {scored} newly-closed signal(s).")

# Show forward expectancy so far
perf = A.overall(conn)
print("\n" + "=" * 55)
print("NAZON FORWARD PERFORMANCE (demo)")
print("=" * 55)
print(perf.summary())

nazon.disconnect()
conn.close()