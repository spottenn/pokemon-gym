import os
import time
import random
import datetime
import logging
import argparse
import csv
import json
import shutil
from typing import Dict, Any
from pokemon_env import PokemonEnvironment, PressKey, Wait
from server.evaluate import PokemonEvaluator
from benchflow import BenchClient

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Global variables for session management
OUTPUT_DIR = "evaluation_sessions"
current_session_dir = None
IMAGES_FOLDER = "images"
CSV_WRITER = None
CSV_FILE = None

class PokemonClient(BenchClient):
    def __init__(self, intelligence_url: str, max_retry: int = 1):
        super().__init__(intelligence_url, max_retry)
    
    def prepare_input(self, raw_step_inputs: Dict[str, Any]) -> Dict[str, Any]:
        return raw_step_inputs

    def parse_response(self, raw_response: str) -> Dict[str, Any]:
        # assume the raw_response is press_key or wait plus the keys and frames
        if "press_key" in raw_response:
            keys_str = raw_response.split("press_key")[1].strip()
            keys_list = keys_str.split()
            return PressKey(keys=keys_list).to_dict()
        elif "wait" in raw_response:
            frames = raw_response.split("wait")[1].strip()
            return Wait(frames=int(frames)).to_dict()
        else:
            raise ValueError(f"Invalid response: {raw_response}")

def setup_session_directory():
    """Create a directory for the evaluation session."""
    global current_session_dir
    
    # Use a fixed directory name instead of timestamp
    session_dir = os.path.join(OUTPUT_DIR, "latest_evaluation")
    
    # Remove existing directory if it exists
    if os.path.exists(session_dir):
        import shutil
        try:
            shutil.rmtree(session_dir)
            logger.info(f"Removed existing directory: {session_dir}")
        except Exception as e:
            logger.error(f"Error removing existing directory: {e}")
    
    # Create session directory
    os.makedirs(session_dir, exist_ok=True)
    
    # Create images subdirectory
    images_dir = os.path.join(session_dir, IMAGES_FOLDER)
    os.makedirs(images_dir, exist_ok=True)
    
    current_session_dir = session_dir
    logger.info(f"Using session directory: {session_dir}")
    
    return session_dir

def initialize_csv_logger():
    """Initialize the CSV logger within the session directory."""
    global CSV_WRITER, CSV_FILE
    
    try:
        filename = os.path.join(current_session_dir, "results.csv")
        
        CSV_FILE = open(filename, 'w', newline='')
        fieldnames = ['timestamp', 'step_number', 'action_type', 'action_details', 'badges', 
                      'inventory', 'location', 'money', 'coordinates', 'pokemons', 'dialog', 
                      'time_interval', 'score']
        CSV_WRITER = csv.DictWriter(CSV_FILE, fieldnames=fieldnames)
        CSV_WRITER.writeheader()
        logger.info(f"Results will be logged to {filename}")
        return filename
    except Exception as e:
        logger.error(f"Error initializing CSV logger: {e}")
        CSV_WRITER = None
        if CSV_FILE:
            CSV_FILE.close()
            CSV_FILE = None
        return None

def log_state(state_dict, action, step_count, evaluator):
    """Log the current state to the CSV file."""
    global CSV_WRITER, CSV_FILE
    global last_action_time
    
    if CSV_WRITER is None:
        return
    
    try:
        # Calculate time interval since last action
        current_time = time.time()
        if 'last_action_time' not in globals():
            # First action, initialize last_action_time
            last_action_time = current_time
            time_interval = 0.0
        else:
            # Calculate interval since last action
            time_interval = current_time - last_action_time
            last_action_time = current_time
        
        action_type = "press_key" if isinstance(action, PressKey) else "wait"
        action_details = action.keys if isinstance(action, PressKey) else action.frames
        
        row = {
            'timestamp': datetime.datetime.now().isoformat(),
            'step_number': step_count,
            'action_type': action_type,
            'action_details': str(action_details),
            'badges': str(state_dict.get('badges', [])),
            'inventory': str(state_dict.get('inventory', [])),
            'location': state_dict.get('location', ''),
            'money': state_dict.get('money', 0),
            'coordinates': str(state_dict.get('coordinates', [])),
            'pokemons': state_dict.get('pokemons', []),
            'dialog': state_dict.get('dialog', ''),
            'time_interval': round(time_interval, 3),  # Time since last action, in seconds
            'score': evaluator.total_score
        }
        CSV_WRITER.writerow(row)
        CSV_FILE.flush()  # Ensure data is written immediately
        
        # If points were gained, log it to console
        initial_score = evaluator.total_score
        score_gained = evaluate_state(evaluator, state_dict)
        if score_gained > 0:
            logger.info(f"Score +{score_gained:.2f} → Total: {evaluator.total_score:.2f}")
            
    except Exception as e:
        logger.error(f"Error logging to CSV: {e}")

def save_evaluation_summary(evaluator, output_dir, duration, step_count):
    """
    Save final evaluation results to a summary file in JSON format
    
    Args:
        evaluator: PokemonEvaluator instance
        output_dir: Output directory path
        duration: Evaluation duration in seconds
        step_count: Total number of steps taken
    """
    summary_file = os.path.join(output_dir, "summary.json")
    
    # Calculate average execution time per step
    avg_execution_time = duration / max(1, step_count)
    
    # Create summary data structure
    summary_data = {
        "duration_minutes": round(duration/60, 1),
        "total_steps": step_count,
        "timing": {
            "total_execution_time": round(duration, 2),
            "average_time_per_step": round(avg_execution_time, 3)
        },
        "final_score": round(evaluator.total_score, 2),
        "stats": {
            "pokemon_discovered": len(evaluator.pokemon_seen),
            "badges_earned": len(evaluator.badges_earned),
            "locations_visited": len(evaluator.locations_visited)
        },
        "pokemon_details": sorted(list(evaluator.pokemon_seen)),
        "badge_details": sorted(list(evaluator.badges_earned)),
        "location_details": sorted(list(evaluator.locations_visited))
    }
    
    with open(summary_file, 'w') as f:
        json.dump(summary_data, f, indent=2)
    
    logger.info(f"JSON summary saved to: {summary_file}")
    return summary_file


def evaluate_state(evaluator, state_dict):
    """
    Evaluate game state using the PokemonEvaluator
    
    Args:
        evaluator: PokemonEvaluator instance
        state_dict: Game state dictionary
    
    Returns:
        Total score before evaluation
    """
    # Store initial score to calculate gain
    initial_score = evaluator.total_score
    
    # Check for new Pokemon
    pokemons = state_dict.get('pokemons', [])
    for pokemon in pokemons:
        pokemon_name = pokemon.get('species', '').upper()
        if pokemon_name:
            evaluator.evaluate_pokemon(pokemon_name)
    
    # Check for new badges
    badges = state_dict.get('badges', [])
    for badge in badges:
        badge_name = badge.upper()
        if badge_name:
            evaluator.evaluate_badge(badge_name)
    
    # Check for new location
    location = state_dict.get('location', '')
    if location:
        evaluator.evaluate_location(location)
    
    # Calculate score gained
    score_gained = evaluator.total_score - initial_score
    return score_gained


def parse_args():
    parser = argparse.ArgumentParser(description='Evaluate Pokemon game')
    parser.add_argument('--intelligence_url', type=str, default="http://localhost:8000", help='Intelligence URL')
    parser.add_argument('--rom_path', type=str, default="Pokemon_Red.gb", help='ROM path')
    parser.add_argument('--max_duration', type=int, default=1, help='Max duration in minutes')
    return parser.parse_args()


def main(args):
    """Main function to run 30-minute Pokemon evaluation"""
    # ROM path
    rom_path = args.rom_path
    
    # Check if ROM file exists
    if not os.path.exists(rom_path):
        logger.error(f"ROM file {rom_path} does not exist!")
        return
        
    client = PokemonClient(intelligence_url="http://localhost:8000", max_retry=1)
    
    # Create output directory and set up CSV logging
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    session_dir = setup_session_directory()
    csv_file = initialize_csv_logger()
    
    # Initialize evaluator
    evaluator = PokemonEvaluator()
    
    # Initialize environment
    logger.info(f"Initializing environment, ROM path: {rom_path}")
    try:
        env = PokemonEnvironment(rom_path=rom_path, headless=True, sound=False)
        logger.info("Environment initialization successful")
    except Exception as e:
        logger.error(f"Environment initialization failed: {e}")
        return
    
    # Set simulation parameters
    start_time = time.time()
    max_duration = args.max_duration * 60  # Convert minutes to seconds
    step_count = 0
    last_summary_time = start_time
    summary_interval = 60  # Print summary every 60 seconds
    
    logger.info(f"Starting Pokemon evaluation simulation for {max_duration/60} minutes")
    logger.info(f"Results directory: {session_dir}")
    
    # Get initial state and evaluate
    state = env.state
    state_dict = {
        'player_name': state.player_name,
        'rival_name': state.rival_name,
        'money': state.money,
        'location': state.location,
        'coordinates': state.coordinates,
        'badges': state.badges,
        'valid_moves': state.valid_moves,
        'inventory': state.inventory,
        'dialog': state.dialog,
        'pokemons': state.pokemons,
        'screenshot_base64': state.screenshot_base64,
        'collision_map': env.get_collision_map(),
        'step_number': env.steps_taken,
        'score': evaluator.total_score
    }
    
    # Log initial state
    
    # Main simulation loop
    try:
        while time.time() - start_time < max_duration:
            # Generate random action
            action = client.get_response(state_dict)
            if action['action_type'] == 'press_key':
                action = PressKey(keys=action['keys'])
            else:
                action = Wait(int(action['frames']))

            # Execute action and get new state
            try:
                new_state = env.step(action)
                step_count += 1
                
                # Convert GameState object to dictionary
                state_dict = {
                    'player_name': new_state.player_name,
                    'rival_name': new_state.rival_name,
                    'money': new_state.money,
                    'location': new_state.location,
                    'coordinates': new_state.coordinates,
                    'badges': new_state.badges,
                    'valid_moves': new_state.valid_moves,
                    'inventory': new_state.inventory,
                    'dialog': new_state.dialog,
                    'pokemons': new_state.pokemons,
                    'screenshot_base64': new_state.screenshot_base64,
                    'collision_map': env.get_collision_map(),
                    'step_number': env.steps_taken,
                    'score': evaluator.total_score
                }
                
                # Log state to CSV and evaluate
                log_state(state_dict, action, step_count, evaluator)
                
                # Print summary every minute
                if time.time() - last_summary_time >= summary_interval:
                    elapsed_time = time.time() - start_time
                    remaining_time = max_duration - elapsed_time
                    
                    logger.info(f"\n--- Status after {elapsed_time/60:.1f} minutes ---")
                    logger.info(f"Total Score: {evaluator.total_score:.2f}")
                    logger.info(f"Pokemon: {len(evaluator.pokemon_seen)} Pokemon discovered")
                    logger.info(f"Badges: {len(evaluator.badges_earned)} Badges earned")
                    logger.info(f"Locations: {len(evaluator.locations_visited)} Locations visited")
                    logger.info(f"Remaining Time: {remaining_time/60:.1f} minutes")
                    logger.info("----------------------------------------\n")
                    last_summary_time = time.time()
                
                # Short delay to prevent executing too quickly
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Step execution failed: {e}")
                continue
            
    except KeyboardInterrupt:
        logger.info("\nEvaluation interrupted by user")
    finally:
        # Always stop the environment and save results
        try:
            env.stop()
            logger.info("Environment stopped")
            
            # Save final evaluation summary
            total_duration = time.time() - start_time
            summary_file = save_evaluation_summary(evaluator, session_dir, total_duration, step_count)
            
            # Close CSV file
            if CSV_FILE:
                CSV_FILE.close()
                
            logger.info(f"\nEvaluation completed after {total_duration/60:.1f} minutes")
            logger.info(f"Total Score: {evaluator.total_score:.2f}")
            logger.info(f"Total Steps: {step_count}")
            logger.info(f"Results saved to: {OUTPUT_DIR}/latest_evaluation/")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


if __name__ == "__main__":
    args = parse_args()
    main(args)
