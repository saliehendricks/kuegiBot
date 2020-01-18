# importing the requests library
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

URL = "https://www.bitmex.com/api/v1/trade/bucketed?binSize=1m&partial=false&symbol=XBTUSD&count=1000&reverse=false"

if exchange == 'bybit':
    URL= "https://api.bybit.com/v2/public/kline/list?symbol=BTCUSD&interval=1"

result= []
start= 1 if exchange == 'bybit' else 0
offset= 0

#init
lastknown= 11 if exchange == 'bybit' else 44
if lastknown >= 0:
    with open('history/'+exchange+'/M1_' + str(lastknown) + '.json', 'r') as file:
        result = json.load(file)
        start = int(result[-1]['open_time']) + 1 if exchange == 'bybit' else lastknown * batchsize + len(result)
        offset= lastknown*batchsize

wroteData= False
lastSync= 0
while True:
    # sending get request and saving the response as response object
    url= URL+"&start="+str(start)
    if exchange == 'bybit':
        url = URL + "&from=" + str(start)
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
        start = int(data[-1]['open_time'])+1 if exchange == 'bybit' else start + len(data)

    if lastSync > 15000 or (len(data) < 10 and not wroteData):
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







