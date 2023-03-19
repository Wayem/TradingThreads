import requests
import hmac
import hashlib
import time
from urllib.parse import urlencode

class BinanceAPIClient:
    """Client d'API pour Binance"""

    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.binance.com"

    def _generate_signature(self, data):
        query_string = urlencode(data)
        return hmac.new(self.api_secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256).hexdigest()

    def _request(self, method, endpoint, params=None):
        url = self.base_url + endpoint
        if params is None:
            params = {}

        params['timestamp'] = int(time.time() * 1000)
        params['recvWindow'] = 5000
        params['signature'] = self._generate_signature(params)

        headers = {
            'X-MBX-APIKEY': self.api_key
        }

        response = requests.request(method, url, headers=headers, params=params)

        return response.json()

    def get_account_info(self):
        endpoint = "/api/v3/account"
        return self._request("GET", endpoint)
    
    def get_all_tickers(self):
        url = f"{self.base_url}/api/v3/ticker/price"
        response = requests.get(url)
        return response.json()
    
    def print_top_assets(self):
        account_info = self.get_account_info()
        balances = account_info['balances']
        prices = self.get_all_tickers()

        # Calculate the total balance in euros
        total_balance_eur = 0
        for balance in balances:
            asset = balance['asset']
            free = float(balance['free'])
            locked = float(balance['locked'])
            balance_eur = 0
            if asset == 'EUR':
                balance_eur = free + locked
            else:
                for price in prices:
                    if price['symbol'] == asset + 'EUR':
                        balance_eur = (free + locked) * float(price['price'])
                        break
            total_balance_eur += balance_eur

        # Sort the assets by their euro value
        assets = {}
        for balance in balances:
            asset = balance['asset']
            free = float(balance['free'])
            locked = float(balance['locked'])
            balance_eur = 0
            if asset == 'EUR':
                balance_eur = free + locked
            else:
                for price in prices:
                    if price['symbol'] == asset + 'EUR':
                        balance_eur = (free + locked) * float(price['price'])
                        break
            assets[asset] = balance_eur

        top_assets = sorted(assets.items(), key=lambda x: x[1], reverse=True)[:10]
        print(top_assets)