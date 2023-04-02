import sys

import pandas as pd

from src.api import BinanceAPIClient
from src.strategies import BaseStrategyThread
from src.utils import plot_close_price_with_signals, add_indicators, nb_days_YTD, add_indicators_signals, \
    short_term_df_with_other_time_frames_signals, SIGNAL_PREFIX

KNOWN_MODES = ["backtest", "live"]


class PlaceOcoWhenItsTime(BaseStrategyThread):
    def __init__(self, name: str, exchange_client: BinanceAPIClient, symbol: str, mode="backtest"):
        super().__init__(name=name, exchange_client=exchange_client, mode=mode)
        assert mode in KNOWN_MODES, f'strategy mode must be one of {KNOWN_MODES}'
        self.symbol = symbol  # 'BTCEUR'

        self.take_profit_threshold = 0.01
        self.stop_loss_threshold = 1.5 * self.take_profit_threshold
        self.in_position = False
        self.last_buy_price = None

        ## <multi frame> ##
        self.long_interval = "1d"
        self.live_long_interval_nb_days_lookup = nb_days_YTD()

        self.medium_interval = "1h"
        self.live_medium_interval_nb_days_lookup = 5

        self.short_interval = "15m"
        self.live_short_interval_nb_days_lookup = 3
        ## <multi frame> ##

    def get_short_df_with_higher_tf_signals(self):
        if self.mode == "backtest":
            self.logger.info("using cached csv")
            df_short = add_indicators(pd.read_csv(f'{self.symbol}_{self.short_interval}.csv'), self.short_interval)
            df_medium = add_indicators(pd.read_csv(f'{self.symbol}_{self.medium_interval}.csv'), self.medium_interval)
            df_long = add_indicators(pd.read_csv(f'{self.symbol}_{self.long_interval}.csv'), self.long_interval)

        elif self.mode == "live":
            raise NotImplemented
            df_short = None  # TODO
            df_medium = None  # TODO
            df_long = None  # TODO

        assert df_short.shape[1] == df_medium.shape[1] == df_long.shape[1]

        short_df_with_signals = add_indicators_signals(df_short, prefix=self.short_interval)
        medium_df_with_signals = add_indicators_signals(df_medium, prefix=self.medium_interval)
        long_df_with_signals = add_indicators_signals(df_long, prefix=self.long_interval)

        aggregated_df = short_term_df_with_other_time_frames_signals(short_df_with_signals, medium_df_with_signals,
                                                                     long_df_with_signals)

        signals_columns = [col for col in aggregated_df.columns if SIGNAL_PREFIX in col]
        aggregated_df.loc[:, signals_columns] = aggregated_df.loc[:, signals_columns].fillna(False)
        return aggregated_df

    def apply_strategy(self, df_with_indicators: pd.DataFrame):
        df_with_indicators['Buy'] = False
        df_with_indicators['Stop loss'] = False
        df_with_indicators['Take profit'] = False

        for idx, row in df_with_indicators.iterrows():
            # Buy
            if not (self.in_position) and self.buy_condition(row):
                row['Buy'] = True
                self.in_position = True
                self.last_buy_price = row['Close']

            elif self.in_position:
                # Stop loss
                if row['Low'] <= self.last_buy_price * (1 - self.stop_loss_threshold):
                    row['Stop loss'] = True
                    self.in_position = False

                # Take profit
                elif row['High'] >= self.last_buy_price * (1 + self.take_profit_threshold):
                    row['Take profit'] = True
                    self.in_position = False

            df_with_indicators.loc[idx] = row

        return df_with_indicators

    def buy_condition(self, row):
        long_term_cond = row[f'{self.long_interval}_ema_short_above_long_{SIGNAL_PREFIX}']
        medium_term_cond = True
        short_term_cond = True

        return long_term_cond & medium_term_cond & short_term_cond

    def backtest(self) -> pd.DataFrame: # df_with_buy_sl_tp_columns
        self.logger.info(f"backtesting {self.name} on local data")
        short_df_with_higher_tf_signals = self.get_short_df_with_higher_tf_signals()
        df_with_buy_sl_tp_columns = self.apply_strategy(short_df_with_higher_tf_signals)
        return df_with_buy_sl_tp_columns
        # df_with_buy_sl_tp_columns.to_csv('df_with_buy_sl_tp_columns.csv')

        # plot_close_price_with_signals(df_with_buy_sl_tp_columns)
        # self.stop()

    def run_live(self):
        self.logger.info('starting live trading')
        # while not self.exit_flag.is_set():
        #     self.logger.info('getting fresh data, aggregate time frames & compute indicators columns')
        #     df_aggregated = self.get_short_df_with_higher_tf_signals()
        #
        #     signals = self.apply_strategy_to_df(df)
        #     self.logger.info('plotting ...')
        #     plot_close_price_with_signals(df, signals)
        #     self.stop()

    def run(self):
        if self.mode == "backtest":
            return self.backtest()
        elif self.mode == "live":
            self.run_live()
