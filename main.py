import os
import time
from threading import Thread
from flask import Flask
import pandas as pd
import requests

app = Flask('')


@app.route('/')
def home():
  return 'Bot is running'


def run_flask():
  port = int(os.environ.get('PORT', 8080))
  app.run(host='0.0.0.0', port=port)


Thread(target=run_flask).start()

EXNESS_ACCOUNT = os.environ.get('EXNESS_ACCOUNT')
EXNESS_PASSWORD = os.environ.get('EXNESS_PASSWORD')
EXNESS_SERVER = os.environ.get('EXNESS_SERVER')

SYMBOLS = ['BTCUSDT', 'EURUSD', 'GBPUSD', 'XAUUSD', 'XAGUSDT']
EMA_FAST = 50
EMA_SLOW = 200
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
TIMEFRAME = '5m'


def calculate_rsi(series, period=14):
  delta = series.diff()
  gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
  loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
  rs = gain / loss
  return 100 - (100 / (1 + rs))


def get_market_data(symbol, timeframe='5m', limit=250):
  try:
    url = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval={timeframe}&limit={limit}'
    response = requests.get(url, timeout=10)
    data = response.json()
    df = pd.DataFrame(data, columns=[
        'timestamp',
        'open',
        'high',
        'low',
        'close',
        'volume',
        'close_time',
        'quote_asset_volume',
        'number_of_trades',
        'taker_buy_base_asset_volume',
        'taker_buy_quote_asset_volume',
        'ignore',
    ])
    df['close'] = df['close'].astype(float)
    return df
  except Exception as e:
    print(f'Error fetching data for {symbol}: {e}')
    return None


def execute_trade(symbol, trade_type):
  print(
      f'EXECUTING {trade_type} FOR {symbol} ON ACCOUNT {EXNESS_ACCOUNT} ('
      f'{EXNESS_SERVER})'
  )


def analyze_symbol(symbol):
  df = get_market_data(symbol, TIMEFRAME)
  if df is None or len(df) < EMA_SLOW:
    return

  df['ema_fast'] = df['close'].ewm(span=EMA_FAST, adjust=False).mean()
  df['ema_slow'] = df['close'].ewm(span=EMA_SLOW, adjust=False).mean()
  df['rsi'] = calculate_rsi(df['close'], RSI_PERIOD)

  latest = df.iloc[-1]
  price = latest['close']
  ema_f = latest['ema_fast']
  ema_s = latest['ema_slow']
  rsi = latest['rsi']

  print(
      f'[{symbol}] Price: {price:.4f} | EMA{EMA_FAST}: {ema_f:.4f} |'
      f' EMA{EMA_SLOW}: {ema_s:.4f} | RSI: {rsi:.2f}'
  )

  if ema_f > ema_s and rsi <= RSI_OVERSOLD:
    print(f'BUY SIGNAL DETECTED FOR {symbol}')
    execute_trade(symbol, 'BUY')
  elif ema_f < ema_s and rsi >= RSI_OVERBOUGHT:
    print(f'SELL SIGNAL DETECTED FOR {symbol}')
    execute_trade(symbol, 'SELL')


if __name__ == '__main__':
  while True:
    for symbol in SYMBOLS:
      analyze_symbol(symbol)
      time.sleep(2)
    time.sleep(30)
