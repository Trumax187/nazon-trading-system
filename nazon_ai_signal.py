#!/usr/bin/env python3
"""NAZON AI Signal — Combines MT5 context with Gemini analysis."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import MetaTrader5 as mt5
import pandas as pd
from nazon.core.mt5_connector import MT5Connector
from nazon.core.signal_engine import build_context, format_context
import nazon_ai as ai


def main():
    connector = MT5Connector()
    if not connector.connect():
        return

    rates = mt5.copy_rates_from_pos("XAUUSDm", mt5.TIMEFRAME_H4, 0, 500)
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")

    ctx = build_context(df, "XAUUSDm")
    context_str = format_context(ctx)

    print("=" * 60)
    print("NAZON CONTEXT")
    print("=" * 60)
    print(context_str)
    print()

    print("=" * 60)
    print("ASKING GEMINI FOR SECOND OPINION")
    print("=" * 60)
    ai_opinion = ai.analyze_chart(context_str)
    print(ai_opinion)

    connector.disconnect()


if __name__ == "__main__":
    main()
