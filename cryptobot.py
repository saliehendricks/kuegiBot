import atexit
import signal
import sys
import threading
from time import sleep
from typing import List

from kuegi_bot.bots.kuegi_bot import KuegiBot
from kuegi_bot.trade_engine import LiveTrading
from kuegi_bot.utils import log
from kuegi_bot.utils.dotdict import dotdict
from kuegi_bot.utils.helper import load_settings_from_args


def start_bot(botSettings):
    live = LiveTrading(settings=botSettings,
                       trading_bot=KuegiBot(max_look_back=botSettings.KB_MAX_LOOK_BACK,
                                            threshold_factor=botSettings.KB_THRESHOLD_FACTOR,
                                            buffer_factor=botSettings.KB_BUFFER_FACTOR,
                                            max_dist_factor=botSettings.KB_MAX_DIST_FACTOR,
                                            max_swing_length=botSettings.KB_MAX_SWING_LENGTH,
                                            min_channel_size_factor=botSettings.KB_MIN_CHANNEL_SIZE_FACTOR,
                                            max_channel_size_factor=botSettings.KB_MAX_CHANNEL_SIZE_FACTOR,
                                            risk_factor=botSettings.KB_RISK_FACTOR,
                                            risk_type=botSettings.KB_RISK_TYPE,
                                            max_risk_mul=botSettings.KB_MAX_RISK_MUL,
                                            entry_tightening=botSettings.KB_ENTRY_TIGHTENING,
                                            bars_till_cancel_triggered=botSettings.KB_BARS_TILL_CANCEL_TRIGGERED,
                                            be_factor=botSettings.KB_BE_FACTOR,
                                            allow_trail_back=botSettings.KB_ALLOW_TRAIL_BACK,
                                            stop_entry=botSettings.KB_STOP_ENTRY,
                                            trail_to_swing=botSettings.KB_TRAIL_TO_SWING,
                                            delayed_entry=botSettings.KB_DELAYED_ENTRY,
                                            delayed_cancel=botSettings.KB_DELAYED_CANCEL
                                            ))
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


activeThreads: List[threading.Thread] = []

signal.signal(signal.SIGTERM, term_handler)
signal.signal(signal.SIGINT, term_handler)
atexit.register(stop_all_and_exit)

settings = load_settings_from_args()

if not settings:
    print("error: no settings defined. nothing to do. exiting")
    sys.exit()

logger = log.setup_custom_logger("cryptobot",
                                 log_level=settings.LOG_LEVEL,
                                 logToConsole=settings.LOG_TO_CONSOLE,
                                 logToFile=settings.LOG_TO_FILE)
logger.info("###### loading %i bots #########" % len(settings.bots))
if settings.bots is not None:
    sets = settings.bots[:]
    del settings.bots  # settings is now just the meta settings
    for botSetting in sets:
        usedSettings = dict(settings)
        usedSettings = dotdict(usedSettings)
        usedSettings.update(botSetting)
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
else:
    logger.warn("no bots defined. nothing to do")
