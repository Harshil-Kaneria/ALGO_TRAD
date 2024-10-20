import time
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

def get_kite_instance():
    if kite_instance is None:
        return None
    return kite_instance

def is_market_open():
    now = datetime.datetime.now()
    return True
    return now.weekday() < 5 and now.time() >= datetime.time(9, 30) and now.time() <= datetime.time(15, 0)

def calculate_target_price(entry_price, target_profit_percentage):
    return entry_price * (1 + target_profit_percentage / 100)

def calculate_advanced_pivot(previous_high, previous_low, previous_close):
    pp = (previous_high + previous_low + previous_close) / 3
    s1 = (2 * pp) - previous_high
    s2 = pp - (previous_high - previous_low)
    s3 = previous_low - 2 * (previous_high - pp)
    
    r1 = (2 * pp) - previous_low
    r2 = pp + (previous_high - previous_low)
    r3 = previous_high + 2 * (pp - previous_low)
    
    return pp, s1, s2, s3, r1, r2, r3

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
    enctoken = ENCTOKEN

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

    if not instrument_token:
        return jsonify({"message": "Instrument not found."}), 404

    # Fetch historical data
    historical_data = kite.historical_data(
        instrument_token,
        datetime.datetime.now() - datetime.timedelta(days=5),
        datetime.datetime.now(),
        "day"
    )
    previous_high = max(data['high'] for data in historical_data)
    previous_low = min(data['low'] for data in historical_data)
    previous_close = historical_data[-1]['close']
    
    # Calculate advanced pivot points
    pp, s1, s2, s3, r1, r2, r3 = calculate_advanced_pivot(previous_high, previous_low, previous_close)
    print("Pivot Point:", pp)
    print("Support Levels:", s1)
    print("Resistance Levels:", r1)

    # ltp_data = kite.ltp(f"{exchange}:{stock_name}")
    # current_price = ltp_data[f"{exchange}:{stock_name}"]['last_price']

    current_price = 1930;
    target_price = calculate_target_price(current_price, target_profit_percentage)

    if current_price <= pp:
        if current_price < s1:
            return jsonify({"message": "DON'T BUY IT AND WAIT FOR REVERSAL, IT'S CLOSER TO SUPPORT LEVEL"}), 400
        else:
            return jsonify({"message": "DON'T BUY IT BECAUSE IT'S CURRENT PRICE IS BELOW THE PIVOT POINT"}), 400
    else:
        if current_price >= r1 - (r1 - pp) * 0.1:
            return jsonify({"message": "DON'T BUY IT BECAUSE IT'S CLOSER TO R1"}), 400
        else:

            print('Buy - ',current_price)

            user_id = kite.profile()["user_id"]
            kws = KiteTicker(api_key="TradeViaPython", access_token=enctoken+"&user_id="+user_id)
            
            def on_ticks(ws, ticks):
                print('ticks',ticks[0]["last_price"])
                if target_price<=ticks[0]["last_price"]:
                    print('Sell - ',target_price)
                    kws.unsubscribe([instrument_token])

            kws.on_ticks = on_ticks
            kws.connect(threaded=True)
            while not kws.is_connected():
                time.sleep(1)
            print("WebSocket : Connected")
            kws.subscribe([instrument_token])
            kws.set_mode(kws.MODE_QUOTE, [instrument_token])
            
            
            return jsonify({"message": "Order placed successfully."}), 200
    
if __name__ == '__main__':
    app.run(debug=True)
