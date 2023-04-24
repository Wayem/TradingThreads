from typing import Dict
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import talib
import pandas as pd

SIGNAL_PREFIX = "SIGNAL"


def timer(fn):
    from time import perf_counter

    def inner(*args, **kwargs):
        start_time = perf_counter()
        to_execute = fn(*args, **kwargs)
        end_time = perf_counter()
        execution_time = end_time - start_time
        print('{0} took {1:.8f}s to execute'.format(fn.__name__, execution_time))
        return to_execute

    return inner


def nb_days_YTD():
    # Get the current date
    today = datetime.now()

    # Calculate the start of the year
    start_of_year = datetime(today.year, 1, 1)

    # Calculate the number of days since the start of the year
    days_since_start_of_year = (today - start_of_year).days
    return days_since_start_of_year


COLUMNS = ['Open time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close time', 'Quote asset volume',
           'Number of trades', 'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore']


def make_df(raw_historical_data):
    # Create a pandas DataFrame from the historical data
    df = pd.DataFrame(raw_historical_data, columns=COLUMNS)

    # Convert the timestamp to a readable datetime format
    df['Open time'] = pd.to_datetime(df['Open time'], unit='ms')
    df['Close time'] = pd.to_datetime(df['Close time'], unit='ms')

    # Set the index to the 'Close time' column
    df.set_index('Close time', inplace=True, drop=False)

    # Convert the 'Close' price column to a numeric type
    df['Open'] = pd.to_numeric(df['Open'])
    df['High'] = pd.to_numeric(df['High'])
    df['Low'] = pd.to_numeric(df['Low'])
    df['Close'] = pd.to_numeric(df['Close'])

    return df


def plot_close_price_with_signals(df_with_buy_sl_tp_columns):
    fig, ax = plt.subplots(figsize=(14, 8))

    # Plot Close prices
    ax.plot(df_with_buy_sl_tp_columns.index, df_with_buy_sl_tp_columns['Close'], label='Close Price')
    ax.set_ylabel('Price')
    ax.legend(loc='best')

    # Plot Buy signals
    buy_signals = df_with_buy_sl_tp_columns[df_with_buy_sl_tp_columns['Buy'] & ~df_with_buy_sl_tp_columns['In position']]
    ax.scatter(buy_signals.index,
               buy_signals.Close, label='Buy', marker='^', color='black')

    # Plot SL signals
    ax.scatter(df_with_buy_sl_tp_columns[df_with_buy_sl_tp_columns['Stop loss']].index,
               df_with_buy_sl_tp_columns.loc[df_with_buy_sl_tp_columns['Stop loss']].Close,
               label='Stop loss', marker='v', color='r')

    # Plot TP signals
    ax.scatter(df_with_buy_sl_tp_columns[df_with_buy_sl_tp_columns['Take profit']].index,
               df_with_buy_sl_tp_columns.loc[df_with_buy_sl_tp_columns['Take profit']].Close,
               label='Take profit', marker='v', color='g')

    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=4))

    plt.xlabel('Date')
    plt.legend(loc='best')
    plt.show()


def interval_to_milliseconds(interval: str) -> int:
    """Convert a string interval to the number of milliseconds"""
    ms = None
    if interval.endswith("m"):
        ms = int(interval[:-1]) * 60 * 1000
    elif interval.endswith("h"):
        ms = int(interval[:-1]) * 60 * 60 * 1000
    elif interval.endswith("d"):
        ms = int(interval[:-1]) * 24 * 60 * 60 * 1000
    elif interval.endswith("w"):
        ms = int(interval[:-1]) * 7 * 24 * 60 * 60 * 1000
    elif interval.endswith("M"):
        ms = int(interval[:-1]) * 30 * 24 * 60 * 60 * 1000
    else:
        raise Exception("Invalid interval")

    return ms

def interval_to_minutes(interval: str) -> int:
    """Convert a string interval to the number of minutes"""
    minutes = None
    if interval.endswith("m"):
        minutes = int(interval[:-1])
    elif interval.endswith("h"):
        minutes = int(interval[:-1]) * 60
    elif interval.endswith("d"):
        minutes = int(interval[:-1]) * 24 * 60
    elif interval.endswith("w"):
        minutes = int(interval[:-1]) * 7 * 24 * 60
    elif interval.endswith("M"):
        minutes = int(interval[:-1]) * 30 * 24 * 60
    else:
        raise Exception("Invalid interval")

    return minutes


## <Signals & indicators> ##
def _add_macd_momentum(df, prefix, consecutive_rows):
    # Define the conditions for 'MACD_UP_Momentum' and 'MACD_DOWN_Momentum'
    macd_hist_prev = df[f'{prefix}_MACD_Hist'].shift(1)
    macd_up_count = 0
    macd_down_count = 0
    macd_up = np.zeros(len(df), dtype=bool)
    macd_down = np.zeros(len(df), dtype=bool)

    for i in range(1, len(df)):
        if df[f'{prefix}_MACD_Hist'].iloc[i] > macd_hist_prev.iloc[i]:
            macd_up_count += 1
            macd_down_count = 0
        elif df[f'{prefix}_MACD_Hist'].iloc[i] < macd_hist_prev.iloc[i]:
            macd_down_count += 1
            macd_up_count = 0
        else:
            macd_up_count = 0
            macd_down_count = 0

        if macd_up_count >= consecutive_rows:
            macd_up[i] = True
        if macd_down_count >= consecutive_rows:
            macd_down[i] = True

    # Add the columns to the dataframe
    df[f'{prefix}_MACD_UP_Momentum'] = macd_up
    df[f'{prefix}_MACD_DOWN_Momentum'] = macd_down

    return df


def add_indicators(df, prefix, consecutive_hist_before_momentum):
    df[f'{prefix}_RSI'] = talib.RSI(df['Close'].astype('float64'), timeperiod=14)

    df[f'{prefix}_Short_EMA'] = talib.EMA(df['Close'].astype('float64'), timeperiod=12)
    df[f'{prefix}_Long_EMA'] = talib.EMA(df['Close'].astype('float64'), timeperiod=26)

    macd, macd_signal, macd_hist = talib.MACD(df['Close'].astype('float64'), fastperiod=12, slowperiod=26,
                                              signalperiod=9)
    df[f'{prefix}_MACD_Hist'] = macd_hist
    df = _add_macd_momentum(df, prefix, consecutive_hist_before_momentum)
    return df


def get_indicators_signals(row: pd.Series, prefix, rsi_oversold, rsi_overbought) -> Dict[str, bool]:
    short_above_long = row[f'{prefix}_Short_EMA'] > row[f'{prefix}_Long_EMA']
    oversold = row[f'{prefix}_RSI'] < rsi_oversold
    overbought = row[f'{prefix}_RSI'] > rsi_overbought
    momentum_up = row[f'{prefix}_MACD_UP_Momentum']
    momentum_down = row[f'{prefix}_MACD_DOWN_Momentum']

    ret = {'ema_short_above_long': short_above_long,
           'oversold': oversold,
           'overbought': overbought,
           'momentum_up': momentum_up,
           'momentum_down': momentum_down}
    return {f'{prefix}_{key}_{SIGNAL_PREFIX}': value for key, value in ret.items()}


def add_indicators_signals(df: pd.DataFrame, prefix, rsi_oversold, rsi_overbought) -> pd.DataFrame:
    signals = df.apply(lambda x: get_indicators_signals(x,
                                                        prefix=prefix,
                                                        rsi_oversold=rsi_oversold,
                                                        rsi_overbought=rsi_overbought),
                       axis=1)

    signals_df = pd.DataFrame.from_records(signals.values, index=signals.index)
    result_df = pd.concat([df, signals_df], axis=1)
    return result_df


def short_term_df_with_other_time_frames_signals(short_df_with_signals, *other_time_frames):
    """
    Returns the short term dataframe with signals columns from the higher time frames dataframes.
    For every Close time (in short term dataframe), the function returns the higher time frame signal value
    that is stored in the Close time (higher df) the closest in date distance in the past.

    :param short_df_with_signals: pandas DataFrame containing the short term data with 'signal' columns.
    :param other_time_frames: variable number of pandas DataFrames for the higher time frames.
    :return: pandas DataFrame containing the short term data with signals from the higher time frames.
    """
    # Convert Close time columns to datetime
    short_df_with_signals['Close time'] = pd.to_datetime(short_df_with_signals['Close time'])
    for df in other_time_frames:
        df['Close time'] = pd.to_datetime(df['Close time'])

    # Merge short term and higher time frame dataframes
    merged_df = short_df_with_signals
    for df in other_time_frames:
        specific_columns = [col for col in df.columns if col not in merged_df.columns]
        merged_df = pd.merge_asof(merged_df.sort_values('Close time'),
                                  df[['Close time'] + specific_columns].sort_values('Close time'),
                                  on='Close time',
                                  direction='backward')

    return merged_df

## </Signals & indicators> ##

def round_to_tick_size(value, tick_size):
    return round(value / tick_size) * tick_size

def round_to_step_size(value, step_size):
    return round(value / step_size) * step_size

def validate_oco_prices(side, stop_price, stop_limit_price, take_profit_price):
    if side == 'BUY':
        if stop_limit_price <= stop_price or take_profit_price <= stop_limit_price:
            raise ValueError("For a BUY order, the stop limit price must be higher than the stop loss price, and the take profit price must be higher than the stop limit price.")
    elif side == 'SELL':
        if stop_limit_price >= stop_price or take_profit_price <= stop_limit_price:
            raise ValueError("For a SELL order, the stop limit price must be lower than the stop loss price, and the take profit price must be higher than the stop limit price.")
