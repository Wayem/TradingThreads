import os
import yaml
import logging

from src.utils.kp_secrets import extract_kp_secrets
from src.strategies.strategy2 import Pyramid
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

    s2 = Pyramid('s2', client)

    runstep('s2', s2.run)

    logger.info('Done.')