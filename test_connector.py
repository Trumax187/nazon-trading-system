# test_connector.py - Test script (directly in NAZON folder)
from nazon.core.mt5_connector import MT5Connector

print("=" * 60)
print("NAZON - TESTING MT5 CONNECTOR")
print("=" * 60)

connector = MT5Connector()
if connector.connect():
    print("\n✅ Connected successfully!")
    
    # Test getting candles for XAUUSDm
    print("\n📊 Fetching candles for XAUUSDm...")
    df = connector.get_candles("XAUUSDm", count=10)
    
    if df is not None:
        print(f"   Got {len(df)} closed candles")
        print(f"\n   Latest candle:")
        latest = df.iloc[-1]
        print(f"   Time: {latest['time']}")
        print(f"   Close: {latest['close']:.2f}")
        
        # Test getting spread
        spread = connector.get_spread("XAUUSDm")
        if spread:
            print(f"\n💰 Current spread: {spread} points")
        
        # Test getting balance
        balance = connector.get_balance()
        if balance:
            print(f"\n💵 Account balance: ${balance:.2f}")
    else:
        print("   Failed to get candles")
    
    connector.disconnect()
else:
    print("❌ Failed to connect to MT5")
    print("   Make sure MT5 is OPEN and LOGGED IN to your DEMO account")

print("\n" + "=" * 60)