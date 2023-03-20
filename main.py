import os
import yaml
import logging

from src.utils.kp_secrets import extract_kp_secrets
from src.strategies.strategy1 import Strategy1
from src.api import BinanceAPIClient

logging.basicConfig(level = logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MainStep():
    def __init__(self, name):
        self.name = name

    def run(self, func):
        logger.info(f'running {self.name}')
        return func()

def runstep(name, func):
    return MainStep(name).run(func)

# NOT GENERIC #
##################################################
if __name__ == "__main__":
    kp_secrets = runstep('keepass access', extract_kp_secrets)

    client = BinanceAPIClient(kp_secrets['BNB_API_KEY'], kp_secrets['BNB_SECRET_KEY'])
    runstep('binance test', client.print_top_assets)

    s1 = Strategy1('s1', client)

    try:
        runstep('s1', s1.run)
    except Exception as e:
        logging.error(f"An error occurred in s1: %s", e)

    logger.info('\n\nDone.')