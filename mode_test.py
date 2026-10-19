# mode_test.py — the test exit_manager.py's own docstring asked for:
# does MODE='breathe' beat MODE='breakeven'?
#
# Runs the SAME historical window through the SAME fixed backtester twice,
# changing only the exit mode. Any difference is the exit policy alone.
#
# Run from the NAZON folder:
#   python mode_test.py [SYMBOL] [BARS] [SPREAD_POINTS]

import sys
import pandas as pd

from nazon.core.mt5_connector import MT5Connector
from nazon.core import exit_manager
from nazon.backtest.backtester import backtest, summarize
from nazon import config

symbol = sys.argv[1] if len(sys.argv) > 1 else "XAUUSDm"
n_bars = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
spread_points = float(sys.argv[3]) if len(sys.argv) > 3 else 20.0

nazon = MT5Connector()
if not nazon.connect():
    print("Could not connect.")
    sys.exit(1)

import MetaTrader5 as mt5
mt5.symbol_select(symbol, True)
rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, n_bars)
nazon.disconnect()

if rates is None or len(rates) < 300:
    got = 0 if rates is None else len(rates)
    print(f"Not enough history ({got} bars).")
    sys.exit(1)

df = pd.DataFrame(rates)
df["time"] = pd.to_datetime(df["time"], unit="s")
point = config.SYMBOLS[symbol]["point"]

print("=" * 62)
print(f"EXIT MODE COMPARISON — {symbol}")
print(f"{len(df)} H4 bars | spread cost: {spread_points} points")
print("=" * 62)

results = {}
for mode in ("breakeven", "breathe"):
    # backtester.py calls exit_manager.update(pos, price) with no mode arg,
    # so update() uses its DEFAULT parameter value -- which Python bound once,
    # at function-definition time, from the module-level MODE. Reassigning
    # exit_manager.MODE therefore does NOT change behaviour (that mistake made
    # both runs identical). We must rebind the function's actual default.
    exit_manager.MODE = mode
    exit_manager.update.__defaults__ = (mode,)
    trades = backtest(df, symbol, point, spread_points=spread_points)
    results[mode] = summarize(trades)

    print(f"\n--- MODE = '{mode}' ---")
    s = results[mode]
    if s.get("n", 0) == 0:
        print("  No trades generated.")
        continue
    print(f"  Trades:        {s['n']}")
    print(f"  Win rate:      {s['win_rate']:.1%}")
    print(f"  Avg win:       +{s['avg_win_r']:.2f}R")
    print(f"  Avg loss:      -{s['avg_loss_r']:.2f}R")
    print(f"  Expectancy:    {s['expectancy_r']:+.3f}R per trade")
    print(f"  Total:         {s['total_r']:+.1f}R")

# ── Verdict ──────────────────────────────────────────────────────────
be = results.get("breakeven", {})
br = results.get("breathe", {})
if be.get("n") and br.get("n"):
    diff = br["expectancy_r"] - be["expectancy_r"]
    print("\n" + "=" * 62)
    print(f"DIFFERENCE: breathe - breakeven = {diff:+.3f}R per trade")
    if br["expectancy_r"] > 0 and be["expectancy_r"] <= 0:
        print("  -> 'breathe' flips expectancy POSITIVE. Strong signal, but")
        print("     verify on out-of-sample data (backtest_split) before trusting.")
    elif diff > 0.05:
        print("  -> 'breathe' is better, but expectancy is still negative.")
        print("     Exits were PART of the problem, not all of it.")
    elif be == br:
        print("  -> IDENTICAL results -- the mode switch did NOT take effect.")
        print("     This is a test harness failure, not a finding. Do not")
        print("     interpret it as 'exits don't matter'.")
    elif abs(diff) <= 0.05:
        print("  -> Essentially no difference. The problem is ENTRY quality,")
        print("     not exit management. Exit tuning won't fix this.")
    else:
        print("  -> 'breakeven' is actually better. The current default stands.")

    print("\nNOTE: both runs use the same in-sample window, so these numbers")
    print("are optimistic by construction. Run backtest_split() on the winner")
    print("before drawing any conclusion about a real edge.")
