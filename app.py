import time
from flask import Flask, jsonify, request, redirect, render_template
from flask_cors import CORS
from kite_trade import KiteApp
from kiteconnect import KiteTicker
import os
import datetime
import yfinance as yf
from bs4 import BeautifulSoup
import requests
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)

load_dotenv()

ENCTOKEN = os.getenv('ENCTOKEN')
KITE_API_KEY = os.getenv('KITE_API_KEY')

# Global variable to hold the KiteApp instance
kite_instance = KiteApp(enctoken=ENCTOKEN)

def get_kite_instance():
    return kite_instance

def is_market_open():
    now = datetime.datetime.now()
    return True
    return now.weekday() < 5 and datetime.time(9, 15) <= now.time() <= datetime.time(15, 30)

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

import requests
from bs4 import BeautifulSoup

def get_top_gainers():
    url = "https://finance.yahoo.com/markets/stocks/gainers/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        table = soup.find('table')
        
        if not table:
            print("Table not found. The website structure might have changed.")
            return []
        
        gainers = []
        for row in table.find_all('tr')[1:6]:
            cells = row.find_all('td')
            if len(cells) >= 4:
                gainers.append({
                    'symbol': cells[0].text.strip().split()[0],
                    'company': ' '.join(cells[0].text.strip().split()[1:]),
                    'price': cells[1].text.strip(),
                    'change': cells[2].text.strip()
                })
        return gainers
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []

def scrape_stock_news(symbol):
    url = f"https://finance.yahoo.com/quote/{symbol}/latest-news"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Error fetching news: {response.status_code}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Debugging: Print the soup to check the content
    print(soup.prettify())  # Uncomment for detailed HTML output
    
    news_items = []
    # Check the class names again on the actual page
    for item in soup.find_all('h3', class_='Mb(5px)'):
        news_items.append(item.get_text(strip=True))
    
    return news_items[:5]

def analyze_sentiment(news_items):
    if not news_items:  # Check if the input list is empty
        return []  # Return an empty list if there are no news items

    vectorizer = TfidfVectorizer()
    clf = MultinomialNB()
    
    train_data = [
        ("Stock price soars", "positive"),
        ("Company reports losses", "negative"),
        ("Neutral market performance", "neutral")
    ]
    
    X_train = vectorizer.fit_transform([x[0] for x in train_data])
    y_train = [x[1] for x in train_data]
    
    clf.fit(X_train, y_train)
    
    X_test = vectorizer.transform(news_items)
    
    # Check if X_test is empty
    if X_test.shape[0] == 0:
        return []  # Return an empty list if there's nothing to predict

    predictions = clf.predict(X_test)
    
    return predictions.tolist()

@app.route('/api/profile', methods=['GET'])
def profile():
    kite = get_kite_instance()
    if not kite:
        return jsonify({"message": "KiteApp instance is not initialized."}), 400

    profile_data = kite.profile()
    return jsonify({"profile_data": profile_data, "market_status": is_market_open()})

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

    try:
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
        print("Support Levels:", s1, s2, s3)
        print("Resistance Levels:", r1, r2, r3)

        ltp_data = kite.ltp(f"{exchange}:{stock_name}")
        current_price = ltp_data[f"{exchange}:{stock_name}"]['last_price']
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
                print('Buy - ', current_price)

                # buy_order = kite.place_order(
                #     variety=kite.VARIETY_REGULAR,
                #     exchange=exchange,
                #     tradingsymbol=stock_name,
                #     transaction_type=kite.TRANSACTION_TYPE_BUY,
                #     quantity=quantity,
                #     product=kite.PRODUCT_CNC,
                #     order_type=kite.ORDER_TYPE_MARKET
                # )
                # print(f"Buy order placed. Order ID: {buy_order}")

                user_id = kite.profile()["user_id"]
                kws = KiteTicker(api_key=KITE_API_KEY, access_token=ENCTOKEN+"&user_id="+user_id)
                
                def on_ticks(ws, ticks):
                    print('ticks', ticks[0]["last_price"])
                    if target_price <= ticks[0]["last_price"]:
                        print('Sell - ', target_price)
                        try:
                            # sell_order = kite.place_order(
                            #     variety=kite.VARIETY_REGULAR,
                            #     exchange=exchange,
                            #     tradingsymbol=stock_name,
                            #     transaction_type=kite.TRANSACTION_TYPE_SELL,
                            #     quantity=quantity,
                            #     product=kite.PRODUCT_CNC,
                            #     order_type=kite.ORDER_TYPE_MARKET
                            # )
                            print(f"Sell order placed. Order ID: {target_price}")
                        except Exception as e:
                            print(f"Error placing sell order: {str(e)}")
                        finally:
                            kws.unsubscribe([instrument_token])

                kws.on_ticks = on_ticks
                kws.connect(threaded=True)
                while not kws.is_connected():
                    time.sleep(1)
                print("WebSocket : Connected")
                kws.subscribe([instrument_token])
                kws.set_mode(kws.MODE_QUOTE, [instrument_token])
                
                return jsonify({"message": "Order placed successfully.", "order_id": buy_order}), 200

    except Exception as e:
        return jsonify({"message": f"Error placing order: {str(e)}"}), 500

@app.route('/api/gainers')
def get_gainers_api():
    gainers = get_top_gainers()
    return jsonify(gainers)

@app.route('/api/scrape/<symbol>')
def scrape_stock(symbol):
    news_items = scrape_stock_news(symbol)
    print('news_items',news_items)
    sentiment = analyze_sentiment(news_items)
    return jsonify({
        'news': news_items,
        'sentiment': sentiment
    })

@app.route('/')
def index():
    # Get top gainers
    top_gainers = get_top_gainers()
    
    # Scrape news and analyze sentiment for top gainers
    gainer_data = []
    for gainer in top_gainers:
        news_items = scrape_stock_news(gainer['symbol'])
        sentiment = analyze_sentiment(news_items)
        gainer_data.append({
            'symbol': gainer['symbol'],
            'company': gainer['company'],
            'price': gainer['price'],
            'change': gainer['change'],
            'news': news_items,
            'sentiment': sentiment
        })

    return render_template('index.html', gainer_data=gainer_data)

if __name__ == '__main__':
    app.run(debug=True)
