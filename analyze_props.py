from props_manager import PropsManager
from datetime import datetime
import json

def display_arbitrage_opportunities(arbs):
    """Display arbitrage opportunities in a readable format"""
    if not arbs:
        print("No arbitrage opportunities found.")
        return
    
    print(f"\n{'='*100}")
    print(f"ARBITRAGE OPPORTUNITIES (Guaranteed Profit)")
    print(f"{'='*100}\n")
    
    for i, arb in enumerate(arbs, 1):
        print(f"{i}. {arb['player'].title()} - {arb['prop_type'].upper()} {arb['line']}")
        print(f"   Game: {arb['game']}")
        print(f"   📈 PROFIT: {arb['profit_percent']:.2f}%")
        print(f"   ")
        print(f"   Bet OVER {arb['line']} on {arb['bet_over']}: {arb['over_odds']:+d}")
        print(f"   Bet UNDER {arb['line']} on {arb['bet_under']}: {arb['under_odds']:+d}")
        print(f"   ")
        print(f"   Example: Stake $100 total")
        
        # Calculate stake distribution for arbitrage
        from props_manager import american_to_decimal
        dec_over = american_to_decimal(arb['over_odds'])
        dec_under = american_to_decimal(arb['under_odds'])
        
        total_stake = 100
        stake_over = total_stake / (1 + (dec_over / dec_under))
        stake_under = total_stake - stake_over
        
        profit = (stake_over * dec_over) - total_stake
        
        print(f"   → Stake ${stake_over:.2f} on OVER")
        print(f"   → Stake ${stake_under:.2f} on UNDER")
        print(f"   → Guaranteed profit: ${profit:.2f}")
        print()

def display_line_discrepancies(discrepancies):
    """Display line discrepancies"""
    if not discrepancies:
        print("No significant line discrepancies found.")
        return
    
    print(f"\n{'='*100}")
    print(f"LINE DISCREPANCIES (Different Lines Across Books)")
    print(f"{'='*100}\n")
    
    for i, disc in enumerate(discrepancies, 1):
        print(f"{i}. {disc['player'].title()} - {disc['prop_type'].upper()}")
        print(f"   Game: {disc['game']}")
        print(f"   📊 Line Difference: {disc['line_difference']:.1f}")
        print(f"   ")
        print(f"   DraftKings: {disc['dk_line']} (O: {disc['dk_over']:+d}, U: {disc['dk_under']:+d})")
        print(f"   FanDuel:    {disc['fd_line']} (O: {disc['fd_over']:+d}, U: {disc['fd_under']:+d})")
        print(f"   ")
        
        # Suggest strategy
        if disc['dk_line'] < disc['fd_line']:
            print(f"   💡 Strategy: Consider DK OVER {disc['dk_line']} or FD UNDER {disc['fd_line']}")
        else:
            print(f"   💡 Strategy: Consider FD OVER {disc['fd_line']} or DK UNDER {disc['dk_line']}")
        print()

def display_best_odds(best_odds):
    """Display best odds opportunities"""
    if not best_odds:
        print("No significant odds differences found.")
        return
    
    print(f"\n{'='*100}")
    print(f"BEST ODDS (Same Line, Better Odds)")
    print(f"{'='*100}\n")
    
    for i, odds in enumerate(best_odds[:20], 1):  # Show top 20
        print(f"{i}. {odds['player'].title()} - {odds['prop_type'].upper()} {odds['side']} {odds['line']}")
        print(f"   Game: {odds['game']}")
        print(f"   💰 Odds Difference: {odds['odds_difference']} points")
        print(f"   ")
        print(f"   ✅ Best: {odds['best_book']} at {odds['best_odds']:+d}")
        print(f"   ❌ Other: {odds['other_odds']:+d}")
        print()

def main():
    manager = PropsManager(base_folder="props_data", use_db=True)
    
    # Get today's date
    today = datetime.now().strftime('%Y-%m-%d')
    print(f"\n{'='*100}")
    print(f"ANALYZING PROPS FOR {today}")
    print(f"{'='*100}")
    
    # 1. Find arbitrage opportunities
    print("\n[1/3] Searching for arbitrage opportunities...")
    arbs = manager.find_arbitrage(today, min_profit=0.1)  # Even 0.1% profit
    display_arbitrage_opportunities(arbs)
    
    # 2. Find line discrepancies
    print("\n[2/3] Searching for line discrepancies...")
    discrepancies = manager.find_line_discrepancies(today, min_diff=0.5)
    display_line_discrepancies(discrepancies[:10])  # Show top 10
    
    # 3. Find best odds
    print("\n[3/3] Searching for best odds...")
    best_odds = manager.find_best_odds(today, min_odds_diff=5)
    display_best_odds(best_odds)
    
    # Summary
    print(f"\n{'='*100}")
    print("SUMMARY")
    print(f"{'='*100}")
    print(f"Arbitrage Opportunities: {len(arbs)}")
    print(f"Line Discrepancies: {len(discrepancies)}")
    print(f"Best Odds Opportunities: {len(best_odds)}")
    print()
    
    manager.close()

if __name__ == "__main__":
    main()