"""
NAZON — Journal Analytics
=========================
Turns the raw trade log into the few numbers that actually decide
demo -> live -> public. No charts here, just honest arithmetic.

The number that matters most is EXPECTANCY: the average amount NAZON makes
(or loses) per trade, measured in R (units of risk). It answers the only
question that counts: over many trades, does this make money?

    expectancy_R = (win_rate * avg_win_R) - (loss_rate * avg_loss_R)

  > 0  : positive edge — every trade is worth taking on average
  = 0  : breakeven — you're just feeding the spread
  < 0  : negative edge — NAZON loses money over time; do NOT go live

A crucial honesty guard: expectancy from a handful of trades is noise. This
module always reports the SAMPLE SIZE alongside the number and warns when it's
too small to trust. 20-40 demo trades is a hint, not a verdict.
"""

from dataclasses import dataclass

MIN_TRUSTWORTHY_SAMPLE = 30   # below this, treat results as suggestive only


@dataclass
class Performance:
    n: int                 # number of closed trades
    wins: int
    losses: int
    breakevens: int
    win_rate: float        # fraction 0..1
    avg_win_r: float       # average winning trade in R
    avg_loss_r: float      # average losing trade in R (positive number)
    expectancy_r: float    # the headline number, in R per trade
    total_r: float         # cumulative R
    profit_factor: float   # gross win / gross loss (>1 = profitable)
    total_pnl: float       # cumulative cash P&L
    trustworthy: bool      # is n big enough to believe?
    cash_tracked: bool = True   # False when no trade in the sample has real
                                # cash P&L recorded (e.g. NAZON's semi-automated
                                # R-based resolver, which only scores R-multiples
                                # since it never places real orders). When False,
                                # profit_factor is computed from R instead of $,
                                # and total_pnl/cash figures shouldn't be read as
                                # real money.

    def summary(self) -> str:
        verdict = (
            "POSITIVE EDGE" if self.expectancy_r > 0.05 else
            "NEGATIVE EDGE — do not go live" if self.expectancy_r < -0.05 else
            "roughly breakeven"
        )
        trust = "" if self.trustworthy else \
            f"  ⚠ only {self.n} trades — too few to trust yet (need ~{MIN_TRUSTWORTHY_SAMPLE})"
        pf_label = "Profit factor" if self.cash_tracked else "Profit factor (R-based, no cash tracked)"
        cash_str = f"({self.total_pnl:+.2f} cash)" if self.cash_tracked else "(cash not tracked — R-based resolver)"
        return (
            f"Trades: {self.n} ({self.wins}W / {self.losses}L / {self.breakevens}BE)\n"
            f"Win rate:      {self.win_rate:.0%}\n"
            f"Avg win:       +{self.avg_win_r:.2f}R   Avg loss: -{self.avg_loss_r:.2f}R\n"
            f"Expectancy:    {self.expectancy_r:+.3f}R per trade   ->  {verdict}\n"
            f"{pf_label}: {self.profit_factor:.2f}\n"
            f"Total:         {self.total_r:+.1f}R  {cash_str}"
            f"{trust}"
        )


def _performance_from_rows(rows) -> Performance:
    """Compute Performance from closed-trade rows (each needs r_multiple, pnl, outcome)."""
    closed = [r for r in rows if r["outcome"] in ("win", "loss", "breakeven")
              and r["r_multiple"] is not None]
    n = len(closed)
    if n == 0:
        return Performance(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, False, True)

    wins = [r for r in closed if r["outcome"] == "win"]
    losses = [r for r in closed if r["outcome"] == "loss"]
    bes = [r for r in closed if r["outcome"] == "breakeven"]

    win_rate = len(wins) / n
    loss_rate = len(losses) / n

    avg_win_r = sum(r["r_multiple"] for r in wins) / len(wins) if wins else 0.0
    avg_loss_r = abs(sum(r["r_multiple"] for r in losses) / len(losses)) if losses else 0.0

    expectancy_r = (win_rate * avg_win_r) - (loss_rate * avg_loss_r)
    total_r = sum(r["r_multiple"] for r in closed)
    total_pnl = sum((r["pnl"] or 0) for r in closed)

    gross_win_cash = sum(r["pnl"] for r in wins if r["pnl"]) or 0.0
    gross_loss_cash = abs(sum(r["pnl"] for r in losses if r["pnl"])) or 0.0

    if gross_win_cash > 0 or gross_loss_cash > 0:
        # Real cash P&L is present for at least some trades (a live/demo path
        # that actually places orders and records broker fills) — use it,
        # it's the ground truth over R approximations.
        cash_tracked = True
        profit_factor = (gross_win_cash / gross_loss_cash) if gross_loss_cash > 0 else float("inf")
    else:
        # No cash P&L recorded at all. This is expected for NAZON's
        # semi-automated outcome_resolver, which only ever scores R-multiples
        # and intentionally never places real orders. Showing cash-based
        # "inf" here would be meaningless, not informative — fall back to
        # an R-based profit factor instead, which reflects reality.
        cash_tracked = False
        gross_win_r = sum(r["r_multiple"] for r in wins if r["r_multiple"] and r["r_multiple"] > 0)
        gross_loss_r = abs(sum(r["r_multiple"] for r in losses if r["r_multiple"] and r["r_multiple"] < 0))
        profit_factor = (gross_win_r / gross_loss_r) if gross_loss_r > 0 else float("inf")

    return Performance(
        n=n, wins=len(wins), losses=len(losses), breakevens=len(bes),
        win_rate=win_rate, avg_win_r=avg_win_r, avg_loss_r=avg_loss_r,
        expectancy_r=expectancy_r, total_r=total_r,
        profit_factor=round(profit_factor, 2) if profit_factor != float("inf") else float("inf"),
        total_pnl=total_pnl,
        trustworthy=(n >= MIN_TRUSTWORTHY_SAMPLE),
        cash_tracked=cash_tracked,
    )


def overall(conn) -> Performance:
    """Performance across all closed trades."""
    rows = conn.execute("SELECT * FROM trades WHERE closed_ts IS NOT NULL").fetchall()
    return _performance_from_rows(rows)


def by_strategy(conn) -> dict[str, Performance]:
    """
    Performance grouped by strategy. A trade can list multiple strategies
    (they agreed), so it counts toward each — this tells you which strategy
    is carrying NAZON and which is dragging it down.
    """
    rows = conn.execute("SELECT * FROM trades WHERE closed_ts IS NOT NULL").fetchall()
    buckets: dict[str, list] = {}
    for r in rows:
        for strat in (r["strategies"] or "").split(","):
            strat = strat.strip()
            if strat:
                buckets.setdefault(strat, []).append(r)
    return {s: _performance_from_rows(rs) for s, rs in buckets.items()}


def by_symbol(conn) -> dict[str, Performance]:
    """Performance per pair — shows if one pair is dragging the system."""
    rows = conn.execute("SELECT * FROM trades WHERE closed_ts IS NOT NULL").fetchall()
    buckets: dict[str, list] = {}
    for r in rows:
        buckets.setdefault(r["symbol"], []).append(r)
    return {s: _performance_from_rows(rs) for s, rs in buckets.items()}


def rejection_breakdown(conn) -> dict[str, int]:
    """
    Count WHY signals were rejected. If one gate blocks almost everything,
    it may be too strict — this is how you'd find out on demo.
    """
    rows = conn.execute(
        "SELECT reject_reason FROM signals WHERE approved=0 AND reject_reason!=''"
    ).fetchall()
    counts: dict[str, int] = {}
    for r in rows:
        # bucket by the leading keyword (HALTED / BLOCK / WARN / regime / etc.)
        key = r["reject_reason"].split("—")[0].split("(")[0].strip()[:40] or "other"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))
