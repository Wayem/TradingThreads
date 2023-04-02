from typing import List

from main import runstep
from src.api import BinanceAPIClient
from src.strategies import BaseStrategyThread
from src.strategies.strategy2 import PlaceOcoWhenItsTime
from src.utils.kp_secrets import extract_kp_secrets


class Backtester():
    def __init__(self, strategies):
        self.client = None # shouldnt have to use this for backstest. Local data only
        self.strategies: List[BaseStrategyThread] = strategies

    def run(self):
        dct_of_df_with_buy_sl_tp_columns = {strategy.name: None for strategy in self.strategies}
        for strategy in self.strategies:
            dct_of_df_with_buy_sl_tp_columns = strategy.run()

        return dct_of_df_with_buy_sl_tp_columns


if __name__ == "__main__":
    btc = "BTC"
    eur = "EUR"
    BTCEUR = btc + eur

    s2 = PlaceOcoWhenItsTime("s2", None, BTCEUR)
    backtester = Backtester([s2])

    dct_of_df_with_buy_sl_tp_columns = backtester.run()

    print(f'got df_with_buy_sl_tp_columns for : {dct_of_df_with_buy_sl_tp_columns.keys()}')

