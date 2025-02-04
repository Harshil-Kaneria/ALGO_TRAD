import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from prophet import Prophet
from skopt import gp_minimize
from sklearn.metrics import mean_absolute_error, mean_squared_error

# Fetch historical stock data
def fetch_data(ticker, start='2020-01-01'):
    end = datetime.today().strftime('%Y-%m-%d')
    data = yf.download(ticker, start=start, end=end)
    data = data[['Close', 'Volume']].reset_index()
    data.columns = ['ds', 'y', 'volume']  # Rename for Prophet compatibility
    data['ds'] = data['ds'].dt.tz_localize(None)  # Remove timezone
    data['y'] = np.log(data['y'])  # Log transformation
    print("fetch_data output:\n", data.head())
    return data

# Feature Engineering (Regressors)
def add_regressors(df):
    print("Columns before regressors:\n", df.columns)
    df['moving_avg'] = df['y'].rolling(7).mean().bfill()
    df['volatility'] = df['y'].rolling(7).std().bfill()
    
    delta = df['y'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-10)
    df.loc[:, 'rsi'] = 100 - (100 / (1 + rs))  # Fixed inplace warning
    df['rsi'] = df['rsi'].fillna(50)  # Fixed inplace warning
    
    short_ema = df['y'].ewm(span=12, adjust=False).mean()
    long_ema = df['y'].ewm(span=26, adjust=False).mean()
    df['macd'] = short_ema - long_ema
    
    df['trend_indicator'] = (df['y'] > df['moving_avg']).astype(int)  # Fixed Prophet reserved name
    df['log_volume'] = np.log(df['volume'] + 1)
    return df.drop(columns=['volume'])

# Objective function for Bayesian Optimization
def objective(params):
    changepoint_prior, seasonality_prior, interval_width = params
    model = Prophet(
        changepoint_prior_scale=changepoint_prior,
        seasonality_prior_scale=seasonality_prior,
        interval_width=interval_width
    )
    model.add_regressor('moving_avg')
    model.add_regressor('volatility')
    model.add_regressor('rsi')
    model.add_regressor('macd')
    model.add_regressor('trend_indicator')  # Updated regressor name
    model.add_regressor('log_volume')
    model.fit(df_train)
    future = model.make_future_dataframe(periods=30)
    future = future.merge(df[['ds', 'volume']], on='ds', how='left')
    future['y'] = np.nan
    future = add_regressors(future)
    forecast = model.predict(future)
    y_pred = forecast['yhat'][:len(df_train)]
    mae = mean_absolute_error(df_train['y'], y_pred)
    return mae

# Train and Forecast
def train_and_forecast(ticker, periods=30):
    global df_train
    df = fetch_data(ticker)
    df_volume = df[['ds', 'volume']].copy()
    df = add_regressors(df)
    df = df.merge(df_volume, on="ds", how="left")
    df_train = df[:-periods].copy()
    print("Training Data Sample:\n", df_train.head())
    df_test = df[-periods:].copy()
    print("Testing Data Sample:\n", df_test.head())

    df_train['volume'] = df[:-periods]['volume']  # Retain volume in df_train
    df_test['volume'] = df[-periods:]['volume']   # Retain volume in df_test
    
    search_space = [(0.001, 0.5), (0.01, 10), (0.8, 0.99)]
    res = gp_minimize(objective, search_space, n_calls=20, random_state=42)
    best_params = {
        'changepoint_prior_scale': res.x[0],
        'seasonality_prior_scale': res.x[1],
        'interval_width': res.x[2]
    }
    
    model = Prophet(**best_params)
    model.add_regressor('moving_avg')
    model.add_regressor('volatility')
    model.add_regressor('rsi')
    model.add_regressor('macd')
    model.add_regressor('trend_indicator')  # Updated regressor name
    model.add_regressor('log_volume')
    model.fit(df_train)
    
    future = model.make_future_dataframe(periods=periods)
    future = future.merge(df[['ds', 'volume']], on='ds', how='left')  # Add volume
    future['y'] = np.nan  # Ensure y exists 
    future = add_regressors(future)
    forecast = model.predict(future)
    test_forecast = forecast[-periods:]
    
    mae = mean_absolute_error(df_test['y'], test_forecast['yhat'])
    mse = mean_squared_error(df_test['y'], test_forecast['yhat'])
    rmse = np.sqrt(mse)
    mape = np.mean(np.abs((df_test['y'] - test_forecast['yhat']) / df_test['y'])) * 100
    
    print(f"Optimized - MAE: {mae:.4f}, RMSE: {rmse:.4f}, MAPE: {mape:.2f}%")
    return df, forecast, test_forecast

# Run the prediction
if __name__ == "__main__":
    ticker = "ASIANPAINT.NS"
    df, forecast, test_forecast = train_and_forecast(ticker)
    print(test_forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']])