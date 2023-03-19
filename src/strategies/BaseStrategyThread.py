import threading
import time
import logging

class BaseStrategyThread(threading.Thread):
    """Classe de base pour implémenter une stratégie financière comme un thread"""

    def __init__(self, name, exchange_client):
        threading.Thread.__init__(self, name=name)
        self.exchange_client = exchange_client
        self.exit_flag = threading.Event()
        self.strategy_name = name
        self.logger = logging.getLogger(self.name)
        logging.config.fileConfig('logging.conf', defaults={'strategy_name': self.strategy_name})

    def run(self):
        while not self.exit_flag.is_set():
            # Implémentation de la stratégie financière ici
            # ...

            # Attente avant la prochaine exécution de la stratégie
            time.sleep(60)

    def stop(self):
        self.exit_flag.set()
