import sqlite3
import os

def clean_odds_value(odds_value):
    """Clean and convert odds value to integer"""
    if odds_value is None:
        return None
    
    odds_str = str(odds_value).strip()
    odds_str = odds_str.replace('−', '-').replace('–', '-').replace('—', '-').replace('\u2212', '-')
    
    try:
        return int(odds_str)
    except (ValueError, TypeError):
        return None

def fix_database_odds():
    db_path = "props_data/props.db"
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all props
    cursor.execute("SELECT id, over_odds, under_odds FROM player_props")
    props = cursor.fetchall()
    
    print(f"Found {len(props)} props to check...")
    
    fixed = 0
    for prop_id, over_odds, under_odds in props:
        cleaned_over = clean_odds_value(over_odds)
        cleaned_under = clean_odds_value(under_odds)
        
        # Only update if values changed
        if cleaned_over != over_odds or cleaned_under != under_odds:
            cursor.execute(
                "UPDATE player_props SET over_odds = ?, under_odds = ? WHERE id = ?",
                (cleaned_over, cleaned_under, prop_id)
            )
            fixed += 1
    
    conn.commit()
    conn.close()
    
    print(f"Fixed {fixed} props with incorrect odds formatting")
    print("Database cleaned successfully!")

if __name__ == "__main__":
    fix_database_odds()