import json
import logging
import sys

from kuegi_bot.bitmex.bitmex_interface import BitmexInterface
from kuegi_bot.bybit.bybit_interface import ByBitInterface
from kuegi_bot.utils import log
from kuegi_bot.utils.helper import load_settings_from_args

settings= load_settings_from_args()

logger = log.setup_custom_logger("cryptobot",
                                 log_level=settings.LOG_LEVEL,
                                 logToConsole=True,
                                 logToFile= False)


def onTick():
    logger.info("got Tick")

if settings.EXCHANGE == 'bybit':
    interface= ByBitInterface(settings= settings,logger= logger,on_tick_callback=onTick)
    b= interface.bybit
    w= interface.ws
else:
    interface= BitmexInterface(settings=settings,logger=logger,on_tick_callback=onTick)

bars= interface.get_bars(240,0)
