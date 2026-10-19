# nazon_backtest.py — run NAZON's strategies over real history
import MetaTrader5 as mt5
import pandas as pd
from nazon.core.mt5_connector import MT5Connector
from nazon.backtest.backtester import backtest, summarize
from nazon import config

nazon = MT5Connector()
if not nazon.connect():
    print("Could not connect."); exit()

# Pull a LOT of history per pair — ~2 years of H4 is about 3000 bars.
BARS = 3000

for symbol in config.PAIRS:
    # copy_rates_from_pos straight from MT5 for the big history pull
    mt5.symbol_select(symbol, True)
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, BARS)
    if rates is None or len(rates) < 300:
        print(f"{symbol}: not enough history ({0 if rates is None else len(rates)})")
        continue
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df = df[["time","open","high","low","close"]].iloc[:-1].reset_index(drop=True)  # drop forming bar

    point = config.SYMBOLS[symbol]["point"]
    trades = backtest(df, symbol, point)
    s = summarize(trades)

    print(f"\n{'='*55}")
    print(f"{symbol}  ({len(df)} bars, ~{len(df)*4//24} days)")
    print(f"{'='*55}")
    if s["n"] == 0:
        print("  No trades generated over this history.")
    else:
        print(f"  Trades:      {s['n']}")
        print(f"  Win rate:    {s['win_rate']:.0%}")
        print(f"  Avg win:     +{s['avg_win_r']}R   Avg loss: -{s['avg_loss_r']}R")
        print(f"  Expectancy:  {s['expectancy_r']:+.3f}R per trade")
        print(f"  Total:       {s['total_r']:+.1f}R")

nazon.disconnect()