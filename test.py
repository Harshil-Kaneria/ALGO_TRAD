import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import talib
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_percentage_error
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
import logging

# Set up logging and warnings
np.random.seed(42)
logging.getLogger("tensorflow").setLevel(logging.ERROR)
import warnings
warnings.filterwarnings("ignore")

# Define stock symbol and index symbol
stock_symbol = 'DMART.NS'
index_symbol = '^NSEI'  # Nifty 50 index

# Define date range
start_date = '2010-01-01'
end_date = datetime.datetime.now().date()

# Fetch stock and index data
stock_data = yf.download(stock_symbol, start=start_date, end=end_date)
index_data = yf.download(index_symbol, start=start_date, end=end_date)

# Add suffixes to column names before merging
stock_data = stock_data.add_suffix('_stock')
index_data = index_data.add_suffix('_index')

# Merge stock and index data on the Date index
merged_data = pd.merge(stock_data, index_data, left_index=True, right_index=True, how='inner')
merged_data = merged_data.reset_index()  # Reset index to make 'Date' a column

# Debugging: Check the shape and type of the input array
print("Shape of Close_stock:", merged_data['Close_stock'].values.shape)
print("Type of Close_stock:", merged_data['Close_stock'].values.dtype)

# Feature Engineering with TA-Lib
# Ensure the input to TA-Lib is a 1-dimensional array of type float
try:
    merged_data['SMA_10_stock'] = talib.SMA(merged_data['Close_stock'].values, timeperiod=10)
    merged_data['EMA_10_stock'] = talib.EMA(merged_data['Close_stock'].values, timeperiod=10)
    merged_data['Volatility_stock'] = talib.STDDEV(merged_data['Close_stock'].pct_change().fillna(0).values, timeperiod=10)
    merged_data['Momentum_stock'] = talib.MOM(merged_data['Close_stock'].values, timeperiod=5)
    merged_data['SMA_10_index'] = talib.SMA(merged_data['Close_index'].values, timeperiod=10)
    merged_data['EMA_10_index'] = talib.EMA(merged_data['Close_index'].values, timeperiod=10)
    merged_data['Volatility_index'] = talib.STDDEV(merged_data['Close_index'].pct_change().fillna(0).values, timeperiod=10)
    merged_data['Momentum_index'] = talib.MOM(merged_data['Close_index'].values, timeperiod=5)
except Exception as e:
    print("Error in TA-Lib calculation:", e)

# Fill missing values
merged_data = merged_data.fillna(method='ffill')
merged_data = merged_data.dropna()

# Prepare data for LSTM
features = ['Close_stock', 'SMA_10_stock', 'EMA_10_stock', 'Volatility_stock', 'Momentum_stock',
            'Close_index', 'SMA_10_index', 'EMA_10_index', 'Volatility_index', 'Momentum_index']
target = 'Prediction'

# Normalize the data
scaler = MinMaxScaler(feature_range=(0, 1))
scaled_data = scaler.fit_transform(merged_data[features + [target]])

# Create sequences for LSTM
def create_sequences(data, seq_length):
    X, y = [], []
    for i in range(seq_length, len(data)):
        X.append(data[i-seq_length:i, :-1])
        y.append(data[i, -1])
    return np.array(X), np.array(y)

seq_length = 60
X, y = create_sequences(scaled_data, seq_length)

# Split data into training and testing sets
split = int(0.8 * len(X))
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]

# Build LSTM model
model = Sequential()
model.add(LSTM(units=50, return_sequences=True, input_shape=(X_train.shape[1], X_train.shape[2])))
model.add(Dropout(0.2))
model.add(LSTM(units=50, return_sequences=False))
model.add(Dropout(0.2))
model.add(Dense(units=25))
model.add(Dense(units=1))

# Compile the model
model.compile(optimizer='adam', loss='mean_squared_error')

# Train the model
model.fit(X_train, y_train, epochs=20, batch_size=32, validation_data=(X_test, y_test))

# Predict on test data
predictions = model.predict(X_test)

# Inverse transform the predictions and actual values
predictions = scaler.inverse_transform(np.concatenate((X_test[:, -1, :-1], predictions), axis=1))[:, -1]
y_test = scaler.inverse_transform(np.concatenate((X_test[:, -1, :-1], y_test.reshape(-1, 1)), axis=1))[:, -1]

# Calculate accuracy
mape = mean_absolute_percentage_error(y_test, predictions)
mse = mean_squared_error(y_test, predictions)

# Print results
print(f"\nAccuracy Metrics:")
print(f"MAPE: {mape:.2%}")  # Display MAPE as percentage
print(f"MSE: {mse:.2f}")
