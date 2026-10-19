#!/usr/bin/env python3
"""Walk-forward validation of signal_engine_v2."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

from nazon.core.mt5_connector import MT5Connector
from nazon.core.signal_engine import build_context
from nazon.core.signal_engine_v2 import generate_signal
from nazon.core.exit_manager import Position, update

WARMUP = 250
MAX_BARS_OPEN = 60
TRAIN_BARS = 1500
TEST_BARS = 400


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


def backtest_window(df, symbol, point):
    trades = []
    i = WARMUP
    spread = 240
    balance = 10000
    
    while i < len(df) - 1:
        window = df.iloc[:i+1].reset_index(drop=True)
        
        try:
            ctx = build_context(window, symbol)
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
    
    return trades


def summarize(trades, label):
    if not trades:
        return {'label': label, 'n': 0}
    n = len(trades)
    wins = [t for t in trades if t['outcome'] == 'win']
    total_r = sum(t['r'] for t in trades)
    return {
        'label': label,
        'n': n,
        'win_rate': len(wins)/n,
        'expectancy': total_r/n,
        'total_r': total_r,
    }


def main():
    connector = MT5Connector()
    if not connector.connect():
        return
    
    symbol = "XAUUSDm"
    point = 0.001
    
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 15000)
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    
    print("=" * 70)
    print("NAZON WALK-FORWARD v2")
    print("=" * 70)
    print(f"Data: {len(df)} bars")
    print(f"From: {df['time'].iloc[0]}")
    print(f"To:   {df['time'].iloc[-1]}")
    print()
    
    windows = []
    start = TRAIN_BARS
    while start + TEST_BARS <= len(df):
        test_slice = df.iloc[start - WARMUP:start + TEST_BARS].reset_index(drop=True)
        trades = backtest_window(test_slice, symbol, point)
        s = summarize(trades, f"Window {len(windows)+1}")
        s['window_start_bar'] = start
        s['window_end_bar'] = start + TEST_BARS
        windows.append(s)
        start += TEST_BARS
    
    traded = [w for w in windows if w.get('n', 0) > 0]
    n_windows = len(traded)
    
    if n_windows == 0:
        print("No windows generated trades.")
        connector.disconnect()
        return
    
    positive = [w for w in traded if w['expectancy'] > 0]
    total_trades = sum(w['n'] for w in traded)
    weighted_exp = sum(w['expectancy'] * w['n'] for w in traded) / total_trades
    
    print("=" * 70)
    print("WALK-FORWARD RESULT")
    print("=" * 70)
    print(f"Windows tested:    {n_windows}")
    print(f"Windows positive:  {len(positive)}")
    print(f"% positive:        {len(positive)/n_windows:.0%}")
    print(f"Total trades:      {total_trades}")
    print(f"Weighted exp:      {weighted_exp:+.3f}R")
    
    if len(positive)/n_windows >= 0.6 and weighted_exp > 0:
        verdict = "ROBUST — positive in majority of windows"
    elif len(positive)/n_windows >= 0.5 and weighted_exp > 0:
        verdict = "MARGINAL — positive in about half the windows"
    elif weighted_exp > 0:
        verdict = "FRAGILE — overall positive but wins in minority"
    else:
        verdict = "NO STABLE EDGE — negative on trade-weighted basis"
    
    print(f"\nVERDICT: {verdict}")
    print()
    
    for w in windows:
        if w.get('n', 0) > 0:
            print(f"  {w['label']}: {w['n']:3d} trades | WR {w['win_rate']:.0%} | Exp {w['expectancy']:+.3f}R")
    
    connector.disconnect()


if __name__ == "__main__":
    main()
