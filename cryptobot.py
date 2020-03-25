import atexit
import json
import os
import signal
import sys
import threading
from time import sleep
from typing import List

from kuegi_bot.bots.MultiStrategyBot import MultiStrategyBot
from kuegi_bot.bots.kuegi_bot import KuegiBot
from kuegi_bot.bots.strategies.SfpStrat import SfpStrategy
from kuegi_bot.bots.strategies.kuegi_strat import KuegiStrategy
from kuegi_bot.bots.strategies.strat_with_exit_modules import SimpleBE, ParaTrail
from kuegi_bot.bots.trading_bot import TradingBot
from kuegi_bot.trade_engine import LiveTrading
from kuegi_bot.utils import log
from kuegi_bot.utils.dotdict import dotdict
from kuegi_bot.utils.helper import load_settings_from_args


def start_bot(botSettings):
    bot = MultiStrategyBot()
    if "strategies" in botSettings.keys():
        strategies = dict(botSettings.strategies)
        del botSettings.strategies  # settings is now just the meta settings
        for stratId in strategies.keys():
            stratSettings = dict(botSettings)
            stratSettings = dotdict(stratSettings)
            stratSettings.update(strategies[stratId])
            if stratSettings.KB_RISK_FACTOR <= 0:
                logger.error("if you don't want to risk money, you shouldn't even run this bot!")
                continue

            if stratId == "kuegi":
                strat = KuegiStrategy(min_channel_size_factor=stratSettings.KB_MIN_CHANNEL_SIZE_FACTOR,
                                      max_channel_size_factor=stratSettings.KB_MAX_CHANNEL_SIZE_FACTOR,
                                      entry_tightening=stratSettings.KB_ENTRY_TIGHTENING,
                                      bars_till_cancel_triggered=stratSettings.KB_BARS_TILL_CANCEL_TRIGGERED,
                                      stop_entry=stratSettings.KB_STOP_ENTRY,
                                      delayed_entry=stratSettings.KB_DELAYED_ENTRY,
                                      delayed_cancel=stratSettings.KB_DELAYED_CANCEL) \
                    .withChannel(max_look_back=stratSettings.KB_MAX_LOOK_BACK,
                                 threshold_factor=stratSettings.KB_THRESHOLD_FACTOR,
                                 buffer_factor=stratSettings.KB_BUFFER_FACTOR,
                                 max_dist_factor=stratSettings.KB_MAX_DIST_FACTOR,
                                 max_swing_length=stratSettings.KB_MAX_SWING_LENGTH)
                if "KB_TRAIL_TO_SWING" in stratSettings.keys():
                    strat.withTrail(trail_to_swing=stratSettings.KB_TRAIL_TO_SWING,
                                    delayed_swing=stratSettings.KB_DELAYED_ENTRY,
                                    trail_back=stratSettings.KB_ALLOW_TRAIL_BACK)
            elif stratId == "sfp":
                strat = SfpStrategy(init_stop_type=stratSettings.SFP_STOP_TYPE,
                                    tp_fac=stratSettings.SFP_TP_FAC,
                                    min_wick_fac=stratSettings.SFP_MIN_WICK_FAC,
                                    min_swing_length=stratSettings.SFP_MIN_SWING_LENGTH,
                                    range_length=stratSettings.SFP_RANGE_LENGTH,
                                    min_rej_length=stratSettings.SFP_MIN_REJ_LENGTH,
                                    range_filter_fac=stratSettings.SFP_RANGE_FILTER_FAC,
                                    close_on_opposite=stratSettings.SFP_CLOSE_ON_OPPOSITE) \
                    .withChannel(max_look_back=stratSettings.KB_MAX_LOOK_BACK,
                                 threshold_factor=stratSettings.KB_THRESHOLD_FACTOR,
                                 buffer_factor=stratSettings.KB_BUFFER_FACTOR,
                                 max_dist_factor=stratSettings.KB_MAX_DIST_FACTOR,
                                 max_swing_length=stratSettings.KB_MAX_SWING_LENGTH)
                if "KB_TRAIL_TO_SWING" in stratSettings.keys():
                    strat.withTrail(trail_to_swing=stratSettings.KB_TRAIL_TO_SWING,
                                    delayed_swing=stratSettings.KB_DELAYED_ENTRY,
                                    trail_back=stratSettings.KB_ALLOW_TRAIL_BACK)
            else:
                strat = None
                logger.warn("unkown strategy: " + stratId)
            if strat is not None:
                strat.withRM(risk_factor=stratSettings.KB_RISK_FACTOR,
                             risk_type=stratSettings.KB_RISK_TYPE,
                             max_risk_mul=stratSettings.KB_MAX_RISK_MUL)
                if "KB_BE_FACTOR" in stratSettings.keys():
                    strat.withExitModule(SimpleBE(factor=stratSettings.KB_BE_FACTOR,
                                                  buffer=stratSettings.KB_BE_BUFFER))
                if "KB_BE2_FACTOR" in stratSettings.keys():
                    strat.withExitModule(SimpleBE(factor=stratSettings.KB_BE2_FACTOR,
                                                  buffer=stratSettings.KB_BE2_BUFFER))
                if "EM_PARA_INIT" in stratSettings.keys():
                    strat.withExitModule(ParaTrail(accInit=stratSettings.EM_PARA_INIT,
                                                   accInc=stratSettings.EM_PARA_INC,
                                                   accMax=stratSettings.EM_PARA_MAX))
                bot.add_strategy(strat)
    else:
        if botSettings.KB_RISK_FACTOR <= 0:
            logger.error("if you don't want to risk money, you shouldn't even run this bot!")
        else:
            bot.add_strategy(KuegiStrategy(min_channel_size_factor=botSettings.KB_MIN_CHANNEL_SIZE_FACTOR,
                                           max_channel_size_factor=botSettings.KB_MAX_CHANNEL_SIZE_FACTOR,
                                           entry_tightening=botSettings.KB_ENTRY_TIGHTENING,
                                           bars_till_cancel_triggered=botSettings.KB_BARS_TILL_CANCEL_TRIGGERED,
                                           stop_entry=botSettings.KB_STOP_ENTRY,
                                           delayed_entry=botSettings.KB_DELAYED_ENTRY,
                                           delayed_cancel=botSettings.KB_DELAYED_CANCEL)
                             .withChannel(max_look_back=botSettings.KB_MAX_LOOK_BACK,
                                          threshold_factor=botSettings.KB_THRESHOLD_FACTOR,
                                          buffer_factor=botSettings.KB_BUFFER_FACTOR,
                                          max_dist_factor=botSettings.KB_MAX_DIST_FACTOR,
                                          max_swing_length=botSettings.KB_MAX_SWING_LENGTH)
                             .withRM(risk_factor=botSettings.KB_RISK_FACTOR,
                                     risk_type=botSettings.KB_RISK_TYPE,
                                     max_risk_mul=botSettings.KB_MAX_RISK_MUL)
                             .withExitModule(SimpleBE(factor=botSettings.KB_BE_FACTOR,
                                                      buffer=botSettings.KB_BE_BUFFER))
                             .withTrail(trail_to_swing=botSettings.KB_TRAIL_TO_SWING,
                                        delayed_swing=botSettings.KB_DELAYED_ENTRY,
                                        trail_back=botSettings.KB_ALLOW_TRAIL_BACK)
                             )
    live = LiveTrading(settings=botSettings, trading_bot=bot)
    t = threading.Thread(target=live.run_loop)
    t.bot: LiveTrading = live
    t.start()
    return t


def stop_all_and_exit():
    logger.info("closing bots")
    for t in activeThreads:
        t.bot.exit()

    logger.info("bye")
    atexit.unregister(stop_all_and_exit)
    sys.exit()


def term_handler(signum, frame):
    logger.info("got SIG %i" % signum)
    stop_all_and_exit()


def write_dashboard(dashboardFile):
    try:
        os.makedirs(os.path.dirname(dashboardFile))
    except Exception:
        pass
    with open(dashboardFile, 'w') as file:
        result = {}

        for thread in activeThreads:
            bot:LiveTrading= thread.bot
            result[bot.id]={
                'alive': bot.alive,
                "last_time": bot.bot.last_time,
                "last_tick": str(bot.bot.last_tick_time)}
            data= result[bot.id]
            data['positions'] = []

            for pos in bot.bot.open_positions:
                data['positions'].append(bot.bot.open_positions[pos].to_json())
        json.dump(result, file, sort_keys=False, indent=4)

def run(settings):
    signal.signal(signal.SIGTERM, term_handler)
    signal.signal(signal.SIGINT, term_handler)
    atexit.register(stop_all_and_exit)

    if not settings:
        print("error: no settings defined. nothing to do. exiting")
        sys.exit()

    logger.info("###### loading %i bots #########" % len(settings.bots))
    if settings.bots is not None:
        sets = settings.bots[:]
        del settings.bots  # settings is now just the meta settings
        for botSetting in sets:
            usedSettings = dict(settings)
            usedSettings = dotdict(usedSettings)
            usedSettings.update(botSetting)
            if len(usedSettings.API_KEY) == 0 or len(usedSettings.API_SECRET) == 0:
                logger.error("You have to put in apiKey and secret before starting!")
            else:
                logger.info("starting " + usedSettings.id)
                activeThreads.append(start_bot(usedSettings))

    logger.info("init done")

    if len(activeThreads) > 0:
        while True:
            sleep(1)
            allActive = True
            for thread in activeThreads:
                if not thread.is_alive() or not thread.bot.alive:
                    allActive = False
                    logger.info("%s died." % thread.bot.id)
                    break

            if not allActive:
                stop_all_and_exit()
                break
            write_dashboard(settings.DASHBOARD_FILE)

    else:
        logger.warn("no bots defined. nothing to do")


activeThreads: List[threading.Thread] = []
logger = None

if __name__ == '__main__':
    settings = load_settings_from_args()
    logger = log.setup_custom_logger("cryptobot",
                                     log_level=settings.LOG_LEVEL,
                                     logToConsole=settings.LOG_TO_CONSOLE,
                                     logToFile=settings.LOG_TO_FILE)
    run(settings)
else:
    logger = log.setup_custom_logger("cryptobot-pkg")
