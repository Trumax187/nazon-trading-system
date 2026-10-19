# funnel_audit.py — the next layer down from strategy_firing_audit.py.
# Of the bars where a strategy fired AND aligned with DI direction, how many
# ALSO survive the Daily trend filter? The gap between "fired+aligned" (758
# historically) and "ever approved" (11) has to come from somewhere after
# where the last audit stopped -- this measures the next gate in line.
#
# Run from the NAZON folder:
#   python funnel_audit.py [SYMBOL] [BARS]

import sys
import pandas as pd

from nazon.core.mt5_connector import MT5Connector
from nazon.core.regime import detect_regime
from nazon.core.signal_engine import _strategies
from nazon.core.htf_filter import daily_trend_from_h4, agrees
from nazon import config

WARMUP = 210

symbol = sys.argv[1] if len(sys.argv) > 1 else "XAUUSDm"
n_bars = int(sys.argv[2]) if len(sys.argv) > 2 else 3000

nazon = MT5Connector()
if not nazon.connect():
    print("Could not connect.")
    sys.exit(1)

import MetaTrader5 as mt5
mt5.symbol_select(symbol, True)
rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, n_bars)
nazon.disconnect()

if rates is None or len(rates) < WARMUP + 50:
    got = 0 if rates is None else len(rates)
    print(f"Not enough history for {symbol} ({got} bars available).")
    sys.exit(1)

df = pd.DataFrame(rates)
df["time"] = pd.to_datetime(df["time"], unit="s")

candidates = 0          # fired + aligned with DI direction
daily_agrees_count = 0  # ...AND agrees with the Daily trend filter too

for i in range(WARMUP, len(df)):
    window = df.iloc[: i + 1]

    regime = detect_regime(window)
    if regime["regime"] == "transition":
        continue

    fired = _strategies(window, regime)
    if not fired:
        continue

    if regime["regime"] == "trending":
        rdir = regime.get("direction")
        want = "buy" if rdir == "up" else "sell" if rdir == "down" else None
        aligned = [(n, d) for n, d in fired if want and d == want]
    else:
        aligned = fired   # ranging: structure_bounce has no DI direction guard

    if not aligned:
        continue

    direction = aligned[0][1]
    candidates += 1

    daily_bias = daily_trend_from_h4(window)
    if agrees(direction, daily_bias):
        daily_agrees_count += 1

print("=" * 60)
print(f"FUNNEL AUDIT — {symbol}  ({len(df)} bars)")
print("=" * 60)
print(f"Strategy fired + aligned with DI:      {candidates}")
if candidates:
    print(f"...AND agrees with Daily trend filter: {daily_agrees_count} "
          f"({daily_agrees_count/candidates:.1%})")
    dropped = candidates - daily_agrees_count
    print(f"\nDropped by the Daily filter alone: {dropped} ({dropped/candidates:.1%})")
else:
    print("No candidates found in this window.")

print("\nNote: this uses the H4-resampled Daily bias (matches backtester.py's")
print("methodology), not real D1 candles the way nazon_demo.py does live --")
print("the filter's own docstring flags the resampled version as LESS")
print("reliable, so your live approval rate could differ from this number")
print("for that reason too, not just because of the filter's strictness.")
