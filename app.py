import time
from flask import Flask, jsonify, request, redirect, render_template
from flask_cors import CORS
from kite_trade import KiteApp
from kiteconnect import KiteTicker
import os
from datetime import datetime, timedelta
import yfinance as yf
from bs4 import BeautifulSoup
import requests
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from dotenv import load_dotenv
from transformers import pipeline
import requests
from bs4 import BeautifulSoup

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
    now = datetime.now()
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
    
    return {
        'pp': pp,
        'r1': r1, 'r2': r2, 'r3': r3,
        's1': s1, 's2': s2, 's3': s3
    }

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
        for row in table.find_all('tr')[1:10]:
            cells = row.find_all('td')
            if len(cells) >= 4:

                ticker = yf.Ticker(cells[0].text.strip().split()[0])
                info = ticker.info
                
                # Get historical data for pivot point calculation
                end_date = datetime.now()
                start_date = end_date - timedelta(days=5)  # Get 5 days of data to ensure we have enough historical data
                hist = ticker.history(start=start_date, end=end_date)
                
                if len(hist) < 2:
                    raise ValueError("Not enough historical data to calculate pivot points")
                
                # Calculate pivot points using the previous day's data
                previous_day = hist.iloc[-2]
                pivot_points = calculate_advanced_pivot(previous_day['High'], previous_day['Low'], previous_day['Close'])
                
                # Current price
                current_price = info.get('currentPrice', hist.iloc[-1]['Close'])
                
                # Determine position relative to pivot points
                position = "At Pivot Point"
                for level in ['s3', 's2', 's1', 'pp', 'r1', 'r2', 'r3']:
                    if current_price < pivot_points[level]:
                        position = f"Between {level.upper()} and {('r1' if level == 'pp' else 'pp' if level == 's1' else f's{int(level[1])+1}').upper()}"
                        break
                if current_price > pivot_points['r3']:
                    position = "Above R3"
                
                stock_info = {
                    'symbol': cells[0].text.strip().split()[0],
                    'company': info.get('longName', 'N/A'),
                    'price': current_price,
                    'change': f"{info.get('regularMarketChangePercent', 0):.2f}%",
                    'pivot_points': pivot_points,
                    'position': position
                }

                gainers.append({
                    'symbol': cells[0].text.strip().split()[0],
                    'company': ' '.join(cells[0].text.strip().split()[1:]),
                    'price': cells[1].text.strip(),
                    'change': cells[2].text.strip(),
                    'stock_info': stock_info
                })

        return gainers
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []

def scrape_stock_news(symbol):
    try:
        # Create a Ticker object
        ticker = yf.Ticker(symbol)
        
        # Fetch news
        news = ticker.news
        # Process and return the first 5 news items
        news_items = []
        for item in news[:5]:
            news_items.append({
                'title': item['title'],
                'url': item['link']
            })
        
        return news_items
    except Exception as e:
        print(f"Error fetching news for {symbol}: {e}")
        return []

sentiment_analyzer = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
def analyze_sentiment(news_items):
    if not news_items:
        return []

    sentiments = []
    for item in news_items:
        try:
            # Fetch the full article content
            response = requests.get(item['url'], timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract the main text content (this may need adjustment based on the specific news site structure)
            paragraphs = soup.find_all('p')
            full_text = ' '.join([p.get_text() for p in paragraphs])
            
            # Truncate text if it's too long (BERT models typically have a max length of 512 tokens)
            max_length = 500  # Adjust as needed
            truncated_text = ' '.join(full_text.split()[:max_length])
            
            # Analyze sentiment
            result = sentiment_analyzer(truncated_text)[0]
            
            sentiments.append({
                'title': item['title'],
                'sentiment': result['label'],
                'score': result['score']
            })
        except Exception as e:
            print(f"Error analyzing sentiment for {item['title']}: {str(e)}")
            sentiments.append({
                'title': item['title'],
                'sentiment': 'NEUTRAL',
                'score': 0.5
            })

    return sentiments

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
            datetime.now() - datetime.timedelta(days=5),
            datetime.now(),
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

def get_stock_details(symbol):
    try:
        # For Indian stocks, we need to append ".NS" for NSE listings
        ticker = yf.Ticker(f"{symbol}.NS")
        info = ticker.info
        
        if not info:
            raise ValueError(f"No information found for symbol {symbol}")
        
        # Get historical data for pivot point calculation
        end_date = datetime.now()
        start_date = end_date - timedelta(days=5)
        hist = ticker.history(start=start_date, end=end_date)
        
        if len(hist) < 2:
            raise ValueError(f"Not enough historical data to calculate pivot points for {symbol}")
        
        # Calculate pivot points using the previous day's data
        previous_day = hist.iloc[-2]
        pivot_points = calculate_advanced_pivot(previous_day['High'], previous_day['Low'], previous_day['Close'])
        
        # Current price
        current_price = info.get('currentPrice', hist.iloc[-1]['Close'])
        
        # Determine position relative to pivot points
        position = "At Pivot Point"
        for level in ['s3', 's2', 's1', 'pp', 'r1', 'r2', 'r3']:
            if current_price < pivot_points[level]:
                position = f"Between {level.upper()} and {('r1' if level == 'pp' else 'pp' if level == 's1' else f's{int(level[1])+1}').upper()}"
                break
        if current_price > pivot_points['r3']:
            position = "Above R3"
        
        return {
            'symbol': symbol,
            'company': info.get('longName', 'N/A'),
            'price': current_price,
            'change': f"{info.get('regularMarketChangePercent', 0):.2f}%",
            'pivot_points': pivot_points,
            'position': position
        }
    except ValueError as ve:
        print(f"ValueError in get_stock_details for {symbol}: {str(ve)}")
        return None
    except Exception as e:
        print(f"Unexpected error in get_stock_details for {symbol}: {str(e)}")
        return None

@app.route('/api/search/<symbol>')
def search_stock(symbol):
    try:
        stock_info = get_stock_details(symbol)
        if not stock_info:
            return jsonify({'error': f"Unable to fetch details for {symbol}. Please ensure the symbol is correct and try again."}), 404
        
        return jsonify(stock_info)
    
    except Exception as e:
        print(f"Error searching stock {symbol}: {e}")
        return jsonify({
            'error': f"Error searching stock {symbol}: {str(e)}"
        }), 400

@app.route('/api/scrape/<symbol>')
def scrape_stock(symbol):
    try:
        # Fetch news and analyze sentiment
        news_items = scrape_stock_news(symbol)
        sentiment = analyze_sentiment(news_items)
        
        return jsonify({
            'news': news_items,
            'sentiment': sentiment
        })
    
    except Exception as e:
        print(f"Error scraping stock {symbol}: {e}")
        return jsonify({
            'error': f"Error scraping stock {symbol}: {str(e)}"
        }), 400

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
