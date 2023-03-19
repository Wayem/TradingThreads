import os
import yaml
import logging.config

from src.utils.kp_secrets import extract_kp_secrets
from src.strategies.strategy1 import Strategy1
from src.api.binance import BinanceAPIClient

logging.config.fileConfig('logging.conf')

class MainStep():
    def __init__(self, name):
        self.name = name
        self.logger = logging.getLogger(self.name)

    def run(self, func):
        self.logger.debug(f'')
        return func()

def runstep(name, func):
    return MainStep(name).run(func)

# NOT GENERIC #
##################################################
if __name__ == "__main__":
    kp_secrets = runstep('keepass access', extract_kp_secrets)

    client = BinanceAPIClient(kp_secrets['BNB_API_KEY'], kp_secrets['BNB_SECRET_KEY'])
    runstep('binance test', client.print_top_assets)
