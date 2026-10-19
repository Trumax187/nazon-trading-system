"""
NAZON — Correlation Block
=========================
Diversification is a lie if your pairs move together. EURUSD and GBPUSD rise
and fall almost in lockstep (both are "sell USD" bets). If NAZON longs BOTH at
1% each, that's not two independent 1% trades — it's effectively ONE ~1.8%
trade in disguise. On a $100 account, that quietly doubles your real exposure
the moment the second trade fires.

This module stops that. Before NAZON approves a NEW signal, it checks the
already-open positions and asks: "would this stack correlated risk in the same
direction?" If yes, it BLOCKS (or warns) the new trade.

Two pieces of correlation to handle:

1) Direct FX correlation — EURUSD vs GBPUSD (both long EUR/GBP = short USD).
   Same direction on correlated pairs = stacking. Opposite direction on
   correlated pairs = roughly a hedge (less of a problem, sometimes pointless).

2) Gold's USD link — XAUUSD usually rises when the USD falls. So "BUY XAUUSD"
   and "SELL USDJPY" are both USD-down bets and DO stack, even though the pairs
   look unrelated on the surface. This is the sneaky one most bots miss.

Correlations aren't fixed — they drift, and they should eventually be measured
from live data. For now we use a sensible static map, clearly labelled, that
you can refine on demo. (That's a real "tune from data" item, not a guess to
agonise over now.)
"""

from dataclasses import dataclass
from typing import Literal


# Pairwise correlation of the 4 NAZON pairs.
# +1 = move together, -1 = move opposite, 0 = unrelated.
# Keyed by frozenset so order doesn't matter. Refine these from demo data.
CORRELATION = {
    frozenset({'EURUSD', 'GBPUSD'}): +0.85,   # strong, same direction
    frozenset({'EURUSD', 'USDJPY'}): -0.65,   # opposite (EUR up = USD down = USDJPY down)
    frozenset({'GBPUSD', 'USDJPY'}): -0.60,
    frozenset({'XAUUSD', 'USDJPY'}): -0.55,   # gold up = USD down = USDJPY down
    frozenset({'XAUUSD', 'EURUSD'}): +0.45,   # both rise when USD falls
    frozenset({'XAUUSD', 'GBPUSD'}): +0.40,
}

# How strong a correlation has to be before NAZON cares.
WARN_ABS = 0.40    # |correlation| >= this -> at least warn
BLOCK_ABS = 0.60   # |correlation| >= this AND risk stacks -> block


@dataclass
class OpenPosition:
    symbol: str
    direction: Literal['buy', 'sell']


@dataclass
class CorrelationCheck:
    status: Literal['pass', 'warn', 'block']
    message: str
    conflicts: list   # list of (symbol, correlation, effect) tuples


def _net_exposure_aligned(corr: float, dir_new: str, dir_open: str) -> bool:
    """
    Do these two positions ADD UP (stack risk) rather than offset?

    Positively correlated pairs stack when traded the SAME direction.
    Negatively correlated pairs stack when traded OPPOSITE directions
    (e.g. BUY XAUUSD + SELL USDJPY are both 'USD down' -> they stack).
    """
    same_direction = (dir_new == dir_open)
    if corr > 0:
        return same_direction
    else:
        return not same_direction


def check_correlation(new_symbol: str,
                      new_direction: str,
                      open_positions: list[OpenPosition]) -> CorrelationCheck:
    """
    Check a proposed new trade against everything already open.

    Returns a CorrelationCheck. 'block' means: don't take this trade, you'd be
    doubling down on risk you already hold.
    """
    conflicts = []
    worst = 0.0

    for pos in open_positions:
        if pos.symbol == new_symbol:
            # Same pair again — that's a scaling/duplicate decision, not
            # correlation. Treat as a hard stack.
            conflicts.append((pos.symbol, 1.0, 'same pair already open'))
            worst = 1.0
            continue

        corr = CORRELATION.get(frozenset({new_symbol, pos.symbol}), 0.0)
        if abs(corr) < WARN_ABS:
            continue  # unrelated enough to ignore

        if _net_exposure_aligned(corr, new_direction, pos.direction):
            effect = (f"stacks risk with {pos.direction.upper()} {pos.symbol} "
                      f"(corr {corr:+.2f})")
            conflicts.append((pos.symbol, corr, effect))
            worst = max(worst, abs(corr))

    if not conflicts:
        return CorrelationCheck('pass',
                                "OK — no correlated exposure already open.",
                                [])

    if worst >= BLOCK_ABS:
        status = 'block'
        head = "BLOCK — this trade stacks correlated risk you already hold:"
    else:
        status = 'warn'
        head = "WARN — some correlated exposure; size down or skip:"

    detail = "; ".join(e for _, _, e in conflicts)
    return CorrelationCheck(status, f"{head} {detail}.", conflicts)


def correlation_ok(check: CorrelationCheck) -> bool:
    """True unless correlation BLOCKS the trade (warn still passes)."""
    return check.status != 'block'
