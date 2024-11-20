import talib
import time
import argparse
from flask import Flask, jsonify, request
from flask_cors import CORS
from kite_trade import KiteApp
from kiteconnect import KiteTicker
import os
from datetime import datetime, timedelta,date
import yfinance as yf
from bs4 import BeautifulSoup
import pandas as pd
from dotenv import load_dotenv
from transformers import pipeline
import requests
from bs4 import BeautifulSoup
import numpy as np
import torch
import torch.nn as nn
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LinearRegression
from typing import Dict
import re

app = Flask(__name__)
CORS(app)

load_dotenv()

ENCTOKEN = os.getenv('ENCTOKEN')

kite_instance = KiteApp(enctoken=ENCTOKEN)

sentiment_analyzer = pipeline("sentiment-analysis", model="yiyanghkust/finbert-tone")

time_frame_mapping = {
    '1': {'interval': 'minute', 'days': 60},
    '3': {'interval': '3minute', 'days': 100},
    '5': {'interval': '5minute', 'days': 100},
    '10': {'interval': '10minute', 'days': 100},
    '15': {'interval': '15minute', 'days': 200},
    '30': {'interval': '30minute', 'days': 200},
    '60': {'interval': '60minute', 'days': 400},
    '1d': {'interval': 'day', 'days': 2000}
}

class StockPricePredictor(nn.Module):
    def __init__(self, input_size):
        super(StockPricePredictor, self).__init__()
        
        # Adjust the first layer to accept dynamic input size
        self.layer1 = nn.Linear(input_size, 64)  # First layer takes 'input_size' features
        self.layer2 = nn.Linear(64, 32)
        self.layer3 = nn.Linear(32, 16)
        self.layer4 = nn.Linear(16, 1)  # Output layer (1 because we're predicting next day's close)
        
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.2)
        
    def forward(self, x):
        # Forward pass with ReLU and Dropout
        x = self.relu(self.layer1(x))
        x = self.dropout(x)
        x = self.relu(self.layer2(x))
        x = self.dropout(x)
        x = self.relu(self.layer3(x))
        x = self.layer4(x)  # Output layer
        return x

class CandlePatternDetector:
    def __init__(self):
        # Updated patterns dictionary with all requested candlestick patterns
        self.patterns = {
            'TWO_CROWS': talib.CDL2CROWS,
            'THREE_BLACK_CROWS': talib.CDL3BLACKCROWS,
            'THREE_INSIDE': talib.CDL3INSIDE,
            'THREE_LINE_STRIKE': talib.CDL3LINESTRIKE,
            'THREE_OUTSIDE': talib.CDL3OUTSIDE,
            'THREE_STARS_IN_SOUTH': talib.CDL3STARSINSOUTH,
            'THREE_WHITE_SOLDIERS': talib.CDL3WHITESOLDIERS,
            'ABANDONED_BABY': talib.CDLABANDONEDBABY,
            'ADVANCE_BLOCK': talib.CDLADVANCEBLOCK,
            'BELT_HOLD': talib.CDLBELTHOLD,
            'BREAKAWAY': talib.CDLBREAKAWAY,
            'CLOSING_MARUBOZU': talib.CDLCLOSINGMARUBOZU,
            'CONCEAL_BABY_SWALL': talib.CDLCONCEALBABYSWALL,
            'COUNTERATTACK': talib.CDLCOUNTERATTACK,
            'DARK_CLOUD_COVER': talib.CDLDARKCLOUDCOVER,
            'DOJI': talib.CDLDOJI,
            'DOJI_STAR': talib.CDLDOJISTAR,
            'DRAGONFLY_DOJI': talib.CDLDRAGONFLYDOJI,
            'ENGULFING': talib.CDLENGULFING,
            'EVENING_DOJI_STAR': talib.CDLEVENINGDOJISTAR,
            'EVENING_STAR': talib.CDLEVENINGSTAR,
            'GAP_SIDE_SIDE_WHITE': talib.CDLGAPSIDESIDEWHITE,
            'GRAVESTONE_DOJI': talib.CDLGRAVESTONEDOJI,
            'HAMMER': talib.CDLHAMMER,
            'HANGING_MAN': talib.CDLHANGINGMAN,
            'HARAMI': talib.CDLHARAMI,
            'HARAMI_CROSS': talib.CDLHARAMICROSS,
            'HIGH_WAVE': talib.CDLHIGHWAVE,
            'HIKKAKE': talib.CDLHIKKAKE,
            'HIKKAKE_MOD': talib.CDLHIKKAKEMOD,
            'HOMING_PIGEON': talib.CDLHOMINGPIGEON,
            'IDENTICAL_3_CROWS': talib.CDLIDENTICAL3CROWS,
            'IN_NECK': talib.CDLINNECK,
            'INVERTED_HAMMER': talib.CDLINVERTEDHAMMER,
            'KICKING': talib.CDLKICKING,
            'KICKING_BY_LENGTH': talib.CDLKICKINGBYLENGTH,
            'LADDER_BOTTOM': talib.CDLLADDERBOTTOM,
            'LONG_LEGGED_DOJI': talib.CDLLONGLEGGEDDOJI,
            'LONG_LINE': talib.CDLLONGLINE,
            'MARUBOZU': talib.CDLMARUBOZU,
            'MATCHING_LOW': talib.CDLMATCHINGLOW,
            'MAT_HOLD': talib.CDLMATHOLD,
            'MORNING_DOJI_STAR': talib.CDLMORNINGDOJISTAR,
            'MORNING_STAR': talib.CDLMORNINGSTAR,
            'ON_NECK': talib.CDLONNECK,
            'PIERCING': talib.CDLPIERCING,
            'RICKSHAW_MAN': talib.CDLRICKSHAWMAN,
            'RISE_FALL_3_METHODS': talib.CDLRISEFALL3METHODS,
            'SEPARATING_LINES': talib.CDLSEPARATINGLINES,
            'SHOOTING_STAR': talib.CDLSHOOTINGSTAR,
            'SHORT_LINE': talib.CDLSHORTLINE,
            'SPINNING_TOP': talib.CDLSPINNINGTOP,
            'STALLED_PATTERN': talib.CDLSTALLEDPATTERN,
            'STICK_SANDWICH': talib.CDLSTICKSANDWICH,
            'TAKURI': talib.CDLTAKURI,
            'TASUKI_GAP': talib.CDLTASUKIGAP,
            'THRUSTING': talib.CDLTHRUSTING,
            'TRISTAR': talib.CDLTRISTAR,
            'UNIQUE_3_RIVER': talib.CDLUNIQUE3RIVER,
            'UPSIDE_GAP_2_CROWS': talib.CDLUPSIDEGAP2CROWS,
            'X_SIDE_GAP_3_METHODS': talib.CDLXSIDEGAP3METHODS
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

class EnhancedPredictor:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.pattern_detector = CandlePatternDetector()
        
    def get_prediction(self) -> Dict:
        try:
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
        except Exception as e:
            print(f"Error: {e}")
            raise

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
            'pp': round(float(pp),2),
            'r1': round(float(r1),2), 'r2': round(float(r2),2), 'r3': round(float(r3),2),
            's1': round(float(s1),2), 's2': round(float(s2),2), 's3': round(float(s3),2)
        }
    except Exception as e:
        print(f"Error calculating pivot points: {e}")
        # Return default values if calculation fails
        return {
            'pp': 0.0,
            'r1': 0.0, 'r2': 0.0, 'r3': 0.0,
            's1': 0.0, 's2': 0.0, 's3': 0.0
        }

def extract_price(price_text):
    """Extract and clean price from text."""
    price_str = re.sub(r"[^0-9.-]", "", price_text)
    return float(price_str) if price_str else 0.0

def get_top_gainers():
    try:
        url = "https://www.moneycontrol.com/stocks/marketstats/nsegainer/index.php"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Failed to fetch data. Status code: {response.status_code}")
            return []

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Locate the table
        table = soup.find('table', {'class': 'mctable1'}) or next(
            (t for t in soup.find_all('table') if any(keyword in t.text.lower() for keyword in ['company', 'price', 'change', '%chg', 'volume'])), 
            None
        )

        if not table:
            print("Could not find the gainers table")
            return []

        gainers = []
        rows = table.find_all('tr')[1:]  # Get all rows except the header
        
        for row in rows:
            if len(gainers) >= 10:  # Stop if we have 10 gainers
                break
            try:
                cols = row.find_all('td')
                if len(cols) < 7:  # Ensure we have enough columns
                    continue

                symbol = cols[0].text.split('Add to')[0].strip()
                current_price = extract_price(cols[3].text)
                price_high = extract_price(cols[1].text)
                price_low = extract_price(cols[2].text)
                price_prev_close = extract_price(cols[4].text)
                price_change = extract_price(cols[5].text)
                change_text = re.sub(r"[^0-9.-]", "", cols[6].text)  # Clean change percentage
                change_percent = float(change_text) if change_text else 0.0

                # Normalize the percentage value
                if abs(change_percent) > 100:
                    change_percent /= 100

                stock_info = {
                    "symbol": symbol,
                    "last_price": current_price,
                    "price_high": price_high,
                    "price_low": price_low,
                    "price_prev_close": price_prev_close,
                    "gain": price_change,
                    "change": f"{change_percent:.2f}%",
                    "pivot_points": calculate_advanced_pivot(current_price * 1.01, current_price * 0.99, current_price),
                    "position": "Above R3" if change_percent > 0 else "Below S3"
                }

                gainers.append({
                    "symbol": symbol,
                    "company": symbol,  # Assuming the company name is the same as symbol
                    "price": f"{current_price:,.2f}",
                    "change": f"+{change_percent:.2f}%",
                    "stock_info": stock_info
                })

            except Exception as e:
                print(f"Error processing row: {str(e)}")
                continue

        return gainers

    except Exception as e:
        print(f"Error in get_top_gainers: {str(e)}")
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
        
        # Overlap Studies
        df['BBANDS_Upper'], df['BBANDS_Middle'], df['BBANDS_Lower'] = talib.BBANDS(df['Close'], timeperiod=20)
        df['DEMA'] = talib.DEMA(df['Close'], timeperiod=10)
        df['EMA'] = talib.EMA(df['Close'], timeperiod=10)
        df['HT_TRENDLINE'] = talib.HT_TRENDLINE(df['Close'])
        df['KAMA'] = talib.KAMA(df['Close'], timeperiod=10)
        df['MA'] = talib.MA(df['Close'], timeperiod=10)
        df['MIDPOINT'] = talib.MIDPOINT(df['Close'], timeperiod=14)
        df['MIDPRICE'] = talib.MIDPRICE(df['High'], df['Low'], timeperiod=14)
        df['SAR'] = talib.SAR(df['High'], df['Low'], acceleration=0.02, maximum=0.2)
        df['SAREXT'] = talib.SAREXT(df['High'], df['Low'])
        df['T3'] = talib.T3(df['Close'], timeperiod=5)
        df['TEMA'] = talib.TEMA(df['Close'], timeperiod=10)
        df['TRIMA'] = talib.TRIMA(df['Close'], timeperiod=10)
        df['WMA'] = talib.WMA(df['Close'], timeperiod=10)
        
        # Momentum Indicators
        df['ADX'] = talib.ADX(df['High'], df['Low'], df['Close'], timeperiod=14)
        df['ADXR'] = talib.ADXR(df['High'], df['Low'], df['Close'], timeperiod=14)
        df['APO'] = talib.APO(df['Close'], fastperiod=12, slowperiod=26)
        df['AROON_Down'], df['AROON_Up'] = talib.AROON(df['High'], df['Low'], timeperiod=14)
        df['AROONOSC'] = talib.AROONOSC(df['High'], df['Low'], timeperiod=14)
        df['BOP'] = talib.BOP(df['Open'], df['High'], df['Low'], df['Close'])
        df['CCI'] = talib.CCI(df['High'], df['Low'], df['Close'], timeperiod=14)
        df['CMO'] = talib.CMO(df['Close'], timeperiod=14)
        df['DX'] = talib.DX(df['High'], df['Low'], df['Close'], timeperiod=14)
        df['MACD'], df['MACD_Signal'], df['MACD_Hist'] = talib.MACD(df['Close'], fastperiod=12, slowperiod=26, signalperiod=9)
        df['MFI'] = talib.MFI(df['High'], df['Low'], df['Close'], df['Volume'], timeperiod=14)
        df['MINUS_DI'] = talib.MINUS_DI(df['High'], df['Low'], df['Close'], timeperiod=14)
        df['MINUS_DM'] = talib.MINUS_DM(df['High'], df['Low'], timeperiod=14)
        df['PLUS_DI'] = talib.PLUS_DI(df['High'], df['Low'], df['Close'], timeperiod=14)
        df['PLUS_DM'] = talib.PLUS_DM(df['High'], df['Low'], timeperiod=14)
        df['PPO'] = talib.PPO(df['Close'], fastperiod=12, slowperiod=26)
        df['ROC'] = talib.ROC(df['Close'], timeperiod=10)
        df['ROCP'] = talib.ROCP(df['Close'], timeperiod=10)
        df['ROCR'] = talib.ROCR(df['Close'], timeperiod=10)
        df['ROCR100'] = talib.ROCR100(df['Close'], timeperiod=10)
        df['RSI'] = talib.RSI(df['Close'], timeperiod=14)
        df['STOCH_K'], df['STOCH_D'] = talib.STOCH(df['High'], df['Low'], df['Close'])
        # df['STOCHRSI'] = talib.STOCHRSI(df['Close'], timeperiod=14)
        df['TRIX'] = talib.TRIX(df['Close'], timeperiod=14)
        df['ULTOSC'] = talib.ULTOSC(df['High'], df['Low'], df['Close'], timeperiod1=7, timeperiod2=14, timeperiod3=28)
        df['WILLR'] = talib.WILLR(df['High'], df['Low'], df['Close'], timeperiod=14)
        
        # Volume Indicators
        df['OBV'] = talib.OBV(df['Close'], df['Volume'])
        df['ADL'] = talib.AD(df['High'], df['Low'], df['Close'], df['Volume'])
        df['ADOSC'] = talib.ADOSC(df['High'], df['Low'], df['Close'], df['Volume'], fastperiod=3, slowperiod=10)
        
        # Volatility Indicators
        df['ATR'] = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=14)
        df['NATR'] = talib.NATR(df['High'], df['Low'], df['Close'], timeperiod=14)
        df['TRANGE'] = talib.TRANGE(df['High'], df['Low'], df['Close'])
        
        # Price Transform
        df['AVGPRICE'] = talib.AVGPRICE(df['Open'], df['High'], df['Low'], df['Close'])
        df['MEDPRICE'] = talib.MEDPRICE(df['High'], df['Low'])
        df['TYPPRICE'] = talib.TYPPRICE(df['High'], df['Low'], df['Close'])
        df['WCLPRICE'] = talib.WCLPRICE(df['High'], df['Low'], df['Close'])
        
        # Cycle Indicators
        df['HT_DCPERIOD'] = talib.HT_DCPERIOD(df['Close'])
        df['HT_DCPHASE'] = talib.HT_DCPHASE(df['Close'])
        df['HT_PHASOR_InPhase'], df['HT_PHASOR_Quadrature'] = talib.HT_PHASOR(df['Close'])
        df['HT_SINE_Sine'], df['HT_SINE_Lead'] = talib.HT_SINE(df['Close'])
        df['HT_TRENDMODE'] = talib.HT_TRENDMODE(df['Close'])
        
        # Statistic Functions
        df['BETA'] = talib.BETA(df['High'], df['Low'], timeperiod=5)
        df['CORREL'] = talib.CORREL(df['High'], df['Low'], timeperiod=30)
        df['LINEARREG'] = talib.LINEARREG(df['Close'], timeperiod=14)
        df['LINEARREG_ANGLE'] = talib.LINEARREG_ANGLE(df['Close'], timeperiod=14)
        df['LINEARREG_INTERCEPT'] = talib.LINEARREG_INTERCEPT(df['Close'], timeperiod=14)
        df['LINEARREG_SLOPE'] = talib.LINEARREG_SLOPE(df['Close'], timeperiod=14)
        df['STDDEV'] = talib.STDDEV(df['Close'], timeperiod=14, nbdev=1)
        df['TSF'] = talib.TSF(df['Close'], timeperiod=14)
        df['VAR'] = talib.VAR(df['Close'], timeperiod=14)

        df['MOM'] = talib.MOM(df['Close'].values, timeperiod=10)
        
        # Handle NaN values
        df = df.ffill().bfill()
        
        return df
    except Exception as e:
        print(f"Error in calculate_technical_indicators at {e.__traceback__.tb_lineno}: {str(e)}")
        return df

def get_time_frame_settings(time_frame):
    time_settings = time_frame_mapping.get(time_frame, {'interval': 'day', 'days': 2000})
    return time_settings['interval'], time_settings['days']

def get_historical_data(symbol,exchange="NSE", interval='day', days=365):
    try:
        kite = get_kite_instance()
        if not kite:
            raise ValueError("KiteApp instance is not initialized")
        
        # Find instrument token
        instrument_token = None
        try:
            instruments = kite.instruments(exchange)
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
        
        # Calculate technical indicators
        df = calculate_technical_indicators(df)
        
        if df.empty:
            raise ValueError(f"No data available for {symbol}")
            
        return df
        
    except Exception as e:
        print(f"Error fetching data for {symbol}: {str(e)}")
        # Return empty DataFrame instead of None
        return pd.DataFrame()

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

def train_regression_model(data):
    try:
        # Handle NaN values by forward and backward filling
        data = data.copy()
        data = data.ffill().bfill()
        
        # Create the target column for next day's close
        data['Next_Close'] = data['Close'].shift(-1)
        
        # Drop the last row as it has no target value
        data = data.iloc[:-1]
        
        # Dynamically identify feature columns (exclude non-indicator columns and target columns)
        feature_columns = [col for col in data.columns if col not in ['Open', 'High', 'Low', 'Close', 'Volume', 'Date', 'Next_Close']]
        
        # Ensure all feature columns exist and preprocess
        for col in feature_columns:
            if col not in data.columns or data[col].isnull().all():
                print(f"Warning: Missing or invalid column {col}. Filling with 0.")
                data[col] = 0.0
        
        # Forward fill any remaining NaN values
        data = data.ffill().bfill()
        
        # Convert to numpy arrays and ensure float64 dtype
        X = data[feature_columns].values.astype(np.float64)
        y = data['Next_Close'].values.astype(np.float64)
        
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
        
        # Check if there's any data left for training
        if len(X_train) == 0 or len(y_train) == 0:
            raise ValueError("No valid data points left for training after preprocessing.")
        
        # Create and fit the pipeline
        pipeline = make_pipeline(
            StandardScaler(),
            LinearRegression()
        )
        
        pipeline.fit(X_train, y_train)
        return pipeline
        
    except Exception as e:
        print(f"Error in train_regression_model: {str(e)}")
        return make_pipeline(StandardScaler(), LinearRegression())  # Default fallback to Linear Regression # Default fallback to Linear Regression

def train_pytorch_model(data):
    try:
        # Create the target column for next day's close
        data['Next_Close'] = data['Close'].shift(-1)
        
        # Drop the last row as it has no target value
        data = data.iloc[:-1]
        
        # Dynamically identify feature columns (exclude non-indicator columns and target columns)
        feature_columns = [col for col in data.columns if col not in ['Open', 'High', 'Low', 'Close', 'Volume', 'Date', 'Next_Close']]
        
        # Prepare features and target
        X = data[feature_columns].values.astype(np.float32)
        y = data['Next_Close'].values.astype(np.float32)
        
        # Use last 80% of data for training
        train_size = int(len(data) * 0.8)
        X_train = X[-train_size:]
        y_train = y[-train_size:]
        
        # Instantiate the model with input size dynamically set based on feature count
        model = StockPricePredictor(input_size=X_train.shape[1])
        
        # Convert to tensors
        X_tensor = torch.tensor(X_train).float()  # Ensure float type for the model
        y_tensor = torch.tensor(y_train).float()
        
        # Loss and optimizer
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        
        # Train the model
        model.train()
        for epoch in range(100):  # Number of epochs can be adjusted
            optimizer.zero_grad()
            outputs = model(X_tensor)
            loss = criterion(outputs.squeeze(), y_tensor)
            loss.backward()
            optimizer.step()

            # Print loss periodically (optional)
            #   if epoch % 10 == 0:
                # print(f"Epoch {epoch}, Loss: {loss.item()}")
        
        model.eval()  # Set model to evaluation mode
        return model

    except Exception as e:
        print(f"Error in train_pytorch_model: {str(e)}")
        return None

def generate_signals(data, regression_model, pytorch_model):
    try:
        latest_data = data.iloc[-1]

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
        
        # Get 5-day forecast
        forecast_days = 5
        forecasted_prices = []
        forecast_dates = []
        current_features = np.array([
            # Price and volume-related features 
            latest_data['SMA_20'], 
            latest_data['SMA_50'], 
            latest_data['Volume_MA'],

            # Overlap Studies
            latest_data['BBANDS_Upper'], 
            latest_data['BBANDS_Middle'], 
            latest_data['BBANDS_Lower'], 
            latest_data['DEMA'], 
            latest_data['EMA'], 
            latest_data['HT_TRENDLINE'], 
            latest_data['KAMA'], 
            latest_data['MA'], 
            latest_data['MIDPOINT'], 
            latest_data['MIDPRICE'], 
            latest_data['SAR'], 
            latest_data['SAREXT'], 
            latest_data['T3'], 
            latest_data['TEMA'], 
            latest_data['TRIMA'], 
            latest_data['WMA'],

            # Momentum Indicators
            latest_data['ADX'], 
            latest_data['ADXR'], 
            latest_data['APO'], 
            latest_data['AROON_Down'], 
            latest_data['AROON_Up'], 
            latest_data['AROONOSC'], 
            latest_data['BOP'], 
            latest_data['CCI'], 
            latest_data['CMO'], 
            latest_data['DX'], 
            latest_data['MACD'], 
            latest_data['MACD_Signal'], 
            latest_data['MACD_Hist'], 
            latest_data['MFI'], 
            latest_data['MINUS_DI'], 
            latest_data['MINUS_DM'], 
            latest_data['PLUS_DI'], 
            latest_data['PLUS_DM'], 
            latest_data['PPO'], 
            latest_data['ROC'], 
            latest_data['ROCP'], 
            latest_data['ROCR'], 
            latest_data['ROCR100'], 
            latest_data['RSI'], 
            latest_data['STOCH_K'], 
            latest_data['STOCH_D'], 
            latest_data['TRIX'], 
            latest_data['ULTOSC'], 
            latest_data['WILLR'],

            # Volume Indicators
            latest_data['OBV'], 
            latest_data['ADL'], 
            latest_data['ADOSC'],

            # Volatility Indicators
            latest_data['ATR'], 
            latest_data['NATR'], 
            latest_data['TRANGE'],

            # Price Transform
            latest_data['AVGPRICE'], 
            latest_data['MEDPRICE'], 
            latest_data['TYPPRICE'], 
            latest_data['WCLPRICE'],

            # Cycle Indicators
            latest_data['HT_DCPERIOD'], 
            latest_data['HT_DCPHASE'], 
            latest_data['HT_PHASOR_InPhase'], 
            latest_data['HT_PHASOR_Quadrature'], 
            latest_data['HT_SINE_Sine'], 
            latest_data['HT_SINE_Lead'], 
            latest_data['HT_TRENDMODE'],

            # Statistic Functions
            latest_data['BETA'], 
            latest_data['CORREL'], 
            latest_data['LINEARREG'], 
            latest_data['LINEARREG_ANGLE'], 
            latest_data['LINEARREG_INTERCEPT'], 
            latest_data['LINEARREG_SLOPE'], 
            latest_data['STDDEV'], 
            latest_data['TSF'], 
            latest_data['VAR'],

            # Additional Momentum
            latest_data['MOM']
        ]).reshape(1, -1)

        
        # Generate forecast for next 5 days
        for i in range(forecast_days):
            # Get prediction for next day
            predicted_price = float(regression_model.predict(current_features)[0])
            forecasted_prices.append(predicted_price)
            
            # Calculate date for this forecast
            forecast_date = (datetime.now() + timedelta(days=i+1)).strftime('%Y-%m-%d')
            forecast_dates.append(forecast_date)
            
            # Update features for next prediction
            # Simple update using moving average
            current_features[0][0] = (current_features[0][0] * 19 + predicted_price) / 20  # Update SMA_20
            current_features[0][1] = (current_features[0][1] * 49 + predicted_price) / 50  # Update SMA_50
            # Keep volume MA constant or update based on historical average
            
        # Calculate profit/loss percentages for each forecasted day
        profit_loss_pcts = [((price - current_price) / current_price) * 100 
                           for price in forecasted_prices]
        
        # Create forecast dictionary
        forecast_data = [{
            'date': date,
            'predicted_price': round(price, 2),
            'profit_loss_pct': round(pct, 2)
        } for date, price, pct in zip(forecast_dates, forecasted_prices, profit_loss_pcts)]

        # Add forecast data to signals
        signals = {
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
            },
            "forecast": {
                'current_price': current_price,
                'daily_forecasts': forecast_data,
                'avg_5day_return': round(sum(profit_loss_pcts) / len(profit_loss_pcts), 2),
                'max_profit_potential': round(max(profit_loss_pcts), 2),
                'min_profit_potential': round(min(profit_loss_pcts), 2)
            }
        }
        
        return signals
        
    except Exception as e:
        print(f"Error in generate_signals {e.__traceback__.tb_lineno}: {str(e)}")
        return None

def get_stock_details(symbol,exchange):
    try:
        # For Indian stocks, we need to append ".NS" for NSE listings
        
        if exchange.upper() == "NSE":
            ticker_symbol = f"{symbol}.NS"
        elif exchange.upper() == "BSE":
            ticker_symbol = f"{symbol}.BO"
        else:
            raise ValueError("Unsupported exchange. Please use 'NSE' or 'BSE'.")
        
        # Fetch stock details
        ticker = yf.Ticker(ticker_symbol)

        info = ticker.info
        
        if not info:
            raise ValueError(f"No information found for symbol {symbol}")
        
        # Get historical data for pivot point calculation
        end_date = date.today() + timedelta(days=1)
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
        
        change_percentage = ((current_price - hist.iloc[-2]['Close']) / hist.iloc[-2]['Close']) * 100

        return {
            'symbol': symbol,
            'company': info.get('longName', 'N/A'),
            'price': current_price,
            'pivot_points': pivot_points,
            'position': position,
            'open': round(hist.iloc[-1]['Open'], 2),
            'high': round(hist.iloc[-1]['High'], 2),
            'low': round(hist.iloc[-1]['Low'], 2),
            'close': round(hist.iloc[-2]['Close'], 2),
            'change_percentage': f"{'+' if change_percentage > 0 else ''}{round(change_percentage, 2)}%"
        }
    except ValueError as ve:
        print(f"ValueError in get_stock_details for {symbol}: {str(ve)}")
        return None
    except Exception as e:
        print(f"Unexpected error in get_stock_details for {symbol}: {str(e)}")
        return None

def get_top_nse_symbols(allData=False):
    try:
        if allData==True:
            kite = get_kite_instance()
            if not kite:
                raise ValueError("KiteApp instance not initialized")
                
            # Get all NSE instruments
            instruments = kite.instruments("NSE")
            
            # Extract only the tradingsymbols
            symbols = [instrument['tradingsymbol'] for instrument in instruments 
                    if instrument.get('tradingsymbol')]
            
            # Filter out any None or empty values
            symbols = [symbol for symbol in symbols if symbol]
            
            # Sort alphabetically
            symbols.sort()
            
            return symbols
        else:       # List of top 100 NSE companies by market cap
            top_nse_symbols = [
                'RELIANCE', 'TCS', 'HDFCBANK', 'ICICIBANK', 'HINDUNILVR',
                'INFY', 'ITC', 'SBIN', 'BHARTIARTL', 'HDFC', 'KOTAKBANK',
                'LT', 'BAJFINANCE', 'ASIANPAINT', 'AXISBANK', 'MARUTI',
                'TITAN', 'SUNPHARMA', 'WIPRO', 'ULTRACEMCO', 'NESTLEIND',
                'POWERGRID', 'TATAMOTORS', 'ADANIENT', 'NTPC', 'BAJAJFINSV',
                'HCLTECH', 'M&M', 'TECHM', 'COALINDIA', 'HINDALCO',
                'JSWSTEEL', 'TATASTEEL', 'GRASIM', 'INDUSINDBK', 'APOLLOHOSP',
                'ADANIPORTS', 'CIPLA', 'DRREDDY', 'BRITANNIA', 'SBILIFE',
                'EICHERMOT', 'DIVISLAB', 'BAJAJ-AUTO', 'TATACONSUM', 'UPL',
                'HEROMOTOCO', 'ONGC', 'BPCL', 'GAIL', 'HINDPETRO',
                'SHREECEM', 'ADANIGREEN', 'NMDC', 'HDFCLIFE', 'SBICARD',
                'IDFCFIRSTB', 'TATAMETALI', 'ABB', 'SIEMENS', 'CUMMINSIND',
                'MINDTREE', 'PIDILITE', 'HAVELLS', 'BANKBARODA', 'HINDZINC',
                'MARICO', 'HDFCAMC', 'LTI', 'BIOCON', 'SREINFRA',
                'UPL', 'TATAPOWER', 'JINDALSTEL', 'ACC', 'KNRCON',
                'MOTILALOFS', 'TATACHEM', 'MINDTREE', 'SOMANYCERA', 
                'CHOLAFIN', 'RECLTD', 'TVSMOTOR', 'AMBUJACEM', 'MGL',
                'BERGEPAINT', 'APOLLOTYRE', 'IRCTC', 'NLCINDIA', 'LICHSGFIN',
                'POLYCAB', 'LUXIND', 'GRAPHITE', 'TATAPOWER', 'GODREJCP',
                'MCX', 'ICICIPRU', 'ICICIGI', 'DLF', 'HINDCOPPER'
            ]
            return top_nse_symbols
    except Exception as e:
        print(f"Error getting symbols: {str(e)}")
        return []

def generate_stock_analysis(allData=False):
    try:
        print("Starting stock analysis...")
        start_time = time.time()
        
        kite = get_kite_instance()
        if not kite:
            raise ValueError("KiteApp instance not initialized")
            
        instruments = kite.instruments("NSE")
        top_symbols = get_top_nse_symbols(allData=allData)
        
        filtered_instruments = [
            instrument for instrument in instruments 
            if instrument['tradingsymbol'] in top_symbols
        ]
        
        print(f"Processing {len(filtered_instruments)} companies...")

        analysis_results = []
        
        for idx, instrument in enumerate(filtered_instruments):

            stock_start_time = time.time()

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

                current_price = float(signals['current_price'])
                predicted_price = float(signals['predictions']['predicted_price'])
                profit_loss_pct = ((predicted_price - current_price) / current_price) * 100
                
                # Enhanced analysis result with all data points
                analysis_result = {
                    'Symbol': symbol,
                    'Current Price': float(signals['current_price']),
                    'Entry Price': float(signals['entry_price']),
                    'Profit/Loss %': round(profit_loss_pct, 2),
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
                    'Volume Above Average': 1 if signals['volume']['current'] > signals['volume']['average'] else 0,

                    # 5-Day Forecast
                    '5D_Avg_Return': float(signals['forecast']['avg_5day_return']),
                    '5D_Max_Potential': float(signals['forecast']['max_profit_potential']),
                    '5D_Min_Potential': float(signals['forecast']['min_profit_potential']),
                    'Day1_Forecast': float(signals['forecast']['daily_forecasts'][0]['predicted_price']),
                    'Day2_Forecast': float(signals['forecast']['daily_forecasts'][1]['predicted_price']),
                    'Day3_Forecast': float(signals['forecast']['daily_forecasts'][2]['predicted_price']),
                    'Day4_Forecast': float(signals['forecast']['daily_forecasts'][3]['predicted_price']),
                    'Day5_Forecast': float(signals['forecast']['daily_forecasts'][4]['predicted_price']),
                }
                
                analysis_results.append(analysis_result)
                
            except Exception as e:
                print(f"Error processing {symbol}: {str(e)}")
                continue
        
            stock_end_time = time.time()
            stock_elapsed_time = stock_end_time - stock_start_time
            print(f"Processed {symbol} in {stock_elapsed_time:.2f} seconds")

            total_stock_elapsed_time = stock_end_time - start_time
            print(f"Processing time: {total_stock_elapsed_time:.2f} seconds")

        df = pd.DataFrame(analysis_results)
        
        # Enhanced scoring system
        df['Technical Score'] = (
            (df['RSI'].clip(0, 100) / 100 * 0.15) +
            ((df['MACD'] > df['MACD Signal']).astype(float) * 0.15) +
            (df['Prediction Probability'] * 0.25) +
            (df['Current Volume'] > df['Average Volume']).astype(float) * 0.15 +
            ((df['Short Term Trend'] == 'Bullish').astype(float) * 0.15) +
            (df['5D_Avg_Return'].clip(-100, 100) / 100 * 0.15)
        )
        
        df_sorted = df.sort_values(['Technical Score', 'Profit/Loss %'], ascending=[False, False])

        total_end_time = time.time()
        total_elapsed_time = total_end_time - start_time
        print(f"Total processing time: {total_elapsed_time:.2f} seconds")

        # Filter for buy_stocks sheet
        buy_stocks_df = df_sorted[
            (df_sorted['Buy Signal'] == 1) &
            (df_sorted['Current Price'] < 3000) &
            (df_sorted['Profit/Loss %'] > 0.2)
        ]
        
        # Define all formats
        header_format = None
        boolean_format = None
        cell_format = None
        percent_format = None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'stock_analysis_{timestamp}.xlsx'
        
        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            # Get workbook object after initializing the writer
            workbook = writer.book
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D8E4BC',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'text_wrap': True
            })
            
            boolean_format = workbook.add_format({
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'num_format': '0;0;0'  # This ensures numbers are displayed as 0 or 1
            })

            cell_format = workbook.add_format({
                'border': 1,
                'align': 'center',
                'valign': 'vcenter'
            })

            percent_format = workbook.add_format({
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'num_format': '0.00"%"'
            })

            # Write the data to Excel sheets
            df_sorted.to_excel(writer, sheet_name='Analysis', index=False)
            buy_stocks_df.to_excel(writer, sheet_name='Buy_stocks', index=False)

            worksheet = writer.sheets['Analysis']
            buy_stocks_worksheet = writer.sheets['Buy_stocks']

            # Formatting and conditional formatting for Analysis sheet
            for col_num, value in enumerate(df_sorted.columns.values):
                worksheet.write(0, col_num, value, header_format)

            for col_num, value in enumerate(buy_stocks_df.columns.values):
                buy_stocks_worksheet.write(0, col_num, value, header_format)

            # Add conditional formatting for Analysis sheet and buy_stocks sheet
            worksheet.conditional_format('B2:B1048576', {
                'type': '3_color_scale',
                'min_color': '#FF9999',
                'mid_color': '#FFFF99',
                'max_color': '#99FF99'
            })

            buy_stocks_worksheet.conditional_format('B2:B1048576', {
                'type': '3_color_scale',
                'min_color': '#FF9999',
                'mid_color': '#FFFF99',
                'max_color': '#99FF99'
            })

            # Adjust column widths and apply number formats
            for idx, col in enumerate(df_sorted.columns):
                max_length = max(
                    df_sorted[col].astype(str).apply(len).max(),
                    len(str(col))
                )
                worksheet.set_column(idx, idx, max_length + 2)

            for idx, col in enumerate(buy_stocks_df.columns):
                max_length = max(
                    buy_stocks_df[col].astype(str).apply(len).max(),
                    len(str(col))
                )
                buy_stocks_worksheet.set_column(idx, idx, max_length + 2)

            # Freeze top row for both sheets
            worksheet.freeze_panes(1, 0)
            buy_stocks_worksheet.freeze_panes(1, 0)

            # Add filters
            worksheet.autofilter(0, 0, len(df_sorted), len(df_sorted.columns) - 1)
            buy_stocks_worksheet.autofilter(0, 0, len(buy_stocks_df), len(buy_stocks_df.columns) - 1)

            # Add number format for Profit/Loss % column
            worksheet.set_column(df_sorted.columns.get_loc('Profit/Loss %'), 
                                 df_sorted.columns.get_loc('Profit/Loss %'),
                                 None, percent_format)

            buy_stocks_worksheet.set_column(
                buy_stocks_df.columns.get_loc('Profit/Loss %'), 
                buy_stocks_df.columns.get_loc('Profit/Loss %'),
                None, percent_format
            )

        print(f"Analysis complete! Results saved to {filename}")
        return filename
        
    except Exception as e:
        print(f"Error generating stock analysis: {str(e)}")
        return None

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

@app.route('/api/gainers')
def get_gainers_api():
    gainers = get_top_gainers()
    return jsonify(gainers)

@app.route('/api/search',methods=['GET'])
def search_stock():
    try:
        symbol = request.args.get('symbol')
        exchange = request.args.get('exchange')
        stock_info = get_stock_details(symbol,exchange)
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

@app.route('/api/signals', methods=['GET'])
def get_signals():
    try:
        exchange = request.args.get('exchange').upper()
        symbol = request.args.get('symbol')
        time = request.args.get('time')
        
        # userdays = request.args.get('days')
        # try:
        #     userdays = int(userdays) if userdays and userdays.isdigit() else None
        # except ValueError:
        #     userdays = None

        interval,days = get_time_frame_settings(time)

        # effective_days = userdays if userdays is not None else days
        effective_days=days


        # Get historical data
        data = get_historical_data(symbol,exchange,interval,effective_days)
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
        
        return jsonify(signals)
        
    except Exception as e:
        print(f"Error in get_signals for {symbol}: {str(e)}")
        return jsonify({
            'error': str(e),
            'details': 'Error occurred while processing signal data'
        }), 500

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Stock Analysis and Trading Application')
    parser.add_argument('--generate', type=str, choices=['true', 'false'], help='Generate stock analysis report if true')
    parser.add_argument('--full', type=str, choices=['true', 'false'], default='false', help='Fetch all symbols if true')
    args = parser.parse_args()
    
    if args.generate and args.generate.lower() == 'true':
        all_data = args.full.lower() == 'true'
        print(f"Generating stock analysis report with full data: {all_data}")
        generate_stock_analysis(allData=all_data)
    else:
       print("Starting backend server...")
       app.run(debug=True, host='0.0.0.0', port=5000)