from functools import reduce

from kuegi_bot.bots.trading_bot import PositionDirection, TradingBot
from kuegi_bot.utils.trading_classes import Position, Order, Account, Bar, Symbol, OrderType
from kuegi_bot.kuegi_channel import Data, clean_range
import math
from typing import List
from datetime import datetime


class Strategy:
    def __init__(self):
        pass

    def myId(self):
        return "GenericStrategy"

    def init(self, bars: List[Bar], account: Account, symbol: Symbol):
        pass

    def min_bars_needed(self) -> int:
        return 5

    def owns_signal_id(self, signalId: str):
        return False

    def got_data_for_position_sync(self, bars: List[Bar]) -> bool:
        raise NotImplementedError

    def prep_bars(self, is_new_bar: bool, bars: list):
        pass

    def position_got_opened(self, position: Position, bars: List[Bar], account: Account):
        pass

    def manage_open_order(self, order, position, bars, to_update, to_cancel):
        pass

    def manage_open_position(self, p, bars, account, pos_ids_to_cancel):
        pass

    def open_orders(self, is_new_bar, bars, account):
        pass


class MultiStrategyBot(TradingBot):

    def __init__(self, logger=None, directionFilter=0):
        super().__init__(logger, directionFilter)
        self.myId = "MultiStrategy"
        self.strategies: List[Strategy] = []

    def add_strategy(self, strategy: Strategy):
        self.strategies.append(strategy)

    def init(self, bars: List[Bar], account: Account, symbol: Symbol, unique_id: str = ""):
        self.logger.info(
            "init with strategies: %s" % reduce((lambda result, strat: result + ", " + strat.myId()), self.strategies,
                                                ""))
        for strat in self.strategies:
            strat.init(bars, account, symbol)
        super().init(bars=bars, account=account, symbol=symbol, unique_id=unique_id)

    def min_bars_needed(self):
        return reduce(lambda x, y: max(x, y.min_bars_needed()), self.strategies, 5)

    def prep_bars(self, bars: list):
        for strat in self.strategies:
            strat.prep_bars(self.is_new_bar, bars)

    def got_data_for_position_sync(self, bars: List[Bar]):
        return reduce((lambda x, y: x and y.got_data_for_position_sync(bars)), self.strategies, True)

    def position_got_opened(self, position: Position, bars: List[Bar], account: Account):
        [signalId, direction] = self.split_pos_Id(position.id)
        for strat in self.strategies:
            if strat.owns_signal_id(signalId):
                strat.position_got_opened(position, bars, account)
                break

    def manage_open_orders(self, bars: List[Bar], account: Account):
        self.sync_executions(bars, account)

        to_cancel = []
        to_update = []
        for order in account.open_orders:
            posId = self.position_id_from_order_id(order.id)
            if posId is None or not posId in self.open_positions.keys():
                continue
            [signalId, direction] = self.split_pos_Id(posId)
            for strat in self.strategies:
                if strat.owns_signal_id(signalId):
                    strat.manage_open_order(order, self.open_positions[posId], bars, to_update, to_cancel)
                    break

        for order in to_cancel:
            self.order_interface.cancel_order(order)

        for order in to_update:
            self.order_interface.update_order(order)

        pos_ids_to_cancel = []
        for p in self.open_positions.values():
            [signalId, direction] = self.split_pos_Id(p.id)
            for strat in self.strategies:
                if strat.owns_signal_id(signalId):
                    strat.manage_open_position(p, bars, account, pos_ids_to_cancel)
                    break

        for key in pos_ids_to_cancel:
            del self.open_positions[key]

    def open_orders(self, bars: List[Bar], account: Account):
        for strat in self.strategies:
            strat.open_orders(self.is_new_bar, bars, account)
