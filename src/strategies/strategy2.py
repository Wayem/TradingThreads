from threading import Thread
from time import sleep
from src.strategies import BaseStrategyThread
import logging
import logging.config
import talib
from src.utils import make_df
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from src.utils import plot_close_price_with_signals

class PlaceOcoWhenItsTime(BaseStrategyThread):
    def __init__(self, name, exchange_client):
        super().__init__(name, exchange_client)

        self.exchange_client = exchange_client
        self.token = "BTC"
        self.base_token = "EUR"
        self.symbol = self.token + self.base_token

        self.interval = "15m"
        self.days_of_historical_data = 2

        self.initial_investment = 1000

        self.take_profit_threshold=0.01
        self.stop_loss_threshold=0.03

    def apply_strategy_to_df(self, df):
        
        # Vous pouvez ajouter d'autres indicateurs techniques ici en utilisant TA-Lib, par exemple :
        # df['SMA'] = talib.SMA(df['Close'], timeperiod=20)
        
        # Initialiser les signaux d'achat et de vente
        df['Buy'] = False
        df['Stop loss'] = False
        df['Take profit'] = False

        in_position = False
        last_buy_price = None

        for i in range(1, len(df)):
            if not(in_position) and self.buy_condition(df, i):
                df.iat[i, df.columns.get_loc('Buy')] = True

                in_position = True
                last_buy_price = df.iat[i, df.columns.get_loc('Close')]

            elif in_position:
                if df.iat[i, df.columns.get_loc('Low')] <= last_buy_price * (1 - self.stop_loss_threshold):
                    df.iat[i, df.columns.get_loc('Stop loss')] = True
                    in_position = False

                elif df.iat[i, df.columns.get_loc('High')] >= last_buy_price * (1 + self.take_profit_threshold):
                    df.iat[i, df.columns.get_loc('Take profit')] = True
                    in_position = False
        #df.to_csv("toto.csv")
        return df

    def buy_condition(self, df, index):
        return df.iat[index, df.columns.get_loc('Close')] > df.iat[index - 1, df.columns.get_loc('Close')]

    def run(self):
        while not self.exit_flag.is_set():
            self.logger.info('starting ...')

            self.logger.info('fetching historical data ...')
            df = self.exchange_client.get_historical_data(self.symbol, self.interval, self.days_of_historical_data)
            signals = self.apply_strategy_to_df(df)
            self.logger.info('plotting ...')
            plot_close_price_with_signals(df, signals)
            self.stop()