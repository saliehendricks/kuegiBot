
########
# some simple exit modules for reuse
##########
import math
from typing import List

from kuegi_bot.bots.strategies.strat_with_exit_modules import ExitModule
from kuegi_bot.utils.trading_classes import Position, Bar


class SimpleBE(ExitModule):
    ''' trails the stop to "break even" when the price move a given factor of the entry-risk in the right direction
        "break even" includes a buffer (multiple of the entry-risk).
    '''

    def __init__(self, factor, buffer):
        super().__init__()
        self.factor = factor
        self.buffer = buffer

    def init(self, logger):
        super().init(logger)
        self.logger.info("init BE %.1f %.1f" % (self.factor, self.buffer))

    def manage_open_order(self, order, position, bars, to_update, to_cancel, open_positions):
        if position is not None:
            # trail
            newStop = order.stop_price
            if self.factor > 0 and position.wanted_entry is not None and position.initial_stop is not None:
                entry_diff = (position.wanted_entry - position.initial_stop)
                ep = bars[0].high if position.amount > 0 else bars[0].low
                be = position.wanted_entry + entry_diff * self.buffer
                if (ep - (position.wanted_entry + entry_diff * self.factor)) * position.amount > 0 \
                        and (be - newStop) * position.amount > 0:
                    newStop = math.floor(be) if position.amount < 0 else math.ceil(be)

            if newStop != order.stop_price:
                order.stop_price = newStop
                to_update.append(order)


class ParaData:
    def __init__(self):
        self.acc = 0
        self.ep = 0
        self.stop = 0


class ParaTrail(ExitModule):
    '''
    trails the stop according to a parabolic SAR. ep is resetted on the entry of the position.
    lastEp and factor is stored in the bar data with the positionId
    '''

    def __init__(self, accInit, accInc, accMax):
        super().__init__()
        self.accInit = accInit
        self.accInc = accInc
        self.accMax = accMax

    def init(self, logger):
        super().init(logger)
        self.logger.info("init ParaTrail %.2f %.2f %.2f" % (self.accInit, self.accInc, self.accMax))

    def data_id(self,position:Position):
        return position.id + '_paraExit'

    def manage_open_order(self, order, position, bars, to_update, to_cancel, open_positions):
        if position is None:
            return

        self.update_bar_data(position, bars)
        data = self.get_data(bars[0],self.data_id(position))
        # trail
        newStop = order.stop_price
        if data is not None and (data.stop - newStop) * position.amount > 0:
            newStop = math.floor(data.stop) if position.amount < 0 else math.ceil(data.stop)

        if newStop != order.stop_price:
            order.stop_price = newStop
            to_update.append(order)

    def update_bar_data(self, position: Position, bars: List[Bar]):
        if position.initial_stop is None or position.entry_tstamp is None or position.entry_tstamp == 0:
            return  # cant trail with no initial and not defined entry
        dataId = self.data_id(position)
        # find first bar with data (or entry bar)
        lastIdx = 1
        while self.get_data(bars[lastIdx], dataId) is None and bars[lastIdx].tstamp > position.entry_tstamp:
            lastIdx += 1
            if lastIdx == len(bars):
                break
        if self.get_data(bars[lastIdx - 1], dataId) is None and bars[lastIdx].tstamp > position.entry_tstamp:
            lastIdx += 1  # didn't see the current bar before: make sure we got the latest update on the last one too

        while lastIdx > 0:
            lastbar = bars[lastIdx]
            currentBar = bars[lastIdx - 1]
            last: ParaData = self.get_data(lastbar, dataId)
            current: ParaData = ParaData()
            if last is not None:
                current.ep = max(last.ep, currentBar.high) if position.amount > 0 else min(last.ep, currentBar.low)
                current.acc = last.acc
                if current.ep != last.ep:
                    current.acc = min(current.acc + self.accInc, self.accMax)
                current.stop = last.stop + (current.ep - last.stop) * current.acc
            else:  # means its the first bar of the position
                current.ep = currentBar.high if position.amount > 0 else currentBar.low
                current.acc = self.accInit
                current.stop = position.initial_stop
            self.write_data(bar=currentBar, dataId=dataId, data=current)
            lastIdx -= 1
