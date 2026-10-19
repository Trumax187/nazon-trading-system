#!/usr/bin/env python3
"""Backtest ONLY the range strategy on Gold, June 2026 – Oct 2026."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime
import MetaTrader5 as mt5
import pandas as pd

from nazon.core.mt5_connector import MT5Connector
from nazon.core.regime import detect_regime
from nazon.core.structure_bounce_v2 import structure_bounce_v2_signals, STOP_ATR_MULT, TP_ATR_MULT
from nazon.core.exit_manager import Position, update


WARMUP = 60


def backtest_range(df, symbol):
    trades = []
    i = WARMUP
    while i < len(df) - 1:
        window = df.iloc[:i+1].reset_index(drop=True)
        regime = detect_regime(window)
        
        if regime["regime"] != "ranging" or regime["adx"] is None:
            i += 1
            continue
        
        fired = structure_bounce_v2_signals(window, regime["adx"])
        if not fired:
            i += 1
            continue
        
        direction = fired[0][1]
        
        # Enter at next bar open
        entry = float(df.iloc[i+1]["open"])
        
        # ATR-based stop/TP
        recent = window.tail(14)
        atr_approx = float((recent["high"] - recent["low"]).mean())
        
        if direction == "buy":
            stop = entry - atr_approx * STOP_ATR_MULT
            tp = entry + atr_approx * TP_ATR_MULT
        else:
            stop = entry + atr_approx * STOP_ATR_MULT
            tp = entry - atr_approx * TP_ATR_MULT
        
        risk = abs(entry - stop)
        if risk <= 0:
            i += 1
            continue
        
        pos = Position(symbol=symbol, direction=direction, entry=entry,
                       stop=stop, tp1=tp, tp2=tp, tp3=tp, lots=1.0)
        
        j = i + 1
        realized_r = 0.0
        while j < len(df) and not pos.closed:
            bar = df.iloc[j]
            prices = [bar["low"], bar["high"]] if direction == "buy" else [bar["high"], bar["low"]]
            for px in prices:
                update(pos, float(px))
                if pos.closed:
                    # Compute R
                    if direction == "buy":
                        exit_px = pos.stop_now
                        r = (exit_px - entry) / risk
                    else:
                        exit_px = pos.stop_now
                        r = (entry - exit_px) / risk
                    realized_r = r
                    break
            j += 1
        
        trades.append({"r": realized_r, "outcome": "win" if realized_r > 0.05 else "loss" if realized_r < -0.05 else "be"})
        i = j + 1
    
    n = len(trades)
    if n == 0:
        return {"n": 0}
    wins = [t for t in trades if t["outcome"] == "win"]
    losses = [t for t in trades if t["outcome"] == "loss"]
    return {
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
    
    print("=" * 65)
    print("RANGE STRATEGY BACKTEST — structure_bounce_v2")
    print("=" * 65)
    
    for symbol in ["XAUUSDm", "EURUSDm"]:
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 3000)
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        
        result = backtest_range(df, symbol)
        
        print(f"\n{symbol}:")
        if result["n"] == 0:
            print("  No trades generated.")
        else:
            print(f"  Trades:     {result['n']}")
            print(f"  Win rate:   {result['win_rate']:.0%}")
            print(f"  Avg win:    +{result['avg_win']:.2f}R")
            print(f"  Avg loss:   -{result['avg_loss']:.2f}R")
            print(f"  Expectancy: {result['expectancy']:+.3f}R")
            print(f"  Total:      {result['total']:+.1f}R")
    
    connector.disconnect()


if __name__ == "__main__":
    main()