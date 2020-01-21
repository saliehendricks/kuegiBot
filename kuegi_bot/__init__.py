import argparse
import os

import shutil

__version__ = 'v1.0'


def run():
    parser = argparse.ArgumentParser(description='kuegi bot')
    parser.add_argument('settings.json', nargs='?', help='settings json to use')
    args = parser.parse_args()

    if args.command is not None and args.command.strip().lower() == 'setup':
        copy_files()

    else:
        # import kuegi_bot here rather than at the top because it depends on live.json existing
        try:
            from kuegi_bot.bots.kuegi_bot import KuegiBot
            from kuegi_bot.trade_engine import LiveTrading

            settings= {}

            live = LiveTrading(KuegiBot(max_look_back=settings.KB_MAX_LOOK_BACK,
                                        threshold_factor=settings.KB_THRESHOLD_FACTOR,
                                        buffer_factor=settings.KB_BUFFER_FACTOR,
                                        max_dist_factor=settings.KB_MAX_DIST_FACTOR,
                                        max_swing_length=settings.KB_MAX_SWING_LENGTH,
                                        min_channel_size_factor=settings.KB_MIN_CHANNEL_SIZE_FACTOR,
                                        max_channel_size_factor=settings.KB_MAX_CHANNEL_SIZE_FACTOR,
                                        risk_factor=settings.KB_RISK_FACTOR,
                                        entry_tightening=settings.KB_ENTRY_TIGHTENING,
                                        bars_till_cancel_triggered=settings.KB_BARS_TILL_CANCEL_TRIGGERED,
                                        be_factor=settings.KB_BE_FACTOR,
                                        allow_trail_back=settings.KB_ALLOW_TRAIL_BACK,
                                        stop_entry=settings.KB_STOP_ENTRY,
                                        trail_to_swing=settings.KB_TRAIL_TO_SWING,
                                        delayed_entry=settings.KB_DELAYED_ENTRY,
                                        delayed_cancel=settings.KB_DELAYED_CANCEL
                                        ))
            live.run_loop()
        except ImportError:
            print('Can\'t find live.json. Run "marketmaker setup" to create project.')


def copy_files():
    package_base = os.path.dirname(__file__)

    try:
        shutil.copytree(package_base, os.path.join(os.getcwd(), 'kuegi_bot'))
        print('Created marketmaker project.\n**** \nImportant!!!\nEdit live.json before starting the bot.\n****')
    except FileExistsError:
        print('Market Maker project already exists!')
