import requests
import json
import os
import time
import random
import re
from collections import defaultdict
from datetime import datetime
from dateutil import tz
from props_manager import PropsManager

# --- CONFIGURATION ---
REGION_CODE = "dkusoh"
LEAGUE_ID = "42648"

PLAYER_PROP_CATEGORIES = {
    'Points': '12488',
    'Threes Made': '12497',
    'Rebounds': '12492',
    'Assists': '12495',
    'Rebounds + Assists': '9974',
    'Points + Rebounds + Assists': '5001',
    'Points + Rebounds': '9976',
    'Points + Assists': '9973',
    'Steals': '13508',
    'Blocks': '13780',
    'Steals + Blocks': '13781'
}

# --- SESSION SETUP ---
def create_fresh_session():
    """Create a new session with fresh headers to avoid caching"""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Referer": "https://sportsbook.draftkings.com/",
        "Origin": "https://sportsbook.draftkings.com",
        "Accept": "*/*",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    })
    return session

# --- FETCH PROP DATA ---
def fetch_props(session, subcategory_id, prop_name):
    # Add timestamp to bust any caching
    timestamp = int(time.time() * 1000)
    
    url = (
        f"https://sportsbook-nash.draftkings.com/sites/US-OH-SB/api/sportscontent/controldata/"
        f"league/leagueSubcategory/v1/markets?isBatchable=false&templateVars={LEAGUE_ID}%2C{subcategory_id}"
        f"&eventsQuery=%24filter%3DleagueId%20eq%20%27{LEAGUE_ID}%27%20AND%20clientMetadata%2FSubcategories%2Fany%28s%3A%20s%2FId%20eq%20%27{subcategory_id}%27%29"
        f"&marketsQuery=%24filter%3DclientMetadata%2FsubCategoryId%20eq%20%27{subcategory_id}%27%20AND%20tags%2Fall%28t%3A%20t%20ne%20%27SportcastBetBuilder%27%29&include=Events&entity=events"
        f"&_={timestamp}"
    )
    print(f"Fetching '{prop_name}' props...")
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Check for actual market data
        markets = data.get('markets', [])
        selections = data.get('selections', [])
        
        print(f"  ✅ '{prop_name}' data received - {len(markets)} markets, {len(selections)} selections")
        print(f"  ⏰ Fetched at: {datetime.now().strftime('%H:%M:%S')}")
        
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
        start_event_date_str = event.get('startEventDate')
        
        if start_event_date_str:
            try:
                if start_event_date_str.endswith('Z'):
                    start_event_date_str = start_event_date_str[:-1] + '+00:00'
                
                utc_time = datetime.fromisoformat(start_event_date_str)
                eastern_tz = tz.gettz('America/New_York')
                local_time = utc_time.astimezone(eastern_tz)
                game_date = local_time.strftime('%Y-%m-%d')
            except ValueError:
                game_date = start_event_date_str.split('T')[0]
        else:
            game_date = datetime.today().strftime('%Y-%m-%d')

        parsed_props.append({
            'player': player_name.lower(),
            'game': event.get('name', 'Unknown Game'),
            'prop_type': prop_type_name.lower(),
            'line': over_sel.get('points'),
            'over_odds': over_sel.get('displayOdds', {}).get('american'),
            'under_odds': under_sel.get('displayOdds', {}).get('american'),
            'sportsbook': 'DraftKings',
            'game_date': game_date
        })

    print(f"  -> Found {len(parsed_props)} {prop_type_name} props")
    return parsed_props

# --- MAIN EXECUTION ---
def run_nba_scraper():
    all_props = []
    scrape_start = datetime.now()
    
    print("\n" + "="*80)
    print("🏀 DRAFTKINGS NBA PROP SCRAPER")
    print(f"Started: {scrape_start.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")
    
    # Create fresh session for each run
    session = create_fresh_session()
    
    for prop_name, sub_id in PLAYER_PROP_CATEGORIES.items():
        data = fetch_props(session, sub_id, prop_name)
        props = parse_props(data, prop_name)
        all_props.extend(props)
        
        # Random delay between requests
        delay = random.uniform(1.5, 3.0)
        time.sleep(delay)

    print(f"\n{'='*80}")
    print(f"SCRAPED {len(all_props)} TOTAL PROPS")
    print(f"{'='*80}\n")

    if all_props:
        # Use PropsManager to save
        print("Saving to database and JSON files...")
        manager = PropsManager(base_folder="props_data", use_db=True)
        manager.save_props(all_props, "draftkings")
        manager.close()
        
        scrape_end = datetime.now()
        duration = (scrape_end - scrape_start).total_seconds()
        
        print(f"\n✅ DraftKings scraping complete!")
        print(f"   Duration: {duration:.1f} seconds")
        print(f"   Props saved: {len(all_props)}")
    else:
        print("\n⚠️  No props were scraped!")

if __name__ == "__main__":
    run_nba_scraper()