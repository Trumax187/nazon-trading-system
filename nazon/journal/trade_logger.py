"""
NAZON — Trade Journal (storage layer)
=====================================
The memory of NAZON. Every signal it produces, every trade it takes, and the
daily safety state all live here in a local SQLite file. No server, no setup —
sqlite3 is built into Python.

Why this is the keystone of the whole project:
  - It persists DayState, so a crash/restart can't wipe the kill switch's
    daily loss count and re-open the floodgates.
  - It records WHY a signal was rejected (which gate failed), not just the
    trades taken — so in 2 months you can see if your gates are too strict.
  - It's the raw material the analytics layer turns into expectancy and win
    rate — the numbers that decide demo -> live -> public.

Three tables:
  signals  — every signal NAZON generated, approved or not, with the reason
  trades   — positions actually taken, and their outcome once closed
  days     — one row per trading day: starting balance, realized P&L, halts

Design choice: storage here is dumb and honest. It records what happened.
The thinking (expectancy, etc.) lives in analytics.py, kept separate so a
reporting bug can never corrupt the stored history.
"""

import sqlite3
from datetime import date, datetime
from pathlib import Path
import hashlib
from pathlib import Path


def config_hash() -> str:
    """Return a short hash of the current config.py so each signal can be
    tied to the exact parameter set that produced it."""
    try:
        from .. import config
        config_path = Path(config.__file__)
        content = config_path.read_bytes()
        return hashlib.sha256(content).hexdigest()[:12]
    except Exception:
        return "unknown"

DB_PATH = Path("nazon_journal.db")


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Open the journal, creating tables on first use."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row     # rows behave like dicts
    _init(conn)
    return conn


def _init(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS signals (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            ts            TEXT NOT NULL,        -- when scanned (ISO)
            symbol        TEXT NOT NULL,
            direction     TEXT,                -- buy / sell / none
            confidence    REAL,
            regime        TEXT,
            strategies    TEXT,                -- which fired, comma-separated
            entry         REAL,
            stop          REAL,
            tp1 REAL, tp2 REAL, tp3 REAL,
            lots          REAL,
            rr            REAL,                -- risk:reward
            approved      INTEGER NOT NULL,    -- 1 / 0
            reject_reason TEXT,                -- why, if not approved
            reasoning     TEXT
        );

        CREATE TABLE IF NOT EXISTS trades (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id     INTEGER,             -- links back to signals.id
            symbol        TEXT NOT NULL,
            direction     TEXT NOT NULL,
            strategies    TEXT,
            opened_ts     TEXT NOT NULL,
            entry         REAL NOT NULL,
            stop          REAL NOT NULL,
            lots          REAL NOT NULL,
            risk_amount   REAL,                -- true cash-at-risk at entry (account
                                                 -- currency). REQUIRED for correct
                                                 -- R-multiples across symbols with
                                                 -- different contract sizes/point
                                                 -- values (XAUUSDm vs EURUSDm etc.).
                                                 -- Must be computed by the caller
                                                 -- using the symbol's real contract
                                                 -- specs, not price-distance alone.
            closed_ts     TEXT,                -- NULL while open
            exit_price    REAL,
            pnl           REAL,                -- realized, account currency
            r_multiple    REAL,                -- pnl in units of initial risk
            outcome       TEXT,                -- win / loss / breakeven / open
            notes         TEXT,
            FOREIGN KEY (signal_id) REFERENCES signals(id)
        );

        CREATE TABLE IF NOT EXISTS days (
            trading_day        TEXT PRIMARY KEY,   -- ISO date
            starting_balance   REAL NOT NULL,
            realized_pnl       REAL DEFAULT 0,
            consecutive_losses INTEGER DEFAULT 0,
            open_trades        INTEGER DEFAULT 0,
            halted_reason      TEXT DEFAULT ''
        );
        """
    )
    conn.commit()


# ---------- signals ----------

def log_signal(conn, *, ts, symbol, direction, confidence, regime, strategies,
               entry, stop, tp1, tp2, tp3, lots, rr, approved,
               reject_reason="", reasoning="") -> int:
    """Record a signal (approved or not). Returns its row id."""
    strat = ",".join(strategies) if isinstance(strategies, (list, tuple)) else (strategies or "")
    cur = conn.execute(
        """INSERT INTO signals (ts, symbol, direction, confidence, regime,
              strategies, entry, stop, tp1, tp2, tp3, lots, rr, approved,
              reject_reason, reasoning)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (ts, symbol, direction, confidence, regime, strat, entry, stop,
         tp1, tp2, tp3, lots, rr, 1 if approved else 0, reject_reason, reasoning),
    )
    conn.commit()
    return cur.lastrowid


def log_signal_obj(conn, sig) -> int:
    """
    Convenience wrapper: log a Signal object (from signal_contract) directly,
    so the scanner doesn't have to unpack every field by hand. Maps the Signal's
    fields onto log_signal's named arguments. Returns the new row id.
    """
    return log_signal(
        conn,
        ts=sig.timestamp,
        symbol=sig.symbol,
        direction=sig.direction,
        confidence=sig.confidence,
        regime=sig.regime,
        strategies=sig.strategies,
        entry=sig.entry,
        stop=sig.stop,
        tp1=sig.tp1, tp2=sig.tp2, tp3=sig.tp3,
        lots=sig.lots,
        rr=sig.rr,
        approved=sig.approved,
        reject_reason=sig.reject_reason,
        reasoning=sig.reasoning,
    )


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, coltype: str) -> None:
    """Add `column` to `table` if it doesn't already exist (safe on old DBs
    created before this column was added to the schema)."""
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")
        conn.commit()


def already_logged_candle(conn, symbol: str, candle_time) -> bool:
    """
    Has NAZON already logged a signal for this symbol's specific candle?
    Returns True if so -> the caller should SKIP logging. This stops the journal
    filling with duplicates when you run the scan several times inside the same
    4-hour candle (the closed candle doesn't change until the next one closes,
    so re-scanning produces identical signals).
    """
    cols = [r[1] for r in conn.execute("PRAGMA table_info(signals)").fetchall()]
    if "candle_time" not in cols:
        conn.execute("ALTER TABLE signals ADD COLUMN candle_time TEXT")
        conn.commit()
    row = conn.execute(
        "SELECT 1 FROM signals WHERE symbol=? AND candle_time=? LIMIT 1",
        (symbol, str(candle_time)),
    ).fetchone()
    return row is not None


def set_candle_time(conn, signal_id: int, candle_time) -> None:
    """Stamp a just-logged signal with the candle it was based on (for dedup)."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(signals)").fetchall()]
    if "candle_time" not in cols:
        conn.execute("ALTER TABLE signals ADD COLUMN candle_time TEXT")
    conn.execute("UPDATE signals SET candle_time=? WHERE id=?",
                 (str(candle_time), signal_id))
    conn.commit()


def open_trade(conn, *, signal_id, symbol, direction, strategies,
               opened_ts, entry, stop, lots, risk_amount=None) -> int:
    """
    Record that a trade was actually entered. Returns its row id.

    risk_amount: the REAL cash-at-risk for this trade in account currency
    (e.g. what you'd lose if the stop is hit cleanly). This must be computed
    by the caller using the symbol's actual contract size / point value
    (e.g. via mt5.symbol_info(symbol) tick_value/contract_size) — NOT derived
    from price-distance * lots alone, since that ratio differs per symbol
    (XAUUSDm vs EURUSDm vs USDJPYm etc.) and silently produces wrong R-multiples
    if treated as if it were cash. If you don't have it yet, pass None — the
    trade will still be logged, but its R-multiple at close will be flagged as
    approximate rather than trusted.
    """
    _ensure_column(conn, "trades", "risk_amount", "REAL")
    strat = ",".join(strategies) if isinstance(strategies, (list, tuple)) else (strategies or "")
    cur = conn.execute(
        """INSERT INTO trades (signal_id, symbol, direction, strategies,
              opened_ts, entry, stop, lots, risk_amount, outcome)
           VALUES (?,?,?,?,?,?,?,?,?, 'open')""",
        (signal_id, symbol, direction, strat, opened_ts, entry, stop, lots, risk_amount),
    )
    conn.commit()
    return cur.lastrowid


def close_trade(conn, *, trade_id, closed_ts, exit_price, pnl, notes="") -> None:
    """
    Close a trade and compute its R-multiple (pnl measured in units of the
    initial risk). R-multiple is the honest way to compare trades of different
    sizes: +2R means you made twice what you risked, regardless of lot size.
    """
    _ensure_column(conn, "trades", "risk_amount", "REAL")
    row = conn.execute("SELECT entry, stop, lots, risk_amount FROM trades WHERE id=?",
                       (trade_id,)).fetchone()
    if row is None:
        raise ValueError(f"trade {trade_id} not found")

    entry, stop, lots, risk_amount = row["entry"], row["stop"], row["lots"], row["risk_amount"]

    if risk_amount and risk_amount > 0:
        # Correct path: real cash-at-risk was recorded at entry, using the
        # symbol's actual contract specs. R-multiple is trustworthy.
        risk_cash = risk_amount
    else:
        # Fallback for trades opened before risk_amount was wired up (or if
        # the caller still isn't passing it). This is price-distance * lots,
        # which is NOT real cash unless contract size happens to be 1 —
        # it will misprice R for XAUUSDm/EURUSDm/GBPUSDm/USDJPYm differently.
        # Flagged in `notes` below so bad historical data is easy to spot
        # and exclude from expectancy/profit-factor analysis.
        risk_per_unit = abs(entry - stop)
        risk_cash = risk_per_unit * lots
        approx_warning = " [WARN: risk_amount missing — R-multiple is a rough approximation, not comparable across symbols]"
        notes = (notes + approx_warning) if notes else approx_warning.strip()

    r_multiple = (pnl / risk_cash) if risk_cash > 0 else None

    if pnl > 0:
        outcome = "win"
    elif pnl < 0:
        outcome = "loss"
    else:
        outcome = "breakeven"

    conn.execute(
        """UPDATE trades SET closed_ts=?, exit_price=?, pnl=?, r_multiple=?,
               outcome=?, notes=? WHERE id=?""",
        (closed_ts, exit_price, pnl,
         round(r_multiple, 3) if r_multiple is not None else None,
         outcome, notes, trade_id),
    )
    conn.commit()


# ---------- days (persists the kill switch's DayState) ----------

def save_day(conn, state) -> None:
    """Upsert a DayState (from kill_switch) so a restart keeps the day's
    loss count and halt. Accepts the kill_switch.DayState dataclass."""
    conn.execute(
        """INSERT INTO days (trading_day, starting_balance, realized_pnl,
               consecutive_losses, open_trades, halted_reason)
           VALUES (?,?,?,?,?,?)
           ON CONFLICT(trading_day) DO UPDATE SET
               starting_balance=excluded.starting_balance,
               realized_pnl=excluded.realized_pnl,
               consecutive_losses=excluded.consecutive_losses,
               open_trades=excluded.open_trades,
               halted_reason=excluded.halted_reason""",
        (state.trading_day.isoformat(), state.starting_balance,
         state.realized_pnl, state.consecutive_losses,
         state.open_trades, state.halted_reason),
    )
    conn.commit()


def load_day(conn, trading_day: date):
    """Return today's saved row (or None). Use to restore DayState on startup."""
    return conn.execute("SELECT * FROM days WHERE trading_day=?",
                        (trading_day.isoformat(),)).fetchone()
