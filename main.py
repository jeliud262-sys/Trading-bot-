import asyncio
import os
import time
from flask import Flask
from metaapi_cloud_sdk import MetaApi
import pandas as pd
import requests
from threading import Thread

# Chukua credentials kutoka Render Environment Variables
META_API_TOKEN = os.environ.get('META_API_TOKEN')
META_ACCOUNT_ID = os.environ.get('META_ACCOUNT_ID')

# Orodha ya Pair na Mipangilio ya Mkakati
SYMBOLS = ['BTCUSDT', 'EURUSD', 'GBPUSD', 'XAUUSD', 'XAGUSDT']
TIMEFRAME = '5m'
EMA_SHORT = 50
EMA_LONG = 200
RSI_PERIOD = 14

app = Flask(__name__)


@app.route('/')
def home():
  return 'Trading Bot na MetaApi Exness Inafanya Kazi!'


def keep_alive():
  app.run(host='0.0.0.0', port=8080)


def fetch_klines(symbol, interval=TIMEFRAME, limit=250):
  url = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}'
  res = requests.get(url).json()
  df = pd.DataFrame(
      res,
      columns=[
          'time',
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
      ],
  )
  df['close'] = df['close'].astype(float)
  return df


def calculate_indicators(df):
  # Kuhesabu Exponential Moving Averages (EMA)
  df['ema_50'] = df['close'].ewm(span=EMA_SHORT, adjust=False).mean()
  df['ema_200'] = df['close'].ewm(span=EMA_LONG, adjust=False).mean()

  # Kuhesabu Relative Strength Index (RSI)
  delta = df['close'].diff()
  gain = (delta.where(delta > 0, 0)).rolling(window=RSI_PERIOD).mean()
  loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIOD).mean()
  rs = gain / loss
  df['rsi'] = 100 - (100 / (1 + rs))

  return df


async def send_order(symbol, trade_type):
  try:
    api = MetaApi(token=META_API_TOKEN)
    account = await api.metatrader_account_api.get_account(META_ACCOUNT_ID)
    connection = account.get_rpc_connection()
    await connection.connect()
    await connection.wait_synchronized()

    # Kubadilisha jina la pair kuendana na Exness MT5 (Mfano: BTCUSDT kuwa BTCUSD)
    mt5_symbol = symbol.replace('USDT', 'USD')

    if trade_type == 'BUY':
      res = await connection.create_market_buy_order(
          symbol=mt5_symbol, volume=0.01
      )
    else:
      res = await connection.create_market_sell_order(
          symbol=mt5_symbol, volume=0.01
      )

    print(
        f'SUCCESS: Oda ya {trade_type} imefanikiwa kufunguka Exness kwa'
        f' {mt5_symbol}: {res}'
    )
  except Exception as e:
    print(f'ERROR: Imeshindikana kutuma oda kupitia MetaApi: {e}')


def execute_trade(symbol, trade_type):
  print(f'Inatuma signal ya {trade_type} ya {symbol} kwenda Exness MT5...')
  asyncio.run(send_order(symbol, trade_type))


def run_bot():
  while True:
    try:
      for symbol in SYMBOLS:
        df = fetch_klines(symbol)
        df = calculate_indicators(df)

        # Kutumia candle iliyofungwa hivi karibuni (-2)
        last_row = df.iloc[-2]

        ema_50 = last_row['ema_50']
        ema_200 = last_row['ema_200']
        rsi = last_row['rsi']
        close_price = last_row['close']

        print(
            f'[{symbol}] Bei: {close_price} | EMA50: {ema_50:.2f} | EMA200:'
            f' {ema_200:.2f} | RSI: {rsi:.2f}'
        )

        # Masharti ya kuingia Trade
        if ema_50 > ema_200 and rsi > 50:
          execute_trade(symbol, 'BUY')
        elif ema_50 < ema_200 and rsi < 50:
          execute_trade(symbol, 'SELL')

    except Exception as e:
      print(f'Kosa kwenye mzunguko wa bot: {e}')

    # Subiri dakika 5 kabla ya kuangalia tena
    time.sleep(300)


if __name__ == '__main__':
  # Anzisha Flask server kwenye thread ya pembeni
  t = Thread(target=keep_alive)
  t.start()

  # Anzisha mzunguko wa bot
  run_bot()
