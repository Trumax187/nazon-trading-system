# nazon_gold.py — Gold backtest with train/test split AND spread cost
import MetaTrader5 as mt5
import pandas as pd
from nazon.core.mt5_connector import MT5Connector
from nazon.backtest.backtester import backtest_split
from nazon import config

# Realistic Gold spread in points for your account during ACTIVE hours.
# Start with 25 (typical Exness Standard XAUUSD). Adjust to your real number.
GOLD_SPREAD_POINTS = 25

nazon = MT5Connector()
if not nazon.connect():
    print("Could not connect."); exit()

symbol = "XAUUSDm"
mt5.symbol_select(symbol, True)
rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 3000)
df = pd.DataFrame(rates)
df["time"] = pd.to_datetime(df["time"], unit="s")
df = df[["time","open","high","low","close"]].iloc[:-1].reset_index(drop=True)
point = config.SYMBOLS[symbol]["point"]

print(f"\nLive spread right now: {nazon.get_spread(symbol)} pts "
      f"(using {GOLD_SPREAD_POINTS} pts for the cost model)")

for label, spread in [("GROSS (no cost)", 0), (f"NET ({GOLD_SPREAD_POINTS}pt spread)", GOLD_SPREAD_POINTS)]:
    res = backtest_split(df, symbol, point, train_frac=0.70, spread_points=spread)
    print(f"\n{'='*55}")
    print(f"XAUUSDm — {label}")
    print(f"{'='*55}")
    for sl in ["train", "test"]:
        s = res[sl]
        tag = "IN-SAMPLE" if sl=="train" else "OUT-OF-SAMPLE"
        if s["n"]==0:
            print(f"  [{tag}] no trades")
        else:
            print(f"  [{tag}] Trades: {s['n']} | Win: {s['win_rate']:.0%} | "
                  f"Expectancy: {s['expectancy_r']:+.3f}R | Total: {s['total_r']:+.1f}R")

nazon.disconnect()