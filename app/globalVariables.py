app = Flask(__name__)
CORS(app)
load_dotenv()

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
