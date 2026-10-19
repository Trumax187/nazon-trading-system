"""
NAZON — Kill Switch (Circuit Breakers)
======================================
A rule in a comment does nothing. "Stop at 5% daily loss" only protects you if
CODE refuses to approve trades once the limit is hit. This module is that code.

It is the last line of defence for a small live account: it turns one bad day
into a small bad day instead of a blown account. It does NOT predict or improve
anything — its only job is to say NO when a safety limit is breached.

Circuit breakers it enforces:
  1. Daily loss limit   — stop trading once today's realized loss hits X% of
                          the day's starting balance. (Your locked-in 5% rule.)
  2. Consecutive losses — after N losing trades in a row, halt and cool off.
                          (Stops "revenge trading" and a strategy that's clearly
                          out of sync with the market today.)
  3. Max open trades    — never hold more than N positions at once, so total
                          risk is capped no matter what the signals say.
  4. Trading window     — optional: only allow new trades during chosen hours
                          (e.g. avoid the thin, spread-wide rollover period).

When ANY breaker is tripped, no new trade is approved until it resets
(daily breakers reset on a new trading day; you call reset_day() then).
Existing positions are NOT force-closed by this module — managing open trades
is the exit manager's job. This module only gates NEW entries.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal


# --- Limits (tune on demo; keep them here, one place) ---
DAILY_LOSS_LIMIT_PCT = 0.05     # 5% of the day's starting balance
MAX_CONSECUTIVE_LOSSES = 3      # halt after 3 losers in a row
MAX_OPEN_TRADES = 3             # never more than 3 positions at once

# Optional trading window (24h clock, server/local time you standardise on).
# Set ALLOW_ALL_HOURS = True to disable the window entirely.
ALLOW_ALL_HOURS = True
WINDOW_START_HOUR = 6
WINDOW_END_HOUR = 22


@dataclass
class DayState:
    """NAZON's running picture of today. Persist this (journal/DB) so a
    restart doesn't wipe the day's loss count and re-open the floodgates."""
    trading_day: date
    starting_balance: float
    realized_pnl: float = 0.0          # sum of closed-trade P&L today
    consecutive_losses: int = 0
    open_trades: int = 0
    halted_reason: str = ""            # non-empty once a breaker has tripped

    @property
    def loss_pct(self) -> float:
        """Today's loss as a positive fraction of starting balance (0 if up)."""
        if self.starting_balance <= 0:
            return 0.0
        loss = min(self.realized_pnl, 0.0)
        return abs(loss) / self.starting_balance


@dataclass
class GateResult:
    allowed: bool
    reason: str


def can_open_new_trade(state: DayState, now: datetime | None = None) -> GateResult:
    """
    The gate the signal engine calls before approving ANY new entry.
    Returns allowed=False with a plain reason if a breaker is tripped.
    """
    # If already halted today, stay halted.
    if state.halted_reason:
        return GateResult(False, f"HALTED — {state.halted_reason}")

    # 1) Daily loss limit
    if state.loss_pct >= DAILY_LOSS_LIMIT_PCT:
        state.halted_reason = (f"daily loss limit hit "
                               f"({state.loss_pct:.1%} of {DAILY_LOSS_LIMIT_PCT:.0%}) "
                               f"— no more trades today")
        return GateResult(False, f"HALTED — {state.halted_reason}")

    # 2) Consecutive losses
    if state.consecutive_losses >= MAX_CONSECUTIVE_LOSSES:
        state.halted_reason = (f"{state.consecutive_losses} losses in a row "
                               f"— cooling off, no more trades today")
        return GateResult(False, f"HALTED — {state.halted_reason}")

    # 3) Max open trades
    if state.open_trades >= MAX_OPEN_TRADES:
        return GateResult(False, f"BLOCKED — already at max open trades "
                                 f"({state.open_trades}/{MAX_OPEN_TRADES})")

    # 4) Trading window
    if not ALLOW_ALL_HOURS:
        hour = (now or datetime.now()).hour
        if not (WINDOW_START_HOUR <= hour < WINDOW_END_HOUR):
            return GateResult(False, f"BLOCKED — outside trading window "
                                     f"({WINDOW_START_HOUR}:00–{WINDOW_END_HOUR}:00)")

    return GateResult(True, "OK — within all safety limits")


# ---- State updates: call these as trades open and close ----

def register_open(state: DayState) -> None:
    """Call when a new trade is actually entered."""
    state.open_trades += 1


def register_close(state: DayState, pnl: float) -> None:
    """
    Call when a trade closes. pnl is the realized profit/loss in account
    currency (negative = loss). Updates the day's totals and loss streak.
    """
    state.realized_pnl += pnl
    state.open_trades = max(0, state.open_trades - 1)

    if pnl < 0:
        state.consecutive_losses += 1
    elif pnl > 0:
        state.consecutive_losses = 0   # a win breaks the losing streak
    # exactly-breakeven (pnl == 0) leaves the streak unchanged


def reset_day(state: DayState, new_day: date, new_starting_balance: float) -> DayState:
    """
    Start a fresh trading day. Daily breakers clear; this is the ONLY way a
    daily-loss or consecutive-loss halt lifts. Carry nothing toxic across days.
    """
    return DayState(trading_day=new_day, starting_balance=new_starting_balance)
