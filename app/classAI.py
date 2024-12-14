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
            raise
