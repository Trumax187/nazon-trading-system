# ============================================================
# nazon_walkforward.py — NAZON walk-forward robustness test
# ------------------------------------------------------------
# Slides an out-of-sample window across ALL of history and asks:
#   "In how many independent windows was the edge positive?"
#
# This is the rigorous follow-up to the single 70/30 split. The split
# said Gold was +0.404R out-of-sample but flagged it "unstable". This
# tells you whether that out-of-sample strength shows up REPEATEDLY
# across history, or only in the recent (possibly lucky) trending slice.
#
# It changes NO parameters — it only MEASURES. Not an optimizer.
# ============================================================
from nazon.core.mt5_connector import MT5Connector
from nazon.backtest.walk_forward import walk_forward
from nazon import config

PAIRS = ["XAUUSDm", "EURUSDm", "GBPUSDm", "USDJPYm"]

BARS = 3000            # total history to pull per pair
TRAIN_BARS = 1200      # context each window trains on
TEST_BARS = 250        # size of each out-of-sample slice
STEP_BARS = 250        # advance per window (=TEST_BARS -> no overlap)
# With 3000 bars this yields ~7 independent windows to vote on. More history
# (raise BARS if MT5 allows) -> more windows -> a more trustworthy verdict.

SPREAD_POINTS = {
    "XAUUSDm": 30,
    "EURUSDm": 2,
    "GBPUSDm": 3,
    "USDJPYm": 3,
}


def show(res):
    print("\n" + "=" * 64)
    print(f"{res['symbol']}   walk-forward over {res['n_windows']} "
          f"independent out-of-sample windows")
    print("=" * 64)

    if res["n_windows"] == 0:
        print(f"  {res['verdict']}")
        return

    # Per-window line: which bars, trades, expectancy, win/loss marker.
    print(f"  {'window (bars)':<20}{'trades':>7}{'expectancy':>13}{'':>4}")
    for w in res["windows"]:
        if w.get("n", 0) == 0:
            print(f"  {w['window_start_bar']:>6}-{w['window_end_bar']:<13}"
                  f"{'0':>7}{'—':>13}")
            continue
        mark = "✓" if w["expectancy_r"] > 0 else "✗"
        print(f"  {w['window_start_bar']:>6}-{w['window_end_bar']:<13}"
              f"{w['n']:>7}{w['expectancy_r']:>+12.3f}R  {mark}")

    print("-" * 64)
    print(f"  Windows positive:      {res['windows_positive']}/{res['n_windows']} "
          f"({res['pct_positive']*100:.0f}%)")
    print(f"  Weighted expectancy:   {res['weighted_expectancy_r']:+.3f}R "
          f"over {res['total_trades']} trades")
    print(f"  -> {res['verdict']}")


def main():
    nazon = MT5Connector()
    if not nazon.connect():
        print("Could not connect. Is the MT5 terminal open and ticking?")
        return

    print("\n" + "#" * 64)
    print("# NAZON WALK-FORWARD ROBUSTNESS  (net of spread cost)")
    print(f"# train {TRAIN_BARS} bars / test {TEST_BARS} bars per window")
    print("#" * 64)

    for symbol in PAIRS:
        df = nazon.get_candles(symbol, count=BARS)
        if df is None or len(df) < TRAIN_BARS + TEST_BARS:
            have = 0 if df is None else len(df)
            print(f"\n{symbol}: not enough candles ({have}).")
            continue
        point = config.SYMBOLS[symbol]["point"]
        sp = SPREAD_POINTS.get(symbol, 0)
        res = walk_forward(df, symbol, point,
                           train_bars=TRAIN_BARS, test_bars=TEST_BARS,
                           step_bars=STEP_BARS, spread_points=sp)
        show(res)

    nazon.disconnect()

    print("\n" + "#" * 64)
    print("# HOW TO READ THIS:")
    print("#  ROBUST   = edge positive in most windows -> real, keep testing")
    print("#  FRAGILE  = positive only in a few windows -> concentrated in")
    print("#             trending patches; the single-split +0.404R was")
    print("#             likely one of those patches. Treat with caution.")
    print("#  NO EDGE  = negative across history -> these strategies don't work")
    print("# None of these is a green light to go live. Forward data decides.")
    print("#" * 64)


if __name__ == "__main__":
    main()
