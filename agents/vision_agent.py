import argparse
import logging
import time
import os
import sys
import json
import datetime
import base64
import io
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from PIL import Image
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from .env file
load_dotenv()

import requests

# Import our unified LLM provider
try:
    from .llm_provider import LiteLLMProvider
    from .session_manager import SessionManager
except ImportError:
    # Handle case when running as main script
    from llm_provider import LiteLLMProvider
    from session_manager import SessionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Create logs directory if not exists
os.makedirs("logs", exist_ok=True)


class ActionType(str, Enum):
    PRESS_KEY = "press_key"
    WAIT = "wait"


class Button(str, Enum):
    A = "a"
    B = "b"
    START = "start"
    SELECT = "select"
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"


class VisionAgent:
    """Simple vision-based Pokemon agent that makes single-turn decisions based on screenshots."""
    
    def __init__(
        self,
        server_url: str = "http://localhost:8080",
        provider: str = "ollama",
        model_name: str = "gemma3:latest",
        temperature: float = 0.7,
        max_tokens: int = 1500,
        thoughts_file: str = "thoughts.txt",
        max_retries: int = 3,
        headless: bool = True,
        sound: bool = False
    ):
        self.server_url = server_url
        self.thoughts_file = thoughts_file
        self.max_retries = max_retries
        self.step_count = 0
        self.headless = headless
        self.sound = sound
        
        # Simple memory system - keep last few actions and observations
        self.recent_actions: List[Dict] = []
        self.memory_limit = 10
        
        # Initialize LLM provider
        self.llm = LiteLLMProvider(
            provider=provider,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Session manager for auto-resume
        self.session_manager = SessionManager()
        
        logger.info(f"Vision agent initialized with {provider} model: {model_name}")
        logger.info(f"Thoughts will be written to: {thoughts_file}")

    def get_simple_prompt(self, screenshot_b64: str, location: str, recent_actions: List[str]) -> str:
        """Create a vision-focused prompt with chain-of-thought reasoning."""
        prompt = f"""You are playing Pokemon Red. Look at the screenshot and decide what to do next.

CURRENT LOCATION: {location}

RECENT ACTIONS: {', '.join(recent_actions[-5:]) if recent_actions else 'None'}

Your goal is to progress through the Pokemon Red game. Analyze the screenshot carefully and choose the best action.

IMPORTANT: Don't just repeat the same action! Look at what's actually on screen:
- If you see a menu, navigate it properly with up/down/a/b
- If you see dialogue, read it and respond appropriately 
- If you see the overworld, move around with directional keys
- If you're stuck in a loop, try a different approach

Format your response like this:

THOUGHTS: [Describe what you see in the screenshot. What objects, characters, menus, or text are visible? What is the current game state? Based on this observation, what should you do next and WHY?]

ACTION: press_key [button]
OR
ACTION: wait [frames]

Available actions:
- press_key: [a, b, start, select, up, down, left, right]  
- wait: [number of frames, e.g., 60]

Remember: Vary your actions based on what you actually see! Don't just press 'a' repeatedly unless you're specifically advancing dialogue."""

        return prompt

    def parse_response(self, response: str) -> Tuple[Optional[str], Optional[Dict]]:
        """Parse LLM response to extract thoughts and action."""
        try:
            lines = response.strip().split('\n')
            thoughts = None
            action_line = None
            
            # Extract thoughts
            for i, line in enumerate(lines):
                if line.strip().startswith('THOUGHTS:'):
                    # Collect thoughts from this line and continue until ACTION line
                    thoughts_lines = [line.replace('THOUGHTS:', '').strip()]
                    for j in range(i + 1, len(lines)):
                        if lines[j].strip().startswith('ACTION:'):
                            break
                        thoughts_lines.append(lines[j].strip())
                    thoughts = ' '.join(thoughts_lines).strip()
                    break
            
            # Extract action
            for line in lines:
                if line.strip().startswith('ACTION:'):
                    action_line = line.strip()
                    break
            
            if not action_line:
                logger.warning("No ACTION found in response")
                return thoughts, None
                
            # Parse "ACTION: press_key a" or "ACTION: wait 60"
            action_part = action_line.replace('ACTION:', '').strip()
            parts = action_part.split()
            
            if len(parts) < 2:
                logger.warning(f"Invalid action format: {action_part}")
                return thoughts, None
                
            action_type = parts[0]
            action = None
            
            if action_type == "press_key":
                if len(parts) != 2:
                    logger.warning(f"Invalid press_key format: {action_part}")
                    return thoughts, None
                action = {
                    "action_type": "press_key",
                    "keys": [parts[1]]
                }
            elif action_type == "wait":
                if len(parts) != 2:
                    logger.warning(f"Invalid wait format: {action_part}")
                    return thoughts, None
                try:
                    frames = int(parts[1])
                    action = {
                        "action_type": "wait",
                        "frames": frames
                    }
                except ValueError:
                    logger.warning(f"Invalid frame count: {parts[1]}")
                    return thoughts, None
            else:
                logger.warning(f"Unknown action type: {action_type}")
                return thoughts, None
                
            return thoughts, action
                
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return None, None

    def get_game_state(self) -> Optional[Dict]:
        """Get current game state from server."""
        try:
            response = requests.get(f"{self.server_url}/game_state", timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get game state: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error getting game state: {e}")
            return None

    def send_action(self, action: Dict) -> Optional[Dict]:
        """Send action to server and get response."""
        try:
            # In streaming mode, we send the action and then immediately request the game state
            # The server will queue the action and return the current state
            response = requests.post(f"{self.server_url}/action", json=action, timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to send action: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error sending action: {e}")
            return None

    def update_thoughts_file(self, thoughts: str, action_desc: str, location: str):
        """Update the thoughts file for streaming display."""
        try:
            with open(self.thoughts_file, 'w', encoding='utf-8') as f:
                f.write(f"=== AI Vision Agent - Step {self.step_count} ===\n\n")
                
                if thoughts:
                    f.write("REASONING:\n")
                    f.write(thoughts)
                    f.write("\n\n")
                
                f.write(f"ACTION: {action_desc}\n\n")
                f.write(f"=== Location: {location} ===\n")
                f.write(f"=== Last Actions: {', '.join([a.get('type', 'unknown') for a in self.recent_actions[-3:]])} ===")
        except Exception as e:
            logger.error(f"Error updating thoughts file: {e}")

    def add_to_memory(self, action_type: str, location: str, observation: str):
        """Add action and observation to simple memory."""
        memory_entry = {
            "step": self.step_count,
            "type": action_type,
            "location": location,
            "observation": observation
        }
        self.recent_actions.append(memory_entry)
        
        # Keep only recent entries
        if len(self.recent_actions) > self.memory_limit:
            self.recent_actions = self.recent_actions[-self.memory_limit:]

    def run_step(self) -> bool:
        """Run a single step of the vision agent."""
        try:
            # Get current game state
            game_state = self.get_game_state()
            if not game_state:
                logger.error("Could not get game state")
                return False
            
            self.step_count += 1
            screenshot_b64 = game_state.get("screenshot_base64", "")
            location = game_state.get("location", "Unknown")
            
            # Create simple prompt
            recent_action_types = [a.get("type", "unknown") for a in self.recent_actions]
            prompt = self.get_simple_prompt(screenshot_b64, location, recent_action_types)
            
            # Get LLM response with screenshot as image
            response = None
            for attempt in range(self.max_retries):
                try:
                    response = self.llm.generate(prompt, image_b64=screenshot_b64)
                    break
                except Exception as e:
                    logger.warning(f"LLM attempt {attempt + 1} failed: {e}")
                    if attempt == self.max_retries - 1:
                        logger.error("All LLM attempts failed")
                        return False
                    time.sleep(1)
            
            if not response:
                return False
            
            # Parse response for thoughts and action
            thoughts, action = self.parse_response(response)
            if not action:
                logger.warning("Could not parse action, using default wait")
                action = {"action_type": "wait", "frames": 60}
                thoughts = thoughts or "Could not parse action, using default wait"
            
            # Send action
            result = self.send_action(action)
            if not result:
                logger.error("Failed to send action")
                return False
            
            # Create action description
            action_desc = f"{action['action_type']}"
            if action['action_type'] == 'press_key':
                action_desc += f" {action['keys'][0]}"
            elif action['action_type'] == 'wait':
                action_desc += f" {action['frames']}"
            
            # Update thoughts file with reasoning and action
            self.update_thoughts_file(thoughts or "No thoughts provided", action_desc, location)
            
            # Update memory
            self.add_to_memory(action_desc, location, f"Moved to {result.get('location', 'unknown')}")
            
            logger.info(f"Step {self.step_count}: {action_desc} in {location}")
            return True
            
        except Exception as e:
            logger.error(f"Error in run_step: {e}")
            return False

    def run(self, max_steps: int = 1000):
        """Run the vision agent for a specified number of steps."""
        logger.info(f"Starting vision agent for {max_steps} steps")
        
        # Try to resume latest session
        latest_session = self.session_manager.get_latest_session()
        if latest_session:
            logger.info(f"Resuming latest session: {latest_session}")
            # Load the session data locally
            if self.session_manager.load_session(latest_session):
                logger.info(f"Successfully loaded session data for: {latest_session}")
            else:
                logger.warning(f"Failed to load session data for: {latest_session}")
            # Initialize with resume
            init_data = {
                "headless": self.headless,
                "sound": self.sound,
                "streaming": True,
                "session_id": latest_session
            }
        else:
            # New session
            init_data = {
                "headless": self.headless,
                "sound": self.sound,
                "streaming": True
            }
        
        # Initialize server
        try:
            response = requests.post(f"{self.server_url}/initialize", json=init_data, timeout=30)
            if response.status_code != 200:
                logger.error(f"Failed to initialize server: {response.status_code}")
                return
        except Exception as e:
            logger.error(f"Error initializing server: {e}")
            return
        
        # Main game loop
        for step in range(max_steps):
            success = self.run_step()
            if not success:
                logger.warning("Step failed, continuing...")
            
            # Small delay to prevent overwhelming the server
            time.sleep(0.5)
        
        logger.info("Vision agent run completed")


def main():
    parser = argparse.ArgumentParser(description="Pokemon Red Vision Agent")
    parser.add_argument("--server-url", default="http://localhost:8080", help="Server URL")
    parser.add_argument("--provider", default="ollama", help="LLM provider")
    parser.add_argument("--model", default="gemma3:latest", help="Model name")
    parser.add_argument("--temperature", type=float, default=0.7, help="Temperature")
    parser.add_argument("--max-tokens", type=int, default=1500, help="Max tokens")
    parser.add_argument("--thoughts-file", default="thoughts.txt", help="Thoughts output file")
    parser.add_argument("--max-steps", type=int, default=1000, help="Maximum steps to run")
    parser.add_argument("--max-retries", type=int, default=3, help="Max LLM retries")
    parser.add_argument("--headless", action="store_true", default=False, help="Run without game window")
    parser.add_argument("--sound", action="store_true", default=False, help="Enable game sound")
    
    args = parser.parse_args()
    
    agent = VisionAgent(
        server_url=args.server_url,
        provider=args.provider,
        model_name=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        thoughts_file=args.thoughts_file,
        max_retries=args.max_retries,
        headless=args.headless,
        sound=args.sound
    )
    
    agent.run(max_steps=args.max_steps)


if __name__ == "__main__":
    main()