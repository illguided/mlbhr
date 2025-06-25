# This is the final version of the script you run on your own computer.

import json
from datetime import datetime
import sys

# Tell Python where to find your 'full' wrapper folder
sys.path.append('.')

try:
    # Import the 'full' folder and give it the alias 'statsapi'
    import full as statsapi
    print("✅ Successfully imported your 'statsapi' wrapper.")
except ImportError as e:
    print(f"--- FAILED TO IMPORT WRAPPER ---\nError: {e}")
    sys.exit()

# A cache to store pitcher IDs so we don't look them up multiple times
pitcher_id_cache = {}

def get_pitcher_id(name):
    """Looks up a pitcher's ID by name and caches the result."""
    if name in pitcher_id_cache:
        return pitcher_id_cache[name]
    
    try:
        # Use the wrapper's lookup_player function
        player_info = statsapi.lookup_player(name)
        if player_info:
            pitcher_id = player_info[0]['id']
            pitcher_id_cache[name] = pitcher_id
            return pitcher_id
    except Exception as e:
        print(f"  Could not find ID for pitcher {name}. Error: {e}")
    return None

def get_live_mlb_stats():
    """
    Uses the statsapi wrapper to find all significant matchups for the day.
    A matchup is significant if the batter has > 0 career HRs against the pitcher.
    """
    print("\n--- Starting MLB Stats Fetcher ---")
    final_stats = []
    
    try:
        today_str = datetime.now().strftime('%Y-%m-%d')
        print(f"Fetching schedule for {today_str}...")
        today_schedule = statsapi.schedule(date=today_str)
        
        if not today_schedule:
            print("No games scheduled for today.")
            return []

        print(f"Found {len(today_schedule)} games. Processing all matchups...")

        for game in today_schedule:
            for matchup_type in ['away', 'home']:
                is_away_batting = matchup_type == 'away'
                pitcher_name = game.get('home_probable_pitcher' if is_away_batting else 'away_probable_pitcher')
                
                if not pitcher_name:
                    continue

                # NEW STEP: Look up the pitcher's ID using their name
                pitcher_id = get_pitcher_id(pitcher_name)
                if not pitcher_id:
                    continue
                
                batting_team_id = game.get('away_id' if is_away_batting else 'home_id')
                roster = statsapi.get('team_roster', {'teamId': batting_team_id}).get('roster', [])

                for player in roster:
                    player_id = player['person']['id']
                        
                    try:
                        bvp_data = statsapi.get('person', {'personId': player_id, 'hydrate': f'stats(group=hitting,type=vsPlayer,opposingPlayerId={pitcher_id})'})
                        career_stats = bvp_data['people'][0]['stats'][0]['splits'][0]['stat']

                        if career_stats.get('homeRuns', 0) > 0:
                            print(f"  --> SUCCESS: Found Matchup! {player['person']['fullName']} vs. {pitcher_name} ({career_stats.get('homeRuns')} HR)")
                            
                            final_stats.append({
                                "playerName": player['person']['fullName'],
                                "playerId": player_id,
                                "team": game.get('away_name' if is_away_batting else 'home_name'),
                                "vsPitcher": pitcher_name,
                                "careerHRs": career_stats.get('homeRuns'),
                                "careerAB": career_stats.get('atBats', 0),
                                "careerAVG": career_stats.get('avg', '.000')
                            })

                    except (KeyError, IndexError):
                        continue
                        
        print(f"\nFinished processing. Found {len(final_stats)} significant matchups.")
        return final_stats

    except Exception as e:
        print(f"\n--- AN ERROR OCCURRED ---")
        print(f"Error details: {e}")
        return None

if __name__ == '__main__':
    mlb_data = get_live_mlb_stats()
    
    if mlb_data is not None:
        with open('daily_stats.json', 'w') as f:
            json.dump(mlb_data, f, indent=4)
        print("\n✅ Successfully saved data to 'daily_stats.json'")
        print("You can now upload this file's content to a new GitHub Gist to update your web app.")