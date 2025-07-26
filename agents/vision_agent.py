"""
Pokemon Red Vision Agent with LiteLLM Tool Calling and Structured Chain of Thought
"""

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
import requests
import litellm

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from .env file
load_dotenv()

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
    format="%(asctime)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Create logs directory if not exists
os.makedirs("logs", exist_ok=True)


class Button(str, Enum):
    """Available buttons in Pokemon Red"""
    A = "A"
    B = "B"
    START = "start"
    SELECT = "select"
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"


# Tool definitions for LiteLLM
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "press_button",
            "description": "Press a button on the Game Boy to interact with Pokemon Red",
            "parameters": {
                "type": "object",
                "properties": {
                    "button": {
                        "type": "string",
                        "enum": ["A", "B", "start", "select", "up", "down", "left", "right"],
                        "description": "The button to press on the Game Boy"
                    }
                },
                "required": ["button"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "wait",
            "description": "Wait for a specified number of frames (60 frames = 1 second)",
            "parameters": {
                "type": "object",
                "properties": {
                    "frames": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 300,
                        "description": "Number of frames to wait (60 frames = 1 second)"
                    }
                },
                "required": ["frames"]
            }
        }
    }
]


class VisionAgent:
    """Advanced vision-based Pokemon agent with LiteLLM tool calling and structured reasoning."""

    def __init__(
        self,
        server_url: str = "http://localhost:8080",
        provider: str = "ollama",
        model_name: str = "PetrosStav/gemma3-tools:4b",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        max_retries: int = 3,
        headless: bool = True,
        sound: bool = False,
        upscale_factor: float = 2.0,
        conversation_history_limit: int = 10,
    ):
        self.server_url = server_url
        self.max_retries = max_retries
        self.step_count = 0
        self.headless = headless
        self.sound = sound
        self.upscale_factor = upscale_factor
        self.conversation_history_limit = conversation_history_limit
        
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        
        # Set up proper log files with timestamps
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.thoughts_log_file = os.path.join(
            "logs", f"vision_agent_thoughts_{timestamp}.log"
        )
        
        # Conversation history for multi-turn context
        self.conversation_history: List[Dict[str, Any]] = []
        
        # Initialize LLM provider
        self.llm = LiteLLMProvider(
            provider=provider,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        # Session manager for auto-resume
        self.session_manager = SessionManager()
        
        # Game context tracking
        self.game_context = {
            "location": "unknown",
            "objective": "progress through Pokemon Red",
            "recent_events": [],
            "battle_state": None,
            "menu_state": None,
        }
        
        logger.info(f"Vision agent initialized with {provider} model: {model_name}")
        logger.info(f"Thoughts will be written to: {self.thoughts_log_file}")
        logger.info(f"Image upscaling factor: {self.upscale_factor}x")

    def upscale_image(self, image_b64: str) -> str:
        """Upscale the image for better vision model performance."""
        try:
            # Decode base64 image
            image_data = base64.b64decode(image_b64)
            image = Image.open(io.BytesIO(image_data))
            
            # Calculate new dimensions
            new_width = int(image.width * self.upscale_factor)
            new_height = int(image.height * self.upscale_factor)
            
            # Upscale using LANCZOS for quality
            upscaled = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert back to base64
            buffer = io.BytesIO()
            upscaled.save(buffer, format="PNG")
            upscaled_b64 = base64.b64encode(buffer.getvalue()).decode()
            
            logger.debug(f"Upscaled image from {image.width}x{image.height} to {new_width}x{new_height}")
            return upscaled_b64
            
        except Exception as e:
            logger.warning(f"Failed to upscale image: {e}")
            return image_b64  # Return original if upscaling fails

    def create_system_prompt(self) -> str:
        """Create the system prompt establishing the agent's identity and capabilities."""
        return """You are an expert Pokemon Red player with decades of experience. You're playing through the entire game strategically, making thoughtful decisions to progress efficiently while enjoying the journey.

## Your Identity
- You are patient and persistent, understanding that Pokemon Red is a long adventure requiring careful planning
- You analyze each screenshot methodically before acting
- You remember past events and learn from mistakes
- You think several steps ahead, considering the consequences of your actions

## Game Understanding
- Pokemon Red is a turn-based RPG where you collect Pokemon, battle trainers, and become the Pokemon Champion
- The game requires navigation through towns, routes, caves, and buildings
- Battles require strategic move selection based on type advantages
- Items and Pokemon management through various menus is crucial
- NPCs provide important information and items

## Chain of Thought Protocol
Before EVERY action, you MUST output structured reasoning in this exact format:

**COT_effort**: [LOW/MEDIUM/HIGH] - How much thinking this situation requires
**COT_length**: [50-500] - Expected reasoning length in words
**COT**: [Your detailed step-by-step reasoning]

### Effort Guidelines:
- **LOW**: Simple navigation, reading dialogue, basic menu navigation (50-100 words)
- **MEDIUM**: Choosing moves in battle, deciding which Pokemon to catch, item usage (100-250 words)  
- **HIGH**: Complex battles, team composition decisions, puzzle solving, strategic planning (250-500 words)

## Your Capabilities
You have two tools available:
1. **press_button**: Press a Game Boy button (A, B, start, select, up, down, left, right)
2. **wait**: Wait for a specified number of frames (60 frames = 1 second)

## Important Notes
- ALWAYS call a tool after your reasoning - never output reasoning without an action
- Base decisions solely on visual information from the screenshot
- If stuck, try different approaches rather than repeating the same action
- Remember this is a marathon, not a sprint - make steady progress"""

    def analyze_screenshot_context(self, screenshot_b64: str) -> Dict[str, Any]:
        """Analyze the screenshot to determine current game context."""
        # This would ideally use a separate vision analysis, but for now we'll
        # return a basic context that will be refined by the main LLM call
        return {
            "requires_analysis": True,
            "timestamp": datetime.datetime.now().isoformat()
        }

    def build_conversation_messages(self, screenshot_b64: str) -> List[Dict[str, Any]]:
        """Build the conversation messages including history and current screenshot."""
        messages = [
            {"role": "system", "content": self.create_system_prompt()}
        ]
        
        # Add conversation history (excluding very old entries)
        history_start = max(0, len(self.conversation_history) - self.conversation_history_limit)
        for entry in self.conversation_history[history_start:]:
            messages.append(entry)
        
        # Add current screenshot with analysis request
        user_message = {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"Step {self.step_count}: Analyze this Pokemon Red screenshot and decide the next action. Remember to output COT_effort, COT_length, and COT before calling a tool."
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{screenshot_b64}"
                    }
                }
            ]
        }
        messages.append(user_message)
        
        return messages

    def parse_tool_response(self, response: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict], Optional[Dict]]:
        """Parse LiteLLM response to extract reasoning and tool calls."""
        try:
            # Extract the main content (reasoning)
            content = response.choices[0].message.content or ""
            
            # Extract tool calls if present
            tool_calls = response.choices[0].message.tool_calls
            
            if not tool_calls:
                logger.warning("No tool calls found in response")
                return content, None, None
            
            # Get the first tool call
            tool_call = tool_calls[0]
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            # Convert to our action format
            if function_name == "press_button":
                action = {
                    "action_type": "press_key",
                    "keys": [function_args["button"].lower()]
                }
            elif function_name == "wait":
                action = {
                    "action_type": "wait",
                    "frames": function_args["frames"]
                }
            else:
                logger.warning(f"Unknown function: {function_name}")
                return content, None, None
            
            # Return content (reasoning), action, and raw tool call
            return content, action, {
                "id": tool_call.id,
                "function": function_name,
                "arguments": function_args
            }
            
        except Exception as e:
            logger.error(f"Error parsing tool response: {e}")
            return None, None, None

    def extract_cot_components(self, reasoning: str) -> Dict[str, str]:
        """Extract COT_effort, COT_length, and COT from the reasoning text."""
        components = {
            "effort": "MEDIUM",
            "length": "150",
            "reasoning": reasoning
        }
        
        try:
            lines = reasoning.split('\n')
            cot_started = False
            cot_lines = []
            
            for line in lines:
                line = line.strip()
                if line.startswith("**COT_effort**:") or line.startswith("COT_effort:"):
                    effort = line.split(":", 1)[1].strip().strip("*[]")
                    components["effort"] = effort.upper()
                elif line.startswith("**COT_length**:") or line.startswith("COT_length:"):
                    length = line.split(":", 1)[1].strip().strip("*[]")
                    components["length"] = length.split()[0]  # Get just the number
                elif line.startswith("**COT**:") or line.startswith("COT:"):
                    cot_started = True
                    cot_text = line.split(":", 1)[1].strip().strip("*[]")
                    if cot_text:
                        cot_lines.append(cot_text)
                elif cot_started and line:
                    cot_lines.append(line)
            
            if cot_lines:
                components["reasoning"] = " ".join(cot_lines)
                
        except Exception as e:
            logger.warning(f"Failed to parse COT components: {e}")
        
        return components

    def update_thoughts_file(self, cot_components: Dict[str, str], action_desc: str):
        """Update the thoughts file for streaming display."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(self.thoughts_log_file, "a", encoding="utf-8") as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"Step {self.step_count} - {timestamp}\n")
                f.write(f"{'='*60}\n\n")
                
                f.write(f"THINKING EFFORT: {cot_components['effort']}\n")
                f.write(f"REASONING LENGTH: {cot_components['length']} words\n\n")
                
                f.write("CHAIN OF THOUGHT:\n")
                f.write(cot_components['reasoning'])
                f.write("\n\n")
                
                f.write(f"ACTION TAKEN: {action_desc}\n")
                f.write(f"{'='*60}\n")
                
        except Exception as e:
            logger.error(f"Error updating thoughts file: {e}")

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
            response = requests.post(
                f"{self.server_url}/action", json=action, timeout=30
            )
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to send action: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error sending action: {e}")
            return None

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
            
            # Upscale the image for better vision performance
            upscaled_screenshot = self.upscale_image(screenshot_b64)
            
            # Build conversation with history
            messages = self.build_conversation_messages(upscaled_screenshot)
            
            # Get LLM response with tool calling
            response = None
            reasoning = None
            action = None
            tool_call = None
            
            for attempt in range(self.max_retries):
                try:
                    # Call LiteLLM with tools
                    response = litellm.completion(
                        model=self.llm.model_name,
                        messages=messages,
                        tools=TOOLS,
                        tool_choice="required",  # Force tool usage
                        temperature=self.llm.temperature,
                        max_tokens=self.llm.max_tokens,
                    )
                    
                    # Parse response
                    reasoning, action, tool_call = self.parse_tool_response(response)
                    
                    if action:
                        break
                    else:
                        logger.warning("No valid action parsed, retrying...")
                        
                except Exception as e:
                    logger.warning(f"LLM attempt {attempt + 1} failed: {e}")
                    if attempt == self.max_retries - 1:
                        logger.error("All LLM attempts failed")
                        return False
                    time.sleep(1)
            
            if not action:
                logger.error("Could not get valid action from LLM")
                return False
            
            # Extract COT components from reasoning
            cot_components = self.extract_cot_components(reasoning or "")
            
            # Send action to server
            result = self.send_action(action)
            if not result:
                logger.error("Failed to send action")
                return False
            
            # Create action description
            action_desc = f"{action['action_type']}"
            if action["action_type"] == "press_key":
                action_desc += f" {action['keys'][0]}"
            elif action["action_type"] == "wait":
                action_desc += f" {action['frames']} frames"
            
            # Update thoughts file
            self.update_thoughts_file(cot_components, action_desc)
            
            # Add to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": reasoning,
                "tool_calls": [tool_call] if tool_call else []
            })
            
            # Log the action
            logger.info(f"Step {self.step_count}: {action_desc} (Effort: {cot_components['effort']})")
            
            return True
            
        except Exception as e:
            logger.error(f"Error in run_step: {e}")
            return False

    def run(self, max_steps: int = 1000):
        """Run the vision agent for a specified number of steps."""
        logger.info(f"Starting advanced vision agent for {max_steps} steps")
        logger.info(f"Using LiteLLM tool calling with model: {self.llm.model_name}")
        
        # Try to resume latest session
        latest_session = self.session_manager.get_latest_session()
        if latest_session:
            logger.info(f"Resuming latest session: {latest_session}")
            if self.session_manager.load_session(latest_session):
                logger.info(f"Successfully loaded session data for: {latest_session}")
            else:
                logger.warning(f"Failed to load session data for: {latest_session}")
            init_data = {
                "headless": self.headless,
                "sound": self.sound,
                "streaming": True,
                "session_id": latest_session,
            }
        else:
            # New session
            init_data = {
                "headless": self.headless,
                "sound": self.sound,
                "streaming": True,
            }
        
        # Initialize server
        try:
            response = requests.post(
                f"{self.server_url}/initialize", json=init_data, timeout=30
            )
            if response.status_code != 200:
                logger.error(f"Failed to initialize server: {response.status_code}")
                return
        except Exception as e:
            logger.error(f"Error initializing server: {e}")
            return
        
        # Main game loop
        consecutive_failures = 0
        for step in range(max_steps):
            success = self.run_step()
            
            if success:
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                logger.warning(f"Step failed ({consecutive_failures} consecutive failures)")
                
                if consecutive_failures >= 5:
                    logger.error("Too many consecutive failures, stopping")
                    break
            
            # Small delay to prevent overwhelming the server
            time.sleep(0.3)
        
        logger.info("Vision agent run completed")
        logger.info(f"Total steps executed: {self.step_count}")


def main():
    parser = argparse.ArgumentParser(
        description="Pokemon Red Vision Agent with LiteLLM Tool Calling"
    )
    parser.add_argument(
        "--server-url", default="http://localhost:8080", help="Server URL"
    )
    parser.add_argument("--provider", default="ollama", help="LLM provider")
    parser.add_argument(
        "--model", default="PetrosStav/gemma3-tools:4b", help="Model name"
    )
    parser.add_argument("--temperature", type=float, default=0.7, help="Temperature")
    parser.add_argument("--max-tokens", type=int, default=2000, help="Max tokens")
    parser.add_argument(
        "--max-steps", type=int, default=1000, help="Maximum steps to run"
    )
    parser.add_argument("--max-retries", type=int, default=3, help="Max LLM retries")
    parser.add_argument(
        "--headless", action="store_true", default=False, help="Run without game window"
    )
    parser.add_argument(
        "--sound", action="store_true", default=False, help="Enable game sound"
    )
    parser.add_argument(
        "--upscale-factor",
        type=float,
        default=2.0,
        help="Image upscaling factor for better vision",
    )
    parser.add_argument(
        "--history-limit",
        type=int,
        default=10,
        help="Number of conversation turns to keep in context",
    )
    
    args = parser.parse_args()
    
    agent = VisionAgent(
        server_url=args.server_url,
        provider=args.provider,
        model_name=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        max_retries=args.max_retries,
        headless=args.headless,
        sound=args.sound,
        upscale_factor=args.upscale_factor,
        conversation_history_limit=args.history_limit,
    )
    
    agent.run(max_steps=args.max_steps)


if __name__ == "__main__":
    main()