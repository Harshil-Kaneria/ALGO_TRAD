import React, { useState, useEffect } from "react";
import axios from "axios";
import CryptoJS from "crypto-js";
import {
  Card,
  Tag,
  Button,
  notification,
  Select,
  Slider,
  Layout,
  Result,
} from "antd";
import { useNavigate } from "react-router-dom";

const decryptMessage = (
  encryptedMessage,
  secretKey = process.env.REACT_APP_API_SECRET_KEY
) => {
  // Ensure the key matches the length (256 bits / 32 bytes)
  const key = CryptoJS.enc.Utf8.parse(secretKey.padEnd(32).slice(0, 32));

  // Decode Base64
  const encryptedBytes = CryptoJS.enc.Base64.parse(encryptedMessage);

  // Extract IV (first 16 bytes)
  const iv = CryptoJS.lib.WordArray.create(
    encryptedBytes.words.slice(0, 4),
    16
  );

  // Extract ciphertext
  const ciphertext = CryptoJS.lib.WordArray.create(
    encryptedBytes.words.slice(4),
    encryptedBytes.sigBytes - 16
  );

  // Decrypt the data
  const decrypted = CryptoJS.AES.decrypt({ ciphertext }, key, { iv });
  return JSON.parse(decrypted.toString(CryptoJS.enc.Utf8));
};

const apiClient = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL,
});

apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("token");
    if (token) {
      config.headers["Authorization"] = token;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add a response interceptor
apiClient.interceptors.response.use(
  (response) => {
    // Decrypt the response data
    if (response.data) {
      response.data = decryptMessage(response.data);
    }
    return response;
  },
  (error) => {
    if (error.response && error.response.status === 401) {
      // Remove token from localStorage
      localStorage.removeItem("token");

      // Show notification
      notification.error({
        message: "Session Expired",
        description: "Your session has expired. Please log in again.",
      });

      // Redirect to login page
      window.location.href = "/"; // Use this in non-React hooks contexts
    }

    // Handle any error
    return Promise.reject(error);
  }
);

const { Content } = Layout;

const MaintenancePage = ({ message, description, onRetry }) => (
  <Layout style={{ minHeight: "100vh" }}>
    <Content
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        backgroundColor: "#f0f2f5",
      }}
    >
      <Result
        status="error"
        title={message}
        subTitle={description}
        extra={
          <Button type="primary" onClick={onRetry}>
            Retry
          </Button>
        }
      />
    </Content>
  </Layout>
);

function Dashboard() {
  const navigate = useNavigate();

  const [profileData, setProfileData] = useState(null);
  const [isMarketOpen, setIsMarketOpen] = useState(false);
  const [exchange, setExchange] = useState("NSE");
  const [timeInterval, setTimeInterval] = useState("1d");
  const [instruments, setInstruments] = useState([]);
  const [searchSymbol, setSearchSymbol] = useState("");
  const [searchResult, setSearchResult] = useState(null);
  const [searchOptions, setSearchOptions] = useState([]);
  const [signals, setSignals] = useState(null);
  const [days, setDays] = useState(2000);
  const [maxDays, setMaxDays] = useState(2000);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const time_frame_mapping = {
    1: { interval: "minute", days: 60 },
    3: { interval: "3minute", days: 100 },
    5: { interval: "5minute", days: 100 },
    10: { interval: "10minute", days: 100 },
    15: { interval: "15minute", days: 200 },
    30: { interval: "30minute", days: 200 },
    60: { interval: "60minute", days: 400 },
    "1d": { interval: "day", days: 2000 },
  };

  const renderSignals = () => {
    if (!signals) return null;

    return (
      <Card
        className="mb-4"
        title="Advanced Trading Analysis"
        extra={
          <span className="text-gray-500">
            Last Updated: {new Date().toLocaleString()}
          </span>
        }
      >
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Trading Signals */}
          <Card type="inner" title="Trading Signals" className="bg-gray-50">
            <div className="space-y-2">
              <Tag
                color={signals.buy_signal ? "green" : "red"}
                className="w-full text-center"
              >
                <i className={signals.buy_signal ? "icon-buy" : "icon-sell"} />{" "}
                Buy Signal: {signals.buy_signal ? "YES" : "NO"}
              </Tag>
              <Tag
                color={signals.sell_signal ? "red" : "default"}
                className="w-full text-center"
              >
                <i
                  className={signals.sell_signal ? "icon-sell" : "icon-neutral"}
                />{" "}
                Sell Signal: {signals.sell_signal ? "YES" : "NO"}
              </Tag>
            </div>
          </Card>

          {/* Price Information */}
          <Card type="inner" title="Price Analysis" className="bg-gray-50">
            <p>
              <strong>Current Price:</strong>{" "}
              <span
                className={
                  signals.current_price < signals.entry_price
                    ? "text-red-500"
                    : "text-green-500"
                }
              >
                {signals.current_price.toFixed(2)}
              </span>
            </p>
            <p>
              <strong>Entry Price:</strong> {signals.entry_price.toFixed(2)}
            </p>
            <p>
              <strong>Predicted Price:</strong>{" "}
              {signals.predictions.predicted_price.toFixed(2)}
            </p>
            <p>
              <strong>Confidence:</strong> {signals.predictions.confidence}
            </p>
            <p>
              <strong>Profit/Loss Percentage:</strong>
              <span className="text-blue-500">
                (
                {(
                  ((signals.predictions.predicted_price -
                    signals.current_price) /
                    signals.current_price) *
                  100
                ).toFixed(2)}
                %){" "}
              </span>
            </p>
          </Card>

          {/* Risk Management */}
          {signals.risk_levels && (
            <Card type="inner" title="Risk Management" className="bg-gray-50">
              <p>
                <strong>Stop Loss:</strong> $
                {signals.risk_levels.stop_loss.toFixed(2)}
              </p>
              <p>
                <strong>Take Profit:</strong> $
                {signals.risk_levels.take_profit.toFixed(2)}
              </p>
              <p>
                <strong>Risk/Reward Ratio:</strong>{" "}
                {signals.risk_levels.risk_reward_ratio}
              </p>
            </Card>
          )}

          {/* Technical Analysis */}
          <Card type="inner" title="Technical Analysis" className="bg-gray-50">
            <p>
              <strong>RSI:</strong> {signals.indicators.rsi.toFixed(2)}
            </p>
            <p>
              <strong>MACD:</strong> {signals.indicators.macd.value.toFixed(2)}{" "}
              (Signal: {signals.indicators.macd.signal.toFixed(2)})
            </p>
            <p className="text-center">
              <hr />
              <strong>Bollinger Bands</strong>
              <hr />
            </p>
            <ul>
              <li>
                <strong>Upper:</strong>{" "}
                {signals.indicators.bollinger_bands.upper.toFixed(2)}
              </li>
              <li>
                <strong>Middle:</strong>{" "}
                {signals.indicators.bollinger_bands.middle.toFixed(2)}
              </li>
              <li>
                <strong>Lower:</strong>{" "}
                {signals.indicators.bollinger_bands.lower.toFixed(2)}
              </li>
            </ul>
          </Card>

          {/* Market Context */}
          <Card type="inner" title="Market Context" className="bg-gray-50">
            <p>
              <strong>Volume Trend:</strong>{" "}
              {signals.market_context.volume_trend}
            </p>
            <p>
              <strong>Trend Strength:</strong>{" "}
              {signals.market_context.trend_strength}
            </p>
            <p>
              <strong>Volatility:</strong> {signals.market_context.volatility}
            </p>
            <p>
              <strong>ADX:</strong> {signals.market_context.adx.toFixed(2)}
            </p>
          </Card>

          {/* Trend Analysis */}
          <Card type="inner" title="Trend Analysis" className="bg-gray-50">
            <p>
              <strong>Short Term:</strong> {signals.trend_analysis.short_term}
            </p>
            <p>
              <strong>Medium Term:</strong> {signals.trend_analysis.medium_term}
            </p>
            <p>
              <strong>Long Term:</strong> {signals.trend_analysis.long_term}
            </p>
          </Card>

          {/* Volume Information */}
          <Card type="inner" title="Volume Analysis" className="bg-gray-50">
            <p>
              <strong>Current Volume:</strong>{" "}
              {signals.volume.current.toLocaleString()}
            </p>
            <p>
              <strong>Average Volume:</strong>{" "}
              {signals.volume.average.toLocaleString()}
            </p>
            <p>
              <strong>Volume Trend:</strong> {signals.volume.trend}
            </p>
          </Card>

          {/* Momentum Indicators */}
          <Card type="inner" title="Momentum Indicators" className="bg-gray-50">
            <p>
              <strong>Momentum:</strong> {signals.momentum.value.toFixed(2)}
            </p>
            <p>
              <strong>Rate of Change (ROC):</strong>{" "}
              {signals.momentum.roc.toFixed(2)}
            </p>
          </Card>

          {/* Pattern Recognition */}
          <Card type="inner" title="Patterns Detected" className="bg-gray-50">
            {Object.entries(signals.patterns).map(
              ([pattern, value]) =>
                value !== 0 && (
                  <Tag key={pattern} color={value > 0 ? "green" : "red"}>
                    {pattern}
                  </Tag>
                )
            )}
            {Object.values(signals.patterns).every((value) => value === 0) && (
              <p>No patterns detected.</p>
            )}
          </Card>
        </div>
      </Card>
    );
  };

  const handleSearchInput = (value) => {
    // if (!value) {
    //   setSearchOptions([]);
    //   return;
    // }

    const filtered = instruments.filter(
      (instrument) =>
        instrument.tradingsymbol.toLowerCase().includes(value.toLowerCase()) ||
        instrument.name.toLowerCase().includes(value.toLowerCase())
    );

    const options = filtered.map((instrument) => ({
      value: instrument.tradingsymbol,
      label: `${instrument.tradingsymbol} - ${instrument.name}`,
    }));

    setSearchOptions(options);
  };

  const fetchProfileData = async () => {
    setIsLoading(true);
    try {
      let response = await apiClient.get(`/api/profile`);
      setProfileData(response.data.profile_data);
      setIsMarketOpen(response.data.market_status);
      if (response.data.market_status === false) {
        notification.error({
          message: "Error",
          description: "Please wait until market open",
        });
      }
    } catch (error) {
      const errorMessage =
        error.response?.data?.message || "Service is temporarily unavailable.";
      setError({ message: "Service Unavailable", description: errorMessage });
      setIsLoading(false);
    }
  };

  const fetchInstruments = async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.get(
        `/api/instruments?exchange=${exchange}`
      );
      setInstruments(response.data);
      setSearchSymbol("");
      handleSearchInput("");
    } catch (error) {
      console.error("Error fetching instruments:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAnalysisSearch = async () => {
    setIsLoading(true);
    try {
      setSignals(null);
      const response = await apiClient.get(
        `/api/signals?exchange=${exchange}&symbol=${searchSymbol}&time=${timeInterval}&days=${days}`
      );
      console.log("response - data", response.data);
      setSignals(response.data.signals);
      setSearchResult(response.data.stock_info);
    } catch (error) {
      console.log("Error fetching signals:", error);
      notification.error({
        message: "Error",
        description: error.response?.data?.error || "Failed to fetch signals",
      });
      setSearchResult(null);
      setSignals(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      const response = await apiClient.get(`/api/logout`);
      localStorage.removeItem("token");
      navigate("/");
    } catch (error) {
      notification.error({
        message: "Error",
        description: error.response?.data?.error || "Error in logout",
      });
    }
  };

  useEffect(() => {
    fetchProfileData();
  }, []);

  useEffect(() => {
    if (profileData && isMarketOpen) {
      setInstruments([]);
      fetchInstruments();
    }
  }, [exchange, profileData, isMarketOpen]);

  if (error) {
    return (
      <MaintenancePage
        message={error.message}
        description={error.description}
        onRetry={() => {
          setError(null); // Clear the error state
          fetchProfileData(); // Retry fetching data
        }}
      />
    );
  }

  if (isLoading) {
    return (
      <div className="fixed inset-0 bg-gray-100 bg-opacity-90 flex flex-col justify-center items-center z-50 backdrop-blur-sm">
        <div className="flex flex-col items-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-blue-500 border-solid border-opacity-70 mb-6"></div>
          <h1 className="text-2xl font-semibold text-gray-700">
            Loading, please wait...
          </h1>
          <p className="text-gray-500 mt-2">
            We’re fetching the latest data for you.
          </p>
        </div>
      </div>
    );
  }

  let pivotPoints = [];
  if (searchResult) {
    pivotPoints = [
      { label: "PP", value: searchResult.pivot_points.pp, color: "#108ee9" },
      { label: "Price", value: searchResult.price, color: "#f50" },
      { label: "R1", value: searchResult.pivot_points.r1, color: "red" },
      { label: "R2", value: searchResult.pivot_points.r2, color: "red" },
      { label: "R3", value: searchResult.pivot_points.r3, color: "red" },
      { label: "S1", value: searchResult.pivot_points.s1, color: "green" },
      { label: "S2", value: searchResult.pivot_points.s2, color: "green" },
      { label: "S3", value: searchResult.pivot_points.s3, color: "green" },
    ];
    pivotPoints.sort((a, b) => a.value - b.value);
  }

  return (
    <div className="bg-gray-100 flex items-center justify-center min-h-screen">
      <div className="bg-white rounded-lg shadow-lg p-8 w-3/4 relative">
        <div className="relative">
          <h1 className="text-3xl font-bold text-center">Smart A! Trading</h1>
          <div className="flex items-center justify-center">
            <hr className="flex-grow border-t border-dashed border-gray-400" />
            <p className="mx-4 text-lg text-gray-600 italic">
              Welcome, {`${profileData?.user?.name}`}
            </p>
            <hr className="flex-grow border-t border-dashed border-gray-400" />
          </div>
          <Button
            color="danger"
            variant="dashed"
            className="absolute right-0 top-0"
            onClick={handleLogout}
          >
            Logout
          </Button>
        </div>
        <div className="">
          <div className="">
            <div className="flex items-center mb-4 space-x-4">
              <h2 className="text-2xl font-bold flex-grow">Search Stock</h2>
              <Button
                type="primary"
                onClick={handleAnalysisSearch}
                className="ml-2"
                ghost
                disabled={!exchange || !searchSymbol || !timeInterval || !days}
              >
                Search
              </Button>
            </div>

            <div className="flex items-center mb-4 space-x-4">
              {/* Exchange Dropdown */}
              <div className="flex-1">
                <label
                  htmlFor="exchangeDropdown"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Exchange
                </label>
                <Select
                  id="exchangeDropdown"
                  value={exchange}
                  onChange={(value) => setExchange(value)}
                  options={[
                    { label: "NSE", value: "NSE" },
                    { label: "BSE", value: "BSE" },
                    // Add more exchange options here if needed
                  ]}
                  placeholder="Select Exchange"
                  className="w-full"
                />
              </div>

              {/* Time Interval Dropdown */}
              <div className="flex-1">
                <label
                  htmlFor="timeIntervalDropdown"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Time Interval
                </label>
                <Select
                  id="timeIntervalDropdown"
                  value={timeInterval}
                  onChange={(value) => {
                    setTimeInterval(value);
                    const maxDays = time_frame_mapping[value]?.days || 5;
                    setDays(maxDays);
                    setMaxDays(maxDays);
                  }}
                  options={[
                    { label: "1 Minute", value: "1" },
                    { label: "3 Minutes", value: "3" },
                    { label: "5 Minutes", value: "5" },
                    { label: "10 Minutes", value: "10" },
                    { label: "15 Minutes", value: "15" },
                    { label: "30 Minutes", value: "30" },
                    { label: "1 Hour", value: "60" },
                    { label: "1 Day", value: "1d" },
                  ]}
                  placeholder="Select Time Interval"
                  className="w-full"
                />
              </div>

              {/* Stock Search Dropdown */}
              <div className="flex-1">
                <label
                  htmlFor="stockSearchDropdown"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Search Stock
                </label>
                <Select
                  id="stockSearchDropdown"
                  showSearch
                  value={searchSymbol}
                  placeholder="Search for a stock"
                  defaultActiveFirstOption={false}
                  showArrow={false}
                  filterOption={false}
                  onSearch={handleSearchInput}
                  onChange={(value) => setSearchSymbol(value)}
                  notFoundContent={null}
                  options={searchOptions}
                  className="w-full"
                />
              </div>
            </div>

            {/* <label className="block text-sm font-medium text-gray-700 mb-1">
                    Days for Analysis
                  </label>
                  <Slider
                    min={5}
                    max={maxDays}
                    value={days}
                    onChange={(value) => setDays(value)}
                    tooltip={{ formatter: (value) => `${value} days` }}
                    marks={{
                      5: "5",
                      [days]: `${days}`,
                      [maxDays]: `${maxDays}`,
                    }}
                    step={1} // Ensures precise control over day selection
                  /> */}

            {searchResult && (
              <Card
                className="mb-4"
                title={`${searchResult.company} (${searchResult.symbol})`}
                extra={
                  <>
                    <Tag color="geekblue">
                      Predicted Price :{" "}
                      {signals.predictions.predicted_price.toFixed(2)}
                    </Tag>
                    <Tag color="geekblue">
                      Confidence : {signals.predictions.confidence}
                    </Tag>
                    <Tag color="geekblue">
                      Profit/Loss Percentage : (
                      {(
                        ((signals.predictions.predicted_price -
                          signals.current_price) /
                          signals.current_price) *
                        100
                      ).toFixed(2)}
                      %)
                    </Tag>
                  </>
                }
              >
                <p className="mb-2 flex justify-evenly">
                  <span>
                    <strong>Price:</strong> {searchResult.price}
                  </span>
                  <span>
                    <strong>Open:</strong> {searchResult.open}
                  </span>
                  <span>
                    <strong>High:</strong> {searchResult.high}
                  </span>
                  <span>
                    <strong>Low:</strong> {searchResult.low}
                  </span>
                  <span>
                    <strong>Prev. close:</strong> {searchResult.close}
                  </span>
                  <span>
                    <strong>Change:</strong> {searchResult.change_percentage}
                  </span>
                </p>
                <br />
                <p className="pl-3 pr-3">
                  <Slider
                    min={searchResult.low} // Lowest value on the slider
                    max={searchResult.high} // Highest value on the slider
                    value={searchResult.price} // Current price position on the slider
                    marks={{
                      [searchResult.low]: {
                        style: { color: "#ff3333" },
                        label: `Low: ${searchResult.low}`,
                      },
                      [searchResult.open]: {
                        style: { color: "#ffaa00" },
                        label: `Open: ${searchResult.open}`,
                      },
                      [searchResult.price]: {
                        style: { color: "#00aaff" },
                        label: `Price: ${searchResult.price}`,
                      },
                      [searchResult.high]: {
                        style: { color: "#00cc44" },
                        label: `High: ${searchResult.high}`,
                      },
                    }}
                    tooltip={{ formatter: null }} // Disables tooltip for interactivity
                    disabled // Makes the slider read-only
                    trackStyle={{
                      background: "linear-gradient(90deg, #00aaff, #00cc44)", // Gradient track
                      height: "8px",
                    }}
                    railStyle={{
                      background: "#f0f0f0", // Light gray rail background
                      height: "8px",
                    }}
                    handleStyle={{
                      borderColor: "#00cc44", // Color of the handle
                      height: "16px",
                      width: "16px",
                      marginTop: "-4px",
                      backgroundColor: "#ffffff",
                      cursor: "default", // Removes hover cross sign
                    }}
                  />
                </p>
                <br />
                <div className="flex justify-center">
                  {pivotPoints.map((tag) => (
                    <Tag color={tag.color} key={tag.label}>
                      {tag.label}: {tag.value}
                    </Tag>
                  ))}
                </div>
              </Card>
            )}
            {signals && <>{renderSignals()}</>}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
