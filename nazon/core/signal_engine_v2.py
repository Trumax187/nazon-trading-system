"""
NAZON — Signal Engine v2 (Context-Based)
==========================================
Rebuilds the signal engine to use market context (trend, regime, S/R, ATR)
and produce a confidence score based on how many factors align.

Output format:
    {
        'direction': 'buy' | 'sell' | 'wait',
        'confidence': 0-100,
        'entry': price,
        'stop': price,
        'tp1': price, 'tp2': price, 'tp3': price,
        'lots': size,
        'reasoning': str,
        'factors': list of factors that contributed,
    }
"""

import pandas as pd
from nazon.core import indicators as ind
from nazon.core.regime import detect_regime
from nazon.core.htf_filter import daily_trend_from_h4
from nazon import config


# ── Confidence weights (recalibrated Oct 2026) ──────────────────
# ADX and S/R are the real edge. Trend and daily are too easy to
# satisfy, so they get less weight. This shifts trades from the
# 80+ bucket (which lost money) to the 70-80 bucket (which made +0.341R).
WEIGHT_TREND = 15
WEIGHT_DAILY = 15
WEIGHT_ADX = 25
WEIGHT_RSI = 10
WEIGHT_SR = 20
WEIGHT_ATR = 10
WEIGHT_SPREAD = 5


def _calculate_confidence(ctx: dict, direction: str, spread_points: float) -> tuple[int, list[str]]:
    """
    Score the setup from 0-100 based on how many factors align.
    Returns (score, list of factors that contributed).
    """
    score = 0
    factors = []
    
    # 1. Trend alignment
    if direction == 'buy' and ctx['trend'] == 'up':
        score += WEIGHT_TREND
        factors.append(f"+{WEIGHT_TREND} trend UP (price > EMA200)")
    elif direction == 'sell' and ctx['trend'] == 'down':
        score += WEIGHT_TREND
        factors.append(f"+{WEIGHT_TREND} trend DOWN (price < EMA200)")
    else:
        factors.append(f"+0 trend against signal")
    
    # 2. Daily bias alignment (20 points)
    if direction == 'buy' and ctx['daily_bias'] == 'up':
        score += WEIGHT_DAILY
        factors.append(f"+{WEIGHT_DAILY} Daily bias UP")
    elif direction == 'sell' and ctx['daily_bias'] == 'down':
        score += WEIGHT_DAILY
        factors.append(f"+{WEIGHT_DAILY} Daily bias DOWN")
    else:
        factors.append(f"+0 Daily bias against signal")
    
    # 3. Regime (20 points)
    if ctx['regime'] == 'trending':
        score += WEIGHT_ADX
        factors.append(f"+{WEIGHT_ADX} ADX {ctx['adx']} (trending)")
    elif ctx['regime'] == 'ranging':
        factors.append(f"+0 ADX {ctx['adx']} (ranging)")
    else:
        factors.append(f"+0 ADX {ctx['adx']} (transition)")
    
    # 4. RSI healthy (10 points)
    if 30 <= ctx['rsi'] <= 70:
        score += WEIGHT_RSI
        factors.append(f"+{WEIGHT_RSI} RSI {ctx['rsi']} (healthy)")
    else:
        factors.append(f"+0 RSI {ctx['rsi']} (extreme)")
    
    # 5. Price near S/R (15 points)
    atr = ctx['atr']
    if atr > 0:
        if direction == 'buy':
            for level in ctx['support']:
                if abs(ctx['price'] - level) / atr < 1.0:
                    score += WEIGHT_SR
                    factors.append(f"+{WEIGHT_SR} price near support {level}")
                    break
        else:
            for level in ctx['resistance']:
                if abs(ctx['price'] - level) / atr < 1.0:
                    score += WEIGHT_SR
                    factors.append(f"+{WEIGHT_SR} price near resistance {level}")
                    break
    
    # 6. ATR normal (10 points)
    if atr > 0:
        # Normal for Gold: 15-35 ATR
        if 10 <= atr <= 40:
            score += WEIGHT_ATR
            factors.append(f"+{WEIGHT_ATR} ATR {atr} (normal)")
        else:
            factors.append(f"+0 ATR {atr} (extreme)")
    
    # 7. Spread acceptable (5 points)
    if spread_points <= 300:
        score += WEIGHT_SPREAD
        factors.append(f"+{WEIGHT_SPREAD} spread {spread_points} (acceptable)")
    else:
        factors.append(f"+0 spread {spread_points} (too wide)")
    
    return score, factors


def generate_signal(ctx: dict, spread_points: float, 
                    balance: float, risk_pct: float = 0.01) -> dict:
    """
    Generate a signal from market context.
    Returns a dict ready to be formatted or logged.
    """
    # Default: wait
    result = {
        'direction': 'wait',
        'confidence': 0,
        'entry': None,
        'stop': None,
        'tp1': None, 'tp2': None, 'tp3': None,
        'lots': None,
        'reasoning': '',
        'factors': [],
    }
    
    # Determine candidate direction from trend
    if ctx['trend'] == 'up' and ctx['daily_bias'] == 'up':
        candidate_dir = 'buy'
    elif ctx['trend'] == 'down' and ctx['daily_bias'] == 'down':
        candidate_dir = 'sell'
    else:
        result['reasoning'] = f"Trend ({ctx['trend']}) and Daily ({ctx['daily_bias']}) disagree — no trade"
        return result
    
    # Calculate confidence
    confidence, factors = _calculate_confidence(ctx, candidate_dir, spread_points)

    # HARD VETO: No trades in ranging markets
    if ctx['regime'] == 'ranging':
        result['confidence'] = confidence
        result['factors'] = factors
        result['reasoning'] = f"ADX {ctx['adx']} — ranging market, no trade"
        return result
    
    # HARD VETO: No trades in the transition zone (ADX 20-30)
    # The walk-forward showed this zone is where most losses happen.
    if 20 < ctx['adx'] < 30:
        result['confidence'] = confidence
        result['factors'] = factors
        result['reasoning'] = f"ADX {ctx['adx']} — transition zone (20-30), no trade"
        return result
    
    # If confidence too low, wait
    if confidence < 70:
        result['confidence'] = confidence
        result['factors'] = factors
        result['reasoning'] = f"Confidence {confidence}/100 below 70 — wait"
        return result
    
    # If confidence too high, SKIP
    if confidence > 80:
        result['confidence'] = confidence
        result['factors'] = factors
        result['reasoning'] = f"Confidence {confidence}/100 above 80 — market extended, reversal likely"
        return result
    
    # If confidence too high, SKIP (market too extended)
    if confidence >= 85:
        result['confidence'] = confidence
        result['factors'] = factors
        result['reasoning'] = f"Confidence {confidence}/100 too high — market extended, reversal likely"
        return result
    
    # Build trade levels
    entry = ctx['price']
    atr = ctx['atr']
    if atr <= 0:
        result['reasoning'] = "ATR invalid — cannot size trade"
        return result
    
    if candidate_dir == 'buy':
        # Stop: 1.5 ATR below, or below nearest support (whichever is higher)
        stop_by_atr = entry - (atr * 1.5)
        stop_by_sr = None
        for level in ctx['support']:
            if level < entry:
                stop_by_sr = level - (atr * 0.3)
                break
        stop = max(stop_by_atr, stop_by_sr) if stop_by_sr else stop_by_atr
        
        risk = entry - stop
        if risk <= 0:
            result['reasoning'] = "Invalid risk distance"
            return result
        
        tp1 = entry + (risk * 1.5)
        tp2 = entry + (risk * 2.5)
        tp3 = entry + (risk * 4.0)
    else:
        stop_by_atr = entry + (atr * 1.5)
        stop_by_sr = None
        for level in ctx['resistance']:
            if level > entry:
                stop_by_sr = level + (atr * 0.3)
                break
        stop = min(stop_by_atr, stop_by_sr) if stop_by_sr else stop_by_atr
        
        risk = stop - entry
        if risk <= 0:
            result['reasoning'] = "Invalid risk distance"
            return result
        
        tp1 = entry - (risk * 1.5)
        tp2 = entry - (risk * 2.5)
        tp3 = entry - (risk * 4.0)
    
    # Position sizing
    risk_amount = balance * risk_pct
    stop_points = abs(entry - stop)
    lots = round(max(0.01, risk_amount / (stop_points * 100)), 2)
    
    # Reason
    reasons = []
    if ctx['trend'] == candidate_dir.replace('buy', 'up').replace('sell', 'down'):
        reasons.append(f"trend {ctx['trend']}")
    if ctx['daily_bias'] == candidate_dir.replace('buy', 'up').replace('sell', 'down'):
        reasons.append(f"daily {ctx['daily_bias']}")
    if ctx['regime'] == 'trending':
        reasons.append(f"ADX {ctx['adx']}")
    
    result['direction'] = candidate_dir
    result['confidence'] = confidence
    result['entry'] = round(entry, 5)
    result['stop'] = round(stop, 5)
    result['tp1'] = round(tp1, 5)
    result['tp2'] = round(tp2, 5)
    result['tp3'] = round(tp3, 5)
    result['lots'] = lots
    result['factors'] = factors
    result['reasoning'] = f"{candidate_dir.upper()} setup: {', '.join(reasons)}"
    
    return result


def format_signal(ctx: dict, signal: dict) -> str:
    """Format the signal as readable output."""
    lines = [
        f"=== NAZON SIGNAL: {ctx['symbol']} ===",
        f"Direction:   {signal['direction'].upper()}",
        f"Confidence:  {signal['confidence']}/100",
        f"Price:       {ctx['price']}",
        "",
        "Context:",
        f"- Trend:       {ctx['trend'].upper()}",
        f"- Daily:       {ctx['daily_bias'].upper()}",
        f"- Regime:      {ctx['regime'].upper()} (ADX {ctx['adx']})",
        f"- RSI:         {ctx['rsi']}",
        f"- ATR:         {ctx['atr']}",
    ]
    
    if signal['direction'] != 'wait':
        lines.extend([
            "",
            "Trade Plan:",
            f"- Entry:       {signal['entry']}",
            f"- Stop:        {signal['stop']}",
            f"- TP1:         {signal['tp1']} (1.5R)",
            f"- TP2:         {signal['tp2']} (2.5R)",
            f"- TP3:         {signal['tp3']} (4.0R)",
            f"- Lots:        {signal['lots']}",
            "",
            "Factors:",
        ])
        for f in signal['factors']:
            lines.append(f"  {f}")
    
    lines.extend([
        "",
        f"Reason: {signal['reasoning']}",
    ])
    
    return "\n".join(lines)