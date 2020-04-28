from kuegi_bot.backtest_engine import BackTest
from kuegi_bot.bots.MultiStrategyBot import MultiStrategyBot
from kuegi_bot.bots.strategies.entry_filters import DayOfWeekFilter
from kuegi_bot.bots.strategies.exit_modules import SimpleBE, ParaTrail
from kuegi_bot.bots.strategies.SfpStrat import SfpStrategy
from kuegi_bot.bots.strategies.kuegi_strat import KuegiStrategy
from kuegi_bot.utils.helper import load_bars, prepare_plot
from kuegi_bot.utils import log
from kuegi_bot.kuegi_channel import KuegiChannel
from kuegi_bot.bots.kuegi_bot import KuegiBot
from kuegi_bot.bots.sfp_bot import SfpBot
from kuegi_bot.utils.trading_classes import Symbol

logger = log.setup_custom_logger()


def plot(bars):
    forplot= bars[:]

    logger.info("initializing indicators")
    indis = [KuegiChannel()]

    logger.info("preparing plot")
    fig= prepare_plot(forplot, indis)
    fig.show()


def backtest(bars):
    bots= []
    for bot in bots:
        BackTest(bot,bars).run()


def increment(min,max,steps,current)->bool:
    current[0] += steps[0]
    for idx in range(len(current)):
        if min[idx] <= current[idx] <= max[idx]:
            return True
        current[idx]= min[idx]
        if idx < len(current)-1:
            current[idx+1] += steps[idx+1]
        else:
            return False


def runOpti(bars,min,max,steps,symbol= None):
    v= min[:]
    while True:
        msg= ""
        for i in v:
            msg += str(i) + " "
        logger.info(msg)
        bot = MultiStrategyBot(logger=logger, directionFilter=0)
        bot.add_strategy(KuegiStrategy(
            min_channel_size_factor=v[2], max_channel_size_factor=v[3],
            entry_tightening=v[1]/10, bars_till_cancel_triggered=5,
            stop_entry=True, delayed_entry=v[0] == 1, delayed_cancel=True, cancel_on_filter= False)
                         .withChannel(max_look_back=v[4], threshold_factor=v[5]/10, buffer_factor=v[6]*0.01,
                                      max_dist_factor=2,max_swing_length=4)
                         .withRM(risk_factor=1, max_risk_mul=2, risk_type=1, atr_factor=2)
                         #.withExitModule(SimpleBE(factor=0.5, buffer=-0.1))
                         #.withExitModule(SimpleBE(factor=1, buffer=0.5))
                         .withExitModule(ParaTrail(accInit=0.015, accInc=0.015, accMax=0.03))
                         #.withEntryFilter(DayOfWeekFilter(55))
                         )
        BackTest(bot, bars,symbol).run()

        if not increment(min,max,steps,v):
            break

def checkDayFilterByDay(bars,symbol= None):
    for i in range(7):
        msg = str(i)
        logger.info(msg)
        bot = MultiStrategyBot(logger=logger, directionFilter=0)
        bot.add_strategy(KuegiStrategy(
            min_channel_size_factor=0, max_channel_size_factor=16,
            entry_tightening=1, bars_till_cancel_triggered=5,
            stop_entry=True, delayed_entry=True, delayed_cancel=True, cancel_on_filter= False)
                         .withChannel(max_look_back=13, threshold_factor=2.6, buffer_factor=0.05,max_dist_factor=2,max_swing_length=4)
                         .withRM(risk_factor=2000, max_risk_mul=2, risk_type=1, atr_factor=2)
                         .withExitModule(SimpleBE(factor=0.5, buffer=-0.1))
                         .withExitModule(SimpleBE(factor=1, buffer=0.5))
                         .withExitModule(ParaTrail(accInit=0.015, accInc=0.015, accMax=0.03))
                         .withEntryFilter(DayOfWeekFilter(55))
                         )

        b= BackTest(bot, bars,symbol).run()

bars_n = load_bars(30 * 12, 240,0,'binance')
#bars_ns = load_bars(30 * 24, 240,0,'binanceSpot')
#bars_b = load_bars(30 * 18, 240,0,'bybit')
#bars_m = load_bars(30 * 12, 240,0,'bitmex')

#bars_b = load_bars(30 * 12, 60,0,'bybit')
#bars_m = load_bars(30 * 24, 60,0,'bitmex')

#bars1= load_bars(24)
#bars2= process_low_tf_bars(m1_bars, 240, 60)
#bars3= process_low_tf_bars(m1_bars, 240, 120)
#bars4= process_low_tf_bars(m1_bars, 240, 180)

#runOpti(bars_m,[1],[63],[1])

#checkDayFilterByDay(bars_m)

runOpti(bars_n,
        [0,0 ,0  ,10,8 ,5 ,-10],
        [1,10,2  ,20,16,30, 10],
        [1,1 ,0.5,2 ,2 ,5 ,  2],
        symbol=Symbol(symbol="BTCUSDT", isInverse=False, tickSize=0.001,
                                      lotSize=0.00001, makerFee=0.02,
                                     takerFee=0.04))


'''
bot=MultiStrategyBot(logger=logger, directionFilter= 0)
bot.add_strategy(KuegiStrategy(
...
                 )
                 
bot.add_strategy(SfpStrategy(
...
                 )
b= BackTest(bot, bars_b).run()

#binance is not inverse: needs different symbol:

b= BackTest(bot, bars_n,
        symbol=Symbol(symbol="BTCUSDT", isInverse=False, tickSize=0.001, lotSize=0.00001, makerFee=0.02,
                                     takerFee=0.04)).run()

#performance chart with lots of numbers
bot.create_performance_plot().show()

# chart with signals:
b.prepare_plot().show()

#'''
