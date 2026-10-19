"""
NAZON — MT5 Connector
=====================
The nervous system: connects NAZON to the live MT5 terminal and feeds it real
candles. Everything the strategy modules need comes through here.

Design choices (matching how NAZON is built):
  - A CLASS, because a connection has STATE (connected or not, which terminal).
  - Pure data out: it returns clean pandas DataFrames; it makes no trading
    decisions. Decide/execute separation stays intact.
  - It drops the still-forming candle before returning data — see get_candles.
    Deciding on an unclosed candle is look-ahead bias and will lie to you.

Run order reminder (from config.py): the MT5 terminal must already be open,
logged in, Algo Trading green, and launched at the SAME privilege level as
Python (both normal). Then this attaches to it.
"""

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

from nazon import config


# Map our timeframe strings to MT5's own constants, so config.py never has to
# import MetaTrader5 itself. Add more here if you ever scan other timeframes.
_TIMEFRAME_MAP = {
    "M15": mt5.TIMEFRAME_M15,
    "H1":  mt5.TIMEFRAME_H1,
    "H4":  mt5.TIMEFRAME_H4,
    "D1":  mt5.TIMEFRAME_D1,
}


class MT5Connector:
    """Holds the live connection to the MT5 terminal."""

    def __init__(self):
        self.connected = False          # state: are we attached?
        self.account = None             # filled in after connect()

    # ---- connection lifecycle ----

    def connect(self) -> bool:
        """
        Attach to the already-running terminal. Returns True on success.
        Uses the timeout from config so a slow machine has room.
        """
        # Build kwargs: only pass path if config actually sets one.
        kwargs = {"timeout": config.INIT_TIMEOUT}
        if config.TERMINAL_PATH:
            kwargs["path"] = config.TERMINAL_PATH

        if not mt5.initialize(**kwargs):
            # last_error() tells us WHY — log it instead of failing silently.
            print(f"[NAZON] Connect failed: {mt5.last_error()}")
            self.connected = False
            return False

        self.account = mt5.account_info()
        self.connected = True

        # Sanity-check we're on the expected account (catches logging into the
        # wrong one by mistake — important before any future live trading).
        if self.account and self.account.login != config.ACCOUNT_LOGIN:
            print(f"[NAZON] WARNING: connected to {self.account.login}, "
                  f"expected {config.ACCOUNT_LOGIN}")

        print(f"[NAZON] Connected -> {self.account.login} | "
              f"{self.account.balance} {self.account.currency} | "
              f"{self.account.server}")
        return True

    def disconnect(self) -> None:
        """Always call this when done, to close the terminal link cleanly."""
        mt5.shutdown()
        self.connected = False
        print("[NAZON] Disconnected.")

    # ---- data fetching ----

    def get_candles(self, symbol: str, count: int = None) -> pd.DataFrame | None:
        """
        Pull recent CLOSED candles for a symbol as a DataFrame.

        Returns columns: time, open, high, low, close, tick_volume.
        Returns None if the symbol name is wrong or no data comes back.

        IMPORTANT: the most recent candle MT5 gives is still forming (it changes
        every tick). We DROP it, so every row NAZON sees is a finished candle.
        This is the single most important line for honest signals & backtests.
        """
        if not self.connected:
            print("[NAZON] get_candles called while not connected.")
            return None

        count = count or config.CANDLE_COUNT
        tf = _TIMEFRAME_MAP.get(config.TIMEFRAME)
        if tf is None:
            print(f"[NAZON] Unknown timeframe '{config.TIMEFRAME}'.")
            return None

        # Make sure the symbol is selected in Market Watch, or copy_rates may
        # return nothing even when the name is correct.
        if not mt5.symbol_select(symbol, True):
            print(f"[NAZON] Could not select symbol '{symbol}'.")
            return None

        # Pull count+1 because we're about to discard the unclosed last candle.
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, count + 1)
        if rates is None or len(rates) == 0:
            print(f"[NAZON] No candles for '{symbol}': {mt5.last_error()}")
            return None

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")   # epoch -> datetime
        df = df[["time", "open", "high", "low", "close", "tick_volume"]]

        # Drop the final (still-forming) candle -> only closed candles remain.
        df = df.iloc[:-1].reset_index(drop=True)
        return df

    def get_daily_candles(self, symbol: str, count: int = 60) -> pd.DataFrame | None:
        """
        Pull recent CLOSED DAILY (D1) candles for the HTF trend filter.

        Same look-ahead guard as get_candles: drops the still-forming daily
        candle so the HTF filter only ever sees finished days. 60 closed daily
        bars is plenty for the EMA50 the filter uses (HTF_EMA_PERIOD=50).

        Independent of config.TIMEFRAME (which is H4) — this always uses D1.
        """
        if not self.connected:
            print("[NAZON] get_daily_candles called while not connected.")
            return None

        if not mt5.symbol_select(symbol, True):
            print(f"[NAZON] Could not select symbol '{symbol}'.")
            return None

        # +1 because we discard the still-forming current daily candle.
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 0, count + 1)
        if rates is None or len(rates) == 0:
            print(f"[NAZON] No daily candles for '{symbol}': {mt5.last_error()}")
            return None

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df = df[["time", "open", "high", "low", "close", "tick_volume"]]
        # Drop the final (still-forming) daily candle -> closed candles only.
        df = df.iloc[:-1].reset_index(drop=True)
        return df

    def get_spread(self, symbol: str) -> int | None:
        """Current spread in POINTS, for the spread gate. None if unavailable."""
        info = mt5.symbol_info(symbol)
        return info.spread if info else None

    def get_balance(self) -> float | None:
        """Live account balance, for the lot-size calculator."""
        acc = mt5.account_info()
        return acc.balance if acc else None
