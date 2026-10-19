#!/usr/bin/env python3
"""
NAZON — Backtest Variants
Compare different filter combinations to find the best config.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime
import MetaTrader5 as mt5
import pandas as pd

from nazon.core.mt5_connector import MT5Connector
from nazon.core import indicators as ind
from nazon.core.regime import detect_regime
from nazon.core.htf_filter import daily_adx
from nazon.core.signal_engine import _strategies
from nazon.core.signal_contract import new_signal
from nazon.core.exit_manager import Position, update
from nazon import config


WARMUP = 210


def simulate_trade(df, i, direction, entry_price, stop_distance, tp_multiples):
    """Simple trade simulation with the real exit manager."""
    if direction == "buy":
        stop = entry_price - stop_distance
        tps = [entry_price + stop_distance * m for m in tp_multiples]
    else:
        stop = entry_price + stop_distance
        tps = [entry_price - stop_distance * m for m in tp_multiples]
    
    pos = Position(symbol="XAUUSDm", direction=direction, entry=entry_price,
                   stop=stop, tp1=tps[0], tp2=tps[1], tp3=tps[2], lots=1.0)
    
    risk = stop_distance
    realized_r = 0.0
    prev_fraction = pos.open_fraction
    j = i + 1
    
    while j < len(df) and not pos.closed:
        bar = df.iloc[j]
        prices = [bar["low"], bar["high"]] if direction == "buy" else [bar["high"], bar["low"]]
        for px in prices:
            px = float(px)
            update(pos, px)
            closed_now = prev_fraction - pos.open_fraction
            if closed_now > 1e-9:
                if direction == "buy":
                    r_here = (px - entry_price) / risk
                else:
                    r_here = (entry_price - px) / risk
                realized_r += r_here * closed_now
                prev_fraction = pos.open_fraction
            if pos.closed:
                break
        j += 1
    
    if not pos.closed and pos.open_fraction > 0:
        last_px = float(df.iloc[-1]["close"])
        if direction == "buy":
            r_here = (last_px - entry_price) / risk
        else:
            r_here = (entry_price - last_px) / risk
        realized_r += r_here * pos.open_fraction
    
    return realized_r, j - i


def run_variant(df, name, min_h4_adx, min_daily_adx, use_ema):
    """Run backtest with a specific filter configuration."""
    trades = []
    i = WARMUP
    
    while i < len(df) - 1:
        window = df.iloc[:i+1].reset_index(drop=True)
        regime = detect_regime(window)
        
        # Filter 1: H4 ADX
        if regime["adx"] is None or regime["adx"] < min_h4_adx:
            i += 1
            continue
        
        # Filter 2: Daily ADX
        if min_daily_adx > 0:
            d_adx = daily_adx(window)
            if d_adx is not None and d_adx < min_daily_adx:
                i += 1
                continue
        
        # Strategy check
        fired = _strategies(window, regime)
        if not fired:
            i += 1
            continue
        
        buys = [n for n, d in fired if d == "buy"]
        sells = [n for n, d in fired if d == "sell"]
        
        if len(buys) >= 1 and len(buys) > len(sells):
            direction = "buy"
        elif len(sells) >= 1 and len(sells) > len(buys):
            direction = "sell"
        else:
            i += 1
            continue
        
        # Filter 3: EMA 20/50
        if use_ema:
            ema_state = ind.ema_cross_state(window["close"], 20, 50)
            if ema_state == "neutral":
                i += 1
                continue
            if direction == "buy" and ema_state == "down":
                i += 1
                continue
            if direction == "sell" and ema_state == "up":
                i += 1
                continue
        
        # Enter at next bar open
        entry_bar = df.iloc[i + 1]
        entry_price = float(entry_bar["open"])
        
        # Stop distance from recent range
        recent = window.tail(14)
        stop_distance = float((recent["high"] - recent["low"]).mean()) * 1.5
        if stop_distance <= 0:
            i += 1
            continue
        
        r, bars = simulate_trade(df, i, direction, entry_price, stop_distance, (1.5, 2.5, 4.0))
        trades.append({"r": r, "outcome": "win" if r > 0.05 else "loss" if r < -0.05 else "be", "bars": bars})
        
        i += bars + 1  # continue after this trade
    
    # Summary
    closed = trades
    n = len(closed)
    if n == 0:
        return {"name": name, "n": 0, "win_rate": 0, "expectancy": 0, "total": 0}
    
    wins = [t for t in closed if t["outcome"] == "win"]
    losses = [t for t in closed if t["outcome"] == "loss"]
    win_rate = len(wins) / n
    avg_win = sum(t["r"] for t in wins) / len(wins) if wins else 0
    avg_loss = abs(sum(t["r"] for t in losses) / len(losses)) if losses else 0
    expectancy = sum(t["r"] for t in closed) / n
    total = sum(t["r"] for t in closed)
    
    return {
        "name": name, "n": n, "win_rate": win_rate,
        "avg_win": avg_win, "avg_loss": avg_loss,
        "expectancy": expectancy, "total": total,
    }


def main():
    print("=" * 70)
    print("NAZON BACKTEST VARIANTS — Finding the Best Configuration")
    print("=" * 70)
    
    connector = MT5Connector()
    if not connector.connect():
        return
    
    # Get 499 days of H4 data
    rates = mt5.copy_rates_from_pos("XAUUSDm", mt5.TIMEFRAME_H4, 0, 3000)
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    print(f"\nData: {len(df)} H4 bars from {df['time'].iloc[0]} to {df['time'].iloc[-1]}")
    
    # Run variants
    variants = [
        ("Baseline (H4 ADX 30, no Daily, no EMA)", 30, 0, False),
        ("H4 ADX 35", 35, 0, False),
        ("H4 ADX 35 + Daily ADX 30", 35, 30, False),
        ("H4 ADX 35 + EMA 20/50", 35, 0, True),
        ("H4 ADX 35 + Daily ADX 30 + EMA 20/50", 35, 30, True),
        ("H4 ADX 40 + Daily ADX 30 + EMA 20/50", 40, 30, True),
    ]
    
    results = []
    for name, h4, d1, ema in variants:
        print(f"\nRunning: {name}...")
        result = run_variant(df, name, h4, d1, ema)
        results.append(result)
    
    # Print comparison table
    print("\n" + "=" * 70)
    print("COMPARISON")
    print("=" * 70)
    print(f"{'Variant':<45} {'N':>4} {'WR':>6} {'Exp':>7} {'Total':>7}")
    print("-" * 70)
    for r in results:
        wr = f"{r['win_rate']:.0%}" if r['n'] > 0 else "—"
        exp = f"{r['expectancy']:+.3f}R" if r['n'] > 0 else "—"
        tot = f"{r['total']:+.1f}R" if r['n'] > 0 else "—"
        print(f"{r['name']:<45} {r['n']:>4} {wr:>6} {exp:>7} {tot:>7}")
    
    connector.disconnect()


if __name__ == "__main__":
    main()