from flask import Flask, jsonify, request, render_template
from kite_trade import KiteApp
from kiteconnect import KiteTicker
import datetime

app = Flask(__name__)

def is_market_open():
    now = datetime.datetime.now()
    return now.weekday() < 5 and now.time() >= datetime.time(9, 30) and now.time() <= datetime.time(15, 0)

def calculate_target_price(entry_price, target_profit_percentage):
    return entry_price * (1 + target_profit_percentage / 100)

def calculate_pivot_point(previous_high, previous_low, previous_close):
    return (previous_high + previous_low + previous_close) / 3

@app.route('/instruments', methods=['GET'])
def get_instruments():
    exchange = request.args.get('exchange').upper()
    enctoken = request.args.get('enctoken')
    kite = KiteApp(enctoken=enctoken)
    instruments = kite.instruments(exchange)
    return jsonify(instruments)

@app.route('/', methods=['GET', 'POST'])
def index():
    profile_data = None
    enctoken = ''
    message = ''

    if request.method == 'POST':
        if 'enctoken' in request.form:
            enctoken = request.form.get('enctoken')
            kite = KiteApp(enctoken=enctoken)
            profile_data = kite.profile()

        elif 'name' in request.form:
            if not is_market_open():
                message = "Please wait until tomorrow. The market is currently closed."
            else:
                stock_name = request.form.get('name')
                quantity = int(request.form.get('quantity'))
                exchange = request.form.get('exchange').upper()
                target_profit_percentage = float(request.form.get('profit_percentage'))

                # Fetch previous day's high, low, close for pivot calculation
                historical_data = kite.historical_data(instrument_token, datetime.datetime.now() - datetime.timedelta(days=1), datetime.datetime.now(), "day")
                previous_high = max(data['high'] for data in historical_data)
                previous_low = min(data['low'] for data in historical_data)
                previous_close = historical_data[-1]['close']

                pivot_point = calculate_pivot_point(previous_high, previous_low, previous_close)
                print(f"Pivot Point: {pivot_point}")

                # Fetch instrument token
                instrument_token = None
                instruments_data = kite.instruments(exchange)
                for instrument in instruments_data:
                    if instrument['tradingsymbol'].lower() == stock_name.lower():
                        instrument_token = instrument['instrument_token']
                        break

                if instrument_token:
                    # Check if the current price is greater than the pivot point before placing the order
                    current_price = kite.ltp(f"{exchange}:{stock_name}")[f"{exchange}:{stock_name}"]['last_price']
                    if current_price > pivot_point:
                        # Place CNC order
                        order = kite.place_order(
                            variety=kite.VARIETY_REGULAR,
                            exchange=exchange,
                            tradingsymbol=stock_name,
                            transaction_type=kite.TRANSACTION_TYPE_BUY,
                            quantity=quantity,
                            product=kite.PRODUCT_CNC,
                            order_type=kite.ORDER_TYPE_MARKET
                        )
                        print("Buy Order:", order)

                        # Calculate target price
                        entry_price = order['average_price']
                        target_price = calculate_target_price(entry_price, target_profit_percentage)
                        print(f"Target Price: {target_price}")

                        # Start WebSocket to monitor price
                        user_id = kite.profile()["user_id"]
                        kws = KiteTicker(api_key="TradeViaPython", access_token=f"{enctoken}&user_id={user_id}")

                        def on_ticks(ws, ticks):
                            for tick in ticks:
                                price = tick['last_price']
                                if price >= target_price:
                                    # Trigger sell order when target price is hit
                                    sell_order = kite.place_order(
                                        variety=kite.VARIETY_REGULAR,
                                        exchange=exchange,
                                        tradingsymbol=stock_name,
                                        transaction_type=kite.TRANSACTION_TYPE_SELL,
                                        quantity=quantity,
                                        product=kite.PRODUCT_CNC,
                                        order_type=kite.ORDER_TYPE_MARKET
                                    )
                                    print("Sell Order:", sell_order)
                                    kws.unsubscribe([instrument_token])
                                    break

                        kws.on_ticks = on_ticks
                        kws.connect(threaded=True)

                        # Subscribe to the instrument token for price updates
                        kws.subscribe([instrument_token])
                        kws.set_mode(kws.MODE_QUOTE, [instrument_token])
                    else:
                        message = "Current price is below the pivot point. Order not placed."

    return render_template('index.html', profile_data=profile_data, enctoken=enctoken, message=message)

@app.route('/sell_previous_orders', methods=['POST'])
def sell_previous_orders():
    enctoken = request.form.get('enctoken')
    profit_percentage = float(request.form.get('profit_percentage', 0.75))
    kite = KiteApp(enctoken=enctoken)

    # Get all completed orders
    orders = kite.orders()
    for order in orders:
        if order['status'] == "COMPLETE" and order['transaction_type'] == kite.TRANSACTION_TYPE_BUY:
            # Get the current price of the stock
            stock_name = order['tradingsymbol']
            exchange = order['exchange']
            instruments_data = kite.instruments(exchange)
            instrument_token = next((inst['instrument_token'] for inst in instruments_data if inst['tradingsymbol'] == stock_name), None)

            if instrument_token:
                current_price = kite.ltp(f"{exchange}:{stock_name}")[f"{exchange}:{stock_name}"]['last_price']
                entry_price = order['average_price']  # Assume this is fetched or stored somewhere
                target_price = calculate_target_price(entry_price, profit_percentage)  # Dynamic target percentage

                # Check if current price has reached target
                if current_price >= target_price:
                    # Place sell order
                    sell_order = kite.place_order(
                        variety=kite.VARIETY_REGULAR,
                        exchange=exchange,
                        tradingsymbol=stock_name,
                        transaction_type=kite.TRANSACTION_TYPE_SELL,
                        quantity=order['quantity'],
                        product=kite.PRODUCT_CNC,
                        order_type=kite.ORDER_TYPE_MARKET
                    )
                    print(f"Sell Order for {stock_name}: {sell_order}")

    return jsonify({"message": "Checked all previous orders for selling."})

if __name__ == '__main__':
    app.run(debug=True)
