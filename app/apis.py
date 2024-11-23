@app.route('/api/profile', methods=['GET'])
def profile():
    kite = get_kite_instance()
    if not kite:
        return encrypt_message({"message": "KiteApp instance is not initialized."}), 400

    profile_data = kite.profile()
    return encrypt_message({"profile_data": profile_data, "market_status": is_market_open()})

@app.route('/api/instruments', methods=['GET'])
def get_instruments():
    exchange = request.args.get('exchange').upper()
    kite = get_kite_instance()
    if not kite:
        return encrypt_message({"message": "KiteApp instance is not initialized."}), 400

    instruments = kite.instruments(exchange)
    return encrypt_message(instruments)

@app.route('/api/gainers')
def get_gainers_api():
    gainers = get_top_gainers()
    return encrypt_message(gainers)

@app.route('/api/search',methods=['GET'])
def search_stock():
    try:
        symbol = request.args.get('symbol')
        exchange = request.args.get('exchange')
        stock_info = get_stock_details(symbol,exchange)
        if not stock_info:
            return encrypt_message({'error': f"Unable to fetch details for {symbol}. Please ensure the symbol is correct and try again."}), 404
        
        return encrypt_message(stock_info)
    
    except Exception as e:
        print(f"Error searching stock {symbol}: {e}")
        return encrypt_message({
            'error': f"Error searching stock {symbol}: {str(e)}"
        }), 400

@app.route('/api/scrape/<symbol>')
def scrape_stock(symbol):
    try:
        # Fetch news and analyze sentiment
        news_items = scrape_stock_news(symbol)
        sentiment = analyze_sentiment(news_items)
        
        return encrypt_message({
            'news': news_items,
            'sentiment': sentiment
        })
    
    except Exception as e:
        print(f"Error scraping stock {symbol}: {e}")
        return encrypt_message({
            'error': f"Error scraping stock {symbol}: {str(e)}"
        }), 400

@app.route('/api/signals', methods=['GET'])
def get_signals():
    try:
        exchange = request.args.get('exchange').upper()
        symbol = request.args.get('symbol')
        time = request.args.get('time')
        
        # userdays = request.args.get('days')
        # try:
        #     userdays = int(userdays) if userdays and userdays.isdigit() else None
        # except ValueError:
        #     userdays = None

        interval,days = get_time_frame_settings(time)

        # effective_days = userdays if userdays is not None else days
        effective_days=days


        # Get historical data
        data = get_historical_data(symbol,exchange,interval,effective_days)
        if data.empty:
            return encrypt_message({'error': f'No historical data available for {symbol}'}), 404
            
        # Calculate indicators
        data = calculate_technical_indicators(data)
        
        # Train models
        regression_model = train_regression_model(data)
        pytorch_model = train_pytorch_model(data)
        
        # Generate signals with the symbol
        signals = generate_signals(data, regression_model, pytorch_model)
        
        if signals is None:
            return encrypt_message({'error': 'Unable to generate signals'}), 500
            
        # Convert numpy values to native types
        signals = convert_to_native_types(signals)
        
        return encrypt_message(signals)
        
    except Exception as e:
        print(f"Error in get_signals for {symbol}: {str(e)}")
        return encrypt_message({
            'error': str(e),
            'details': 'Error occurred while processing signal data'
        }), 500