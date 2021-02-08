import ccxt
import time
import talib
import pandas as pd
import logging

logger = logging.getLogger()
logger.setLevel(logging.ERROR)
file_handler = logging.FileHandler(filename="error.log")
logger.addHandler(file_handler)

coin_list = []

file = open('coin_list.txt', 'r')
while (1):
    line = file.readline()
    try:
        escape = line.index('\n')
    except:
        escape = len(line)

    if line:
        coin_list.append(line[0:escape])
    else:
        break
file.close

exchange = ccxt.bithumb({'apiKey':'access Key 입력',
                    'secret':'Secret Key 입력',
                    'enableRateLimit': False, #변동성 돌파는 시장가로 매매, 시장가가 싫으면 True로.
                    })

def run():
    print('Bollinger Bot Start')
    while True:
        try:
            time.sleep(1)
            for ticker in coin_list:
                df = getCandleStick(ticker)
                curPrice = getCurrPrice(ticker)
                signal = getSignalBB(df, curPrice)
                stopPrice = getStopPrice(df)
                #macdSignal = getMACDSignal(df)
                if signal == 1 : #and macdSignal == 1: #매수
                    balance = getBalance()  # 잔고
                    invest_price = float(balance) / len(coin_list)
                    ticker_amt = getTickerAmt(ticker)
                    if ticker_amt == 0.0: #매수한 가상화폐가 없으면
                        buyTransNo = buy_crypto_currency(ticker, invest_price) # 매수
                        print(ticker + 'buy!!')
                elif signal == -1 or curPrice < stopPrice: #매도
                    unit = getTickerAmt(ticker)
                    if unit > 0: # 보유하고 있는 가상화폐가 있으면
                        sellTransNo = sell_crypto_currency(ticker, unit) # 매도
                        print(ticker + 'sell!!')
                elif signal == 0: #관망
                    time.sleep(1)
                    pass
        except Exception as e:
            logger.error(e)
            pass



def getCandleStick(ticker):
    ohlcv = exchange.fetch_ohlcv(ticker, '1h')
    ohlcv_4h = [] #4시간 봉을 얻기위함.
    timestpam = 0
    open = 1
    high = 2
    low = 3
    close = 4
    volume = 5

    while ohlcv is None:
        time.sleep(0.5)
        ohlcv = exchange.fetch_ohlcv(ticker, '1h') #1시간 봉을 가져온다.
    if len(ohlcv) > 3: #4시간봉을 만드는 부분
        for i in range(0, len(ohlcv) -3, 4):
            highs = [ohlcv[i+j][high] for j in range(0, 4) if ohlcv[i + j][high]]
            lows = [ohlcv[i+j][low] for j in range(0, 4) if ohlcv[i + j][low]]
            volumes = [ohlcv[i+j][volume] for j in range(0, 4) if ohlcv[i + j][volume]]
            candle = [
                ohlcv[i + 0][timestpam],
                ohlcv[i + 0][open],
                max(highs) if len(highs) else None,
                min(lows) if len(lows) else None,
                ohlcv[i + 3][close],
                sum(volumes) if len(volumes) else None
            ]
            ohlcv_4h.append((candle))

    #dataframe = pd.DataFrame(ohlcv, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
    dataframe = pd.DataFrame(ohlcv_4h, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
    return dataframe

def getStopPrice(df):
    df20 = df.iloc[-21:-1]
    maxPrice = df20['high'].max()
    atr = talib.ATR(df['high'], df['low'], df['close'], timeperiod = 20).iloc[-1]
    stopPrice = maxPrice - 2.0 * atr
    return stopPrice

def getCurrPrice(ticker):
    currPrice = 0
    while currPrice == 0:
        currPrice = exchange.fetch_ticker(ticker)['close']
        time.sleep(0.5)
    return currPrice

def getBalance():
    bal = exchange.fetch_balance()
    return bal['info']['data']['available_krw']


def getTickerAmt(ticker):
    tickerAmt = exchange.fetch_balance()
    charPosition = ticker.find('/') # ETH/KRW라고 되었을때 '/'의 위치를 찾는다. 이때 charPosition은 3이된다.
    return tickerAmt[ticker[0:charPosition]]['free'] #ETH라는 글자만 빼오기 위해 ticker[0:5]를 사용한다.


def getSignalBB(df, curPrice):
    upper, middle, lower = talib.BBANDS(df['close'], 20, 2, 2) #볼린저 밴드
    b = ((curPrice - lower.iloc[-1]) / (upper.iloc[-1] - lower.iloc[-1])) * 100
    mfi = talib.MFI(df['high'], df['low'], df['close'], df['volume'], 10) #MFI(high, low, close, volume, timeperiod=10)
    nowMfi = mfi.iloc[-1]

    if b > 80 and nowMfi > 80:
        return 1 # 매수
    elif b < 20 or nowMfi < 20:
        return -1 # 매도
    else:
        return 0 # 관망

def getMACDSignal(df):
    macd, macdSignal, macdHist = talib.MACD(df['close'], 12, 26, 9)
    if macd.iloc[-1] > macdSignal.iloc[-1]: #매수 시그널
        return 1
    elif macd.iloc[-1] < macdSignal.iloc[-1]: #매도 시그널
        return -1
    else:
        return 0

def buy_crypto_currency(ticker, invest_price):
    try:
        krw = invest_price
        orderbook = exchange.fetch_order_book(ticker)
        sell_price = orderbook['asks'][0][0]
        unit = round(krw / sell_price,4)
        buy_order = exchange.create_market_buy_order(ticker, unit)  # 시장가 매수
        return buy_order
    except Exception as e:
        logger.error(e)
        pass

def sell_crypto_currency(ticker, unit):
    try:
        sell_order = exchange.create_market_sell_order(ticker, unit)
        return sell_order
    except Exception as e:
        logger.error(e)

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    run()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
