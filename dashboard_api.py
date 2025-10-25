from flask import Flask, jsonify
from flask_cors import CORS
from props_manager import PropsManager
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

@app.route('/api/props/<date>')
def get_props(date):
    manager = PropsManager(base_folder="props_data", use_db=True)
    props = manager.get_all_props_comparison(date)
    manager.close()
    return jsonify(props)

@app.route('/api/arbitrage/<date>')
def get_arbitrage(date):
    manager = PropsManager(base_folder="props_data", use_db=True)
    arbs = manager.find_arbitrage(date, min_profit=0.1)
    manager.close()
    return jsonify(arbs)

@app.route('/api/discrepancies/<date>')
def get_discrepancies(date):
    manager = PropsManager(base_folder="props_data", use_db=True)
    disc = manager.find_line_discrepancies(date, min_diff=0.5)
    manager.close()
    return jsonify(disc)

@app.route('/api/best-odds/<date>')
def get_best_odds(date):
    manager = PropsManager(base_folder="props_data", use_db=True)
    odds = manager.find_best_odds(date, min_odds_diff=5)
    manager.close()
    return jsonify(odds)

@app.route('/api/today')
def get_today():
    return jsonify({'date': datetime.now().strftime('%Y-%m-%d')})

if __name__ == '__main__':
    app.run(debug=True, port=5000)