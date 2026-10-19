#!/usr/bin/env python3
"""Run Walk-Forward Analysis on Gold."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime
import MetaTrader5 as mt5
import pandas as pd

from nazon.core.mt5_connector import MT5Connector
from nazon.backtest.walk_forward import walk_forward


def main():
    print("=" * 70)
    print("NAZON — WALK-FORWARD ANALYSIS")
    print("=" * 70)
    
    connector = MT5Connector()
    if not connector.connect():
        return
    
    symbol = "XAUUSDm"
    point = 0.001
    
    # Get max history
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 15000)
    if rates is None:
        print(f"Could not fetch candles for {symbol}")
        connector.disconnect()
        return
    
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    
    print(f"\nData: {len(df)} H4 bars")
    print(f"From: {df['time'].iloc[0]}")
    print(f"To:   {df['time'].iloc[-1]}")
    print(f"Approx {len(df) / 6 / 30:.1f} months of history\n")
    
    result = walk_forward(
        df=df,
        symbol=symbol,
        point=point,
        train_bars=1500,
        test_bars=400,
        spread_points=260,
    )
    
    print("=" * 70)
    print("WALK-FORWARD RESULT")
    print("=" * 70)
    print(f"Symbol:            {result['symbol']}")
    print(f"Windows tested:    {result['n_windows']}")
    print(f"Windows positive:  {result.get('windows_positive', 0)}")
    print(f"% positive:        {result.get('pct_positive', 0):.0%}")
    print(f"Total trades:      {result.get('total_trades', 0)}")
    print(f"Weighted exp:      {result.get('weighted_expectancy_r', 0):+.3f}R")
    print(f"\nVERDICT:\n{result['verdict']}")
    
    print("\n" + "-" * 70)
    print("PER-WINDOW DETAIL")
    print("-" * 70)
    for i, w in enumerate(result.get("windows", []), 1):
        if w.get("n", 0) == 0:
            print(f"Window {i:2d}: 0 trades")
        else:
            print(f"Window {i:2d}: {w['n']:3d} trades | WR {w['win_rate']:.0%} | Exp {w['expectancy_r']:+.3f}R")
    
    connector.disconnect()


if __name__ == "__main__":
    main()