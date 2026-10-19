# ============================================================
# nazon_regime_breakdown.py — where does NAZON's edge actually live?
# ------------------------------------------------------------
# The analysis for the DECISION POINT (after ~30 forward trades).
#
# Overall expectancy hides the real question. NAZON is built for TRENDS,
# and the walk-forward hinted its edge concentrates in trending patches.
# This script breaks the CLOSED forward trades down by the ADX at entry
# and by strategy, so you can see:
#
#   "Is NAZON positive in STRONG trends and just scratching in weak ones?"
#        -> if yes, the fix is to TIGHTEN the regime filter (real weakness)
#   "Is it break-even even in strong trends?"
#        -> if yes, these strategies don't beat the market. Retire them.
#
# Reads the journal only. Changes nothing. Pure measurement.
# ============================================================
import sqlite3
import os
import re

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nazon_journal.db")

# ADX buckets to group trades by. Edit if you want finer/coarser bands.
# (low edge expected in <30; the system's home turf is the high bands)
BUCKETS = [
    ("weak  (ADX < 30)",   0,   30),
    ("good  (30-40)",      30,   40),
    ("strong(40-50)",      40,   50),
    ("very strong (50+)",  50,  999),
]


def adx_from_reasoning(text: str):
    """Pull the ADX number out of a signal's reasoning string, e.g.
    '...trending market (ADX 49.5, DI dir up, daily up)...' -> 49.5"""
    if not text:
        return None
    m = re.search(r"ADX\s+([\d.]+)", text)
    return float(m.group(1)) if m else None


def summarize(rows):
    """rows = list of r_multiples. Return n / win% / expectancy / total."""
    n = len(rows)
    if n == 0:
        return None
    wins = [r for r in rows if r > 0.05]
    exp = sum(rows) / n
    return {
        "n": n,
        "win_rate": len(wins) / n,
        "expectancy": exp,
        "total": sum(rows),
    }


def line(label, s):
    if s is None:
        print(f"  {label:<22}  no trades")
        return
    print(f"  {label:<22}  n={s['n']:<3}  win {s['win_rate']*100:>3.0f}%   "
          f"exp {s['expectancy']:+.3f}R   total {s['total']:+.1f}R")


def main():
    if not os.path.exists(DB):
        print(f"No journal found at {DB}")
        return

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row

    # Closed trades joined to the signal that produced them (for ADX + regime).
    rows = con.execute("""
        SELECT t.r_multiple   AS r,
               t.strategies   AS strat,
               t.outcome      AS outcome,
               s.regime       AS regime,
               s.reasoning    AS reasoning
        FROM trades t
        LEFT JOIN signals s ON s.id = t.signal_id
        WHERE t.outcome IN ('win','loss','breakeven')
          AND t.r_multiple IS NOT NULL
    """).fetchall()
    con.close()

    if not rows:
        print("No closed trades yet. Run this again once trades accumulate.")
        print("(Need ~30 closed trades before the breakdown means anything.)")
        return

    all_r = [r["r"] for r in rows]
    print("\n" + "=" * 60)
    print(f"NAZON REGIME BREAKDOWN  ({len(all_r)} closed forward trades)")
    print("=" * 60)

    overall = summarize(all_r)
    print("\nOVERALL")
    line("all trades", overall)
    if overall["n"] < 30:
        print(f"  ** only {overall['n']} trades — read as provisional, not final **")

    # --- by ADX bucket -------------------------------------------------
    print("\nBY TREND STRENGTH (ADX at entry)")
    untagged = 0
    for label, lo, hi in BUCKETS:
        bucket_r = []
        for row in rows:
            adx = adx_from_reasoning(row["reasoning"])
            if adx is None:
                continue
            if lo <= adx < hi:
                bucket_r.append(row["r"])
        line(label, summarize(bucket_r))
    # count how many couldn't be tagged with an ADX
    untagged = sum(1 for row in rows if adx_from_reasoning(row["reasoning"]) is None)
    if untagged:
        print(f"  ({untagged} trade(s) had no ADX in reasoning — older/edge cases)")

    # --- by strategy ---------------------------------------------------
    print("\nBY STRATEGY")
    strat_names = set()
    for row in rows:
        for nm in (row["strat"] or "").split(","):
            if nm.strip():
                strat_names.add(nm.strip())
    for nm in sorted(strat_names):
        s_r = [row["r"] for row in rows if nm in (row["strat"] or "")]
        line(nm, summarize(s_r))

    # --- by regime label ----------------------------------------------
    print("\nBY REGIME LABEL")
    regimes = sorted({(row["regime"] or "unknown") for row in rows})
    for rg in regimes:
        rg_r = [row["r"] for row in rows if (row["regime"] or "unknown") == rg]
        line(rg, summarize(rg_r))

    # --- the read ------------------------------------------------------
    print("\n" + "-" * 60)
    print("HOW TO READ:")
    print("  If the high-ADX bands (40+) are clearly POSITIVE while the weak")
    print("  band drags the overall toward zero -> the edge is real but lives")
    print("  in strong trends. Action: tighten the regime filter to skip weak")
    print("  setups. That's acting on a forward-confirmed weakness, not")
    print("  curve-fitting.")
    print("  If even the high-ADX bands are break-even -> these strategies")
    print("  don't beat the market. Retire them; reuse the pipeline for new")
    print("  ideas. No shame — it's the expected result for textbook indicators.")
    print("-" * 60)


if __name__ == "__main__":
    main()