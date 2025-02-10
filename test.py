import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error
from sklearn.model_selection import GridSearchCV, train_test_split
import xgboost as xgb
from flask import Flask, request, jsonify
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from sklearn.preprocessing import MinMaxScaler
import datetime
import statsmodels.api as sm
from sklearn.base import BaseEstimator, RegressorMixin

app = Flask(__name__)

# Function to fetch the latest stock data
def fetch_stock_data(stock_symbol, period='1y', interval='1d'):
    stock_data = yf.download(stock_symbol, period=period, interval=interval)
    stock_data['Date'] = stock_data.index
    stock_data.reset_index(drop=True, inplace=True)
    return stock_data

# Function to add additional features (Technical Indicators)
def add_features(data):
    data['Moving_Avg_10'] = data['Close'].rolling(window=10).mean()
    data['Moving_Avg_50'] = data['Close'].rolling(window=50).mean()
    data['RSI'] = compute_rsi(data['Close'], 14)
    data['EMA_12'] = data['Close'].ewm(span=12, adjust=False).mean()
    return data.dropna()

# Function to compute Relative Strength Index (RSI)
def compute_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Prepare the data for LSTM model
def prepare_data_for_lstm(data, time_step=60):
    features = data[['Close', 'Moving_Avg_10', 'Moving_Avg_50', 'RSI', 'EMA_12']].values
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(features)

    X, y = [], []
    for i in range(time_step, len(scaled_data)):
        X.append(scaled_data[i-time_step:i])
        y.append(scaled_data[i, 0])  # Predicting 'Close' price

    X = np.array(X)
    y = np.array(y)
    return X, y, scaler

# Custom Keras Regressor for GridSearchCV
class KerasRegressor(BaseEstimator, RegressorMixin):
    def __init__(self, units=50, dropout_rate=0.2, epochs=10, batch_size=32):
        self.units = units
        self.dropout_rate = dropout_rate
        self.epochs = epochs
        self.batch_size = batch_size
        self.model = self._build_model()

    def _build_model(self):
        model = Sequential()
        model.add(LSTM(units=self.units, return_sequences=True, input_shape=(None, 5)))
        model.add(Dropout(self.dropout_rate))
        model.add(LSTM(units=self.units, return_sequences=False))
        model.add(Dropout(self.dropout_rate))
        model.add(Dense(units=1))
        model.compile(optimizer='adam', loss='mean_squared_error')
        return model

    def fit(self, X, y):
        self.model.fit(X, y, epochs=self.epochs, batch_size=self.batch_size, verbose=0)
        return self

    def predict(self, X):
        return self.model.predict(X).flatten()

    def score(self, X, y):
        return -self.model.evaluate(X, y, verbose=0)

# Function to tune LSTM hyperparameters (GridSearchCV)
def tune_lstm_model(X_train, y_train, time_step):
    model = KerasRegressor()

    # Define the parameter grid
    param_grid = {
        'epochs': [10, 20, 30],
        'batch_size': [16, 32],
        'units': [50, 100],
        'dropout_rate': [0.2, 0.3]
    }

    # Perform grid search
    grid_search = GridSearchCV(estimator=model, param_grid=param_grid, cv=3, verbose=1, scoring='neg_mean_squared_error')
    grid_search.fit(X_train, y_train)

    print(f"Best Hyperparameters: {grid_search.best_params_}")
    return grid_search.best_estimator_

# Recursive Rolling Forecasting Function with LSTM
def rolling_forecast(data, forecast_days=5, time_step=60):
    predictions = []

    # Prepare data for LSTM
    X, y, scaler = prepare_data_for_lstm(data, time_step)

    # Split the data into training and testing sets
    train_size = int(len(X) * 0.8)
    X_train, X_test = X[:train_size], X[train_size:]
    y_train, y_test = y[:train_size], y[train_size:]

    # Tune LSTM hyperparameters using GridSearch
    best_lstm_model = tune_lstm_model(X_train, y_train, time_step)

    # Predict future stock prices
    for i in range(forecast_days):
        last_sequence = X_test[-1].reshape(1, X_test.shape[1], X_test.shape[2])
        predicted_price = best_lstm_model.predict(last_sequence)
        predictions.append(scaler.inverse_transform(predicted_price.reshape(-1, 1))[0][0])
        # Add the new prediction into the X_test data for the next prediction
        X_test = np.append(X_test, predicted_price.reshape(1, -1), axis=0)

    return predictions

# XGBoost model implementation
def xgboost_forecast(data, forecast_days=5):
    X = data[['Close', 'Moving_Avg_10', 'Moving_Avg_50', 'RSI', 'EMA_12']].values
    y = data['Close'].values
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

    model = xgb.XGBRegressor(objective="reg:squarederror", n_estimators=1000, max_depth=10, learning_rate=0.01)
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    forecast_prices = []
    for i in range(forecast_days):
        forecast_prices.append(predictions[i])

    return forecast_prices

# ARIMA model implementation
def arima_forecast(data, forecast_days=5):
    model = sm.tsa.ARIMA(data['Close'], order=(5, 1, 0))
    model_fit = model.fit()
    forecast = model_fit.forecast(steps=forecast_days)
    return forecast

# API Endpoint for stock prediction
@app.route('/search', methods=['GET'])
def stock_prediction():
    stock_symbol = request.args.get('symbol', default='DMART.NS', type=str)

    # Fetch and process stock data
    stock_data = fetch_stock_data(stock_symbol)
    stock_data = add_features(stock_data)

    # Perform rolling forecast (5 days in the future)
    forecast_prices_lstm = rolling_forecast(stock_data)
    forecast_prices_xgboost = xgboost_forecast(stock_data)
    forecast_prices_arima = arima_forecast(stock_data)

    # Calculate metrics for LSTM model
    rmse_lstm = np.sqrt(mean_squared_error(stock_data['Close'][-len(forecast_prices_lstm):], forecast_prices_lstm))
    mds_lstm = mean_absolute_error(stock_data['Close'][-len(forecast_prices_lstm):], forecast_prices_lstm)

    # Calculate metrics for XGBoost model
    rmse_xgboost = np.sqrt(mean_squared_error(stock_data['Close'][-len(forecast_prices_xgboost):], forecast_prices_xgboost))
    mds_xgboost = mean_absolute_error(stock_data['Close'][-len(forecast_prices_xgboost):], forecast_prices_xgboost)

    # Calculate metrics for ARIMA model
    rmse_arima = np.sqrt(mean_squared_error(stock_data['Close'][-len(forecast_prices_arima):], forecast_prices_arima))
    mds_arima = mean_absolute_error(stock_data['Close'][-len(forecast_prices_arima):], forecast_prices_arima)

    # Prepare response
    response = {
        "LSTM RMSE": rmse_lstm,
        "LSTM MDS": mds_lstm,
        "XGBoost RMSE": rmse_xgboost,
        "XGBoost MDS": mds_xgboost,
        "ARIMA RMSE": rmse_arima,
        "ARIMA MDS": mds_arima,
        "CURRENT_PRICE": stock_data['Close'].iloc[-1],
        "LSTM_Forecast": forecast_prices_lstm,
        "XGBoost_Forecast": forecast_prices_xgboost,
        "ARIMA_Forecast": forecast_prices_arima
    }

    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)