"""
NAZON — Spread Gate
===================
The survival check. Your risk manager sizes a trade from a clean entry and a
stop X points away. But you don't enter at the clean price — you enter across
the SPREAD (the gap between bid and ask). On Gold especially, that spread is
normally small but EXPLODES around news, rollover (server midnight), and
illiquid hours — from ~20 cents to several dollars.

Why it matters to a $100 account:
  If your stop is 70 points away and the spread is 7 points, the spread is
  10% of your stop distance. That means ~10% of your risk is gone the instant
  you enter, before price moves at all. Size on the clean stop and your real
  risk is quietly bigger than the 1% you intended. Do this in a blowout and a
  "1% trade" becomes a 3% trade.

So before NAZON approves ANY trade, it checks the live spread and either:
  - PASS  : spread is small vs the stop -> proceed normally
  - WARN  : spread is getting heavy -> proceed but flag it (and consider
            widening the stop / shrinking size, or just waiting)
  - BLOCK : spread is too wide -> do NOT enter. No trade is better than a
            trade that's mispriced from the first tick.

This module is pure logic. Live spread comes from MT5:
    info = mt5.symbol_info(symbol)
    spread_points = info.spread          # in points
    point = info.point                   # value of one point
Feed those in; NAZON decides.
"""

from dataclasses import dataclass
from typing import Literal


# --- Thresholds as a FRACTION of stop distance (not absolute prices, so the
#     same rule works on Gold and on EURUSD without rewriting). Tune on demo. ---
WARN_RATIO = 0.05     # spread >= 5% of stop distance -> warn
BLOCK_RATIO = 0.10    # spread >= 10% of stop distance -> block

# A hard floor so a tiny stop can't make a normal spread look catastrophic,
# and so we always reject obviously broken/zero data.
MIN_STOP_POINTS = 1


@dataclass
class SpreadCheck:
    status: Literal['pass', 'warn', 'block']
    spread_points: float
    stop_points: float
    ratio: float                 # spread as a fraction of the stop distance
    message: str
    effective_risk_multiplier: float   # how much the spread inflates real risk


def check_spread(entry: float,
                 stop: float,
                 spread_points: float,
                 point: float) -> SpreadCheck:
    """
    Decide whether the live spread is acceptable for this trade.

    entry, stop     : prices (the planned entry and stop)
    spread_points   : current spread in POINTS (from mt5.symbol_info().spread)
    point           : price value of one point (from mt5.symbol_info().point)

    Returns a SpreadCheck the signal engine / card can read directly.
    """
    # Convert everything to points so the comparison is apples-to-apples.
    stop_distance_price = abs(entry - stop)
    stop_points = stop_distance_price / point if point > 0 else 0
    spread_price = spread_points * point

    # Guard against broken data: zero/negative stop distance or missing point.
    if stop_points < MIN_STOP_POINTS or point <= 0:
        return SpreadCheck(
            status='block',
            spread_points=spread_points,
            stop_points=round(stop_points, 1),
            ratio=0.0,
            message="BLOCK — stop distance or point size invalid; cannot size safely.",
            effective_risk_multiplier=0.0,
        )

    ratio = spread_points / stop_points

    # If you size on the clean stop but really risk (stop + spread), your true
    # risk is inflated by roughly this factor.
    effective_risk_multiplier = (stop_distance_price + spread_price) / stop_distance_price

    if ratio >= BLOCK_RATIO:
        status = 'block'
        message = (f"BLOCK — spread is {ratio:.0%} of stop distance "
                   f"({spread_points:.0f} pts vs {stop_points:.0f} pt stop). "
                   f"Real risk ~{effective_risk_multiplier:.2f}x intended. Wait for it to tighten.")
    elif ratio >= WARN_RATIO:
        status = 'warn'
        message = (f"WARN — spread is {ratio:.0%} of stop distance "
                   f"({spread_points:.0f} pts). Real risk ~{effective_risk_multiplier:.2f}x intended. "
                   f"Consider waiting or widening the stop.")
    else:
        status = 'pass'
        message = (f"OK — spread {spread_points:.0f} pts is {ratio:.0%} of stop distance. Negligible.")

    return SpreadCheck(
        status=status,
        spread_points=spread_points,
        stop_points=round(stop_points, 1),
        ratio=round(ratio, 3),
        message=message,
        effective_risk_multiplier=round(effective_risk_multiplier, 2),
    )


def spread_ok(check: SpreadCheck) -> bool:
    """Convenience gate: True unless the spread BLOCKS the trade.
    (A 'warn' still lets the trade through — it's a flag, not a veto.)"""
    return check.status != 'block'
