from typing import List
from functools import reduce

import math
import plotly.graph_objects as go

from kuegi_bot.bots.MultiStrategyBot import Strategy
from kuegi_bot.bots.trading_bot import TradingBot
from kuegi_bot.kuegi_channel import KuegiChannel, Data
from kuegi_bot.utils.trading_classes import Bar, Account, Symbol, OrderType


class ExitModule:
    def __init__(self):
        self.logger= None
        pass

    def manage_open_order(self, order, position, bars, to_update, to_cancel, open_positions):
        pass

    def init(self,logger):
        self.logger= logger

    def got_data_for_position_sync(self, bars: List[Bar]) -> bool:
        return True

    def get_stop_for_unmatched_amount(self, amount: float, bars: List[Bar]):
        return None


class StrategyWithExitModules(Strategy):

    def __init__(self):
        super().__init__()
        self.exitModules = []

    def withExitModule(self,module:ExitModule):
        self.exitModules.append(module)
        return self

    def init(self, bars: List[Bar], account: Account, symbol: Symbol):
        super().init(bars, account, symbol)
        for module in self.exitModules:
            module.init(self.logger)

    def got_data_for_position_sync(self, bars: List[Bar]) -> bool:
        return reduce((lambda x, y: x and y.got_data_for_position_sync(bars)), self.exitModules, True)

    def get_stop_for_unmatched_amount(self, amount: float, bars: List[Bar]):
        for module in self.exitModules:
            exit= module.get_stop_for_unmatched_amount(amount,bars)
            if exit is not None:
                return exit
        return None

    def manage_open_order(self, order, position, bars, to_update, to_cancel, open_positions):
        orderType = TradingBot.order_type_from_order_id(order.id)
        if orderType == OrderType.SL:
            for module in self.exitModules:
                module.manage_open_order(order,position,bars,to_update,to_cancel,open_positions)

########
# some simple exit modules for reuse
##########

class SimpleBE(ExitModule):

    def __init__(self, factor, buffer):
        self.factor = factor
        self.buffer = buffer

    def init(self,logger):
        super().init(logger)
        self.logger.info("init BE %.1f %.1f" %(self.factor,self.buffer))

    def manage_open_order(self, order, position, bars, to_update, to_cancel, open_positions):
        if position is not None:
            # trail
            newStop = order.stop_price
            if self.factor > 0 and position.wanted_entry is not None and position.initial_stop is not None:
                entry_diff = (position.wanted_entry - position.initial_stop)
                ep = bars[0].high if position.amount > 0 else bars[0].low
                be = position.wanted_entry + entry_diff * self.buffer
                if (ep - (position.wanted_entry + entry_diff * self.factor)) * position.amount > 0 \
                    and (be - newStop) * position.amount > 0 :
                    newStop= math.floor(be) if position.amount < 0 else math.ceil(be)

            if newStop != order.stop_price:
                order.stop_price = newStop
                to_update.append(order)
