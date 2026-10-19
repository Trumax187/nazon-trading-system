"""
NAZON — Central Configuration
==============================
All tunable settings in one place.
"""

# ── ACCOUNT ──────────────────────────────────────────────────────────
ACCOUNT_LOGIN = 436240478
ACCOUNT_SERVER = "Exness-MT5Trial9"

# Path to MT5 terminal (None = attach to running terminal)
TERMINAL_PATH = None

# Connection timeout (milliseconds)
INIT_TIMEOUT = 120000


# ── SYMBOLS ──────────────────────────────────────────────────────────
SYMBOLS = {
    "XAUUSDm": {"point": 0.001,  "digits": 3, "label": "Gold vs US Dollar"},
    "EURUSDm": {"point": 1e-05,  "digits": 5, "label": "Euro vs US Dollar"},
    "GBPUSDm": {"point": 1e-05,  "digits": 5, "label": "Pound vs US Dollar"},
    "USDJPYm": {"point": 0.001,  "digits": 3, "label": "US Dollar vs Yen"},
}
PAIRS = list(SYMBOLS.keys())


# ── TIMEFRAME ────────────────────────────────────────────────────────
TIMEFRAME = "H4"
CANDLE_COUNT = 300


# ── RISK & TRADE RULES ───────────────────────────────────────────────
RISK_PCT = 0.01
MIN_RR = 1.5
MIN_CONF = 70
MIN_STRATEGIES_AGREE = 1


# ── REGIME THRESHOLDS ────────────────────────────────────────────────
# Tighter ADX threshold — 30 was too loose, allowing chop trades
MIN_H4_ADX = 35              # H4 must show strong trend

# Daily confirmation — H4 signals need the Daily to also be trending
MIN_DAILY_ADX = 30           # Daily ADX must be at least this

# EMA trend filter — blocks trades that fight the immediate trend
USE_EMA_FILTER = True


# ── JOURNAL ──────────────────────────────────────────────────────────
JOURNAL_DB = "nazon_journal.db"

# ── REGIME THRESHOLDS (FIXED — Oct 2026) ─────────────────────────────
# TRENDING: H4 ADX must be at least this for trend strategies
MIN_TREND_ADX = 25
# RANGING: H4 ADX must be at most this for range strategy
MAX_RANGE_ADX = 25

# Daily ADX — only used as additional confirmation in trending regime
MIN_DAILY_ADX = 30

# EMA 20/50 trend confirmation filter
USE_EMA_FILTER = True

# Legacy aliases (kept for compatibility)
MIN_H4_ADX = MIN_TREND_ADX