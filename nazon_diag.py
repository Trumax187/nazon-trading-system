# nazon_diag.py — find out WHERE trades are being lost
import MetaTrader5 as mt5
import pandas as pd
from nazon.core.mt5_connector import MT5Connector
from nazon.core.regime import detect_regime
from nazon.core.signal_engine import _strategies, _build_plan
from nazon.core.signal_contract import new_signal
from nazon import config

nazon = MT5Connector()
if not nazon.connect():
    print("Could not connect."); exit()

symbol = "XAUUSDm"
mt5.symbol_select(symbol, True)
rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 3000)
df = pd.DataFrame(rates)
df["time"] = pd.to_datetime(df["time"], unit="s")
df = df[["time","open","high","low","close"]].iloc[:-1].reset_index(drop=True)
point = config.SYMBOLS[symbol]["point"]

# Counters for each stage
counts = {"bars":0, "regime_trending":0, "regime_ranging":0, "regime_transition":0,
          "any_fired":0, "enough_agree":0, "rr_ok":0, "rr_fail":0}
rr_samples = []

WARMUP = 210
for i in range(WARMUP, len(df)-1):
    window = df.iloc[:i+1]
    counts["bars"] += 1
    regime = detect_regime(window)
    counts[f"regime_{regime['regime']}"] += 1

    fired = _strategies(window, regime)
    if fired:
        counts["any_fired"] += 1
        buys = [n for n,d in fired if d=="buy"]
        sells = [n for n,d in fired if d=="sell"]
        if len(buys) >= config.MIN_STRATEGIES_AGREE or len(sells) >= config.MIN_STRATEGIES_AGREE:
            counts["enough_agree"] += 1
            direction = "buy" if len(buys)>=config.MIN_STRATEGIES_AGREE else "sell"
            sig = new_signal(symbol)
            _build_plan(sig, window, direction, point)
            if sig.rr is not None:
                rr_samples.append(sig.rr)
                if sig.rr >= config.MIN_RR:
                    counts["rr_ok"] += 1
                else:
                    counts["rr_fail"] += 1

nazon.disconnect()

print("\n--- DIAGNOSTIC: XAUUSDm over", counts["bars"], "decision bars ---")
for k,v in counts.items():
    print(f"  {k:20s}: {v}")
if rr_samples:
    import statistics
    print(f"\n  R:R values seen: min={min(rr_samples):.2f} "
          f"max={max(rr_samples):.2f} avg={statistics.mean(rr_samples):.2f}")
    print(f"  MIN_RR required: {config.MIN_RR}")
print(f"\n  MIN_STRATEGIES_AGREE = {config.MIN_STRATEGIES_AGREE}")