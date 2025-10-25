from props_manager import PropsManager
from datetime import datetime, timedelta
import json

def main():
    manager = PropsManager(base_folder="props_data", use_db=True)
    
    # Example 1: Get all props for today
    today = datetime.now().strftime('%Y-%m-%d')
    print(f"\n=== Props for {today} ===")
    props_today = manager.get_props_for_date(today)
    print(f"Found {len(props_today)} props")
    
    # Example 2: Get DraftKings props only
    print(f"\n=== DraftKings Props for {today} ===")
    dk_props = manager.get_props_for_date(today, sportsbook="draftkings")
    print(f"Found {len(dk_props)} DraftKings props")
    
    # Example 3: Compare odds across books
    print(f"\n=== Comparing Odds Across Books for {today} ===")
    comparisons = manager.compare_books(today)
    
    # Show first 5 comparisons
    for i, comp in enumerate(comparisons[:5]):
        print(f"\n{comp['player'].title()} - {comp['prop_type'].upper()}")
        print(f"  Line: {comp['line']}")
        print(f"  DraftKings: Over {comp['dk_over']} / Under {comp['dk_under']}")
        print(f"  FanDuel: Over {comp['fd_over']} / Under {comp['fd_under']}")
    
    # Example 4: Get player history
    print(f"\n=== LeBron James Points History (Last 30 Days) ===")
    history = manager.get_player_history("lebron james", "points", days=30)
    for prop in history[:5]:  # Show first 5
        print(f"  {prop['game_date']} - {prop['sportsbook']}: Line {prop['line']} (O: {prop['over_odds']}, U: {prop['under_odds']})")
    
    manager.close()

if __name__ == "__main__":
    main()