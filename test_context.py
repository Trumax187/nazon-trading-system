# test_signal_v2.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import MetaTrader5 as mt5
import pandas as pd
from nazon.core.mt5_connector import MT5Connector
from nazon.core.signal_engine import build_context, format_context
from nazon.core.signal_engine_v2 import generate_signal, format_signal


def main():
    connector = MT5Connector()
    if not connector.connect():
        return
    
    # Get H4 data
    rates = mt5.copy_rates_from_pos("XAUUSDm", mt5.TIMEFRAME_H4, 0, 500)
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    
    # Build context
    ctx = build_context(df, "XAUUSDm")
    print(format_context(ctx))
    print()
    
    # Get current spread and balance
    spread = connector.get_spread("XAUUSDm") or 260
    balance = connector.get_balance() or 10000
    
    # Generate signal
    signal = generate_signal(ctx, spread_points=spread, balance=balance, risk_pct=0.01)
    
    print(format_signal(ctx, signal))
    
    connector.disconnect()


if __name__ == "__main__":
    main()