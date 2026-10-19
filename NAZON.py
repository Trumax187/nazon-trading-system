#Creating a variable
name = "NAZON"
version = 1
balance = 1000.00
Running = True
#Printing them
print("Name: ", name)
print("version: ", version)
print("Balance: ", balance)
print("Running: ", Running)

#More examples for NAZON
pair = 'XAUUSD' # The Gold pair we are trading
price = 2345.50 # Current Gold price
lot_size = 0.04 # How many lots to trade
stop_loss = 2321.00 #SL price
take_profit = 2394.50 #TP price
connected = False # MT5 not connected
signal = "BUY" #Trade direction
confidence = "82%" # AI confidence score
print("Pair: ", pair)
print("Price: ", price)
print("lot size: ", lot_size)
print("Stop Loss: ", stop_loss)
print("Take Profit: ", take_profit)
print("Connected: ", connected)
print("Signal: ", signal)
print("Confidence: ", confidence)

# Updating variables
balance = 100.0
print("Balance: ", balance)
# After winning a trade
balance = balance + 20.00
print("Balance: ", balance)
# MT5 just connected
connected = False
connected = True
print("Connected: ", connected)

# Math with variables
entry = 2345.50
stop_loss = 2321.00
take_profit = 2394.50
risk_pips = entry - stop_loss
reward_pips = take_profit - entry
rr_ratio = reward_pips / risk_pips
print("Risk: ", risk_pips, "points")
print("Reward: ", reward_pips, "points")
print("R:R : 1 : ", rr_ratio,)

# practice
pair1 = "XAUUSD"
pair2 = "USDJPY"
pair3 = "GBPUSD"
pair4 = "EURUSD"
entry = 1.2745
stop_loss = 1.2680
take_profit = 1.2880
risk_pips = entry - stop_loss
reward_pips = take_profit - entry
rr_ratio = reward_pips / risk_pips
valid_trade = True
print("Risk: ", risk_pips)
print("Reward: ", reward_pips)
print("R:R : 1 : ", rr_ratio)
balance = 1000.00
balance += 50
print(balance)

# LESSON 2 (STRINGS AND F-STRINGS)
pair1 = 'XAUUSD'
pair2 = "GBPUSD"
msg = 'NAZON is online!'
print(pair1)
print(pair2)
print(msg)
# Joining strings
pair = 'XAUUSD'
signal = 'BUY'
# Old way of joining strings with +
msg = 'Signal for ' + pair + ' is: ' + signal
print(msg)
# Better way of using f-string (use it in NAZON!)
msg = f'Signal for {pair} is: {signal}'
print(msg)
# f-Strings with Numbers
pair = 'XAUUSD'
price = 2345.50
rsi = 68.5
confidence = 82
print(f'Pair : {pair}')
print(f'Price : {price}')
print(f'RSI : {rsi}')
print(f'Confidence : {confidence}%')
# Round to 2 decimal places inside   the f-string
lot = 0.0431667
print(f'Lot Size : {lot:.2f}')
# Building the AI Prompt (Real NAZON Code)
# This is how NAZON sends data to Claude AI.
pair = 'XAUUSD'
price = 2345.50
rsi = 68.5 # RSI = Relative Strength Index fromm 0 to 100
macd = 0.0012 # Moving Average Convergence Divengence
ema200 = 2300.00 # Exponential Moving Average
balance = 1000.00

prompt = f'''
You are NAZON AI, a professional forex analyst.
Analyse the following setup for the swing trading:
Pair : {pair}
Price : {price}
RSI(14) : {rsi}
MACD : {macd}
EMA : {ema200}
Balance : {balance}
Give a signal: BUY, SELL, or WAIT.
Include confidence (0-100) and one reason.
'''
print(prompt)

pair = ' xauusd'
# Remove spaces
print(pair.strip())
# Make uppercase
print(pair.strip().upper())
print(pair.strip().lower())
# Replace part of the string
print('XAUUSD'.replace('XAU', 'GBP'))
# Checking if something is inside
print('XAU' in 'XAUUSD')
print('JPY' in 'XAUUSD')
# Length of a string
print(len("XAUUSD"))
# Split a string
msg = 'SIGNAL:BUY:82'
parts = msg.split(":")
print(parts)

#PRACTICE QUESTIONS
pair = 'gbpusd'
print('Pair: ', pair.strip().upper())
pair = 'GBPUSD'
entry = 1.2745
stop_loss = 1.2680
take_profit = 1.2880
print(f'Pair: {pair} | Entry: {entry} | SL: {stop_loss} | TP: {take_profit}')
msg = 'PAIR:XAUUSD:SIGNAL:BUY'
parts = msg.split(':')
print(parts)
print("USD" in msg)
#NAZON AI PROFESSIONAL FOREX ANALYST
pair = 'EURUSD'
price = 2345.50
rsi = 72.5 # RSI = Relative Strength Index fromm 0 to 100
macd = 0.0012 # Moving Average Convergence Divengence
ema200 = 2300.00 # Exponential Moving Average
balance = 10000.00

prompt = f'''
You are NAZON AI, a professional forex analyst.
Analyse the following setup for the swing trading:
Pair : {pair}
Price : {price}
RSI(14) : {rsi}
MACD : {macd}
EMA : {ema200}
Balance : {balance}
Give a signal: BUY, SELL, or WAIT.
Include confidence (0-100) and one reason.
'''
print(prompt)

# Practice: Lists
pairs = ('EURUSD', 'GBPUSD', 'XAUUSD', 'USDJPY')
closes = [2340.5, 2345.0, 2350.5, 2347.5]

print(len(closes))
avg = sum(closes) / len(closes)
print(max(closes))
print(min(closes))
print(f'Average: {round(avg)}')
signals = ['BUY', 'WAIT', 'SELL', 'BUY']
buy_count = signals.count('BUY')
print(buy_count)
print(pairs[0 : 2])
# NAZON stores al pair signals in one dictionary
all_signals = {
    'XAUUSD': {'direction' : 'BUY', 'confidence': 82, 'entry': 2345.50},
    'GBPUSD': {'direction': 'SELL', 'confidence': 75, 'entry': 1.2745},
    'EURUSD': {'direction': 'WAIT', 'confidence': 45, 'entry': 1.0850},
    'USDJPY': {'direction': 'WAIT', 'confidence': 70, 'entry': 149.50},
}
# Access nested values
print(all_signals['XAUUSD']['direction'])
print(all_signals['GBPUSD']['confidence'])
# Loop through all pairs
for pair, data in all_signals.items():
    print(f"{pair}: {data['direction']} ({data['confidence']}%)")

rsi = 65.0
macd = 0.0015 # positve = bullish momentum
trend = 'bullish' # price is above EMA 200
price = 2345.50
ema200 = 2300.00
if trend == 'bullish' and rsi < 70 and macd > 0:
    signal = 'BUY'
elif trend == 'bearish' and rsi > 30 and macd < 0:
    signal = 'SELL'
else:
    signal = 'WAIT'

print(f'NAZON Signal: {signal}')
# Risk Management Checks
# core/risk_manager.py - NAZON runs these before every trade
balance = 1000.00
daily_loss = -45.00 # how much lost today
max_loss = -50.00 # daily loss limit
rr_ratio = 2.0 # risk:reward
confidence = 82 # AI confidence

if daily_loss <= max_loss:
    print('BLOCKED: Daily loss limit reached!')
elif rr_ratio < 1.5:
    print('BLOCKED: Risk:Reward too low!')
elif confidence < 65:
    print('BLOCKED: AI not confident enough!')
else:
    print('APPROVED: Trade meets all NAZON Criterial')
# 'and' - BOTH must be TRUE
rsi = 65
trend = 'bullish'
if rsi < 70 and trend == 'bullish':
    print("Both condtions met - BUY possible")
# 'or' - at least ONE must be TRUE
pair = 'XAUUSD'
if pair == 'XAUUSD' or pair == 'GBPUSD':
    print(f'{pair} is a NAZON priority pair')
# 'not' - reverses TRUE/FALSE
connected = False
if not connected:
    print("MT5 is not connected - reconnecting...")

#Nested if statements
pair = 'XAUUSD'
confidence = 82
rr_ratio = 2.0
signal = 'BUY'
if signal != 'WAIT':
    if confidence >= 70:
        if rr_ratio >= 1.5:
            print(f'NAZON: Execute {signal} on {pair}')
            print(f'Confidence: {confidence}% | RR: 1:{rr_ratio}')
else:
    print('RR too low - skip')

# 13th March, 2026.
# NAZON FOR LOOP
pairs = ['XAUUSD', 'GBPUSD', 'EURUSD', 'USDJPY']
for pair in pairs:
    print(f'Scanning {pair}...')
for i, pair in enumerate(pairs, 1):
    print(f'{i}. Analysing {pair}')
signals = {}
rsi_data = {
    'XAUUSD' : 65.0,
    'GBPUSD' : 72.5,
    'EURUSD' : 44.0,
    'USDJPY' : 28.5,
}
for pair in pairs:
    rsi = rsi_data[pair]
    if rsi > 70:
        signals[pair] = 'SELL'
    elif rsi < 30:
        signals[pair] = 'BUY'
    else:
        signals[pair] = "WAIT"
print(f'{pair}: RSI = {rsi} => {signals[pair]}') 

# WHILE LOOP for NAZON
import time
scan_count = 0
max_scans = 3 # in real NAZON this runs  forever
while scan_count < max_scans:
    scan_count += 1
    print(f'Scan #{scan_count} - Checking all pairs...')
    print(" XAUUSD: BUY")
    print(' GBPUSD: WAIT')
    print(f' Scan complete. Next scan in 4 hours.')
    print()
print('Max scans reached - NAZON stopped.')

# Break and control in NAZON
pairs = ['XAUUSD', 'GBPUSD', 'EURUSD', 'USDJPY']
bad_pair = 'EURUSD' # pretend connection failed for this
for pair in pairs:
    if pair == bad_pair:
        print(f'Skipping {pair} - no data')
        continue # skip to next pair
    print(f'Analysed {pair} successfully')
print('---')

# Stop scanning if critical error happens
for pair in pairs:
    if pair == 'GBPUSD':
        print('Critical error - stopping all scans!')
        break # exit the loop
    print(f'Scanned {pair} succefully')

# PRACTICE
pairs = ['GBPUSD', 'XAUUSD', 'EURUSD', 'USDJPY']
pairs = rsi_data.keys()
for I in pairs:
    print(f'Checking {I}...')
signals = {}
rsi_data = {
    'XAUUSD' : 65.0,
    'GBPUSD' : 72.5,
    'EURUSD' : 50.0,
    'USDJPY' : 28.5,
}
for pair in pairs:
    rsi = rsi_data[pair]
    if rsi > 70:
        signals[pair] = 'SELL'
    elif rsi < 30:
        signals[pair] = 'BUY'
    else:
        signals[pair] = "WAIT"
    print(f'{pair}: RSI = {rsi} => {signals[pair]}') 
for i, pair in enumerate(pairs, 1):
    print(f'{i}. Analysing {pair}...')
scan_count = 0
scan_max = 3
while scan_count < scan_max:
    scan_count += 1
    print(f'Scan #{scan_count} complete')
for pair in pairs:
    if pair == 'EURUSD':
        continue
    print(pair)
# Functions
# Basic Function
def greet():
    print('NAZON Forex Analyser is online!')
    print('Connecting to MT5...')
greet()
# Function with Parameters
def analyse_pair(pair, timeframe):
    print(f'Analying {pair} on {timeframe} chart...')
    print(f'Fetching last 50 candles for {pair}')
analyse_pair('XAUUSD', 'H4')
analyse_pair('GBPUSD' , 'D1')
analyse_pair('EURUSD', 'H4')
# Return Function
def calculate_rr(entry, sl, tp):
    risk = abs(entry - sl)
    reward = abs(tp - entry)
    rr = reward / risk
    return round(rr, 2)
def get_signal(rsi):
    if rsi > 70:
        return 'SELL'
    elif rsi < 30:
        return 'BUY'
    else:
        return 'WAIT'
#Use the functions
rr = calculate_rr(entry=2345.5, sl=2321.0, tp=2394.5)
print(f'R:R ratio: 1:{rr}')
sig = get_signal(rsi=28.5)
print(f'RSI Signal: {sig}')
# Lot Size Calculator
# core/risk_manager.py
def calculate_lot_size(balance, risk_pct, sl_points, pip_value = 0.1):
    '''
    Calculate lot size to risk a % of balance.
    balance : account balance in USD
    risk_pct : e.g. 0.01 for 1%
    sl_points : stop oss distance in points
    pip_value : value of 1 pip for this pair
    Returns : lot  size rounded to 2 decimmal places
    '''
    risk_dollars = balance * risk_pct
    lot_size = risk_dollars / (sl_points*pip_value)
    return round(lot_size, 2)

# Test it:
balance = 1000.00
sl_pts = 245 # 24.5 points on Gold
lot = calculate_lot_size(balance, 0.001, sl_pts)
print(f'1% risk lot size : {lot}')
lot2 = calculate_lot_size(balance, 0.002, sl_pts)
print(f'2% risk lot size : {lot2}')
# Default Parameters
def scan_pair(pair, timeframe = 'H4', candles = 50, risk = 0.01):
    print(f'Scanning {pair}')
    print(f'Timeframe : {timeframe}')
    print(f'Candles : {candles}')
    print(f'Risk : {risk*100}%')
# Uses all defaults
scan_pair('XAUUSD')
print()
# Override timeframe only
scan_pair('GBPUSD', timeframe= 'D1')
print()
# Override multiple
scan_pair('EURUSD', timeframe= 'D1', candles=100, risk=0.02)

# Returning Multiple Values

def get_trade_levels(entry, risk_pct= 0.01, rr = 2.0):
    '''
    Returns SL and TP based on entry and RR.
    '''
    risk_points = entry * risk_pct
    stop_loss = round(entry - risk_points, 2)
    take_profit = round(entry + risk_points * rr, 2)
    return stop_loss, take_profit
entry = 2345.50
sl, tp = get_trade_levels(entry)
print(f'Entry : {entry}')
print(f'SL : {sl}')
print(f'TP : {tp}')

#PRACTICE : FUNCTIONS
def get_signals(rsi):
    if rsi > 70:
        return 'SELL'
    elif rsi < 30:
        return 'BUY'
    else:
        return 'WAIT'
# Use the functions
rr = calculate_rr(entry=2345.5, sl=2321.0, tp=2394.5)
print(f'R:R ratio : 1: {rr}')
sig = get_signal(rsi= 29.0)
print(f'RSI Signal : {sig}')

#LOT SIZE CALCULATOR
# Lot size is the number of currency units (transaction amounts) bought or sold as a unit of measurements for trade size!
#core/risk_manager.py
def calculate_lot_size(balance, risk_pct, sl_points, pip_value=0.1):
    '''
    Calculate lot size to risk a % of balance.
    balance : account balance in USD
    risk_pct : e.g 0.01 for 1%
    sl_points : stop lose distance in points
    pip_value : value of 1 pip for this pair
    Returns : lot size rounded to 2 decimal places
    '''
    risk_dollars = balance * risk_pct
    lot_size = risk_dollars / (sl_points * pip_value)
    return round(lot_size, 2)
# Testing it
balance = 1000.00
sl_pts = 245 # 24.5 points on Gold
lot = calculate_lot_size(balance, 0.001, sl_pts)
print(f'1% risk lot size : {lot}')
lot2 = calculate_lot_size(balance, 0.002, sl_pts)
print(f' 2% risk lot size : {lot2}')

# LIBRARIES & IMPORTS
#EXAMPLE 1 - THREE WAYS TO IMPORT
# Way 1: import whole library with alias
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
# Way 2: import specific function only
from datetime import datetime
from os import getenv
# Way 3: import everything (use carefully)
from math import *
# Using them:
now = datetime.now()
print(f'NAZON started at: {now}')
# EXAMPLE 2 - DATETIME LIBRARY USED IN TRADE JOURNAL
from datetime import datetime
now = datetime.now()
print(now)
print(now.strftime('%Y-%m-%D %H:%M'))
print(now.strftime('%D/%m%Y'))
print(now.hour)
print(now.minute)
# EXAMPLE 3 - OS LIBRARY (READING .ENV)
import os
# Set an environment variable (normally done in .env file)
os.environ['NAZON_VERSION'] = '1.0'
# Read it back
version = os.getenv('NAZON_VERSION')
print(f'NAZON version: {version}')
#Check if a path/file exists
print(os.path.exists('data/trades.db'))
import pandas as pd
# Creating a simple table like a spreadsheet
data = {
    'pair' : ['XAUSD', 'GBPUSD', 'EURUSD', 'USDJPY'],
    'signal' : ['BUY', 'SELL', 'WAIT', 'BUY'],
    'confidance' : [82, 75, 45, 70],
}
df = pd.DataFrame(data)
print(df)



# INTERMEDIATE NAZON VERSION 1.0
# Classes and Object-Oriented Programming (OOP)
class TradeSignal:
    def __init__(self, pair, direction, confidence):
        self.pair = pair
        self.direction = direction
        self.confidence = confidence

    def is_strong(self):
        return self.confidence >= 70
    
    def display(self):
        status = 'STRONG' if self.is_strong() else 'WEAK'
        print(f'{self.pair}: {self.direction} | {self.confidence}% | {status}')
# Create objects from the blueprint
s1 = TradeSignal('XAUUSD', 'BUY', 82)
s2 = TradeSignal('GBPUSD', 'SELL', 55)
s3 = TradeSignal('EURUSD', 'WAIT', 40)
s1.display()
s2.display()
s3.display()

# The RiskManager Class
class RiskManager:
    def __init__(self, balance, risk_pct = 0.1, min_rr = 1.5):
        self.balance = balance
        self.risk_pct = risk_pct
        self.min_rr = min_rr
    def get_risk_amount(self):
        return self.balance * self.risk_pct
    def calculate_lot(self, sl_points, pip_value = 1):
        risk = self.get_risk_amount()
        return round(risk / (sl_points * pip_value), 2)

    def is_valid_rr(self, sl, tp, entry):
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        rr = reward / risk
        return rr >= self.min_rr

    def check_trade(self, sl, tp, entry):
        if not self.is_valid_rr(sl, tp, entry):
         return False, 'RR to low'
        return True, 'Trade approved'

rm = RiskManager(balance=1000, risk_pct=0.01)
print(f'Risk amount : ${rm.get_risk_amount()}')
print(f'Lot size : {rm.calculate_lot(245)}')
ok, msg = rm.check_trade(entry=2345.5, sl=2321.0, tp=2395.5)
print(f'Trade valid : {ok} - {msg}')

class MT5Connector:
    def __init__(self):
        self.connected = False
        self.account = None
    def connect(self):
        #in real code: mt5. initialize()
        self.connected = True
        self.account = {'balance' : 1000.0, 'equity' : 1024.5}
        print('Connected to MT5!')
        return True
    def get_balance(self):
        if not self.connected:
            return None
        return self.account['balance']
    def disconnect(self):
        self.connected = False
        print('Disconnected from MT5.')
    def status(self):
        state = 'ONLINE' if self.connected else 'OFFLINE'
        print(f'MT5 Status: {state}')
conn = MT5Connector()
conn.status()
conn.connect()
conn.status()
print(f'Balance: ${conn.get_balance()}')
conn.disconnect()
conn.status()

#ERROR HANDLING (try / except)
#Example 1 - Baic try/except
#print (1/0) # ZeroDivisionError: division by zero
#with error handling
try:
    result = 1 / 0
except ZeroDivisionError:
    print('Cannot divide by zero!')
    result = 0
print(f'Result: {result}')
print('App is still running!')
#Example 2 - Multiple ecept Blocks
def safe_divide(a, b):
    try:
        result = a / b
        return result
    except ZeroDivisionError:
        print('Error: Cannot divide by zero')
        return None
    except TypeError:
        print('Error: Both inputs must be numbers')
        return None
    
print(f'Division Result: {safe_divide(10, 2)}')
print(safe_divide(10, 0))
print(safe_divide(10, 'x'))

# Example 3 - NAAZON MT5 Safe Connection
class MT5Connector:
    def __init__(self):
        self.connected = False
    def connect(self):
        try:
            #Stimulate connection attempt
            #In real code: mt5.initialize()
            print('Attempting MT5 connection...')
            self.connected = True
            print('Connected successfuly!')
            return True
        except Exception as e:
            print(f'Connection failed: {e}')
            self.connected = False
            return False
    def get_candles(self, pair):
        try:
            if not self.connected:
                raise ConnectionError('MT5 not connected')
            print(f'Fetching {pair} candles...')
            return [] # would return real candles
        except ConnectionError as e:
            print(f'Cannot fetch {pair}: {e}')
            return None
conn = MT5Connector()
conn.get_candles('XAUUSD') # not connected yet
conn.connect()
conn.get_candles('XAUUSD') #now connected

#  Try / except / else / fianlly
def scan_pair(pair):
    try:
        print(f'Scanning {pair}...')
        if pair not in ['XAUUSD', 'GBPUSD', 'EURUSD', 'USDJPY']:
            raise ValueError(f'{pair} is not a valid NAZON pair')
        result = 'BUY'
    except ValueError as e:
        print(f'Invalid pair error: {e}')
        result = None
    except Exception as e:
        print(f'Unexpected error: {e}')
        result = None
    else:
        # Only runs if NO exception happened
        print(f' Signal: {result}')
    finally:
        # ALWAYS  runs - error or not
        print(f' Scan of {pair} complete.')
        return result
scan_pair('XAUUSD')
print()
scan_pair('BTCUSD')

  # Working with Files & CSV
  # Write to a file
with open('nazon_log.txt', 'a') as f:
    f.write('NAZON Trade Log\n')
    f.write('==================\n')
    f.write('XAUUSD BUY 2345.50\n')
    f.write('GBPUSD SELL 1.2745\n')

    # Read it back
with open('nazon_log.txt', 'r') as f:
    content = f.read()
print(content)

    # Read Line by Line
with open('nazon_log.txt', 'r') as f:
    lines = f.readlines()
for i, line in enumerate(lines, 1):
    print(f'Line {i}: {line.strip()}')

# CSV Trade Journal
import csv
from datetime import datetime
def log_trade(pair, direction, entry, sl, tp, lot):
    with open('trades.csv', 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now() .strftime('%Y-%m-%D %H:%M'),
            pair, direction,
            entry, sl, tp, lot
        ])
    print(f'Logged: {pair} {direction} @ {entry}')
# Log some trades
log_trade('XAUUSD', 'BUY', 2345.50, 2321.00, 2394.50, 0.04)
log_trade('GBPUSD', 'SELL', 1.2745, 1.2820, 1.2680, 0.10)
log_trade('USDJPY', 'BUY', 149.50, 148.20, 151.90, 0.05)
# Read trades back
with open('trades.csv', 'r') as f:
    reader = csv.reader(f)
    for row in reader:
        print(row)

# Pandas & DataFrames
import pandas as pd
#Stimulate what MT5 gives us
data = {
    'time': ['2026-01-01', '2026-01-02', '2026-01-03', '2026-01-04', '2026-01-05'],
    'open' : [2330.0, 2335.0, 2340.0, 2345.0, 2350.0],
    'high' : [2345.0, 2340.0, 2350.0, 2360.0, 2365.0],
    'low' : [2320.0, 2325.0, 2330.0, 2340.0, 2345.0],
    'close' : [2335.0, 2340.0, 2345.0, 2350.0, 2355.0],
    'volume' : [18420, 21300, 19800, 22100, 17500],
}
df = pd.DataFrame(data)
print(df)

# Reading Data from DataFrame
closes = df['close']
print('Close prices:')
print(closes.tolist())
# Most recent close
latest = df['close'].iloc[-1]
print(f'Latest close: {latest}')
# Last 3 rows
print(df.tail(3))
# Basic statistics
print(f'Highest close: {df["close"].max()}')
print(f'Lowest close: {df["close"].min()}')
print(f'Average close: {df["close"].mean()}')
# Adding indicator Columns
# Add useful columns
df['bullish'] = df['close'] > df['open']
df['body_size'] = abs(df['close'] - df['open'])
df['wick_size'] = df['high'] - df[['open', 'close']].max(axis=1)
df['wick_down'] = df[['open', 'close']].min(axis=1) - df['low']
print(df[['time', 'close', 'bullish', 'body_size']].to_string())
# Pandas-ta indicators (REAL NAZON)
# pip install pandas-ta
import pandas_ta as ta
# Add RSI
df['RSI'] = ta.rsi(df['close'], length=3) #lenth = 3 for short data
# Add EMA
df['ema3'] = ta.ema(df['close'], length=3)
print(df[['time', 'close', 'RSI', 'ema3']].tail(3).to_string())
# Get the latest values
latest_rsi = df['RSI'].iloc[-1]
latest_ema = df['ema3'].iloc[-1]
print(f'Latest RSI: {round(latest_rsi, 2)}')
print(f'Latest EMA: {round(latest_ema, 2)}')

# .env Files & config management
# Create a file called: .env
# Put it in your project root folder (same level as main.py)
CLAUDE_API_KEY="sk-ant-your-real-key-here"
MT5_LOGIN=12345678
MT5_PASSWORD="yourPassword"
MT5_SERVER="YourBroker-MT5Demo"
DEFAULT_RISK=0.01
# MAX_DAILY_LOSS=0.05
# Creating a config.py to Read the .env
# config.py - central settings file for all NAZON
import os
# pip install python-dotenv
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return None
# Loading the .env file (if available)
load_dotenv()
# Credentials (secret - from .env)
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
MT5_LOGIN = os.getenv('MT5_LOGIN')
MT5_PASSWORD = os.getenv('MT5_PASSWORD')
MT5_SERVER = os.getenv('MT5_SERVER')
# Risk Management Settings (from .env)
DEFAULT_RISK = float(os.getenv('DEFAULT_RISK', 0.01))
MAX_DAILY_LOSS = float(os.getenv('MAX_DAILY_LOSS', 0.05))
# Trading config (not secret - hardcoded here is fine
PAIRS = ['XAUUSD', 'GBPUSD', 'EURUSD', 'USDJPY']
TIMEFRAME = 'H4'
RSI_PERIOD = 14
MIN_RR = 1.5
MIN_CONFIDENCE = 70
CANDLE_COUNT = 100
# In any NAZON file, just import it needed:
# from config import PAIRS, TIMEFRAME, MIN_RR, MIN_CONFIDENCE
# Now you can use these settings anywhere in NAZON code:
for pair in PAIRS:
    print(f'Will scan {pair} on {TIMEFRAME}')
    print(f'Min RR : {MIN_RR}')
    print(f'Min Confidence : {MIN_CONFIDENCE}%')


# Create .gitignore
with open('.gitignore', 'w') as f:
    f.write('.env\n')
    f.write('__pycache__/\n')
    f.write('*.pyc\n')
    f.write('data/trades.db\n')
    f.write('*.log\n')
# WHAT WILL BE HAPPENING WHEN NAZON CALLS AI
#This is the flow
# 1. NAZON collects: pair, price, rsi, macd, ema200, balance
# 2. NAZON builds a text prompt describing the market
# 3. NAZON sends the prompt to AI (Claude API)
# 4. NAZON reads the AI response: signal, confidence, reason and acts on it.
# pip install openai
# Get your API key: console.openai.com
import anthropic
import os
from dotenv import load_dotenv
load_dotenv()
client = anthropic.Client(api_key=os.getenv('CLAUDE_API_KEY'))
response = client.messages.create(
    model = 'claude-4-2026-03-14',
    max_tokens = 100,
    messages = [
        {
            'role' : 'user',
                'content' : 'Say hello from NAZON!'}
    ]
)
print(response.choices[0].message.content)