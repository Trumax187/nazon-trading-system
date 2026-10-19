# window_length_audit.py — does the SHORT fixed window live actually uses
# (config.CANDLE_COUNT candles) fire strategies at a different rate than the
# EVER-GROWING window backtester.py / the previous audits used? Both
# analytics.py's rejection_breakdown() (0 spread-blocks, 0 kill-switch-halts,
# 61/61 "no strategy fired") and this whole investigation point at the
# strategy-firing step itself behaving differently live vs. in backtest --
# this isolates whether window length is why.
#
# Run from the NAZON folder:
#   python window_length_audit.py [SYMBOL] [BARS]

import sys
import pandas as pd

from nazon.core.mt5_connector import MT5Connector
from nazon.core.regime import detect_regime
from nazon.core.signal_engine import _strategies
from nazon import config

WARMUP = 210
WINDOW = config.CANDLE_COUNT   # exactly what nazon.get_candles() returns live

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

if rates is None or len(rates) < WARMUP + WINDOW:
    got = 0 if rates is None else len(rates)
    print(f"Not enough history for {symbol} ({got} bars available, need "
          f"{WARMUP + WINDOW}).")
    sys.exit(1)

df = pd.DataFrame(rates)
df["time"] = pd.to_datetime(df["time"], unit="s")

growing_fired = 0
sliding_fired = 0
trending_total = 0
mismatches = []

start = max(WARMUP, WINDOW)
for i in range(start, len(df)):
    growing_window = df.iloc[: i + 1]                     # full history (backtester.py's method)
    sliding_window = df.iloc[i + 1 - WINDOW: i + 1]        # last WINDOW bars only (live's method)

    regime_growing = detect_regime(growing_window)
    if regime_growing["regime"] != "trending":
        continue
    trending_total += 1

    regime_sliding = detect_regime(sliding_window)

    g = bool(_strategies(growing_window, regime_growing))
    s = bool(_strategies(sliding_window, regime_sliding))

    if g:
        growing_fired += 1
    if s:
        sliding_fired += 1
    if g != s or regime_growing["regime"] != regime_sliding["regime"]:
        mismatches.append({
            "time": str(df.iloc[i]["time"]),
            "growing_regime": regime_growing["regime"], "growing_fired": g,
            "sliding_regime": regime_sliding["regime"], "sliding_fired": s,
        })

print("=" * 60)
print(f"WINDOW-LENGTH AUDIT — {symbol}")
print(f"Growing window = full history up to each bar (matches backtester.py)")
print(f"Sliding window = last {WINDOW} bars only (matches live's config.CANDLE_COUNT)")
print("=" * 60)
if trending_total == 0:
    print("No trending bars found in this range.")
else:
    print(f"Trending bars (per growing-window regime calc): {trending_total}")
    print(f"  Fired, growing window: {growing_fired} ({growing_fired/trending_total:.1%})")
    print(f"  Fired, sliding window: {sliding_fired} ({sliding_fired/trending_total:.1%})")
    print(f"\nDisagreements (regime OR fired differs): {len(mismatches)} "
          f"({len(mismatches)/trending_total:.1%} of trending bars)")
    if mismatches:
        print("\nFirst 5 disagreements:")
        for m in mismatches[:5]:
            print(f"  {m}")
