#!/usr/bin/env python3
"""NAZON Forward Logger — records every signal for paper trading validation."""
import csv
import os
from datetime import datetime

LOG_FILE = "nazon_forward_log.csv"

def log_signal(symbol, direction, confidence, entry, stop, tp1, tp2, tp3, lots):
    """Append a signal to the forward-test log."""
    file_exists = os.path.isfile(LOG_FILE)
    
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "timestamp", "symbol", "direction", "confidence",
                "entry", "stop", "tp1", "tp2", "tp3", "lots",
                "outcome", "exit_price", "r_multiple", "notes"
            ])
        writer.writerow([
            datetime.now().isoformat(timespec="seconds"),
            symbol, direction, confidence,
            entry, stop, tp1, tp2, tp3, lots,
            "OPEN", "", "", ""
        ])
    print(f"[LOGGED] {symbol} {direction.upper()} @ {entry} | confidence {confidence}")

def update_outcome(row_index, outcome, exit_price, r_multiple, notes=""):
    """Update a closed trade's outcome."""
    rows = []
    with open(LOG_FILE, "r") as f:
        reader = csv.reader(f)
        rows = list(reader)
    
    if row_index < 1 or row_index >= len(rows):
        print(f"[ERROR] Row {row_index} not found")
        return
    
    rows[row_index][10] = outcome
    rows[row_index][11] = exit_price
    rows[row_index][12] = r_multiple
    rows[row_index][13] = notes
    
    with open(LOG_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    print(f"[UPDATED] Row {row_index}: {outcome} @ {exit_price} ({r_multiple}R)")

def show_log():
    """Print the current log."""
    if not os.path.isfile(LOG_FILE):
        print("No log file yet.")
        return
    
    with open(LOG_FILE, "r") as f:
        reader = csv.reader(f)
        rows = list(reader)
    
    if len(rows) <= 1:
        print("No trades logged yet.")
        return
    
    print(f"\n{'='*80}")
    print(f"FORWARD-TEST LOG ({len(rows)-1} trades)")
    print(f"{'='*80}")
    print(f"{'#':<3} {'Timestamp':<20} {'Symbol':<10} {'Dir':<5} {'Conf':<5} {'Outcome':<8} {'R':<6}")
    print(f"{'-'*80}")
    
    open_count = 0
    win_count = 0
    loss_count = 0
    
    for i, row in enumerate(rows[1:], start=1):
        if len(row) < 11:
            continue
        outcome = row[10] if len(row) > 10 else "?"
        r_val = row[12] if len(row) > 12 else ""
        if outcome == "OPEN":
            open_count += 1
        elif outcome == "WIN":
            win_count += 1
        elif outcome == "LOSS":
            loss_count += 1
        print(f"{i:<3} {row[0][:19]:<20} {row[1]:<10} {row[2]:<5} {row[3]:<5} {outcome:<8} {r_val:<6}")
    
    total_closed = win_count + loss_count
    if total_closed > 0:
        win_rate = win_count / total_closed * 100
        print(f"\nSummary: {open_count} open | {win_count} wins | {loss_count} losses | Win rate: {win_rate:.0f}%")
    else:
        print(f"\nSummary: {open_count} open | 0 closed")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "show":
        show_log()
    else:
        print("Usage:")
        print("  python forward_logger.py show    — view the log")
        print("  Or import it in your signal script:")
        print("    from forward_logger import log_signal")
