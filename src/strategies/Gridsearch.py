from tqdm import tqdm
import pickle

from src.strategies.Backtester import Backtester
from src.strategies.CallStrategyAtClose import CallStrategyAtClose


def gridsearch(exchange_client, symbols, long_intervals, medium_intervals, short_intervals, tp_thresholds,
               sl_ratio_to_tp_thresholds, rsi_oversolds, consecutive_hists):
    results = []

    total_iterations = (len(long_intervals) * len(medium_intervals) * len(short_intervals) *
                        len(tp_thresholds) * len(sl_ratio_to_tp_thresholds) * len(rsi_oversolds) * len(
                consecutive_hists) * len(symbols))

    with tqdm(total=total_iterations, desc="Grid Search Progress") as pbar:
        for long_interval in long_intervals:
            for medium_interval in medium_intervals:
                for short_interval in short_intervals:
                    for tp_threshold in tp_thresholds:
                        for sl_ratio_to_tp_threshold in sl_ratio_to_tp_thresholds:
                            for rsi_oversold in rsi_oversolds:
                                for consecutive_hist in consecutive_hists:
                                    for symbol_tuple in symbols:
                                        strategy = CallStrategyAtClose(
                                            name="s",
                                            initial_investment_in_base_symbol_quantity=100,
                                            exchange_client=exchange_client,
                                            symbol=symbol_tuple[0] + symbol_tuple[1],
                                            token=symbol_tuple[0],
                                            base_symbol=symbol_tuple[1],
                                            long_interval=long_interval,
                                            medium_interval=medium_interval,
                                            short_interval=short_interval,
                                            tp_threshold=tp_threshold,
                                            sl_ratio_to_tp_threshold=sl_ratio_to_tp_threshold,
                                            mode="backtest",
                                            rsi_oversold=rsi_oversold,
                                            consecutive_hist_before_momentum=consecutive_hist,
                                        )
                                        backtester = Backtester([strategy], plot=False)
                                        latest_perf_values = backtester.run()
                                        score = latest_perf_values["s"]

                                        params = {
                                            'symbol': symbol_tuple[0] + symbol_tuple[1],
                                            'long_interval': long_interval,
                                            'medium_interval': medium_interval,
                                            'short_interval': short_interval,
                                            'tp_threshold': tp_threshold,
                                            'sl_ratio_to_tp_threshold': sl_ratio_to_tp_threshold,
                                            'rsi_oversold': rsi_oversold,
                                            'consecutive_hist_before_momentum': consecutive_hist,
                                        }

                                        results.append({'score': score, 'params': params})
                                        pbar.update(1)

    return results


def print_cached_results():
    with open('sorted_results.pkl', 'rb') as f:
        sorted_results = pickle.load(f)
    print(sorted_results[0:20])


if __name__ == "__main__":
    btc = "BTC"
    ada = "ADA"
    bnb = "BNB"
    eur = "EUR"
    BTCEUR = btc + eur
    BNBEUR = bnb + eur
    ADAEUR = ada + eur
    client = None

    results = gridsearch(
        exchange_client=client,
        symbols=[(bnb, eur)],
        long_intervals=["1d", "4h"],
        medium_intervals=["1h"],
        short_intervals=["15m", "30m", "5m"],
        tp_thresholds=[0.0055, 0.0105, 0.02, 0.05],
        sl_ratio_to_tp_thresholds=[1.5, 2,3],
        rsi_oversolds=[20, 30, 40,50],
        consecutive_hists=[2, 3, 5, 8],
    )

    sorted_results = sorted(results, key=lambda x: x['score'], reverse=True)
    print(sorted_results)
    with open('sorted_results.pkl', 'wb') as f:
        pickle.dump(sorted_results, f)
