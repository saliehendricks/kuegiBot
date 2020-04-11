from datetime import datetime
from typing import List

import binance_f
from binance_f import RequestClient, SubscriptionClient
from binance_f.exception.binanceapiexception import BinanceApiException
from binance_f.model import OrderSide, OrderType, TimeInForce, CandlestickInterval, SubscribeMessageType

from kuegi_bot.utils.trading_classes import ExchangeInterface, Order, Bar, Account, AccountPosition, \
    process_low_tf_bars, Symbol


class BinanceInterface(ExchangeInterface):

    def __init__(self, settings, logger,on_tick_callback=None):
        super().__init__(settings,logger,on_tick_callback)
        self.symbol = settings.SYMBOL
        self.client= RequestClient(api_key=settings.API_KEY,
                                 secret_key=settings.API_SECRET)
        self.ws = SubscriptionClient(api_key=settings.API_KEY,
                                 secret_key=settings.API_SECRET)

        self.orders = {}
        self.positions = {}
        self.bars = []
        self.last = 0
        self.open = False
        self.init()

    def init(self):
        self.logger.info("loading market data. this may take a moment")
        self.initOrders()
        self.initPositions()
        self.logger.info("got all data. subscribing to live updates.")
        self.ws.subscribe_order()
        self.ws.subscribe_stop_order()
        self.ws.subscribe_execution()
        self.ws.subscribe_position()
        subbarsIntervall = CandlestickInterval.MIN1 if self.settings.MINUTES_PER_BAR <= 60 else CandlestickInterval.HOUR1
        self.ws.subscribe_candlestick_event(self.symbol, subbarsIntervall, self.callback, self.error)
        self.open= True
        self.logger.info("ready to go")

    def callback(self,data_type: 'SubscribeMessageType', event: 'any'):
        #TODO: implement! (update bars, orders and account)
        if data_type == SubscribeMessageType.RESPONSE:
            print("Event ID: ", event)
        elif  data_type == SubscribeMessageType.PAYLOAD:
            print("Event type: ", event.eventType)
            print("Event time: ", event.eventTime)
            print("Symbol: ", event.symbol)
            print("Data:", event.data)
        else:
            print("Unknown Data:")
        print()

    def error(self,e: 'BinanceApiException'):
        self.exit()
        print(e.error_code + e.error_message)

    def initOrders(self):
        apiOrders = self.client.get_open_orders()
        for o in apiOrders:
            order = self.convertOrder(o)
            if order.active:
                self.orders[order.exchange_id] = order

    def convertOrder(self, apiOrder:binance_f.model.Order) -> Order:
        direction= 1 if apiOrder.side == OrderSide.BUY else -1
        order= Order(orderId= apiOrder.clientOrderId,
                     amount= apiOrder.origQty*direction,
                     limit=apiOrder.price,
                     stop=apiOrder.stopPrice)
        order.executed_amount= apiOrder.executedQty*direction
        order.executed_price= apiOrder.avgPrice
        order.active= apiOrder.status in ["NEW", "PARTIALLY_FILLED"]
        order.exchange_id= apiOrder.orderId
        return order

    def initPositions(self):
        balance = self.client.get_balance()
        usdBalance= 0
        for bal in balance:
            if bal.asset == "USDT":
                usdBalance= bal.balance
        api_positions = self.client.get_position()
        self.positions[self.symbol] = AccountPosition(self.symbol, 0, 0, 0)
        if api_positions is not None:
            for pos in api_positions:
                sizefac = -1 if pos["side"] == "Sell" else 1
                self.positions[pos.symbol] = AccountPosition(pos.symbol,
                                                                avgEntryPrice=pos.entryPrice,
                                                                quantity=pos.positionAmt,
                                                                walletBalance = usdBalance if "USDT" in pos.symbol else 0)

        self.logger.info(
            "starting with %.2f in wallet and pos  %.2f @ %.2f" % (self.positions[self.symbol].walletBalance,
                                                                   self.positions[self.symbol].quantity,
                                                                   self.positions[self.symbol].avgEntryPrice))


    def exit(self):
        self.ws.unsubscribe_all()
        self.open= False

    def internal_cancel_order(self, order: Order):
        if order.exchange_id in self.orders.keys():
            self.orders[order.exchange_id].active= False
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
        self.cancel_order(order) # stupid binance can't update orders
        self.send_order(order)

    def get_orders(self) -> List[Order]:
        return list(self.orders.values())

    def get_bars(self, timeframe_minutes, start_offset_minutes) -> List[Bar]:
        tf = CandlestickInterval.MIN1 if timeframe_minutes <= 60 else CandlestickInterval.HOUR1

        bars = self.client.get_candlestick_data(symbol=self.symbol,interval=tf, limit= 1000)

        return self._aggregate_bars(reversed(bars), timeframe_minutes, start_offset_minutes)

    def recent_bars(self, timeframe_minutes, start_offset_minutes) -> List[Bar]:
        return self._aggregate_bars(self.bars, timeframe_minutes, start_offset_minutes)

    def _aggregate_bars(self, bars, timeframe_minutes, start_offset_minutes) -> List[Bar]:
        subbars = []
        for b in bars:
            subbars.append(self.convertBar(b))
        return process_low_tf_bars(subbars, timeframe_minutes, start_offset_minutes)

    def convertBar(self,apiBar: binance_f.model.candlestick.Candlestick):
        return Bar(tstamp= apiBar.openTime/1000,open=apiBar.open, high= apiBar.high, low=apiBar.low, close=apiBar.close,
                   volume= apiBar.volume)

    def get_instrument(self, symbol=None):
        if symbol is None:
            symbol = self.symbol
        instr : binance_f.model.exchangeinformation.ExchangeInformation = self.client.get_exchange_information()
        for symb in instr.symbols:
            if symb.symbol == symbol:
                baseLength= len(symb.baseAsset)
                lotSize= 0
                tickSize= 0
                for filter in symb.filters:
                    if filter['filterType'] == 'LOT_SIZE':
                        lotSize= filter['stepSize']
                    if filter['filterType'] == 'PRICE_FILTER':
                        tickSize= filter['tickSize']

                return Symbol(symbol=symb.symbol,
                              isInverse= symb.baseAsset != symb.symbol[:baseLength],
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
        return self.open # TODO: is that the best we can do?

    def update_account(self, account: Account):
        pass


