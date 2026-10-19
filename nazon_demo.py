# ============================================================
# nazon_demo.py — NAZON demo-phase scanner
# Run this during the demo to log Gold signals to the journal.
# It scans the latest CLOSED candle, logs one signal per candle
# (no duplicates), and shows clear timing so you always know
# what NAZON is looking at and when.
# ============================================================
from datetime import date, datetime, timedelta

from nazon.core.mt5_connector import MT5Connector
from nazon.core.signal_engine import analyse
from nazon.core.kill_switch import DayState
from nazon.journal import trade_logger as J
from nazon import config

# Which pairs to scan in the demo. Gold focus (NAZON's proven-ish edge).
DEMO_PAIRS = ["XAUUSDm"]


def main():
    nazon = MT5Connector()
    if not nazon.connect():
        print("Could not connect. Is the MT5 terminal open and ticking?")
        return

    balance = nazon.get_balance()
    conn = J.connect(config.JOURNAL_DB)

    # Restore today's kill-switch state (or start fresh) so daily limits persist.
    today = date.today()
    saved = J.load_day(conn, today)
    if saved:
        day = DayState(
            trading_day=today,
            starting_balance=saved["starting_balance"],
            realized_pnl=saved["realized_pnl"],
            consecutive_losses=saved["consecutive_losses"],
            open_trades=saved["open_trades"],
            halted_reason=saved["halted_reason"],
        )
    else:
        day = DayState(trading_day=today, starting_balance=balance)

    print("\n" + "=" * 60)
    print("NAZON DEMO SCAN")
    print(f"  Run at:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (your computer time)")
    print(f"  Balance: ${balance:.2f}")
    print("=" * 60)

    for symbol in DEMO_PAIRS:
        df = nazon.get_candles(symbol)
        if df is None or len(df) < 200:
            print(f"\n{symbol}: not enough candles yet.")
            continue

        candle_time = df.iloc[-1]["time"]                 # last CLOSED candle
        next_candle = candle_time + timedelta(hours=4)    # when the next closes

        # Skip if we already logged a signal for this exact candle.
        if J.already_logged_candle(conn, symbol, candle_time):
            print(f"\n{symbol}: last closed candle is {candle_time} (server time).")
            print(f"   Already logged this one — no new candle yet.")
            print(f"   Next candle closes ~{next_candle} (server time). Run again after then.")
            continue

        spread = nazon.get_spread(symbol)
        point = config.SYMBOLS[symbol]["point"]
        d1 = nazon.get_daily_candles(symbol, count=60)   # HTF Daily trend filter

        sig = analyse(symbol, df, spread_points=spread, point=point,
                      balance=balance, open_positions=[], day_state=day, d1=d1)

        # Log every signal (approved or not) and stamp its candle for dedup.
        sid = J.log_signal_obj(conn, sig)
        J.set_candle_time(conn, sid, candle_time)

        print("\n" + sig.one_line())
        print(f"   based on closed candle: {candle_time} (server time)")
        print(f"   next candle ~{next_candle} | regime: {sig.regime} "
              f"(ADX {sig.regime_adx}) | spread: {spread} pts")
        if sig.status == "approved":
            print(f"   PLAN: entry {sig.entry} | stop {sig.stop} | "
                  f"TP {sig.tp1}/{sig.tp2}/{sig.tp3} | lots {sig.lots} | RR {sig.rr}")

    # Persist today's kill-switch state so a restart doesn't reset daily limits.
    J.save_day(conn, day)
    conn.close()
    nazon.disconnect()

    print("\n" + "=" * 60)
    print("Signal logged. Run nazon_results.py to score closed trades & see expectancy.")
    print("=" * 60)


if __name__ == "__main__":
    main()
