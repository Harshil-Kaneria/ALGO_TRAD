from flask import Flask, jsonify, request, render_template
from kite_trade import KiteApp

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    profile_data = None
    instruments_data = None
    enctoken = ''  # Initialize enctoken for the input field

    if request.method == 'POST':
        enctoken = request.form.get('enctoken')
        # Create Kite object with the user's token
        kite = KiteApp(enctoken=enctoken)
        profile_data = kite.profile()
        instruments_data = kite.instruments('BSE')

    return render_template('index.html', profile_data=profile_data, instruments_data=instruments_data, enctoken=enctoken)

if __name__ == '__main__':
    app.run(debug=True)
