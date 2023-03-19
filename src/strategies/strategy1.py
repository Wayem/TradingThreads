from threading import Thread
from time import sleep

class Strategy1(Thread):
    def __init__(self, api_client):
        Thread.__init__(self)
        self.api_client = api_client

    def run(self):
        while True:
            # Récupérer les informations sur le compte
            account_info = self.api_client.get_account_info()

            # Calculer la position à prendre
            position = calculate_position(account_info)

            # Passer un ordre sur Binance pour ouvrir une position
            order = self.api_client.create_order(position)

            # Attendre 1 minute avant de reprendre la boucle
            sleep(60)
