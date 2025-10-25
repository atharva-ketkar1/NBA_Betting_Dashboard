#!/usr/bin/env python3
"""
Master scraper that runs all scrapers and updates both JSON files and database.
Run this daily to get fresh props data.
"""

import sys
import time
from datetime import datetime
from scrape_draftkings import run_nba_scraper as run_dk_scraper
from scrape_fanduel import run_scraper as run_fd_scraper

def print_banner(text):
    """Print a nice banner"""
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80 + "\n")

def main():
    start_time = time.time()
    
    print_banner("🏀 NBA PROPS MASTER SCRAPER")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"This will scrape both DraftKings and FanDuel and update the database.\n")
    
    # Track success/failure
    results = {
        'draftkings': {'success': False, 'error': None},
        'fanduel': {'success': False, 'error': None}
    }
    
    # Run DraftKings scraper
    print_banner("STEP 1: Scraping DraftKings")
    try:
        run_dk_scraper()
        results['draftkings']['success'] = True
        print("✅ DraftKings scraping completed successfully!")
    except Exception as e:
        results['draftkings']['error'] = str(e)
        print(f"❌ DraftKings scraping failed: {e}")
    
    # Small delay between scrapers
    time.sleep(3)
    
    # Run FanDuel scraper
    print_banner("STEP 2: Scraping FanDuel")
    try:
        run_fd_scraper()
        results['fanduel']['success'] = True
        print("✅ FanDuel scraping completed successfully!")
    except Exception as e:
        results['fanduel']['error'] = str(e)
        print(f"❌ FanDuel scraping failed: {e}")
    
    # Summary
    elapsed_time = time.time() - start_time
    print_banner("SCRAPING SUMMARY")
    
    print(f"DraftKings: {'✅ SUCCESS' if results['draftkings']['success'] else '❌ FAILED'}")
    if results['draftkings']['error']:
        print(f"  Error: {results['draftkings']['error']}")
    
    print(f"\nFanDuel: {'✅ SUCCESS' if results['fanduel']['success'] else '❌ FAILED'}")
    if results['fanduel']['error']:
        print(f"  Error: {results['fanduel']['error']}")
    
    print(f"\nTotal time: {elapsed_time:.2f} seconds")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check database
    print_banner("DATABASE STATUS")
    try:
        from props_manager import PropsManager
        manager = PropsManager(base_folder="props_data", use_db=True)
        
        # Get today's date
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Check props for today
        props_today = manager.get_props_for_date(today)
        dk_props = manager.get_props_for_date(today, sportsbook='draftkings')
        fd_props = manager.get_props_for_date(today, sportsbook='fanduel')
        
        print(f"Props for {today}:")
        print(f"  Total: {len(props_today)}")
        print(f"  DraftKings: {len(dk_props)}")
        print(f"  FanDuel: {len(fd_props)}")
        
        # Get arbitrage opportunities
        arbs = manager.find_arbitrage(today, min_profit=0.1)
        discs = manager.find_line_discrepancies(today, min_diff=0.5)
        best = manager.find_best_odds(today, min_odds_diff=5)
        
        print(f"\nOpportunities for {today}:")
        print(f"  Arbitrage: {len(arbs)}")
        print(f"  Line Discrepancies: {len(discs)}")
        print(f"  Best Odds: {len(best)}")
        
        manager.close()
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")
    
    print("\n" + "="*80)
    print("✅ All done! Your dashboard is ready to use.")
    print("="*80 + "\n")
    
    # Exit with appropriate code
    if results['draftkings']['success'] or results['fanduel']['success']:
        sys.exit(0)  # Success if at least one worked
    else:
        sys.exit(1)  # Failure if both failed

if __name__ == "__main__":
    main()