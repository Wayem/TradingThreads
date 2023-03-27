import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import talib

def nb_days_YTD():
    # Get the current date
    today = datetime.now()

    # Calculate the start of the year
    start_of_year = datetime(today.year, 1, 1)

    # Calculate the number of days since the start of the year
    days_since_start_of_year = (today - start_of_year).days
    return days_since_start_of_year

COLUMNS = ['Open time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close time', 'Quote asset volume', 'Number of trades', 'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore']
def make_df(raw_historical_data):
    # Create a pandas DataFrame from the historical data
    df = pd.DataFrame(raw_historical_data, columns=COLUMNS)
    
    # Convert the timestamp to a readable datetime format
    df['Open time'] = pd.to_datetime(df['Open time'], unit='ms')
    df['Close time'] = pd.to_datetime(df['Close time'], unit='ms')
    
    # Set the index to the 'Close time' column
    df.set_index('Close time', inplace=True)
    
    # Convert the 'Close' price column to a numeric type
    df['Open'] = pd.to_numeric(df['Open'])
    df['High'] = pd.to_numeric(df['High'])
    df['Low'] = pd.to_numeric(df['Low'])
    df['Close'] = pd.to_numeric(df['Close'])
    return df

def plot_close_price_with_signals(historical_df, signals_df):
    fig, ax = plt.subplots(figsize=(14, 8))

    # Plot Close prices
    ax.plot(historical_df.index, historical_df['Close'], label='Close Price')
    ax.set_ylabel('Price')
    ax.legend(loc='best')

    # Plot Buy signals
    ax.scatter(signals_df[signals_df['Buy']].index, historical_df.loc[signals_df['Buy']].Close, label='Buy', marker='^', color='black')

    # Plot SL signals
    ax.scatter(signals_df[signals_df['Stop loss']].index, historical_df.loc[signals_df['Stop loss']].Close, label='Stop loss', marker='v', color='r')

    # Plot TP signals
    ax.scatter(signals_df[signals_df['Take profit']].index, historical_df.loc[signals_df['Take profit']].Close, label='Take profit', marker='v', color='g')


    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=4))

    plt.xlabel('Date')
    plt.legend(loc='best')
    plt.show()

def add_indicators(df):

    df['RSI'] = talib.RSI(df['Close'].astype('float64'), timeperiod=14)
    df['Short_EMA'] = talib.EMA(df['Close'].astype('float64'), timeperiod=12)
    df['Long_EMA'] = talib.EMA(df['Close'].astype('float64'), timeperiod=26)

    return df