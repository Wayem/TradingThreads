import os
from datetime import datetime, timedelta

import logging

from src.utils.kp_secrets import extract_kp_secrets
from src.api import BinanceAPIClient

LOCAL_TZ = 'Europe/Paris'

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

dir_path = os.path.dirname(os.path.realpath(__file__))
logs_dir = os.path.join(dir_path, 'logs')
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)


class MainStep:
    def __init__(self, name):
        self.name = name

    def run(self, func):
        logger.info(f"running {self.name}")
        return func()


def runstep(name, func):
    return MainStep(name).run(func)


# NOT GENERIC #
##################################################
if __name__ == "__main__":
    kp_secrets = runstep("keepass access", extract_kp_secrets)
    client = BinanceAPIClient(kp_secrets["BNB_API_KEY"], kp_secrets["BNB_SECRET_KEY"])

    start_ytd = datetime.now() - timedelta(days=2)
    data = client.get_historical_data('BTCEUR', '15m', start_ytd, None)

    # # Localize the 'Open time' and 'Close time' columns to UTC and then convert to Paris local time
    data[f'Open time {LOCAL_TZ}'] = data['Open time'].dt.tz_localize('UTC').dt.tz_convert(LOCAL_TZ)
    data[f'Close time {LOCAL_TZ}'] = data['Close time'].dt.tz_localize('UTC').dt.tz_convert(LOCAL_TZ)

    print(data)

    # runstep("binance test", client.print_top_assets)

    # s2 = PlaceOcoWhenItsTime("s2", client, "BTCEUR", mode='live')
    # runstep("live s2", s2.run)
    # logger.info("Done.")
