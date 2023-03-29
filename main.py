import os
import yaml
import logging

from src.utils.kp_secrets import extract_kp_secrets
from src.strategies.strategy2 import PlaceOcoWhenItsTime
from src.api import BinanceAPIClient

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

    token = "BTC"
    base_token = "EUR"
    symbol = token + base_token

    logger.info('fetching historical data ...')
    df = client.get_historical_data(symbol, short_interval, start_time_ms)
    runstep("binance test", client.print_top_assets)

    runstep("testing binance cache", client.print_top_assets)

    s2 = PlaceOcoWhenItsTime("s2", client)

    runstep("s2", s2.run)

    logger.info("Done.")
