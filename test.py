import pandas as pd
import numpy as np
from prophet import Prophet
from sklearn.model_selection import ParameterGrid
from sklearn.metrics import mean_squared_error, mean_absolute_error
import matplotlib.pyplot as plt
import yfinance as yf

# Load stock data using yfinance
ticker = "DMART.NS"
stock_data = yf.download(ticker, start='2015-01-01', end=pd.Timestamp.today().strftime('%Y-%m-%d'))

# Ensure the DataFrame has the required columns 'ds' and 'y'
df = stock_data.reset_index()[['Date', 'Close']]
df.columns = ['ds', 'y']

# Remove timezone information to avoid Prophet errors
df['ds'] = pd.to_datetime(df['ds']).dt.tz_localize(None)

# Split data into train and test sets
train_size = int(0.8 * len(df))
train_df = df.iloc[:train_size]
test_df = df.iloc[train_size:]

# Define the hyperparameter grid for tuning
param_grid = {
    'seasonality_mode': ['additive', 'multiplicative'],
    'changepoint_prior_scale': [0.01, 0.05, 0.1, 0.5],
    'seasonality_prior_scale': [1.0, 5.0, 10.0],
    'holidays_prior_scale': [1.0, 5.0, 10.0]
}

# Function to train and evaluate a Prophet model with given parameters
def evaluate_model(params, train_df, test_df):
    model = Prophet(
        seasonality_mode=params['seasonality_mode'],
        changepoint_prior_scale=params['changepoint_prior_scale'],
        seasonality_prior_scale=params['seasonality_prior_scale'],
        holidays_prior_scale=params['holidays_prior_scale']
    )
    
    model.fit(train_df)
    future = model.make_future_dataframe(periods=len(test_df), freq='D')
    forecast = model.predict(future)
    
    # Filter for the test period
    forecast_test = forecast.iloc[-len(test_df):]
    rmse = np.sqrt(mean_squared_error(test_df['y'], forecast_test['yhat']))
    mae = mean_absolute_error(test_df['y'], forecast_test['yhat'])
    return rmse, mae, model

# Perform grid search for hyperparameter tuning
best_rmse = float('inf')
best_params = None
best_model = None

for params in ParameterGrid(param_grid):
    rmse, mae, model = evaluate_model(params, train_df, test_df)
    print(f"Params: {params}, RMSE: {rmse}, MAE: {mae}")
    if rmse < best_rmse:
        best_rmse = rmse
        best_params = params
        best_model = model

print("Best Parameters:", best_params)
print("Best RMSE:", best_rmse)

# Forecast for the next 5 days
forecast_periods = 5
future = best_model.make_future_dataframe(periods=forecast_periods, freq='D')
forecast = best_model.predict(future)

# Show the last 5 days' prediction
five_day_forecast = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(forecast_periods)
print("5-Day Forecast:")
print(five_day_forecast)

# Plot the best model's forecast
plt.figure(figsize=(10, 6))
plt.plot(train_df['ds'], train_df['y'], label='Training Data')
plt.plot(test_df['ds'], test_df['y'], label='Actual Test Data')
plt.plot(forecast['ds'], forecast['yhat'], label='Forecasted Data')
plt.fill_between(forecast['ds'], forecast['yhat_lower'], forecast['yhat_upper'], color='gray', alpha=0.2)
plt.legend()
plt.title('Forecast vs Actuals with 5-Day Forecast')
plt.show()
