"""
NAZON — Exit Manager
====================
A signal isn't a trade until it's CLOSED. This module manages a position
after entry: the three take-profit partials, and what happens to the stop.

The plan (3-target swing exit):
  TP1 hit -> close 1/3 of the position, move stop to BREAKEVEN
  TP2 hit -> close another 1/3, trail stop up to TP1
  TP3 hit -> close the final 1/3, trade complete
  Stop hit -> close whatever remains

Why breakeven-at-TP1 (the default):
  Its job is to make sure a winner never becomes a loser. Once TP1 is banked
  and the stop is at entry, the worst case is a small win. That fits NAZON's
  "decide, not feel" rule and protects a small live account. The cost: a normal
  pullback can stop you at breakeven before price runs on. That trade-off is
  right while the edge is unproven — flip MODE to 'breathe' later, once the
  trade journal shows a win rate that justifies wider variance.

This module is pure logic: feed it the current price, it tells you what to do.
It places no orders itself — execution stays separate (so the same logic runs
in backtest, demo, and live untouched).
"""

from dataclasses import dataclass, field
from typing import Literal


MODE: Literal['breakeven', 'breathe'] = 'breakeven'   # NAZON default


@dataclass
class Position:
    """A live NAZON position being managed toward its exits."""
    symbol: str
    direction: Literal['buy', 'sell']
    entry: float
    stop: float
    tp1: float
    tp2: float
    tp3: float
    lots: float                      # total opening size

    # --- state that changes as the trade plays out ---
    open_fraction: float = 1.0       # how much of the position is still open
    stop_now: float = field(default=None)   # current (possibly moved) stop
    tp1_done: bool = False
    tp2_done: bool = False
    tp3_done: bool = False
    closed: bool = False
    _bar_time: object = None   # optional; set by backtester to enable weekend close
    def __post_init__(self):
        if self.stop_now is None:
            self.stop_now = self.stop


def _hit(direction: str, price: float, level: float, is_target: bool) -> bool:
    """
    Did `price` reach `level`?
    For a BUY: targets are above (price >= level), stop is below (price <= level).
    For a SELL: targets are below (price <= level), stop is above (price >= level).
    """
    if direction == 'buy':
        return price >= level if is_target else price <= level
    else:  # sell
        return price <= level if is_target else price >= level


def fill_price(direction: str, level: float, bar_open: float, is_stop: bool) -> float:
    """
    Realistic execution price for a stop or target crossed intrabar. For use
    by anything REPLAYING price history against this module (backtester.py,
    outcome_resolver.py) rather than by update() itself, which only needs to
    know whether a level was touched, not what a real fill would have cost.

    Naively using a candle's raw high/low as the fill price books every
    stop-out at the candle's worst tick and every target at its best tick --
    that's not a real fill (which happens at, or very near, the level itself)
    and it systematically distorts R-multiples on both sides. The one time
    the extreme IS the honest answer is a genuine gap: if the bar's OPEN
    already jumped past the level before the candle started trading, the
    open is the best fill you could actually have gotten.

    Both backtester.py and outcome_resolver.py import this, so historical
    and forward-demo R-multiples are measured the same honest way.
    """
    if direction == 'buy':
        gapped = (bar_open < level) if is_stop else (bar_open > level)
    else:  # sell
        gapped = (bar_open > level) if is_stop else (bar_open < level)
    return bar_open if gapped else level


def update(pos: Position, price: float, mode: str = MODE) -> list[str]:
    """
    Advance the position given the latest price. Returns a list of plain-English
    actions NAZON took this step (for logging / the dashboard / the journal).

    Call this once per closed candle (or per tick if managing live).
    Order of checks matters: we check the STOP first, because if price gapped
    through the stop we must exit before considering any target.
    """
    actions = []
    if pos.closed:
        return actions
    # Weekend close: force exit on Friday late session
    # This prevents holding through weekend gaps.
    # bar_time is passed via a new optional parameter; if absent, skip.
    if hasattr(pos, "_bar_time") and pos._bar_time is not None:
        bt = pos._bar_time
        if bt.weekday() == 4 and bt.hour >= 20:   # Friday 20:00+
            actions.append(f"WEEKEND CLOSE — force exit at {price:.5f}")
            pos.open_fraction = 0.0
            pos.closed = True
            return actions
    # 1) Stop check first — protection before profit.
    if _hit(pos.direction, price, pos.stop_now, is_target=False):
        where = 'breakeven' if abs(pos.stop_now - pos.entry) < 1e-9 else 'stop'
        actions.append(f"STOP hit at {pos.stop_now:.5f} ({where}) — "
                       f"closed remaining {pos.open_fraction:.0%}")
        pos.open_fraction = 0.0
        pos.closed = True
        return actions

    # 2) Targets, in order. Each closes one third.
    if not pos.tp1_done and _hit(pos.direction, price, pos.tp1, is_target=True):
        pos.tp1_done = True
        pos.open_fraction -= 1 / 3
        actions.append(f"TP1 hit at {pos.tp1:.5f} — closed 1/3, "
                       f"{pos.open_fraction:.0%} still open")
        if mode == 'breakeven':
            pos.stop_now = pos.entry
            actions.append(f"Stop moved to BREAKEVEN ({pos.entry:.5f}) — "
                           f"trade is now risk-free")

    if not pos.tp2_done and _hit(pos.direction, price, pos.tp2, is_target=True):
        pos.tp2_done = True
        pos.open_fraction -= 1 / 3
        actions.append(f"TP2 hit at {pos.tp2:.5f} — closed 1/3, "
                       f"{pos.open_fraction:.0%} still open")
        # Trail the stop up to TP1 — lock in more than breakeven.
        pos.stop_now = pos.tp1
        actions.append(f"Stop trailed to TP1 ({pos.tp1:.5f})")

    if not pos.tp3_done and _hit(pos.direction, price, pos.tp3, is_target=True):
        pos.tp3_done = True
        pos.open_fraction = 0.0
        pos.closed = True
        actions.append(f"TP3 hit at {pos.tp3:.5f} — closed final 1/3, "
                       f"trade COMPLETE")

    return actions
