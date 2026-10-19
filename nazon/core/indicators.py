"""
NAZON — Indicators
==================
Technical indicators used by strategies: EMA, RSI, MACD, plus trend state helpers.
"""

import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential moving average. Weights recent prices more heavily."""
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index (Wilder's). 0..100."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """
    MACD line, signal line, histogram.
    Returns (macd_line, signal_line, histogram).
    """
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def ema_cross_state(series: pd.Series, fast: int = 20, slow: int = 50) -> str:
    """
    EMA cross state on latest closed candle:
      'up'      — fast EMA above slow EMA (bullish)
      'down'    — fast EMA below slow EMA (bearish)
      'neutral' — EMAs within 0.1% of each other (no clear trend)
    """
    if len(series) < slow + 5:
        return "neutral"

    ema_fast = ema(series, fast).iloc[-1]
    ema_slow = ema(series, slow).iloc[-1]

    if pd.isna(ema_fast) or pd.isna(ema_slow) or ema_slow == 0:
        return "neutral"

    diff_pct = abs(ema_fast - ema_slow) / ema_slow
    if diff_pct < 0.001:
        return "neutral"
    return "up" if ema_fast > ema_slow else "down"

def find_swing_levels(df: pd.DataFrame, lookback: int = 5, 
                      num_levels: int = 3) -> dict:
    """
    Find recent swing highs and lows (support/resistance).
    
    A swing high is a candle whose high is higher than the `lookback` candles
    on both sides. A swing low is the inverse.
    
    Returns:
        {
            'resistance': [list of recent swing highs, newest first],
            'support': [list of recent swing lows, newest first],
        }
    """
    highs = df['high'].values
    lows = df['low'].values
    n = len(df)
    
    swing_highs = []
    swing_lows = []
    
    for i in range(lookback, n - lookback):
        # Swing high: high[i] > all highs in [i-lookback, i+lookback]
        window_highs = highs[i - lookback:i + lookback + 1]
        if highs[i] == max(window_highs) and window_highs.tolist().count(highs[i]) == 1:
            swing_highs.append((i, float(highs[i])))
        
        # Swing low
        window_lows = lows[i - lookback:i + lookback + 1]
        if lows[i] == min(window_lows) and window_lows.tolist().count(lows[i]) == 1:
            swing_lows.append((i, float(lows[i])))
    
    # Return newest first, limited to num_levels
    resistance = [price for _, price in reversed(swing_highs[-num_levels:])]
    support = [price for _, price in reversed(swing_lows[-num_levels:])]
    
    return {
        'resistance': resistance,
        'support': support,
    }


def calculate_atr(df: pd.DataFrame, period: int = 14) -> float:
    """Return the latest ATR value."""
    high = df['high']
    low = df['low']
    close = df['close']
    prev_close = close.shift(1)
    
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    
    atr = tr.rolling(window=period).mean()
    return float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else 0.0