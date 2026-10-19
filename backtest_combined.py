#!/usr/bin/env python3
"""
NAZON — Combined Backtest (Trend + Range)
==========================================
Tests the multi-strategy approach:
  - ADX > 30 → trend-following (trend_rider / momentum)
  - ADX < 20 → range mean-reversion (structure_bounce_v2)
  - In between → no trade

Compares this against the individual strategies.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime
import MetaTrader5 as mt5
import pandas as pd

from nazon.core.mt5_connector import MT5Connector
from nazon.core.regime import detect_regime
from nazon.core.signal_engine import _strategies, TP_MULTIPLES
from nazon.core.structure_bounce_v2 import structure_bounce_v2_signals
from nazon.core.exit_manager import Position, update
import nazon.core.indicators as ind


WARMUP = 210


def simulate(df, i, direction, entry, stop, tp1, tp2, tp3):
    """Walk forward and return realized R."""
    risk = abs(entry - stop)
    if risk <= 0:
        return 0.0, i+1
    
    pos = Position(symbol="XAUUSDm", direction=direction, entry=entry,
                   stop=stop, tp1=tp1, tp2=tp2, tp3=tp3, lots=1.0)
    
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
                    r_here = (px - entry) / risk
                else:
                    r_here = (entry - px) / risk
                realized_r += r_here * closed_now
                prev_fraction = pos.open_fraction
            if pos.closed:
                break
        j += 1
    
    if not pos.closed and pos.open_fraction > 0:
        last_px = float(df.iloc[-1]["close"])
        if direction == "buy":
            r_here = (last_px - entry) / risk
        else:
            r_here = (entry - last_px) / risk
        realized_r += r_here * pos.open_fraction
    
    return realized_r, j - i


def backtest_combined(df, symbol):
    """Multi-strategy: trend in trends, range in ranges."""
    trades = []
    i = WARMUP
    
    while i < len(df) - 1:
        window = df.iloc[:i+1].reset_index(drop=True)
        regime = detect_regime(window)
        adx = regime["adx"]
        
        if adx is None:
            i += 1
            continue
        
        strategy_used = None
        direction = None
        
        # ── TREND REGIME ──────────────────────────────────────────
        if regime["regime"] == "trending":
            fired = _strategies(window, regime)
            if fired:
                buys = [n for n, d in fired if d == "buy"]
                sells = [n for n, d in fired if d == "sell"]
                if len(buys) >= 1 and len(buys) > len(sells):
                    direction = "buy"
                    strategy_used = "trend"
                elif len(sells) >= 1 and len(sells) > len(buys):
                    direction = "sell"
                    strategy_used = "trend"
        
        # ── RANGE REGIME ──────────────────────────────────────────
        elif regime["regime"] == "ranging":
            fired = structure_bounce_v2_signals(window, adx)
            if fired:
                direction = fired[0][1]
                strategy_used = "range"
        
        # ── TRANSITION: skip ──────────────────────────────────────
        else:
            i += 1
            continue
        
        if direction is None:
            i += 1
            continue
        
        # Enter at next bar open
        entry = float(df.iloc[i+1]["open"])
        
        # ATR-based geometry
        recent = window.tail(14)
        atr_approx = float((recent["high"] - recent["low"]).mean())
        
        if strategy_used == "trend":
            stop_dist = atr_approx * 1.5
            tps = [entry + stop_dist * m if direction == "buy" else entry - stop_dist * m
                   for m in TP_MULTIPLES]
            stop = entry - stop_dist if direction == "buy" else entry + stop_dist
        else:  # range
            stop_dist = atr_approx * 3.5
            tp_dist = atr_approx * 1.0
            if direction == "buy":
                stop = entry - stop_dist
                tps = [entry + tp_dist] * 3
            else:
                stop = entry + stop_dist
                tps = [entry - tp_dist] * 3
        
        r, bars = simulate(df, i, direction, entry, stop, tps[0], tps[1], tps[2])
        trades.append({
            "r": r,
            "strategy": strategy_used,
            "outcome": "win" if r > 0.05 else "loss" if r < -0.05 else "be",
            "bars": bars,
        })
        
        i += bars + 1
    
    return trades


def summarize(trades, label=""):
    if not trades:
        return {"label": label, "n": 0}
    n = len(trades)
    wins = [t for t in trades if t["outcome"] == "win"]
    losses = [t for t in trades if t["outcome"] == "loss"]
    return {
        "label": label,
        "n": n,
        "win_rate": len(wins) / n,
        "avg_win": sum(t["r"] for t in wins) / len(wins) if wins else 0,
        "avg_loss": abs(sum(t["r"] for t in losses) / len(losses)) if losses else 0,
        "expectancy": sum(t["r"] for t in trades) / n,
        "total": sum(t["r"] for t in trades),
    }


def main():
    connector = MT5Connector()
    if not connector.connect():
        return
    
    print("=" * 70)
    print("NAZON — COMBINED BACKTEST (Trend + Range)")
    print("=" * 70)
    
    symbol = "XAUUSDm"
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 3000)
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    
    print(f"\nData: {len(df)} H4 bars from {df['time'].iloc[0]} to {df['time'].iloc[-1]}")
    
    trades = backtest_combined(df, symbol)
    
    trend_trades = [t for t in trades if t["strategy"] == "trend"]
    range_trades = [t for t in trades if t["strategy"] == "range"]
    
    print("\n" + "=" * 70)
    print("COMBINED RESULTS")
    print("=" * 70)
    r = summarize(trades, "ALL")
    print(f"Total trades:  {r['n']}")
    print(f"Win rate:      {r['win_rate']:.0%}")
    print(f"Avg win:       +{r['avg_win']:.2f}R")
    print(f"Avg loss:      -{r['avg_loss']:.2f}R")
    print(f"Expectancy:    {r['expectancy']:+.3f}R")
    print(f"Total:         {r['total']:+.1f}R")
    
    print("\n" + "─" * 70)
    print("BREAKDOWN BY STRATEGY")
    print("─" * 70)
    tr = summarize(trend_trades, "Trend")
    rr = summarize(range_trades, "Range")
    for s in [tr, rr]:
        if s["n"] > 0:
            print(f"\n{s['label']} ({s['n']} trades):")
            print(f"  Win rate:   {s['win_rate']:.0%}")
            print(f"  Expectancy: {s['expectancy']:+.3f}R")
            print(f"  Total:      {s['total']:+.1f}R")
    
    connector.disconnect()


if __name__ == "__main__":
    main()