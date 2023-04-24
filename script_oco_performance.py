from main import runstep
from src.api import BinanceAPIClient
from src.utils.kp_secrets import extract_kp_secrets

def test_order_sequence(historical_orders):
    filled_orders = [ord for ord in historical_orders if ord["status"] == "FILLED"]
    # Sort the orders by their creation timestamp
    sorted_orders = sorted(filled_orders, key=lambda x: x["time"])

    # Find the index of the first market order followed by a limit order or a limit stop order that is FILLED
    first_market_limit_pair_index = None
    for i, order in enumerate(sorted_orders[:-1]):
        if order["type"] == "MARKET" and (sorted_orders[i + 1]["type"] in ["LIMIT_MAKER", "STOP_LOSS_LIMIT"] and sorted_orders[i + 1]["status"] == "FILLED"):
            first_market_limit_pair_index = i
            break

    # If there is no market-limit pair, raise AssertionError with a message
    if first_market_limit_pair_index is None:
        raise AssertionError("Test failed: No market-limit order pairs found.")

    # Create a new list of orders starting from the first market-limit pair
    orders_from_first_market_limit_pair = sorted_orders[first_market_limit_pair_index:]

    # If the list ends with a market order, remove it
    if orders_from_first_market_limit_pair[-1]["type"] == "MARKET":
        orders_from_first_market_limit_pair = orders_from_first_market_limit_pair[:-1]

    # Set the expected order types sequence
    expected_order_types = ["MARKET", ["LIMIT_MAKER", "STOP_LOSS_LIMIT"]]

    # Iterate through the orders and check if the order types follow the expected sequence
    for i in range(len(orders_from_first_market_limit_pair) - 1):
        current_order_type = orders_from_first_market_limit_pair[i]["type"]
        next_order_type = orders_from_first_market_limit_pair[i + 1]["type"]

        # Check if the current order type matches the expected order type in the sequence
        if (i % 2 == 0 and current_order_type != expected_order_types[i % 2]) or (i % 2 != 0 and current_order_type not in expected_order_types[i % 2]):
            raise AssertionError(f"Test failed: Order type mismatch at index {i}. Expected {expected_order_types[i % 2]}, found {current_order_type}.")

        # Check if the current order is a market order and the next order is not a FILLED limit order or a FILLED limit stop order
        if current_order_type == "MARKET" and (next_order_type not in ["LIMIT_MAKER", "STOP_LOSS_LIMIT"] or orders_from_first_market_limit_pair[i + 1]["status"] != "FILLED"):
            raise AssertionError(f"Test failed: Market order at index {i} not followed by a FILLED limit maker or a FILLED limit stop order for order {orders_from_first_market_limit_pair[i]['clientOrderId']}")

    return orders_from_first_market_limit_pair


def calculate_strategy_performance(orders):
    winning_pairs = 0
    losing_pairs = 0
    total_profit = 0
    total_investment = 0

    for i in range(0, len(orders) - 1, 2):
        market_order = orders[i]
        limit_order = orders[i + 1]

        if market_order["side"] == "BUY" and limit_order["side"] == "SELL":
            executed_price = float(market_order["cummulativeQuoteQty"]) / float(market_order["executedQty"])
            investment = executed_price * float(market_order["executedQty"])
            profit = (float(limit_order["price"]) - executed_price) * float(market_order["executedQty"])

            if profit > 0:
                winning_pairs += 1
            else:
                losing_pairs += 1

            total_profit += profit
            total_investment += investment

    overall_performance = total_profit / total_investment if total_investment > 0 else 0

    return {
        "winning_pairs": winning_pairs,
        "losing_pairs": losing_pairs,
        "overall_performance": overall_performance
    }




if __name__ == "__main__":
    kp_secrets = runstep("keepass access", extract_kp_secrets)
    client = BinanceAPIClient(kp_secrets["BNB_API_KEY"], kp_secrets["BNB_SECRET_KEY"])

    w = client._get_current_weight()
    print(f"weight: {w}")

    historical_orders = client.get_historical_orders("BNB","EUR", "oco_scalp")

    order_seq_ok = test_order_sequence(historical_orders)
    print(calculate_strategy_performance(order_seq_ok))