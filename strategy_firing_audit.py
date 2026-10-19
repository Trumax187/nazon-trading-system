# strategy_firing_audit.py — how often does each strategy actually fire
# WITHIN the regime it's allowed to trade in? This is the real answer to
# "is the strategy too strict" -- not 3-4 live candles, but hundreds of
# historical bars.
#
# Run from the NAZON folder:
#   python strategy_firing_audit.py [SYMBOL] [BARS]
# Defaults to XAUUSDm, 3000 H4 bars (~2 years) if not given.

import sys
import pandas as pd

from nazon.core.mt5_connector import MT5Connector
from nazon.core.regime import detect_regime
from nazon.core.signal_engine import _strategies
from nazon import config

WARMUP = 210  # matches backtester.py's EMA200 warm-up requirement

symbol = sys.argv[1] if len(sys.argv) > 1 else "XAUUSDm"
n_bars = int(sys.argv[2]) if len(sys.argv) > 2 else 3000

nazon = MT5Connector()
if not nazon.connect():
    print("Could not connect.")
    sys.exit(1)

# Pull a big history window directly. MT5Connector.get_candles() as used in
# nazon_scan.py/nazon_demo.py caps at config.CANDLE_COUNT (300 bars) -- not
# enough to say anything statistically meaningful about firing rates. This
# piggybacks on the session the connector just opened, same as
# outcome_resolver.py does.
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

counts = {
    "bars": 0,
    "trending": 0, "ranging": 0, "transition": 0,
    "trending_fired_raw": 0,       # trend_rider/momentum fired, BEFORE direction guard
    "trending_fired_aligned": 0,   # ...AND agreed with DI direction (survives the guard)
    "ranging_fired": 0,            # structure_bounce fired (RSI extreme)
}

for i in range(WARMUP, len(df)):
    window = df.iloc[: i + 1]
    counts["bars"] += 1

    regime = detect_regime(window)
    r = regime["regime"]
    counts[r] = counts.get(r, 0) + 1

    if r == "transition":
        continue  # allow=[] by design -- excluded from firing stats entirely

    fired = _strategies(window, regime)
    if not fired:
        continue

    if r == "trending":
        counts["trending_fired_raw"] += 1
        rdir = regime.get("direction")
        want = "buy" if rdir == "up" else "sell" if rdir == "down" else None
        if want and any(d == want for _, d in fired):
            counts["trending_fired_aligned"] += 1
    elif r == "ranging":
        counts["ranging_fired"] += 1

print("=" * 60)
print(f"STRATEGY FIRING AUDIT — {symbol}  ({counts['bars']} bars, "
      f"~{counts['bars']*4/24:.0f} days)")
print("=" * 60)
print(f"Regime split:  trending={counts['trending']} ({counts['trending']/counts['bars']:.0%})  "
      f"ranging={counts['ranging']} ({counts['ranging']/counts['bars']:.0%})  "
      f"transition={counts['transition']} ({counts['transition']/counts['bars']:.0%})")

print("\nWithin TRENDING bars (trend_rider / momentum allowed):")
if counts["trending"] > 0:
    print(f"  Fired (any direction):     {counts['trending_fired_raw']:>5} / {counts['trending']} "
          f"({counts['trending_fired_raw']/counts['trending']:.1%})")
    print(f"  Fired AND aligned with DI: {counts['trending_fired_aligned']:>5} / {counts['trending']} "
          f"({counts['trending_fired_aligned']/counts['trending']:.1%})  <- this is what actually becomes a signal")
else:
    print("  No trending bars in this window.")

print("\nWithin RANGING bars (structure_bounce allowed):")
if counts["ranging"] > 0:
    print(f"  Fired: {counts['ranging_fired']:>5} / {counts['ranging']} "
          f"({counts['ranging_fired']/counts['ranging']:.1%})")
else:
    print("  No ranging bars in this window.")

print("\nTRANSITION bars are excluded from firing stats -- regime.py sets")
print("allow=[] there by design, so silence there is guaranteed, not a")
print("strictness signal.")
