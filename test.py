from flask import Flask, jsonify, request
import yfinance as yf
import pandas as pd
import talib  # TA-Lib for technical analysis

app = Flask(__name__)

def calculate_technical_indicators(data):
    """
    Calculate all technical indicators for the given stock data using TA-Lib.
    """

    # Calculate SMA (Simple Moving Average)
    data['SMA_5'] = talib.SMA(data['Close'], timeperiod=5)
    data['SMA_10'] = talib.SMA(data['Close'], timeperiod=10)
    data['SMA_20'] = talib.SMA(data['Close'], timeperiod=20)
    data['SMA_50'] = talib.SMA(data['Close'], timeperiod=50)
    data['SMA_100'] = talib.SMA(data['Close'], timeperiod=100)
    data['SMA_200'] = talib.SMA(data['Close'], timeperiod=200)

    # Calculate EMA (Exponential Moving Average)
    data['EMA_5'] = talib.EMA(data['Close'], timeperiod=5)
    data['EMA_10'] = talib.EMA(data['Close'], timeperiod=10)
    data['EMA_20'] = talib.EMA(data['Close'], timeperiod=20)
    data['EMA_50'] = talib.EMA(data['Close'], timeperiod=50)
    data['EMA_100'] = talib.EMA(data['Close'], timeperiod=100)
    data['EMA_200'] = talib.EMA(data['Close'], timeperiod=200)

    # Calculate Stochastic Oscillator
    data['Stoch_%K'], data['Stoch_%D'] = talib.STOCH(
        data['High'], data['Low'], data['Close'],
        fastk_period=14, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0
    )

    # Overlap Studies
    data['BB_Upper'], data['BB_Middle'], data['BB_Lower'] = talib.BBANDS(data['Close'], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
    data['DEMA'] = talib.DEMA(data['Close'], timeperiod=30)
    data['EMA'] = talib.EMA(data['Close'], timeperiod=30)
    data['HT_TRENDLINE'] = talib.HT_TRENDLINE(data['Close'])
    data['KAMA'] = talib.KAMA(data['Close'], timeperiod=30)
    data['MA'] = talib.MA(data['Close'], timeperiod=30, matype=0)
    data['MAMA'], data['FAMA'] = talib.MAMA(data['Close'], fastlimit=0.5, slowlimit=0.05)
    data['MAVP'] = talib.MAVP(data['Close'], data['Volume'], minperiod=2, maxperiod=30, matype=0)
    data['MIDPOINT'] = talib.MIDPOINT(data['Close'], timeperiod=14)
    data['MIDPRICE'] = talib.MIDPRICE(data['High'], data['Low'], timeperiod=14)
    data['SAR'] = talib.SAR(data['High'], data['Low'], acceleration=0.02, maximum=0.2)
    data['SAREXT'] = talib.SAREXT(data['High'], data['Low'], startvalue=0, offsetonreverse=0, accelerationinitlong=0.02, accelerationlong=0.02, accelerationmaxlong=0.2, accelerationinitshort=0.02, accelerationshort=0.02, accelerationmaxshort=0.2)
    data['SMA'] = talib.SMA(data['Close'], timeperiod=30)
    data['T3'] = talib.T3(data['Close'], timeperiod=5, vfactor=0)
    data['TEMA'] = talib.TEMA(data['Close'], timeperiod=30)
    data['TRIMA'] = talib.TRIMA(data['Close'], timeperiod=30)
    data['WMA'] = talib.WMA(data['Close'], timeperiod=30)

    # Momentum Indicators
    data['ADX'] = talib.ADX(data['High'], data['Low'], data['Close'], timeperiod=14)
    data['ADXR'] = talib.ADXR(data['High'], data['Low'], data['Close'], timeperiod=14)
    data['APO'] = talib.APO(data['Close'], fastperiod=12, slowperiod=26, matype=0)
    data['AROON_DOWN'], data['AROON_UP'] = talib.AROON(data['High'], data['Low'], timeperiod=14)
    data['AROONOSC'] = talib.AROONOSC(data['High'], data['Low'], timeperiod=14)
    data['BOP'] = talib.BOP(data['Open'], data['High'], data['Low'], data['Close'])
    data['CCI'] = talib.CCI(data['High'], data['Low'], data['Close'], timeperiod=14)
    data['CMO'] = talib.CMO(data['Close'], timeperiod=14)
    data['DX'] = talib.DX(data['High'], data['Low'], data['Close'], timeperiod=14)
    data['MACD'], data['MACD_Signal'], data['MACD_Histogram'] = talib.MACD(data['Close'], fastperiod=12, slowperiod=26, signalperiod=9)
    data['MACDEXT'], data['MACDEXT_Signal'], data['MACDEXT_Histogram'] = talib.MACDEXT(data['Close'], fastperiod=12, fastmatype=0, slowperiod=26, slowmatype=0, signalperiod=9, signalmatype=0)
    # data['MACDFIX'], data['MACDFIX_Signal'] = talib.MACDFIX(data['Close'], signalperiod=9)
    data['MFI'] = talib.MFI(data['High'], data['Low'], data['Close'], data['Volume'], timeperiod=14)
    data['MINUS_DI'] = talib.MINUS_DI(data['High'], data['Low'], data['Close'], timeperiod=14)
    data['MINUS_DM'] = talib.MINUS_DM(data['High'], data['Low'], timeperiod=14)
    data['Momentum'] = talib.MOM(data['Close'], timeperiod=10)
    data['PLUS_DI'] = talib.PLUS_DI(data['High'], data['Low'], data['Close'], timeperiod=14)
    data['PLUS_DM'] = talib.PLUS_DM(data['High'], data['Low'], timeperiod=14)
    data['PPO'] = talib.PPO(data['Close'], fastperiod=12, slowperiod=26, matype=0)
    data['ROC'] = talib.ROC(data['Close'], timeperiod=10)
    data['ROCP'] = talib.ROCP(data['Close'], timeperiod=10)
    data['ROCR'] = talib.ROCR(data['Close'], timeperiod=10)
    data['ROCR100'] = talib.ROCR100(data['Close'], timeperiod=10)
    data['RSI'] = talib.RSI(data['Close'], timeperiod=14)
    data['STOCH_SLOWK'], data['STOCH_SLOWD'] = talib.STOCH(data['High'], data['Low'], data['Close'], fastk_period=14, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0)
    data['STOCH_FASTK'], data['STOCH_FASTD'] = talib.STOCHF(data['High'], data['Low'], data['Close'], fastk_period=14, fastd_period=3, fastd_matype=0)
    # data['STOCHRSI'] = talib.STOCHRSI(data['Close'], timeperiod=14, fastk_period=3, fastd_period=3, fastd_matype=0)
    data['TRIX'] = talib.TRIX(data['Close'], timeperiod=30)
    data['ULTOSC'] = talib.ULTOSC(data['High'], data['Low'], data['Close'], timeperiod1=7, timeperiod2=14, timeperiod3=28)
    data['WILLR'] = talib.WILLR(data['High'], data['Low'], data['Close'], timeperiod=14)

    # Volume Indicators
    data['AD'] = talib.AD(data['High'], data['Low'], data['Close'], data['Volume'])
    data['ADOSC'] = talib.ADOSC(data['High'], data['Low'], data['Close'], data['Volume'], fastperiod=3, slowperiod=10)
    data['OBV'] = talib.OBV(data['Close'], data['Volume'])

    # Cycle Indicators
    data['HT_DCPERIOD'] = talib.HT_DCPERIOD(data['Close'])
    data['HT_DCPHASE'] = talib.HT_DCPHASE(data['Close'])
    data['HT_PHASOR_INPHASE'], data['HT_PHASOR_QUADRATURE'] = talib.HT_PHASOR(data['Close'])
    data['HT_SINE_SINE'], data['HT_SINE_LEADSINE'] = talib.HT_SINE(data['Close'])
    data['HT_TRENDMODE'] = talib.HT_TRENDMODE(data['Close'])

    # Price Transform
    data['AVGPRICE'] = talib.AVGPRICE(data['Open'], data['High'], data['Low'], data['Close'])
    data['MEDPRICE'] = talib.MEDPRICE(data['High'], data['Low'])
    data['TYPPRICE'] = talib.TYPPRICE(data['High'], data['Low'], data['Close'])
    data['WCLPRICE'] = talib.WCLPRICE(data['High'], data['Low'], data['Close'])

    # Volatility Indicators
    data['ATR'] = talib.ATR(data['High'], data['Low'], data['Close'], timeperiod=14)
    data['NATR'] = talib.NATR(data['High'], data['Low'], data['Close'], timeperiod=14)
    data['TRANGE'] = talib.TRANGE(data['High'], data['Low'], data['Close'])

    # Pattern Recognition (Candlestick Patterns)
    candlestick_patterns = [
        'CDL2CROWS', 'CDL3BLACKCROWS', 'CDL3INSIDE', 'CDL3LINESTRIKE', 'CDL3OUTSIDE',
        'CDL3STARSINSOUTH', 'CDL3WHITESOLDIERS', 'CDLABANDONEDBABY', 'CDLADVANCEBLOCK',
        'CDLBELTHOLD', 'CDLBREAKAWAY', 'CDLCLOSINGMARUBOZU', 'CDLCONCEALBABYSWALL',
        'CDLCOUNTERATTACK', 'CDLDARKCLOUDCOVER', 'CDLDOJI', 'CDLDOJISTAR', 'CDLDRAGONFLYDOJI',
        'CDLENGULFING', 'CDLEVENINGDOJISTAR', 'CDLEVENINGSTAR', 'CDLGAPSIDESIDEWHITE',
        'CDLGRAVESTONEDOJI', 'CDLHAMMER', 'CDLHANGINGMAN', 'CDLHARAMI', 'CDLHARAMICROSS',
        'CDLHIGHWAVE', 'CDLHIKKAKE', 'CDLHIKKAKEMOD', 'CDLHOMINGPIGEON', 'CDLIDENTICAL3CROWS',
        'CDLINNECK', 'CDLINVERTEDHAMMER', 'CDLKICKING', 'CDLKICKINGBYLENGTH', 'CDLLADDERBOTTOM',
        'CDLLONGLEGGEDDOJI', 'CDLLONGLINE', 'CDLMARUBOZU', 'CDLMATCHINGLOW', 'CDLMATHOLD',
        'CDLMORNINGDOJISTAR', 'CDLMORNINGSTAR', 'CDLONNECK', 'CDLPIERCING', 'CDLRICKSHAWMAN',
        'CDLRISEFALL3METHODS', 'CDLSEPARATINGLINES', 'CDLSHOOTINGSTAR', 'CDLSHORTLINE',
        'CDLSPINNINGTOP', 'CDLSTALLEDPATTERN', 'CDLSTICKSANDWICH', 'CDLTAKURI', 'CDLTASUKIGAP',
        'CDLTHRUSTING', 'CDLTRISTAR', 'CDLUNIQUE3RIVER', 'CDLUPSIDEGAP2CROWS', 'CDLXSIDEGAP3METHODS'
    ]
    for pattern in candlestick_patterns:
        data[pattern] = getattr(talib, pattern)(data['Open'], data['High'], data['Low'], data['Close'])

    # Statistic Functions
    data['BETA'] = talib.BETA(data['High'], data['Low'], timeperiod=5)
    data['CORREL'] = talib.CORREL(data['High'], data['Low'], timeperiod=30)
    data['LINEARREG'] = talib.LINEARREG(data['Close'], timeperiod=14)
    data['LINEARREG_ANGLE'] = talib.LINEARREG_ANGLE(data['Close'], timeperiod=14)
    data['LINEARREG_INTERCEPT'] = talib.LINEARREG_INTERCEPT(data['Close'], timeperiod=14)
    data['LINEARREG_SLOPE'] = talib.LINEARREG_SLOPE(data['Close'], timeperiod=14)
    data['STDDEV'] = talib.STDDEV(data['Close'], timeperiod=5, nbdev=1)
    data['TSF'] = talib.TSF(data['Close'], timeperiod=14)
    data['VAR'] = talib.VAR(data['Close'], timeperiod=5, nbdev=1)

    # Math Transform
    data['ACOS'] = talib.ACOS(data['Close'])
    data['ASIN'] = talib.ASIN(data['Close'])
    data['ATAN'] = talib.ATAN(data['Close'])
    data['CEIL'] = talib.CEIL(data['Close'])
    data['COS'] = talib.COS(data['Close'])
    data['COSH'] = talib.COSH(data['Close'])
    data['EXP'] = talib.EXP(data['Close'])
    data['FLOOR'] = talib.FLOOR(data['Close'])
    data['LN'] = talib.LN(data['Close'])
    data['LOG10'] = talib.LOG10(data['Close'])
    data['SIN'] = talib.SIN(data['Close'])
    data['SINH'] = talib.SINH(data['Close'])
    data['SQRT'] = talib.SQRT(data['Close'])
    data['TAN'] = talib.TAN(data['Close'])
    data['TANH'] = talib.TANH(data['Close'])

    # Math Operators
    data['ADD'] = talib.ADD(data['High'], data['Low'])
    data['DIV'] = talib.DIV(data['High'], data['Low'])
    data['MAX'] = talib.MAX(data['Close'], timeperiod=30)
    data['MAXINDEX'] = talib.MAXINDEX(data['Close'], timeperiod=30)
    data['MIN'] = talib.MIN(data['Close'], timeperiod=30)
    data['MININDEX'] = talib.MININDEX(data['Close'], timeperiod=30)
    # data['MINMAX'] = talib.MINMAX(data['Close'], timeperiod=30)
    # data['MINMAXINDEX'] = talib.MINMAXINDEX(data['Close'], timeperiod=30)
    data['MULT'] = talib.MULT(data['High'], data['Low'])
    data['SUB'] = talib.SUB(data['High'], data['Low'])
    data['SUM'] = talib.SUM(data['Close'], timeperiod=30)

    return data

def get_indicator_range(indicator_type):
    """
    Return the min, max, and range for a given indicator type.
    """
    ranges = {
        "RSI": {"min": 0, "max": 100, "range": "0 to 100"},
        "MACD": {"min": None, "max": None, "range": "Unbounded"},
        "Stochastic": {"min": 0, "max": 100, "range": "0 to 100"},
        "CCI": {"min": -200, "max": 200, "range": "-200 to 200"},
        "Momentum": {"min": None, "max": None, "range": "Unbounded"},
        "SMA": {"min": None, "max": None, "range": "Unbounded"},
        "EMA": {"min": None, "max": None, "range": "Unbounded"},
        "ATR": {"min": 0, "max": None, "range": "0 to ∞"},
        "ADX": {"min": 0, "max": 100, "range": "0 to 100"},
        "Williams_%R": {"min": -100, "max": 0, "range": "-100 to 0"},
        "OBV": {"min": None, "max": None, "range": "Unbounded"},
        "ROC": {"min": None, "max": None, "range": "Unbounded"},
        "Bollinger_Bands": {"min": None, "max": None, "range": "Unbounded"},
        "SAR": {"min": None, "max": None, "range": "Unbounded"},
        "MFI": {"min": 0, "max": 100, "range": "0 to 100"},
        "TRIX": {"min": None, "max": None, "range": "Unbounded"},
        "ULTOSC": {"min": 0, "max": 100, "range": "0 to 100"},
        "WILLR": {"min": -100, "max": 0, "range": "-100 to 0"},
        "AD": {"min": None, "max": None, "range": "Unbounded"},
        "ADOSC": {"min": None, "max": None, "range": "Unbounded"},
        "HT_DCPERIOD": {"min": None, "max": None, "range": "Unbounded"},
        "HT_DCPHASE": {"min": None, "max": None, "range": "Unbounded"},
        "HT_PHASOR": {"min": None, "max": None, "range": "Unbounded"},
        "HT_SINE": {"min": None, "max": None, "range": "Unbounded"},
        "HT_TRENDMODE": {"min": 0, "max": 1, "range": "0 to 1"},
        "AVGPRICE": {"min": None, "max": None, "range": "Unbounded"},
        "MEDPRICE": {"min": None, "max": None, "range": "Unbounded"},
        "TYPPRICE": {"min": None, "max": None, "range": "Unbounded"},
                "WCLPRICE": {"min": None, "max": None, "range": "Unbounded"},
        "NATR": {"min": 0, "max": None, "range": "0 to ∞"},
        "TRANGE": {"min": 0, "max": None, "range": "0 to ∞"},
        "BETA": {"min": None, "max": None, "range": "Unbounded"},
        "CORREL": {"min": -1, "max": 1, "range": "-1 to 1"},
        "LINEARREG": {"min": None, "max": None, "range": "Unbounded"},
        "LINEARREG_ANGLE": {"min": None, "max": None, "range": "Unbounded"},
        "LINEARREG_INTERCEPT": {"min": None, "max": None, "range": "Unbounded"},
        "LINEARREG_SLOPE": {"min": None, "max": None, "range": "Unbounded"},
        "STDDEV": {"min": 0, "max": None, "range": "0 to ∞"},
        "TSF": {"min": None, "max": None, "range": "Unbounded"},
        "VAR": {"min": 0, "max": None, "range": "0 to ∞"},
        "ACOS": {"min": 0, "max": 3.14159, "range": "0 to π"},
        "ASIN": {"min": -1.5708, "max": 1.5708, "range": "-π/2 to π/2"},
        "ATAN": {"min": -1.5708, "max": 1.5708, "range": "-π/2 to π/2"},
        "CEIL": {"min": None, "max": None, "range": "Unbounded"},
        "COS": {"min": -1, "max": 1, "range": "-1 to 1"},
        "COSH": {"min": 1, "max": None, "range": "1 to ∞"},
        "EXP": {"min": 0, "max": None, "range": "0 to ∞"},
        "FLOOR": {"min": None, "max": None, "range": "Unbounded"},
        "LN": {"min": None, "max": None, "range": "Unbounded"},
        "LOG10": {"min": None, "max": None, "range": "Unbounded"},
        "SIN": {"min": -1, "max": 1, "range": "-1 to 1"},
        "SINH": {"min": None, "max": None, "range": "Unbounded"},
        "SQRT": {"min": 0, "max": None, "range": "0 to ∞"},
        "TAN": {"min": None, "max": None, "range": "Unbounded"},
        "TANH": {"min": -1, "max": 1, "range": "-1 to 1"},
        "ADD": {"min": None, "max": None, "range": "Unbounded"},
        "DIV": {"min": None, "max": None, "range": "Unbounded"},
        "MAX": {"min": None, "max": None, "range": "Unbounded"},
        "MAXINDEX": {"min": 0, "max": None, "range": "0 to ∞"},
        "MIN": {"min": None, "max": None, "range": "Unbounded"},
        "MININDEX": {"min": 0, "max": None, "range": "0 to ∞"},
        "MINMAX": {"min": None, "max": None, "range": "Unbounded"},
        "MINMAXINDEX": {"min": 0, "max": None, "range": "0 to ∞"},
        "MULT": {"min": None, "max": None, "range": "Unbounded"},
        "SUB": {"min": None, "max": None, "range": "Unbounded"},
        "SUM": {"min": None, "max": None, "range": "Unbounded"},
    }
    return ranges.get(indicator_type, {"min": None, "max": None, "range": "Unbounded"})

def get_color_for_value(value, indicator_type, latest_data=None):
    """
    Determine the color based on the value and indicator type.
    """
    if indicator_type == "RSI":
        if value < 30:
            return "positive"  # Oversold
        elif value > 70:
            return "negative"  # Overbought
        else:
            return "neutral"  # Neutral
    elif indicator_type == "MACD":
        if value > 0:
            return "positive"  # Bullish
        else:
            return "negative"  # Bearish
    elif indicator_type == "Stochastic":
        if value > 80:
            return "negative"  # Overbought
        elif value < 20:
            return "positive"  # Oversold
        else:
            return "neutral"  # Neutral
    elif indicator_type == "CCI":
        if value > 100:
            return "negative"  # Overbought
        elif value < -100:
            return "positive"  # Oversold
        else:
            return "neutral"  # Neutral
    elif indicator_type == "Momentum":
        if value > 0:
            return "positive"  # Positive momentum
        else:
            return "negative"  # Negative momentum
    elif indicator_type == "SMA" or indicator_type == "EMA":
        # For SMA/EMA, compare with the current price
        if latest_data is not None and value < latest_data['Close']:
            return "positive"  # Price above SMA/EMA
        else:
            return "negative"  # Price below SMA/EMA
    elif indicator_type == "ATR":
        return "neutral"  # ATR is typically neutral
    elif indicator_type == "ADX":
        if value > 25:
            return "positive"  # Strong trend
        else:
            return "neutral"  # Weak trend
    elif indicator_type == "Williams_%R":
        if value < -80:
            return "positive"  # Oversold
        elif value > -20:
            return "negative"  # Overbought
        else:
            return "neutral"  # Neutral
    elif indicator_type == "MFI":
        if value < 20:
            return "positive"  # Oversold
        elif value > 80:
            return "negative"  # Overbought
        else:
            return "neutral"  # Neutral
    elif indicator_type == "TRIX":
        if value > 0:
            return "positive"  # Positive momentum
        else:
            return "negative"  # Negative momentum
    elif indicator_type == "ULTOSC":
        if value < 30:
            return "positive"  # Oversold
        elif value > 70:
            return "negative"  # Overbought
        else:
            return "neutral"  # Neutral
    elif indicator_type == "WILLR":
        if value < -80:
            return "positive"  # Oversold
        elif value > -20:
            return "negative"  # Overbought
        else:
            return "neutral"  # Neutral
    elif indicator_type == "AD":
        return "neutral"  # AD is typically neutral
    elif indicator_type == "ADOSC":
        return "neutral"  # ADOSC is typically neutral
    elif indicator_type == "HT_DCPERIOD":
        return "neutral"  # HT_DCPERIOD is typically neutral
    elif indicator_type == "HT_DCPHASE":
        return "neutral"  # HT_DCPHASE is typically neutral
    elif indicator_type == "HT_PHASOR":
        return "neutral"  # HT_PHASOR is typically neutral
    elif indicator_type == "HT_SINE":
        return "neutral"  # HT_SINE is typically neutral
    elif indicator_type == "HT_TRENDMODE":
        return "neutral"  # HT_TRENDMODE is typically neutral
    elif indicator_type == "AVGPRICE":
        return "neutral"  # AVGPRICE is typically neutral
    elif indicator_type == "MEDPRICE":
        return "neutral"  # MEDPRICE is typically neutral
    elif indicator_type == "TYPPRICE":
        return "neutral"  # TYPPRICE is typically neutral
    elif indicator_type == "WCLPRICE":
        return "neutral"  # WCLPRICE is typically neutral
    elif indicator_type == "NATR":
        return "neutral"  # NATR is typically neutral
    elif indicator_type == "TRANGE":
        return "neutral"  # TRANGE is typically neutral
    elif indicator_type == "BETA":
        return "neutral"  # BETA is typically neutral
    elif indicator_type == "CORREL":
        if value > 0:
            return "positive"  # Positive correlation
        else:
            return "negative"  # Negative correlation
    elif indicator_type == "LINEARREG":
        return "neutral"  # LINEARREG is typically neutral
    elif indicator_type == "LINEARREG_ANGLE":
        return "neutral"  # LINEARREG_ANGLE is typically neutral
    elif indicator_type == "LINEARREG_INTERCEPT":
        return "neutral"  # LINEARREG_INTERCEPT is typically neutral
    elif indicator_type == "LINEARREG_SLOPE":
        return "neutral"  # LINEARREG_SLOPE is typically neutral
    elif indicator_type == "STDDEV":
        return "neutral"  # STDDEV is typically neutral
    elif indicator_type == "TSF":
        return "neutral"  # TSF is typically neutral
    elif indicator_type == "VAR":
        return "neutral"  # VAR is typically neutral
    elif indicator_type == "ACOS":
        return "neutral"  # ACOS is typically neutral
    elif indicator_type == "ASIN":
        return "neutral"  # ASIN is typically neutral
    elif indicator_type == "ATAN":
        return "neutral"  # ATAN is typically neutral
    elif indicator_type == "CEIL":
        return "neutral"  # CEIL is typically neutral
    elif indicator_type == "COS":
        return "neutral"  # COS is typically neutral
    elif indicator_type == "COSH":
        return "neutral"  # COSH is typically neutral
    elif indicator_type == "EXP":
        return "neutral"  # EXP is typically neutral
    elif indicator_type == "FLOOR":
        return "neutral"  # FLOOR is typically neutral
    elif indicator_type == "LN":
        return "neutral"  # LN is typically neutral
    elif indicator_type == "LOG10":
        return "neutral"  # LOG10 is typically neutral
    elif indicator_type == "SIN":
        return "neutral"  # SIN is typically neutral
    elif indicator_type == "SINH":
        return "neutral"  # SINH is typically neutral
    elif indicator_type == "SQRT":
        return "neutral"  # SQRT is typically neutral
    elif indicator_type == "TAN":
        return "neutral"  # TAN is typically neutral
    elif indicator_type == "TANH":
        return "neutral"  # TANH is typically neutral
    elif indicator_type == "ADD":
        return "neutral"  # ADD is typically neutral
    elif indicator_type == "DIV":
        return "neutral"  # DIV is typically neutral
    elif indicator_type == "MAX":
        return "neutral"  # MAX is typically neutral
    elif indicator_type == "MAXINDEX":
        return "neutral"  # MAXINDEX is typically neutral
    elif indicator_type == "MIN":
        return "neutral"  # MIN is typically neutral
    elif indicator_type == "MININDEX":
        return "neutral"  # MININDEX is typically neutral
    elif indicator_type == "MINMAX":
        return "neutral"  # MINMAX is typically neutral
    elif indicator_type == "MINMAXINDEX":
        return "neutral"  # MINMAXINDEX is typically neutral
    elif indicator_type == "MULT":
        return "neutral"  # MULT is typically neutral
    elif indicator_type == "SUB":
        return "neutral"  # SUB is typically neutral
    elif indicator_type == "SUM":
        return "neutral"  # SUM is typically neutral
    else:
        return "neutral"  # Default to neutral

def detect_candlestick_patterns(data):
    """
    Detect candlestick patterns in the latest data.
    """
    patterns = []
    candlestick_patterns = [
        'CDL2CROWS', 'CDL3BLACKCROWS', 'CDL3INSIDE', 'CDL3LINESTRIKE', 'CDL3OUTSIDE',
        'CDL3STARSINSOUTH', 'CDL3WHITESOLDIERS', 'CDLABANDONEDBABY', 'CDLADVANCEBLOCK',
        'CDLBELTHOLD', 'CDLBREAKAWAY', 'CDLCLOSINGMARUBOZU', 'CDLCONCEALBABYSWALL',
        'CDLCOUNTERATTACK', 'CDLDARKCLOUDCOVER', 'CDLDOJI', 'CDLDOJISTAR', 'CDLDRAGONFLYDOJI',
        'CDLENGULFING', 'CDLEVENINGDOJISTAR', 'CDLEVENINGSTAR', 'CDLGAPSIDESIDEWHITE',
        'CDLGRAVESTONEDOJI', 'CDLHAMMER', 'CDLHANGINGMAN', 'CDLHARAMI', 'CDLHARAMICROSS',
        'CDLHIGHWAVE', 'CDLHIKKAKE', 'CDLHIKKAKEMOD', 'CDLHOMINGPIGEON', 'CDLIDENTICAL3CROWS',
        'CDLINNECK', 'CDLINVERTEDHAMMER', 'CDLKICKING', 'CDLKICKINGBYLENGTH', 'CDLLADDERBOTTOM',
        'CDLLONGLEGGEDDOJI', 'CDLLONGLINE', 'CDLMARUBOZU', 'CDLMATCHINGLOW', 'CDLMATHOLD',
        'CDLMORNINGDOJISTAR', 'CDLMORNINGSTAR', 'CDLONNECK', 'CDLPIERCING', 'CDLRICKSHAWMAN',
        'CDLRISEFALL3METHODS', 'CDLSEPARATINGLINES', 'CDLSHOOTINGSTAR', 'CDLSHORTLINE',
        'CDLSPINNINGTOP', 'CDLSTALLEDPATTERN', 'CDLSTICKSANDWICH', 'CDLTAKURI', 'CDLTASUKIGAP',
        'CDLTHRUSTING', 'CDLTRISTAR', 'CDLUNIQUE3RIVER', 'CDLUPSIDEGAP2CROWS', 'CDLXSIDEGAP3METHODS'
    ]
    for pattern in candlestick_patterns:
        if data[pattern].iloc[-1] != 0:
            patterns.append({"name": pattern, "description": f"{pattern} pattern detected."})
    return patterns

@app.route('/api/stock-data', methods=['GET'])
def get_stock_data():
    # Get the stock ticker from the request
    ticker = request.args.get('ticker', default='ASIANPAINT.NS')  # Default to Asian Paints
    period = request.args.get('period', default='1y')  # Default to 1 year of data

    # Fetch stock data using yfinance
    stock = yf.Ticker(ticker)
    data = stock.history(period=period)

    # Calculate technical indicators
    data = calculate_technical_indicators(data)

    # Get the latest row (most recent data)
    latest_data = data.iloc[-1]

    latest_data_dict = latest_data.to_dict()

    # Detect candlestick patterns
    candlestick_patterns = detect_candlestick_patterns(data)

    # Prepare the response
    response = {
        "head": {
            "status": "0",
            "statusDescription": "Success",
            "responseCode": None
        },
        "body": {
            "data":latest_data_dict,
            "parameters": {
                "sma_parameters": [
                    {
                        "name": "5 Day",
                        "value": latest_data['SMA_5'],
                        "color": get_color_for_value(latest_data['SMA_5'], "SMA", latest_data),
                        **get_indicator_range("SMA")
                    },
                    {
                        "name": "10 Day",
                        "value": latest_data['SMA_10'],
                        "color": get_color_for_value(latest_data['SMA_10'], "SMA", latest_data),
                        **get_indicator_range("SMA")
                    },
                    {
                        "name": "20 Day",
                        "value": latest_data['SMA_20'],
                        "color": get_color_for_value(latest_data['SMA_20'], "SMA", latest_data),
                        **get_indicator_range("SMA")
                    },
                    {
                        "name": "50 Day",
                        "value": latest_data['SMA_50'],
                        "color": get_color_for_value(latest_data['SMA_50'], "SMA", latest_data),
                        **get_indicator_range("SMA")
                    },
                    {
                        "name": "100 Day",
                        "value": latest_data['SMA_100'],
                        "color": get_color_for_value(latest_data['SMA_100'], "SMA", latest_data),
                        **get_indicator_range("SMA")
                    },
                    {
                        "name": "200 Day",
                        "value": latest_data['SMA_200'],
                        "color": get_color_for_value(latest_data['SMA_200'], "SMA", latest_data),
                        **get_indicator_range("SMA")
                    }
                ],
                "ema_parameters": [
                    {
                        "name": "5 Day",
                        "value": latest_data['EMA_5'],
                        "color": get_color_for_value(latest_data['EMA_5'], "EMA", latest_data),
                        **get_indicator_range("EMA")
                    },
                    {
                        "name": "10 Day",
                        "value": latest_data['EMA_10'],
                        "color": get_color_for_value(latest_data['EMA_10'], "EMA", latest_data),
                        **get_indicator_range("EMA")
                    },
                    {
                        "name": "20 Day",
                        "value": latest_data['EMA_20'],
                        "color": get_color_for_value(latest_data['EMA_20'], "EMA", latest_data),
                        **get_indicator_range("EMA")
                    },
                    {
                        "name": "50 Day",
                        "value": latest_data['EMA_50'],
                        "color": get_color_for_value(latest_data['EMA_50'], "EMA", latest_data),
                        **get_indicator_range("EMA")
                    },
                    {
                        "name": "100 Day",
                        "value": latest_data['EMA_100'],
                        "color": get_color_for_value(latest_data['EMA_100'], "EMA", latest_data),
                        **get_indicator_range("EMA")
                    },
                    {
                        "name": "200 Day",
                        "value": latest_data['EMA_200'],
                        "color": get_color_for_value(latest_data['EMA_200'], "EMA", latest_data),
                        **get_indicator_range("EMA")
                    }
                ],
                "rsi": {
                    "name": "RSI(14)",
                    "value": latest_data['RSI'],
                    "color": get_color_for_value(latest_data['RSI'], "RSI"),
                    **get_indicator_range("RSI")
                },
                "macd": {
                    "name": "MACD(12, 26, 9)",
                    "value": latest_data['MACD'],
                    "signal": latest_data['MACD_Signal'],
                    "histogram": latest_data['MACD_Histogram'],
                    "color": get_color_for_value(latest_data['MACD'], "MACD"),
                    **get_indicator_range("MACD")
                },
                "stochastic_oscillator": {
                    "name": "Stochastic Oscillator",
                    "value": latest_data['Stoch_%K'],
                    "signal": latest_data['Stoch_%D'],
                    "color": get_color_for_value(latest_data['Stoch_%K'], "Stochastic"),
                    **get_indicator_range("Stochastic")
                },
                "atr": {
                    "name": "ATR",
                    "value": latest_data['ATR'],
                    "color": get_color_for_value(latest_data['ATR'], "ATR"),
                    **get_indicator_range("ATR")
                },
                "adx": {
                    "name": "ADX",
                    "value": latest_data['ADX'],
                    "color": get_color_for_value(latest_data['ADX'], "ADX"),
                    **get_indicator_range("ADX")
                },
                "cci": {
                    "name": "CCI",
                    "value": latest_data['CCI'],
                    "color": get_color_for_value(latest_data['CCI'], "CCI"),
                    **get_indicator_range("CCI")
                },
                "momentum": {
                    "name": "Momentum",
                    "value": latest_data['Momentum'],
                    "color": get_color_for_value(latest_data['Momentum'], "Momentum"),
                    **get_indicator_range("Momentum")
                },
                "bollinger_bands": {
                    "name": "Bollinger Bands",
                    "upper": latest_data['BB_Upper'],
                    "middle": latest_data['BB_Middle'],
                    "lower": latest_data['BB_Lower'],
                    "color": "neutral",
                    **get_indicator_range("Bollinger_Bands")
                },
                "sar": {
                    "name": "Parabolic SAR",
                    "value": latest_data['SAR'],
                    "color": "neutral",
                    **get_indicator_range("SAR")
                },
                "obv": {
                    "name": "OBV",
                    "value": latest_data['OBV'],
                    "color": "neutral",
                    **get_indicator_range("OBV")
                },
                "roc": {
                    "name": "ROC",
                    "value": latest_data['ROC'],
                    "color": "neutral",
                    **get_indicator_range("ROC")
                },
                "williams_%R": {
                    "name": "Williams %R",
                    "value": latest_data['WILLR'],
                    "color": get_color_for_value(latest_data['WILLR'], "Williams_%R"),
                    **get_indicator_range("Williams_%R")
                },
                "candlestick_patterns": candlestick_patterns,
                "current_price": latest_data['Close'],
                "startPrice": data.iloc[0]['Close'],
                "price_change": latest_data['Close'] - data.iloc[0]['Close'],
                "price_change_percent": ((latest_data['Close'] - data.iloc[0]['Close']) / data.iloc[0]['Close']) * 100
            }
        }
    }

    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True)