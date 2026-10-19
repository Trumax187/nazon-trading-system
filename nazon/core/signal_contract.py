"""
NAZON — Signal Contract
=======================
The single agreed shape of a NAZON signal. The engine FILLS it; the dashboard
card and the trade journal READ it. Because everyone speaks this one structure,
no module has to guess another's field names, and changing the analysis never
breaks the display or the log.

Think of it as the form NAZON fills out for every pair, every scan:
  - what it found (direction, confidence, the strategies that agreed)
  - the actual trade plan (entry, stop, three TPs, lot size, R:R)
  - what the market looked like (regime, spread status)
  - the verdict (approved or not) and the plain-English reason why
  - the reasoning paragraph (later: written by Claude Haiku)

A dataclass (not a bare dict) so typos become errors instead of silent bugs,
and so every signal is guaranteed to have every field.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Literal, Optional


@dataclass
class Signal:
    # ---- identity ----
    symbol: str                       # e.g. "XAUUSDm"
    timestamp: str                    # ISO time of the scan
    label: str = ""                   # human name, e.g. "Gold vs US Dollar"

    # ---- the finding ----
    direction: Literal["buy", "sell", "none"] = "none"
    confidence: int = 0               # 0..100
    strategies: list[str] = field(default_factory=list)   # which fired & agreed

    # ---- the trade plan ----
    entry: Optional[float] = None     # entry price (or zone midpoint)
    entry_low: Optional[float] = None # entry zone bounds (optional)
    entry_high: Optional[float] = None
    stop: Optional[float] = None
    tp1: Optional[float] = None
    tp2: Optional[float] = None
    tp3: Optional[float] = None
    lots: Optional[float] = None
    rr: Optional[float] = None        # reward:risk to TP1 (or blended)

    # ---- market context ----
    regime: str = ""                  # "trending" / "ranging" / "transition"
    regime_adx: Optional[float] = None
    spread_points: Optional[int] = None
    spread_status: Literal["pass", "warn", "block", ""] = ""

    # ---- the verdict ----
    approved: bool = False
    status: Literal["approved", "not_approved", "watch", "error"] = "not_approved"
    reject_reason: str = ""           # which gate failed, plain English

    # ---- explanation ----
    reasoning: str = ""               # paragraph; later filled by Claude Haiku

    # ---- helpers ----

    def to_dict(self) -> dict:
        """Flat dict — for the journal (log_signal) and any JSON output."""
        return asdict(self)

    def one_line(self) -> str:
        """Compact human summary, handy for console scans & logging."""
        if self.status == "approved":
            tag = "APPROVED"
        elif self.status == "watch":
            tag = "WATCH"
        elif self.status == "error":
            tag = "ERROR"
        else:
            tag = "not approved"
        dir_txt = self.direction.upper() if self.direction != "none" else "—"
        return (f"{self.symbol:9s} {dir_txt:4s} {self.confidence:3d}%  "
                f"[{tag}] {self.reject_reason or self.reasoning[:40]}")


def new_signal(symbol: str, label: str = "") -> Signal:
    """
    Start a fresh signal for a symbol at the current time. The engine then
    fills in the rest as it runs each gate. Centralising creation here means
    the timestamp format is always consistent.
    """
    return Signal(
        symbol=symbol,
        label=label,
        timestamp=datetime.now().isoformat(timespec="seconds"),
    )


def reject(sig: Signal, reason: str) -> Signal:
    """
    Mark a signal as not approved, with the reason. Used whenever a gate
    blocks the trade (regime, <2 strategies, spread, correlation, kill switch).
    Returns the same signal for convenient chaining.
    """
    sig.approved = False
    sig.status = "not_approved"
    sig.reject_reason = reason
    return sig


def approve(sig: Signal) -> Signal:
    """Mark a signal as a fully approved, tradeable setup."""
    sig.approved = True
    sig.status = "approved"
    sig.reject_reason = ""
    return sig
