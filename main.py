import os
import logging
import sys

from src.strategies.CallStrategyAtClose import CallStrategyAtClose
from src.utils.kp_secrets import extract_kp_secrets
from src.api import BinanceAPIClient

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

dir_path = os.path.dirname(os.path.realpath(__file__))
logs_dir = os.path.join(dir_path, 'logs')
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)


class MainStep:
    def __init__(self, name):
        self.name = name

    def run(self, func):
        logger.info(f"running {self.name}")
        return func()


def runstep(name, func):
    return MainStep(name).run(func)


# NOT GENERIC #
##################################################
if __name__ == "__main__":
    kp_secrets = runstep("keepass access", extract_kp_secrets)
    client = BinanceAPIClient(kp_secrets["BNB_API_KEY"], kp_secrets["BNB_SECRET_KEY"])

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
                             mode='live')

    print(s2.get_df_with_buy_sl_tp_columns())
    sys.exit()
    runstep("live s2", s2.run)
    logger.info("Done.")