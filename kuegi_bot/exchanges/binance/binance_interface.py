from typing import List

import binance_f
from binance_f import RequestClient
from binance_f.model import OrderSide, OrderType, TimeInForce

from kuegi_bot.utils.trading_classes import ExchangeInterface, Order, Bar, Account

class BinanceInterface(ExchangeInterface):

    def __init__(self, settings, logger,on_tick_callback=None):
        super().__init__(settings,logger,on_tick_callback)
        self.symbol = settings.SYMBOL
        self.client= RequestClient(api_key=settings.API_KEY,
                                 secret_key=settings.API_SECRET)

        self.orders = {}
        self.positions = {}
        self.bars = []
        self.last = 0
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
        subbarsIntervall = '1' if self.settings.MINUTES_PER_BAR <= 60 else '60'
        self.ws.subscribe_klineV2(subbarsIntervall, self.symbol)
        self.ws.subscribe_instrument_info(self.symbol)
        self.logger.info("ready to go")

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
        api_positions = self._execute(self.bybit.Positions.Positions_myPosition())
        self.positions[self.symbol] = AccountPosition(self.symbol, 0, 0, 0)
        if api_positions is not None:
            for pos in api_positions:
                sizefac = -1 if pos["side"] == "Sell" else 1
                self.positions[pos['symbol']] = AccountPosition(pos['symbol'],
                                                                avgEntryPrice=pos["entry_price"],
                                                                quantity=pos["size"] * sizefac,
                                                                walletBalance=float(pos['wallet_balance']))
        self.logger.info(
            "starting with %.2f in wallet and pos  %.2f @ %.2f" % (self.positions[self.symbol].walletBalance,
                                                                   self.positions[self.symbol].quantity,
                                                                   self.positions[self.symbol].avgEntryPrice))


    def exit(self):
        pass

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
        return []

    def get_bars(self, timeframe_minutes, start_offset_minutes) -> List[Bar]:
        return []

    def recent_bars(self, timeframe_minutes, start_offset_minutes) -> List[Bar]:
        return []

    def get_instrument(self, symbol=None):
        pass

    def get_position(self, symbol=None):
        pass

    def is_open(self):
        return False

    def check_market_open(self):
        return False

    def update_account(self, account: Account):
        pass


