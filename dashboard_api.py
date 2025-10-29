# dashboard_api.py
from flask import Flask, jsonify, Response
from flask_cors import CORS
from props_manager import PropsManager
from datetime import datetime
import subprocess # <-- Import subprocess
import sys # <-- Import sys to get Python executable path
import os # <-- Import os to check script path

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# --- Data Fetching Routes ---
@app.route('/api/props/<date>')
def get_props(date):
    manager = PropsManager(base_folder="props_data", use_db=True)
    try:
        props = manager.get_all_props_comparison(date)
        return jsonify(props)
    except Exception as e:
        print(f"Error in /api/props/{date}: {e}")
        return jsonify({"error": "Failed to fetch props data"}), 500
    finally:
        manager.close()


@app.route('/api/arbitrage/<date>')
def get_arbitrage(date):
    manager = PropsManager(base_folder="props_data", use_db=True)
    try:
        arbs = manager.find_arbitrage(date, min_profit=0.1)
        return jsonify(arbs)
    except Exception as e:
        print(f"Error in /api/arbitrage/{date}: {e}")
        return jsonify({"error": "Failed to fetch arbitrage data"}), 500
    finally:
        manager.close()


@app.route('/api/discrepancies/<date>')
def get_discrepancies(date):
    manager = PropsManager(base_folder="props_data", use_db=True)
    try:
        disc = manager.find_line_discrepancies(date, min_diff=0.5)
        return jsonify(disc)
    except Exception as e:
        print(f"Error in /api/discrepancies/{date}: {e}")
        return jsonify({"error": "Failed to fetch discrepancies data"}), 500
    finally:
        manager.close()


@app.route('/api/best-odds/<date>')
def get_best_odds(date):
    manager = PropsManager(base_folder="props_data", use_db=True)
    try:
        # This now finds bets where one side is + and other is -
        odds = manager.find_best_odds(date, min_odds_diff=5)
        return jsonify(odds)
    except Exception as e:
        print(f"Error in /api/best-odds/{date}: {e}")
        return jsonify({"error": "Failed to fetch best odds data"}), 500
    finally:
        manager.close()


@app.route('/api/value-bets/<date>')
def get_value_bets(date):
    manager = PropsManager(base_folder="props_data", use_db=True)
    try:
        # This finds bets with the largest odds disagreement, regardless of +/-
        value_bets = manager.find_value_bets(date, min_edge=1.5, min_odds_diff=20)
        return jsonify(value_bets)
    except Exception as e:
        print(f"Error in /api/value-bets/{date}: {e}")
        return jsonify({"error": "Failed to fetch value bets data"}), 500
    finally:
        manager.close()

# <-- MODIFIED API ENDPOINT -->
@app.route('/api/consensus-bets/<date>')
def get_consensus_bets(date):
    manager = PropsManager(base_folder="props_data", use_db=True)
    try:
        # Finds bets where both books favor a side, but one has a discount
        # MODIFIED: Changed min_odds_diff to 20 to match your manager file's new default
        bets = manager.find_consensus_bets(date, min_odds_diff=20) 
        return jsonify(bets)
    except Exception as e:
        print(f"Error in /api/consensus-bets/{date}: {e}")
        return jsonify({"error": "Failed to fetch consensus bets data"}), 500
    finally:
        manager.close()


@app.route('/api/today')
def get_today():
    try:
        return jsonify({'date': datetime.now().strftime('%Y-%m-%d')})
    except Exception as e:
        print(f"Error in /api/today: {e}")
        return jsonify({"error": "Failed to get today's date"}), 500

# --- Action Route to Trigger Scrapers ---
@app.route('/api/trigger-scrape', methods=['POST']) # Use POST for actions
def trigger_scrape():
    # Assumes run_all_scrapers.py is in the same directory as dashboard_api.py
    script_dir = os.path.dirname(os.path.abspath(__file__))
    scraper_script_path = os.path.join(script_dir, "run_all_scrapers.py")
    python_executable = sys.executable # Use the same python that runs Flask

    print(f"[{datetime.now()}] API received request to trigger scrapers...")
    print(f"Attempting to run: {python_executable} {scraper_script_path}")

    if not os.path.exists(scraper_script_path):
        print(f"Error: Scraper script '{scraper_script_path}' not found.")
        return jsonify({"error": f"Scraper script not found: {scraper_script_path}"}), 500

    try:
        # Run in the background (non-blocking) - API returns faster
        print(f"Starting scraper script: {scraper_script_path}")
        # Using Popen to run non-blocking. Output will go to Flask console.
        process = subprocess.Popen([python_executable, scraper_script_path])
        print(f"Scraper process started with PID: {process.pid}")
        # API returns immediately, scraper runs in background
        return jsonify({"message": "Scraping process initiated."}), 202 # 202 Accepted status

    except Exception as e:
        print(f"An unexpected error occurred while trying to start scraper: {e}")
        # Log the full exception for debugging
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to start scraper process: {str(e)}"}), 500


if __name__ == '__main__':
    # Use host='0.0.0.0' to make it accessible on your network if needed
    # Use debug=False for production deployment
    app.run(debug=True, host='0.0.0.0', port=5000)
