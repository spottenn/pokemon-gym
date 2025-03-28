import json
import logging
import os
import time
from typing import Dict, List, Any

from agent.base_agent import BaseAgent
from pokemon_env import PokemonEnvironment

logger = logging.getLogger(__name__)


class PokemonEvaluator:
    """Class for evaluating Pokemon agents."""
    
    def __init__(self, rom_path: str, headless: bool = True, sound: bool = False, output_dir: str = "results"):
        """
        Initialize the evaluator.
        
        Args:
            rom_path: Path to the Pokemon ROM file
            headless: Whether to run without display
            sound: Whether to enable sound
            output_dir: Directory to save results
        """
        self.rom_path = rom_path
        self.headless = headless
        self.sound = sound
        self.output_dir = output_dir
        
        # Ensure the output directory exists
        os.makedirs(output_dir, exist_ok=True)
    
    def evaluate_agent(self, agent: BaseAgent, num_steps: int = 100, save_results: bool = True) -> Dict[str, Any]:
        """
        Evaluate an agent for a specified number of steps.
        
        Args:
            agent: The agent to evaluate
            num_steps: The number of steps to run
            save_results: Whether to save results to a file
            
        Returns:
            A dictionary containing evaluation metrics
        """
        # Create environment
        env = PokemonEnvironment(
            rom_path=self.rom_path,
            headless=self.headless,
            sound=self.sound
        )
        
        # Start the episode
        agent.on_episode_start()
        
        # Track metrics
        total_time = 0
        steps_completed = 0
        badges_earned = []
        max_badges = 0
        
        try:
            logger.info(f"Starting evaluation for {num_steps} steps")
            
            start_time = time.time()
            
            # Initial state
            state = env.state
            
            # Agent loop
            while steps_completed < num_steps:
                # Get action from agent
                step_start = time.time()
                action = agent.get_action(state)
                agent_time = time.time() - step_start
                
                # Execute action in environment
                state = env.step(action)
                
                # Log step information
                logger.info(f"Step {steps_completed+1}: {action}, Location: {state.location}")
                
                # Update metrics
                steps_completed += 1
                total_time += agent_time
                
                # Check badges
                current_badges = state.memory_info.get('badges', [])
                if len(current_badges) > max_badges:
                    max_badges = len(current_badges)
                    badges_earned = current_badges
            
            # End the episode
            agent.on_episode_end()
            
            # Calculate metrics
            total_execution_time = time.time() - start_time
            avg_action_time = total_time / steps_completed if steps_completed > 0 else 0
            avg_env_time = env.get_average_action_time()
            
            # Create results dictionary
            results = {
                "total_steps": steps_completed,
                "badges_earned": badges_earned,
                "total_agent_time": total_time,
                "average_agent_time": avg_action_time,
                "average_env_time": avg_env_time,
                "total_execution_time": total_execution_time,
                "final_location": state.location,
                "party_size": len(state.party_pokemon),
                "party_pokemon": [
                    {
                        "species": pokemon.get("species", "Unknown"),
                        "level": pokemon.get("level", 0)
                    }
                    for pokemon in state.party_pokemon
                ]
            }
            
            # Save results if requested
            if save_results:
                self._save_results(results)
            
            return results
            
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, stopping evaluation")
        except Exception as e:
            logger.error(f"Error during evaluation: {e}")
        finally:
            # Stop the environment
            env.stop()
            
        return {}
    
    def _save_results(self, results: Dict[str, Any]) -> None:
        """Save evaluation results to a file."""
        timestamp = int(time.time())
        filename = os.path.join(self.output_dir, f"evaluation_{timestamp}.json")
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
            
        logger.info(f"Results saved to {filename}")
    
    def compare_agents(self, agents: List[BaseAgent], agent_names: List[str], num_steps: int = 100) -> Dict[str, Any]:
        """
        Compare multiple agents on the same task.
        
        Args:
            agents: List of agents to compare
            agent_names: Names for each agent (for reporting)
            num_steps: Number of steps for each evaluation
            
        Returns:
            A dictionary containing comparison results
        """
        if len(agents) != len(agent_names):
            raise ValueError("Number of agents and agent names must match")
            
        comparison = {}
        
        for agent, name in zip(agents, agent_names):
            logger.info(f"Evaluating agent: {name}")
            results = self.evaluate_agent(agent, num_steps, save_results=True)
            comparison[name] = results
            
        # Save comparison results
        timestamp = int(time.time())
        filename = os.path.join(self.output_dir, f"comparison_{timestamp}.json")
        
        with open(filename, 'w') as f:
            json.dump(comparison, f, indent=2)
            
        logger.info(f"Comparison results saved to {filename}")
        
        return comparison 