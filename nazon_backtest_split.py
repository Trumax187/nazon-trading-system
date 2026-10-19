# ============================================================
# nazon_backtest_split.py — NAZON train/test split validation
# ------------------------------------------------------------
# The honest test of the edge. Splits each pair's history into:
#   TRAIN (in-sample, older 70%)  — data the strategies were shaped around
#   TEST  (out-of-sample, recent 30%) — data the system never "saw"
#
# A REAL edge is positive on BOTH, AND survives realistic spread cost.
# An overfit edge looks great on TRAIN and falls apart on TEST.
#
# This runs the SAME backtester the full-sample run uses — so it includes
# the new direction guard. Compare TEST expectancy here against the old
# pre-fix out-of-sample number to see if the fix made the edge real.
# ============================================================
from nazon.core.mt5_connector import MT5Connector
from nazon.backtest.backtester import backtest_split
from nazon import config

# Gold is the focus, but we run all four so you can see the contrast.
PAIRS = ["XAUUSDm", "EURUSDm", "GBPUSDm", "USDJPYm"]

# How many bars of history to pull per pair (matches your full backtest ~3000).
BARS = 3000

# Realistic spread cost in POINTS, charged on entry. Gold's swing stops are
# wide so this is tiny in R, but include it — the edge must survive cost.
# Set per-pair if you like; 0 shows the gross (cost-free) number.
SPREAD_POINTS = {
    "XAUUSDm": 30,    # active-hours gold spread (the 280 you saw was off-hours)
    "EURUSDm": 2,
    "GBPUSDm": 3,
    "USDJPYm": 3,
}

TRAIN_FRAC = 0.70     # 70% train / 30% test


def verdict(train, test):
    """One-line honest read of a split result."""
    if train.get("n", 0) == 0 or test.get("n", 0) == 0:
        return "INCONCLUSIVE — too few trades in one slice"
    te = test["expectancy_r"]
    tr = train["expectancy_r"]
    if te > 0 and tr > 0:
        return "EDGE HOLDS out-of-sample — strongest evidence short of forward data"
    if te > 0 and tr <= 0:
        return "TEST positive but TRAIN negative — unstable, treat with caution"
    if te <= 0 and tr > 0:
        return "OVERFIT WARNING — good in-sample, negative out-of-sample"
    return "NO EDGE — negative on both slices"


def show(symbol, res):
    train, test = res["train"], res["test"]
    print("\n" + "=" * 60)
    print(f"{symbol}   train {res['train_bars']} bars / test {res['test_bars']} bars")
    print("=" * 60)

    for name, s in (("TRAIN (in-sample)", train), ("TEST  (out-of-sample)", test)):
        if s.get("n", 0) == 0:
            print(f"  {name}: no trades generated")
            continue
        print(f"  {name}")
        print(f"     Trades:     {s['n']}")
        print(f"     Win rate:   {s['win_rate']*100:.0f}%")
        print(f"     Avg win:    +{s['avg_win_r']:.3f}R   Avg loss: -{s['avg_loss_r']:.3f}R")
        print(f"     Expectancy: {s['expectancy_r']:+.3f}R   Total: {s['total_r']:+.1f}R")

    print(f"  -> {verdict(train, test)}")


def main():
    nazon = MT5Connector()
    if not nazon.connect():
        print("Could not connect. Is the MT5 terminal open and ticking?")
        return

    print("\n" + "#" * 60)
    print("# NAZON TRAIN/TEST SPLIT  (net of spread cost)")
    print(f"# {int(TRAIN_FRAC*100)}% train / {int((1-TRAIN_FRAC)*100)}% test")
    print("#" * 60)

    for symbol in PAIRS:
        df = nazon.get_candles(symbol, count=BARS)
        if df is None or len(df) < 500:
            print(f"\n{symbol}: not enough candles ({0 if df is None else len(df)}).")
            continue
        point = config.SYMBOLS[symbol]["point"]
        sp = SPREAD_POINTS.get(symbol, 0)
        res = backtest_split(df, symbol, point,
                             train_frac=TRAIN_FRAC, spread_points=sp)
        show(symbol, res)

    nazon.disconnect()

    print("\n" + "#" * 60)
    print("# Read GOLD first. If TEST expectancy is positive, the edge")
    print("# survived out-of-sample WITH the direction guard — that's the")
    print("# green light to keep forward-testing on demo. It is NOT a green")
    print("# light to go live. Forward data is still the final word.")
    print("#" * 60)


if __name__ == "__main__":
    main()
