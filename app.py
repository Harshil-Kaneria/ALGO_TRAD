from flask import Flask, jsonify, request, render_template
from kite_trade import *
import datetime
import threading

app = Flask(__name__)

def is_market_open():
    now = datetime.datetime.now()
    return now.weekday() < 5 and now.time() >= datetime.time(9, 30) and now.time() <= datetime.time(15, 0)

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
                profit_percentage = float(request.form.get('profit_percentage'))

                kite = KiteApp(enctoken=enctoken)
                instruments_data = kite.instruments(exchange)
                instrument_token = None

                for instrument in instruments_data:
                    if instrument['tradingsymbol'].lower() == stock_name.lower():
                        instrument_token = instrument['instrument_token']
                        break

                if instrument_token:
                    order = kite.place_order(
                        variety=kite.VARIETY_REGULAR,
                        exchange=exchange,
                        tradingsymbol=stock_name,
                        transaction_type=kite.TRANSACTION_TYPE_BUY,
                        quantity=quantity,
                        product=kite.PRODUCT_MIS,
                        order_type=kite.ORDER_TYPE_MARKET
                    )
                    print("Buy Order:", order)

                    threading.Thread(target=start_websocket, args=(kite, instrument_token, quantity, profit_percentage)).start()

    return render_template('index.html', profile_data=profile_data, enctoken=enctoken, message=message)

if __name__ == '__main__':
    app.run(debug=True)
