from threading import Thread
from time import sleep
from src.strategies import BaseStrategyThread
import logging
import logging.config

class Strategy1(BaseStrategyThread):
    def __init__(self, name, exchange_client):
        super().__init__(name, exchange_client)

    def run(self):
        self.logger.info('starting ...')
        while True:
            pass
            raise NotImplementedError
