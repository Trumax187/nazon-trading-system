"""
NAZON — Walk-Forward Analyzer
=============================
The rigorous version of a single train/test split. Instead of one 70/30 cut
(which can flatter a strategy if the one test window happened to trend), this
slides the OUT-OF-SAMPLE window across the WHOLE history in steps:

    [-------- train --------][ test ]                      window 1
            [-------- train --------][ test ]              window 2
                    [-------- train --------][ test ]      window 3
                            ... and so on ...

Each window trains on the bars before it and tests on the next unseen chunk.
We then ask the honest question:

    In how many independent out-of-sample windows was the edge positive?

A REAL edge wins in MOST windows. An edge that only shows up because the most
recent slice happened to trend will win in just one or two. This is exactly
the "is +0.404R real or a lucky recent trend?" question, answered across all
of history instead of only the last 30%.

No new strategy logic — it reuses backtester.backtest() and summarize(), so it
tests the SAME engine (with the direction guard) that live trading uses.
NOT an optimizer: it changes no parameters, it only MEASURES stability.
"""

import pandas as pd

from nazon.backtest.backtester import backtest_with_engine, summarize, WARMUP


def walk_forward(df: pd.DataFrame,
                 symbol: str,
                 point: float,
                 train_bars: int = 1500,
                 test_bars: int = 400,
                 step_bars: int = None,
                 spread_points: float = 0.0) -> dict:
    """
    Slide a train->test window across df and backtest each test slice.

    train_bars : how many bars each window trains on (context before the test).
    test_bars  : size of each out-of-sample test slice.
    step_bars  : how far to advance each window (defaults to test_bars = no
                 overlap between test slices, so each trade is counted once).
    spread_points : realistic per-trade cost in points (net numbers).

    Returns a dict with per-window summaries and an aggregate verdict.
    """
    if step_bars is None:
        step_bars = test_bars

    n = len(df)
    windows = []

    # The first test slice can only start once we have train_bars of history
    # AND the engine's own WARMUP inside that training context.
    start = train_bars
    while start + test_bars <= n:
        # Test slice is [start, start+test_bars). The backtest needs WARMUP
        # bars of lead-in INSIDE the slice it receives, so we hand it a frame
        # that begins WARMUP bars before the test window and ends at its close.
        slice_begin = start - WARMUP
        slice_end = start + test_bars
        test_slice = df.iloc[slice_begin:slice_end].reset_index(drop=True)

        trades = backtest_with_engine(test_slice, symbol, point, spread_points)
        s = summarize(trades)
        s["window_start_bar"] = start
        s["window_end_bar"] = slice_end
        windows.append(s)

        start += step_bars

    return _aggregate(symbol, windows)


def _aggregate(symbol: str, windows: list[dict]) -> dict:
    """Roll per-window results into an honest stability verdict."""
    # Only windows that actually generated trades count toward the vote.
    traded = [w for w in windows if w.get("n", 0) > 0]
    n_windows = len(traded)

    if n_windows == 0:
        return {
            "symbol": symbol,
            "n_windows": 0,
            "verdict": "INCONCLUSIVE — no window generated trades",
            "windows": windows,
        }

    positive = [w for w in traded if w["expectancy_r"] > 0]
    pct_positive = len(positive) / n_windows

    # Trade-weighted expectancy across all windows (one combined number that
    # weights each window by how many trades it produced — fairer than a plain
    # average of window expectancies).
    total_trades = sum(w["n"] for w in traded)
    weighted_exp = sum(w["expectancy_r"] * w["n"] for w in traded) / total_trades

    if pct_positive >= 0.6 and weighted_exp > 0:
        verdict = ("ROBUST — positive in a majority of independent windows. "
                   "Strongest backtest evidence the edge is real, not a "
                   "one-off trend. Forward data is still the final word.")
    elif pct_positive >= 0.5 and weighted_exp > 0:
        verdict = ("MARGINAL — positive in about half the windows. A weak/"
                   "regime-dependent edge. Worth forward-testing, not funding.")
    elif weighted_exp > 0:
        verdict = ("FRAGILE — overall positive but wins in a MINORITY of "
                   "windows. The edge likely concentrates in a few trending "
                   "patches (matches the 'lucky recent slice' worry). Caution.")
    else:
        verdict = ("NO STABLE EDGE — negative on a trade-weighted basis "
                   "across history. Do not pursue with these strategies.")

    return {
        "symbol": symbol,
        "n_windows": n_windows,
        "windows_positive": len(positive),
        "pct_positive": round(pct_positive, 2),
        "weighted_expectancy_r": round(weighted_exp, 3),
        "total_trades": total_trades,
        "verdict": verdict,
        "windows": windows,
    }
