from flask import Flask, jsonify, request, redirect
from flask_cors import CORS
from kite_trade import KiteApp
from kiteconnect import KiteTicker
import os
import datetime

app = Flask(__name__)
CORS(app)

from dotenv import load_dotenv
load_dotenv()

ENCTOKEN = os.getenv('ENCTOKEN')

# Global variable to hold the KiteApp instance
kite_instance = KiteApp(enctoken=ENCTOKEN)

def is_market_open():
    now = datetime.datetime.now()
    return True
    return now.weekday() < 5 and now.time() >= datetime.time(9, 30) and now.time() <= datetime.time(15, 0)

def calculate_target_price(entry_price, target_profit_percentage):
    return entry_price * (1 + target_profit_percentage / 100)

def calculate_pivot_point(previous_high, previous_low, previous_close):
    return (previous_high + previous_low + previous_close) / 3

def get_kite_instance():
    if kite_instance is None:
        return None
    return kite_instance

@app.route('/api/profile', methods=['GET'])
def profile():
    kite = get_kite_instance()
    if not kite:
        return jsonify({"message": "KiteApp instance is not initialized."}), 400

    profile_data = kite.profile()
    return jsonify({"profile_data":profile_data,"market_status":is_market_open()})

@app.route('/api/instruments', methods=['GET'])
def get_instruments():
    exchange = request.args.get('exchange').upper()
    kite = get_kite_instance()
    if not kite:
        return jsonify({"message": "KiteApp instance is not initialized."}), 400

    instruments = kite.instruments(exchange)
    return jsonify(instruments)

@app.route('/api/order', methods=['POST'])
def place_order():
    data = request.json
    stock_name = data.get('name')
    quantity = data.get('quantity')
    exchange = data.get('exchange').upper()
    target_profit_percentage = data.get('profit_percentage')

    if not is_market_open():
        return jsonify({"message": "Market is closed."}), 400

    kite = get_kite_instance()
    if not kite:
        return jsonify({"message": "KiteApp instance is not initialized."}), 400

    # Fetch instrument token
    instrument_token = None
    instruments_data = kite.instruments(exchange)
    for instrument in instruments_data:
        if instrument['tradingsymbol'].lower() == stock_name.lower():
            instrument_token = instrument['instrument_token']
            break

    # Fetch historical data
    historical_data = kite.historical_data(instrument_token, datetime.datetime.now() - datetime.timedelta(days=1), datetime.datetime.now(), "day")
    previous_high = max(data['high'] for data in historical_data)
    previous_low = min(data['low'] for data in historical_data)
    previous_close = historical_data[-1]['close']
    pivot_point = calculate_pivot_point(previous_high, previous_low, previous_close)

    current_price = kite.ltp(f"{exchange}:{stock_name}")[f"{exchange}:{stock_name}"]['last_price']
    if current_price > pivot_point:
        target_price = calculate_target_price(current_price, target_profit_percentage)

        # Start WebSocket to monitor price
        user_id = kite.profile()["user_id"]
        kws = KiteTicker(api_key="TradeViaPython", access_token=f"{ENCTOKEN}&user_id={user_id}")

        def on_ticks(ws, ticks):
            for tick in ticks:
                price = tick['last_price']
                if price >= target_price:
                    print("Sell Order:", price)
                    kws.unsubscribe([instrument_token])
                    break

        kws.on_ticks = on_ticks
        kws.connect(threaded=True)
        kws.subscribe([instrument_token])
        kws.set_mode(kws.MODE_QUOTE, [instrument_token])

        return jsonify({"message": "Order placed successfully.", "target_price": target_price}), 200
    else:
        return jsonify({"message": "Current price is below the pivot point. Order not placed."}), 400

@app.route('/api/sell_previous_orders', methods=['POST'])
def sell_previous_orders():
    kite = get_kite_instance()
    if not kite:
        return jsonify({"message": "KiteApp instance is not initialized."}), 400

    profit_percentage = float(request.json.get('profit_percentage', 0.75))
    orders = kite.orders()
    sell_orders = []
    for order in orders:
        if order['status'] == "COMPLETE" and order['transaction_type'] == kite.TRANSACTION_TYPE_BUY:
            stock_name = order['tradingsymbol']
            exchange = order['exchange']
            instruments_data = kite.instruments(exchange)
            instrument_token = next((inst['instrument_token'] for inst in instruments_data if inst['tradingsymbol'] == stock_name), None)

            if instrument_token:
                current_price = kite.ltp(f"{exchange}:{stock_name}")[f"{exchange}:{stock_name}"]['last_price']
                entry_price = order['average_price']
                target_price = calculate_target_price(entry_price, profit_percentage)

                if current_price >= target_price:
                    sell_orders.append(f"Sell Order for {stock_name}: {current_price}")

    return jsonify({"message": "Checked all previous orders for selling.", "sell_orders": sell_orders})

if __name__ == '__main__':
    app.run(debug=True)
