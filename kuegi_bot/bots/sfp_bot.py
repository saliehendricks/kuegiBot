import math
from datetime import datetime
from typing import List

import plotly.graph_objects as go

from kuegi_bot.bots.trading_bot import PositionDirection
from kuegi_bot.kuegi_channel import KuegiChannel, Data, clean_range
from kuegi_bot.trade_engine import TradingBot
from kuegi_bot.utils.trading_classes import Position, Order, Account, Bar, OrderType


class SfpBot(TradingBot):

    def __init__(self, logger=None, directionFilter=0, risk_factor: float = 1,
                 max_look_back: int = 13, threshold_factor: float = 0.9, buffer_factor: float = 0.05,
                 max_dist_factor: float = 1, max_swing_length: int = 3,
                 be_factor: float = 1, be_buffer: float= 0.1, tp_fac: float = 0, init_stop_type: int = 0,
                 min_wick_fac: float = 0.2, min_swing_length: int = 2,
                 range_length: int = 50, range_filter_fac: float = 0,
                 close_on_opposite: bool = False, risk_type:int= 0, max_risk_mul:float = 2):
        super().__init__(logger, directionFilter)
        self.channel = KuegiChannel(max_look_back, threshold_factor, buffer_factor, max_dist_factor, max_swing_length)
        self.be_factor = be_factor
        self.be_buffer= be_buffer
        self.risk_factor = risk_factor
        self.min_wick_fac = min_wick_fac
        self.min_swing_length = min_swing_length
        self.init_stop_type = init_stop_type
        self.tp_fac = tp_fac
        self.range_length = range_length
        self.range_filter_fac = range_filter_fac
        self.close_on_opposite = close_on_opposite
        self.risk_type= risk_type
        self.max_risk_mul= max_risk_mul

    def uid(self) -> str:
        return "SFP"

    def min_bars_needed(self):
        return self.channel.max_look_back + 1

    def prep_bars(self, bars: list):
        if self.is_new_bar:
            self.channel.on_tick(bars)

    def position_got_opened(self, position: Position, bars: List[Bar], account: Account):
        pass

    def got_data_for_position_sync(self, bars: List[Bar]):
        return self.channel.get_data(bars[1]) is not None

    def get_stop_for_unmatched_amount(self, amount: float, bars: List[Bar]):
        data = self.channel.get_data(bars[1])
        stopLong = int(max(data.shortSwing, data.longTrail) if data.shortSwing is not None else data.longTrail)
        stopShort = int(min(data.longSwing, data.shortTrail) if data.longSwing is not None else data.shortTrail)
        return stopLong if amount > 0 else stopShort

    def manage_open_orders(self, bars: List[Bar], account: Account):
        self.sync_executions(bars, account)

        # check for BE

        if len(bars) < 5:
            return

        # trail stop only on new bar
        data: Data = self.channel.get_data(bars[1])
        if data is None:
            return

        stopLong = data.longTrail
        stopShort = data.shortTrail

        to_update = []
        for order in account.open_orders:
            posId = self.position_id_from_order_id(order.id)
            if posId not in self.open_positions.keys():
                continue
            pos = self.open_positions[posId]
            orderType = self.order_type_from_order_id(order.id)
            if orderType == OrderType.SL:
                # trail
                newStop = order.stop_price
                if order.amount < 0:  # long position
                    if self.is_new_bar and newStop < stopLong:
                        newStop = int(stopLong)
                    if self.be_factor > 0 and \
                            pos.wanted_entry is not None and \
                            pos.initial_stop is not None and \
                            bars[0].high > pos.wanted_entry + (pos.wanted_entry - pos.initial_stop) * self.be_factor \
                            and newStop < pos.wanted_entry + 1:
                        newStop = pos.wanted_entry + data.atr*self.be_buffer# make fees and bit of slipage

                if order.amount > 0:
                    if self.is_new_bar and newStop > stopShort:
                        newStop = int(stopShort)
                    if self.be_factor > 0 and \
                            pos.wanted_entry is not None and \
                            pos.initial_stop is not None and \
                            bars[0].low < pos.wanted_entry + (pos.wanted_entry - pos.initial_stop) * self.be_factor \
                            and newStop > pos.wanted_entry - 1:
                        newStop = pos.wanted_entry - data.atr*self.be_buffer # make fees and bit of slipage

                if newStop != order.stop_price:
                    order.stop_price = newStop
                    to_update.append(order)

        for order in to_update:
            self.order_interface.update_order(order)

    def calc_pos_size(self, risk, entry, exitPrice, data):
        if self.risk_type <= 2:
            delta = entry - exitPrice
            if self.risk_type == 1 and data is not None:
                # use atr as delta reference, but max X the actual delta. so risk is never more than X times the
                # wanted risk
                delta = math.copysign(min(self.max_risk_mul * abs(delta), self.max_risk_mul * data.atr), delta)

            size = 0
            if not self.symbol.isInverse:
                size = risk / delta
            else:
                size = -int(risk / (1 / entry - 1 / (entry - delta)))
            return size

    def open_orders(self, bars: List[Bar], account: Account):
        if (not self.is_new_bar) or len(bars) < 5:
            return  # only open orders on beginning of bar

        self.logger.info("---- analyzing: %s" %
                         (str(datetime.fromtimestamp(bars[0].tstamp))))

        atr = clean_range(bars, offset=0, length=self.channel.max_look_back * 2)
        risk = self.risk_factor

        # test for SFP:
        # High > HH der letzten X
        # Close < HH der vorigen X
        # ? min Wick size?
        # initial SL

        data: Data = self.channel.get_data(bars[1])
        maxLength = min(len(bars), self.range_length)
        highSupreme = 0
        hhBack = 0
        hh = bars[2].high
        swingHigh = 0
        gotHighSwing = False
        for idx in range(2, maxLength):
            if bars[idx].high < bars[1].high:
                highSupreme = idx - 1
                if hh < bars[idx].high:
                    hh = bars[idx].high
                    hhBack = idx
                elif self.min_swing_length < hhBack <= idx - self.min_swing_length:
                    gotHighSwing = True
                    swingHigh = hh  # confirmed
            else:
                break

        lowSupreme = 0
        llBack = 0
        ll = bars[2].low
        swingLow = 0
        gotLowSwing = False
        for idx in range(2, maxLength):
            if bars[idx].low > bars[1].low:
                lowSupreme = idx - 1
                if ll > bars[idx].low:
                    ll = bars[idx].low
                    llBack = idx
                elif self.min_swing_length < llBack <= idx - self.min_swing_length:
                    gotLowSwing = True
                    swingLow = ll  # confirmed
            else:
                break

        rangeMedian = (bars[maxLength - 1].high + bars[maxLength - 1].low) / 2
        alpha = 2 / (maxLength + 1)
        for idx in range(maxLength - 2, 0, -1):
            rangeMedian = rangeMedian * alpha + (bars[idx].high + bars[idx].low) / 2 * (1 - alpha)

        expectedEntrySplipagePerc = 0.0015
        expectedExitSlipagePerc = 0.0015

        signalId = str(bars[0].tstamp)

        # SHORT
        longSFP = gotHighSwing and bars[1].close < swingHigh
        longRej = bars[1].high > hh > bars[1].close and highSupreme > maxLength / 2 \
                  and bars[1].high - bars[1].close > (bars[1].high-bars[1].low)/2
        if (longSFP or longRej) and (bars[1].high - bars[1].close) > atr * self.min_wick_fac \
                and self.directionFilter <= 0 and bars[1].high > rangeMedian + atr * self.range_filter_fac:
            # close existing short pos
            if self.close_on_opposite:
                for pos in self.open_positions.values():
                    if pos.status == "open" and self.split_pos_Id(pos.id)[1] == PositionDirection.LONG:
                        # execution will trigger close and cancel of other orders
                        self.order_interface.send_order(Order(orderId=self.generate_order_id(pos.id, OrderType.SL),
                                                              amount=-pos.amount, stop=None, limit=None))

            if self.init_stop_type == 1:
                stop = bars[1].high
            elif self.init_stop_type == 2:
                stop = bars[1].high + (bars[0].high - bars[0].close) * 0.5
            else:
                stop = max(swingHigh, (bars[1].high + bars[1].close) / 2)
            stop = stop + 1  # buffer

            entry = bars[0].open
            amount = self.calc_pos_size(risk=risk, exitPrice=stop * (1 + expectedExitSlipagePerc),
                                        entry=entry * (1 - expectedEntrySplipagePerc), data= data)

            posId = self.full_pos_id(signalId, PositionDirection.SHORT)
            self.order_interface.send_order(Order(orderId=self.generate_order_id(posId, OrderType.ENTRY),
                                                  amount=amount, stop=None, limit=None))
            self.order_interface.send_order(Order(orderId=self.generate_order_id(posId, OrderType.SL),
                                                  amount=-amount, stop=stop, limit=None))
            if self.tp_fac > 0:
                tp = entry - (stop - entry) * self.tp_fac
                self.order_interface.send_order(Order(orderId=self.generate_order_id(posId, OrderType.TP),
                                                      amount=-amount, stop=None, limit=tp))
            self.open_positions[posId] = Position(id=posId, entry=entry, amount=amount, stop=stop,
                                                  tstamp=bars[0].tstamp)
        # LONG
        shortSFP = gotLowSwing and bars[1].close > swingLow
        shortRej= bars[1].low < ll < bars[1].close and lowSupreme > maxLength / 2\
                  and bars[1].close - bars[1].low > (bars[1].high-bars[1].low)/2
        if (shortSFP or shortRej) and (bars[1].close - bars[1].low) > atr * self.min_wick_fac \
                and self.directionFilter >= 0 and bars[1].low < rangeMedian - self.range_filter_fac:
            # close existing short pos
            if self.close_on_opposite:
                for pos in self.open_positions.values():
                    if pos.status == "open" and self.split_pos_Id(pos.id)[1] == PositionDirection.SHORT:
                        # execution will trigger close and cancel of other orders
                        self.order_interface.send_order(Order(orderId=self.generate_order_id(pos.id, OrderType.SL),
                                                              amount=-pos.amount, stop=None, limit=None))

            if self.init_stop_type == 1:
                stop = bars[1].low
            elif self.init_stop_type == 2:
                stop = bars[1].low + (bars[0].low - bars[0].close) * 0.5
            else:
                stop = min(swingLow, (bars[1].low + bars[1].close) / 2)
            stop = stop - 1  # buffer

            entry = bars[0].open
            amount = self.calc_pos_size(risk=risk, exitPrice=stop * (1 - expectedExitSlipagePerc),
                                        entry=entry * (1 + expectedEntrySplipagePerc), data= data)

            posId = self.full_pos_id(signalId, PositionDirection.LONG)
            self.order_interface.send_order(Order(orderId=self.generate_order_id(posId, OrderType.ENTRY),
                                                  amount=amount, stop=None, limit=None))
            self.order_interface.send_order(Order(orderId=self.generate_order_id(posId, OrderType.SL),
                                                  amount=-amount, stop=stop, limit=None))
            if self.tp_fac > 0:
                tp = entry + (entry - stop) * self.tp_fac
                self.order_interface.send_order(Order(orderId=self.generate_order_id(posId, OrderType.TP),
                                                      amount=-amount, stop=None, limit=tp))

            self.open_positions[posId] = Position(id=posId, entry=entry, amount=amount, stop=stop,
                                                  tstamp=bars[0].tstamp)

    def add_to_plot(self, fig: go.Figure, bars: List[Bar], time):
        super().add_to_plot(fig, bars, time)
        lines = self.channel.get_number_of_lines()
        styles = self.channel.get_line_styles()
        names = self.channel.get_line_names()
        offset = 1  # we take it with offset 1
        self.logger.info("adding channel")
        for idx in range(0, lines):
            sub_data = list(map(lambda b: self.channel.get_data_for_plot(b)[idx], bars))
            fig.add_scatter(x=time, y=sub_data[offset:], mode='lines', line=styles[idx],
                            name=self.channel.id + "_" + names[idx])
