# check_data_gaps.py
import MetaTrader5 as mt5
import pandas as pd
from datetime import timedelta

mt5.initialize()
rates = mt5.copy_rates_from_pos("XAUUSDm", mt5.TIMEFRAME_H4, 0, 15000)
df = pd.DataFrame(rates)
df["time"] = pd.to_datetime(df["time"], unit="s")

# Expected interval: 4 hours (with weekend gaps)
df["gap"] = df["time"].diff()

# Weekend gaps should be ~48-72 hours. Anything else is suspicious.
weekday_gaps = df[(df["gap"] < timedelta(hours=12)) & (df["gap"] > timedelta(hours=5))]
big_gaps = df[df["gap"] > timedelta(hours=80)]

print(f"Total bars: {len(df)}")
print(f"Date range: {df['time'].iloc[0]} to {df['time'].iloc[-1]}")
print(f"\nAbnormal weekday gaps: {len(weekday_gaps)}")
print(f"Weekend gaps (>80h): {len(big_gaps)}")

# Check for missing days
expected_days = (df["time"].iloc[-1] - df["time"].iloc[0]).days
actual_days = df["time"].dt.date.nunique()
print(f"\nExpected trading days (approx): {expected_days * 5/7:.0f}")
print(f"Actual unique days: {actual_days}")

mt5.shutdown()