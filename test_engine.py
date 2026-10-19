#!/usr/bin/env python3
"""Sanity check: does the LIVE engine produce trades on recent data?"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import MetaTrader5 as mt5
import pandas as pd

from nazon.core.mt5_connector import MT5Connector
from nazon.backtest.backtester import backtest_with_engine, summarize


def main():
    connector = MT5Connector()
    if not connector.connect():
        return

    rates = mt5.copy_rates_from_pos("XAUUSDm", mt5.TIMEFRAME_H4, 0, 3000)
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")

    print(f"Testing {len(df)} bars")
    print(f"From: {df['time'].iloc[0]}")
    print(f"To:   {df['time'].iloc[-1]}")
    print()

    trades = backtest_with_engine(df, "XAUUSDm", 0.001, spread_points=260)
    result = summarize(trades)

    print("=" * 55)
    print("LIVE ENGINE RESULTS (parity check)")
    print("=" * 55)
    print(f"Trades:     {result.get('n', 0)}")
    print(f"Win rate:   {result.get('win_rate', 0):.0%}")
    print(f"Avg win:    +{result.get('avg_win_r', 0):.2f}R")
    print(f"Avg loss:   -{result.get('avg_loss_r', 0):.2f}R")
    print(f"Expectancy: {result.get('expectancy_r', 0):+.3f}R")
    print(f"Total:      {result.get('total_r', 0):+.1f}R")

    # If trades exist, show the first few
    if trades:
        print("\n" + "-" * 55)
        print("SAMPLE TRADES")
        print("-" * 55)
        for t in trades[:5]:
            print(f"{t['symbol']} {t['direction']:4s} | regime {t.get('regime', '?'):10s} | "
                  f"R {t['r_multiple']:+.2f} | {t['bars_held']} bars")

    connector.disconnect()


if __name__ == "__main__":
    main()