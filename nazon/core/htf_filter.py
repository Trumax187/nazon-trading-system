"""
NAZON — Higher-Timeframe (HTF) Trend Filter
===========================================
Tells NAZON what the DAILY trend is, and provides a Daily ADX gate.
The signal engine requires H4 signals to agree with the Daily direction.
"""

import pandas as pd
from nazon.core import indicators as ind


HTF_EMA_PERIOD = 50


def daily_trend_from_d1(d1: pd.DataFrame) -> str:
    """
    Daily trend from real D1 candles: 'up', 'down', or 'none' (warm-up).
    Uses price vs a Daily EMA.
    """
    if d1 is None or len(d1) < HTF_EMA_PERIOD:
        return "none"
    ema = ind.ema(d1["close"], HTF_EMA_PERIOD)
    price = d1["close"].iloc[-1]
    e = ema.iloc[-1]
    if pd.isna(e):
        return "none"
    return "up" if price > e else "down"


def daily_trend_from_h4(h4_window: pd.DataFrame) -> str:
    """
    Fallback: derive Daily bias by resampling an H4 window into daily bars.
    Uses only data INSIDE the window -> no look-ahead.
    """
    if h4_window is None or "time" not in h4_window or len(h4_window) < HTF_EMA_PERIOD * 6:
        return "none"
    df = h4_window.copy()
    df = df.set_index("time")
    daily = df["close"].resample("1D").last().dropna()
    if len(daily) < HTF_EMA_PERIOD:
        return "none"
    ema = daily.ewm(span=HTF_EMA_PERIOD, adjust=False).mean()
    return "up" if daily.iloc[-1] > ema.iloc[-1] else "down"


def agrees(signal_direction: str, daily_bias: str) -> bool:
    """
    Does the H4 signal agree with the Daily bias?
    If bias is 'none' (warm-up), let it pass rather than block everything.
    """
    if daily_bias == "none":
        return True
    if signal_direction == "buy":
        return daily_bias == "up"
    if signal_direction == "sell":
        return daily_bias == "down"
    return False


def daily_adx(df_h4, period: int = 14) -> float | None:
    """
    Compute Daily ADX by resampling H4 candles to Daily.
    Returns the latest Daily ADX value, or None if insufficient data.
    """
    if df_h4 is None or "time" not in df_h4 or len(df_h4) < period * 6:
        return None

    try:
        df = df_h4.copy()
        df = df.set_index("time")
        daily = df.resample("1D").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
        }).dropna().reset_index()

        if len(daily) < period + 5:
            return None

        from nazon.core.regime import compute_adx
        daily = compute_adx(daily, period)
        adx_value = daily["adx"].iloc[-1]

        if pd.isna(adx_value):
            return None
        return float(adx_value)
    except Exception:
        return None