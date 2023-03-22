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

class Pyramid(BaseStrategyThread):
    def __init__(self, name, exchange_client):
        super().__init__(name, exchange_client)

        self.exchange_client = exchange_client
        self.symbol = "BTCUSDT"
        self.interval = "15m"
        self.days_of_historical_data = 2
        
        self.initial_investment = 1000
        self.position_value = 0
        self.in_position = False

    def apply_incremental_profit_strategy(self, df, buy_threshold=0.01, sell_threshold=0.01, stop_loss_threshold=0.05):
        
        # Vous pouvez ajouter d'autres indicateurs techniques ici en utilisant TA-Lib, par exemple :
        # df['SMA'] = talib.SMA(df['Close'], timeperiod=20)
        
        # Initialiser les signaux d'achat et de vente
        df['Buy'] = False
        df['Sell'] = False

        for i in range(1, len(df)):
            if not self.in_position and self.buy_condition(df, i):  # Insérez vos conditions d'achat basées sur des indicateurs techniques ici
                self.position_value = self.initial_investment
                self.in_position = True
                df.at[i, 'Buy'] = True

            if self.in_position:
                current_value = self.position_value * (1 + (df.at[i, 'Close'] - df.at[i - 1, 'Close']) / df.at[i - 1, 'Close'])

                if current_value >= self.position_value * (1 + sell_threshold):
                    sell_amount = self.position_value * sell_threshold
                    self.position_value -= sell_amount
                    df.at[i, 'Sell'] = True

                if current_value <= self.position_value * (1 - stop_loss_threshold):
                    self.position_value = 0
                    self.in_position = False
                    df.at[i, 'Sell'] = True

        return df

    def buy_condition(self, df, index):
        # Exemple de condition d'achat simple : acheter lorsque le prix de clôture est supérieur à la moyenne mobile à 20 jours
        # Remplacez cette condition par les conditions d'achat de votre choix en fonction des indicateurs techniques
        previous_index = df.index[df.index.get_loc(index) - 1]
        return df.at[index, 'Close'] > df.at[previous_index, 'Close']


    def run(self):
        while not self.exit_flag.is_set():
            self.logger.info('starting ...')

            self.logger.info('fetching historical data ...')
            data = self.exchange_client.get_historical_data(self.symbol, self.interval, self.days_of_historical_data)

            self.logger.info('making df ...')
            df = make_df(data)
            signals = self.apply_incremental_profit_strategy(df)
            self.logger.info('plotting ...')
            plot_close_price_with_signals(df, signals)
            self.stop()