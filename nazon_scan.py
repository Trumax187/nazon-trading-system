# nazon_scan.py — run the full NAZON engine on live candles
from datetime import date
from nazon.core.mt5_connector import MT5Connector
from nazon.core.signal_engine import analyse
from nazon.core.kill_switch import DayState
from nazon import config

nazon = MT5Connector()
if not nazon.connect():
    print("Could not connect."); exit()

balance = nazon.get_balance()
day = DayState(trading_day=date.today(), starting_balance=balance)  # fresh day

print("\n" + "=" * 60)
print("NAZON LIVE SCAN")
print("=" * 60)

for symbol in config.PAIRS:
    df = nazon.get_candles(symbol)          # full 300 closed candles
    if df is None or len(df) < 200:
        print(f"{symbol}: not enough candles"); continue
    spread = nazon.get_spread(symbol)
    point = config.SYMBOLS[symbol]["point"]
    d1 = nazon.get_daily_candles(symbol, count=60)   # HTF Daily trend filter --
                                                       # without this, analyse()
                                                       # falls back to resampling
                                                       # H4 into pseudo-daily
                                                       # candles, which its own
                                                       # docstring flags as less
                                                       # reliable than real D1.
    sig = analyse(symbol, df, spread_points=spread, point=point,
                  balance=balance, open_positions=[], day_state=day, d1=d1)
    print("\n" + sig.one_line())
    print(f"   regime: {sig.regime} (ADX {sig.regime_adx}) | spread: {spread}pts")
    if sig.status == "approved":
        print(f"   PLAN: entry {sig.entry} | stop {sig.stop} | "
              f"TP {sig.tp1}/{sig.tp2}/{sig.tp3} | lots {sig.lots} | RR {sig.rr}")

nazon.disconnect()
print("\n" + "=" * 60)