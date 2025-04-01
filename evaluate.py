import os
import time
import random
import datetime
import logging
import argparse
from typing import Dict, Any
from pokemon_env import PokemonEnvironment, Action, PressKey, Wait
from server.evaluate import PokemonEvaluator
from benchflow import BenchClient

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class PokemonClient(BenchClient):
    def __init__(self, intelligence_url: str, max_retry: int = 1):
        super().__init__(intelligence_url, max_retry)
    
    def prepare_input(self, raw_step_inputs: Dict[str, Any]) -> Dict[str, Any]:
        return raw_step_inputs

    def parse_response(self, raw_response: str) -> Dict[str, Any]:
        # assume the raw_response is press_key or wait plus the keys and frames
        if "press_key" in raw_response:
            keys = raw_response.split("press_key")[1].strip()
            return PressKey(keys)
        elif "wait" in raw_response:
            frames = raw_response.split("wait")[1].strip()
            return Wait(frames)
        else:
            raise ValueError(f"Invalid response: {raw_response}")

def generate_random_action() -> Action:
    """
    Generate random action
    
    Returns:
        A random action (PressKey or Wait)
    """
    # Available keys
    available_keys = ["a", "b", "start", "select", "up", "down", "left", "right"]
    
    # 70% chance to select key operation, 30% chance to wait
    if random.random() < 0.7:
        # Select 1-2 keys
        num_keys = random.randint(1, 2)
        keys = random.sample(available_keys, num_keys)
        return PressKey(keys)
    else:
        # Wait for 10-60 frames
        frames = random.randint(10, 60)
        return Wait(frames)


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
    parser.add_argument('--max_duration', type=int, default=30, help='Max duration in minutes')
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
    # Create output directory with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"evaluation_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    
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
    max_duration = args.max_duration * 60  # 5 minutes (in seconds)
    step_count = 0
    last_summary_time = start_time
    summary_interval = 60  # Print summary every 60 seconds
    
    logger.info(f"Starting Pokemon evaluation simulation for {max_duration/60} minutes")
    logger.info(f"Results will be saved to: {output_dir}")
    
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
        'execution_time': start_time - start_time,
        'score': evaluator.total_score
    }
    
    score_gained = evaluate_state(evaluator, state_dict)
    
    # Main simulation loop
    try:
        while time.time() - start_time < max_duration:
            # Generate random action
            action = client.get_response(state_dict)
            
            # Execute action and get new state
            try:
                new_state = env.step(action)
                step_count += 1
                logger.info(f"Step {step_count}: Executing action {action}")
                
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
                    'execution_time': time.time() - start_time,
                    'score': evaluator.total_score
                }
                
                # Evaluate state
                score_gained = evaluate_state(evaluator, state_dict)
                
                # Log progress
                elapsed_time = time.time() - start_time
                remaining_time = max_duration - elapsed_time
                
                # Print score information (if points were gained)
                if score_gained > 0:
                    logger.info(f"Score +{score_gained:.2f} → Total: {evaluator.total_score:.2f}")
                
                # Print summary every minute
                if time.time() - last_summary_time >= summary_interval:
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
        # Always stop the environment
        try:
            env.stop()
            logger.info("Environment stopped")
        except Exception as e:
            logger.error(f"Error stopping environment: {e}")
    
    # Save final results to txt file
    summary_file = os.path.join(output_dir, "evaluation_summary.txt")
    with open(summary_file, 'w') as f:
        f.write("=== Pokemon Game Evaluation Summary ===\n\n")
        f.write(f"Final Score: {evaluator.total_score:.2f}\n")
        f.write(f"Pokemon Discovered: {len(evaluator.pokemon_seen)}\n")
        f.write(f"Badges Earned: {len(evaluator.badges_earned)}\n")
        f.write(f"Locations Visited: {len(evaluator.locations_visited)}\n\n")
        
        f.write("--- Pokemon Details ---\n")
        for pokemon in sorted(evaluator.pokemon_seen):
            f.write(f"- {pokemon}\n")
        
        f.write("\n--- Badge Details ---\n")
        for badge in sorted(evaluator.badges_earned):
            f.write(f"- {badge}\n")
        
        f.write("\n--- Location Details ---\n")
        for location in sorted(evaluator.locations_visited):
            f.write(f"- {location}\n")
    
    logger.info(f"\nEvaluation completed after {(time.time() - start_time)/60:.1f} minutes")
    logger.info(f"Total Score: {evaluator.total_score:.2f}")
    logger.info(f"Total Steps: {step_count}")
    logger.info(f"Full results saved to: {summary_file}")


if __name__ == "__main__":
    args = parse_args()
    main(args)
