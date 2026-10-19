#!/usr/bin/env python3
"""Analyze loss distribution to check for fill bugs."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import MetaTrader5 as mt5
import pandas as pd

from nazon.core.mt5_connector import MT5Connector
from nazon.backtest.backtester import backtest_with_engine


def main():
    connector = MT5Connector()
    if not connector.connect():
        return

    rates = mt5.copy_rates_from_pos("XAUUSDm", mt5.TIMEFRAME_H4, 0, 3000)
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")

    trades = backtest_with_engine(df, "XAUUSDm", 0.001, spread_points=260)

    if not trades:
        print("No trades produced.")
        connector.disconnect()
        return

    wins = [t for t in trades if t["outcome"] == "win"]
    losses = [t for t in trades if t["outcome"] == "loss"]

    print("=" * 65)
    print(f"TRADE ANALYSIS — {len(trades)} total")
    print("=" * 65)
    print(f"Wins:   {len(wins)}")
    print(f"Losses: {len(losses)}")
    print()

    print("=" * 65)
    print("LOSS DISTRIBUTION (are losses ~-1.0R or worse?)")
    print("=" * 65)

    loss_rs = sorted([t["r_multiple"] for t in losses])
    for r in loss_rs:
        bar = "█" * int(abs(r) * 10)
        print(f"  {r:+.2f}R  {bar}")

    if losses:
        avg_loss = sum(t["r_multiple"] for t in losses) / len(losses)
        print(f"\nAverage loss: {avg_loss:+.3f}R")

        # Bucket losses
        small_losses = [r for r in loss_rs if r > -1.20]
        big_losses = [r for r in loss_rs if r <= -1.20]
        print(f"\nLosses between -1.0R and -1.2R: {len(small_losses)} (fill close to stop)")
        print(f"Losses worse than -1.20R:       {len(big_losses)} (slippage or gap)")

    print()
    print("=" * 65)
    print("WIN DISTRIBUTION")
    print("=" * 65)
    win_rs = sorted([t["r_multiple"] for t in wins], reverse=True)
    for r in win_rs:
        bar = "█" * int(r * 10)
        print(f"  {r:+.2f}R  {bar}")

    if wins:
        avg_win = sum(t["r_multiple"] for t in wins) / len(wins)
        print(f"\nAverage win: {avg_win:+.3f}R")

    print()
    print("=" * 65)
    print("BAR HOLD TIMES")
    print("=" * 65)

    if wins:
        win_bars = [t["bars_held"] for t in wins]
        print(f"Winners held: avg {sum(win_bars)/len(win_bars):.1f} bars")
    if losses:
        loss_bars = [t["bars_held"] for t in losses]
        print(f"Losers held:  avg {sum(loss_bars)/len(loss_bars):.1f} bars")

    connector.disconnect()


if __name__ == "__main__":
    main()