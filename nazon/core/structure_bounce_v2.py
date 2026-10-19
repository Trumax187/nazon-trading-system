"""
NAZON — Structure Bounce v2 (Range Mean-Reversion Strategy)
============================================================
A dedicated mean-reversion strategy for RANGING markets (ADX < 25).

Designed to complement the trend-following strategies (trend_rider, momentum)
which only fire in TRENDING markets (ADX > 30).

Logic (triple-filter confirmation):
  1. REGIME: only fires when ADX < 25 (ranging confirmed)
  2. TRIGGER: Stochastic %K crosses %D (momentum reversal)
  3. CONFIRM: price touches Bollinger Band (statistical extreme)
  4. OPTIONAL FILTER: Gaussian Channel midline alignment

Exit strategy: tight stop, small TP (high win rate, small wins).

This is a SEPARATE strategy from the trend-following ones. It has its own
tuning constants and its own logic. Do not mix with trend_rider/momentum.
"""

import pandas as pd
from nazon.core import indicators as ind


# ── Tuning constants (all here, one place) ─────────────────────────────
ADX_RANGE_MAX = 25          # Only fire when ADX below this
BB_PERIOD = 20              # Bollinger Band lookback
BB_STD = 2.0                # Bollinger Band standard deviations
STOCH_PERIOD = 14           # Stochastic lookback
STOCH_SMOOTH = 3            # Stochastic %K smoothing
STOCH_OB = 80               # Overbought threshold (sell zone)
STOCH_OS = 20               # Oversold threshold (buy zone)

# Risk geometry (tight stops for range trading)
STOP_ATR_MULT = 3.5         # Wider stop for range trades (absorb noise)
TP_ATR_MULT = 1.0           # Small target (mean-reversion move)


def _stochastic(df: pd.DataFrame, period: int = STOCH_PERIOD,
                smooth_k: int = STOCH_SMOOTH, smooth_d: int = 3):
    """
    Compute Stochastic %K and %D.
    Returns (k_series, d_series).
    """
    low_min = df["low"].rolling(window=period).min()
    high_max = df["high"].rolling(window=period).max()

    # %K raw
    k_raw = 100 * (df["close"] - low_min) / (high_max - low_min + 1e-10)
    # Smooth %K
    k = k_raw.rolling(window=smooth_k).mean()
    # %D = SMA of %K
    d = k.rolling(window=smooth_d).mean()
    return k, d


def _bollinger(series: pd.Series, period: int = BB_PERIOD, num_std: float = BB_STD):
    """
    Bollinger Bands: middle (SMA), upper, lower.
    Returns (mid, upper, lower).
    """
    mid = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return mid, upper, lower


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range — for stop/target sizing."""
    high = df["high"]
    low = df["low"]
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def structure_bounce_v2_signals(df: pd.DataFrame, adx_value: float) -> list[tuple[str, str]]:
    """
    Run the range mean-reversion strategy on the latest closed candles.
    
    Returns a list of (strategy_name, direction) — same format as other
    strategies so signal_engine can consume it uniformly.
    
    Args:
        df: DataFrame with columns: open, high, low, close (latest closed candle last)
        adx_value: current ADX (from regime detection)
    
    Returns:
        [('structure_bounce_v2', 'buy')] if long setup
        [('structure_bounce_v2', 'sell')] if short setup
        [] if no setup
    """
    # Need enough history
    if len(df) < max(BB_PERIOD, STOCH_PERIOD, 20) + 5:
        return []

    # Guard: only fire in ranging regime
    if adx_value is None or adx_value >= ADX_RANGE_MAX:
        return []

    # Calculate indicators
    k, d = _stochastic(df)
    bb_mid, bb_upper, bb_lower = _bollinger(df["close"])
    atr = _atr(df)

    # Latest values
    price = float(df["close"].iloc[-1])
    k_now = k.iloc[-1]
    d_now = d.iloc[-1]
    k_prev = k.iloc[-2] if len(k) > 1 else None
    d_prev = d.iloc[-2] if len(d) > 1 else None
    
    bb_lo = bb_lower.iloc[-1]
    bb_hi = bb_upper.iloc[-1]
    bb_mid_val = bb_mid.iloc[-1]
    atr_val = atr.iloc[-1]

    # Guard against NaN (warm-up)
    if any(pd.isna(v) for v in [k_now, d_now, k_prev, d_prev, bb_lo, bb_hi, bb_mid_val, atr_val]):
        return []

    fired = []

    # ── LONG SETUP ──────────────────────────────────────────────────
    # Oversold + stochastic cross up + price near lower band + below midline
    oversold = k_now < STOCH_OS
    stoch_cross_up = (k_prev is not None and d_prev is not None 
                      and k_prev <= d_prev and k_now > d_now)
    near_lower = price <= bb_lo * 1.002      # within 0.2% of lower band
    below_mid = price < bb_mid_val

    if oversold and stoch_cross_up and near_lower and below_mid:
        fired.append(("structure_bounce_v2", "buy"))

    # ── SHORT SETUP ─────────────────────────────────────────────────
    # Overbought + stochastic cross down + price near upper band + above midline
    overbought = k_now > STOCH_OB
    stoch_cross_down = (k_prev is not None and d_prev is not None
                        and k_prev >= d_prev and k_now < d_now)
    near_upper = price >= bb_hi * 0.998      # within 0.2% of upper band
    above_mid = price > bb_mid_val

    if overbought and stoch_cross_down and near_upper and above_mid:
        fired.append(("structure_bounce_v2", "sell"))

    return fired