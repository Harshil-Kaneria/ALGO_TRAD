import yfinance as yf
import pandas as pd
import numpy as np
from prophet import Prophet
from sklearn.model_selection import ParameterGrid
from sklearn.metrics import mean_absolute_error, mean_squared_error

# Fetch historical stock data
def fetch_data(ticker, start='2020-01-01', end='2025-02-03'):
    data = yf.download(ticker, start=start, end=end)
    data = data[['Close']].reset_index()
    data.columns = ['ds', 'y']  # Rename for Prophet compatibility
    data['ds'] = data['ds'].dt.tz_localize(None)  # Remove timezone
    return data

# Feature Engineering (Regressors)
def add_regressors(df, last_y=None):
    if 'y' not in df or df['y'].isnull().all():
        df['y'] = last_y if last_y is not None else np.nan
    df['y'].fillna(method='ffill', inplace=True)  # Ensure no NaN before calculations
    df['moving_avg'] = df['y'].rolling(7).mean().bfill()
    df['volatility'] = df['y'].rolling(7).std().bfill()
    return df

# Tune Prophet Hyperparameters
def tune_hyperparameters(df_train):
    param_grid = {
        'changepoint_prior_scale': [0.001, 0.01, 0.1, 0.5],
        'seasonality_prior_scale': [0.01, 0.1, 1.0, 10.0],
        'seasonality_mode': ['additive', 'multiplicative']
    }
    
    best_params = None
    best_error = float('inf')
    for params in ParameterGrid(param_grid):
        model = Prophet(**params)
        model.add_regressor('moving_avg')
        model.add_regressor('volatility')
        model.fit(df_train)
        
        future = model.make_future_dataframe(periods=10)
        last_y = df_train['y'].iloc[-1]  # Use last known price
        future = add_regressors(future, last_y)
        forecast = model.predict(future)
        
        error = np.mean(np.abs(forecast['yhat'][:len(df_train)] - df_train['y']))
        if error < best_error:
            best_error = error
            best_params = params
    
    return best_params

# Train and Predict
def train_and_forecast(ticker, periods=30):
    df = fetch_data(ticker)
    df = add_regressors(df)
    df_train = df[:-periods]
    df_test = df[-periods:]
    
    best_params = tune_hyperparameters(df_train)
    
    model = Prophet(**best_params)
    model.add_regressor('moving_avg')
    model.add_regressor('volatility')
    model.fit(df_train)
    
    future = model.make_future_dataframe(periods=periods)
    last_y = df_train['y'].iloc[-1]  # Use last known price
    future = add_regressors(future, last_y)
    forecast = model.predict(future)
    
    # Evaluate the model on the test set
    test_forecast = forecast[-periods:]
    mae = mean_absolute_error(df_test['y'], test_forecast['yhat'])
    mse = mean_squared_error(df_test['y'], test_forecast['yhat'])
    rmse = np.sqrt(mse)
    
    print(f"MAE: {mae}, MSE: {mse}, RMSE: {rmse}")
    
    return df, forecast, test_forecast

# Run the prediction
if __name__ == "__main__":
    ticker = "ASIANPAINT.NS"  # Change ticker as needed
    df, forecast, test_forecast = train_and_forecast(ticker)
    print(test_forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']])