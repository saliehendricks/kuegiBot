import time
from datetime import datetime
from typing import List

import binance_f
from binance_f import RequestClient, SubscriptionClient
from binance_f.exception.binanceapiexception import BinanceApiException
from binance_f.model import OrderSide, OrderType, TimeInForce, CandlestickInterval, SubscribeMessageType
from binance_f.model.accountupdate import Position
from binance_f.model.candlestickevent import Candlestick

from Binance_Futures_python.build.lib.binance_f.model.accountupdate import Balance
from kuegi_bot.utils.trading_classes import ExchangeInterface, Order, Bar, Account, AccountPosition, \
    process_low_tf_bars, Symbol


class BinanceInterface(ExchangeInterface):

    def __init__(self, settings, logger, on_tick_callback=None):
        super().__init__(settings, logger, on_tick_callback)
        self.symbol = settings.SYMBOL
        self.client = RequestClient(api_key=settings.API_KEY,
                                    secret_key=settings.API_SECRET)
        self.ws = SubscriptionClient(api_key=settings.API_KEY,
                                     secret_key=settings.API_SECRET)

        self.orders = {}
        self.positions = {}
        self.candles: List[Candlestick] = []
        self.last = 0
        self.open = False
        self.listen_key = ""
        self.init()

    def init(self):
        self.logger.info("loading market data. this may take a moment")
        self.initOrders()
        self.initPositions()
        self.logger.info("got all data. subscribing to live updates.")
        self.listen_key = self.client.start_user_data_stream()

        self.ws.subscribe_user_data_event(self.listen_key, self.callback, self.error)
        subbarsIntervall = CandlestickInterval.MIN1 if self.settings.MINUTES_PER_BAR <= 60 else CandlestickInterval.HOUR1
        self.ws.subscribe_candlestick_event(self.symbol, subbarsIntervall, self.callback, self.error)
        self.open = True
        self.lastUserDataKeep = time.time()
        self.logger.info("ready to go")

    def callback(self, data_type: 'SubscribeMessageType', event: 'any'):
        gotTick = False
        # refresh userdata every 15 min
        if self.lastUserDataKeep < time.time() - 15 * 60:
            self.lastUserDataKeep = time.time()
            self.client.keep_user_data_stream()
        # TODO: implement! (update bars, orders and account)
        if data_type == SubscribeMessageType.RESPONSE:
            pass # what to do herE?
        elif data_type == SubscribeMessageType.PAYLOAD:
            if event.eventType == "kline":
                # {'eventType': 'kline', 'eventTime': 1587064627164, 'symbol': 'BTCUSDT',
                # 'data': <binance_f.model.candlestickevent.Candlestick object at 0x0000016B89856760>}
                if event.symbol == self.symbol:
                    candle: Candlestick = event.data
                    if len(self.candles) > 0:
                        if candle.startTime <= self.candles[0].startTime and candle.startTime > self.candles[-1].startTime:
                            # somewhere inbetween to replace
                            for idx in range(0, len(self.candles)):
                                if candle.startTime == self.candles[idx].startTime:
                                    self.candles[idx] = candle
                                    break
                        elif candle.startTime > self.candles[0].startTime:
                            self.candles.insert(0, candle)
                            gotTick = True
                    else:
                        self.candles.append(candle)
                        gotTick = True
            elif (event.eventType == "ACCOUNT_UPDATE"):
                # {'eventType': 'ACCOUNT_UPDATE', 'eventTime': 1587063874367, 'transactionTime': 1587063874365,
                # 'balances': [<binance_f.model.accountupdate.Balance object at 0x000001FAF470E100>,...],
                # 'positions': [<binance_f.model.accountupdate.Position object at 0x000001FAF470E1C0>...]}
                usdBalance = 0
                for b in event.balances:
                    bal: Balance = b
                    if bal.asset == "USDT":
                        usdBalance = bal.walletBalance
                for p in event.positions:
                    pos: Position = p
                    if pos.symbol not in self.positions.keys():
                        self.positions[pos.symbol] = AccountPosition(pos.symbol,
                                                                        avgEntryPrice=float(pos.entryPrice),
                                                                        quantity=float(pos.amount),
                                                                     walletBalance=usdBalance if "USDT" in pos.symbol else 0)
                    else:
                        accountPos = self.positions[pos.symbol]
                        accountPos.quantity = float(pos.amount)
                        accountPos.avgEntryPrice = float(pos.entryPrice)
                        if "USDT" in pos.symbol:
                            accountPos.walletBalance= usdBalance

            elif (event.eventType == "ORDER_TRADE_UPDATE"):
                # {'eventType': 'ORDER_TRADE_UPDATE', 'eventTime': 1587063513592, 'transactionTime': 1587063513589,
                # 'symbol': 'BTCUSDT', 'clientOrderId': 'web_ybDNrTjCi765K3AvOMRK', 'side': 'BUY', 'type': 'LIMIT',
                # 'timeInForce': 'GTC', 'origQty': 0.01, 'price': 6901.0, 'avgPrice': 0.0, 'stopPrice': 0.0,
                # 'executionType': 'NEW', 'orderStatus': 'NEW', 'orderId': 2705199704, 'lastFilledQty': 0.0,
                # 'cumulativeFilledQty': 0.0, 'lastFilledPrice': 0.0, 'commissionAsset': None, 'commissionAmount': None,
                # 'orderTradeTime': 1587063513589, 'tradeID': 0, 'bidsNotional': 138.81, 'asksNotional': 0.0,
                # 'isMarkerSide': False, 'isReduceOnly': False, 'workingType': 'CONTRACT_PRICE'}
                sideMulti= 1 if event.side == 'BUY' else -1
                order:Order = Order(orderId=event.clientOrderId,
                                    stop= event.stopPrice,
                                    limit= event.price,
                                    amount=event.origQty*sideMulti
                                    )
                order.exchange_id= event.orderId
                #FIXME: how do i know stop triggered on binance?
                #order.stop_triggered =
                order.executed_amount= event.cumulativeFilledQty *sideMulti
                order.executed_price= event.avgPrice
                order.tstamp= event.transactionTime
                order.execution_tstamp= event.orderTradeTime

                prev: Order = self.orders[order.exchange_id] if order.exchange_id in self.orders.keys() else None
                if prev is not None:
                    if prev.tstamp > order.tstamp or abs(prev.executed_amount) > abs(order.executed_amount):
                        # already got newer information, probably the info of the stop order getting
                        # triggered, when i already got the info about execution
                        self.logger.info("ignoring delayed update for %s " % (prev.id))
                    if order.stop_price is None:
                        order.stop_price = prev.stop_price
                    if order.limit_price is None:
                        order.limit_price = prev.limit_price
                prev = order
                if not prev.active and prev.execution_tstamp == 0:
                    prev.execution_tstamp = datetime.utcnow().timestamp()
                self.orders[order.exchange_id] = prev

                self.logger.info("received order update: %s" % (str(order)))
        else:
            self.logger.warn("Unknown Data in websocket callback")

        if gotTick and self.on_tick_callback is not None:
            self.on_tick_callback()  # got something new

    def error(self, e: 'BinanceApiException'):
        self.exit()
        self.logger.error(e.error_code + e.error_message)

    def initOrders(self):
        apiOrders = self.client.get_open_orders()
        for o in apiOrders:
            order = self.convertOrder(o)
            if order.active:
                self.orders[order.exchange_id] = order

    def convertOrder(self, apiOrder: binance_f.model.Order) -> Order:
        direction = 1 if apiOrder.side == OrderSide.BUY else -1
        order = Order(orderId=apiOrder.clientOrderId,
                      amount=apiOrder.origQty * direction,
                      limit=apiOrder.price,
                      stop=apiOrder.stopPrice)
        order.executed_amount = apiOrder.executedQty * direction
        order.executed_price = apiOrder.avgPrice
        order.active = apiOrder.status in ["NEW", "PARTIALLY_FILLED"]
        order.exchange_id = apiOrder.orderId
        return order

    def initPositions(self):
        balance = self.client.get_balance()
        usdBalance = 0
        for bal in balance:
            if bal.asset == "USDT":
                usdBalance = bal.balance
        api_positions = self.client.get_position()
        self.positions[self.symbol] = AccountPosition(self.symbol, 0, 0, 0)
        if api_positions is not None:
            for pos in api_positions:
                self.positions[pos.symbol] = AccountPosition(pos.symbol,
                                                             avgEntryPrice=pos.entryPrice,
                                                             quantity=pos.positionAmt,
                                                             walletBalance=usdBalance if "USDT" in pos.symbol else 0)

        self.logger.info(
            "starting with %.2f in wallet and pos  %.2f @ %.2f" % (self.positions[self.symbol].walletBalance,
                                                                   self.positions[self.symbol].quantity,
                                                                   self.positions[self.symbol].avgEntryPrice))

    def exit(self):
        self.ws.unsubscribe_all()
        self.open = False

    def internal_cancel_order(self, order: Order):
        if order.exchange_id in self.orders.keys():
            self.orders[order.exchange_id].active = False
        self.client.cancel_order(symbol=self.symbol, origClientOrderId=order.id)

    def internal_send_order(self, order: Order):
        order_type = OrderType.MARKET
        if order.limit_price is not None:
            if order.stop_price is not None:
                order_type = OrderType.STOP
            else:
                order_type = OrderType.LIMIT
        else:
            order_type = OrderType.STOP_MARKET

        resultOrder: binance_f.model.Order = self.client.post_order(symbol=self.symbol,
                                                                    side=OrderSide.BUY if order.amount > 0 else OrderSide.SELL,
                                                                    ordertype=order_type,
                                                                    timeInForce=TimeInForce.GTC,
                                                                    quantity=abs(order.amount),
                                                                    price=order.limit_price, stopPrice=order.stop_price,
                                                                    newClientOrderId=order.id)
        order.exchange_id = resultOrder.orderId

    def internal_update_order(self, order: Order):
        self.cancel_order(order)  # stupid binance can't update orders
        self.send_order(order)

    def get_orders(self) -> List[Order]:
        return list(self.orders.values())

    def get_bars(self, timeframe_minutes, start_offset_minutes) -> List[Bar]:
        tf = CandlestickInterval.MIN1 if timeframe_minutes <= 60 else CandlestickInterval.HOUR1

        bars = self.client.get_candlestick_data(symbol=self.symbol, interval=tf, limit=1000)

        return self._aggregate_bars(reversed(bars), timeframe_minutes, start_offset_minutes)

    def recent_bars(self, timeframe_minutes, start_offset_minutes) -> List[Bar]:
        return self._aggregate_bars(self.bars, timeframe_minutes, start_offset_minutes)

    def _aggregate_bars(self, bars, timeframe_minutes, start_offset_minutes) -> List[Bar]:
        subbars = []
        for b in bars:
            subbars.append(self.convertBar(b))
        return process_low_tf_bars(subbars, timeframe_minutes, start_offset_minutes)

    @staticmethod
    def convertBar(apiBar: binance_f.model.candlestick.Candlestick):
        return Bar(tstamp=apiBar.openTime / 1000, open=apiBar.open, high=apiBar.high, low=apiBar.low,
                   close=apiBar.close,
                   volume=apiBar.volume)

    @staticmethod
    def barArrayToBar(b):
        return Bar(tstamp=b[0] / 1000, open=float(b[1]), high=float(b[2]), low=float(b[3]),
                   close=float(b[4]), volume=float(b[5]))

    def get_instrument(self, symbol=None):
        if symbol is None:
            symbol = self.symbol
        instr: binance_f.model.exchangeinformation.ExchangeInformation = self.client.get_exchange_information()
        for symb in instr.symbols:
            if symb.symbol == symbol:
                baseLength = len(symb.baseAsset)
                lotSize = 0
                tickSize = 0
                for filter in symb.filters:
                    if filter['filterType'] == 'LOT_SIZE':
                        lotSize = filter['stepSize']
                    if filter['filterType'] == 'PRICE_FILTER':
                        tickSize = filter['tickSize']

                return Symbol(symbol=symb.symbol,
                              isInverse=symb.baseAsset != symb.symbol[:baseLength],
                              lotSize=lotSize,
                              tickSize=tickSize,
                              makerFee=0.02,
                              takerFee=0.04)
        return None

    def get_position(self, symbol=None):
        if symbol is None:
            symbol = self.symbol
        return self.positions[symbol] if symbol in self.positions.keys() else None

    def is_open(self):
        return self.open

    def check_market_open(self):
        return self.open  # TODO: is that the best we can do?

    def update_account(self, account: Account):
        pass
