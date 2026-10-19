#!/usr/bin/env python3
"""
NAZON — Experiment Runner
==========================
Tests multiple parameter variants in one run. No file edits between tests.

Each variant re-runs backtest_with_engine() with different parameters,
so you can see all results in a single comparison table.

Usage:
    python run_experiments.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

from nazon.core.mt5_connector import MT5Connector

# Import the backtester and summarize
from nazon.backtest import backtester


def run_variant(df, symbol, point, spread_points, tp_multiples, 
                min_trend_adx, min_daily_adx, use_weekend_close):
    """
    Run one experiment variant with overridden parameters.
    Temporarily monkey-patches config and signal_engine so we don't edit files.
    """
    from nazon import config
    from nazon.core import signal_engine
    from nazon.core import exit_manager

    # Save originals
    orig_tp = signal_engine.TP_MULTIPLES
    orig_trend_adx = getattr(config, "MIN_TREND_ADX", 30)
    orig_daily_adx = getattr(config, "MIN_DAILY_ADX", 30)
    orig_weekend = getattr(exit_manager, "WEEKEND_CLOSE", False)

    # Apply variant
    signal_engine.TP_MULTIPLES = tp_multiples
    config.MIN_TREND_ADX = min_trend_adx
    config.MIN_DAILY_ADX = min_daily_adx
    exit_manager.WEEKEND_CLOSE = use_weekend_close

    try:
        trades = backtester.backtest_with_engine(
            df, symbol, point, spread_points=spread_points
        )
        result = backtester.summarize(trades)
    finally:
        # Restore originals
        signal_engine.TP_MULTIPLES = orig_tp
        config.MIN_TREND_ADX = orig_trend_adx
        config.MIN_DAILY_ADX = orig_daily_adx
        exit_manager.WEEKEND_CLOSE = orig_weekend

    return result


def main():
    connector = MT5Connector()
    if not connector.connect():
        return

    print("=" * 75)
    print("NAZON EXPERIMENT RUNNER")
    print("=" * 75)

    # Fetch data once
    rates = mt5.copy_rates_from_pos("XAUUSDm", mt5.TIMEFRAME_H4, 0, 3000)
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")

    print(f"\nData: {len(df)} H4 bars")
    print(f"From: {df['time'].iloc[0]}")
    print(f"To:   {df['time'].iloc[-1]}\n")

    # Define variants to test
    variants = [
        # (label, tp_multiples, trend_adx, daily_adx, weekend_close)
        ("Baseline (1.5/2.5/4.0, ADX 30/30)", (1.5, 2.5, 4.0), 30, 30, False),
        ("TP wider (1.5/3.0/5.5)",           (1.5, 3.0, 5.5), 30, 30, False),
        ("TP much wider (1.5/4.0/7.0)",      (1.5, 4.0, 7.0), 30, 30, False),
        ("Tighter TP1 (1.0/2.5/5.0)",        (1.0, 2.5, 5.0), 30, 30, False),
        ("Higher ADX (35/35)",               (1.5, 2.5, 4.0), 35, 35, False),
        ("Higher ADX (40/35)",               (1.5, 2.5, 4.0), 40, 35, False),
        ("Lower ADX (25/25)",                (1.5, 2.5, 4.0), 25, 25, False),
        ("TP wider + ADX 35/35",             (1.5, 3.0, 5.5), 35, 35, False),
    ]

    results = []
    for label, tps, trend, daily, weekend in variants:
        print(f"Running: {label}...", end=" ", flush=True)
        r = run_variant(df, "XAUUSDm", 0.001, 260, tps, trend, daily, weekend)
        r["label"] = label
        results.append(r)
        n = r.get("n", 0)
        exp = r.get("expectancy_r", 0)
        print(f"{n} trades, {exp:+.3f}R")

    # Print comparison table
    print("\n" + "=" * 75)
    print("COMPARISON")
    print("=" * 75)
    print(f"{'Variant':<38} {'N':>4} {'WR':>5} {'AvgW':>7} {'AvgL':>7} {'Exp':>8}")
    print("-" * 75)

    for r in results:
        n = r.get("n", 0)
        if n == 0:
            print(f"{r['label']:<38} {'—':>4} {'—':>5} {'—':>7} {'—':>7} {'—':>8}")
            continue
        wr = f"{r['win_rate']:.0%}"
        aw = f"+{r['avg_win_r']:.2f}"
        al = f"-{r['avg_loss_r']:.2f}"
        ex = f"{r['expectancy_r']:+.3f}"
        print(f"{r['label']:<38} {n:>4} {wr:>5} {aw:>7} {al:>7} {ex:>8}")

    print("=" * 75)
    print("\nBest expectancy:")
    best = max(results, key=lambda x: x.get("expectancy_r", -999))
    print(f"  {best['label']}: {best.get('expectancy_r', 0):+.3f}R over {best.get('n', 0)} trades")

    connector.disconnect()


if __name__ == "__main__":
    main()