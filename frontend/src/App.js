import io from 'socket.io-client';
import React, { useState, useEffect,useCallback } from 'react';
import axios from 'axios';
import GainersTable from './GainersTable';
import { Card, Tag, Button, List, Typography, notification,Select } from 'antd';

function App() {
  const [profileData, setProfileData] = useState(null);
  const [isMarketOpen, setIsMarketOpen] = useState(false);
  const [stockName, setStockName] = useState('');
  const [quantity, setQuantity] = useState('');
  const [exchange, setExchange] = useState('NSE');
  const [profitPercentage, setProfitPercentage] = useState(0.75);
  const [checkPivot, setCheckPivot] = useState(true);
  const [instruments, setInstruments] = useState([]);
  const [filteredInstruments, setFilteredInstruments] = useState([]);
  const [message, setMessage] = useState('');
  const [dropdownVisible, setDropdownVisible] = useState(false);
  const [gainers, setGainers] = useState([]);
  const [selectedGainer, setSelectedGainer] = useState(null);
  const [news, setNews] = useState([]);
  const [sentiment, setSentiment] = useState([]);
  const [isScrapingStarted, setIsScrapingStarted] = useState(false);
  const [searchSymbol, setSearchSymbol] = useState('');
  const [searchResult, setSearchResult] = useState(null);
  const [isSearchScrapingStarted, setIsSearchScrapingStarted] = useState(false);
  const [searchOptions, setSearchOptions] = useState([]);

  const [socket, setSocket] = useState(null);
  const [signals, setSignals] = useState(null);
  
  // Add this function to handle signal updates
  const handleSignalUpdate = useCallback((data) => {
    if (data.symbol === searchSymbol) {
      console.log('data.signals',data.signals);
      setSignals(data.signals);
      
      // Update UI based on signals
      if (data.signals.buy_signal) {
        notification.success({
          message: 'Buy Signal',
          description: `Buy signal detected for ${data.symbol} at ${data.signals.entry_price}`,
          placement: 'topRight', // You can adjust the placement
        });
      }
    
      if (data.signals.sell_signal) {
        notification.error({
          message: 'Sell Signal',
          description: `Sell signal detected for ${data.symbol} at ${data.signals.entry_price}`,
          placement: 'topRight', // You can adjust the placement
        });
      }

    }
  }, [searchSymbol]);

  // Add WebSocket connection effect
  useEffect(() => {
    const newSocket = io(process.env.REACT_APP_API_BASE_URL);
    
    newSocket.on('connect', () => {
      console.log('Connected to WebSocket');
    });
    
    newSocket.on('signal_update', handleSignalUpdate);
    
    newSocket.on('disconnect', () => {
      console.log('Disconnected from WebSocket');
    });
    
    setSocket(newSocket);
    
    return () => {
      newSocket.close();
    };
  }, [handleSignalUpdate]);

  const renderSignals = () => {
    if (!signals) return null;

    return (
      <Card className="mb-4" title="Advanced Trading Analysis" extra={<span className="text-gray-500">Last Updated: {new Date().toLocaleString()}</span>}>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Trading Signals */}
          <Card type="inner" title="Trading Signals" className="bg-gray-50">
            <div className="space-y-2">
              <Tag color={signals.buy_signal ? "green" : "red"} className="w-full text-center">
                <i className={signals.buy_signal ? "icon-buy" : "icon-sell"} /> Buy Signal: {signals.buy_signal ? "YES" : "NO"}
              </Tag>
              <Tag color={signals.sell_signal ? "red" : "default"} className="w-full text-center">
                <i className={signals.sell_signal ? "icon-sell" : "icon-neutral"} /> Sell Signal: {signals.sell_signal ? "YES" : "NO"}
              </Tag>
            </div>
          </Card>

          {/* Price Information */}
          <Card type="inner" title="Price Analysis" className="bg-gray-50">
            <p><strong>Current Price:</strong> <span className={signals.current_price < signals.entry_price ? "text-red-500" : "text-green-500"}>{signals.current_price.toFixed(2)}</span></p>
            <p><strong>Entry Price:</strong> {signals.entry_price.toFixed(2)}</p>
            <p><strong>Predicted Price:</strong> {signals.predictions.predicted_price.toFixed(2)}</p>
            <p><strong>Confidence:</strong> {signals.predictions.confidence}</p>
            <p><strong>Profit/Loss Percentage:</strong><span className="text-blue-500">({((signals.predictions.predicted_price - signals.current_price) / signals.current_price * 100).toFixed(2)}%) </span></p>
          </Card>

          {/* Forecast Section */}
          <Card type="inner" title="Forecast (Day 1 - Day 5)" className="bg-gray-50">
            <div className="space-y-2">
              {signals.forecast.daily_forecasts.map((forecast, index) => (
                <p key={index}>
                  <strong>Day {index + 1}:</strong> {forecast.predicted_price.toFixed(2)} 
                  <span className={`text-${forecast.profit_loss_pct > 0 ? "green" : "red"}-500`}>
                    ({forecast.profit_loss_pct.toFixed(2)}%)
                  </span>
                </p>
              ))}
            </div>
          </Card>

          {/* Risk Management */}
          {signals.risk_levels && (
            <Card type="inner" title="Risk Management" className="bg-gray-50">
              <p><strong>Stop Loss:</strong> ${signals.risk_levels.stop_loss.toFixed(2)}</p>
              <p><strong>Take Profit:</strong> ${signals.risk_levels.take_profit.toFixed(2)}</p>
              <p><strong>Risk/Reward Ratio:</strong> {signals.risk_levels.risk_reward_ratio}</p>
            </Card>
          )}

          {/* Technical Analysis */}
          <Card type="inner" title="Technical Analysis" className="bg-gray-50">
            <p><strong>RSI:</strong> {signals.indicators.rsi.toFixed(2)}</p>
            <p><strong>MACD:</strong> {signals.indicators.macd.value.toFixed(2)} (Signal: {signals.indicators.macd.signal.toFixed(2)})</p>
            <p><strong>Bollinger Bands:</strong></p>
            <ul>
              <li><strong>Upper:</strong> {signals.indicators.bollinger_bands.upper.toFixed(2)}</li>
              <li><strong>Middle:</strong> {signals.indicators.bollinger_bands.middle.toFixed(2)}</li>
              <li><strong>Lower:</strong> {signals.indicators.bollinger_bands.lower.toFixed(2)}</li>
            </ul>
          </Card>

          {/* Market Context */}
          <Card type="inner" title="Market Context" className="bg-gray-50">
            <p><strong>Volume Trend:</strong> {signals.market_context.volume_trend}</p>
            <p><strong>Trend Strength:</strong> {signals.market_context.trend_strength}</p>
            <p><strong>Volatility:</strong> {signals.market_context.volatility}</p>
            <p><strong>ADX:</strong> {signals.market_context.adx.toFixed(2)}</p>
          </Card>

          {/* Trend Analysis */}
          <Card type="inner" title="Trend Analysis" className="bg-gray-50">
            <p><strong>Short Term:</strong> {signals.trend_analysis.short_term}</p>
            <p><strong>Medium Term:</strong> {signals.trend_analysis.medium_term}</p>
            <p><strong>Long Term:</strong> {signals.trend_analysis.long_term}</p>
          </Card>

          {/* Volume Information */}
          <Card type="inner" title="Volume Analysis" className="bg-gray-50">
            <p><strong>Current Volume:</strong> {signals.volume.current.toLocaleString()}</p>
            <p><strong>Average Volume:</strong> {signals.volume.average.toLocaleString()}</p>
            <p><strong>Volume Trend:</strong> {signals.volume.trend}</p>
          </Card>

          {/* Momentum Indicators */}
          <Card type="inner" title="Momentum Indicators" className="bg-gray-50">
            <p><strong>Momentum:</strong> {signals.momentum.value.toFixed(2)}</p>
            <p><strong>Rate of Change (ROC):</strong> {signals.momentum.roc.toFixed(2)}</p>
          </Card>

          {/* Pattern Recognition */}
          <Card type="inner" title="Patterns Detected" className="bg-gray-50">
            {Object.entries(signals.patterns).map(([pattern, value]) => (
              value !== 0 && (
                <Tag key={pattern} color={value > 0 ? "green" : "red"}>
                  {pattern}
                </Tag>
              )
            ))}
            {Object.values(signals.patterns).every(value => value === 0) && (
              <p>No patterns detected.</p>
            )}
          </Card>
        </div>
      </Card>
    );
};

  // Fetch user profile data
  const fetchProfileData = async () => {
    try {
      const response = await axios.get(`${process.env.REACT_APP_API_BASE_URL}/api/profile`);
      setProfileData(response.data.profile_data);
      setIsMarketOpen(response.data.market_status);
      if (response.data.market_status === false) {
        setMessage('Please wait until market open');
      }
    } catch (error) {
      setMessage(error.response?.data?.message || 'Error logging in');
    }
  };

  // Fetch instruments based on selected exchange
  const fetchInstruments = async () => {
    try {
      const response = await axios.get(`${process.env.REACT_APP_API_BASE_URL}/api/instruments?exchange=${exchange}`);
      setInstruments(response.data);
    } catch (error) {
      console.error('Error fetching instruments:', error);
    }
  };

  const handleSearchInput = (value) => {
    if (!value) {
      setSearchOptions([]);
      return;
    }

    const filtered = instruments.filter(instrument =>
      instrument.tradingsymbol.toLowerCase().includes(value.toLowerCase()) ||
      instrument.name.toLowerCase().includes(value.toLowerCase())
    );

    const options = filtered.map(instrument => ({
      value: instrument.tradingsymbol,
      label: `${instrument.tradingsymbol} - ${instrument.name}`
    }));

    setSearchOptions(options);
  };

  // Place order function
  const placeOrder = async () => {
    try {
      const response = await axios.post(`${process.env.REACT_APP_API_BASE_URL}/api/order`, {
        name: stockName,
        quantity,
        exchange,
        profit_percentage: profitPercentage,
      });
      setMessage(response.data.message);
    } catch (error) {
      setMessage(error.response?.data?.message || 'Error placing order');
    }
  };

  // Filter instruments based on user input
  const filterInstruments = (input) => {
    const filtered = instruments.filter(instrument =>
      instrument.tradingsymbol.toLowerCase().includes(input.toLowerCase()) ||
      instrument.name.toLowerCase().includes(input.toLowerCase())
    );
    setFilteredInstruments(filtered);
    setDropdownVisible(input.length > 0 && filtered.length > 0);
  };

  // Fetch top gainers
  const fetchGainers = async () => {
    try {
      const response = await axios.get(`${process.env.REACT_APP_API_BASE_URL}/api/gainers`);
      setGainers(response.data);
    } catch (error) {
      console.error('Error fetching gainers:', error);
    }
  };

  // Start scraping for a specific stock
  const startScraping = async (symbol) => {
    setIsScrapingStarted(true);
    setSelectedGainer(symbol);
    try {
      const response = await axios.get(`${process.env.REACT_APP_API_BASE_URL}/api/scrape/${symbol}`);
      setNews(response.data.news);
      setSentiment(response.data.sentiment);
    } catch (error) {
      console.error('Error scraping data:', error);
    }
    setIsScrapingStarted(false);
  };

  useEffect(() => {
    fetchProfileData();
    fetchGainers();
  }, []);

  useEffect(() => {
    if (profileData && isMarketOpen) {
      setStockName('');
      setInstruments([]);
      fetchInstruments();
    }
  }, [exchange, profileData, isMarketOpen]);

  const handleAnalysisSearch = async () => {
    try {
      setSignals(null);
      const response = await axios.get(`${process.env.REACT_APP_API_BASE_URL}/api/signals/${searchSymbol}`);
      if (response.data) {
        console.log('Initial signals:', response.data);
        setSignals(response.data);
      }
    } catch (error) {
      console.error('Error fetching signals:', error);
      notification.error({
        message: 'Error',
        description: error.response?.data?.error || 'Failed to fetch signals',
      });
    }
  };
  
  // Update the WebSocket connection effect
  useEffect(() => {
    const newSocket = io(process.env.REACT_APP_API_BASE_URL, {
      transports: ['websocket'],
      reconnection: true,
      reconnectionAttempts: 5
    });
    
    newSocket.on('connect', () => {
      console.log('Connected to WebSocket');
    });
    
    newSocket.on('signal_update', (data) => {
      console.log('Received signal update:', data);
      if (data.symbol === searchSymbol) {
        console.log('Updating signals for', searchSymbol);
        setSignals(data.signals);
        
        // Notifications for signals
        if (data.signals.buy_signal) {
          notification.success({
            message: 'Buy Signal',
            description: `Buy signal detected for ${data.symbol} at ${data.signals.entry_price}`,
            placement: 'topRight',
          });
        }
        
        if (data.signals.sell_signal) {
          notification.error({
            message: 'Sell Signal',
            description: `Sell signal detected for ${data.symbol} at ${data.signals.entry_price}`,
            placement: 'topRight',
          });
        }
      }
    });
    
    newSocket.on('disconnect', () => {
      console.log('Disconnected from WebSocket');
    });
    
    newSocket.on('error', (error) => {
      console.error('WebSocket error:', error);
    });
    
    setSocket(newSocket);
    
    return () => {
      if (newSocket) {
        newSocket.close();
      }
    };
  }, [searchSymbol]); 

  const handleSearch = async () => {
    handleAnalysisSearch()
    try {
      const response = await axios.get(`${process.env.REACT_APP_API_BASE_URL}/api/search/${searchSymbol}`);
      setSearchResult(response.data);
      setMessage('');
    } catch (error) {
      console.error('Error searching stock:', error);
      setMessage(error.response?.data?.error || 'Error searching stock');
      setSearchResult(null);
    }
  };

  const startSearchScraping = async () => {
    if (isSearchScrapingStarted) return;
    setIsSearchScrapingStarted(true);
    try {
      const response = await axios.get(`${process.env.REACT_APP_API_BASE_URL}/api/scrape/${searchResult.symbol}`);
      setSearchResult(prevState => ({
        ...prevState,
        news: response.data.news,
        sentiment: response.data.sentiment
      }));
    } catch (error) {
      console.error('Error scraping search data:', error);
      setMessage(error.response?.data?.error || 'Error scraping search data');
    } finally {
      setIsSearchScrapingStarted(false);
    }
  };

  return (
    <div className="bg-gray-100 flex items-center justify-center min-h-screen">
      <div className="bg-white rounded-lg shadow-lg p-8 w-3/4 relative">
        <h1 className="text-3xl font-bold text-center mb-6">Kite Smart Trading App</h1>
        <div className="flex items-center mb-6">
          <hr className="flex-grow border-t border-dashed border-gray-400" />
          <p className="mx-4 text-lg text-gray-600 italic">By: Harshil Kaneria</p>
          <hr className="flex-grow border-t border-dashed border-gray-400" />
        </div>

        {profileData ? (
          <div className="mb-6">
            <div className="bg-gray-100 p-6 rounded-lg shadow-md mb-6">
              <div className="flex flex-col items-center mb-4">
                <img
                  src={profileData.avatar_url}
                  alt="Avatar"
                  className="w-32 h-32 rounded-full shadow-md mb-4"
                />
                <h2 className="text-2xl font-semibold mb-2">{profileData.user_name}</h2>
                <p className="text-lg text-gray-600"><strong>Email:</strong> {profileData.email}</p>
                <p className="text-lg text-gray-600"><strong>User ID:</strong> {profileData.user_id}</p>
              </div>
            </div>

            {isMarketOpen && (
              <>
                <div className="mb-6">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="mb-4">
                      <label htmlFor="exchange" className="block text-sm font-medium text-gray-700">Exchange:</label>
                      <select
                        id="exchange"
                        value={exchange}
                        onChange={(e) => setExchange(e.target.value)}
                        className="mt-1 block w-full border border-gray-300 rounded-md p-2"
                      >
                        <option value="NSE">NSE</option>
                        <option value="BSE">BSE</option>
                      </select>
                    </div>

                    <div className="mb-4">
                      <label htmlFor="name" className="block text-sm font-medium text-gray-700">Stock Name:</label>
                      <input
                        type="text"
                        id="name"
                        value={stockName}
                        disabled={instruments.length === 0}
                        onChange={(e) => {
                          setStockName(e.target.value);
                          filterInstruments(e.target.value);
                        }}
                        className="mt-1 block w-full border border-gray-300 rounded-md p-2"
                        placeholder="Stock Name"
                        required
                      />
                      {dropdownVisible && (
                        <div className="absolute bg-white border border-gray-300 w-full rounded-md z-10">
                          {filteredInstruments.map((instrument) => (
                            <div
                              key={instrument.tradingsymbol}
                              onClick={() => {
                                setStockName(instrument.tradingsymbol);
                                setDropdownVisible(false);
                              }}
                              className="p-2 cursor-pointer hover:bg-gray-200"
                            >
                              {instrument.tradingsymbol} - {instrument.name}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="mb-4">
                      <label htmlFor="quantity" className="block text-sm font-medium text-gray-700">Quantity:</label>
                      <input
                        type="number"
                        id="quantity"
                        value={quantity}
                        onChange={(e) => setQuantity(e.target.value)}
                        step="1"
                        min="1"
                        className="mt-1 block w-full border border-gray-300 rounded-md p-2"
                        required
                      />
                    </div>

                    <div className="mb-4">
                      <label htmlFor="profit_percentage" className="block text-sm font-medium text-gray-700">Profit Percentage:</label>
                      <input
                        type="number"
                        id="profit_percentage"
                        value={profitPercentage}
                        onChange={(e) => setProfitPercentage(e.target.value)}
                        className="mt-1 block w-full border border-gray-300 rounded-md p-2"
                        step="0.01"
                        defaultValue={profitPercentage}
                        required
                      />
                    </div>

                    <div className="mb-4">
                      <label htmlFor="check_pivot" className="text-sm font-medium text-gray-700">Check pivot point:</label>
                      <input
                        className='ml-2'
                        type="checkbox"
                        id="check_pivot"
                        checked={checkPivot}
                        onChange={(e) => setCheckPivot(e.target.checked)}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <button
                      onClick={placeOrder}
                      className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 transition"
                    >
                      Submit This Order
                    </button>
                  </div>
                </div>


                <div className="mb-6">
                  <hr className="flex-grow border-t border-dashed border-gray-400 mb-4" />
                  <h2 className="text-2xl font-bold mb-4">Search Stock</h2>
                  <div className="flex items-center mb-4">
                  <Select
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
        style={{ width: '100%' }}
        className="flex-grow"
      />
      <Button
        type="primary"
        onClick={handleSearch}
        className="ml-2"
      >
        Search
      </Button>
                  </div>
                  {searchResult && (
                    <Card className="mb-4" title={`${searchResult.company} (${searchResult.symbol})`}>
                      <p><strong>Price:</strong> {searchResult.price}</p>
                      <p><strong>Change:</strong> {searchResult.change}</p>
                      <hr className="my-2" />

                      <div className="flex flex-wrap">
                        <p><strong>Position:</strong> <Tag color="blue">{searchResult.position}</Tag></p>
                        <Tag color="blue">PP: {searchResult.pivot_points.pp}</Tag><br />
                      </div>
                      <div className="flex flex-wrap">
                        <Tag color="red">R1: {searchResult.pivot_points.r1}</Tag><br />
                        <Tag color="red">R2: {searchResult.pivot_points.r2}</Tag><br />
                        <Tag color="red">R3: {searchResult.pivot_points.r3}</Tag><br />
                      </div>
                      <div className="flex flex-wrap">
                        <Tag color="green">S1: {searchResult.pivot_points.s1}</Tag><br />
                        <Tag color="green">S2: {searchResult.pivot_points.s2}</Tag><br />
                        <Tag color="green">S3: {searchResult.pivot_points.s3}</Tag><br />
                      </div>
                      <hr className="my-2" />
                      <div className='flex justify-center'>
                        <Button
                          onClick={startSearchScraping}
                          disabled={isSearchScrapingStarted}
                          type="primary"
                          loading={isSearchScrapingStarted}
                        >
                          {isSearchScrapingStarted ? 'Scraping...' : 'Start Scraping'}
                        </Button>
                      </div>
                    </Card>
                  )}
                  {((searchResult && signals)) && (<>{renderSignals()}</>)}
                  {searchResult && searchResult.news && (
                    <Card className="mb-6" title={`News and Sentiment for ${searchResult.symbol}`} bordered>
                      <List
                        itemLayout="vertical"
                        dataSource={searchResult.news}
                        renderItem={(item, index) => (
                          <List.Item key={index}>
                            <Typography.Title level={4} style={{ margin: 0 }}>
                              {item.title}
                            </Typography.Title>
                            <Typography.Paragraph>
                              Published By - <strong>{item.publisher}</strong> on{' '}
                              <strong>{item.publish_time}</strong>
                            </Typography.Paragraph>
                            <a href={item.url} target="_blank" rel="noopener noreferrer">
                              Read More
                            </a>
                            <br />
                            <Tag color={searchResult.sentiment[index].sentiment === 'Positive' ? 'green' : searchResult.sentiment[index].sentiment === 'Negative' ? 'red' : 'gold'}>
                              Sentiment: {searchResult.sentiment[index].sentiment}
                            </Tag>
                            <Tag color="blue">Score: {searchResult.sentiment[index].score}</Tag>
                          </List.Item>
                        )}
                      />
                    </Card>
                  )}
                </div>

                {gainers.length > 0 && (
                  <GainersTable
                    gainers={gainers}
                    isScrapingStarted={isScrapingStarted}
                    selectedGainer={selectedGainer}
                    startScraping={startScraping}
                  />
                )}

                {news.length > 0 && (
                  selectedGainer && (
                    <Card className="mb-6" title={`News and Sentiment for ${selectedGainer}`} bordered>
                      <List
                        itemLayout="vertical"
                        dataSource={news}
                        renderItem={(item, index) => (
                          <List.Item key={index}>
                            <Typography.Title level={4} style={{ margin: 0 }}>
                              {item.title}
                            </Typography.Title>
                            <Typography.Paragraph>
                              Published By - <strong>{item.publisher}</strong> on{' '}
                              <strong>{item.publish_time}</strong>
                            </Typography.Paragraph>
                            <a href={item.url} target="_blank" rel="noopener noreferrer">
                              Read More
                            </a>
                            <br />
                            <Tag color={sentiment[index].sentiment === 'Positive' ? 'green' : sentiment[index].sentiment === 'Negative' ? 'red' : 'gold'}>
                              Sentiment: {sentiment[index].sentiment}
                            </Tag>
                            <Tag color="blue">Score: {sentiment[index].score}</Tag>
                          </List.Item>
                        )}
                      />
                    </Card>
                  )
                )}
              </>
            )}
          </div>
        ) : (
          <p className="mt-4 text-red-600">Loading or not working</p>
        )}

        {message && <p className="mt-4 text-red-600">{message}</p>}
      </div>
    </div>
  );
}

export default App;
