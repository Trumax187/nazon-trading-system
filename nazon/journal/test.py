# compare_test.py - Compare resolver vs manual candle walk
import sys
sys.path.insert(0, r"C:\Users\TRUEMAX KATEMA\Desktop\NAZON")

import sqlite3
from datetime import datetime
from nazon.core.mt5_connector import MT5Connector
from nazon.core.exit_manager import Position, update
from nazon.core.signal_engine import TP_MULTIPLES

# Get one recent trade from the journal
conn = sqlite3.connect(r"C:\Users\TRUEMAX KATEMA\Desktop\NAZON\nazon_journal.db")
conn.row_factory = sqlite3.Row

trade = conn.execute("""
    SELECT * FROM trades 
    WHERE symbol='XAUUSDm' 
    ORDER BY opened_ts DESC 
    LIMIT 1
""").fetchone()

if trade is None:
    print("❌ No trades in journal. Run nazon_results.py first.")
    sys.exit(1)

print("=" * 60)
print("TRADE TO VERIFY")
print("=" * 60)
print(f"Opened:      {trade['opened_ts']}")
print(f"Direction:   {trade['direction']}")
print(f"Entry:       {trade['entry']}")
print(f"Stop:        {trade['stop']}")
print(f"R-multiple:  {trade['r_multiple']}")
print(f"Outcome:     {trade['outcome']}")
print(f"Notes:       {trade['notes']}")

# Now manually walk candles
mt5 = MT5Connector()
if not mt5.connect():
    print("❌ Could not connect to MT5")
    sys.exit(1)

import MetaTrader5 as _mt5
import pandas as pd

symbol = trade['symbol']
after = datetime.fromisoformat(trade['opened_ts'])

rates = _mt5.copy_rates_from_pos(symbol, _mt5.TIMEFRAME_H4, 0, 3000)
df = pd.DataFrame(rates)
df["time"] = pd.to_datetime(df["time"], unit="s")
df = df[df["time"] >= after].reset_index(drop=True)

print(f"\nCandles after signal: {len(df)}")
print(f"First candle: {df.iloc[0]['time']}")
print(f"Last candle:  {df.iloc[-1]['time']}")

# Build position
entry = trade['entry']
stop = trade['stop']
risk = abs(entry - stop)
direction = trade['direction']

if direction == "buy":
    tp1 = entry + risk * TP_MULTIPLES[0]
    tp2 = entry + risk * TP_MULTIPLES[1]
    tp3 = entry + risk * TP_MULTIPLES[2]
else:
    tp1 = entry - risk * TP_MULTIPLES[0]
    tp2 = entry - risk * TP_MULTIPLES[1]
    tp3 = entry - risk * TP_MULTIPLES[2]

print(f"\nRisk: {risk:.4f}")
print(f"TP1:  {tp1:.4f}")
print(f"TP2:  {tp2:.4f}")
print(f"TP3:  {tp3:.4f}")

pos = Position(symbol=symbol, direction=direction, entry=entry, stop=stop,
               tp1=tp1, tp2=tp2, tp3=tp3, lots=1.0)

print("\n" + "=" * 60)
print("CANDLE WALK")
print("=" * 60)

for i, bar in df.iterrows():
    if pos.closed:
        break
    l, h = float(bar["low"]), float(bar["high"])
    extremes = [l, h] if direction == "buy" else [h, l]
    
    for extreme in extremes:
        update(pos, extreme)
        if pos.closed:
            print(f"\n✅ Closed at candle {i}: {bar['time']}")
            print(f"   Low: {l:.4f}  High: {h:.4f}")
            print(f"   Stop now: {pos.stop_now:.4f}")
            print(f"   Remaining: {pos.open_fraction}")
            break
    if i >= 60:
        break

print(f"\nFinal: closed={pos.closed}, remaining={pos.open_fraction}")

mt5.disconnect()
conn.close()