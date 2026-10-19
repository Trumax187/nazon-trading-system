# ============================================================
# nazon_auto.py — NAZON automatic runner (for Windows Task Scheduler)
# Runs the demo scan AND resolves any closed trades, every time it
# fires. Wrapped in error handling so a hiccup (MT5 not open, no
# internet) just logs the problem instead of crashing — the next
# scheduled run will simply try again.
#
# Writes a small log to nazon_auto.log so you can see, anytime, that
# it has been running while you were away.
# ============================================================
import sys
import traceback
from datetime import datetime
from pathlib import Path

LOG_FILE = Path(__file__).parent / "nazon_auto.log"


def log(msg: str):
    """Append a timestamped line to the auto-log AND print it."""
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass  # never let logging itself crash the run


def run_scan():
    """Run the demo scan (logs new signals)."""
    from nazon.core.mt5_connector import MT5Connector
    from nazon.core.signal_engine import analyse
    from nazon.core.kill_switch import DayState
    from nazon.journal import trade_logger as J
    from nazon import config
    from datetime import date

    nazon = MT5Connector()
    if not nazon.connect():
        log("SCAN skipped — could not connect to MT5 (terminal closed?).")
        return

    balance = nazon.get_balance()
    conn = J.connect(config.JOURNAL_DB)
    today = date.today()
    saved = J.load_day(conn, today)
    if saved:
        day = DayState(trading_day=today, starting_balance=saved["starting_balance"],
                       realized_pnl=saved["realized_pnl"],
                       consecutive_losses=saved["consecutive_losses"],
                       open_trades=saved["open_trades"],
                       halted_reason=saved["halted_reason"])
    else:
        day = DayState(trading_day=today, starting_balance=balance)

    for symbol in ["XAUUSDm"]:
        df = nazon.get_candles(symbol)
        if df is None or len(df) < 200:
            log(f"SCAN {symbol}: not enough candles.")
            continue
        candle_time = df.iloc[-1]["time"]
        if J.already_logged_candle(conn, symbol, candle_time):
            log(f"SCAN {symbol}: candle {candle_time} already logged — skipped.")
            continue
        spread = nazon.get_spread(symbol)
        point = config.SYMBOLS[symbol]["point"]
        d1 = nazon.get_daily_candles(symbol, count=60)   # HTF Daily trend filter
        sig = analyse(symbol, df, spread_points=spread, point=point,
                      balance=balance, open_positions=[], day_state=day, d1=d1)
        sid = J.log_signal_obj(conn, sig)
        J.set_candle_time(conn, sid, candle_time)
        log(f"SCAN {symbol}: logged {sig.status} {sig.direction} "
            f"(candle {candle_time}, spread {spread}).")

    J.save_day(conn, day)
    conn.close()
    nazon.disconnect()


def run_resolve():
    """Score any approved signals that have now closed."""
    from nazon.core.mt5_connector import MT5Connector
    from nazon.journal import trade_logger as J
    from nazon.journal.outcome_resolver import resolve_open_signals
    from nazon import config

    nazon = MT5Connector()
    if not nazon.connect():
        log("RESOLVE skipped — could not connect to MT5.")
        return
    conn = J.connect(config.JOURNAL_DB)
    scored = resolve_open_signals(conn)
    log(f"RESOLVE: scored {scored} newly-closed signal(s).")
    conn.close()
    nazon.disconnect()


if __name__ == "__main__":
    log("--- NAZON auto run start ---")
    try:
        run_scan()
    except Exception:
        log("SCAN ERROR:\n" + traceback.format_exc())
    try:
        run_resolve()
    except Exception:
        log("RESOLVE ERROR:\n" + traceback.format_exc())
    log("--- NAZON auto run end ---\n")
