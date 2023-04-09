from datetime import datetime, timedelta

import pandas as pd
import pytz as pytz
import schedule
import time

from src.Constants import LOCAL_TZ
from src.api import BinanceAPIClient
from src.strategies import BaseStrategyThread
from src.utils import add_indicators, add_indicators_signals, \
    short_term_df_with_other_time_frames_signals, SIGNAL_PREFIX, interval_to_minutes

KNOWN_MODES = ["backtest", "live"]

class PlaceOcoWhenItsTime(BaseStrategyThread):
    def __init__(self, name: str,
                 exchange_client: BinanceAPIClient,
                 symbol: str,
                 long_interval="1d",
                 medium_interval="1h",
                 short_interval="15m",
                 tp_threshold=0.01,
                 sl_ratio_to_tp_threshold=1.5,
                 mode="backtest",
                 rsi_oversold=30,
                 consecutive_hist_before_momentum=3):
        super().__init__(name=name, exchange_client=exchange_client, mode=mode)
        assert mode in KNOWN_MODES, f'strategy mode must be one of {KNOWN_MODES}'
        self.symbol = symbol  # 'BTCEUR'

        self.take_profit_threshold = tp_threshold
        self.stop_loss_threshold = sl_ratio_to_tp_threshold * self.take_profit_threshold
        self.in_position = False
        self.last_buy_price = None

        ## <multi frame> ##
        self.long_interval = long_interval
        self.live_long_interval_nb_days_lookup = 1

        self.medium_interval = medium_interval
        self.live_medium_interval_nb_days_lookup = 1

        self.short_interval = short_interval
        self.live_short_interval_nb_days_lookup = 1
        ## <multi frame> ##

        ## Tuning Params
        self.rsi_oversold = rsi_oversold
        self.consecutive_hist_before_momentum = consecutive_hist_before_momentum
        ##

    def update_historical_data_csv(self):
        if self.mode == "live":
            start_long = datetime.now() - timedelta(days=self.live_long_interval_nb_days_lookup)
            start_medium = datetime.now() - timedelta(days=self.live_medium_interval_nb_days_lookup)
            start_short = datetime.now() - timedelta(days=self.live_short_interval_nb_days_lookup)
            self.exchange_client.update_historical_data_csv(self.symbol, self.long_interval,
                                                            start_long)
            self.exchange_client.update_historical_data_csv(self.symbol, self.medium_interval,
                                                            start_medium)
            self.exchange_client.update_historical_data_csv(self.symbol, self.short_interval,
                                                            start_short)
        elif self.mode == "backtest":
            self.logger.info("using cached csv")

    def read_raw_data_frames(self):
        df_short_raw = pd.read_csv(f'{self.symbol}_{self.short_interval}.csv')
        df_medium_raw = pd.read_csv(f'{self.symbol}_{self.medium_interval}.csv')
        df_long_raw = pd.read_csv(f'{self.symbol}_{self.long_interval}.csv')

        # df_short_raw['Open time'] = pd.to_datetime(df_short_raw['Open time'].tz_localize(LOCAL_TZ))
        # df_short_raw['Close time'] = pd.to_datetime(df_short_raw['Close time'].tz_localize(LOCAL_TZ))
        #
        # df_medium_raw['Open time'] = pd.to_datetime(df_medium_raw['Open time'].tz_localize(LOCAL_TZ))
        # df_medium_raw['Close time'] = pd.to_datetime(df_medium_raw['Close time'].tz_localize(LOCAL_TZ))
        #
        # df_long_raw['Open time'] = pd.to_datetime(df_long_raw['Open time'].tz_localize(LOCAL_TZ))
        # df_long_raw['Close time'] = pd.to_datetime(df_long_raw['Close time'].tz_localize(LOCAL_TZ))

        return df_short_raw, df_medium_raw, df_long_raw

    def add_indicators_to_data_frames(self, df_short_raw, df_medium_raw, df_long_raw):
        df_short = add_indicators(df_short_raw,
                                  prefix=self.short_interval,
                                  consecutive_hist_before_momentum=self.consecutive_hist_before_momentum)

        df_medium = add_indicators(df_medium_raw,
                                   prefix=self.medium_interval,
                                   consecutive_hist_before_momentum=self.consecutive_hist_before_momentum)

        df_long = add_indicators(df_long_raw,
                                 prefix=self.long_interval,
                                 consecutive_hist_before_momentum=self.consecutive_hist_before_momentum)

        return df_short, df_medium, df_long

    def add_signals_to_data_frames(self, df_short, df_medium, df_long):
        short_df_with_signals = add_indicators_signals(df_short,
                                                       prefix=self.short_interval,
                                                       rsi_oversold=self.rsi_oversold)

        medium_df_with_signals = add_indicators_signals(df_medium,
                                                        prefix=self.medium_interval,
                                                        rsi_oversold=self.rsi_oversold)

        long_df_with_signals = add_indicators_signals(df_long,
                                                      prefix=self.long_interval,
                                                      rsi_oversold=self.rsi_oversold)

        return short_df_with_signals, medium_df_with_signals, long_df_with_signals

    def get_short_df_with_higher_tf_signals(self):
        assert self.mode in ['backtest', 'live']

        self.update_historical_data_csv()

        df_short_raw, df_medium_raw, df_long_raw = self.read_raw_data_frames()

        df_short, df_medium, df_long = self.add_indicators_to_data_frames(df_short_raw, df_medium_raw, df_long_raw)

        assert df_short.shape[1] == df_medium.shape[1] == df_long.shape[1]

        short_df_with_signals, medium_df_with_signals, long_df_with_signals = self.add_signals_to_data_frames(
            df_short, df_medium, df_long)

        aggregated_df = short_term_df_with_other_time_frames_signals(short_df_with_signals,
                                                                     medium_df_with_signals,
                                                                     long_df_with_signals)

        signals_columns = [col for col in aggregated_df.columns if SIGNAL_PREFIX in col]
        aggregated_df.loc[:, signals_columns] = aggregated_df.loc[:, signals_columns].fillna(False)

        aggregated_df['Open time'] = pd.to_datetime(aggregated_df['Open time'])
        aggregated_df['Close time'] = pd.to_datetime(aggregated_df['Close time'])

        aggregated_df[f'Open time {LOCAL_TZ}'] = aggregated_df['Open time'].dt.tz_localize('UTC').dt.tz_convert(
            LOCAL_TZ)
        aggregated_df[f'Close time {LOCAL_TZ}'] = aggregated_df['Close time'].dt.tz_localize('UTC').dt.tz_convert(
            LOCAL_TZ)
        return aggregated_df

    def apply_strategy(self, df_with_indicators: pd.DataFrame):
        df_with_indicators['Buy'] = False
        df_with_indicators['Stop loss'] = False
        df_with_indicators['Take profit'] = False

        def process_row(row):
            nonlocal self
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

            return row

        df_with_indicators = df_with_indicators.apply(process_row, axis=1)
        return df_with_indicators

    def buy_condition(self, row):
        long_term_cond = row[f'{self.long_interval}_ema_short_above_long_{SIGNAL_PREFIX}']
        medium_term_cond = row[f'{self.medium_interval}_momentum_up_{SIGNAL_PREFIX}']
        short_term_cond = row[f'{self.short_interval}_oversold_{SIGNAL_PREFIX}']

        return long_term_cond & medium_term_cond & short_term_cond

    def backtest(self) -> pd.DataFrame:  # df_with_buy_sl_tp_columns
        self.logger.info(f"backtesting {self.name} on local data")
        short_df_with_higher_tf_signals = self.get_short_df_with_higher_tf_signals()
        df_with_buy_sl_tp_columns = self.apply_strategy(short_df_with_higher_tf_signals)
        return df_with_buy_sl_tp_columns

    def is_current_time_close_to_last_row(self, df, threshold_seconds=30):
        # Get the close time of the last row
        last_row_close_time = df.iloc[-1][f'Close time {LOCAL_TZ}']

        # Get the current time and calculate the time difference between the expected close time and the current time
        current_dt = datetime.now(pytz.UTC).astimezone(pytz.timezone(LOCAL_TZ))
        time_difference = abs(current_dt - last_row_close_time)

        # Check if the time difference is within the threshold
        if time_difference.seconds <= threshold_seconds:
            return True
        else:
            return False

    def run_live(self):
        self.logger.info('starting live trading')
        short_df_with_higher_tf_signals = self.get_short_df_with_higher_tf_signals()
        df_with_buy_sl_tp_columns = self.apply_strategy(short_df_with_higher_tf_signals)

        if self.is_current_time_close_to_last_row(df_with_buy_sl_tp_columns):
            self.logger.info("Data are fresh !")
            if df_with_buy_sl_tp_columns.iloc[-1]['Buy'] == True:
                self.logger.info("Got buy signal. Let's go !")

        # log next jobs
        next_executions = self.get_next_scheduled_executions()
        for job, next_run_time in next_executions:
            self.logger.info(f"Job: {job}, Next run time: {next_run_time}")

    def get_next_scheduled_executions(self):
        # Iterate over the scheduled jobs and find their next run times
        next_executions = []
        for job in schedule.get_jobs():
            next_run_time = job.next_run.strftime("%Y-%m-%d %H:%M:%S")
            next_executions.append((job, next_run_time))

        return next_executions

    def schedule_trading_strategy(self):
        # Find the next launch time
        current_time = datetime.now()

        next_launch_time = current_time
        minutes_to_next = 15 - (current_time.minute % 15)
        print(f'minutes_to_next: {minutes_to_next}')
        if minutes_to_next < 15:
            next_launch_time += timedelta(minutes=minutes_to_next - 1)
        next_launch_time = next_launch_time.replace(second=30) # Adjust to be 30 seconds before the quarter-hour

        wait_sec = (next_launch_time - current_time).seconds

        self.logger.info(f'sleeping {wait_sec} sec. Next launch time: {next_launch_time.strftime("%Y-%m-%d %H:%M:%S")}')
        time.sleep(wait_sec)

        schedule.every(15).minutes.do(self.run_live)
        self.run_live()

        while True:
            schedule.run_pending()
            time.sleep(5)

    def run(self):
        if self.mode == "backtest":
            return self.backtest()
        elif self.mode == "live":
            self.schedule_trading_strategy()
