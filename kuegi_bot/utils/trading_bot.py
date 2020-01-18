from kuegi_bot.utils.trading_classes import Bar, Position, Symbol, OrderInterface, Account, OrderType, Order

import plotly.graph_objects as go

from typing import List
from datetime import datetime
from random import randint
from enum import Enum

import os
import json
import csv


class PositionDirection(Enum):
    LONG = "long",
    SHORT = "short"


class TradingBot:
    def __init__(self, logger, directionFilter: int = 0):
        self.logger = logger
        self.directionFilter = directionFilter
        self.order_interface: OrderInterface = None
        self.symbol: Symbol = None
        self.unique_id: str = ""
        self.last_time = 0
        self.last_tick_time = 0
        self.is_new_bar = True
        self.open_positions = {}
        self.known_order_history = 0
        self.position_history: List[Position] = []
        self.reset()

    def uid(self) -> str:
        return "GenericBot"

    def min_bars_needed(self):
        return 5

    def reset(self):
        self.last_time = 0
        self.open_positions = {}
        self.known_order_history = 0
        self.position_history = []

    def _get_pos_file(self):
        return self.symbol.symbol + "_" + self.unique_id + ".json" if self.unique_id is not None else None

    def init(self, bars: List[Bar], account: Account, symbol: Symbol, unique_id: str = ""):
        '''init open position etc.'''
        self.symbol = symbol
        self.unique_id = unique_id
        if unique_id is not None:
            base = 'openPositions/'
            try:
                os.makedirs(base)
            except Exception:
                pass
            try:
                with open(base + self._get_pos_file(), 'r') as file:
                    data = json.load(file)
                    self.last_time = data["last_time"]
                    for pos_json in data["positions"]:
                        pos: Position = Position.from_json(pos_json)
                        self.open_positions[pos.id] = pos
                    self.logger.info("done loading " + str(
                        len(self.open_positions)) + " positions from " + self._get_pos_file() + " last time " + str(
                        self.last_time))
            except Exception as e:
                self.logger.warn("Error loading open positions: " + str(e))
                self.open_positions = {}

    ############### ids of pos, signal and order

    def generate_order_id(self, positionId: str, type: OrderType):
        if "_" in positionId:
            self.logger.warn("position id must not include '_' but does: " + positionId)
        orderId = positionId + "_" + str(type)
        if type == OrderType.SL or type == OrderType.TP:
            orderId = orderId + "_" + str(
                randint(0, 999))  # add random part to prevent conflicts if the order was canceled before
        return orderId

    @staticmethod
    def position_id_from_order_id(order_id: str):
        id_parts = order_id.split("_")
        if len(id_parts) >= 1:
            return id_parts[0]
        return None

    @staticmethod
    def order_type_from_order_id(order_id: str):
        id_parts = order_id.split("_")
        if len(id_parts) >= 2:
            type = id_parts[1]
            if type == str(OrderType.ENTRY):
                return OrderType.ENTRY
            elif type == str(OrderType.SL):
                return OrderType.SL
            elif type == str(OrderType.TP):
                return OrderType.TP
        return None

    @staticmethod
    def full_pos_id(signalId: str, direction: PositionDirection):
        return signalId + "-" + str(direction)

    @staticmethod
    def get_other_direction_id(posId: str):
        parts = posId.split("-")
        if len(parts) >= 2:
            parts[1] = str(
                PositionDirection.LONG if parts[1] == str(PositionDirection.SHORT) else PositionDirection.SHORT)
            return '-'.join(parts)
        return None

    ############### handling of open orders

    def cancel_entry(self, positionId, account: Account):
        to_cancel = self.generate_order_id(positionId, OrderType.ENTRY)
        for o in account.open_orders:
            if o.id == to_cancel:
                self.order_interface.cancel_order(o)
                # only cancel position if entry was still there
                if positionId in self.open_positions.keys():
                    del self.open_positions[positionId]
                break

    def sync_executions(self, bars: List[Bar], account: Account):
        for order in account.order_history[self.known_order_history:]:
            if order.executed_amount == 0:
                self.logger.info("ignored canceled order: " + order.id)
                continue
            posId = self.position_id_from_order_id(order.id)
            if posId not in self.open_positions.keys():
                self.logger.info("executed order not found in positions: " + order.id)
                continue
            position = self.open_positions[posId]

            if position is not None:
                orderType = self.order_type_from_order_id(order.id)
                if orderType == OrderType.ENTRY and (
                        position.status == "pending" or position.status == "triggered"):
                    self.logger.info("position %s got opened" % position.id)
                    position.status = "open"
                    position.filled_entry = order.executed_price
                    position.entry_tstamp = order.execution_tstamp
                    # clear other side
                    other_id = self.get_other_direction_id(position.id)
                    if other_id in self.open_positions.keys():
                        self.open_positions[other_id].markForCancel = bars[0].tstamp
                    # add stop
                    order = Order(orderId=self.generate_order_id(positionId=position.id,
                                                                 type=OrderType.SL),
                                  stop=position.initial_stop,
                                  amount=-position.amount)
                    self.order_interface.send_order(order)
                    # added temporarily, cause sync with open orders is in the next loop and otherwise the orders vs
                    # position check fails
                    if order not in account.open_orders:  # outside world might have already added it
                        account.open_orders.append(order)

                elif (orderType == OrderType.SL or orderType == OrderType.TP) and position.status == "open":
                    self.logger.info("position %s got closed" % position.id)
                    position.status = "closed"
                    position.filled_exit = order.executed_price
                    position.exit_tstamp = order.execution_tstamp
                    position.exit_equity = account.equity
                    self.position_closed(position, account)
                else:
                    self.logger.warn(
                        "don't know what to do with execution of " + order.id + " for position " + str(
                            position))
            else:
                self.logger.warn("no position found on execution of " + order.id)

        self.known_order_history = len(account.order_history)
        self.sync_positions_with_open_orders(bars, account)

    def sync_positions_with_open_orders(self, bars: List[Bar], account: Account):
        raise NotImplementedError

    #####################################################

    def save_open_positions(self):
        if self.unique_id is None:
            return
        base = 'openPositions/'
        try:
            os.makedirs(base)
        except Exception:
            pass
        with open(base + self._get_pos_file(), 'w') as file:
            pos_json = []
            for pos in self.open_positions:
                pos_json.append(self.open_positions[pos].to_json())
            data = {"last_time": self.last_time,
                    "last_tick": str(self.last_tick_time),
                    "positions": pos_json}
            json.dump(data, file)

    def cancel_all_orders_for_position(self, positionId, account: Account):
        to_cancel = []
        for order in account.open_orders:
            if self.position_id_from_order_id(order.id) == positionId:
                to_cancel.append(order)

        for o in to_cancel:
            self.order_interface.cancel_order(o)

    def position_closed(self, position: Position, account: Account):
        self.position_history.append(position)
        del self.open_positions[position.id]

        # cancel other open orders of this position (sl/tp etc)
        self.logger.info("canceling remaining orders for position: " + position.id)
        self.cancel_all_orders_for_position(position.id, account)

        if self.unique_id is None:
            return
        base = 'positionHistory/'
        filename = base + self._get_pos_file()
        size = 0
        try:
            os.makedirs(base)
        except Exception:
            pass
        try:
            size = os.path.getsize(filename)
        except Exception:
            pass
        with open(filename, 'a') as file:
            writer = csv.writer(file)
            if size == 0:
                csv_columns = ['signalTStamp', 'size', 'wantedEntry', 'initialStop', 'openTime', 'openPrice',
                               'closeTime',
                               'closePrice', 'equityOnExit']
                writer.writerow(csv_columns)
            writer.writerow([
                datetime.fromtimestamp(position.signal_tstamp).isoformat(),
                position.amount,
                position.wanted_entry,
                position.initial_stop,
                datetime.fromtimestamp(position.entry_tstamp).isoformat(),
                position.filled_entry,
                datetime.fromtimestamp(position.exit_tstamp).isoformat(),
                position.filled_exit,
                position.exit_equity
            ])

    def on_tick(self, bars: List[Bar], account: Account):
        """checks price and levels to manage current orders and set new ones"""
        self.last_tick_time = datetime.now()
        self.update_new_bar(bars)
        self.prep_bars(bars)
        try:
            self.manage_open_orders(bars, account)
            self.open_orders(bars, account)
        except Exception as e:
            self.save_open_positions()
            raise e
        self.save_open_positions()

    def prep_bars(self, bars: List[Bar]):
        pass

    ###
    # Order Management
    ###

    def manage_open_orders(self, bars: list, account: Account):
        pass

    def open_orders(self, bars: list, account: Account):
        pass

    def update_new_bar(self, bars: List[Bar]):
        """checks if this tick started a new bar.
        only works on the first call of a bar"""
        if bars[0].tstamp != self.last_time:
            self.last_time = bars[0].tstamp
            self.is_new_bar = True
        else:
            self.is_new_bar = False

    ####
    # additional stuff
    ###

    def create_performance_plot(self):
        self.logger.info("preparing stats")
        stats = {
            "dd": 0,
            "maxDD": 0,
            "hh": 1,
            "underwaterDays": 0,
            "percWin": 0,
            "avgResult": 0,
            "tradesInRange": 0,
            "maxWinner": 0,
            "maxLoser": 0
        }

        yaxis = {
            "equity": 'y1',
            "dd": 'y2',
            "maxDD": 'y2',
            "hh": 'y1',
            "underwaterDays": 'y5',
            "tradesInRange": 'y6',
            "percWin": 'y7',
            "avgResult": 'y4',
            "maxWinner": 'y4',
            "maxLoser": 'y4'
        }

        months_in_range = 1
        alpha = 0.3
        firstPos = self.position_history[0]
        lastHHTstamp = firstPos.signal_tstamp
        startEquity = firstPos.exit_equity - firstPos.amount * (1 / firstPos.filled_entry - 1 / firstPos.filled_exit)

        stats_range = []
        actual_history = list(
            filter(lambda p: p.filled_entry is not None and p.filled_exit is not None, self.position_history))
        for pos in actual_history:
            # update range
            stats_range.append(pos)
            range_start = pos.exit_tstamp - months_in_range * 30 * 60 * 60 * 60
            while stats_range[0].exit_tstamp < range_start:
                stats_range.pop(0)

            avg = 0.0
            stats['tradesInRange'] = alpha * len(stats_range) + stats['tradesInRange'] * (1 - alpha)
            winners = 0.0
            maxWinner = 0
            maxLoser = 0
            for p in stats_range:
                # BEWARE: assumes inverse swap
                result = p.amount / p.filled_entry - p.amount / p.filled_exit
                maxLoser = min(result, maxLoser)
                maxWinner = max(result, maxWinner)
                avg += result / len(stats_range)
                if result > 0:
                    winners += 1.0

            stats['percWin'] = alpha * (100.0 * winners / len(stats_range)) + stats['percWin'] * (1 - alpha)
            stats['avgResult'] = alpha * avg + stats['avgResult'] * (1 - alpha)
            stats['maxWinner'] = alpha * maxWinner + stats['maxWinner'] * (1 - alpha)
            stats['maxLoser'] = alpha * (-maxLoser) + stats['maxLoser'] * (1 - alpha)

            if stats['hh'] < pos.exit_equity:
                stats['hh'] = pos.exit_equity
                lastHHTstamp = pos.exit_tstamp

            stats['underwaterDays'] = (pos.exit_tstamp - lastHHTstamp) / (60 * 60 * 24)
            dd = stats['hh'] - pos.exit_equity
            if dd > stats['maxDD']:
                stats['maxDD'] = dd
            stats['dd'] = dd
            stats['equity'] = pos.exit_equity

            pos.stats = stats.copy()
            pos.stats['equity'] = pos.exit_equity - startEquity
            pos.stats['hh'] = pos.stats['hh'] - startEquity

        self.logger.info("creating equityline")
        time = list(map(lambda p: datetime.fromtimestamp(p.exit_tstamp), actual_history))

        data = []
        for key in yaxis.keys():
            sub_data = list(map(lambda p: p.stats[key], actual_history))
            data.append(
                go.Scatter(x=time, y=sub_data, mode='lines', yaxis=yaxis[key], name=key + ":" + "%.1f" % (stats[key])))

        layout = go.Layout(
            xaxis=dict(
                anchor='y5'
            ),
            yaxis=dict(
                domain=[0.4, 1]
            ),
            yaxis2=dict(
                domain=[0.4, 1],
                range=[0, 2 * stats['maxDD']],
                overlaying='y',
                side='right'
            ),
            yaxis3=dict(
                domain=[0.2, 0.39]
            ),
            yaxis4=dict(
                domain=[0.2, 0.39],
                overlaying='y3',
                side='right'
            ),
            yaxis5=dict(
                domain=[0, 0.19]
            ),
            yaxis6=dict(
                domain=[0, 0.19],
                overlaying='y5',
                side='right'
            ),
            yaxis7=dict(
                domain=[0, 0.19],
                range=[0, 100],
                overlaying='y5',
                side='right'
            )
        )

        fig = go.Figure(data=data, layout=layout)
        fig.update_layout(xaxis_rangeslider_visible=False)
        return fig

    def add_to_plot(self, fig, bars, time):
        self.logger.info("adding trades")
        # trades
        for pos in self.position_history:
            if pos.status == "closed":
                fig.add_shape(go.layout.Shape(
                    type="line",
                    x0=datetime.fromtimestamp(pos.entry_tstamp),
                    y0=pos.filled_entry,
                    x1=datetime.fromtimestamp(pos.exit_tstamp),
                    y1=pos.filled_exit,
                    line=dict(
                        color="Green" if pos.amount > 0 else "Red",
                        width=2,
                        dash="solid"
                    )
                ))
            if pos.status == "notFilled":
                fig.add_shape(go.layout.Shape(
                    type="line",
                    x0=datetime.fromtimestamp(pos.signal_tstamp),
                    y0=pos.wanted_entry,
                    x1=datetime.fromtimestamp(pos.exit_tstamp),
                    y1=pos.wanted_entry,
                    line=dict(
                        color="Blue",
                        width=1,
                        dash="dot"
                    )
                ))

        fig.update_shapes(dict(xref='x', yref='y'))
