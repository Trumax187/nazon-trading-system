#!/usr/bin/env python3
"""Backtest Signal Engine v2 on historical Gold data."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import MetaTrader5 as mt5
import pandas as pd

from nazon.core.mt5_connector import MT5Connector
from nazon.core.signal_engine import build_context
from nazon.core.signal_engine_v2 import generate_signal
from nazon.core.exit_manager import Position, update


WARMUP = 250
MAX_BARS_OPEN = 60


def simulate_trade(df, entry_idx, direction, entry, stop, tp1, tp2, tp3):
    risk = abs(entry - stop)
    if risk <= 0:
        return 0.0, 1
    
    pos = Position(symbol="XAUUSDm", direction=direction, entry=entry,
                   stop=stop, tp1=tp1, tp2=tp2, tp3=tp3, lots=1.0)
    
    realized_r = 0.0
    prev_fraction = pos.open_fraction
    j = entry_idx + 1
    bars = 0
    
    while j < len(df) and not pos.closed and bars < MAX_BARS_OPEN:
        bar = df.iloc[j]
        prices = [bar["low"], bar["high"]] if direction == "buy" else [bar["high"], bar["low"]]
        for px in prices:
            px = float(px)
            update(pos, px)
            closed_now = prev_fraction - pos.open_fraction
            if closed_now > 1e-9:
                if direction == "buy":
                    r_here = (px - entry) / risk
                else:
                    r_here = (entry - px) / risk
                realized_r += r_here * closed_now
                prev_fraction = pos.open_fraction
            if pos.closed:
                break
        j += 1
        bars += 1
    
    if not pos.closed and pos.open_fraction > 0:
        last_px = float(df.iloc[min(j, len(df)-1)]["close"])
        if direction == "buy":
            r_here = (last_px - entry) / risk
        else:
            r_here = (entry - last_px) / risk
        realized_r += r_here * pos.open_fraction
    
    return realized_r, bars


def main():
    connector = MT5Connector()
    if not connector.connect():
        return

    rates = mt5.copy_rates_from_pos("XAUUSDm", mt5.TIMEFRAME_H4, 0, 3000)
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    
    print("=" * 60)
    print("NAZON SIGNAL V2 BACKTEST")
    print("=" * 60)
    print(f"Data: {len(df)} bars")
    print(f"From: {df['time'].iloc[0]}")
    print(f"To:   {df['time'].iloc[-1]}")
    print()
    
    spread = 240
    balance = 10000
    
    trades = []
    i = WARMUP
    
    while i < len(df) - 1:
        window = df.iloc[:i+1].reset_index(drop=True)
        
        try:
            ctx = build_context(window, "XAUUSDm")
            signal = generate_signal(ctx, spread_points=spread, balance=balance, risk_pct=0.01)
        except Exception:
            i += 1
            continue
        
        if signal['direction'] == 'wait':
            i += 1
            continue
        
        entry_idx = i + 1
        entry = float(df.iloc[entry_idx]["open"])
        
        risk = abs(signal['entry'] - signal['stop'])
        if risk <= 0:
            i += 1
            continue
        
        if signal['direction'] == 'buy':
            stop = entry - risk
            tp1 = entry + risk * 1.5
            tp2 = entry + risk * 2.5
            tp3 = entry + risk * 4.0
        else:
            stop = entry + risk
            tp1 = entry - risk * 1.5
            tp2 = entry - risk * 2.5
            tp3 = entry - risk * 4.0
        
        r, bars = simulate_trade(df, entry_idx, signal['direction'], entry, stop, tp1, tp2, tp3)
        
        trades.append({
            'confidence': signal['confidence'],
            'direction': signal['direction'],
            'r': r,
            'outcome': 'win' if r > 0.05 else 'loss' if r < -0.05 else 'be',
            'bars': bars,
        })
        
        i = entry_idx + bars + 1
    
    connector.disconnect()
    
    if not trades:
        print("No trades generated.")
        return
    
    n = len(trades)
    wins = [t for t in trades if t['outcome'] == 'win']
    losses = [t for t in trades if t['outcome'] == 'loss']
    total_r = sum(t['r'] for t in trades)
    expectancy = total_r / n
    
    print("=" * 60)
    print("OVERALL RESULTS")
    print("=" * 60)
    print(f"Trades:      {n}")
    print(f"Win rate:    {len(wins)/n:.0%}")
    print(f"Total R:     {total_r:+.1f}R")
    print(f"Expectancy:  {expectancy:+.3f}R per trade")
    print()
    
    buckets = [
        (50, 60, "50-60"),
        (60, 70, "60-70"),
        (70, 80, "70-80"),
        (80, 101, "80+"),
    ]
    
    print("=" * 60)
    print("BY CONFIDENCE BUCKET")
    print("=" * 60)
    print(f"{'Bucket':<10} {'N':>4} {'WR':>6} {'Avg R':>8} {'Total':>8}")
    print("-" * 60)
    
    for low, high, label in buckets:
        bucket_trades = [t for t in trades if low <= t['confidence'] < high]
        if not bucket_trades:
            print(f"{label:<10} {0:>4}")
            continue
        bn = len(bucket_trades)
        bw = len([t for t in bucket_trades if t['outcome'] == 'win'])
        avg_r = sum(t['r'] for t in bucket_trades) / bn
        tot = sum(t['r'] for t in bucket_trades)
        print(f"{label:<10} {bn:>4} {bw/bn:>6.0%} {avg_r:>+8.3f} {tot:>+8.1f}")
    
    print()
    print("=" * 60)
    print("SAMPLE TRADES (first 10)")
    print("=" * 60)
    for t in trades[:10]:
        print(f"  {t['direction']:4s} | conf {t['confidence']:3d} | R {t['r']:+.2f} | {t['outcome']}")


if __name__ == "__main__":
    main()
