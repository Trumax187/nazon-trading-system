"""
NAZON — Outcome Resolver (Fixed)
==================================
Closes the loop for the demo phase. Walks candles AFTER each approved signal
and records the actual exit time, price, and R-multiple.

FIXED: now records actual exit timestamp (not batch-stamped at run time).
"""

import pandas as pd
from datetime import datetime

from nazon.core.exit_manager import Position, update, fill_price
from nazon.core.signal_engine import TP_MULTIPLES
from nazon import config


MAX_BARS_OPEN = 60


def _candles_after(symbol: str, after_time: datetime, max_bars: int = 200):
    """Pull H4 candles at/after a given time."""
    import MetaTrader5 as mt5
    mt5.symbol_select(symbol, True)
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 3000)
    if rates is None or len(rates) == 0:
        return None
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df = df[df["time"] >= pd.to_datetime(after_time)].reset_index(drop=True)
    return df if len(df) else None


def _score_signal(symbol, direction, entry, stop, after_time) -> dict | None:
    """
    Replay one signal. Returns outcome dict including exit_time and exit_price,
    or None if still in flight.
    """
    df = _candles_after(symbol, after_time)
    if df is None or len(df) < 2:
        return None

    risk = abs(entry - stop)
    if risk <= 0:
        return None

    # Build TPs
    if direction == "buy":
        tp1 = entry + risk * TP_MULTIPLES[0]
        tp2 = entry + risk * TP_MULTIPLES[1]
        tp3 = entry + risk * TP_MULTIPLES[2]
    else:
        tp1 = entry - risk * TP_MULTIPLES[0]
        tp2 = entry - risk * TP_MULTIPLES[1]
        tp3 = entry - risk * TP_MULTIPLES[2]

    pos = Position(symbol=symbol, direction=direction, entry=entry, stop=stop,
                   tp1=tp1, tp2=tp2, tp3=tp3, lots=1.0)

    realized_r = 0.0
    bars = 0
    exit_time = None
    exit_price = None

    for _, bar in df.iterrows():
        bars += 1
        o = float(bar["open"])
        l = float(bar["low"])
        h = float(bar["high"])
        bar_time = bar["time"]

        extremes = [l, h] if direction == "buy" else [h, l]

        for extreme in extremes:
            prev_closed = pos.closed
            prev_stop_now = pos.stop_now
            prev_tp1, prev_tp2, prev_tp3 = pos.tp1_done, pos.tp2_done, pos.tp3_done
            prev_open_fraction = pos.open_fraction

            update(pos, extreme)

            tp3_just_fired = (not prev_tp3) and pos.tp3_done
            stop_just_fired = pos.closed and not prev_closed and not tp3_just_fired

            if stop_just_fired:
                fill = fill_price(direction, prev_stop_now, o, is_stop=True)
                r_here = ((fill - entry) / risk) if direction == "buy" else ((entry - fill) / risk)
                realized_r += r_here * prev_open_fraction
                exit_time = bar_time
                exit_price = fill
            else:
                remaining = prev_open_fraction
                if (not prev_tp1) and pos.tp1_done:
                    fill = fill_price(direction, tp1, o, is_stop=False)
                    r_here = ((fill - entry) / risk) if direction == "buy" else ((entry - fill) / risk)
                    realized_r += r_here * (1 / 3)
                    remaining -= 1 / 3
                if (not prev_tp2) and pos.tp2_done:
                    fill = fill_price(direction, tp2, o, is_stop=False)
                    r_here = ((fill - entry) / risk) if direction == "buy" else ((entry - fill) / risk)
                    realized_r += r_here * (1 / 3)
                    remaining -= 1 / 3
                if tp3_just_fired:
                    fill = fill_price(direction, tp3, o, is_stop=False)
                    r_here = ((fill - entry) / risk) if direction == "buy" else ((entry - fill) / risk)
                    realized_r += r_here * remaining
                    exit_time = bar_time
                    exit_price = fill

            if pos.closed:
                break
        if pos.closed or bars >= MAX_BARS_OPEN:
            break

    if not pos.closed and bars < MAX_BARS_OPEN:
        return None

    # Time-cap close
    if not pos.closed and pos.open_fraction > 0:
        last_bar = df.iloc[min(bars, len(df)) - 1]
        last_px = float(last_bar["close"])
        r_here = ((last_px - entry) / risk) if direction == "buy" else ((entry - last_px) / risk)
        realized_r += r_here * pos.open_fraction
        exit_time = last_bar["time"]
        exit_price = last_px

    return {
        "r_multiple": round(realized_r, 3),
        "outcome": "win" if realized_r > 0.05 else "loss" if realized_r < -0.05 else "breakeven",
        "bars_held": bars,
        "exit_time": exit_time.isoformat() if exit_time is not None else None,
        "exit_price": float(exit_price) if exit_price is not None else None,
    }


def resolve_open_signals(conn) -> int:
    """Find approved signals that haven't been scored yet and score them."""
    rows = conn.execute("""
        SELECT s.* FROM signals s
        LEFT JOIN trades t ON t.signal_id = s.id
        WHERE s.approved = 1 AND t.id IS NULL
        ORDER BY s.ts
    """).fetchall()

    scored = 0
    for s in rows:
        after_time = datetime.fromisoformat(s["ts"])
        result = _score_signal(s["symbol"], s["direction"],
                               s["entry"], s["stop"], after_time)
        if result is None:
            continue

        conn.execute("""
            INSERT INTO trades (signal_id, symbol, direction, strategies,
                opened_ts, entry, stop, lots, closed_ts, exit_price, pnl,
                r_multiple, outcome, notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            s["id"], s["symbol"], s["direction"], s["strategies"],
            s["ts"], s["entry"], s["stop"], s["lots"] or 0.01,
            result["exit_time"],              # ← REAL exit time
            result["exit_price"],             # ← REAL exit price
            None,
            result["r_multiple"], result["outcome"],
            f"auto-resolved, {result['bars_held']} bars",
        ))
        scored += 1

    conn.commit()
    return scored


# Keep backward-compatible alias in case other files import this name
def resolve_closed_trades(conn, symbols=None) -> int:
    """Alias for resolve_open_signals — kept for compatibility."""
    return resolve_open_signals(conn)