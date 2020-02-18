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

    def get_data(self,bar:Bar,dataId):
        if 'modules' in bar.bot_data.keys() and self.id in bar.bot_data['modules'].keys():
            return bar.bot_data["modules"][dataId]
        else:
            return None

    def write_data(self,bar:Bar, dataId, data):
        if "modules" not in bar.bot_data.keys():
            bar.bot_data['modules']={}

        bar.bot_data["modules"][dataId] = data


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
	''' trails the stop to "break even" when the price move a given factor of the entry-risk in the right direction
		"break even" includes a buffer (multiple of the entry-risk).
	'''

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


class ParaData:
	def __init__(self):
		self.acc= 0
		self.ep= 0
		self.stop= 0

class ParaTrail(ExitModule):
	''' trails the stop according to a parabolic SAR. ep is resetted on the entry of the position. 
	lastEp and factor is stored in the bar data with the positionId
	'''

    def __init__(self, accInit, accInc, accMax):
        self.accInit = accInit
        self.accInc = accInc
        self.accMax = accMax

    def init(self,logger):
        super().init(logger)
        self.logger.info("init ParaTrail %.2f %.2f %.2f" %(self.accInit,self.accInc,self.accMax))

    def manage_open_order(self, order, position, bars, to_update, to_cancel, open_positions):
        if position is not None:
        	self.update_bar_data(position,bars)
        	data= self.get_data(bars[0])
            # trail
            newStop = order.stop_price
            if data is not None and (data.stop - newStop) * position.amount > 0 :
                 newStop= math.floor(data.stop) if position.amount < 0 else math.ceil(data.stop)

            if newStop != order.stop_price:
                order.stop_price = newStop
                to_update.append(order)

    def update_bar_data(self,position,bars:List[Bar]):
    	if position.initial_stop is not None and position.
    	dataId= position.id+'_paraExit'
    	# find first bar with data (or entry bar)
    	lastIdx= 1
    	while lastIdx > 0:
    		lastbar= bars[barIdx]
    		currentBar= bars[barIdx-1]
	    	last:ParaData= self.get_data(bar,dataId)
			current:ParaData= ParaData()
			if last is not None:
	    		current.ep = max(last.ep,currentBar.high) if position.amount > 0 else min(last.ep,currentBar.low)

	    	else: # means its the first bar of the position
	    		current.ep= currentBar.high if position.amount>0 else currentBar.low
	    		current.acc= self.accInit
	    		current.trail= position.initial_stop

