import os
from datetime import datetime, timedelta

import logging

from src.strategies.CallStrategyAtClose import CallStrategyAtClose
from src.utils.kp_secrets import extract_kp_secrets
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

    s2 = CallStrategyAtClose(name="oco_petit_joueur",
                             initial_investment_in_base_symbol_quantity= 100,
                             exchange_client= client,
                             token = "BTC",
                             base_symbol = "EUR",
                             symbol= "BTCEUR",
                             mode='live')
    runstep("live s2", s2.run)
    logger.info("Done.")
