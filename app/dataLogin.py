def refresh_kite_instance():
    TOTP_SECRET = os.getenv('TOTP_SECRET')
    USER_ID = os.getenv('USER_ID')
    PASSWORD = os.getenv('PASSWORD')
    totp = pyotp.TOTP(TOTP_SECRET, interval=30, digits=6, digest="sha1")
    current_otp = totp.now()
    new_enctoken = get_enctoken(USER_ID, PASSWORD, current_otp)
    return KiteApp(enctoken=new_enctoken)

def get_kite_instance():
    global kite_instance
    kite = kite_instance
    profile_data = kite.profile()
    if ENCTOKEN_LOGIN == "true":
        return kite
    elif profile_data and "user_id" in profile_data and "user_type" in profile_data:
        return kite
    else:
        refreshed_instance = refresh_kite_instance()
        kite_instance = refreshed_instance
        return kite_instance

if ENCTOKEN_LOGIN == "true":
    ENCTOKEN = os.getenv('ENCTOKEN')
    kite_instance = KiteApp(enctoken=ENCTOKEN)
else:
    kite_instance = refresh_kite_instance()