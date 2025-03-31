import os
import time
import random
import datetime
import logging

from pokemon_env import PokemonEnvironment, Action, PressKey, Wait
from server.evaluate import PokemonEvaluator

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

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


def main():
    """Main function to run 30-minute Pokemon evaluation"""
    # ROM path
    rom_path = "Pokemon_Red.gb"  # Make sure this path is correct
    
    # Check if ROM file exists
    if not os.path.exists(rom_path):
        logger.error(f"ROM file {rom_path} does not exist!")
        return
    
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
    max_duration = 30 * 60  # 30 minutes (in seconds)
    step_count = 0
    last_summary_time = start_time
    summary_interval = 60  # Print summary every 60 seconds
    
    logger.info(f"Starting Pokemon evaluation simulation for 30 minutes")
    logger.info(f"Results will be saved to: {output_dir}")
    
    # Get initial state and evaluate
    initial_state = env.state
    initial_state_dict = {
        'player_name': initial_state.player_name,
        'rival_name': initial_state.rival_name,
        'money': initial_state.money,
        'location': initial_state.location,
        'coordinates': initial_state.coordinates,
        'badges': initial_state.badges,
        'valid_moves': initial_state.valid_moves,
        'inventory': initial_state.inventory,
        'dialog': initial_state.dialog,
        'pokemons': initial_state.pokemons
    }
    
    evaluator.evaluate_state(initial_state_dict)
    
    # Main simulation loop
    try:
        while time.time() - start_time < max_duration:
            # Generate random action
            action = generate_random_action()
            
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
                    'pokemons': new_state.pokemons
                }
                
                # Evaluate state
                score_gained = evaluator.evaluate_state(state_dict)
                
                # Log progress
                elapsed_time = time.time() - start_time
                remaining_time = max_duration - elapsed_time
                
                # Print score information (if points were gained)
                if score_gained > 0:
                    logger.info(f"Score +{score_gained:.2f} → Total: {evaluator.total_score:.2f}")
                
                # Print summary every minute
                if time.time() - last_summary_time >= summary_interval:
                    summary = evaluator.get_summary()
                    logger.info(f"\n--- Status after {elapsed_time/60:.1f} minutes ---")
                    logger.info(f"Total Score: {evaluator.total_score:.2f}")
                    logger.info(f"Pokemon: {summary['pokemon']['count']} ({summary['pokemon']['percentage']:.1f}%)")
                    logger.info(f"Badges: {summary['badges']['count']} ({summary['badges']['percentage']:.1f}%)")
                    logger.info(f"Locations: {summary['locations']['count']}")
                    logger.info(f"Remaining Time: {remaining_time/60:.1f} minutes")
                    logger.info("----------------------------------------\n")
                    last_summary_time = time.time()
                    
                    # Save intermediate summary
                    evaluator.save_summary(output_dir)
                
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
    
    # Save final results
    final_summary_path = evaluator.save_summary(output_dir)
    
    logger.info(f"\nEvaluation completed after {(time.time() - start_time)/60:.1f} minutes")
    logger.info(f"Total Score: {evaluator.total_score:.2f}")
    logger.info(f"Total Steps: {step_count}")
    logger.info(f"Full results saved to: {final_summary_path}")


if __name__ == "__main__":
    main()
