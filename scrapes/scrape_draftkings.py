import requests
import csv
import os
import time
import random
import re
from collections import defaultdict
from datetime import datetime

# --- CONFIGURATION ---
REGION_CODE = "dkusoh"  # DraftKings US Ohio
LEAGUE_ID = "42648"      # NBA league ID

PLAYER_PROP_CATEGORIES = {
    'Points': '12488',
    'Threes Made': '12497',
    'Rebounds': '12492',
    'Assists': '12495'
}

OUTPUT_DIR = "draftkings_nba_props"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- SESSION SETUP ---
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Referer": "https://sportsbook.draftkings.com/",
    "Origin": "https://sportsbook.draftkings.com",
    "Accept": "*/*",
})

# --- FETCH PROP DATA ---
def fetch_props(subcategory_id, prop_name):
    url = (
        f"https://sportsbook-nash.draftkings.com/sites/US-OH-SB/api/sportscontent/controldata/"
        f"league/leagueSubcategory/v1/markets?isBatchable=false&templateVars={LEAGUE_ID}%2C{subcategory_id}"
        f"&eventsQuery=%24filter%3DleagueId%20eq%20%27{LEAGUE_ID}%27%20AND%20clientMetadata%2FSubcategories%2Fany%28s%3A%20s%2FId%20eq%20%27{subcategory_id}%27%29"
        f"&marketsQuery=%24filter%3DclientMetadata%2FsubCategoryId%20eq%20%27{subcategory_id}%27%20AND%20tags%2Fall%28t%3A%20t%20ne%20%27SportcastBetBuilder%27%29&include=Events&entity=events"
    )
    print(f"Fetching '{prop_name}' props...")
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        print(f"  ✅ '{prop_name}' data received successfully.")
        return data
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Error fetching '{prop_name}': {e}")
        return None

# --- PARSE PROP DATA ---
def parse_props(data, prop_type_name):
    if not data:
        return []

    events = data.get('events', [])
    markets = data.get('markets', [])
    selections = data.get('selections', [])

    event_map = {event['id']: event for event in events}

    selections_by_market = defaultdict(dict)
    for sel in selections:
        market_id = sel.get('marketId')
        label = sel.get('label', '').lower()
        if market_id and label in ['over', 'under']:
            selections_by_market[market_id][label] = sel

    parsed_props = []
    for market in markets:
        market_id = market.get('id')
        outcomes = selections_by_market.get(market_id)
        if not outcomes or 'over' not in outcomes or 'under' not in outcomes:
            continue
        over_sel = outcomes['over']
        under_sel = outcomes['under']

        # Find player name from market name
        search_name = prop_type_name.split(' ')[0]
        market_name = market['name']
        match = re.search(r'\b' + re.escape(search_name), market_name, re.IGNORECASE)
        if match:
            player_name = market_name[:match.start()].strip()
        else:
            player_name = market_name.replace(f" {prop_type_name} O/U", "").strip()

        # Event date
        event_id = market.get('eventId')
        event = event_map.get(event_id, {})
        start_event_date = event.get('startEventDate')
        if start_event_date:
            game_date = start_event_date.split('T')[0]  # YYYY-MM-DD
        else:
            game_date = datetime.today().strftime('%Y-%m-%d')  # fallback

        parsed_props.append({
            'player_name': player_name,
            'game': event.get('name', 'Unknown Game'),
            'prop_type': prop_type_name,
            'line': over_sel.get('points'),
            'over_odds': over_sel.get('displayOdds', {}).get('american'),
            'under_odds': under_sel.get('displayOdds', {}).get('american'),
            'sportsbook': 'DraftKings',
            'game_date': game_date
        })

    print(f"  -> Found {len(parsed_props)} {prop_type_name} props")
    return parsed_props

# --- SAVE CSV ---
def save_props_to_csv(props):
    if not props:
        return
    # Group props by game_date
    grouped = defaultdict(list)
    for prop in props:
        grouped[prop['game_date']].append(prop)

    for date, props_list in grouped.items():
        file_path = os.path.join(OUTPUT_DIR, f"draftkings_nba_props_{date}.csv")
        fieldnames = ['player_name', 'game', 'prop_type', 'line', 'over_odds', 'under_odds', 'sportsbook', 'game_date']
        file_exists = os.path.exists(file_path)
        try:
            with open(file_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                if not file_exists:
                    writer.writeheader()
                writer.writerows(props_list)
            print(f"  ✅ Saved {len(props_list)} props to {file_path}")
        except Exception as e:
            print(f"  ❌ Error saving CSV for {date}: {e}")

# --- MAIN EXECUTION ---
def run_nba_scraper():
    all_props = []
    print("\n--- Starting NBA Player Prop Scraping ---")
    for prop_name, sub_id in PLAYER_PROP_CATEGORIES.items():
        data = fetch_props(sub_id, prop_name)
        props = parse_props(data, prop_name)
        all_props.extend(props)
        time.sleep(random.uniform(1.5, 3.0))

    save_props_to_csv(all_props)
    print("\n✅ NBA DraftKings prop scraping complete!")

if __name__ == "__main__":
    run_nba_scraper()
