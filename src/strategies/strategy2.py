from threading import Thread
from datetime import datetime
from src.strategies import BaseStrategyThread
from src.utils import plot_close_price_with_signals, add_indicators, nb_days_YTD
import time
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PlaceOcoWhenItsTime(BaseStrategyThread):
    def __init__(self, name, exchange_client):
        super().__init__(name, exchange_client)

        self.exchange_client = exchange_client
        self.token = "BTC"
        self.base_token = "EUR"
        self.symbol = self.token + self.base_token


        self.long_interval = "1d"
        self.days_of_long_interval = nb_days_YTD() #nb_days_YTD() too long ! 

        self.short_interval = "15m"
        self.days_of_short_interval = 4

        self.initial_investment = 1000

        self.take_profit_threshold=0.005
        self.stop_loss_threshold=0.015

        ## 1. Long-term trend condition
        ## Récupérer le graph '1D'
        ## assurer EMA_short > EMA_long sur le 1D
        self.long_term_uptrend = self.is_long_term_uptrend()
        logger.info(f"{self.days_of_long_interval} days long_term_uptrend: {self.long_term_uptrend}")


        
    def is_long_term_uptrend(self):
        now = datetime.now()
        simulated_time = now.replace(hour=12, minute=0, second=0, microsecond=0)
        current_time_ms = int(simulated_time.timestamp() * 1000)
        start_time_ms = current_time_ms - (self.days_of_long_interval * 24 * 60 * 60 * 1000)

        df = self.exchange_client.get_historical_data(self.symbol, self.long_interval, start_time_ms)
        logger.info(f'long term df is {len(df)} rows')
        df = add_indicators(df)

        short_ema_col = df.columns.get_loc('Short_EMA')
        long_ema_col = df.columns.get_loc('Long_EMA')

        # Condition 1: Short EMA is above Long EMA
        short_above_long = df.iat[len(df) - 1, short_ema_col] > df.iat[len(df) - 1, long_ema_col]

        return short_above_long
    
    def apply_strategy_to_df(self, df):
        
        df = add_indicators(df)
        
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
        rsi_col = df.columns.get_loc('RSI')
        short_ema_col = df.columns.get_loc('Short_EMA')
        long_ema_col = df.columns.get_loc('Long_EMA')

        # Condition 1: Short EMA is above Long EMA
        short_above_long = df.iat[index, short_ema_col] > df.iat[index, long_ema_col]

        # Condition 2: RSI is below 30 (oversold condition)
        rsi_oversold = df.iat[index, rsi_col] < 30

        # Buy if both conditions are met
        return self.long_term_uptrend and short_above_long #and rsi_oversold

    def run(self):
        while not self.exit_flag.is_set():
            current_time_ms = int(time.time() * 1000)
            start_time_ms = current_time_ms - (self.days_of_short_interval * 24 * 60 * 60 * 1000)

            self.logger.info('starting ...')

            self.logger.info('fetching historical data ...')
            df = self.exchange_client.get_historical_data(self.symbol, self.short_interval, start_time_ms)
            logger.info(f'short term df is {len(df)} rows')
            signals = self.apply_strategy_to_df(df)
            self.logger.info('plotting ...')
            plot_close_price_with_signals(df, signals)
            self.stop()