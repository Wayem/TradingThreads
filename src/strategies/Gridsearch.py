from tqdm import tqdm
import pickle

from src.strategies.Backtester import Backtester
from src.strategies.PlaceOcoWhenItsTime import PlaceOcoWhenItsTime


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
                                    for symbol in symbols:
                                        strategy = PlaceOcoWhenItsTime(
                                            name="s",
                                            exchange_client=exchange_client,
                                            symbol=symbol,
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
                                            'symbol': symbol,
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
        symbols=[BNBEUR],
        long_intervals=["1d"],
        medium_intervals=["1h", "4h"],
        short_intervals=["15m", "30m", "5m"],
        tp_thresholds=[0.0105, 0.02, 0.05],
        sl_ratio_to_tp_thresholds=[1.5, 3],
        rsi_oversolds=[20, 30, 50],
        consecutive_hists=[2, 3, 5, 8],
    )

    sorted_results = sorted(results, key=lambda x: x['score'], reverse=True)
    print(sorted_results)
    with open('sorted_results.pkl', 'wb') as f:
        pickle.dump(sorted_results, f)