import yfinance as yf
import pandas as pd
import numpy as np
import datetime
from prophet import Prophet
from sklearn.metrics import mean_squared_error, mean_absolute_percentage_error
from sklearn.model_selection import ParameterGrid
from statsmodels.stats.outliers_influence import variance_inflation_factor
import warnings

warnings.filterwarnings("ignore")

# Define the stock symbol, start date, and end date
stock_symbol = 'AAPL'  # Using Apple share prices Just for example
start_date = '2010-01-01'
end_date = datetime.datetime.now().date()

# Fetch the stock data
stock_data = yf.download(stock_symbol, start=start_date, end=end_date)
stock_data = stock_data.reset_index()

# Ensure the `Close` column is numeric
# stock_data['Close'] = pd.to_numeric(stock_data['Close'])
stock_data = stock_data.dropna()  # Drop rows with NaN values in `Close`

# Display the data
print(stock_data.head())
print(stock_data.dtypes)

close = ['Close']
forecast_period = 15  # Number of future periods to forecast
validation_period = 15

# Load and preprocess data
def load_and_preprocess_data(df, vars_list):
    df = df.dropna()
    processed_data = {}
    for var in vars_list:
        # Ensure the `y` column is numeric
        # df[var] = pd.to_numeric(df[var], errors='coerce')
        df = df.dropna()  # Drop rows with NaN values in `y`
        processed_data[var] = df[['Date', var]].rename(columns={'Date': 'ds', var: 'y'})
    return processed_data

# Apply differencing to make the series stationary
def apply_differencing(df, order=1):
    print("Before differencing:")
    print(df.head())
    print(df.dtypes)

    df['y_diff'] = df['y'].diff(periods=order)
    df = df.dropna()

    print("After differencing:")
    print(df.head())
    print(df.dtypes)

    # Ensure `y` is numeric
    # df['y'] = pd.to_numeric(df['y'], errors='coerce')  # Coerce non-numeric values to NaN
    df = df.dropna()  # Drop rows with NaN values in `y`

    print("After numeric conversion:")
    print(df.head())
    print(df.dtypes)

    return df

# Split data into training and validation sets
def split_data(df, validation_size):
    train_size = len(df) - validation_size
    train = df.iloc[:train_size].copy()
    valid = df.iloc[train_size:].copy()

    print("Training data:")
    print(train.head())
    print(train.dtypes)

    print("Validation data:")
    print(valid.head())
    print(valid.dtypes)

    return train, valid

# Train Prophet model with hyperparameter tuning
def train_prophet(train_df, add_monthly=True, add_quarterly=True, add_rolling_mean=True, add_rolling_std=True, add_expanding_std=True, **params):
    """
    Train a Prophet model using the provided training dataframe and parameters.
    """
    # Ensure `y` is numeric
    # train_df['y'] = pd.to_numeric(train_df['y'], errors='coerce')
    train_df = train_df.dropna()  # Drop rows with NaN values in `y`

    model = Prophet(**params)

    if add_rolling_mean:
        model.add_regressor('rolling_mean_3')
    if add_rolling_std:
        model.add_regressor('rolling_std_3')   
    if add_expanding_std:
        model.add_regressor('expanding_std')
    if add_monthly:
        model.add_seasonality(name='monthly', period=30.5, fourier_order=5)
    if add_quarterly:
        model.add_seasonality(name='quarterly', period=91.25, fourier_order=5)

    return model.fit(train_df)

# Find optimal parameters with differencing and feature engineering
def find_optimal_params(df, validation_period):
    best_rmse = float('inf')
    param_grid = {
        'changepoint_prior_scale': [0.01, 0.05, 0.1],
        'seasonality_prior_scale': [1.0, 10.0, 15.0],
        'seasonality_mode':  ['additive', 'multiplicative'],
        'yearly_seasonality': [True, False],
        'add_monthly': [True, False],
        'add_quarterly': [True, False],
        'daily_seasonality':[True, False],
        'add_rolling_mean': [True, False],
        'add_rolling_std':[True, False],
        'add_expanding_std':[True, False]
    }
    grid = ParameterGrid(param_grid)

    for params in grid:
        train_df, valid_df = split_data(df, validation_period)
        train_df = apply_differencing(train_df)

        # Ensure `y` is numeric
        # train_df['y'] = pd.to_numeric(train_df['y'], errors='coerce')
        train_df = train_df.dropna()  # Drop rows with NaN values in `y`

        model = train_prophet(train_df, **params)
        _, rmse, _, _ = validate_model(model, train_df, valid_df, validation_period)
        if rmse < best_rmse:
            best_rmse = rmse
            best_params = params

    print(f"Best Parameters: {best_params}")  # Print best parameters
    return best_params

# Load and preprocess data

def create_rolling_expanding_features(df, window=3):
    df[f'rolling_mean_{window}'] = df['y'].rolling(window=window).mean().shift(1)
    df[f'rolling_std_{window}'] = df['y'].rolling(window=window).std().shift(1)
    df[f'expanding_std'] = df['y'].expanding().std().shift(1)

    return df.dropna()

def forecast_complete_data(data, vars_list, validation_period, forecast_period):
    results = {}
    for var in vars_list:
        df = data[var]

        df = create_rolling_expanding_features(df)
        

        df = df.dropna()

        if len(df) < 2:
            print(f"Not enough data to train model for {var}.")
            continue

        best_params = find_optimal_params(df, validation_period)

        train_df, valid_df = split_data(df, validation_period)
        train_df = apply_differencing(train_df)
        valid_df = apply_differencing(valid_df)

        features_df = train_df.drop(columns=['ds', 'y'])
        vif_data = calculate_vif(features_df)
        print(vif_data)

        # Train model on training data
        model = train_prophet(train_df, **best_params)
        val_forecast, rmse, mape,mda = validate_model(model, train_df, valid_df, validation_period)

        # Combine training and validation data
        combined_df = pd.concat([train_df, valid_df])

        # Re-fit model on the complete dataset
        final_model = train_prophet(combined_df, **best_params)

        # Make predictions with the re-fitted model
        forecast = make_predictions(final_model, combined_df, forecast_period)

        # Plot final forecast as an extension of historical data
        plot_final_forecast(combined_df, forecast, var)

        # Save outputs
        # save_outputs(var, forecast, val_forecast)

        results[var] = {
            'Forecast': forecast,
            'Validation Forecast': val_forecast,
            'RMSE': rmse,
            'MAPE': mape,
            'MDA': mda
        }
    return results

# Process and forecast
datasets = load_and_preprocess_data(stock_data[['Date'] + close], close)
results_stock_price = forecast_complete_data(datasets, close, validation_period, forecast_period)

for var in close:
    print('--------------------------------------')
    print('VAR: ', var)
    print("RMSE : ", results_stock_price[var]['RMSE'])
    print("Acurracy(1- MAPE) : ", results_stock_price[var]['MAPE'])
    print("MDA : ", results_stock_price[var]['MDA'])