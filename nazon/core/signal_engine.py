"""
NAZON — Signal Engine
=====================
The brain that ties everything together. For one pair's closed candles it:

  1. Computes indicators (EMA200, RSI, MACD, + ADX regime).
  2. Asks the REGIME FILTER which strategies may even fire.
  3. Runs the allowed STRATEGIES; collects the ones that agree on a direction.
  3b. DIRECTION GUARD: drops any signal that fights the regime's own DI-based
      trend direction (the bug that shorted six gold up-trends: the engine
      used only the lagging H4 EMA200 and ignored the regime direction).
  4. Requires MIN_STRATEGIES_AGREE pointing the same way, else -> not approved.
  4b. HTF DAILY FILTER: the H4 signal must agree with the Daily trend. This
      filter existed in htf_filter.py but was never wired in — now it is.
  5. Builds the trade plan (entry / stop / TP1-3 / lot / R:R).
  6. Runs the SPREAD GATE, CORRELATION BLOCK, and KILL SWITCH.
  7. Returns a fully-decided Signal (the contract) for the card + journal.

It DECIDES; it does not place orders. Same logic runs in backtest/demo/live.

The three strategies (from NAZON V1, now regime-aware):
  trend_rider      — trade WITH the trend on an RSI pullback + MACD agreement
  structure_bounce — fade an RSI extreme back toward the mean (ranging markets)
  momentum         — trade a strong MACD thrust in the trend direction
"""

import pandas as pd
from nazon.core.structure_bounce_v2 import structure_bounce_v2_signals
from nazon import config
from nazon.core import indicators as ind
from nazon.core.regime import detect_regime, strategy_allowed
from nazon.core.htf_filter import (
    daily_trend_from_d1, daily_trend_from_h4, agrees,
)
from nazon.core.spread_gate import check_spread, spread_ok
from nazon.core.correlation import check_correlation, correlation_ok, OpenPosition
from nazon.core.kill_switch import can_open_new_trade
from nazon.core.signal_contract import new_signal, approve, reject, Signal

def build_context(df: pd.DataFrame, symbol: str) -> dict:
    """
    Build a complete market context for one pair.
    Returns everything the signal engine needs to make a decision.
    """
    close = df['close']
    high = df['high']
    low = df['low']
    
    # Trend (EMA200)
    ema200 = ind.ema(close, 200).iloc[-1]
    current_price = close.iloc[-1]
    trend = 'up' if current_price > ema200 else 'down'
    
    # Regime (ADX)
    from nazon.core.regime import detect_regime
    regime = detect_regime(df)
    
    # Support/Resistance
    sr = ind.find_swing_levels(df, lookback=5, num_levels=3)
    
    # ATR
    atr = ind.calculate_atr(df, period=14)
    
    # RSI
    rsi = ind.rsi(close, 14).iloc[-1]
    
    # Daily trend (from H4 resample)
    from nazon.core.htf_filter import daily_trend_from_h4
    daily_bias = daily_trend_from_h4(df)
    
    return {
        'symbol': symbol,
        'price': round(float(current_price), 5),
        'trend': trend,
        'ema200': round(float(ema200), 5),
        'regime': regime['regime'],
        'adx': regime['adx'],
        'direction': regime['direction'],
        'daily_bias': daily_bias,
        'rsi': round(float(rsi), 2),
        'atr': round(float(atr), 5),
        'support': [round(p, 5) for p in sr['support']],
        'resistance': [round(p, 5) for p in sr['resistance']],
    }


def format_context(ctx: dict) -> str:
    """Format context as a readable block for output."""
    lines = [
        f"=== {ctx['symbol']} Context ===",
        f"Price:        {ctx['price']}",
        f"Trend (EMA200): {ctx['trend'].upper()} ({ctx['ema200']})",
        f"Daily bias:   {ctx['daily_bias'].upper()}",
        f"Regime:       {ctx['regime'].upper()} (ADX {ctx['adx']})",
        f"Direction:    {ctx['direction'].upper()}",
        f"RSI:          {ctx['rsi']}",
        f"ATR:          {ctx['atr']}",
        f"Resistance:   {ctx['resistance']}",
        f"Support:      {ctx['support']}",
    ]
    return "\n".join(lines)

# ── Strategy tuning (kept here, one place) ───────────────────────────
EMA_PERIOD = 200
RSI_PERIOD = 14
RSI_PULLBACK_LOW, RSI_PULLBACK_HIGH = 40, 65   # healthy pullback zone in a trend
RSI_OVERBOUGHT, RSI_OVERSOLD = 70, 30          # extremes for structure bounce

# Trade-plan geometry: stop distance and TP multiples (in units of risk).
# Stop is placed a fixed fraction beyond entry for now; tuned later on demo.
STOP_ATR_MULT = 1.5        # placeholder geometry — refined when ATR is added
# TP multiples in units of risk (R). TP1 must be >= MIN_RR (1.5) or every trade
# gets rejected at the R:R gate. The backtest diagnostic caught the old 1.0
# value rejecting 100% of trades. 1.5 / 2.5 / 4.0 gives a healthy runner spread.
TP_MULTIPLES = (1.5, 2.5, 5.0)   # TP1=1.5R, TP2=2.5R, TP3=5R

from nazon.core.structure_bounce_v2 import structure_bounce_v2_signals
def _strategies(df: pd.DataFrame, regime: dict) -> list[tuple[str, str]]:
    """
    Run each ALLOWED strategy on the latest closed candle.
    Returns a list of (strategy_name, direction) for those that fired.
    direction is 'buy' or 'sell'.
    """
    fired = []

    close = df["close"]
    ema200 = ind.ema(close, EMA_PERIOD)
    rsi = ind.rsi(close, RSI_PERIOD)
    macd_line, signal_line, hist = ind.macd(close)

    # latest CLOSED values
    price = close.iloc[-1]
    e = ema200.iloc[-1]
    r = rsi.iloc[-1]
    m = macd_line.iloc[-1]

    # Guard against warm-up NaNs (need 200+ candles for EMA200).
    if pd.isna(e) or pd.isna(r) or pd.isna(m):
        return fired

    trend_up = price > e          # above EMA200 = uptrend bias
    trend_dn = price < e

    # Strategy 1 — Trend Rider (with-trend pullback). Allowed in trends.
    if strategy_allowed("trend_rider", regime):
        if trend_up and RSI_PULLBACK_LOW <= r <= RSI_PULLBACK_HIGH and m > 0:
            fired.append(("trend_rider", "buy"))
        elif trend_dn and (100 - RSI_PULLBACK_HIGH) <= r <= (100 - RSI_PULLBACK_LOW) and m < 0:
            fired.append(("trend_rider", "sell"))

    # Strategy 2 — Structure Bounce (fade an extreme). Allowed in ranges.
    if strategy_allowed("structure_bounce", regime):
        if r < RSI_OVERSOLD:
            fired.append(("structure_bounce", "buy"))
        elif r > RSI_OVERBOUGHT:
            fired.append(("structure_bounce", "sell"))
    # Strategy 2b — Structure Bounce v2 (range mean-reversion)
    if regime["regime"] == "ranging":
        adx_value = regime.get("adx")
        if adx_value is not None and adx_value < 25:
            v2_signals = structure_bounce_v2_signals(df, adx_value)
            fired.extend(v2_signals)

    # Strategy 3 — Momentum (strong MACD thrust with trend). Allowed in trends.
    if strategy_allowed("momentum", regime):
        if trend_up and m > 0 and hist.iloc[-1] > 0:
            fired.append(("momentum", "buy"))
        elif trend_dn and m < 0 and hist.iloc[-1] < 0:
            fired.append(("momentum", "sell"))

    return fired

    # Strategy 4 — Structure Bounce v2 (range mean-reversion)
    if regime["regime"] == "ranging":
        adx_val = regime.get("adx")
        if adx_val is not None and adx_val < 25:
            v2 = structure_bounce_v2_signals(df, adx_val)
            fired.extend(v2)


def _build_plan(sig: Signal, df: pd.DataFrame, direction: str, point: float):
    """
    Fill entry / stop / TP1-3 on the signal. Simple, explainable geometry:
    stop a fixed distance from entry, TPs at 1R/2R/3R. Refined on demo later.
    """
    price = float(df["close"].iloc[-1])
    # crude stop distance from recent range (high-low of last 14 closed bars)
    recent = df.tail(14)
    rng = float((recent["high"] - recent["low"]).mean())
    stop_dist = max(rng * STOP_ATR_MULT, point * 10)   # never absurdly tiny

    sig.entry = round(price, 6)
    if direction == "buy":
        sig.stop = round(price - stop_dist, 6)
        sig.tp1 = round(price + stop_dist * TP_MULTIPLES[0], 6)
        sig.tp2 = round(price + stop_dist * TP_MULTIPLES[1], 6)
        sig.tp3 = round(price + stop_dist * TP_MULTIPLES[2], 6)
    else:
        sig.stop = round(price + stop_dist, 6)
        sig.tp1 = round(price - stop_dist * TP_MULTIPLES[0], 6)
        sig.tp2 = round(price - stop_dist * TP_MULTIPLES[1], 6)
        sig.tp3 = round(price - stop_dist * TP_MULTIPLES[2], 6)

    sig.rr = round(abs(sig.tp1 - sig.entry) / abs(sig.entry - sig.stop), 2)


def analyse(symbol: str,
            df: pd.DataFrame,
            spread_points: int,
            point: float,
            balance: float,
            open_positions: list[OpenPosition],
            day_state,
            d1: pd.DataFrame = None) -> Signal:
    """
    Produce a fully-decided Signal for one pair. df = CLOSED candles only.
    open_positions + day_state come from the live account / kill switch.

    d1 (optional) = CLOSED Daily candles for the same symbol, used by the HTF
    filter. If None, the filter falls back to resampling df (needs ~300 H4
    bars or it returns 'none' and lets trades pass). Passing real D1 is safer.
    """
    label = config.SYMBOLS.get(symbol, {}).get("label", "")
    sig = new_signal(symbol, label)

    # --- 0. Kill switch first: is NAZON even allowed to trade right now? ---
    gate = can_open_new_trade(day_state)
    if not gate.allowed:
        return reject(sig, gate.reason)

    # --- 1. Regime ---
    regime = detect_regime(df)
    sig.regime = regime["regime"]
    sig.regime_adx = regime["adx"]
    
    # --- 1a. Tighter H4 ADX gate (Oct 2026) ---
    if regime["adx"] is not None and regime["adx"] < config.MIN_H4_ADX:
        return reject(sig, f"H4 ADX {regime['adx']:.1f} below {config.MIN_H4_ADX} — too weak")
    
    # --- 1b. Daily ADX gate (Oct 2026) ---
    from nazon.core.htf_filter import daily_adx
    d_adx = daily_adx(df)
    if d_adx is not None and d_adx < config.MIN_DAILY_ADX:
        return reject(sig, f"Daily ADX {d_adx:.1f} below {config.MIN_DAILY_ADX} — no daily trend")

    # --- 2. Strategies (only those the regime allows) ---
    fired_raw = _strategies(df, regime)

    # --- 2b. DIRECTION GUARD (the fix) ----------------------------------
    # The regime module already computes the trend DIRECTION from the DI
    # lines (plus_di vs minus_di) — a faster, non-lagging read than the H4
    # EMA200 the strategies use internally. A trend-following strategy must
    # NOT fight it. In an up-trend, only buys survive; in a down-trend, only
    # sells. This is exactly what shorted six gold up-trends: ADX said
    # "strong trend", DI said "up", but the lagging EMA200 said "down" and
    # the engine listened to the EMA200. Now the regime direction wins.
    rdir = regime.get("direction")
    if rdir in ("up", "down"):
        want = "buy" if rdir == "up" else "sell"
        fired = [(n, d) for (n, d) in fired_raw if d == want]
    else:
        fired = fired_raw

    sig.strategies = [name for name, _ in fired]

    if not fired:
        if fired_raw:
            # A strategy DID signal here -- it just fought the regime's own
            # DI-based direction and got vetoed. Distinct from genuine
            # silence: if THIS bucket grows large in the rejection
            # breakdown, it means strategies are regularly firing against
            # price's own momentum, which is worth investigating on its own
            # (possibly a strategy whose internal trend read disagrees with
            # DI more often than expected) rather than being invisible inside
            # a generic "no strategy fired" count.
            vetoed = ",".join(n for n, _ in fired_raw)
            return reject(sig, f"direction guard vetoed {vetoed} "
                               f"({regime['regime']} regime, DI dir {rdir})")
        return reject(sig, f"no strategy fired ({regime['regime']} regime)")
            # --- 2a. EMA 20/50 trend filter (Oct 2026) ---
    if config.USE_EMA_FILTER:
        ema_state = ind.ema_cross_state(df["close"], fast=20, slow=50)
        # Determine intended direction from fired strategies
        buys = [n for n, d in fired if d == "buy"]
        sells = [n for n, d in fired if d == "sell"]
        intended = "buy" if len(buys) >= len(sells) else "sell"
        
        if ema_state == "neutral":
            return reject(sig, "EMA 20/50 neutral — no clear short-term trend")
        if intended == "buy" and ema_state == "down":
            return reject(sig, f"BUY signal against EMA 20/50 (state: down)")
        if intended == "sell" and ema_state == "up":
            return reject(sig, f"SELL signal against EMA 20/50 (state: up)")

    # --- 3. Do enough strategies agree on ONE direction? ---
    buys = [n for n, d in fired if d == "buy"]
    sells = [n for n, d in fired if d == "sell"]
    if len(buys) >= config.MIN_STRATEGIES_AGREE:
        direction, agreeing = "buy", buys
    elif len(sells) >= config.MIN_STRATEGIES_AGREE:
        direction, agreeing = "sell", sells
    else:
        # something fired but not enough agreement -> show it, mark not approved
        sig.direction = fired[0][1]
        sig.confidence = 55
        sig.status = "watch"
        return reject(sig, f"only {len(fired)} strategy agreed (need "
                           f"{config.MIN_STRATEGIES_AGREE})")

    sig.direction = direction
    sig.strategies = agreeing
    sig.confidence = min(95, 60 + 10 * len(agreeing))   # more agreement = more confidence

    # --- 3b. HTF DAILY FILTER (now actually wired in) -------------------
    # The H4 signal must agree with the Daily trend. Prefer real D1 candles;
    # fall back to resampling the H4 window (needs ~300 H4 bars, else it
    # returns 'none' and passes — so fetching real D1 is strongly preferred).
    daily_bias = daily_trend_from_d1(d1) if d1 is not None else daily_trend_from_h4(df)
    if not agrees(direction, daily_bias):
        return reject(sig, f"against Daily trend (daily={daily_bias})")

    # --- 4. Build the trade plan ---
    _build_plan(sig, df, direction, point)

    # lot size from risk % and stop distance (real point value)
    risk_amount = balance * config.RISK_PCT
    stop_points = abs(sig.entry - sig.stop) / point
    # crude per-point cash value placeholder; refined with real tick value later
    sig.lots = round(max(0.01, risk_amount / max(stop_points, 1) / 10), 2)

    # --- 5. R:R rule ---
    if sig.rr < config.MIN_RR:
        return reject(sig, f"R:R {sig.rr} below minimum {config.MIN_RR}")

    # --- 6. Spread gate ---
    sc = check_spread(sig.entry, sig.stop, spread_points, point)
    sig.spread_points = spread_points
    sig.spread_status = sc.status
    if not spread_ok(sc):
        return reject(sig, sc.message)

    # --- 7. Correlation block ---
    cc = check_correlation(symbol, direction, open_positions)
    if not correlation_ok(cc):
        return reject(sig, cc.message)

    # --- 8. All gates passed ---
    approve(sig)
    sig.reasoning = (f"{', '.join(agreeing)} agree on {direction.upper()} in a "
                     f"{regime['regime']} market (ADX {regime['adx']}, "
                     f"DI dir {regime.get('direction')}, daily {daily_bias}). "
                     f"Spread {sc.status}, correlation clear, within risk limits.")
    return sig
