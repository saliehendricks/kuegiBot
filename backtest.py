from kuegi_bot.backtest_engine import BackTest
from kuegi_bot.bots.MultiStrategyBot import MultiStrategyBot
from kuegi_bot.bots.strategies.strat_with_exit_modules import SimpleBE, ParaTrail
from kuegi_bot.bots.strategies.SfpStrat import SfpStrategy
from kuegi_bot.bots.strategies.kuegi_strat import KuegiStrategy
from kuegi_bot.utils.helper import load_bars, prepare_plot
from kuegi_bot.utils import log
from kuegi_bot.kuegi_channel import KuegiChannel
from kuegi_bot.bots.kuegi_bot import KuegiBot
from kuegi_bot.bots.sfp_bot import SfpBot

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

def increment(min,max,current)->bool:
    current[0] += 1
    for idx in range(len(current)):
        if min[idx] <= current[idx] <= max[idx]:
            return True
        current[idx]= min[idx]
        if idx < len(current)-1:
            current[idx+1] += 1
        else:
            return False

def runOpti(bars,min,max):
    v= min[:]
    while True:
        msg= ""
        for i in v:
            msg += str(i) + " "
        logger.info(msg)
        bot = MultiStrategyBot(logger=logger, directionFilter=0)
        bot.add_strategy(KuegiStrategy(
            min_channel_size_factor=1.618, max_channel_size_factor=16,
            entry_tightening=0.1, bars_till_cancel_triggered=3,
            stop_entry=True, delayed_entry=False, delayed_cancel=True)
            .withChannel( max_look_back=13, threshold_factor=2.5, buffer_factor=-0.0618,max_dist_factor=1, max_swing_length=4)
            .withRM(risk_factor=1, max_risk_mul=2, risk_type=0)
            .withExitModule(SimpleBE(factor=0.1*v[0], buffer=0.1*v[1]))
            .withExitModule(ParaTrail(accInit=0.004, accInc=0, accMax=0.01))
            #.withTrail(trail_to_swing=False, delayed_swing=False,trail_back=False)
            )
        BackTest(bot, bars).run()

        if not increment(min,max,v):
            break


#bars_b = load_bars(30 * 12, 240,0,'bybit')
bars_m = load_bars(30 * 24, 240,0,'bitmex')

#bars_b = load_bars(30 * 12, 60,0,'bybit')
#bars_m = load_bars(30 * 24, 60,0,'bitmex')

#bars1= load_bars(24)
#bars2= process_low_tf_bars(m1_bars, 240, 60)
#bars3= process_low_tf_bars(m1_bars, 240, 120)
#bars4= process_low_tf_bars(m1_bars, 240, 180)

#runOpti(bars_b,[5,2,13,6],[10,5,18,10])

'''

Bybit:

bot=MultiStrategyBot(logger=logger, directionFilter= 0)
bot.add_strategy(SfpStrategy(
    init_stop_type=1, tp_fac=10,
    min_wick_fac=0.5, min_swing_length=11,
    range_length=70, range_filter_fac=0,
    close_on_opposite=False)
                 .withChannel(max_look_back=13, threshold_factor=0.8, buffer_factor=0.05, max_dist_factor=1,
                              max_swing_length=4)
                 .withRM(risk_factor=4, max_risk_mul=2, risk_type=0)
                 .withExitModule(SimpleBE(factor=0.6, buffer=0.4))
                 .withExitModule(SimpleBE(factor=1.6, buffer=0.8))
                 .withExitModule(ParaTrail(accInit=0.005, accInc=0.01, accMax=0.1))
                 .withTrail(trail_to_swing=False, delayed_swing=False, trail_back=False)
                 )
                 
                 
bot=MultiStrategyBot(logger=logger, directionFilter= 0)
bot.add_strategy(KuegiStrategy(
    min_channel_size_factor=0, max_channel_size_factor=16,
    entry_tightening=1, bars_till_cancel_triggered=5,
    stop_entry=True, delayed_entry=True, delayed_cancel=True)
    .withChannel(max_look_back=13, threshold_factor=0.8, buffer_factor=0.05,max_dist_factor=2,max_swing_length=4)
    .withRM(risk_factor=1, max_risk_mul=2, risk_type=1)
    .withExitModule(SimpleBE(factor=0.5, buffer=-0.1))
    .withExitModule(SimpleBE(factor=1, buffer=0.5))
    .withExitModule(ParaTrail(accInit=0.015, accInc=0.015, accMax=0.03))
                 )
b= BackTest(bot, bars_b).run()

#Bitmex:

bot=MultiStrategyBot(logger=logger, directionFilter= 0)
bot.add_strategy(KuegiStrategy(
    min_channel_size_factor=1.618, max_channel_size_factor=16,
    entry_tightening=0.1, bars_till_cancel_triggered=3,
    stop_entry=True, delayed_entry=False, delayed_cancel=True)
    .withChannel( max_look_back=13, threshold_factor=2.5, buffer_factor=-0.0618,max_dist_factor=1, max_swing_length=4)
    .withRM(risk_factor=1, max_risk_mul=2, risk_type=0)
    .withExitModule(SimpleBE(factor=1.2, buffer=0.2))
    .withExitModule(ParaTrail(accInit=0.004, accInc=0.003, accMax=0.07))
    )
b= BackTest(bot, bars_m).run()


bot.create_performance_plot().show()

b.prepare_plot().show()

good be levels kuegi: 5/-1 10/5 13/8 15/11

# 5 0 10 5 -> 10.76

good be levels sfp: 6/4  10/5  16/8  20/16 -> 7.22
#  6 4 10 5 -> 5.54
# 8 3 16 7 -> 5.7
6 4 16 7 -> 5.86
6 4 16 8 -> 6.36

6 4 17 13 -> 5,88

6 4 25 14-> 6,66
6 4 20 16 -> 6,90
'''

'''
##### SFP 240



2020-03-03
bybit 12: pos: 106 | profit: 36.72 | HH: 37.52 | maxDD: 3.71 | rel: 9.80 | UW days: 34.8

    init_stop_type=1, tp_fac=10,
    min_wick_fac=0.5, min_swing_length=11,
    range_length=70, range_filter_fac=0,
    close_on_opposite=False)
                 .withChannel(max_look_back=13, threshold_factor=0.8, buffer_factor=0.05, max_dist_factor=1,
                              max_swing_length=4)
                 .withRM(risk_factor=1, max_risk_mul=2, risk_type=0)
                 .withExitModule(SimpleBE(factor=0.6, buffer=0.4))
                 .withExitModule(SimpleBE(factor=1.6, buffer=0.8))
                 .withExitModule(ParaTrail(accInit=0.005, accInc=0.01, accMax=0.1))
                 .withTrail(trail_to_swing=False, delayed_swing=False, trail_back=False)
             


bitmex 24:  pos: 604 | profit: 101.65 | HH: 117.14 | maxDD: 18.33 | rel: 2.83 | UW days: 113.1

             init_stop_type=2, tp_fac=25,
             min_wick_fac=0.3, min_swing_length=2,
             range_length=20, range_filter_fac=0,
             close_on_opposite=False)
    .withChannel(max_look_back=13, threshold_factor=0.8, buffer_factor=0.05,max_dist_factor=1,max_swing_length=4)
    .withRM(risk_factor=1, max_risk_mul=2, risk_type=0)
    .withExitModule(SimpleBE(factor=1, buffer=0.3))
    .withTrail(trail_to_swing=False, delayed_swing=False,trail_back=False)
            


############## Kuegi Bot

bot=MultiStrategyBot(logger=logger, directionFilter= 0)
bot.add_strategy(KuegiStrategy(
    min_channel_size_factor=0, max_channel_size_factor=16, 
    entry_tightening=1, bars_till_cancel_triggered=5,
    stop_entry=True, delayed_entry=True, delayed_cancel=True)
    .withChannel(max_look_back=13, threshold_factor=0.8, buffer_factor=0.05,max_dist_factor=2,max_swing_length=4)
    .withRM(risk_factor=1, max_risk_mul=2, risk_type=1) 
    .withExitModule(SimpleBE(factor=1, buffer=0.4))
    .withTrail(trail_to_swing=False, delayed_swing=True,trail_back=False)
                 )
b= BackTest(bot, bars_b).run()

bot.create_performance_plot().show()

b.prepare_plot().show()

#'''

#BackTest(bot, bars1).run().prepare_plot().show()

''' results on 24 month test    

12 mo bybit:  pos: 168 | profit: 43.14 | HH: 50.95 | maxDD: 12.41 | rel: 3.48 | UW days: 43.8
12 mo bitmex: pos: 180 | profit: 26.76 | HH: 26.76 | maxDD: 30.17 | rel: 0.89 | UW days: 199.9
24 mo bitmex: pos: 321 | profit: 4.78 | HH: 18.93 | maxDD: 42.59 | rel: 0.11 | UW days: 290.3
original: pos: 319 | profit: 39.17 | HH: 39.17 | maxDD: 30.71 | rel: 1.28 | UW days: 202.4
    max_look_back=13, threshold_factor=0.9, buffer_factor=0.05,
    max_dist_factor=2, max_swing_length=3,
    min_channel_size_factor=0, max_channel_size_factor=6, 
    risk_factor=1, entry_tightening=1, bars_till_cancel_triggered=5,
    be_factor= 1.5, allow_trail_back= False,
    stop_entry=True, trail_to_swing=True, delayed_entry=True, delayed_cancel=True
    
##########
Bybit Opti:
    
Fokus relation stand 2020-03-03
12 mo bybit: pos: 170 | profit: 126.02 | HH: 139.37 | maxDD: 13.64 | maxExp: 357.33 | rel: 9.14 | UW days: 42.5 | pos days: 0.0/2.1/20.2
    min_channel_size_factor=0, max_channel_size_factor=16,
    entry_tightening=1, bars_till_cancel_triggered=5,
    stop_entry=True, delayed_entry=True, delayed_cancel=True)
                 .withChannel(max_look_back=13, threshold_factor=0.8, buffer_factor=0.05,max_dist_factor=2,max_swing_length=4)
                 .withRM(risk_factor=1, max_risk_mul=2, risk_type=1)
                 .withExitModule(SimpleBE(factor=0.5, buffer=-0.1))
                 .withExitModule(SimpleBE(factor=1, buffer=0.5))
                 .withExitModule(ParaTrail(accInit=0.015, accInc=0.015, accMax=0.03))

#############
Bitmex Opti
Fokus on Profit/DD: 
12 mo bybit pos: 266 | profit: 50.77 | HH: 66.65 | maxDD: 22.89 | rel: 2.22 | UW days: 94.93

12 months: pos: 273 | profit: 125.10 | HH: 125.10 | maxDD: 11.67 | maxExp: 267.47 | rel: 10.93 | UW days: 28.7 | pos days: 0.0/4.1/18.3
24 months: pos: 553 | profit: 289.02 | HH: 289.02 | maxDD: 11.67 | maxExp: 388.81 | rel: 12.63 | UW days: 28.7 | pos days: 0.0/4.5/21.3
    min_channel_size_factor=1.618, max_channel_size_factor=16,
    entry_tightening=0.1, bars_till_cancel_triggered=3,
    stop_entry=True, delayed_entry=False, delayed_cancel=True)
    .withChannel( max_look_back=13, threshold_factor=2.5, buffer_factor=-0.0618,max_dist_factor=1, max_swing_length=4)
    .withRM(risk_factor=1, max_risk_mul=2, risk_type=0)
    .withExitModule(SimpleBE(factor=1.2, buffer=0.2))
    .withExitModule(ParaTrail(accInit=0.004, accInc=0.003, accMax=0.07))
    


low UW: 
24 months: pos: 383 | profit: 91.10 | HH: 101.66 | maxDD: 13.25 | rel: 6.88 | UW days: 55.9
48 months: pos: 763 | profit: 224.53 | HH: 228.34 | maxDD: 16.29 | rel: 13.78 | UW days: 140.0
    max_look_back=13, threshold_factor=2.5, buffer_factor=-0.0618,
    max_dist_factor=1, max_swing_length=4,
    min_channel_size_factor=0, max_channel_size_factor=16.18, 
    risk_factor=1, max_risk_mul=2, risk_type= 2,
    entry_tightening=0,bars_till_cancel_triggered=3,
    be_factor= 2, allow_trail_back= True,
    stop_entry=True, trail_to_swing=False, delayed_entry=True, delayed_cancel=True



buffer 0: pos: 516 | profit: 120.09 | HH: 125.58 | maxDD: 24.49 | rel: 4.90 | UW days: 97.3
    max_look_back=13, threshold_factor=2.5, buffer_factor=0,
    max_dist_factor=1, max_swing_length=3,
    max_channel_size_factor=6, risk_factor=1, entry_tightening=0,bars_till_cancel_triggered=3,
    be_factor= 2, allow_trail_back= True,
    stop_entry=True, trail_to_swing=False, delayed_entry=False, delayed_cancel=True

'''