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

class Strategy1(BaseStrategyThread):
    def __init__(self, name, exchange_client):
        super().__init__(name, exchange_client)

        self.exchange_client = exchange_client
        self.symbol = "BTCUSDT"
        self.interval = "15m"
        self.days_of_historical_data = 2


    def heikin_ashi_smoothed_buy_sell_signals(self, df, ema_length=16):
        src = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4

        ha_open = (src + src.shift(1)) / 2
        ha_c = (src + ha_open + df['High'].combine(ha_open, max) + df['Low'].combine(ha_open, min)) / 4

        ema1 = ha_c.ewm(span=ema_length).mean()
        ema2 = ema1.ewm(span=ema_length).mean()
        ema3 = ema2.ewm(span=ema_length).mean()
        tma1 = 3 * ema1 - 3 * ema2 + ema3

        ema4 = tma1.ewm(span=ema_length).mean()
        ema5 = ema4.ewm(span=ema_length).mean()
        ema6 = ema5.ewm(span=ema_length).mean()
        tma2 = 3 * ema4 - 3 * ema5 + ema6

        ipek = tma1 - tma2
        yasin = tma1 + ipek

        hlc3 = (df['High'] + df['Low'] + df['Close']) / 3

        ema7 = hlc3.ewm(span=ema_length).mean()
        ema8 = ema7.ewm(span=ema_length).mean()
        ema9 = ema8.ewm(span=ema_length).mean()
        tma3 = 3 * ema7 - 3 * ema8 + ema9

        ema10 = tma3.ewm(span=ema_length).mean()
        ema11 = ema10.ewm(span=ema_length).mean()
        ema12 = ema11.ewm(span=ema_length).mean()
        tma4 = 3 * ema10 - 3 * ema11 + ema12

        ipek1 = tma3 - tma4
        yasin1 = tma3 + ipek1

        mavi = yasin1
        kirmizi = yasin

        long_cond = (mavi > kirmizi) & (mavi.shift(1) <= kirmizi.shift(1))
        short_cond = (mavi < kirmizi) & (mavi.shift(1) >= kirmizi.shift(1))

        signals_df = pd.DataFrame(index=df.index)
        signals_df['Buy'] = long_cond
        signals_df['Sell'] = short_cond

        return signals_df
    
    def run(self):
        while not self.exit_flag.is_set():
            self.logger.info('starting ...')

            self.logger.info('fetching historical data ...')
            data = self.exchange_client.get_historical_data(self.symbol, self.interval, self.days_of_historical_data)

            self.logger.info('making df ...')
            df = make_df(data)
            signals = self.heikin_ashi_smoothed_buy_sell_signals(df)
            self.logger.info('plotting ...')
            plot_close_price_with_signals(df, signals)
            self.stop()