app = Flask(__name__)
talisman = Talisman(app)

load_dotenv()

limiter = Limiter(
    get_remote_address, 
    app=app,
    default_limits=["1500 per day", "120 per hour"],
    storage_uri="memory://"
)

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config["SECRET_KEY"] = os.getenv('SECRET_DATABASE_KEY')
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['BABEL_DEFAULT_LOCALE'] = 'en'  # Set the default locale to English
app.config['BABEL_DEFAULT_TIMEZONE'] = 'UTC'  # Set the default timezone to UTC
app.config['DEBUG'] = os.getenv('MODE')=="development"

babel = Babel(app)
db = SQLAlchemy(app)

origins=["http://localhost:3000"]
blocked_ips = [""]
whitelisted_ips = ["127.0.0.1"]
CORS(app,origins=origins)

API_SECRET_KEY = os.getenv('API_SECRET_KEY')
ENCTOKEN_LOGIN = os.getenv('ENCTOKEN_LOGIN')

kite_instance=None
sentiment_analyzer = pipeline("sentiment-analysis", model="yiyanghkust/finbert-tone")
time_frame_mapping = {
    '1': {'interval': 'minute', 'days': 60},
    '3': {'interval': '3minute', 'days': 100},
    '5': {'interval': '5minute', 'days': 100},
    '10': {'interval': '10minute', 'days': 100},
    '15': {'interval': '15minute', 'days': 200},
    '30': {'interval': '30minute', 'days': 200},
    '60': {'interval': '60minute', 'days': 400},
    '1d': {'interval': 'day', 'days': 2000}
}

@app.after_request
def add_csp(response):
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; object-src 'none';"
    return response

@app.before_request
def enforce_https():
    if os.getenv('MODE')!="development" and not request.is_secure:
        url = request.url.replace("http://", "https://", 1)
        return redirect(url, code=301)
    
@app.before_request
def block_ip():
    if request.remote_addr in blocked_ips:
        abort(403)  # Forbidden

# Whitelist certain IPs to bypass rate limits
@limiter.request_filter
def ip_whitelist():
    return request.remote_addr in whitelisted_ips