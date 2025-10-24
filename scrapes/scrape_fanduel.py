import requests
import json
import time
from datetime import datetime, timedelta, timezone
import os # Added os import

def get_nba_main_page_data():
    """Fetches the main NBA page and returns the raw data needed for parsing."""
    url = "https://api.sportsbook.fanduel.com/sbapi/content-managed-page?page=CUSTOM&customPageId=nba&pbHorizontal=false&_ak=FhMFpcPWXMeyZxOx&timezone=America%2FNew_York"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        'x-sportsbook-region': 'OH' # You can change this to your region if needed
    }
    try:
        # Add a timeout to the request
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching NBA main page: {e}")
        return None

def get_all_available_tabs(event_id):
    """
    Fetch the event page to see what tabs are actually available.
    This call does NOT get all the markets, just the tab layout.
    """
    cache_buster = int(time.time())
    url = f"https://api.sportsbook.fanduel.com/sbapi/event-page?_ak=FhMFpcPWXMeyZxOx&eventId={event_id}&_={cache_buster}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        'x-sportsbook-region': 'OH'
    }
    try:
        # Add a timeout to the request
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        # Extract tab information
        tabs = data.get('layout', {}).get('tabs', {})
        available_tabs = []
        for tab_id, tab_info in tabs.items():
            tab_title = tab_info.get('title', '')
            # Create the 'name' parameter which is what the API expects for the 'tab' query
            tab_name = tab_title.lower().replace(' ', '-')
            
            # Filter out tabs that are clearly not player props
            # Updated to include the noisy tabs we found
            if tab_name in ['game-lines', 'popular', 'odds', 'same-game-parlay', 'quick-bets',
                            'half', 'quarter', '4th-quarter', '1st-quarter', '2nd-quarter', '3rd-quarter',
                            'total-parlays', 'team-props', 'race-to', 'margin', 'parlays', 'teasers',
                            'featured', 'live-sgp', 'same-game-parlay™']:
                continue

            available_tabs.append({
                'id': tab_id,
                'title': tab_title,
                'name': tab_name # e.g., 'player-points', 'player-combos'
            })
        return available_tabs
    except Exception as e:
        print(f"Error fetching tabs for event {event_id}: {e}")
        return []

def get_player_props(event_id, prop_tab_name):
    """
    Fetches the player props for a specific game (event_id) and string-based prop tab name.
    """
    cache_buster = int(time.time())
    # Use the string name (e.g., 'player-points') as the 'tab' parameter
    url = f"https://api.sportsbook.fanduel.com/sbapi/event-page?_ak=FhMFpcPWXMeyZxOx&eventId={event_id}&tab={prop_tab_name}&_={cache_buster}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
        'x-sportsbook-region': 'OH'
    }
    try:
        # --- MODIFICATION: Added print statement and timeout ---
        print(f"    ... requesting {prop_tab_name} data from API...")
        response = requests.get(url, headers=headers, timeout=15) # 15-second timeout
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching props for event {event_id}, tab {prop_tab_name}: {e}")
        return None

def extract_team_name_from_logo(logo_url):
    """Extracts and formats a team name from a FanDuel logo URL."""
    if not logo_url:
        return "Unknown Team"
    try:
        team_slug = logo_url.split('/')[-1].replace('.png', '').replace('_jersey', '')
        return ' '.join(word.capitalize() for word in team_slug.split('_'))
    except Exception:
        return "Unknown Team"

def normalize_player_name(name):
    """
    Normalizes player names to a standard format for cross-site comparison.
    e.g., "LeBron James Jr." -> "lebron james"
    """
    if not name:
        return "unknown_player"
    # Lowercase, strip whitespace
    name = name.lower().strip()
    # Remove punctuation
    name = name.replace('.', '').replace("'", "")
    # Remove common suffixes (this list can be expanded)
    suffixes = [' jr', ' sr', ' ii', ' iii', ' iv', ' v']
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    
    # Add any other known special cases here
    # special_cases = {
    #     'mo bamba': 'mohamed bamba',
    # }
    # if name in special_cases:
    #     return special_cases[name]
            
    return name

def normalize_prop_type(prop_name):
    """Normalizes prop type strings to a standard key."""
    if not prop_name:
        return "unknown_prop"
    
    prop_name_lower = prop_name.lower().strip()
    
    # Direct matches - this is the most reliable
    mapping = {
        'points': 'points',
        'rebounds': 'rebounds',
        'assists': 'assists',
        'made threes': 'threes',
        'steals': 'steals',
        'blocks': 'blocks',
        'turnovers': 'turnovers',
        'pts + reb + ast': 'pra',
        'pts + reb': 'pr',
        'pts + ast': 'pa',
        'reb + ast': 'ra',
        'steals + blocks': 'stocks',
    }
    if prop_name_lower in mapping:
        return mapping[prop_name_lower]
    
    # Fallback for partial matches (less reliable but good)
    if 'pts + reb + ast' in prop_name_lower:
        return 'pra'
    if 'pts + reb' in prop_name_lower:
        return 'pr'
    if 'pts + ast' in prop_name_lower:
        return 'pa'
    if 'reb + ast' in prop_name_lower:
        return 'ra'
    if 'steals + blocks' in prop_name_lower:
        return 'stocks'
    if 'points' in prop_name_lower:
        return 'points'
    if 'rebounds' in prop_name_lower:
        return 'rebounds'
    if 'assists' in prop_name_lower:
        return 'assists'
    if 'made threes' in prop_name_lower or '3-point' in prop_name_lower:
        return 'threes'
    if 'steals' in prop_name_lower:
        return 'steals'
    if 'blocks' in prop_name_lower:
        return 'blocks'
    if 'turnovers' in prop_name_lower:
        return 'turnovers'

    # Fallback: just return a cleaned version
    return prop_name_lower.replace(' ', '_')

def get_upcoming_nba_games(main_page_data, days_ahead=7):
    """
    Parses the main page data to find games scheduled within the next N days.
    This function now iterates only over the main events attachment, 
    ensuring no duplicates are returned.
    """
    attachments = main_page_data.get('attachments', {})
    events_data = attachments.get('events', {})
    
    if not events_data:
        print("No events found in the API response.")
        return []
    
    now_utc = datetime.now(timezone.utc)
    upcoming_events = []
    processed_event_ids = set() # Use a set to prevent duplicates

    print(f"Parsing {len(events_data)} total events from main page...")

    # --- MODIFICATION: Single pass over all events ---
    for event_id, event_detail in events_data.items():
        
        if event_id in processed_event_ids:
            continue # Skip if already processed
            
        # --- MODIFICATION: Stricter check for 'openDate' ---
        open_time_str = event_detail.get('openDate')
        if not open_time_str:
            # Skip events with no openDate (e.g., "NBA Specials")
            continue
            
        if open_time_str.endswith('Z'):
            open_time_str = open_time_str[:-1] + '+00:00'
            
        try:
            open_time = datetime.fromisoformat(open_time_str)
            # Check if game is within the specified window
            if open_time > now_utc and open_time - now_utc < timedelta(days=days_ahead):
                # Only add if it's a valid game with a valid date
                event_detail['open_time_parsed'] = open_time # Add parsed datetime
                upcoming_events.append((event_detail, [])) # Market IDs from coupons aren't needed
                processed_event_ids.add(event_id)
        except ValueError:
            # Skip events with unparseable dates
            print(f"  Warning: Could not parse openDate '{open_time_str}' for event {event_id}. Skipping game.")
    
    return upcoming_events

def run_scraper():
    """Main scraper function that prints all props for upcoming NBA games."""
    print("\nFetching all upcoming NBA games...")
    main_page_data = get_nba_main_page_data()
    
    if not main_page_data:
        print("Could not fetch main page data. Exiting.")
        return
    
    upcoming_events = get_upcoming_nba_games(main_page_data)
    
    if not upcoming_events:
        print("Found 0 games scheduled for the upcoming week.")
        return
    else:
        print(f"Found {len(upcoming_events)} games scheduled for the upcoming week.\n")
    
    scrape_time = datetime.now().isoformat()
    
    # --- MODIFICATION: Store props in a dict keyed by game_date ---
    props_by_date = {}
    games_processed = 0
    # --- MODIFICATION: Removed duplicate checker set, it's now in get_upcoming_nba_games ---
    # processed_event_ids = set() 
    
    for event, market_ids in upcoming_events:
        event_id = event['eventId']
        game_name = event['name']
        
        # --- MODIFICATION: Removed duplicate checker logic ---
        # if event_id in processed_event_ids: ...

        # --- MODIFICATION: Get game date string early for header ---
        open_time_dt = event.get('open_time_parsed')
        
        # --- MODIFICATION: This check should always pass now, but good to keep ---
        if not open_time_dt:
            print(f"  Warning: Skipping game {game_name} (ID: {event_id}) due to missing parsed date.")
            continue
            
        game_date_str = open_time_dt.strftime('%Y-%m-%d')
        game_start_time_iso = open_time_dt.isoformat()
        
        # Skip futures and special markets - ONLY process games with @ symbol
        if '@' not in game_name:
            continue
        
        games_processed += 1
        
        print(f"\n{'='*80}")
        # --- MODIFICATION: Add game date to header ---
        print(f"GAME: {game_name} (Event ID: {event_id}) - DATE: {game_date_str}")
        print(f"{'='*80}\n")
        
        # Parse game info
        if ' @ ' in game_name:
            away_team = game_name.split(' @ ')[0]
            home_team = game_name.split(' @ ')[1]
        else:
            away_team = "Unknown"
            home_team = "Unknown"
        
        # --- MODIFICATION: Get game date string for file naming and data ---
        # --- This block is now redundant, we moved it up ---
        
        # --- MODIFICATION: Fetch all available tabs for THIS specific game ---
        print(f"Discovering available player prop tabs for {game_name}...")
        available_tabs = get_all_available_tabs(event_id)
        
        if not available_tabs:
            print("  No player prop tabs found for this game. Skipping.")
            # time.sleep(1) # So we don't skip too fast <-- REMOVED
            continue
            
        print(f"  Found {len(available_tabs)} player prop tabs. Fetching props for each...")
        # Example tabs: 'Player Points', 'Player Combos', 'Player Defensive'
        
        # Loop through the *actual* available tabs returned by the API
        for tab in available_tabs:
            tab_name = tab['name']    # This is the string name, e.g., 'player-combos'
            tab_title = tab['title']  # This is the display name, e.g., 'Player Combos'
            
            print(f"\n--- Fetching '{tab_title}' (tab={tab_name}) ---")
            
            # Get data for this specific tab
            prop_data = get_player_props(event_id, tab_name)
            
            if not prop_data or 'attachments' not in prop_data or 'markets' not in prop_data['attachments']:
                print(f"  No data available")
                continue
            
            markets = prop_data['attachments']['markets']
            
            if not markets:
                print(f"  No markets found")
                continue

            # --- DEBUG BLOCK REMOVED ---
            # The filter below handles grabbing only O/U props.
            
            prop_count = 0
            
            for market in markets.values():
                market_type = market.get('marketType', '')
                market_name = market.get('marketName', '')
                
                # This filter is designed to get Over/Under props
                # e.g., PLAYER_POINTS_TOTAL_O_U, PLAYER_STEALS_TOTAL_O_U, PLAYER_POINTS_REBOUNDS_ASSISTS_TOTAL_O_U
                if (not market_type.startswith('PLAYER_') or 'TOTAL' not in market_type):
                    # Fallback check for market types that might just be "PLAYER_PROPS"
                    if not (market_type == "PLAYER_PROPS" and "O/U" in market_name):
                        continue
                
                # NBA props typically have format: "Player Name - Prop Type"
                if " - " not in market_name:
                    continue
                
                # Skip alternate/quarter-specific props
                if "Alt " in market_name or "1st Qtr" in market_name or "1st Half" in market_name or "Quarter" in market_name or "Half" in market_name:
                    continue
                
                try:
                    player_name, prop_type = market_name.rsplit(' - ', 1)
                    
                    # Further filter out non O/U props that might have slipped through
                    if "Yes/No" in prop_type:
                        continue

                except ValueError:
                    # print(f"  Could not parse market name: {market_name}") # Optional: uncomment for more verbose debugging
                    continue

                runners = market.get('runners', [])
                
                if len(runners) != 2:
                    continue # Skip if not a standard Over/Under market
                
                # Find over/under runners
                over_runner = next((r for r in runners if r.get('result', {}).get('type') == 'OVER'), None)
                under_runner = next((r for r in runners if r.get('result', {}).get('type') == 'UNDER'), None)
                
                if not over_runner or not under_runner:
                    continue
                
                # Get team from logo URL
                logo_url = over_runner.get('secondaryLogo', '')
                team_name = extract_team_name_from_logo(logo_url)
                
                line = over_runner.get('handicap')
                over_odds = over_runner.get('winRunnerOdds', {}).get('americanDisplayOdds', {}).get('americanOdds')
                under_odds = under_runner.get('winRunnerOdds', {}).get('americanDisplayOdds', {}).get('americanOdds')
                
                # Ensure all data is present before adding
                if line is None or over_odds is None or under_odds is None:
                    continue

                # --- MODIFICATION: Use normalization functions ---
                normalized_player = normalize_player_name(player_name)
                normalized_prop = normalize_prop_type(prop_type)

                # --- MODIFICATION: Simplified prop_info structure ---
                prop_info = {
                    'player': normalized_player,
                    'team': team_name,
                    'prop_type': normalized_prop,
                    'line': line,
                    'over_odds': over_odds,
                    'under_odds': under_odds,
                    # --- You can add these back if you want more context ---
                    # 'game': game_name,
                    # 'game_date': game_date_str,
                    # 'sportsbook': 'FanDuel',
                    # 'scrape_timestamp': scrape_time,
                }
                
                # --- MODIFICATION: Append to date-specific list ---
                if game_date_str not in props_by_date:
                    props_by_date[game_date_str] = []
                props_by_date[game_date_str].append(prop_info)
                
                # Print the prop (using normalized names for clarity)
                print(f"  {normalized_player} ({team_name}) - {normalized_prop} (Raw: {prop_type})")
                print(f"    Line: {line} | Over: {over_odds} | Under: {under_odds}")
                
                prop_count += 1
            
            print(f"  Found {prop_count} props for '{tab_title}'")
            # time.sleep(0.5)  # Rate limiting between tabs <-- REMOVED
        
        # time.sleep(1)  # Extra delay between games <-- REMOVED
    
    # Print summary
    print(f"\n{'='*80}")
    print(f"SCRAPING COMPLETE")
    print(f"{'='*80}")
    print(f"Total events found: {len(upcoming_events)}")
    print(f"Actual games processed: {games_processed}")
    
    # --- MODIFICATION: Update total prop count ---
    total_props_collected = sum(len(props) for props in props_by_date.values())
    print(f"Total props collected: {total_props_collected}")
    print(f"Scrape timestamp: {scrape_time}")
    
    # Optional: Print breakdown by prop type
    print("\nProps by type:")
    prop_types = {}
    # --- MODIFICATION: Iterate through new data structure ---
    for game_date, props_list in props_by_date.items():
        for prop in props_list:
            prop_type = prop['prop_type'] # Use simplified prop type
            prop_types[prop_type] = prop_types.get(prop_type, 0) + 1
    
    for prop_type, count in sorted(prop_types.items()):
        print(f"  {prop_type}: {count}")
    
    # --- MODIFICATION: Save all data to a JSON file PER DAY into a folder ---
    
    # Define the output folder
    output_folder = "fanduel_nba_props"
    
    # Create the folder if it doesn't exist
    if not os.path.exists(output_folder):
        try:
            os.makedirs(output_folder)
            print(f"\nCreated output folder: {output_folder}")
        except Exception as e:
            print(f"\nError creating output folder: {e}. Saving to current directory.")
            output_folder = "." # Fallback to current directory
    
    print(f"\nSaving props for {len(props_by_date)} game date(s) to '{output_folder}'...")
    total_saved = 0
    for game_date, props_list in props_by_date.items():
        # Create the filename and join it with the output folder path
        filename = f'fanduel_nba_props_{game_date}.json'
        file_path = os.path.join(output_folder, filename)
        
        try:
            with open(file_path, 'w') as f:
                json.dump(props_list, f, indent=2)
            print(f"  Successfully saved {len(props_list)} props to {file_path}")
            total_saved += len(props_list)
        except Exception as e:
            print(f"  Error saving data for {game_date} to JSON: {e}")
    
    print(f"\nTotal props saved across all files: {total_saved}")

    return props_by_date # Return the grouped data

if __name__ == "__main__":
    run_scraper()







