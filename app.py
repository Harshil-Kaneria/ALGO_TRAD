import eventlet
eventlet.monkey_patch()
import talib
import time
import argparse
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
from typing import List, Dict
from scipy import stats

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

load_dotenv()

ENCTOKEN = os.getenv('ENCTOKEN')
KITE_API_KEY = "TradeViaPython"

# Global variable to hold the KiteApp instance
kite_instance = KiteApp(enctoken=ENCTOKEN)

# Define a simple neural network model
class StockPricePredictor(nn.Module):
    def __init__(self):
        super(StockPricePredictor, self).__init__()
        self.layer1 = nn.Linear(3, 64)
        self.layer2 = nn.Linear(64, 32)
        self.layer3 = nn.Linear(32, 16)
        self.layer4 = nn.Linear(16, 1)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.2)
        
    def forward(self, x):
        x = self.relu(self.layer1(x))
        x = self.dropout(x)
        x = self.relu(self.layer2(x))
        x = self.dropout(x)
        x = self.relu(self.layer3(x))
        x = self.layer4(x)
        return x

class CandlePatternDetector:
    def __init__(self):
        self.patterns = {
            'DOJI': talib.CDLDOJI,
            'HAMMER': talib.CDLHAMMER,
            'SHOOTING_STAR': talib.CDLSHOOTINGSTAR,
            'ENGULFING': talib.CDLENGULFING,
            'MORNING_STAR': talib.CDLMORNINGSTAR,
            'EVENING_STAR': talib.CDLEVENINGSTAR,
            'THREE_WHITE_SOLDIERS': talib.CDL3WHITESOLDIERS,
            'THREE_BLACK_CROWS': talib.CDL3BLACKCROWS
        }

    def detect_patterns(self, df: pd.DataFrame) -> Dict[str, int]:
        results = {}
        for pattern_name, pattern_func in self.patterns.items():
            pattern_value = pattern_func(
                df['Open'].values,
                df['High'].values,
                df['Low'].values,
                df['Close'].values
            )[-1]
            # Convert numpy.int32 to Python int
            results[pattern_name] = int(pattern_value)
        return results

def get_kite_instance():
    return kite_instance

def convert_to_native_types(obj):
    """Convert numpy/pandas data types to native Python types for JSON serialization"""
    if isinstance(obj, dict):
        return {key: convert_to_native_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_native_types(item) for item in obj]
    elif isinstance(obj, (np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj

def is_market_open():
    now = datetime.now()
    return True
    return now.weekday() < 5 and datetime.time(9, 15) <= now.time() <= datetime.time(15, 30)

def calculate_target_price(entry_price, target_profit_percentage):
    return entry_price * (1 + target_profit_percentage / 100)

def calculate_advanced_pivot(previous_high, previous_low, previous_close):
    try:
        # Convert inputs to float if they're not already
        previous_high = float(previous_high)
        previous_low = float(previous_low)
        previous_close = float(previous_close)
        
        # Calculate pivot point
        pp = (previous_high + previous_low + previous_close) / 3
        
        # Calculate support and resistance levels
        s1 = (2 * pp) - previous_high
        s2 = pp - (previous_high - previous_low)
        s3 = previous_low - 2 * (previous_high - pp)
        
        r1 = (2 * pp) - previous_low
        r2 = pp + (previous_high - previous_low)
        r3 = previous_high + 2 * (pp - previous_low)
        
        return {
            'pp': float(pp),
            'r1': float(r1), 'r2': float(r2), 'r3': float(r3),
            's1': float(s1), 's2': float(s2), 's3': float(s3)
        }
    except Exception as e:
        print(f"Error calculating pivot points: {e}")
        # Return default values if calculation fails
        return {
            'pp': 0.0,
            'r1': 0.0, 'r2': 0.0, 'r3': 0.0,
            's1': 0.0, 's2': 0.0, 's3': 0.0
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
        for row in table.find_all('tr')[1:10]:  # Get top 10 gainers
            cells = row.find_all('td')
            if len(cells) >= 4:
                try:
                    # Get the ticker symbol
                    ticker = yf.Ticker(cells[0].text.strip().split()[0])
                    info = ticker.info
                    
                    # Get historical data for pivot point calculation
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=365)  # Get 5 days of data
                    hist = ticker.history(start=start_date, end=end_date, interval='1d')
                    
                    if len(hist) < 2:
                        print(f"Not enough historical data for {cells[0].text.strip()}")
                        continue
                    
                    # Calculate pivot points using the previous day's data
                    previous_day = hist.iloc[-2]
                    pivot_points = calculate_advanced_pivot(
                        previous_day['High'], 
                        previous_day['Low'], 
                        previous_day['Close']
                    )
                    
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
                    
                except Exception as e:
                    print(f"Error processing stock {cells[0].text.strip()}: {str(e)}")
                    continue

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

# Add technical indicators calculation function
def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    try:
        # Convert price and volume columns to float64
        numeric_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in numeric_columns:
            df[col] = df[col].astype('float64')
        
        # Calculate SMAs first
        df['SMA_20'] = df['Close'].rolling(window=20, min_periods=1).mean()
        df['SMA_50'] = df['Close'].rolling(window=50, min_periods=1).mean()
        df['Volume_MA'] = df['Volume'].rolling(window=20, min_periods=1).mean()
        
        # Basic indicators
        df['RSI'] = talib.RSI(df['Close'].values, timeperiod=14)
        df['MACD'], df['MACD_Signal'], df['MACD_Hist'] = talib.MACD(
            df['Close'].values, fastperiod=12, slowperiod=26, signalperiod=9
        )
        
        # Volume indicators
        df['OBV'] = talib.OBV(df['Close'].values, df['Volume'].values)
        df['ADL'] = talib.AD(df['High'].values, df['Low'].values, 
                            df['Close'].values, df['Volume'].values)
        
        # Volatility indicators
        df['ATR'] = talib.ATR(df['High'].values, df['Low'].values, 
                             df['Close'].values, timeperiod=14)
        df['BBANDS_Upper'], df['BBANDS_Middle'], df['BBANDS_Lower'] = talib.BBANDS(
            df['Close'].values, timeperiod=20
        )
        
        # Momentum indicators
        df['MOM'] = talib.MOM(df['Close'].values, timeperiod=10)
        df['ROC'] = talib.ROC(df['Close'].values, timeperiod=10)
        
        # Handle NaN values
        df = df.ffill().bfill()
        
        # Print column names for debugging
        print(f"Available columns: {df.columns.tolist()}")
        
        return df
    except Exception as e:
        print(f"Error in calculate_technical_indicators: {str(e)}")
        return df

class RealTimeStore:
    def __init__(self):
        self._data = {}
        self._callbacks = {}

    def update_data(self, symbol: str, data: dict):
        self._data[symbol] = data
        # Trigger callbacks if any
        if symbol in self._callbacks:
            for callback in self._callbacks[symbol]:
                callback(data)

    def get_data(self, symbol: str) -> dict:
        return self._data.get(symbol)

    def add_callback(self, symbol: str, callback):
        if symbol not in self._callbacks:
            self._callbacks[symbol] = []
        self._callbacks[symbol].append(callback)

# Create a global instance
realtime_store = RealTimeStore()

# Modify get_historical_data for 5-min candles
def get_historical_data(symbol, interval='5minute', days=30):
    try:
        kite = get_kite_instance()
        if not kite:
            raise ValueError("KiteApp instance is not initialized")
        
        # Find instrument token
        instrument_token = None
        try:
            instruments = kite.instruments("NSE")
            for instrument in instruments:
                if instrument['tradingsymbol'] == symbol:
                    instrument_token = instrument['instrument_token']
                    break
                    
            if not instrument_token:
                # Try with common stock suffixes
                for suffix in ['', '-EQ', '.NS']:
                    modified_symbol = symbol + suffix
                    for instrument in instruments:
                        if instrument['tradingsymbol'] == modified_symbol:
                            instrument_token = instrument['instrument_token']
                            break
                    if instrument_token:
                        break
        except Exception as e:
            print(f"Error finding instrument token: {e}")
            raise ValueError(f"Could not find instrument token for {symbol}")
        
        if not instrument_token:
            raise ValueError(f"Instrument token not found for {symbol}")
            
        print(f"Found instrument token {instrument_token} for {symbol}")  # Debug print
        
        # Get historical 15-minute data
        from_date = datetime.now() - timedelta(days=days)
        to_date = datetime.now()
        
        historical_data = kite.historical_data(
            instrument_token,
            from_date,
            to_date,
            interval
        )
        
        if not historical_data:
            raise ValueError(f"No historical data returned for {symbol}")
        
        # Convert to DataFrame and standardize column names
        df = pd.DataFrame(historical_data)
        df.set_index('date', inplace=True)
        
        # Rename columns to match expected format
        df = df.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        })
        
        # Add real-time data if available
        realtime_data = realtime_store.get_data(symbol)
        if realtime_data:
            # Ensure realtime data has matching column names
            realtime_df = pd.DataFrame([{
                'Open': realtime_data.get('open', realtime_data.get('Open')),
                'High': realtime_data.get('high', realtime_data.get('High')),
                'Low': realtime_data.get('low', realtime_data.get('Low')),
                'Close': realtime_data.get('close', realtime_data.get('Close')),
                'Volume': realtime_data.get('volume', realtime_data.get('Volume'))
            }])
            df = pd.concat([df, realtime_df])
        
        # Calculate technical indicators
        df = calculate_technical_indicators(df)
        
        if df.empty:
            raise ValueError(f"No data available for {symbol}")
            
        print(f"Successfully fetched data for {symbol} with shape {df.shape}")  # Debug print
        return df
        
    except Exception as e:
        print(f"Error fetching data for {symbol}: {str(e)}")
        # Return empty DataFrame instead of None
        return pd.DataFrame()

# Add market sentiment analysis
def analyze_market_sentiment(df: pd.DataFrame) -> Dict:
    latest = df.iloc[-1]
    
    # Volume analysis
    volume_sma = df['Volume'].rolling(window=20).mean().iloc[-1]
    volume_trend = "High" if latest['Volume'] > volume_sma else "Low"
    
    # Trend strength
    adx = talib.ADX(df['High'].values, df['Low'].values, df['Close'].values, timeperiod=14)[-1]
    trend_strength = "Strong" if adx > 25 else "Weak" if adx > 20 else "No Trend"
    
    # Volatility
    current_atr = latest['ATR']
    avg_atr = df['ATR'].mean()
    volatility = "High" if current_atr > avg_atr else "Low"
    
    return {
        "volume_trend": volume_trend,
        "trend_strength": trend_strength,
        "volatility": volatility,
        "adx": float(adx)  # Convert numpy.float64 to Python float
    }

class EnhancedPredictor:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.pattern_detector = CandlePatternDetector()
        
    def get_prediction(self) -> Dict:
        latest = self.df.iloc[-1]
        patterns = self.pattern_detector.detect_patterns(self.df)
        sentiment = analyze_market_sentiment(self.df)
        
        # Calculate probability based on multiple factors
        bullish_factors = 0
        bearish_factors = 0
        
        # Pattern analysis
        for pattern, value in patterns.items():
            if value > 0:
                bullish_factors += 1
            elif value < 0:
                bearish_factors += 1
        
        # Technical indicator analysis
        if latest['RSI'] > 70:
            bearish_factors += 1
        elif latest['RSI'] < 30:
            bullish_factors += 1
            
        if latest['MACD'] > latest['MACD_Signal']:
            bullish_factors += 1
        else:
            bearish_factors += 1
            
        if latest['Close'] > latest['BBANDS_Upper']:
            bearish_factors += 1
        elif latest['Close'] < latest['BBANDS_Lower']:
            bullish_factors += 1
            
        # Volume analysis
        if sentiment['volume_trend'] == "High":
            if latest['Close'] > latest['Open']:
                bullish_factors += 1
            else:
                bearish_factors += 1
                
        # Calculate probability
        total_factors = bullish_factors + bearish_factors
        if total_factors == 0:
            probability = 0.5
        else:
            probability = bullish_factors / total_factors
            
        # Predict price movement
        atr = latest['ATR']
        current_price = latest['Close']
        
        predicted_movement = (probability - 0.5) * 2 * atr
        predicted_price = current_price + predicted_movement
        
        return {
            "current_price": float(current_price),
            "predicted_price": float(predicted_price),
            "probability": float(probability),
            "confidence": "High" if abs(probability - 0.5) > 0.3 else "Medium" if abs(probability - 0.5) > 0.15 else "Low",
            "patterns": {k: int(v) for k, v in patterns.items()},
            "sentiment": {k: float(v) if isinstance(v, (np.int32, np.int64, np.float32, np.float64)) else v 
                         for k, v in sentiment.items()},
            "technical_signals": {
                "rsi": float(latest['RSI']),
                "macd": float(latest['MACD']),
                "macd_signal": float(latest['MACD_Signal']),
                "momentum": float(latest['MOM'])
            }
        }


# Function to calculate indicators
def calculate_indicators(data):
    try:
        # Make a copy to avoid modifying the original data
        df = data.copy()
        
        # Convert all relevant columns to float64
        numeric_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Calculate indicators
        df['SMA_20'] = df['Close'].rolling(window=20, min_periods=1).mean()
        df['SMA_50'] = df['Close'].rolling(window=50, min_periods=1).mean()
        df['Volume_MA'] = df['Volume'].rolling(window=20, min_periods=1).mean()
        
        # Handle any remaining NaN values
        df = df.fillna(method='ffill').fillna(method='bfill')
        
        # If still have NaN values after forward/backward fill, fill with mean
        df = df.fillna(df.mean())
        
        return df
        
    except Exception as e:
        print(f"Error in calculate_indicators: {str(e)}")
        return data  # Return original data if calculation fails

# Function to train the regression model
def train_regression_model(data):
    try:
        # Handle NaN values first
        data = data.copy()
        data = data.ffill().bfill()
        
        # Prepare features with proper column names
        feature_columns = ['SMA_20', 'SMA_50', 'Volume_MA']
        
        # Ensure all feature columns exist
        for col in feature_columns:
            if col not in data.columns:
                if 'SMA' in col:
                    window = int(col.split('_')[1])
                    data[col] = data['Close'].rolling(window=window, min_periods=1).mean()
                else:
                    data[col] = data['Volume'].rolling(window=20, min_periods=1).mean()
        
        # Forward fill any remaining NaN values
        data = data.ffill().bfill()
        
        # Convert to numpy arrays and ensure float64 dtype
        X = data[feature_columns].values.astype(np.float64)
        y = data['Close'].values.astype(np.float64)
        
        # Additional check for NaN values
        if np.isnan(X).any() or np.isnan(y).any():
            print("Warning: NaN values found after preprocessing")
            # Remove rows with NaN values
            mask = ~np.isnan(X).any(axis=1) & ~np.isnan(y)
            X = X[mask]
            y = y[mask]
        
        # Ensure we have enough data to train
        if len(X) < 2:
            raise ValueError("Not enough valid data points for training")
        
        # Use last 80% of data for training
        train_size = int(len(X) * 0.8)
        X_train = X[-train_size:]
        y_train = y[-train_size:]
        
        # Create and fit the pipeline
        pipeline = make_pipeline(
            StandardScaler(),
            LinearRegression()
        )
        
        pipeline.fit(X_train, y_train)
        return pipeline
        
    except Exception as e:
        print(f"Error in train_regression_model: {str(e)}")
        return make_pipeline(StandardScaler(), LinearRegression())

# Function to train the PyTorch model
def train_pytorch_model(data):
    model = StockPricePredictor()
    
    # Prepare features and target
    feature_columns = ['SMA_20', 'SMA_50', 'Volume_MA']
    X = data[feature_columns].values.astype(np.float32)
    y = data['Close'].values.astype(np.float32)
    
    # Use last 80% of data for training
    train_size = int(len(data) * 0.8)
    X_train = X[-train_size:]
    y_train = y[-train_size:]
    
    # Convert to tensors
    X_tensor = torch.tensor(X_train)
    y_tensor = torch.tensor(y_train)
    
    # Train the model
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    model.train()
    for epoch in range(100):
        optimizer.zero_grad()
        outputs = model(X_tensor)
        loss = criterion(outputs.squeeze(), y_tensor)
        loss.backward()
        optimizer.step()
    
    model.eval()
    return model

# Function to generate signals and predictions
def generate_signals(data, regression_model, pytorch_model):
    try:
        latest_data = data.iloc[-1]
        print(f"Latest data: {latest_data}")  # Debug print

        kite = get_kite_instance()
        
        # Extract symbol correctly from the data
        try:
            # First try to get symbol from the index name if it's a string
            if isinstance(latest_data.name, str):
                symbol = latest_data.name.split(':')[-1]
            else:
                # If index is a timestamp, try to get symbol from the data columns or parameters
                # You might need to pass the symbol separately to this function
                symbol = data.columns[0].split(':')[0] if ':' in data.columns[0] else None
                
            if not symbol:
                # Fallback: try to get symbol from the first column name
                symbol = data.columns[0].split('_')[0] if '_' in data.columns[0] else data.columns[0]
            
            symbol_with_exchange = f"NSE:{symbol}"
            
            # Try to get real-time price
            ltp_data = kite.ltp([symbol_with_exchange])
            current_price = ltp_data[symbol_with_exchange]['last_price']
            print(f"Real-time price fetched: {current_price}")
            
        except Exception as price_error:
            print(f"Error getting real-time price: {price_error}")
            # Fallback to the last price from historical data
            current_price = float(latest_data['Close'])
            print(f"Using historical price: {current_price}")
        
        # Calculate technical indicators and patterns
        pattern_detector = CandlePatternDetector()
        patterns = pattern_detector.detect_patterns(data)
        sentiment = analyze_market_sentiment(data)
        
        # Enhanced prediction logic
        predictor = EnhancedPredictor(data)
        prediction = predictor.get_prediction()
        
        print(f"Generated prediction: {prediction}")  # Debug print
        
        return {
            "buy_signal": bool(prediction['probability'] > 0.7 and prediction['confidence'] == "High"),
            "sell_signal": bool(prediction['probability'] < 0.3 and prediction['confidence'] == "High"),
            "entry_price": float(latest_data['Close']),
            "current_price": float(latest_data['Close']),
            "patterns": {k: float(v) if isinstance(v, (np.int32, np.int64, np.float32, np.float64)) else v 
                        for k, v in patterns.items()},
            "trend_analysis": {
                "short_term": "Bullish" if prediction['probability'] > 0.6 else "Bearish",
                "medium_term": "Bullish" if prediction['probability'] > 0.55 else "Bearish",
                "long_term": "Bullish" if prediction['probability'] > 0.5 else "Bearish"
            },
            "predictions": {
                k: float(v) if isinstance(v, (np.int32, np.int64, np.float32, np.float64)) else v 
                for k, v in prediction.items()
            },
            "technical_signals": {
                "rsi": float(latest_data['RSI']),
                "macd": float(latest_data['MACD']),
                "macd_signal": float(latest_data['MACD_Signal']),
                "momentum": float(latest_data['MOM'])
            },
            "market_context": {
                k: float(v) if isinstance(v, (np.int32, np.int64, np.float32, np.float64)) else v 
                for k, v in sentiment.items()
            },
            "indicators": {
                "rsi": float(latest_data['RSI']),
                "macd": {
                    "value": float(latest_data['MACD']),
                    "signal": float(latest_data['MACD_Signal']),
                    "histogram": float(latest_data['MACD_Hist'])
                },
                "bollinger_bands": {
                    "upper": float(latest_data['BBANDS_Upper']),
                    "middle": float(latest_data['BBANDS_Middle']),
                    "lower": float(latest_data['BBANDS_Lower'])
                }
            },
            "volume": {
                "current": float(latest_data['Volume']),
                "average": float(data['Volume'].mean()),
                "trend": "Above Average" if latest_data['Volume'] > data['Volume'].mean() else "Below Average"
            },
            "momentum": {
                "value": float(latest_data['MOM']),
                "roc": float(latest_data['ROC'])
            }
        }
        
    except Exception as e:
        print(f"Error in generate_signals: {str(e)}")
        return None

# Add this function to continuously monitor signals
def monitor_signals(symbol):
    def on_tick_update(tick_data):
        try:
            # Get 15-minute candle data
            data = get_historical_data(symbol)
            if len(data) == 0:
                return
                
            # Generate predictions
            predictor = EnhancedPredictor(data)
            prediction = predictor.get_prediction()
            
            # Generate trading signals
            signals = {
                "buy_signal": int(prediction['probability'] > 0.7 and prediction['confidence'] == "High"),
                "sell_signal": int(prediction['probability'] < 0.3 and prediction['confidence'] == "High"),
                "prediction": prediction,
                "timestamp": datetime.now().isoformat()
            }
            
            # Emit the signals through WebSocket
            socketio.emit('signal_update', {
                'symbol': symbol,
                'signals': signals
            })
            
        except Exception as e:
            print(f"Error monitoring signals for {symbol}: {str(e)}")

    # Register callback for real-time updates
    realtime_store.add_callback(symbol, on_tick_update)

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
            datetime.now() - datetime.timedelta(days=365),
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
        start_date = end_date - timedelta(days=365)
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
        if data.empty:
            return jsonify({'error': f'No historical data available for {symbol}'}), 404
            
        # Calculate indicators
        data = calculate_technical_indicators(data)
        
        # Train models
        regression_model = train_regression_model(data)
        pytorch_model = train_pytorch_model(data)
        
        # Generate signals with the symbol
        signals = generate_signals(data, regression_model, pytorch_model)
        
        if signals is None:
            return jsonify({'error': 'Unable to generate signals'}), 500
            
        # Convert numpy values to native types
        signals = convert_to_native_types(signals)
        
        # Emit through WebSocket
        socketio.emit('signal_update', {
            'symbol': symbol,
            'signals': signals
        })
        
        return jsonify(signals)
        
    except Exception as e:
        print(f"Error in get_signals for {symbol}: {str(e)}")
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

def get_top_50_nse_symbols():
    try:
        # List of top 50 NSE companies by market cap (Nifty 50 constituents)
        nifty50_symbols = [
            'RELIANCE', 'TCS', 'HDFCBANK', 'ICICIBANK', 'HINDUNILVR', 
            'INFY', 'ITC', 'SBIN', 'BHARTIARTL', 'HDFC', 'KOTAKBANK', 
            'LT', 'BAJFINANCE', 'ASIANPAINT', 'AXISBANK', 'MARUTI', 
            'TITAN', 'SUNPHARMA', 'WIPRO', 'ULTRACEMCO', 'NESTLEIND', 
            'POWERGRID', 'TATAMOTORS', 'ADANIENT', 'NTPC', 'BAJAJFINSV',
            'HCLTECH', 'M&M', 'TECHM', 'COALINDIA', 'HINDALCO', 'JSWSTEEL',
            'TATASTEEL', 'GRASIM', 'INDUSINDBK', 'APOLLOHOSP', 'ADANIPORTS',
            'CIPLA', 'DRREDDY', 'BRITANNIA', 'SBILIFE', 'EICHERMOT',
            'DIVISLAB', 'BAJAJ-AUTO', 'TATACONSUM', 'UPL', 'HEROMOTOCO',
            'HINDUNILVR', 'ONGC', 'BPCL'
        ]
        return nifty50_symbols
    except Exception as e:
        print(f"Error getting top 50 symbols: {str(e)}")
        return []

def generate_stock_analysis():
    try:
        print("Starting stock analysis...")
        
        kite = get_kite_instance()
        if not kite:
            raise ValueError("KiteApp instance not initialized")
            
        instruments = kite.instruments("NSE")
        top_50_symbols = get_top_50_nse_symbols()
        
        filtered_instruments = [
            instrument for instrument in instruments 
            if instrument['tradingsymbol'] in top_50_symbols
        ]
        
        print(f"Processing {len(filtered_instruments)} top companies...")

        analysis_results = []
        
        for idx, instrument in enumerate(filtered_instruments):
            try:
                symbol = instrument['tradingsymbol']
                print(f"Processing {idx + 1}/{len(filtered_instruments)}: {symbol}")
                
                data = get_historical_data(symbol)
                if data.empty:
                    continue
                    
                data = calculate_technical_indicators(data)
                regression_model = train_regression_model(data)
                pytorch_model = train_pytorch_model(data)
                signals = generate_signals(data, regression_model, pytorch_model)
                
                if signals is None:
                    continue
                
                signals = convert_to_native_types(signals)
                
                # Enhanced analysis result with all data points
                analysis_result = {
                    'Symbol': symbol,
                    'Current Price': float(signals['current_price']),
                    'Entry Price': float(signals['entry_price']),
                    # Convert boolean values to 1 or 0
                    'Buy Signal': 1 if signals['buy_signal'] else 0,
                    'Sell Signal': 1 if signals['sell_signal'] else 0,
                    
                    # Predictions
                    'Predicted Price': float(signals['predictions']['predicted_price']),
                    'Prediction Probability': float(signals['predictions']['probability']),
                    'Prediction Confidence': signals['predictions']['confidence'],
                    
                    # Technical Indicators
                    'RSI': float(signals['technical_signals']['rsi']),
                    'MACD': float(signals['technical_signals']['macd']),
                    'MACD Signal': float(signals['technical_signals']['macd_signal']),
                    'Momentum': float(signals['technical_signals']['momentum']),
                    
                    # Bollinger Bands
                    'BB Upper': float(signals['indicators']['bollinger_bands']['upper']),
                    'BB Middle': float(signals['indicators']['bollinger_bands']['middle']),
                    'BB Lower': float(signals['indicators']['bollinger_bands']['lower']),
                    
                    # Market Context
                    'ADX': float(signals['market_context']['adx']),
                    'Trend Strength': signals['market_context']['trend_strength'],
                    'Volatility': signals['market_context']['volatility'],
                    'Volume Trend': signals['market_context']['volume_trend'],
                    
                    # Momentum Indicators
                    'ROC': float(signals['momentum']['roc']),
                    'Momentum Value': float(signals['momentum']['value']),
                    
                    # Candlestick Patterns - Convert to 1 or 0
                    'Pattern_DOJI': 1 if signals['patterns']['DOJI'] != 0 else 0,
                    'Pattern_ENGULFING': 1 if signals['patterns']['ENGULFING'] != 0 else 0,
                    'Pattern_EVENING_STAR': 1 if signals['patterns']['EVENING_STAR'] != 0 else 0,
                    'Pattern_HAMMER': 1 if signals['patterns']['HAMMER'] != 0 else 0,
                    'Pattern_MORNING_STAR': 1 if signals['patterns']['MORNING_STAR'] != 0 else 0,
                    'Pattern_SHOOTING_STAR': 1 if signals['patterns']['SHOOTING_STAR'] != 0 else 0,
                    'Pattern_THREE_BLACK_CROWS': 1 if signals['patterns']['THREE_BLACK_CROWS'] != 0 else 0,
                    'Pattern_THREE_WHITE_SOLDIERS': 1 if signals['patterns']['THREE_WHITE_SOLDIERS'] != 0 else 0,
                    
                    # Trend Analysis - Convert to 1 or 0
                    'Short Term Trend': 1 if signals['trend_analysis']['short_term'] == 'Bullish' else 0,
                    'Medium Term Trend': 1 if signals['trend_analysis']['medium_term'] == 'Bullish' else 0,
                    'Long Term Trend': 1 if signals['trend_analysis']['long_term'] == 'Bullish' else 0,
                    
                    # Volume Analysis
                    'Current Volume': float(signals['volume']['current']),
                    'Average Volume': float(signals['volume']['average']),
                    'Volume Above Average': 1 if signals['volume']['current'] > signals['volume']['average'] else 0
                }
                
                analysis_results.append(analysis_result)
                
            except Exception as e:
                print(f"Error processing {symbol}: {str(e)}")
                continue
        
        df = pd.DataFrame(analysis_results)
        
        # Enhanced scoring system
        df['Technical Score'] = (
            (df['RSI'].clip(0, 100) / 100 * 0.2) +
            ((df['MACD'] > df['MACD Signal']).astype(float) * 0.2) +
            (df['Prediction Probability'] * 0.3) +
            (df['Current Volume'] > df['Average Volume']).astype(float) * 0.15 +
            ((df['Short Term Trend'] == 'Bullish').astype(float) * 0.15)
        )
        
        df_sorted = df.sort_values('Technical Score', ascending=False)

        boolean_columns = [
            'Buy Signal', 'Sell Signal', 
            'Pattern_DOJI', 'Pattern_ENGULFING', 'Pattern_EVENING_STAR',
            'Pattern_HAMMER', 'Pattern_MORNING_STAR', 'Pattern_SHOOTING_STAR',
            'Pattern_THREE_BLACK_CROWS', 'Pattern_THREE_WHITE_SOLDIERS',
            'Short Term Trend', 'Medium Term Trend', 'Long Term Trend',
            'Volume Above Average'
        ]
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'stock_analysis_{timestamp}.xlsx'
        
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            df_sorted.to_excel(writer, sheet_name='Analysis', index=False)
            
            workbook = writer.book
            worksheet = writer.sheets['Analysis']

            boolean_format = workbook.add_format({
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'num_format': '0;0;0'  # This ensures numbers are displayed as 0 or 1
            })
            
            # Enhanced formatting
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D8E4BC',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'text_wrap': True
            })
            
            cell_format = workbook.add_format({
                'border': 1,
                'align': 'center',
                'valign': 'vcenter'
            })
            
            # Format headers
            for col_num, value in enumerate(df_sorted.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
            # Add conditional formatting for different columns
            worksheet.conditional_format('B2:B1048576', {
                'type': '3_color_scale',
                'min_color': '#FF9999',
                'mid_color': '#FFFF99',
                'max_color': '#99FF99'
            })
            
            # RSI conditional formatting
            worksheet.conditional_format('I2:I1048576', {
                'type': '3_color_scale',
                'min_value': 0,
                'mid_value': 50,
                'max_value': 100,
                'min_color': '#FF9999',
                'mid_color': '#FFFF99',
                'max_color': '#99FF99'
            })
            
            # Adjust column widths
            for idx, col in enumerate(df_sorted.columns):
                max_length = max(
                    df_sorted[col].astype(str).apply(len).max(),
                    len(str(col))
                )
                worksheet.set_column(idx, idx, max_length + 2)
            
            # Freeze top row
            worksheet.freeze_panes(1, 0)
            
            # Add filters
            worksheet.autofilter(0, 0, len(df_sorted), len(df_sorted.columns) - 1)

            for col_num, col_name in enumerate(df_sorted.columns):
                if col_name in boolean_columns:
                    worksheet.set_column(col_num, col_num, None, boolean_format)
        
        print(f"Analysis complete! Results saved to {filename}")
        return filename
        
    except Exception as e:
        print(f"Error generating stock analysis: {str(e)}")
        return None

if __name__ == '__main__':
    # Create argument parser
    parser = argparse.ArgumentParser(description='Stock Analysis and Trading Application')
    parser.add_argument('--generate', type=str, choices=['true', 'false'], 
                       help='Generate stock analysis report if true')
    
    args = parser.parse_args()
    
    # Check if generate flag is set to true
    if args.generate and args.generate.lower() == 'true':
        print("Generating stock analysis report...")
        generate_stock_analysis()
    else:
        # Run the socket server
        print("Starting socket server...")
        socketio.run(app, debug=True, host='0.0.0.0', port=5000, use_reloader=False)