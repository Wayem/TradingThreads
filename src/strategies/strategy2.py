import pandas as pd
from src.strategies import BaseStrategyThread
from src.utils import plot_close_price_with_signals, add_indicators, nb_days_YTD, get_indicators_signals
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

KNOWN_MODES = ["backtest", "live"]


class PlaceOcoWhenItsTime(BaseStrategyThread):
    def __init__(self, name: str, symbol: str, mode="backtest"):
        super().__init__(name, mode)
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

    def get_df(self):
        if self.mode == "backtest":
            df_short = add_indicators(pd.read_csv(f'{self.symbol}_{self.short_interval}.csv'))
            df_medium = add_indicators(pd.read_csv(f'{self.symbol}_{self.medium_interval}.csv'))
            df_long = add_indicators(pd.read_csv(f'{self.symbol}_{self.long_interval}.csv'))

        elif self.mode == "live":
            raise NotImplemented
            df_short = None  # TODO
            df_medium = None  # TODO
            df_long = None  # TODO

        assert df_short.shape[1] == df_medium.shape[1] == df_long.shape[1]

        short_df_with_signals = get_indicators_signals(df_short, prefix=self.short_interval)
        medium_df_with_signals = get_indicators_signals(df_medium, prefix=self.medium_interval)
        long_df_with_signals = get_indicators_signals(df_long, prefix=self.long_interval)

        aggregated_df = short_term_df_with_other_time_frames_signals(short_df_with_signals, medium_df_with_signals,
                                                                     long_df_with_signals)

        return aggregated_df

    def apply_strategy(self, df: pd.DataFrame):
        df['Buy'] = False
        df['Stop loss'] = False
        df['Take profit'] = False

        for idx, row in df.iterrows():
            # Buy
            if not (self.in_position) and self.buy_condition(df, row):
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

            df.loc[idx] = row

        return df

    def buy_condition(self, row):
        long_term_cond = row[f'{self.long_interval}_ema_short_above_long']
        medium_term_cond = True
        short_term_cond = True

        return long_term_cond & medium_term_cond & short_term_cond

    def run_live(self):
        self.logger.info('starting live trading')
        while not self.exit_flag.is_set():
            logger.info('getting fresh data ...')
            # assert data is fresh

            logger.info('computing signals')

            signals = self.apply_strategy_to_df(df)
            self.logger.info('plotting ...')
            plot_close_price_with_signals(df, signals)
            self.stop()

    def run(self):

        if self.mode == "backtest":
            self.backtest()
        elif self.mode == "live":
            self.run_live()
