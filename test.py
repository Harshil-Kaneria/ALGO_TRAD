import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from prophet import Prophet
from skopt import gp_minimize
from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error
from statsmodels.stats.outliers_influence import variance_inflation_factor
import logging
import warnings

np.random.seed(42)
logging.getLogger("cmdstanpy").disabled = True  # Suppress cmdstanpy logs
logging.getLogger("prophet").disabled = True  # Suppress Prophet logs
warnings.filterwarnings("ignore")

# Fetch historical stock data
def fetch_data(ticker, start='2020-01-01'):
    end = datetime.today().strftime('%Y-%m-%d')
    data = yf.download(ticker, start=start, end=end)
    if data.empty:
        raise ValueError(f"No data found for {ticker}. Please check the ticker symbol.")
    data = data[['Close', 'Volume']].reset_index()
    data.columns = ['ds', 'y', 'volume']  # Rename for Prophet compatibility
    data['ds'] = data['ds'].dt.tz_localize(None)  # Remove timezone
    data['y'] = np.log(data['y'])  # Log transformation to stabilize variance
    return data

def add_regressors(df):
    """Adds technical indicators as regressors."""
    if 'y' not in df.columns:
        raise KeyError("'y' column is missing from DataFrame")
    
    df['moving_avg'] = df['y'].rolling(7).mean().bfill()
    df['volatility'] = df['y'].rolling(7).std().bfill()
    df['rsi'] = 100 - (100 / (1 + df['y'].diff().rolling(14).mean().bfill()))
    df['macd'] = df['y'].ewm(span=12).mean() - df['y'].ewm(span=26).mean()
    df['trend_indicator'] = (df['y'] > df['moving_avg']).astype(int)
    df['log_volume'] = np.log(df.get('volume', 1) + 1)  # Avoid KeyError
    
    df = df.fillna(0)  # Ensure no NaNs
    return df

# Check Variance Inflation Factor (VIF) to reduce multicollinearity
def calculate_vif(df, features):
    vif_data = pd.DataFrame()
    vif_data['Feature'] = features
    vif_data['VIF'] = [variance_inflation_factor(df[features].values, i) for i in range(len(features))]
    return vif_data

# Objective function for Bayesian Optimization
def objective(params, df, df_train):
    changepoint_prior, seasonality_prior, interval_width = params
    model = Prophet(
        changepoint_prior_scale=changepoint_prior,
        seasonality_prior_scale=seasonality_prior,
        interval_width=interval_width
    )
    regressors = ['moving_avg', 'volatility', 'rsi', 'macd', 'trend_indicator', 'log_volume']
    for reg in regressors:
        model.add_regressor(reg)
    
    model.fit(df_train)

    future = model.make_future_dataframe(periods=30)
    
    # Ensure future has 'y' column by merging with past data
    future = future.merge(df[['ds', 'y']], on='ds', how='left')
    future['y'] = future['y'].fillna(method='ffill').fillna(0)  # Fill missing values safely

    if 'volume' in df.columns:
        future = future.merge(df[['ds', 'volume']], on='ds', how='left').fillna(0)
    else:
        future['volume'] = 0
    
    future = add_regressors(future)  # Ensure all regressors exist

    forecast = model.predict(future)
    y_pred = forecast['yhat'][:len(df_train)]
    
    return mean_absolute_error(df_train['y'], y_pred)

# Train and Forecast
def train_and_forecast(ticker, periods=180):
    df = fetch_data(ticker)
    df = add_regressors(df)

    if df.isnull().values.any():
        df = df.fillna(0)  # Ensure no NaNs before training

    df_train = df[:-periods].copy()
    df_test = df[-periods:].copy()

    # Bayesian Optimization
    search_space = [(0.001, 0.5), (0.01, 10), (0.8, 0.99)]
    res = gp_minimize(lambda params: objective(params, df, df_train), search_space, n_calls=20, random_state=42)

    best_params = {
        'changepoint_prior_scale': res.x[0],
        'seasonality_prior_scale': res.x[1],
        'interval_width': res.x[2]
    }

    # Train final model
    model = Prophet(**best_params)
    regressors = ['moving_avg', 'volatility', 'rsi', 'macd', 'trend_indicator', 'log_volume']
    for reg in regressors:
        model.add_regressor(reg)
    model.fit(df_train)

    # Make future predictions
    future = model.make_future_dataframe(periods=periods)
    
    # Ensure 'y' column exists
    future = future.merge(df[['ds', 'y']], on='ds', how='left')
    future['y'] = future['y'].fillna(method='ffill').fillna(0)

    if 'volume' in df.columns:
        future = future.merge(df[['ds', 'volume']], on='ds', how='left').fillna(0)
    else:
        future['volume'] = 0

    future = add_regressors(future)

    forecast = model.predict(future)

    # Convert test predictions back from log scale
    test_forecast = forecast[-periods:]
    df_test['y'] = np.exp(df_test['y'])
    test_forecast[['yhat', 'yhat_lower', 'yhat_upper']] = np.exp(test_forecast[['yhat', 'yhat_lower', 'yhat_upper']])

    # Evaluate Model
    mae = mean_absolute_error(df_test['y'], test_forecast['yhat'])
    mse = mean_squared_error(df_test['y'], test_forecast['yhat'])
    rmse = np.sqrt(mse)
    mape = mean_absolute_percentage_error(df_test['y'], test_forecast['yhat']) * 100

    print(f"Optimized - MAE: {mae:.4f}, RMSE: {rmse:.4f}, MAPE: {mape:.2f}%")

    return df, forecast, test_forecast

# Run the prediction
if __name__ == "__main__":
    ticker = "ASIANPAINT.NS"
    try:
        df, forecast, test_forecast = train_and_forecast(ticker)
        print(test_forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']])
    except Exception as e:
        print(f"Error: {e}")
