from datetime import datetime

import requests
import hmac
import hashlib
from urllib.parse import urlencode
import pandas as pd
import logging

from src.utils import make_df, interval_to_milliseconds, round_to_step_size, round_to_tick_size
import time
import cachetools
import functools

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
            # logger.warning(f"Cache does not exist for function {func.__name__} with arguments {args}")
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
        self.k_lines_limit = 500

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

        if response.status_code != 200:
            raise Exception(f'Request failed with status code {response.status_code}: {response.content}')

        return response.json()

    def _get_account_info(self):
        endpoint = "/api/v3/account"
        return self._request("GET", endpoint)

    def _get_all_tickers(self):
        url = f"{self.base_url}/api/v3/ticker/price"
        return requests.get(url).json()

    def get_historical_data(self, symbol: str, interval: str, start_time: datetime,
                            end_time: datetime = datetime.now()) -> pd.DataFrame:
        # Convert start_time and end_time to Unix timestamps in milliseconds
        start_time_ms = int(start_time.timestamp() * 1000)
        end_time_ms = int(end_time.timestamp() * 1000) if end_time else None
        limit = self.k_lines_limit if end_time_ms else 1000

        endpoint = "/api/v3/klines"

        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': start_time_ms,
            'endTime': end_time_ms,
            'limit': limit
        }

        data = self._request('GET', endpoint, params, signed=False)
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

    def place_vanilla_order(self, order_type, side, token, base_symbol, *, quantity=None, amount_base=None,
                            limit_price=None, stop_loss_price=None, custom_order_id = None):
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
        }

        # Add custom_order_id to the parameters if provided
        if custom_order_id is not None:
            params['newClientOrderId'] = custom_order_id

        # Get symbol filters
        filters = self.get_symbol_filters(token + base_symbol)

        # Round quantity and prices according to the filters
        quantity = round_to_step_size(quantity, filters['stepSize'])
        if order_type in ['LIMIT', 'STOP_LOSS_LIMIT']:
            limit_price = round_to_tick_size(limit_price, filters['tickSize'])
            params['price'] = f"{limit_price:.8f}"
            params['timeInForce'] = 'GTC'

        if order_type == 'STOP_LOSS_LIMIT':
            stop_loss_price = round_to_tick_size(stop_loss_price, filters['tickSize'])
            params['stopPrice'] = f"{stop_loss_price:.8f}"

        # Add rounded quantity to the parameters
        params['quantity'] = f"{quantity:.8f}"

        # Execute the order
        response = self._request("POST", endpoint, params)

        if response.get("code"):
            raise Exception(f"Error {response['code']}: {response['msg']}")

        # If the order is a market order, return the executed quantity and executed price
        if order_type == 'MARKET':
            executed_qty = 0
            total_quote_qty = 0
            total_fee = 0
            for fill in response.get('fills', []):
                fill_qty = float(fill['qty'])
                fill_price = float(fill['price'])
                fee = float(fill['commission'])  # assuming the fee is in the 'commission' field, adjust if needed
                executed_qty += fill_qty
                total_quote_qty += fill_qty * fill_price
                total_fee += fee

            executed_price = total_quote_qty / executed_qty if executed_qty != 0 else 0
            quantity_after_fees = executed_qty - total_fee

            return quantity_after_fees, executed_price

        # For other order types, you may return the whole response or any other relevant information
        return response

    def place_oco_order(self, side, token, base_symbol, *, quantity, stop_price, stop_limit_price,
                        take_profit_price, custom_order_id):

        if side not in ['BUY', 'SELL']:
            raise ValueError("Invalid order side. Must be 'BUY' or 'SELL'.")

        if token == base_symbol:
            raise ValueError("Cannot trade a symbol against itself.")

        # Get symbol filters
        filters = self.get_symbol_filters(token + base_symbol)

        # Round quantity and prices according to the filters
        quantity = round_to_step_size(quantity, filters['stepSize'])
        stop_price = round_to_tick_size(stop_price, filters['tickSize'])
        stop_limit_price = round_to_tick_size(stop_limit_price, filters['tickSize'])
        take_profit_price = round_to_tick_size(take_profit_price, filters['tickSize'])

        # Prepare the OCO order parameters
        endpoint = "/api/v3/order/oco"
        params = {
            'symbol': token + base_symbol,
            'side': side,
            'quantity': f"{quantity:.8f}",
            'stopPrice': f"{stop_price:.8f}",
            'stopLimitPrice': f"{stop_limit_price:.8f}",
            'stopLimitTimeInForce': 'GTC',
            'price': f"{take_profit_price:.8f}",
            'limitClientOrderId': custom_order_id
        }

        # Execute the OCO order
        response = self._request("POST", endpoint, params)

        if response.get("code"):
            raise Exception(f"Error {response['code']}: {response['msg']}")



    def update_historical_data_csv(self, symbol: str, interval: str, start_time: datetime,
                                   end_time: datetime = datetime.now(),
                                   chunk_size: int = 499) -> pd.DataFrame:
        # Your new function that uses your existing function to get historical data beyond Binance API limitations

        # Convert the interval string to the number of milliseconds
        ms_interval = interval_to_milliseconds(interval)

        # Convert start_time and end_time to Unix timestamps in milliseconds
        start_time_ms = int(start_time.timestamp() * 1000)
        end_time_ms = int(end_time.timestamp() * 1000)

        # Calculate the number of chunks needed to cover the specified time range
        my_chunks = ((end_time_ms - start_time_ms) // (ms_interval * chunk_size)) + 1
        logger.info(f'Requesting historical data in {my_chunks} chunks')

        # Initialize an empty list to store the results
        results = []

        # Loop over each chunk and call the get_historical_data function to retrieve data
        last_loop = False
        for i in range(my_chunks):
            if (i == my_chunks - 1):
                last_loop = True
            # Calculate the start and end time for the current chunk
            chunk_start_millis = start_time_ms + i * ms_interval * chunk_size
            chunk_end_millis = min(end_time_ms, chunk_start_millis + ms_interval * chunk_size)

            chunk_start_time = datetime.utcfromtimestamp(chunk_start_millis / 1000)
            chunk_end_time = datetime.utcfromtimestamp(chunk_end_millis / 1000) if not (last_loop) else None

            # Call the get_historical_data function to retrieve data for the current chunk
            chunk_data = self.get_historical_data(symbol, interval, chunk_start_time, chunk_end_time)

            LOCAL_TZ = 'Europe/Paris'
            chunk_data[f'Open time {LOCAL_TZ}'] = chunk_data['Open time'].dt.tz_localize('UTC').dt.tz_convert(LOCAL_TZ)
            chunk_data[f'Close time {LOCAL_TZ}'] = chunk_data['Close time'].dt.tz_localize('UTC').dt.tz_convert(
                LOCAL_TZ)

            # Append the chunk data to the results list
            results.append(chunk_data)

        # Concatenate all the results into a big dataframe
        df = pd.concat(results)
        df.drop_duplicates(subset=['Open time'])

        csv: str = f'{symbol}_{interval}.csv'  # start_time.strftime("%Y-%m-%d")
        logger.info(f'just updated {csv}')
        # Save the dataframe to a CSV file
        df.to_csv(csv, index=False)

        return df

    def get_open_orders(self, token, base_symbol, strategy_name):
        open_orders = self._request("GET", "/api/v3/openOrders", {"symbol": token + base_symbol})

        return open_orders

    def get_symbol_filters(self, symbol):
        endpoint = "/api/v3/exchangeInfo"
        response = self._request("GET", endpoint, signed=False)

        if response.get("code"):
            raise Exception(f"Error {response['code']}: {response['msg']}")

        for s in response['symbols']:
            if s['symbol'] == symbol:
                filters = {}
                for f in s['filters']:
                    if f['filterType'] == 'PRICE_FILTER':
                        filters['minPrice'] = float(f['minPrice'])
                        filters['maxPrice'] = float(f['maxPrice'])
                        filters['tickSize'] = float(f['tickSize'])
                    elif f['filterType'] == 'LOT_SIZE':
                        filters['minQty'] = float(f['minQty'])
                        filters['maxQty'] = float(f['maxQty'])
                        filters['stepSize'] = float(f['stepSize'])

                return filters

        raise ValueError(f"Symbol {symbol} not found.")
