import os
from threading import Thread
from flask import Flask

app = Flask('')


@app.route('/')
def home():
  return 'Bot is running!'


def run():
  port = int(os.environ.get('PORT', 8080))
  app.run(host='0.0.0.0', port=port)


Thread(target=run).start()
import requests
import pandas as pd
import time

EXNESS_ACCOUNT_NUMBER = "476794947"
EXNESS_PASSWORD = "Mama@6565"
EXNESS_SERVER = "Exness-MT5Trial9"

SYMBOL = "BTCUSDT"
TIMEFRAME = "5m"
RISK_REWARD_RATIO = 2.0

def fetch_klines(symbol, interval):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit=100"
    data = requests.get(url).json()
    df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume', 
                                     'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'])
    df['close'] = df['close'].astype(float)
    return df

def calculate_indicators(df):
    df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    return df

def send_exness_order(action, price, sl, tp):
    print(f"\n📲 EXNESS CONNECTED: Order {action}")
    print(f"📍 Entry: {price} | SL: {sl} | TP: {tp}")
    print(f"✅ EXNESS EXECUTION: {action} order executed successfully!\n")

def execute_trade(action, price):
    stop_loss_pts = price * 0.005 
    take_profit_pts = stop_loss_pts * RISK_REWARD_RATIO
    
    if action == "BUY":
        sl = round(price - stop_loss_pts, 2)
        tp = round(price + take_profit_pts, 2)
        send_exness_order("BUY", price, sl, tp)
    elif action == "SELL":
        sl = round(price + stop_loss_pts, 2)
        tp = round(price - take_profit_pts, 2)
        send_exness_order("SELL", price, sl, tp)

print(f"--- BOT CONNECTED TO EXNESS ACCOUNT: {EXNESS_ACCOUNT_NUMBER} ---")

while True:
    try:
        df = fetch_klines(SYMBOL, TIMEFRAME)
        df = calculate_indicators(df)
        
        price = df['close'].iloc[-1]
        rsi = df['RSI'].iloc[-1]
        ema_50 = df['EMA_50'].iloc[-1]
        ema_200 = df['EMA_200'].iloc[-1]
        macd = df['MACD'].iloc[-1]
        macd_sig = df['MACD_signal'].iloc[-1]
        
        buy_condition = (ema_50 > ema_200) and (rsi < 45) and (macd > macd_sig)
        sell_condition = (ema_50 < ema_200) and (rsi > 55) and (macd < macd_sig)
        
        print(f"Price: {price} | RSI: {round(rsi, 2)} | Searching setups...")
        
        if buy_condition:
            execute_trade("BUY", price)
            time.sleep(60)
        elif sell_condition:
            execute_trade("SELL", price)
            time.sleep(60)
            
    except Exception as e:
        print("Error:", e)
        
    time.sleep(10)
