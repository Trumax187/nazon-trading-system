# test_connection.py - Run this FIRST
import MetaTrader5 as mt5

print("=" * 50)
print("NAZON - MT5 CONNECTION TEST")
print("=" * 50)

# Initialize MT5
if mt5.initialize():
    print("✅ MT5 initialized successfully")
else:
    print(f"❌ MT5 initialization failed. Error: {mt5.last_error()}")
    mt5.shutdown()
    exit()

# Check if you're logged in
account = mt5.account_info()
if account is not None:
    print(f"✅ Logged in! Account: {account.login}")
    print(f"💰 Balance: ${account.balance:.2f}")
    print(f"📊 Equity: ${account.equity:.2f}")
else:
    print("❌ NOT LOGGED IN")
    print("   Please open MT5 and log into your Exness account")
    print("   Then run this script again")

mt5.shutdown()
# NAZON v0.6 - Fixed Connection Version
import MetaTrader5 as mt5
import pandas as pd
import pandas_ta as ta
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================
PAIRS = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD']
TIMEFRAME = mt5.TIMEFRAME_H1
RISK_PERCENT = 0.01

# ============================================================
# CONNECT TO MT5 (WITH ERROR HANDLING)
# ============================================================
print("=" * 70)
print("🔍 NAZON CANDLE PATTERN SCANNER v0.6")
print("=" * 70)

# Initialize MT5
if not mt5.initialize():
    print(f"❌ MT5 initialization failed!")
    print(f"   Error: {mt5.last_error()}")
    print("\n💡 SOLUTION:")
    print("   1. Open MetaTrader 5")
    print("   2. Log into your Exness account")
    print("   3. Run this script again")
    mt5.shutdown()
    exit()

# Get account info
account = mt5.account_info()
if account is None:
    print("❌ Not logged into MT5!")
    print("\n💡 SOLUTION:")
    print("   1. In MT5, go to File → Login to Trade Account")
    print("   2. Enter your Exness credentials")
    print("   3. Run this script again")
    mt5.shutdown()
    exit()

# Success!
print(f"✅ Connected to MT5")
print(f"💰 Account: {account.login} | Balance: ${account.balance:.2f}")
print("=" * 70)

# ============================================================
# REST OF YOUR SCANNER CODE HERE
# ============================================================
# (Copy the rest of the scanner from my previous message)
# NAZON v0.6 - Full Candle Pattern Scanner
import MetaTrader5 as mt5
import pandas as pd
import pandas_ta as ta
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================
PAIRS = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD']
TIMEFRAME = mt5.TIMEFRAME_H1
RISK_PERCENT = 0.01  # 1% risk per trade

# ============================================================
# CONNECT TO MT5
# ============================================================
mt5.initialize()
account = mt5.account_info()

print("=" * 70)
print(f"🔍 NAZON CANDLE PATTERN SCANNER v0.6 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("=" * 70)
print(f"💰 Account: {account.login} | Balance: ${account.balance:.2f}")
print("=" * 70)

# ============================================================
# CANDLE PATTERN DETECTION FUNCTIONS
# ============================================================

def detect_candle_pattern(candle):
    """Detect candle patterns from a single candle (dictionary)"""
    patterns = []
    
    open_price = candle['open']
    close_price = candle['close']
    high = candle['high']
    low = candle['low']
    
    body = abs(close_price - open_price)
    total_range = high - low
    upper_wick = high - max(open_price, close_price)
    lower_wick = min(open_price, close_price) - low
    
    is_bullish = close_price > open_price
    is_bearish = close_price < open_price
    
    # Marubozu (no wicks)
    if total_range > 0 and body / total_range > 0.9:
        patterns.append("🟢 MARUBOZU BULLISH" if is_bullish else "🔴 MARUBOZU BEARISH")
    
    # Doji (very small body)
    if total_range > 0 and body / total_range < 0.1:
        patterns.append("⚪ DOJI - Indecision")
    
    # Hammer / Hanging Man
    if body > 0 and lower_wick > body * 2 and upper_wick < body * 0.3:
        patterns.append("🔨 HAMMER" if is_bullish else "📌 HANGING MAN")
    
    # Shooting Star
    if body > 0 and upper_wick > body * 2 and lower_wick < body * 0.3 and is_bearish:
        patterns.append("⭐ SHOOTING STAR")
    
    # Engulfing requires 2 candles (will detect separately)
    
    return patterns if patterns else ["📊 STANDARD CANDLE"]

def detect_engulfing(df, idx):
    """Detect bullish/bearish engulfing pattern"""
    if idx < 1:
        return None
    
    curr = df.iloc[idx]
    prev = df.iloc[idx - 1]
    
    curr_bullish = curr['close'] > curr['open']
    prev_bearish = prev['close'] < prev['open']
    
    # Bullish Engulfing
    if (curr_bullish and prev_bearish and 
        curr['open'] < prev['close'] and 
        curr['close'] > prev['open']):
        return "🟢 BULLISH ENGULFING"
    
    curr_bearish = curr['close'] < curr['open']
    prev_bullish = prev['close'] > prev['open']
    
    # Bearish Engulfing
    if (curr_bearish and prev_bullish and 
        curr['open'] > prev['close'] and 
        curr['close'] < prev['open']):
        return "🔴 BEARISH ENGULFING"
    
    return None

# ============================================================
# INDICATOR FUNCTIONS
# ============================================================

def calculate_rsi(prices, period=14):
    """RSI calculator"""
    if len(prices) < period + 1:
        return 50
    
    deltas = []
    for i in range(1, len(prices)):
        deltas.append(prices[i] - prices[i-1])
    
    gains = []
    losses = []
    for delta in deltas:
        if delta > 0:
            gains.append(delta)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(delta))
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)

def calculate_lot_size(balance, risk_pct, sl_pips, pip_value=0.1):
    """Position sizing"""
    risk_dollars = balance * risk_pct
    lot_size = risk_dollars / (sl_pips * pip_value)
    return round(lot_size, 2)

# ============================================================
# MAIN SCANNING LOOP
# ============================================================
strong_signals = 0
weak_signals = 0

for pair in PAIRS:
    print(f"\n{'='*70}")
    print(f"📊 SCANNING: {pair}")
    print("=" * 70)
    
    try:
        # Get last 100 candles
        rates = mt5.copy_rates_from_pos(pair, TIMEFRAME, 0, 100)
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # Current price
        tick = mt5.symbol_info_tick(pair)
        current_price = tick.bid if tick else df['close'].iloc[-1]
        
        # ====================================================
        # CANDLE PATTERN ANALYSIS (Last 2 candles)
        # ====================================================
        print("\n🕯️ CANDLE PATTERN ANALYSIS:")
        print("-" * 40)
        
        # Last candle
        last_candle = df.iloc[-1].to_dict()
        last_patterns = detect_candle_pattern(last_candle)
        print(f"   Last candle: {last_patterns[0]}")
        
        if last_candle['close'] > last_candle['open']:
            print(f"   Direction: 🟢 BULLISH (Close: {last_candle['close']:.5f} > Open: {last_candle['open']:.5f})")
        else:
            print(f"   Direction: 🔴 BEARISH (Close: {last_candle['close']:.5f} < Open: {last_candle['open']:.5f})")
        
        # Candle measurements
        body = abs(last_candle['close'] - last_candle['open'])
        total_range = last_candle['high'] - last_candle['low']
        wick_upper = last_candle['high'] - max(last_candle['open'], last_candle['close'])
        wick_lower = min(last_candle['open'], last_candle['close']) - last_candle['low']
        
        print(f"   Body size: {body:.5f} | Range: {total_range:.5f}")
        print(f"   Upper wick: {wick_upper:.5f} | Lower wick: {wick_lower:.5f}")
        
        # Engulfing pattern (last 2 candles)
        engulfing = detect_engulfing(df, -1)
        if engulfing:
            print(f"   🔥 PATTERN: {engulfing}")
        
        # Second last candle
        if len(df) > 1:
            prev_candle = df.iloc[-2].to_dict()
            prev_patterns = detect_candle_pattern(prev_candle)
            prev_dir = "🟢 BULLISH" if prev_candle['close'] > prev_candle['open'] else "🔴 BEARISH"
            print(f"   Previous candle: {prev_patterns[0]} ({prev_dir})")
        
        # ====================================================
        # INDICATORS
        # ====================================================
        print("\n📈 INDICATORS:")
        print("-" * 40)
        
        closes = df['close'].tolist()
        rsi = calculate_rsi(closes)
        
        # Moving averages
        ma_20 = df['close'].tail(20).mean()
        ma_50 = df['close'].tail(50).mean()
        
        # MACD
        macd_data = ta.macd(df['close'])
        if macd_data is not None and len(macd_data) > 0:
            last_macd = macd_data.iloc[-1]
            macd_cols = macd_data.columns.tolist()
            macd_line = last_macd[macd_cols[0]] if len(macd_cols) > 0 else 0
            signal_line = last_macd[macd_cols[1]] if len(macd_cols) > 1 else 0
            macd_histogram = macd_line - signal_line
        else:
            macd_histogram = 0
        
        print(f"   RSI (14): {rsi}")
        print(f"   MA20: {ma_20:.5f} | MA50: {ma_50:.5f}")
        print(f"   MACD Histogram: {macd_histogram:.5f}")
        
        # Trend
        if current_price > ma_20 and ma_20 > ma_50:
            trend = "🟢 BULLISH UPTREND"
        elif current_price < ma_20 and ma_20 < ma_50:
            trend = "🔴 BEARISH DOWNTREND"
        else:
            trend = "🟡 CONSOLIDATION / TRANSITION"
        print(f"   Trend: {trend}")
        
        # ====================================================
        # SIGNAL LOGIC (Enhanced with candle patterns)
        # ====================================================
        print("\n🎯 NAZON SIGNAL:")
        print("-" * 40)
        
        # Check for strong patterns
        has_marubozu = "MARUBOZU" in last_patterns[0]
        has_engulfing = engulfing is not None
        is_hammer = "HAMMER" in last_patterns[0]
        
        # Strong signal conditions
        if (rsi > 65 and current_price < ma_20 and macd_histogram < 0) or (has_marubozu and "BEARISH" in last_patterns[0]):
            signal = "🔴 STRONG SELL"
            reason = "Overbought + bearish MA + MACD down" + (" + BEARISH MARUBOZU" if has_marubozu and "BEARISH" in last_patterns[0] else "")
            strong_signals += 1
        elif (rsi < 35 and current_price > ma_20 and macd_histogram > 0) or (has_marubozu and "BULLISH" in last_patterns[0]):
            signal = "🟢 STRONG BUY"
            reason = "Oversold + bullish MA + MACD up" + (" + BULLISH MARUBOZU" if has_marubozu and "BULLISH" in last_patterns[0] else "")
            strong_signals += 1
        elif has_engulfing and "BULLISH" in engulfing and rsi < 45:
            signal = "🟢 BULLISH ENGULFING BUY"
            reason = f"Bullish engulfing pattern + RSI {rsi}"
            weak_signals += 1
        elif has_engulfing and "BEARISH" in engulfing and rsi > 55:
            signal = "🔴 BEARISH ENGULFING SELL"
            reason = f"Bearish engulfing pattern + RSI {rsi}"
            weak_signals += 1
        elif is_hammer and rsi < 40:
            signal = "🔨 HAMMER REVERSAL BUY"
            reason = f"Hammer pattern at potential bottom + RSI {rsi}"
            weak_signals += 1
        elif current_price > ma_20 and ma_20 > ma_50:
            signal = "🟡 WEAK BUY"
            reason = "Uptrend confirmed, wait for RSI pullback to 30-40"
            weak_signals += 1
        elif current_price < ma_20 and ma_20 < ma_50:
            signal = "🟠 WEAK SELL"
            reason = "Downtrend confirmed, wait for RSI bounce to 60-70"
            weak_signals += 1
        else:
            signal = "⚪ WAIT"
            reason = "No clear setup - market consolidating"
        
        print(f"   → {signal}")
        print(f"   📝 {reason}")
        
        # Position sizing
        if "BUY" in signal or "SELL" in signal:
            # Calculate ATR for stop loss
            highs = df['high'].tail(14).tolist()
            lows = df['low'].tail(14).tolist()
            closes_14 = df['close'].tail(14).tolist()
            tr_values = []
            for i in range(1, len(closes_14)):
                hl = highs[i] - lows[i]
                hc = abs(highs[i] - closes_14[i-1])
                lc = abs(lows[i] - closes_14[i-1])
                tr_values.append(max(hl, hc, lc))
            atr = sum(tr_values) / len(tr_values) if tr_values else 0.001
            sl_pips = int(atr * 10000)
            
            lot = calculate_lot_size(account.balance, RISK_PERCENT, max(sl_pips, 20))
            print(f"   📐 Suggested lot: {lot} (${RISK_PERCENT*100}% risk)")
        
    except Exception as e:
        print(f"   ❌ ERROR: {e}")

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 70)
print("📊 NAZON SCAN COMPLETE")
print("=" * 70)
print(f"   🔥 Strong signals: {strong_signals}")
print(f"   📈 Weak signals: {weak_signals}")
print(f"   ⚪ Wait/Neutral: {len(PAIRS) - strong_signals - weak_signals}")
print("=" * 70)

print("\n💡 LEGEND:")
print("   🟢 STRONG BUY/SELL - HIGH probability setups")
print("   🟡/🟠 WEAK - Good trend, wait for entry")
print("   ⚪ WAIT - No clear setup")
print("   🔨 HAMMER - Potential reversal pattern")
print("   🟢/🔴 ENGULFING - Strong reversal pattern")
print("   🟢/🔴 MARUBOZU - Extreme momentum")

mt5.shutdown()
print("\n✅ NAZON v0.6 scan complete!")