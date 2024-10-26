import React, { useState, useEffect } from 'react';
import axios from 'axios';

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

                {gainers.length > 0 && (<>
                  <div className="mb-6">
                    <h2 className="text-2xl font-bold mb-4">Top Gainers</h2>
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                      {gainers.map((gainer, index) => (
                        <div key={index} className="bg-gray-100 p-4 rounded-lg shadow">
                          <h3 className="text-lg font-semibold">{gainer.symbol} - {gainer.company}</h3>
                          <p>Price: {gainer.price}</p>
                          <p>Change: {gainer.change}</p>
                          <hr className="flex-grow border-t border-dashed border-gray-400 mt-1" />
                          <p className="rounded-full bg-blue-500 text-white px-1 mt-1">PP: {gainer.stock_info.pivot_points.pp}</p>
                          <p className="rounded-full bg-red-500 text-white px-1 mt-1">R1: {gainer.stock_info.pivot_points.r1}</p>
                          <p className="rounded-full bg-red-500 text-white px-1 mt-1">R2: {gainer.stock_info.pivot_points.r2}</p>
                          <p className="rounded-full bg-red-500 text-white px-1 mt-1">R3: {gainer.stock_info.pivot_points.r3}</p>
                          <p className="rounded-full bg-green-500 text-white px-1 mt-1">S1: {gainer.stock_info.pivot_points.s1}</p>
                          <p className="rounded-full bg-green-500 text-white px-1 mt-1">S2: {gainer.stock_info.pivot_points.s2}</p>
                          <p className="rounded-full bg-green-500 text-white px-1 mt-1 mb-1">S3: {gainer.stock_info.pivot_points.s3}</p>
                          <hr className="flex-grow border-t border-dashed border-gray-400" />
                          <p className="rounded-full bg-yellow-500 text-white px-1 mt-1">Position: {gainer.stock_info.position}</p>
                          <button
                            onClick={() => startScraping(gainer.symbol)}
                            disabled={isScrapingStarted}
                            className="text-center mt-2 bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600 transition"
                          >
                            {isScrapingStarted && selectedGainer === gainer.symbol ? 'Scraping...' : 'Start Scraping'}
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                </>)}

                {news.length > 0 && (<>
                  {selectedGainer && (
                    <div className="mb-6">
                      <h2 className="text-2xl font-bold mb-4">News and Sentiment for {selectedGainer}</h2>
                      <ul className="list-disc pl-5">
                        {news.map((item, index) => (
                          <li key={index} className="mb-2">
                            {item.title}
                            <br />
                            <a href={item.url} target="_blank" rel="noopener noreferrer">Read More</a>
                            <br /><span className={`font-bold ${sentiment[index].sentiment == 'POSITIVE' ? 'text-green-600' : sentiment[index].sentiment == 'NEGATIVE' ? 'text-red-600' : 'text-yellow-600'}`}>
                              Sentiment: {sentiment[index].sentiment}<br />
                              Score: {sentiment[index].score}
                            </span>
                            <hr />
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>)}
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
