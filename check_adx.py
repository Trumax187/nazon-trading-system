# check_adx.py
import sys
sys.path.insert(0, r"C:\Users\TRUEMAX KATEMA\Desktop\NAZON")

from nazon.core.mt5_connector import MT5Connector
from nazon.core.regime import detect_regime

connector = MT5Connector()
if connector.connect():
    df = connector.get_candles("XAUUSDm", count=100)
    if df is not None:
        regime = detect_regime(df)
        print(f"Current XAUUSDm:")
        print(f"  ADX: {regime['adx']}")
        print(f"  Regime: {regime['regime']}")
        print(f"  Direction: {regime['direction']}")
        print(f"  Price: {df['close'].iloc[-1]:.2f}")
    connector.disconnect()