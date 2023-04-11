from typing import List
from src.strategies import BaseStrategyThread
from src.strategies.CallStrategyAtClose import CallStrategyAtClose
import matplotlib.pyplot as plt

from src.utils import plot_close_price_with_signals


class Backtester():
    def __init__(self, strategies: List[BaseStrategyThread], plot = True):
        self.client = None  # shouldnt have to use this for backstest. Local data only
        self.strategies_list: List[BaseStrategyThread] = strategies
        self.plot = plot

        self.dct_of_df_with_buy_sl_tp_columns = {s.name: None for s in self.strategies_list}

    def run(self):

        # Fill self.dct_of_df_with_buy_sl_tp_columns
        for strategy_name, strategy in zip([s.name for s in self.strategies_list], self.strategies_list):
            df_with_buy_sl_tp_columns = strategy.run()
            self.dct_of_df_with_buy_sl_tp_columns.update({strategy.name: df_with_buy_sl_tp_columns})
            self.add_performance_column(strategy_name)
            if self.plot:
                plot_close_price_with_signals(df_with_buy_sl_tp_columns)
                self.plot_performance(strategy_name)

        # Read perfs columns freshly added
        last_perfs_values = self.latest_perf_values()
        return last_perfs_values  # {"s2": "0.78", "s1": "1.12"}

    def _strategies_attributes(self, strategy_name: str):
        s = [s for s in self.strategies_list if s.name == strategy_name][0]
        return s.initial_investment_in_base_symbol_quantity, \
            s.stop_loss_threshold, \
            s.take_profit_threshold

    def add_performance_column(self, strategy_name):
        df = self.dct_of_df_with_buy_sl_tp_columns[strategy_name]
        initial_investment, stop_loss, take_profit = self._strategies_attributes(strategy_name)

        portfolio_value = initial_investment
        in_market = False

        performances_list = []

        for index, row in df.iterrows():
            if row['Buy'] and not in_market:
                in_market = True
                entry_price = row['Close']
            elif row['Stop loss'] and in_market:
                in_market = False
                exit_price = row['Close']
                portfolio_value *= (1 - stop_loss)
            elif row['Take profit'] and in_market:
                in_market = False
                exit_price = row['Close']
                portfolio_value *= (1 + take_profit)

            if in_market:
                current_value = (portfolio_value * row['Close']) / entry_price
            else:
                current_value = portfolio_value

            performances_list.append(current_value)

        df['Performance'] = [p / initial_investment for p in performances_list]
        return df  # With perf col added

    def plot_performance(self, strategy_name):
        df = self.dct_of_df_with_buy_sl_tp_columns[strategy_name]
        plt.figure(figsize=(12, 6))
        plt.plot(df['Close time'], df['Performance'])
        plt.xlabel('Time')
        plt.ylabel('Portfolio Value (€)')
        plt.title('Portfolio Performance Over Time')
        plt.show()

    def latest_perf_values(self):
        ret = {strategy_name: None for strategy_name in self.dct_of_df_with_buy_sl_tp_columns.keys()}

        for strategy_name, df in self.dct_of_df_with_buy_sl_tp_columns.items():
            df_with_perf = self.add_performance_column(strategy_name)
            last_perf_value = df_with_perf['Performance'].iloc[-1]
            ret.update({strategy_name: last_perf_value})

        return ret  # {"s2": "0.78", "s1": "1.12"}

def main():
    client = None

    s2 = CallStrategyAtClose(name="oco_scalp",
                             initial_investment_in_base_symbol_quantity= 100,
                             long_interval='1d',
                             medium_interval='1h',
                             short_interval='5m',
                             tp_threshold=0.0055,
                             sl_ratio_to_tp_threshold=3,
                             rsi_oversold=50,
                             consecutive_hist_before_momentum=2,
                             exchange_client= client,
                             token = "BNB",
                             base_symbol = "EUR",
                             symbol= "BNBEUR",
                             mode='backtest')

    backtester = Backtester([s2])

    latest_perf_values = backtester.run()  # {"s2": "0.78", "s1": "1.12"}
    print(f'last_perfs_values : {latest_perf_values}')

if __name__ == "__main__":
    main()

