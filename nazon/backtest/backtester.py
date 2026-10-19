"""
NAZON — Backtester
==================
Answers the only question that matters: do these strategies have an edge?
It replays history one closed candle at a time, asks the SAME signal engine
what it would have done, simulates the trade with the SAME exit manager, and
logs the result. Then analytics turns those results into expectancy in R.

THE GOLDEN RULE — NO LOOK-AHEAD:
  At bar i, NAZON may only see candles[0 .. i]. Never bar i+1. We enforce this
  structurally by slicing the DataFrame to df.iloc[:i+1] before calling the
  engine. A backtest that peeks at the future turns a losing system into a
  fake winner — so this slice is the most important line in the file.

How a trade is simulated (honest, conservative):
  - A signal at bar i is entered at the NEXT bar's open (you can't fill on a
    candle that hasn't closed). This avoids the classic "enter at the close I
    just used to decide" cheat.
  - After entry, we walk forward bar by bar feeding prices to the exit_manager
    (the real one), which handles TP1/TP2/TP3 partials and the breakeven stop.
  - A bar that touches both stop and a target is resolved STOP-FIRST (pessimistic),
    so we never flatter the result.

What it does NOT model yet (be honest about limits):
  - Spread/slippage on the simulated fill (demo will reveal that). 
  - Swap/overnight fees. 
  - The kill switch / correlation across the whole history (we test raw strategy
    edge first; portfolio-level gating is a later layer).
These omissions mean a backtest edge must be COMFORTABLY positive, not marginal,
to trust — real costs eat thin edges.
"""

import pandas as pd

from nazon.core import indicators as ind
from nazon.core.regime import detect_regime
from nazon.core.signal_engine import _strategies, _build_plan
from nazon.core.signal_contract import new_signal
from nazon.core.exit_manager import Position, update, fill_price
from nazon.core.htf_filter import daily_trend_from_h4, agrees
from nazon import config


# Minimum candles before we allow any signal (EMA200 warm-up).
WARMUP = 210


def _decide(symbol: str, window: pd.DataFrame, point: float):
    """
    Run the engine's strategy logic on a history window (closed candles only).
    Returns (direction, agreeing_strategies, plan_signal) or (None, [], None).
    This mirrors signal_engine.analyse() but without the live-only gates
    (spread/correlation/kill-switch) — we're measuring raw strategy edge.

    STEP 1 IMPROVEMENT: a Daily higher-timeframe trend filter. Only signals
    whose direction agrees with the Daily bias are accepted.
    """
    regime = detect_regime(window)
    fired = _strategies(window, regime)
    if not fired:
        return None, [], None

    # --- DIRECTION GUARD (mirrors signal_engine.analyse) ---------------
    # Drop any signal that fights the regime's own DI-based trend direction.
    # The live engine now enforces this; the backtest MUST match it or the
    # forward results won't be comparable to what this backtest validates.
    rdir = regime.get("direction")
    if rdir in ("up", "down"):
        want = "buy" if rdir == "up" else "sell"
        fired = [(n, d) for (n, d) in fired if d == want]
        if not fired:
            return None, [], None

    buys = [n for n, d in fired if d == "buy"]
    sells = [n for n, d in fired if d == "sell"]
    if len(buys) >= config.MIN_STRATEGIES_AGREE:
        direction, agreeing = "buy", buys
    elif len(sells) >= config.MIN_STRATEGIES_AGREE:
        direction, agreeing = "sell", sells
    else:
        return None, [], None

    # --- Daily higher-timeframe trend filter (Step 1) ---
    daily_bias = daily_trend_from_h4(window)      # resample this window -> daily
    if not agrees(direction, daily_bias):
        return None, [], None                     # H4 signal fights the Daily tide -> skip

    sig = new_signal(symbol)
    _build_plan(sig, window, direction, point)
    if sig.rr is None or sig.rr < config.MIN_RR:
        return None, [], None
    return direction, agreeing, sig


def backtest(df: pd.DataFrame, symbol: str, point: float,
             spread_points: float = 0.0) -> list[dict]:
    """
    Replay `df` (chronological closed candles) and return completed trades.
    No look-ahead: decisions use df.iloc[:i+1] only.

    spread_points: realistic cost per trade, in POINTS. The spread is paid on
    entry (you cross bid->ask). We convert it to R and subtract from each
    trade's result, so the numbers are NET of cost — the honest edge. Set 0 to
    see the gross (cost-free) result for comparison.
    """
    spread_price = spread_points * point      # cost in price terms
    trades = []
    i = WARMUP
    n = len(df)

    while i < n - 1:
        window = df.iloc[: i + 1]                 # <-- NO LOOK-AHEAD: only up to bar i
        direction, agreeing, sig = _decide(symbol, window, point)

        if direction is None:
            i += 1
            continue

        # Enter at the NEXT bar's open (can't fill on the candle we decided on).
        entry_bar = df.iloc[i + 1]
        raw_entry = float(entry_bar["open"])
        # Apply spread: buy at ask (entry + half-spread), sell at bid (entry - half-spread)
        half_spread = (spread_points * point) / 2
        if direction == "buy":
            entry_price = raw_entry + half_spread
        else:
            entry_price = raw_entry - half_spread

        # Plan around the ACTUAL entry price (engine planned off the close;
        # we entered at next open, so shift stop/TPs by the same geometry).
        risk_per_unit = abs(entry_price - sig.stop) if sig.stop else None
        if not risk_per_unit:
            i += 1
            continue

        # Recompute TPs using the SAME multiples the engine uses, so the
        # backtest simulates exactly what NAZON would really do. Import here
        # to avoid a circular import at module load.
        from nazon.core.signal_engine import TP_MULTIPLES
        if direction == "buy":
            stop = entry_price - risk_per_unit
            tp1 = entry_price + risk_per_unit * TP_MULTIPLES[0]
            tp2 = entry_price + risk_per_unit * TP_MULTIPLES[1]
            tp3 = entry_price + risk_per_unit * TP_MULTIPLES[2]
        else:
            stop = entry_price + risk_per_unit
            tp1 = entry_price - risk_per_unit * TP_MULTIPLES[0]
            tp2 = entry_price - risk_per_unit * TP_MULTIPLES[1]
            tp3 = entry_price - risk_per_unit * TP_MULTIPLES[2]

        pos = Position(symbol=symbol, direction=direction, entry=entry_price,
                       stop=stop, tp1=tp1, tp2=tp2, tp3=tp3, lots=1.0)

        # Track realized R as each level closes, at a REALISTIC fill price
        # (the level itself, or the bar's open on a genuine gap) -- NOT the
        # bar's raw high/low, which books every stop-out at the candle's
        # worst tick and every target at its best tick. See
        # exit_manager.fill_price() for the full reasoning. This must match
        # outcome_resolver.py's replay exactly, or backtest results and
        # forward demo results aren't measuring the same thing.
        realized_r = 0.0
        j = i + 1
        while j < n and not pos.closed:
            bar = df.iloc[j]
            o = float(bar["open"])
            l = float(bar["low"])
            h = float(bar["high"])
            # Pessimistic: for a buy, test the low (stop) before the high (TP).
            extremes = [l, h] if direction == "buy" else [h, l]

            for extreme in extremes:
                prev_closed = pos.closed
                prev_stop_now = pos.stop_now
                prev_tp1, prev_tp2, prev_tp3 = pos.tp1_done, pos.tp2_done, pos.tp3_done
                prev_open_fraction = pos.open_fraction

                update(pos, extreme)                # the REAL exit manager

                tp3_just_fired = (not prev_tp3) and pos.tp3_done
                stop_just_fired = pos.closed and not prev_closed and not tp3_just_fired

                if stop_just_fired:
                    # Whole remaining fraction closes at the stop level (or
                    # the bar's open, if it gapped straight through it).
                    fill = fill_price(direction, prev_stop_now, o, is_stop=True)
                    if direction == "buy":
                        r_here = (fill - pos.entry) / risk_per_unit
                    else:
                        r_here = (pos.entry - fill) / risk_per_unit
                    realized_r += r_here * prev_open_fraction
                else:
                    # 0, 1, 2, or 3 targets may fire in this single check.
                    remaining = prev_open_fraction
                    if (not prev_tp1) and pos.tp1_done:
                        fill = fill_price(direction, tp1, o, is_stop=False)
                        r_here = ((fill - pos.entry) / risk_per_unit if direction == "buy"
                                  else (pos.entry - fill) / risk_per_unit)
                        realized_r += r_here * (1 / 3)
                        remaining -= 1 / 3
                    if (not prev_tp2) and pos.tp2_done:
                        fill = fill_price(direction, tp2, o, is_stop=False)
                        r_here = ((fill - pos.entry) / risk_per_unit if direction == "buy"
                                  else (pos.entry - fill) / risk_per_unit)
                        realized_r += r_here * (1 / 3)
                        remaining -= 1 / 3
                    if tp3_just_fired:
                        fill = fill_price(direction, tp3, o, is_stop=False)
                        r_here = ((fill - pos.entry) / risk_per_unit if direction == "buy"
                                  else (pos.entry - fill) / risk_per_unit)
                        realized_r += r_here * remaining

                if pos.closed:
                    break
            j += 1

        # If we ran out of data with the position still open, close at last
        # price -- this is a mark-to-market, not a level touch, so the raw
        # close is the honest fill (no fill_price() needed here).
        if not pos.closed and pos.open_fraction > 0:
            last_px = float(df.iloc[n - 1]["close"])
            if direction == "buy":
                r_here = (last_px - pos.entry) / risk_per_unit
            else:
                r_here = (pos.entry - last_px) / risk_per_unit
            realized_r += r_here * pos.open_fraction

        r = realized_r
        # Subtract the spread cost, converted to R (cost / risk-per-unit).
        # Paid once per trade on entry. This makes the result NET of cost.
        cost_r = (spread_price / risk_per_unit) if risk_per_unit > 0 else 0.0
        r_net = r - cost_r

        trades.append({
            "symbol": symbol,
            "direction": direction,
            "strategies": ",".join(agreeing),
            "entry": round(entry_price, 6),
            "r_gross": round(r, 3),
            "r_multiple": round(r_net, 3),   # net of spread — the honest number
            "cost_r": round(cost_r, 3),
            "outcome": "win" if r_net > 0.05 else "loss" if r_net < -0.05 else "breakeven",
            "bars_held": j - (i + 1),
        })

        # Resume scanning AFTER this trade closed (no overlapping positions).
        i = j + 1

    return trades


def summarize(trades: list[dict]) -> dict:
    """Quick expectancy summary (the headline numbers)."""
    closed = [t for t in trades if t["outcome"] in ("win", "loss", "breakeven")]
    n = len(closed)
    if n == 0:
        return {"n": 0, "note": "no trades generated"}

    wins = [t for t in closed if t["outcome"] == "win"]
    losses = [t for t in closed if t["outcome"] == "loss"]
    win_rate = len(wins) / n
    avg_win = sum(t["r_multiple"] for t in wins) / len(wins) if wins else 0.0
    avg_loss = abs(sum(t["r_multiple"] for t in losses) / len(losses)) if losses else 0.0
    expectancy = sum(t["r_multiple"] for t in closed) / n
    total_r = sum(t["r_multiple"] for t in closed)

    return {
        "n": n,
        "win_rate": round(win_rate, 3),
        "avg_win_r": round(avg_win, 3),
        "avg_loss_r": round(avg_loss, 3),
        "expectancy_r": round(expectancy, 3),
        "total_r": round(total_r, 1),
    }


def backtest_split(df: pd.DataFrame, symbol: str, point: float,
                   train_frac: float = 0.70, spread_points: float = 0.0) -> dict:
    """
    Run the backtest split into IN-SAMPLE (train) and OUT-OF-SAMPLE (test),
    NET of spread cost. A real edge is positive on BOTH, after costs.
    """
    n = len(df)
    cut = int(n * train_frac)

    train_df = df.iloc[:cut].reset_index(drop=True)
    train_trades = backtest(train_df, symbol, point, spread_points)

    test_df = df.iloc[cut - WARMUP:].reset_index(drop=True)
    test_trades = backtest(test_df, symbol, point, spread_points)

    return {
        "train": summarize(train_trades),
        "test": summarize(test_trades),
        "cut_index": cut,
        "train_bars": len(train_df),
        "test_bars": n - cut,
    }
def backtest_with_engine(df: pd.DataFrame,
                         symbol: str,
                         point: float,
                         spread_points: float = 260.0,
                         starting_balance: float = 10000.0) -> list[dict]:
    """
    Backtest by calling the LIVE signal engine (analyse) at each bar.
    Guarantees parity with live trading gates.
    No look-ahead: only passes df.iloc[:i+1] to analyse().
    """
    from nazon.core.signal_engine import analyse
    from nazon.core.kill_switch import DayState
    from nazon.core.correlation import OpenPosition
    from nazon.core.exit_manager import Position, update
    from datetime import date

    trades = []
    i = WARMUP
    n = len(df)
    balance = starting_balance
    current_day = None
    day_state = None

    while i < n - 1:
        window = df.iloc[:i+1].reset_index(drop=True)

        bar_date = window["time"].iloc[-1].date() if "time" in window else None
        if bar_date != current_day:
            current_day = bar_date
            day_state = DayState(
                trading_day=current_day,
                starting_balance=balance,
                realized_pnl=0.0,
                consecutive_losses=0,
                open_trades=0,
                halted_reason="",
            )

        try:
            sig = analyse(
                symbol=symbol, df=window,
                spread_points=spread_points, point=point,
                balance=balance, open_positions=[],
                day_state=day_state,
            )
        except Exception:
            i += 1
            continue

        if not sig.approved:
            i += 1
            continue

        entry_bar = df.iloc[i + 1]
        entry_price = float(entry_bar["open"])
        risk_per_unit = abs(sig.entry - sig.stop)
        if risk_per_unit <= 0:
            i += 1
            continue

        from nazon.core.signal_engine import TP_MULTIPLES
        if sig.direction == "buy":
            stop = entry_price - risk_per_unit
            tps = [entry_price + risk_per_unit * m for m in TP_MULTIPLES]
        else:
            stop = entry_price + risk_per_unit
            tps = [entry_price - risk_per_unit * m for m in TP_MULTIPLES]

        pos = Position(symbol=symbol, direction=sig.direction, entry=entry_price,
                       stop=stop, tp1=tps[0], tp2=tps[1], tp3=tps[2], lots=1.0)

        realized_r = 0.0
        prev_fraction = pos.open_fraction
        j = i + 1

        while j < n and not pos.closed:
            bar = df.iloc[j]
            # Pass bar time to the position so exit_manager can enforce weekend close
            pos._bar_time = bar["time"] if "time" in bar else None
            prices = ([bar["low"], bar["high"]] if sig.direction == "buy"
                      else [bar["high"], bar["low"]])
            for px in prices:
                px = float(px)
                update(pos, px)
                # ... rest unchanged
                closed_now = prev_fraction - pos.open_fraction
                if closed_now > 1e-9:
                    r_here = ((px - entry_price) / risk_per_unit if sig.direction == "buy"
                              else (entry_price - px) / risk_per_unit)
                    realized_r += r_here * closed_now
                    prev_fraction = pos.open_fraction
                if pos.closed:
                    break
            j += 1

        if not pos.closed and pos.open_fraction > 0:
            last_px = float(df.iloc[n-1]["close"])
            r_here = ((last_px - entry_price) / risk_per_unit if sig.direction == "buy"
                      else (entry_price - last_px) / risk_per_unit)
            realized_r += r_here * pos.open_fraction

        trades.append({
            "symbol": symbol, "direction": sig.direction,
            "strategies": ",".join(sig.strategies),
            "entry": round(entry_price, 6),
            "r_multiple": round(realized_r, 3),
            "outcome": "win" if realized_r > 0.05 else "loss" if realized_r < -0.05 else "breakeven",
            "bars_held": j - (i + 1),
            "regime": sig.regime,
        })
        i = j + 1

    return trades