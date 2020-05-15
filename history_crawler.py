# importing the requests library
import os

import requests
import json
import math
import sys
from time import sleep

from datetime import datetime
# ====================================
#
# api-endpoint
from kuegi_bot.utils.trading_classes import parse_utc_timestamp

exchange = sys.argv[1] if len(sys.argv) > 1 else 'bybit'
print("crawling from "+exchange)

batchsize = 50000

urls = {
    "bitmex": "https://www.bitmex.com/api/v1/trade/bucketed?binSize=1m&partial=false&symbol=XBTUSD&count=1000&reverse=false",
    "bybit": "https://api.bybit.com/v2/public/kline/list?symbol=BTCUSD&interval=1",
    "binance": "https://fapi.binance.com/fapi/v1/klines?symbol=BTCUSDT&interval=1m&limit=1000",
    "binanceSpot": "https://api.binance.com/api/v1/klines?symbol=BTCUSDT&interval=1m&limit=1000"
}

URL = urls[exchange]

result = []
start = 1 if exchange == 'bybit' else 0
offset = 0

# init
# TODO: adapt this to your number if you already have history files
filecount = {
    "bitmex": 45,
    "bybit": 15,
    "binance": 6,
    "binanceSpot": 28
}
lastknown = filecount[exchange]

try:
    os.makedirs('history/'+exchange)
except Exception:
    pass

if lastknown >= 0:
    try:
        with open('history/'+exchange+'/M1_' + str(lastknown) + '.json', 'r') as file:
            result = json.load(file)
            if exchange == 'bitmex':
                start = lastknown * batchsize + len(result)
            elif exchange == 'bybit':
                start = int(result[-1]['open_time']) + 1
            elif exchange in ['binance','binanceSpot']:
                start= int(result[-1][6])
            offset= lastknown*batchsize
    except:
        print("lier! you didn't have any history yet!")
        lastknown = 0

wroteData= False
lastSync= 0
while True:
    # sending get request and saving the response as response object
    url= URL+"&start="+str(start)
    if exchange == 'bybit':
        url = URL + "&from=" + str(start)
    elif exchange in ['binance','binanceSpot']:
        url= URL + "&startTime="+str(start)
    print(url+" __ "+str(len(result)))
    r = requests.get(url=url)
    # extracting data in json format
    data= r.json()
    if exchange == 'bybit':
        data = r.json()["result"]
    if len(data) < 200:
        print(str(data)[:100])
        sleep(10)
    else:
        wroteData= False
        if exchange == 'bitmex':
            for b in data:
                b['tstamp'] = parse_utc_timestamp(b['timestamp'])
        result += data
        lastSync += len(data)
        if exchange == 'bitmex':
            start= start +len(data)
        elif exchange == 'bybit':
            start = int(data[-1]['open_time'])+1
        elif exchange in ['binance','binanceSpot']:
            start= data[-1][6] # closeTime of last bar
    if lastSync > 15000 or (len(data) < 200 and not wroteData):
        wroteData= True
        lastSync= 0
        max= math.ceil((len(result)+offset)/batchsize)
        idx= max - 2
        while idx < max:
            if idx*batchsize-offset >= 0:
                with open('history/'+exchange+'/M1_'+str(idx)+'.json','w') as file:
                    json.dump(result[idx*batchsize-offset:(idx+1)*batchsize-offset],file)
                    print("wrote file "+str(idx))
            idx += 1

#########################################
# live tests
########







