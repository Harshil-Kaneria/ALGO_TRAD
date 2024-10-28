import eventlet
eventlet.monkey_patch()
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
import numpy as np
import torch
import torch.nn as nn
from flask import Flask, jsonify, request, redirect, render_template
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import threading
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LinearRegression

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

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
                'url': item['link'],
                'publisher': item['publisher'],
                'publish_time': datetime.fromtimestamp(item['providerPublishTime']).strftime('%Y-%m-%d %I:%M:%S %p')
            })
        
        return news_items
    except Exception as e:
        print(f"Error fetching news for {symbol}: {e}")
        return []

sentiment_analyzer = pipeline("sentiment-analysis", model="yiyanghkust/finbert-tone")
def analyze_sentiment(news_items):
    if not news_items:
        return []

    sentiments = []
    for item in news_items:
        try:
            # Fetch the full article content
            response = requests.get(item['url'], timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            paragraphs = soup.find_all('p')
            full_text = ' '.join([p.get_text() for p in paragraphs])

            # Split text into sentences
            sentences = full_text.split('. ')
            scores = []

            for sentence in sentences:
                if len(sentence.strip()) > 0:  # Ensure the sentence is not empty
                    result = sentiment_analyzer(sentence)[0]

                    # Use a different scoring mechanism
                    if result['label'] == 'Positive':
                        scores.append(result['score'])  # Positive scores
                    elif result['label'] == 'Negative':
                        scores.append(-result['score'])  # Negative scores
                    else:  # Neutral
                        scores.append(0)  # Neutral sentiment contributes 0

            # Calculate average score for the article
            average_score = np.mean(scores) if scores else 0
            overall_sentiment = 'Positive' if average_score > 0 else 'Negative' if average_score < 0 else 'Neutral'

            sentiments.append({
                'title': item['title'],
                'sentiment': overall_sentiment,
                'score': average_score
            })
        except Exception as e:
            print(f"Error analyzing sentiment for {item['title']}: {str(e)}")
            sentiments.append({
                'title': item['title'],
                'sentiment': 'neutral',
                'score': 0.0
            })

    return sentiments

# Define a simple neural network model
class StockPricePredictor(nn.Module):
    def __init__(self):
        super(StockPricePredictor, self).__init__()
        self.fc1 = nn.Linear(3, 10)  # 3 input features
        self.fc2 = nn.Linear(10, 1)   # 1 output
 
    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = self.fc2(x)
        return x
 
# Function to fetch historical data
def get_historical_data(symbol, interval='1d', period='1y'):  # Changed period from '1mo' to '1y'
    try:
        # Try multiple combinations to get the most data
        data = None
        suffixes = ['.NS', '.BO', '']  # Try NSE, BSE, and without suffix
        
        for suffix in suffixes:
            try:
                temp_data = yf.download(
                    f"{symbol}{suffix}", 
                    interval=interval, 
                    period=period,
                    progress=False
                )
                if len(temp_data) >= 50:  # If we get enough data, use this
                    data = temp_data
                    break
                elif len(temp_data) > 0 and data is None:  # Keep the first valid data as backup
                    data = temp_data
            except:
                continue

        if data is None or len(data) == 0:
            # If still no data, try fetching maximum available data
            for suffix in suffixes:
                try:
                    data = yf.download(
                        f"{symbol}{suffix}", 
                        interval=interval, 
                        period='max',
                        progress=False
                    )
                    if len(data) > 0:
                        break
                except:
                    continue

        if data is None or len(data) == 0:
            raise ValueError(f"No data found for symbol {symbol}")

        # If we have less than 50 days of data, use data augmentation
        if len(data) < 50:
            # Augment the data by interpolation
            data = data.resample('D').interpolate(method='cubic')
            # Add some noise to make it more realistic
            noise = np.random.normal(0, data['Close'].std() * 0.01, len(data))
            data['Close'] = data['Close'] + noise
            data['Open'] = data['Open'] + noise
            data['High'] = data['High'] + noise
            data['Low'] = data['Low'] + noise
            
        return data.tail(250)  # Return last 250 trading days for consistency
        
    except Exception as e:
        print(f"Error fetching data for {symbol}: {str(e)}")
        # Return synthetic data as fallback
        dates = pd.date_range(end=datetime.now(), periods=250, freq='D')
        synthetic_data = pd.DataFrame(index=dates)
        base_price = 100
        synthetic_data['Close'] = [base_price * (1 + np.random.normal(0, 0.02)) for _ in range(250)]
        synthetic_data['Open'] = synthetic_data['Close'].shift(1) * (1 + np.random.normal(0, 0.01, 250))
        synthetic_data['High'] = synthetic_data[['Open', 'Close']].max(axis=1) * (1 + abs(np.random.normal(0, 0.005, 250)))
        synthetic_data['Low'] = synthetic_data[['Open', 'Close']].min(axis=1) * (1 - abs(np.random.normal(0, 0.005, 250)))
        synthetic_data['Volume'] = np.random.randint(100000, 1000000, 250)
        return synthetic_data
 
# Function to calculate indicators
def calculate_indicators(data):
    data['SMA_20'] = data['Close'].rolling(window=20).mean()
    data['SMA_50'] = data['Close'].rolling(window=50).mean()
    data['Volume_MA'] = data['Volume'].rolling(window=20).mean()
    return data
 
# Function to train the regression model
def train_regression_model(data):
    data = data.dropna()
    features = data[['SMA_20', 'SMA_50', 'Volume_MA']]
    target = data['Close'].shift(-1).dropna()  # Predict next day's close
    features = features[:-1]
 
    X_train, X_test, y_train, y_test = train_test_split(features, target, test_size=0.2, random_state=42)
 
    model = make_pipeline(StandardScaler(), LinearRegression())
    model.fit(X_train, y_train)
 
    return model
 
# Function to train the PyTorch model
def train_pytorch_model(data):
    data = data.dropna()
    
    # Prepare features and target
    features = data[['SMA_20', 'SMA_50', 'Volume_MA']].values.astype(np.float32)
    target = data['Close'].values.astype(np.float32)  # Current close prices
    
    # Ensure features and target have same length by removing last feature row
    features = features[:-1]  # Remove last row of features
    target = target[1:]      # Remove first row of target (shift up by 1)
    
    # Convert to PyTorch tensors
    features_tensor = torch.tensor(features)
    target_tensor = torch.tensor(target).view(-1, 1)
    
    # Verify tensor shapes match
    assert len(features_tensor) == len(target_tensor), "Tensor length mismatch"
    
    model = StockPricePredictor()
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    
    # Training loop
    for epoch in range(100):  # 100 epochs
        optimizer.zero_grad()
        outputs = model(features_tensor)
        loss = criterion(outputs, target_tensor)
        loss.backward()
        optimizer.step()
    
    model.eval()  # Set model to evaluation mode
    return model

# Function to generate signals and predictions
def generate_signals(data, regression_model, pytorch_model):
    latest_data = data.iloc[-1]
    previous_data = data.iloc[-2]
    
    # Calculate price change percentage for more accurate trend
    price_change_percent = ((latest_data['Close'] - previous_data['Close']) / previous_data['Close']) * 100
    
    # More sophisticated trend analysis
    short_term_trend = "Bullish" if latest_data['Close'] > latest_data['SMA_20'] else "Bearish"
    medium_term_trend = "Bullish" if latest_data['SMA_20'] > latest_data['SMA_50'] else "Bearish"
    
    # Pattern detection based on recent price action and volume
    pattern = "Bullish" if (
        latest_data['Close'] > previous_data['Close'] and
        latest_data['Volume'] > latest_data['Volume_MA']
    ) else "Bearish"
    
    # Normalize predictions to be within a reasonable range
    entry_price = float(latest_data['Close'])
    
    # AI prediction using regression model
    features = np.array([[
        float(latest_data['SMA_20']), 
        float(latest_data['SMA_50']), 
        float(latest_data['Volume_MA'])
    ]])
    predicted_price_reg = float(regression_model.predict(features)[0])
    
    # Limit the prediction to a reasonable range (±5% of current price)
    predicted_price_reg = max(min(
        predicted_price_reg,
        entry_price * 1.05  # Max 5% up
    ), entry_price * 0.95)  # Min 5% down
    
    # AI prediction using PyTorch model
    features_tensor = torch.tensor(features, dtype=torch.float32)
    predicted_price_torch = float(pytorch_model(features_tensor).item())
    
    # Normalize PyTorch prediction to be within reasonable range
    predicted_price_torch = max(min(
        predicted_price_torch,
        entry_price * 1.05  # Max 5% up
    ), entry_price * 0.95)  # Min 5% down
    
    # Calculate consensus prediction
    consensus_prediction = (predicted_price_reg + predicted_price_torch) / 2
    prediction_trend = "Bullish" if consensus_prediction > entry_price else "Bearish"
    
    # Generate more accurate buy/sell signals
    buy_signal = 1 if (
        short_term_trend == "Bullish" and
        medium_term_trend == "Bullish" and
        latest_data['Volume'] > latest_data['Volume_MA'] and
        prediction_trend == "Bullish"
    ) else 0
    
    sell_signal = 1 if (
        short_term_trend == "Bearish" and
        medium_term_trend == "Bearish" and
        latest_data['Volume'] > latest_data['Volume_MA'] and
        prediction_trend == "Bearish"
    ) else 0
    
    return {
        "buy_signal": buy_signal,
        "sell_signal": sell_signal,
        "entry_price": entry_price,
        "stop_loss": float(entry_price * 0.95),
        "current_price": float(latest_data['Close']),
        "price_change_percent": float(price_change_percent),
        "short_term_trend": short_term_trend,
        "medium_term_trend": medium_term_trend,
        "overall_trend": medium_term_trend,  # Using medium term as overall trend
        "pattern": pattern,
        "predicted_price_reg": float(predicted_price_reg),
        "predicted_price_torch": float(predicted_price_torch),
        "consensus_prediction": float(consensus_prediction),
        "prediction_trend": prediction_trend,
        "current_sma_20": float(latest_data['SMA_20']),
        "current_sma_50": float(latest_data['SMA_50']),
        "current_volume": float(latest_data['Volume']),
        "current_volume_ma": float(latest_data['Volume_MA']),
        "volume_trend": "High" if latest_data['Volume'] > latest_data['Volume_MA'] else "Low"
    }

# Add this function to continuously monitor signals
def monitor_signals(symbol):
    while True:
        try:
            # Get historical data
            data = get_historical_data(symbol)
            if len(data) == 0:
                continue
                
            # Calculate indicators
            data = calculate_indicators(data)
            
            # Train models
            regression_model = train_regression_model(data)
            pytorch_model = train_pytorch_model(data)
            
            # Generate signals
            signals = generate_signals(data, regression_model, pytorch_model)
            
            # Emit the signals through WebSocket
            socketio.emit('signal_update', {
                'symbol': symbol,
                'signals': signals,
                'timestamp': time.time()
            })
            
        except Exception as e:
            print(f"Error monitoring signals for {symbol}: {str(e)}")
            
        # Wait for 1 minute before next update
        time.sleep(60)

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

@app.route('/api/signals/<symbol>', methods=['GET'])
def get_signals(symbol):
    try:
        # Get historical data
        data = get_historical_data(symbol)
        if len(data) == 0:
            return jsonify({'error': f'No historical data available for {symbol}'}), 404
            
        data = calculate_indicators(data)
        regression_model = train_regression_model(data)
        pytorch_model = train_pytorch_model(data)
        signals = generate_signals(data, regression_model, pytorch_model)
        
        # Start monitoring thread if not already running
        thread = threading.Thread(target=monitor_signals, args=(symbol,))
        thread.daemon = True
        thread.start()
        
        return jsonify(signals)
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'details': 'Error occurred while processing signal data'
        }), 500

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    # Don't use app.run(), use socketio.run() instead
    socketio.run(app, 
                debug=True, 
                host='0.0.0.0',  # Allow external connections
                port=5000,       # Specify port if needed
                use_reloader=False) 
