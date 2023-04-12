import threading
import time
import logging
import logging.config

class BaseStrategyThread(threading.Thread):
    """Classe de base pour implémenter une stratégie financière comme un thread"""

    def __init__(self, name, exchange_client, mode = "backtest", initial_investment = 100):
        threading.Thread.__init__(self, name=name)
        self.exchange_client = exchange_client
        self.initial_investment_in_base_symbol_quantity = initial_investment
        self.strategy_name = name
        self.mode = mode
        self.exit_flag = threading.Event()

        # this whole stuff just for logs
        self.logger = logging.getLogger(self.strategy_name)
        # Set the max file size and the number of backup files to keep
        max_file_size = 3 * 1024 * 1024  # 10 MB
        backup_count = 3

        file_handler = logging.RotatingFileHandler(f'logs/{self.strategy_name}.log',
                                                   maxBytes = max_file_size,
                                                   backupCount = backup_count)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def run(self):
        while not self.exit_flag.is_set():
            # Implémentation de la stratégie financière ici
            # ...

            # Attente avant la prochaine exécution de la stratégie
            time.sleep(60)

    def stop(self):
        self.exit_flag.set()
