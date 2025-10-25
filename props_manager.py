import os
import json
import sqlite3
from datetime import datetime
from collections import defaultdict

def get_output_path(base_folder, sportsbook, game_date_str):
    """
    Creates a hierarchical path: base_folder/sportsbook/YYYY/MM/filename.json
    Example: props_data/draftkings/2025/10/draftkings_nba_props_2025-10-24.json
    """
    # Parse the date
    date_obj = datetime.strptime(game_date_str, '%Y-%m-%d')
    year = date_obj.strftime('%Y')
    month = date_obj.strftime('%m')
    
    # Create the directory structure
    folder_path = os.path.join(base_folder, sportsbook, year, month)
    os.makedirs(folder_path, exist_ok=True)
    
    # Create the filename
    filename = f"{sportsbook}_nba_props_{game_date_str}.json"
    
    return os.path.join(folder_path, filename)

def american_to_decimal(american_odds):
    """Convert American odds to decimal odds - handles strings, unicode, None, etc."""
    if american_odds is None:
        return None
    
    # Convert to string first to handle any type
    odds_str = str(american_odds).strip()
    
    # Replace unicode minus signs with standard hyphen
    odds_str = odds_str.replace('−', '-')  # Unicode minus
    odds_str = odds_str.replace('–', '-')  # En dash
    odds_str = odds_str.replace('—', '-')  # Em dash
    odds_str = odds_str.replace('\u2212', '-')  # Another unicode minus
    
    # Remove any extra whitespace
    odds_str = odds_str.strip()
    
    # Try to convert to int
    try:
        american_odds = int(odds_str)
    except (ValueError, TypeError):
        print(f"Warning: Could not convert odds '{american_odds}' to integer")
        return None
    
    # Now do the conversion
    if american_odds > 0:
        return (american_odds / 100) + 1
    else:
        return (100 / abs(american_odds)) + 1

def decimal_to_implied_probability(decimal_odds):
    """Convert decimal odds to implied probability (as percentage)"""
    return (1 / decimal_odds) * 100

def calculate_arbitrage_profit(odds1, odds2):
    """
    Calculate if there's an arbitrage opportunity and return profit percentage.
    Returns None if no arbitrage exists or if odds are invalid.
    
    odds1, odds2: American odds for opposite sides of a bet
    """
    # Convert to decimal
    decimal1 = american_to_decimal(odds1)
    decimal2 = american_to_decimal(odds2)
    
    # Check if conversion was successful
    if decimal1 is None or decimal2 is None:
        return None
    
    # Calculate implied probabilities
    prob1 = 1 / decimal1
    prob2 = 1 / decimal2
    
    # Total probability (should be < 1 for arbitrage)
    total_prob = prob1 + prob2
    
    if total_prob < 1:
        # Profit percentage (assuming $100 total stake)
        profit_percent = ((1 / total_prob) - 1) * 100
        return round(profit_percent, 2)
    
    return None

def calculate_ev(odds, true_probability):
    """
    Calculate expected value of a bet.
    
    odds: American odds
    true_probability: Your estimated probability of the outcome (0-100)
    """
    decimal_odds = american_to_decimal(odds)
    
    if decimal_odds is None:
        return None
    
    prob = true_probability / 100
    
    # EV = (Probability of winning * Amount won) - (Probability of losing * Amount lost)
    ev = (prob * (decimal_odds - 1)) - ((1 - prob) * 1)
    return round(ev * 100, 2)  # Return as percentage

class PropsDatabase:
    def __init__(self, db_path="props_data/props.db"):
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.create_tables()
    
    def create_tables(self):
        """Create the props table if it doesn't exist"""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_props (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player TEXT NOT NULL,
                team TEXT,
                prop_type TEXT NOT NULL,
                line REAL NOT NULL,
                over_odds INTEGER,
                under_odds INTEGER,
                sportsbook TEXT NOT NULL,
                game_date TEXT NOT NULL,
                game TEXT,
                scrape_timestamp TEXT NOT NULL,
                UNIQUE(player, prop_type, line, sportsbook, game_date)
            )
        ''')
        
        # Create indexes for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_player_date 
            ON player_props(player, game_date)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_date_sportsbook 
            ON player_props(game_date, sportsbook)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_prop_type 
            ON player_props(prop_type)
        ''')
        
        self.conn.commit()
    
    def insert_props(self, props_list, sportsbook):
        """
        Delete all props for the given sportsbook and game_dates, 
        then insert the new props list.
        """
        if not props_list:
            print(f"  No props provided for {sportsbook}. Nothing to insert.")
            return 0, 0
            
        cursor = self.conn.cursor()
        scrape_time = datetime.now().isoformat()
        
        # --- NEW: Clear stale data first ---
        # Get all unique game dates from the props list
        game_dates_in_batch = set(p.get('game_date') for p in props_list if p.get('game_date'))
        
        deleted = 0
        if game_dates_in_batch:
            print(f"  Clearing stale props for {sportsbook} on dates: {', '.join(game_dates_in_batch)}...")
            try:
                # Use a tuple for the IN clause
                placeholders = ','.join('?' for _ in game_dates_in_batch)
                query = f"DELETE FROM player_props WHERE sportsbook = ? AND game_date IN ({placeholders})"
                
                # Prepare arguments
                args = [sportsbook] + list(game_dates_in_batch)
                
                cursor.execute(query, args)
                deleted = cursor.rowcount
            except sqlite3.Error as e:
                print(f"  Error deleting props: {e}")
                
            if deleted > 0:
                print(f"  ...removed {deleted} stale props.")
        # --- END NEW ---

        inserted = 0
        for prop in props_list:
            try:
                # Clean odds values before inserting
                over_odds = prop.get('over_odds')
                under_odds = prop.get('under_odds')
                
                # Convert odds to integers if they're strings
                if over_odds is not None:
                    over_odds_str = str(over_odds).replace('−', '-').replace('–', '-').replace('—', '-').strip()
                    try:
                        over_odds = int(over_odds_str)
                    except (ValueError, TypeError):
                        print(f"Warning: Invalid over_odds '{over_odds}' for {prop.get('player')} - skipping")
                        continue
                
                if under_odds is not None:
                    under_odds_str = str(under_odds).replace('−', '-').replace('–', '-').replace('—', '-').strip()
                    try:
                        under_odds = int(under_odds_str)
                    except (ValueError, TypeError):
                        print(f"Warning: Invalid under_odds '{under_odds}' for {prop.get('player')} - skipping")
                        continue

                # --- MODIFIED: Use a simple INSERT ---
                # We no longer need ON CONFLICT because we deleted all old data
                cursor.execute('''
                    INSERT INTO player_props 
                    (player, team, prop_type, line, over_odds, under_odds, 
                    sportsbook, game_date, game, scrape_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    prop.get('player'),
                    prop.get('team'),
                    prop.get('prop_type'),
                    prop.get('line'),
                    over_odds,
                    under_odds,
                    sportsbook,
                    prop.get('game_date'),
                    prop.get('game'),
                    scrape_time
                ))
                
                inserted += 1
                    
            except sqlite3.Error as e:
                # Handle UNIQUE constraint error just in case, e.g., duplicate in scrape
                if "UNIQUE constraint" in str(e):
                    print(f"  Warning: Duplicate prop found in scrape batch for {prop.get('player')}. Skipping.")
                else:
                    print(f"  Error inserting prop: {e}")
                continue
        
        self.conn.commit()
        # --- MODIFIED: Updated print message ---
        print(f"  📊 Database: Inserted {inserted} new props for {sportsbook}.")
        return inserted, 0  # Return (inserted, updated) - updated is now 0
    
    def get_props_for_date(self, game_date, sportsbook=None):
        """Retrieve all props for a specific date"""
        cursor = self.conn.cursor()
        
        if sportsbook:
            cursor.execute('''
                SELECT * FROM player_props 
                WHERE game_date = ? AND sportsbook = ?
                ORDER BY player, prop_type
            ''', (game_date, sportsbook))
        else:
            cursor.execute('''
                SELECT * FROM player_props 
                WHERE game_date = ?
                ORDER BY player, prop_type, sportsbook
            ''', (game_date,))
        
        columns = [description[0] for description in cursor.description]
        results = cursor.fetchall()
        
        return [dict(zip(columns, row)) for row in results]
    
    def get_player_history(self, player_name, prop_type, days=30):
        """Get historical props for a specific player"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM player_props 
            WHERE player = ? AND prop_type = ?
            AND game_date >= date('now', '-' || ? || ' days')
            ORDER BY game_date DESC, sportsbook
        ''', (player_name, prop_type, days))
        
        columns = [description[0] for description in cursor.description]
        results = cursor.fetchall()
        
        return [dict(zip(columns, row)) for row in results]
    
    def compare_books_for_date(self, game_date):
        """Compare lines across sportsbooks for a given date"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                player,
                prop_type,
                line,
                MAX(CASE WHEN LOWER(sportsbook) = 'draftkings' THEN over_odds END) as dk_over,
                MAX(CASE WHEN LOWER(sportsbook) = 'draftkings' THEN under_odds END) as dk_under,
                MAX(CASE WHEN LOWER(sportsbook) = 'fanduel' THEN over_odds END) as fd_over,
                MAX(CASE WHEN LOWER(sportsbook) = 'fanduel' THEN under_odds END) as fd_under
            FROM player_props
            WHERE game_date = ?
            GROUP BY player, prop_type, line
            HAVING COUNT(DISTINCT sportsbook) > 1
            ORDER BY player, prop_type
        ''', (game_date,))
        
        columns = [description[0] for description in cursor.description]
        results = cursor.fetchall()
        
        return [dict(zip(columns, row)) for row in results]
    
    # Add these methods to the PropsDatabase class

    def get_all_props_for_comparison(self, game_date):
        """Get all props for a date, grouped by player and prop_type for comparison"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                player,
                prop_type,
                line,
                over_odds,
                under_odds,
                sportsbook,
                game,
                team
            FROM player_props
            WHERE game_date = ?
            ORDER BY player, prop_type, sportsbook, line
        ''', (game_date,))
        
        columns = [description[0] for description in cursor.description]
        results = cursor.fetchall()
        
        return [dict(zip(columns, row)) for row in results]

    def find_arbitrage_opportunities(self, game_date, min_profit_percent=0.5):
        """
        Find arbitrage opportunities where betting both sides guarantees profit.
        Returns opportunities with expected profit percentage.
        """
        cursor = self.conn.cursor()
        
        # Get all props with their odds from both books
        cursor.execute('''
            WITH prop_comparison AS (
                SELECT 
                    player,
                    prop_type,
                    line,
                    MAX(CASE WHEN LOWER(sportsbook) = 'draftkings' THEN over_odds END) as dk_over,
                    MAX(CASE WHEN LOWER(sportsbook) = 'draftkings' THEN under_odds END) as dk_under,
                    MAX(CASE WHEN LOWER(sportsbook) = 'fanduel' THEN over_odds END) as fd_over,
                    MAX(CASE WHEN LOWER(sportsbook) = 'fanduel' THEN under_odds END) as fd_under,
                    MAX(game) as game,
                    MAX(team) as team
                FROM player_props
                WHERE game_date = ?
                GROUP BY player, prop_type, line
                HAVING COUNT(DISTINCT sportsbook) > 1
            )
            SELECT *
            FROM prop_comparison
            WHERE (dk_over IS NOT NULL AND fd_under IS NOT NULL)
            OR (fd_over IS NOT NULL AND dk_under IS NOT NULL)
        ''', (game_date,))
        
        columns = [description[0] for description in cursor.description]
        results = cursor.fetchall()
        props = [dict(zip(columns, row)) for row in results]
        
        arbitrage_opportunities = []
        
        for prop in props:
            # Check DK Over vs FD Under
            if prop['dk_over'] and prop['fd_under']:
                profit = calculate_arbitrage_profit(prop['dk_over'], prop['fd_under'])
                if profit and profit >= min_profit_percent:
                    arbitrage_opportunities.append({
                        'player': prop['player'],
                        'prop_type': prop['prop_type'],
                        'line': prop['line'],
                        'game': prop['game'],
                        'team': prop['team'],
                        'bet_over': 'DraftKings',
                        'over_odds': prop['dk_over'],
                        'bet_under': 'FanDuel',
                        'under_odds': prop['fd_under'],
                        'profit_percent': profit,
                        'type': 'arbitrage'
                    })
            
            # Check FD Over vs DK Under
            if prop['fd_over'] and prop['dk_under']:
                profit = calculate_arbitrage_profit(prop['fd_over'], prop['dk_under'])
                if profit and profit >= min_profit_percent:
                    arbitrage_opportunities.append({
                        'player': prop['player'],
                        'prop_type': prop['prop_type'],
                        'line': prop['line'],
                        'game': prop['game'],
                        'team': prop['team'],
                        'bet_over': 'FanDuel',
                        'over_odds': prop['fd_over'],
                        'bet_under': 'DraftKings',
                        'under_odds': prop['dk_under'],
                        'profit_percent': profit,
                        'type': 'arbitrage'
                    })
        
        return sorted(arbitrage_opportunities, key=lambda x: x['profit_percent'], reverse=True)

    def find_line_discrepancies(self, game_date, min_line_diff=1.0):
        """
        Find props where the same player/prop has different lines across sportsbooks.
        This could indicate value betting opportunities.
        """
        cursor = self.conn.cursor()
        
        # Get all unique player/prop combinations that exist on both books
        cursor.execute('''
            WITH dk_props AS (
                SELECT player, prop_type, line, over_odds, under_odds, game, team
                FROM player_props
                WHERE game_date = ? AND LOWER(sportsbook) = 'draftkings'
            ),
            fd_props AS (
                SELECT player, prop_type, line, over_odds, under_odds, game, team
                FROM player_props
                WHERE game_date = ? AND LOWER(sportsbook) = 'fanduel'
            )
            SELECT 
                dk.player,
                dk.prop_type,
                dk.line as dk_line,
                dk.over_odds as dk_over,
                dk.under_odds as dk_under,
                fd.line as fd_line,
                fd.over_odds as fd_over,
                fd.under_odds as fd_under,
                dk.game,
                dk.team,
                ABS(dk.line - fd.line) as line_difference
            FROM dk_props dk
            JOIN fd_props fd ON dk.player = fd.player AND dk.prop_type = fd.prop_type
            WHERE ABS(dk.line - fd.line) >= ?
            ORDER BY line_difference DESC
        ''', (game_date, game_date, min_line_diff))
        
        columns = [description[0] for description in cursor.description]
        results = cursor.fetchall()
        
        return [dict(zip(columns, row)) for row in results]

    def find_best_odds(self, game_date, min_odds_diff=10):
        """
        Find props where one book offers significantly better odds for the same line.
        min_odds_diff: minimum difference in American odds to be considered significant
        """
        cursor = self.conn.cursor()
        
        cursor.execute('''
            WITH prop_comparison AS (
                SELECT 
                    player,
                    prop_type,
                    line,
                    MAX(CASE WHEN LOWER(sportsbook) = 'draftkings' THEN over_odds END) as dk_over,
                    MAX(CASE WHEN LOWER(sportsbook) = 'draftkings' THEN under_odds END) as dk_under,
                    MAX(CASE WHEN LOWER(sportsbook) = 'fanduel' THEN over_odds END) as fd_over,
                    MAX(CASE WHEN LOWER(sportsbook) = 'fanduel' THEN under_odds END) as fd_under,
                    MAX(game) as game,
                    MAX(team) as team
                FROM player_props
                WHERE game_date = ?
                GROUP BY player, prop_type, line
                HAVING COUNT(DISTINCT sportsbook) > 1
            )
            SELECT *
            FROM prop_comparison
            WHERE (ABS(dk_over - fd_over) >= ? AND dk_over IS NOT NULL AND fd_over IS NOT NULL)
            OR (ABS(dk_under - fd_under) >= ? AND dk_under IS NOT NULL AND fd_under IS NOT NULL)
        ''', (game_date, min_odds_diff, min_odds_diff))
        
        columns = [description[0] for description in cursor.description]
        results = cursor.fetchall()
        props = [dict(zip(columns, row)) for row in results]
        
        best_odds = []
        
        for prop in props:
            # Compare over odds
            if prop['dk_over'] and prop['fd_over']:
                over_diff = abs(prop['dk_over'] - prop['fd_over'])
                if over_diff >= min_odds_diff:
                    best_book = 'DraftKings' if prop['dk_over'] > prop['fd_over'] else 'FanDuel'
                    best_odds_value = max(prop['dk_over'], prop['fd_over'])
                    worst_odds_value = min(prop['dk_over'], prop['fd_over'])
                    
                    best_odds.append({
                        'player': prop['player'],
                        'prop_type': prop['prop_type'],
                        'line': prop['line'],
                        'game': prop['game'],
                        'team': prop['team'],
                        'side': 'Over',
                        'best_book': best_book,
                        'best_odds': best_odds_value,
                        'other_odds': worst_odds_value,
                        'odds_difference': over_diff,
                        'dk_odds': prop['dk_over'],
                        'fd_odds': prop['fd_over']
                    })
            
            # Compare under odds
            if prop['dk_under'] and prop['fd_under']:
                under_diff = abs(prop['dk_under'] - prop['fd_under'])
                if under_diff >= min_odds_diff:
                    best_book = 'DraftKings' if prop['dk_under'] > prop['fd_under'] else 'FanDuel'
                    best_odds_value = max(prop['dk_under'], prop['fd_under'])
                    worst_odds_value = min(prop['dk_under'], prop['fd_under'])
                    
                    best_odds.append({
                        'player': prop['player'],
                        'prop_type': prop['prop_type'],
                        'line': prop['line'],
                        'game': prop['game'],
                        'team': prop['team'],
                        'side': 'Under',
                        'best_book': best_book,
                        'best_odds': best_odds_value,
                        'other_odds': worst_odds_value,
                        'odds_difference': under_diff,
                        'dk_odds': prop['dk_under'],
                        'fd_odds': prop['fd_under']
                    })
        
        return sorted(best_odds, key=lambda x: x['odds_difference'], reverse=True)
    
    def close(self):
        self.conn.close()


class PropsManager:
    def __init__(self, base_folder="props_data", use_db=True):
        self.base_folder = base_folder
        self.use_db = use_db
        if use_db:
            db_path = os.path.join(base_folder, "props.db")
            self.db = PropsDatabase(db_path)
    
    def save_props(self, props, sportsbook):
        """Save to both JSON (backup) and SQLite (querying)"""
        if not props:
            print("No props to save")
            return
        
        grouped = defaultdict(list)
        for prop in props:
            grouped[prop['game_date']].append(prop)
        
        for date, props_list in grouped.items():
            # Save to JSON (organized by year/month)
            json_path = get_output_path(self.base_folder, sportsbook, date)
            self._save_json(json_path, props_list)
            
            # Save to database
            if self.use_db:
                self.db.insert_props(props_list, sportsbook)
    
    def _save_json(self, file_path, props_list):
        """Helper to save JSON with deduplication"""
        existing_props = []
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    existing_props = json.load(f)
            except json.JSONDecodeError:
                print(f"  ⚠️  Warning: Could not read existing {file_path}, overwriting...")
                existing_props = []
        
        all_props = existing_props + props_list
        
        # Remove duplicates (keep latest)
        unique_props = {}
        for prop in all_props:
            key = (prop['player'], prop['prop_type'], prop['line'])
            unique_props[key] = prop
        
        final_props = list(unique_props.values())
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(final_props, f, indent=2, ensure_ascii=False)
            print(f"  ✅ Saved {len(final_props)} props to {file_path}")
        except Exception as e:
            print(f"  ❌ Error saving JSON: {e}")
    
    def get_props_for_date(self, game_date, sportsbook=None):
        """Query props from database"""
        if self.use_db:
            return self.db.get_props_for_date(game_date, sportsbook)
        return []
    
    def get_player_history(self, player_name, prop_type, days=30):
        """Get player history from database"""
        if self.use_db:
            return self.db.get_player_history(player_name, prop_type, days)
        return []
    
    def compare_books(self, game_date):
        """Compare odds across sportsbooks"""
        if self.use_db:
            return self.db.compare_books_for_date(game_date)
        return []
    
    def find_arbitrage(self, game_date, min_profit=0.5):
        """Find arbitrage opportunities"""
        if self.use_db:
            return self.db.find_arbitrage_opportunities(game_date, min_profit)
        return []

    def find_line_discrepancies(self, game_date, min_diff=1.0):
        """Find line discrepancies between books"""
        if self.use_db:
            return self.db.find_line_discrepancies(game_date, min_diff)
        return []

    def find_best_odds(self, game_date, min_odds_diff=10):
        """Find best odds opportunities"""
        if self.use_db:
            return self.db.find_best_odds(game_date, min_odds_diff)
        return []

    def get_all_props_comparison(self, game_date):
        """Get all props for comparison"""
        if self.use_db:
            return self.db.get_all_props_for_comparison(game_date)
        return []
    
    def close(self):
        if self.use_db:
            self.db.close()