"""
NAZON — Market Regime Filter
=============================
Tells NAZON what KIND of market a pair is in before any strategy fires.

Why this matters:
  - Trend Rider works in TRENDING markets, fails in ranges (gets chopped up).
  - Structure Bounce works in RANGING markets, fails in strong trends
    (price blows through the level you bounced off).
So before picking a strategy, NAZON should ask: "what regime is this?"

We use ADX (Average Directional Index) — the standard tool for measuring
trend STRENGTH (not direction). Plus the +DI / -DI lines for direction.

  ADX >= 25  -> trending     (let Trend Rider / Momentum run)
  ADX <= 20  -> ranging      (let Structure Bounce run)
  20 < ADX < 25 -> transition (uncertain — NAZON should be cautious)

This module computes ADX from raw OHLC candles with no external TA library,
so it works anywhere (no pandas-ta dependency needed for this piece).
"""

import pandas as pd


# ---- Tunable thresholds (keep them here, not scattered in the code) ----
ADX_PERIOD = 14          # standard ADX lookback
TREND_MIN = 30           # ADX at/above this = trending (raised 25->30: weak
                         # trends near 25 chop up pullback entries; require a
                         # genuinely strong trend before Trend Rider fires)
RANGE_MAX = 20           # ADX at/below this = ranging
# Between RANGE_MAX and TREND_MIN is the "transition" no-man's-land.


def compute_adx(df: pd.DataFrame, period: int = ADX_PERIOD) -> pd.DataFrame:
    """
    Compute ADX, +DI and -DI from a candle DataFrame.

    Expects columns: 'high', 'low', 'close' (lowercase, as MT5 gives them).
    Returns the same DataFrame with 'adx', 'plus_di', 'minus_di' added.

    Note: the first `period` rows will be NaN/unreliable while the indicator
    warms up. That's expected — never trade on warm-up bars.
    """
    df = df.copy()

    high = df['high']
    low = df['low']
    close = df['close']
    prev_close = close.shift(1)

    # --- True Range: the real range of a candle including gaps ---
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)

    # --- Directional Movement ---
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low

    plus_dm = ((up_move > down_move) & (up_move > 0)) * up_move
    minus_dm = ((down_move > up_move) & (down_move > 0)) * down_move

    # --- Wilder's smoothing (an EMA with alpha = 1/period) ---
    atr = tr.ewm(alpha=1 / period, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr)

    # --- ADX itself: smoothed version of the DI spread ---
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.ewm(alpha=1 / period, adjust=False).mean()

    df['adx'] = adx
    df['plus_di'] = plus_di
    df['minus_di'] = minus_di
    return df


def detect_regime(df: pd.DataFrame, period: int = ADX_PERIOD) -> dict:
    """
    Decide the current market regime from the most recent CLOSED candle.

    Returns:
      {
        'regime'    : 'trending' | 'ranging' | 'transition',
        'direction' : 'up' | 'down' | 'none',
        'adx'       : float,
        'allow'     : [list of strategy names allowed]
      }
    """
    df = compute_adx(df, period)
    last = df.iloc[-1]

    adx = last['adx']
    plus_di = last['plus_di']
    minus_di = last['minus_di']

    # Guard against warm-up bars where ADX is still NaN
    if pd.isna(adx):
        return {
            'regime': 'transition',
            'direction': 'none',
            'adx': None,
            'allow': [],
        }

    # Direction from which DI line is on top
    if plus_di > minus_di:
        direction = 'up'
    elif minus_di > plus_di:
        direction = 'down'
    else:
        direction = 'none'

    # ── REGIME CLASSIFICATION ──────────────────────────────────────
    if adx >= TREND_MIN:
        regime = 'trending'
        allow = ['trend_rider', 'momentum']
    elif adx <= RANGE_MAX:
        regime = 'ranging'
        allow = ['structure_bounce', 'structure_bounce_v2']
    else:
        regime = 'transition'
        allow = []

    return {
        'regime': regime,
        'direction': direction,
        'adx': round(float(adx), 1),
        'allow': allow,
    }


def strategy_allowed(strategy_name: str, regime_info: dict) -> bool:
    """
    Quick gate the signal engine calls before running a strategy.

      if not strategy_allowed('trend_rider', regime_info):
          skip this strategy

    Keeps the regime logic in one place instead of sprinkling
    if-statements through the engine.
    """
    return strategy_name in regime_info.get('allow', [])
