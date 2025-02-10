import yfinance as yf
import numpy as np
from datetime import datetime
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_percentage_error
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX
from sklearn.linear_model import LinearRegression
from xgboost import XGBRegressor
from prophet import Prophet
import tensorflow as tf
from arch import arch_model

# Helper functions for metrics
def calculate_mda(actual, predicted):
    direction_actual = np.sign(np.diff(actual))
    direction_predicted = np.sign(np.diff(predicted))
    return np.mean(direction_actual == direction_predicted)

def calculate_metrics(actual, predicted):
    rmse = np.sqrt(mean_squared_error(actual, predicted))
    mape = mean_absolute_percentage_error(actual, predicted)
    accuracy = 1 - mape
    mda = calculate_mda(actual, predicted)
    return rmse, accuracy, mda

# Fetch stock data
def fetch_data(ticker, start, end):
    data = yf.download(ticker, start=start, end=end)
    data['Return'] = data['Close'].pct_change().dropna()
    return data

# LSTM model
def lstm_model(data):
    # Preprocessing for LSTM
    from sklearn.preprocessing import MinMaxScaler
    scaler = MinMaxScaler()
    data_scaled = scaler.fit_transform(data.reshape(-1, 1))
    
    # Create sequences
    X, y = [], []
    for i in range(60, len(data_scaled)):
        X.append(data_scaled[i-60:i, 0])
        y.append(data_scaled[i, 0])
    X, y = np.array(X), np.array(y)
    X = np.reshape(X, (X.shape[0], X.shape[1], 1))
    
    # Build LSTM model
    model = tf.keras.Sequential([
        tf.keras.layers.LSTM(units=50, return_sequences=True, input_shape=(X.shape[1], 1)),
        tf.keras.layers.LSTM(units=50),
        tf.keras.layers.Dense(1)
    ])
    model.compile(optimizer='adam', loss='mean_squared_error')
    model.fit(X, y, epochs=10, batch_size=32, verbose=0)
    
    # Predict
    predictions = model.predict(X)
    predictions = scaler.inverse_transform(predictions)
    return predictions.flatten()

# GARCH model
def garch_model(data):
    model = arch_model(data, vol='Garch', p=1, q=1)
    res = model.fit(disp='off')
    return res.forecast(horizon=len(data)).mean.iloc[-1].values

# XGBoost model
def xgboost_model(data):
    from sklearn.model_selection import train_test_split
    X = np.arange(len(data)).reshape(-1, 1)
    y = data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = XGBRegressor()
    model.fit(X_train, y_train)
    return model.predict(X_test)

# ARIMA model
def arima_model(data):
    model = ARIMA(data, order=(5, 1, 0))
    res = model.fit()
    return res.forecast(steps=len(data))

# SARIMA model
def sarima_model(data):
    model = SARIMAX(data, order=(1, 1, 1), seasonal_order=(1, 1, 1, 12))
    res = model.fit(disp=False)
    return res.forecast(steps=len(data))

# Regression model
def regression_model(data):
    X = np.arange(len(data)).reshape(-1, 1)
    y = data
    model = LinearRegression()
    model.fit(X, y)
    return model.predict(X)

# Prophet model
def prophet_model(data):
    # Ensure `data` is a Pandas Series with a DateTime index
    df = pd.DataFrame({'ds': data.index, 'y': data})
    model = Prophet()
    model.fit(df)
    future = model.make_future_dataframe(periods=30)  # Forecast next 30 days
    forecast = model.predict(future)
    return forecast['yhat'][:len(data)].values  # Return only the matching forecast values

# Neural Network model (Simple)
def neural_network_model(data):
    from sklearn.preprocessing import MinMaxScaler
    scaler = MinMaxScaler()
    data_scaled = scaler.fit_transform(data.reshape(-1, 1))
    
    X, y = [], []
    for i in range(60, len(data_scaled)):
        X.append(data_scaled[i-60:i, 0])
        y.append(data_scaled[i, 0])
    X, y = np.array(X), np.array(y)
    
    model = tf.keras.Sequential([
        tf.keras.layers.Dense(50, activation='relu'),
        tf.keras.layers.Dense(1)
    ])
    model.compile(optimizer='adam', loss='mean_squared_error')
    model.fit(X, y, epochs=10, verbose=0)
    predictions = model.predict(X)
    return scaler.inverse_transform(predictions).flatten()

# Main function
def main():
    ticker = "ASIANPAINT.NS"
    start_date = "2020-01-01"
    end_date = datetime.today().strftime('%Y-%m-%d')
    data = fetch_data(ticker, start_date, end_date)['Close']

    models = {
        "LSTM": lstm_model,
        "GARCH": garch_model,
        "XGBoost": xgboost_model,
        "ARIMA": arima_model,
        "SARIMA": sarima_model,
        "Regression": regression_model,
        "Prophet": prophet_model,
        "Neural Network": neural_network_model
    }

    results = {}
    for model_name, model_func in models.items():
        if model_name == "Prophet":
            predictions = model_func(data)  # Pass full data for Prophet
        else:
            predictions = model_func(data.values)
        
        # Align lengths: truncate actual data to match predictions
        min_length = min(len(data.values), len(predictions))
        actual = data.values[-min_length:]
        predictions = predictions[-min_length:]
        
        rmse, accuracy, mda = calculate_metrics(actual, predictions)
        results[model_name] = {
            "RMSE": rmse,
            "Accuracy": accuracy,
            "MDA": mda
        }

    best_model = max(results, key=lambda x: results[x]["Accuracy"])
    print(f"Best Model: {best_model}")
    print(f"Metrics: {results[best_model]}")

if __name__ == "__main__":
    main()
