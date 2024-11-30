@app.route('/api/login', methods=['POST'])
def login_user():
    data = request.get_json()
    email = data.get('email')
    login_pin = data.get('loginPin')

    if not email or not login_pin:
        return encrypt_message({"message": "Email and PIN are required."}), 400

    # Fetch the user from the database
    user = UserTable.query.filter_by(email=email).first()

    if not user or user.loginPin != login_pin:
        return encrypt_message({"message": "Invalid email or PIN."}), 401

    # Generate a new session token
    new_token = secrets.token_hex(32)

    # Update the user with the new token, invalidating the old session
    user.session_token = new_token
    db.session.commit()

    return encrypt_message({"message": "Login successful.", "token": new_token}), 200

@app.route('/api/profile', methods=['GET'])
@token_required
def profile():
    kite = get_kite_instance()
    if not kite:
        return encrypt_message({"message": "KiteApp instance is not initialized."}), 500

    profile_data = kite.profile()
    if profile_data is None:
        return encrypt_message({"message": "Failed to retrieve profile data."}), 500
    
    user = g.get('user')
    if not user:
        return encrypt_message({"message": "User not found!"}), 404
    
    if isinstance(user, UserTable):
        user = {
            "name": user.name,
            "email": user.email
        }

    
    return encrypt_message({"profile_data": {'isWorking':True,"user":user}, "market_status": is_market_open()})

@app.route('/api/instruments', methods=['GET'])
@token_required
def get_instruments():
    exchange = request.args.get('exchange').upper()
    kite = get_kite_instance()
    if not kite:
        return encrypt_message({"message": "KiteApp instance is not initialized."}), 400

    instruments = kite.instruments(exchange)
    return encrypt_message(instruments)

@app.route('/api/gainers')
@token_required
def get_gainers_api():
    gainers = get_top_gainers()
    return encrypt_message(gainers)

@app.route('/api/search',methods=['GET'])
@token_required
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
@token_required
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
@token_required
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
    
@app.route('/api/logout', methods=['GET'])
@token_required
def logout_user():
    user = g.get('user')
    if not user:
        return encrypt_message({"message": "User not found!"}), 404

    user.session_token = None
    db.session.commit()
    return encrypt_message({"message": "Logout successful."}), 200
