import requests
import hmac
import hashlib
import time
from urllib.parse import urlencode
import pandas as pd
import logging
from src.utils import make_df
import time
import cachetools
import functools

logging.basicConfig(level = logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

## CACHE SYSTEM ##
# Create a cache with a maximum size of 100 and a time-to-live (TTL) of 300 seconds
cache = cachetools.TTLCache(maxsize=100, ttl=300)

def cache_results(func):
    @functools.wraps(func)
    def wrapper(self, *args):
        cache_key = (func.__name__, *args)

        try:
            result = cache[cache_key]
            logger.warning(f"Cache exists for function {func.__name__} with arguments {args}")
        except KeyError:
            #logger.warning(f"Cache does not exist for function {func.__name__} with arguments {args}")
            result = func(self, *args)
            cache[cache_key] = result

        return result
    return wrapper
## CACHE SYSTEM ##

class BinanceAPIClient:
    # other code ...
    """Client d'API pour Binance"""
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.binance.com"
        self.limit_klines_rows = 500

    def _generate_signature(self, data):
        query_string = urlencode(data)
        return hmac.new(self.api_secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256).hexdigest()

    def _request(self, method, endpoint, params=None, signed=True):
        url = self.base_url + endpoint
        if params is None:
            params = {}

        if signed:
            params['timestamp'] = int(time.time() * 1000)
            params['recvWindow'] = 5000
            params['signature'] = self._generate_signature(params)

        headers = {
            'X-MBX-APIKEY': self.api_key
        }

        response = requests.request(method, url, headers=headers, params=params)

        return response.json()

    @cache_results
    def _get_account_info(self):
        endpoint = "/api/v3/account"
        return self._request("GET", endpoint)
    
    @cache_results
    def _get_all_tickers(self):
        url = f"{self.base_url}/api/v3/ticker/price"
        return requests.get(url).json()
    
    @cache_results
    def get_historical_data(self, symbol, interval, start_time, end_time=None):
        if end_time is None:
            end_time = int(time.time() * 1000)

        endpoint = "/api/v3/klines"
        
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': start_time,
            'endTime': end_time
        }
        
        data = self._request('GET', endpoint, params, signed=False)
        assert len(data) < self.limit_klines_rows, f'get_historical_data() hit request size limit'
        return make_df(data)
    
    def print_top_assets(self):
        account_info = self._get_account_info()
        balances = account_info['balances']
        prices = self._get_all_tickers()

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

    def get_asset_value_in_currency(self, token, currency):
        account_info = self._get_account_info()
        balances = account_info['balances']
        prices = self._get_all_tickers()

        # Find the balance of the specified token
        token_balance = 0
        for balance in balances:
            asset = balance['asset']
            if asset == token:
                free = float(balance['free'])
                locked = float(balance['locked'])
                token_balance = free + locked
                break

        # Calculate the token value in the target currency
        token_value_in_currency = 0
        if token == currency:
            token_value_in_currency = token_balance
        else:
            for price in prices:
                if price['symbol'] == token + currency:
                    token_value_in_currency = token_balance * float(price['price'])
                    break

        return token_value_in_currency
    
    def place_vanilla_order(self, order_type, side, token, base_symbol, *, quantity=None, amount_base=None, limit_price=None, stop_loss_price=None):
        if token == base_symbol:
            raise ValueError("Cannot trade a symbol against itself.")

        if side not in ['BUY', 'SELL']:
            raise ValueError("Invalid order side. Must be 'BUY' or 'SELL'.")

        if order_type not in ['MARKET', 'LIMIT', 'STOP_LOSS_LIMIT']:
            raise ValueError("Invalid order type. Must be 'MARKET', 'LIMIT', or 'STOP_LOSS_LIMIT'.")

        if order_type == 'LIMIT' and limit_price is None:
            raise ValueError("Limit price must be provided for LIMIT orders.")

        if order_type == 'STOP_LOSS_LIMIT' and (limit_price is None or stop_loss_price is None):
            raise ValueError("Limit price and stop-loss price must be provided for STOP_LOSS_LIMIT orders.")

        if quantity is None and amount_base is None:
            raise ValueError("Either quantity or amount in base symbol must be provided.")

        # Get the current token price in the base symbol
        prices = self._get_all_tickers()
        token_price_base = None
        for price in prices:
            if price['symbol'] == token + base_symbol:
                token_price_base = float(price['price'])
                break

        if token_price_base is None:
            raise ValueError(f"Token price for {token}{base_symbol} not found.")

        if amount_base is not None:
            # Calculate the quantity to buy/sell using the amount in base symbol
            quantity = amount_base / token_price_base

        # Prepare the order parameters
        endpoint = "/api/v3/order"
        params = {
            'symbol': token + base_symbol,
            'side': side,
            'type': order_type,
            'quantity': round(quantity, 8),  # Round the quantity to 8 decimal places
        }

        if order_type in ['LIMIT', 'STOP_LOSS_LIMIT']:
            params['price'] = f"{limit_price:.8f}"
            params['timeInForce'] = 'GTC'

        if order_type == 'STOP_LOSS_LIMIT':
            params['stopPrice'] = f"{stop_loss_price:.8f}"

        # Execute the order
        response = self._request("POST", endpoint, params)
        
        if response.get("code"):
            raise Exception(f"Error {response['code']}: {response['msg']}")
        
def place_oco_order(self, side, token, base_symbol, *, quantity, stop_loss_price, stop_limit_price, take_profit_price):
    if side not in ['BUY', 'SELL']:
        raise ValueError("Invalid order side. Must be 'BUY' or 'SELL'.")

    if token == base_symbol:
        raise ValueError("Cannot trade a symbol against itself.")

    # Prepare the OCO order parameters
    endpoint = "/api/v3/order/oco"
    params = {
        'symbol': token + base_symbol,
        'side': side,
        'quantity': round(quantity, 8),  # Round the quantity to 8 decimal places
        'stopPrice': f"{stop_loss_price:.8f}",
        'stopLimitPrice': f"{stop_limit_price:.8f}",
        'stopLimitTimeInForce': 'GTC',
        'price': f"{take_profit_price:.8f}",
    }

    # Execute the OCO order
    response = self._request("POST", endpoint, params)

    if response.get("code"):
        raise Exception(f"Error {response['code']}: {response['msg']}")
