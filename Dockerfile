FROM python:3

# Install dependencies
RUN pip install plotly
RUN pip install requests
RUN pip install future
RUN pip install websocket-client
RUN pip install bybit

COPY . .
WORKDIR /kuegiBot

# Install Binance futures from git

RUN git clone https://github.com/Binance-docs/Binance_Futures_python.git
WORKDIR /kuegiBot/Binance_Futures_python
RUN python3 setup.py install

WORKDIR /kuegiBot
#Install kuegi_bot module (is this even needed?)
RUN python3 setup.py install

# Entry to auto start the a script - crawler / cryptbot / 
#ENTRYPOINT ["python3", "kuegi_bot/scripts/history_crawler.py phemex BTCUSD"]
ENTRYPOINT ["tail", "-f", "/dev/null"]
