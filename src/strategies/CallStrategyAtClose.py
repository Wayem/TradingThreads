from datetime import datetime, timedelta

import pandas as pd
import pytz as pytz
import schedule
import time

from src.Constants import LOCAL_TZ, PRINTED_DATE_FORMAT
from src.api import BinanceAPIClient
from src.strategies import BaseStrategyThread
from src.utils import add_indicators, add_indicators_signals, \
    short_term_df_with_other_time_frames_signals, SIGNAL_PREFIX, interval_to_minutes, nb_days_YTD

KNOWN_MODES = ["backtest", "live"]


class CallStrategyAtClose(BaseStrategyThread):
    def __init__(self, name: str,
                 exchange_client: BinanceAPIClient,
                 symbol: str,
                 token: str,
                 base_symbol: str,
                 initial_investment_in_base_symbol_quantity,
                 long_interval="1d",
                 medium_interval="1h",
                 short_interval="15m",
                 tp_threshold=0.007,
                 sl_ratio_to_tp_threshold=1.5,
                 mode="backtest",
                 rsi_oversold=50,
                 consecutive_hist_before_momentum=3):
        super().__init__(name=name, exchange_client=exchange_client, mode=mode)
        assert mode in KNOWN_MODES, f'strategy mode must be one of {KNOWN_MODES}'
        assert (token + base_symbol) == symbol, "wtf are you doing ?"

        self.symbol = symbol  # 'BTCEUR'
        self.token = token
        self.base_symbol = base_symbol

        self.initial_investment_in_base_symbol_quantity = initial_investment_in_base_symbol_quantity
        self.take_profit_threshold = tp_threshold
        self.stop_loss_threshold = sl_ratio_to_tp_threshold * self.take_profit_threshold
        self.in_position = False
        self.last_buy_price = None
        self.order_ids = self._load_order_ids_from_cache()

        ## <multi frame> ##
        self.long_interval = long_interval
        self.live_long_interval_nb_days_lookup = nb_days_YTD()

        self.medium_interval = medium_interval
        self.live_medium_interval_nb_days_lookup = 2

        self.short_interval = short_interval
        self.live_short_interval_nb_days_lookup = 2
        ## <multi frame> ##

        ## Tuning Params
        self.rsi_oversold = rsi_oversold
        self.consecutive_hist_before_momentum = consecutive_hist_before_momentum
        ##

    def is_in_position(self):
        open_orders = self.exchange_client.get_open_orders(self.token, self.base_symbol, self.strategy_name)

        for order in open_orders:
            if order.get("clientOrderId", "") in self.order_ids:
                return True

        return False

    def _save_order_id_to_cache(self, order_id):
        cache_file = f"{self.strategy_name}_order_ids_cache.txt"
        with open(cache_file, 'a+') as file:
            file.write(order_id + '\n')

    def _load_order_ids_from_cache(self):
        cache_file = f"{self.strategy_name}_order_ids_cache.txt"
        try:
            with open(cache_file, 'r') as file:
                return [line.strip() for line in file.readlines()]
        except FileNotFoundError:
            return []

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
                self.buy()

    def get_next_scheduled_executions(self):
        # Iterate over the scheduled jobs and find their next run times
        next_executions = []
        for job in schedule.get_jobs():
            next_run_time = job.next_run.strftime(PRINTED_DATE_FORMAT)
            next_executions.append((job, next_run_time))

        return next_executions

    def schedule_trading_strategy(self):
        assert self.short_interval[-1] == 'm', "short interval must be minute"
        minutes = interval_to_minutes(self.short_interval)
        # Find the next launch time
        current_time = datetime.now()

        next_launch_time = current_time
        minutes_to_next = minutes - (current_time.minute % minutes)
        if minutes_to_next < minutes:
            next_launch_time += timedelta(minutes=minutes_to_next - 1)
        next_launch_time = next_launch_time.replace(second=30)  # Adjust to be 30 seconds before

        wait_sec = (next_launch_time - current_time).seconds

        self.logger.info(f'sleeping {wait_sec} sec. Next launch time: {next_launch_time.strftime(PRINTED_DATE_FORMAT)}')
        time.sleep(wait_sec)

        schedule.every(minutes).minutes.do(self.run_live)
        self.run_live()

        while True:
            schedule.run_pending()
            time.sleep(1)

    def buy(self):
        side = 'BUY'
        quantity_in_base = self.initial_investment_in_base_symbol_quantity

        # Get the current token price in the base symbol
        prices = self.exchange_client._get_all_tickers()
        token_price_base = None
        for price in prices:
            if price['symbol'] == self.token + self.base_symbol:
                token_price_base = float(price['price'])
                break

        quantity = quantity_in_base / token_price_base

        # Define the prices for the OCO order (you can adjust these values based on your strategy)
        stop_loss_price = token_price_base * (1 - self.stop_loss_threshold * 0.984)
        stop_limit_price = stop_loss_price * (1 - self.stop_loss_threshold)
        take_profit_price = token_price_base * (1 + self.take_profit_threshold)
        order_id = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')
        self.order_ids.append(order_id)
        self.save_order_id_to_cache(order_id)

        self.exchange_client.place_oco_order(side=side,
                                             token=self.token,
                                             base_symbol=self.base_symbol,
                                             quantity=quantity,
                                             stop_loss_price=stop_loss_price,
                                             stop_limit_price=stop_limit_price,
                                             take_profit_price=take_profit_price,
                                             custom_order_id=order_id)


    def run(self):
        if self.mode == "backtest":
            return self.backtest()
        elif self.mode == "live":
            self.logger.info(f'{self.name} going: '
                             f'OCO,'
                             f'{self.symbol},'
                             f'{self.initial_investment_in_base_symbol_quantity}{self.base_symbol},'
                             f'tp {self.take_profit_threshold},'
                             f'sl {self.stop_loss_threshold},')
            if self.is_in_position():
                self.logger.info(f"{self.name} already in position. doing nothing")
            else:
                self.schedule_trading_strategy()