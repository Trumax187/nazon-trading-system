# backtest_demo_period.py
import sys
sys.path.insert(0, r"C:\Users\TRUEMAX KATEMA\Desktop\NAZON")

from datetime import datetime
from nazon.core.mt5_connector import MT5Connector
from nazon.backtest.backtester import backtest, summarize
import MetaTrader5 as mt5
import pandas as pd

connector = MT5Connector()
connector.connect()

# Get candles from June 2026 to now
import MetaTrader5 as _mt5
rates = _mt5.copy_rates_range(
    "XAUUSDm",
    _mt5.TIMEFRAME_H4,
    datetime(2026, 6, 1),
    datetime.now()
)
df = pd.DataFrame(rates)
df["time"] = pd.to_datetime(df["time"], unit="s")

print(f"Backtesting {len(df)} candles from {df['time'].iloc[0]} to {df['time'].iloc[-1]}")
print(f"Comparing to demo period (June 11 - Oct 8)")

trades = backtest(df, "XAUUSDm", 0.001)
result = summarize(trades)

print("\n" + "=" * 55)
print("BACKTEST — SAME PERIOD AS DEMO")
print("=" * 55)
print(f"Trades:     {result['n']}")
print(f"Win rate:   {result['win_rate']:.0%}")
print(f"Avg win:    +{result['avg_win_r']:.2f}R")
print(f"Avg loss:   -{result['avg_loss_r']:.2f}R")
print(f"Expectancy: {result['expectancy_r']:+.3f}R")
print(f"Total:      {result['total_r']:+.1f}R")

connector.disconnect()