import csv
import os
from milestones import all_difficulty_ratings

def evaluate_csv(csv_file_path):
    """
    Evaluate a Pokemon gameplay CSV file and calculate a score based on milestones achieved.
    
    Args:
        csv_file_path (str): Path to the CSV file to evaluate
    
    Returns:
        float: Total score achieved
    """
    if not os.path.exists(csv_file_path):
        print(f"Error: CSV file not found at {csv_file_path}")
        return 0
    
    # Initialize counters to track achievements
    pokemon_seen = set()
    badges_earned = set()
    locations_visited = set()
    
    total_score = 0
    
    # Read the CSV file
    try:
        with open(csv_file_path, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                # Check for Pokemon
                if row.get('pokemons'):
                    # Parse the Pokemon string - format like "[{'nickname': 'CHARMANDER', 'species': 'CHARMANDER', ...}]"
                    pokemons_str = row.get('pokemons', '[]')
                    
                    import ast
                    pokemon_list = ast.literal_eval(pokemons_str)
                    
                    for pokemon_dict in pokemon_list:
                        if isinstance(pokemon_dict, dict) and 'species' in pokemon_dict:
                            pokemon_name = pokemon_dict['species']
                            if pokemon_name and pokemon_name not in pokemon_seen:
                                if pokemon_name in all_difficulty_ratings:
                                    pokemon_score = all_difficulty_ratings[pokemon_name]
                                    total_score += pokemon_score
                                    pokemon_seen.add(pokemon_name)
                                    print(f"New Pokemon: {pokemon_name}, Score: +{pokemon_score}")
                
                # Check for Badges
                if row.get('badges'):
                    badges_str = row.get('badges', '[]')
                    badge_list = ast.literal_eval(badges_str)
                    for badge in badge_list:
                        if badge and badge not in badges_earned:
                            if badge in all_difficulty_ratings:
                                badge_score = all_difficulty_ratings[badge]
                                total_score += badge_score
                                badges_earned.add(badge)
                                print(f"New Badge: {badge}, Score: +{badge_score}")
                
                # Check for Locations
                if row.get('location'):
                    location = row.get('location')
                    location = location.replace(" ", "_")
                    if location and location not in locations_visited:
                        if location in all_difficulty_ratings:
                            location_score = all_difficulty_ratings[location]
                            total_score += location_score
                            locations_visited.add(location)
                            print(f"New Location: {location}, Score: +{location_score}")
    
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return 0
    
    # Print summary
    print("\n=== Evaluation Summary ===")
    print(f"Total Unique Pokemon: {len(pokemon_seen)}")
    print(f"Total Badges Earned: {len(badges_earned)}")
    print(f"Total Locations Visited: {len(locations_visited)}")
    print(f"Total Score: {total_score:.2f}")
    
    return total_score

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Evaluate Pokemon gameplay CSV file")
    parser.add_argument("csv_file", help="Path to the gameplay CSV file to evaluate")
    
    args = parser.parse_args()
    
    evaluate_csv(args.csv_file)
