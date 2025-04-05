import argparse
import logging
import random
import time
from typing import Dict, List, Any, Optional
import json
import datetime

import requests
from PIL import Image
import base64
import io
import copy
import os
from anthropic import Anthropic

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are playing Pokemon Red. You can see the game screen and control the game by executing emulator commands.

Your goal is to play through Pokemon Red and eventually defeat the Elite Four. Make decisions based on what you see on the screen.

You have two tools available to control the game:
1. press_key - Press a single button (A, B, Start, Select, Up, Down, Left, Right)
2. wait - Wait for a specified number of frames

The A button is typically used to confirm actions or attack, B serves as a cancel or secondary action button, Start is used to pause the game or access menus, Select allows you to switch options or settings, and the directional buttons (Up, Down, Left, Right) control movement.

IMPORTANT: You can only take ONE action at a time. Choose the most appropriate single button press or wait action based on the current game state.

Before each action, explain your reasoning briefly, then use the appropriate tool to execute your chosen command.

The conversation history may occasionally be summarized to save context space. If you see a message labeled "CONVERSATION HISTORY SUMMARY", this contains the key information about your progress so far. Use this information to maintain continuity in your gameplay."""

# Available tools
AVAILABLE_TOOLS = [
    {
        "name": "press_key",
        "description": "Press a single button on the Game Boy.",
        "input_schema": {
            "type": "object",
            "properties": {
                "button": {
                    "type": "string",
                    "enum": ["a", "b", "start", "select", "up", "down", "left", "right"],
                    "description": "The button to press. Valid buttons: 'a', 'b', 'start', 'select', 'up', 'down', 'left', 'right'"
                }
            },
            "required": ["button"],
        },
    },
    {
        "name": "wait",
        "description": "Wait for a specified number of frames.",
        "input_schema": {
            "type": "object",
            "properties": {
                "frames": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Number of frames to wait."
                }
            },
            "required": ["frames"],
        },
    }
]


class AIServerAgent:
    """AI Agent that controls Pokemon Red through the evaluator server API"""
    
    def __init__(self, 
                 server_url: str = "http://localhost:8080", 
                 model_name: str = "claude-3-7-sonnet-20250219", 
                 temperature: float = 1.0, 
                 max_tokens: int = 4000,
                 max_history: int = 30,
                 log_file: str = "agent_log.jsonl",
                 max_retries: int = 5,
                 retry_delay: float = 1.0):
        """
        Initialize the AI Agent
        
        Args:
            server_url: URL of the evaluation server
            model_name: Claude model to use
            temperature: Temperature parameter for Claude
            max_tokens: Maximum tokens for Claude to generate
            max_history: Maximum number of messages to keep in history
            log_file: File to save generated content
            max_retries: Maximum number of retries for API calls
            retry_delay: Base delay between retries in seconds
        """
        # Server connection
        self.server_url = server_url
        self.session = requests.Session()
        self.initialized = False
        
        # Claude API
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_history = max_history
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Chat history
        self.message_history = []
        self.current_state = None
        self.running = True
        self.step_count = 0
        
        # Logging generated content
        self.log_file = log_file
        # Create log file with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = f"{os.path.splitext(self.log_file)[0]}_{timestamp}.jsonl"
        # Create directory if it doesn't exist
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        logger.info(f"Will log all generated content to: {self.log_file}")
    
    def log_step_data(self, step_num: int, user_message: Any, assistant_response, action_taken: Dict[str, Any]):
        """
        Log data from a step to the log file
        
        Args:
            step_num: Step number
            user_message: The message sent to Claude
            assistant_response: Claude's response object
            action_taken: Details of the action that was taken
        """
        # Extract text blocks and tool use from Claude's response
        text_content = []
        tool_uses = []
        
        # Handle different response formats based on API version
        if hasattr(assistant_response, 'content'):
            for block in assistant_response.content:
                if block.type == "text":
                    text_content.append(block.text)
                elif block.type == "tool_use":
                    tool_uses.append({
                        "name": block.name,
                        "input": block.input
                    })
        
        # Simplify user message if it's complex
        simplified_user_message = ""
        if isinstance(user_message, list):
            for item in user_message:
                if isinstance(item, dict) and item.get("type") == "text":
                    simplified_user_message += item.get("text", "") + "\n"
        else:
            simplified_user_message = str(user_message)
        
        # Create log entry
        log_entry = {
            "step": step_num,
            "timestamp": datetime.datetime.now().isoformat(),
            "user_message": simplified_user_message,
            "assistant_response": {
                "text": text_content,
                "tool_uses": tool_uses
            },
            "action_taken": action_taken
        }
        
        # Append to log file
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    def initialize(self, headless: bool = True, sound: bool = False,
                  load_state_file: str = None, load_autosave: bool = False,
                  session_id: str = None) -> Dict[str, Any]:
        """
        Initialize the game environment
        
        Args:
            headless: Whether to run without a GUI
            sound: Whether to enable sound
            load_state_file: Optional path to a saved state file to load
            load_autosave: Whether to load the latest autosave
            session_id: Optional session ID to continue an existing session
            
        Returns:
            Initial game state
        """
        try:
            logger.info("Initializing environment...")
            
            # Prepare initialization parameters
            init_params = {
                "headless": headless,
                "sound": sound,
                "load_autosave": load_autosave
            }
            
            # Add load_state_file if provided
            if load_state_file:
                init_params["load_state_file"] = load_state_file
                logger.info(f"Will try to load state from {load_state_file}")
            
            # Add session_id if provided
            if session_id:
                init_params["session_id"] = session_id
                logger.info(f"Will continue existing session: {session_id}")
            
            response = self.session.post(
                f"{self.server_url}/initialize",
                headers={"Content-Type": "application/json"},
                json=init_params
            )
            
            response.raise_for_status()
            self.current_state = response.json()
            
            # Set initialization flag
            self.initialized = True
            
            # Create initial conversation history
            self.message_history = [{"role": "user", "content": "You may now begin playing Pokemon Red."}]
            
            # Log initial state
            with open(self.log_file, 'a', encoding='utf-8') as f:
                initial_entry = {
                    "step": "initial",
                    "timestamp": datetime.datetime.now().isoformat(),
                    "game_state": {
                        "location": self.current_state.get('location', ''),
                        "coordinates": self.current_state.get('coordinates', []),
                        "money": self.current_state.get('money', 0),
                        "badges": self.current_state.get('badges', []),
                        "score": self.current_state.get('score', 0.0),  # Add score to log
                    }
                }
                f.write(json.dumps(initial_entry, ensure_ascii=False) + '\n')
            
            logger.info(f"Initialization successful, location: {self.current_state['location']}")
            
            return self.current_state
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Initialization error: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Server response: {e.response.text}")
            raise
    
    def take_action(self, action_type: str, **kwargs) -> Dict[str, Any]:
        """
        Send an action request to the server
        
        Args:
            action_type: Action type ("press_key" or "wait")
            **kwargs: Action parameters
                press_key: keys
                wait: frames
        
        Returns:
            Game state after executing the action
        """
        if not self.initialized:
            raise RuntimeError("Environment not initialized, please call initialize() first")
        
        try:
            # Prepare request data
            request_data = {"action_type": action_type, **kwargs}
            
            # Send request
            response = self.session.post(
                f"{self.server_url}/action",
                headers={"Content-Type": "application/json"},
                json=request_data
            )
            
            response.raise_for_status()
            self.current_state = response.json()
            self.step_count += 1
            
            return self.current_state
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Action execution error: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Server response: {e.response.text}")
            raise
    
    def _call_api_with_retry(self, api_func, *args, **kwargs):
        """
        Call an API function with retry mechanism
        
        Args:
            api_func: Function to call
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            API response
        """
        retries = 0
        last_exception = None
        
        while retries < self.max_retries:
            try:
                return api_func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                retries += 1
                wait_time = self.retry_delay * (2 ** (retries - 1))  # Exponential backoff
                logger.warning(f"API call failed (attempt {retries}/{self.max_retries}): {e}")
                logger.info(f"Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
        
        logger.error(f"API call failed after {self.max_retries} attempts: {last_exception}")
        raise last_exception
    
    def decide_action(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decide on the next action based on current state
        
        Args:
            state: Current game state
            
        Returns:
            Game state after executing the action
        """
        # Prepare state information for Claude
        screenshot_b64 = state['screenshot_base64']
        
        # Create message content with the game state information
        content = [
            {"type": "text", "text": "Here is the current state of the game:"},
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": screenshot_b64,
                },
            },
            {"type": "text", "text": f"\nGame state information:"},
            {"type": "text", "text": f"Location: {state['location']}"},
            {"type": "text", "text": f"Coordinates: {state['coordinates']}"},
            {"type": "text", "text": f"Score: {state.get('score', 0.0)}"},
            {"type": "text", "text": f"Dialog: {state['dialog']}"},
            {"type": "text", "text": f"Pokemons: {state['pokemons']}"},
            {"type": "text", "text": f"Inventory: {state['inventory']}"},
            {"type": "text", "text": f"Valid moves: {state['valid_moves']}"},
            {"type": "text", "text": f"Money: {state['money']}"},
            {"type": "text", "text": f"Badges: {state['badges']}"},
        ]
        
        # Add dialog information if available
        if state['dialog']:
            content.append({"type": "text", "text": f"Dialog: {state['dialog']}"})
        
        # Add party pokemon information
        if state['pokemons']:
            pokemon_info = "\nParty Pokemon:\n"
            for i, pokemon in enumerate(state['pokemons']):
                pokemon_info += f"{i+1}. {pokemon['nickname']} ({pokemon['species']}) Lv.{pokemon['level']} " \
                               f"HP: {pokemon['hp']['current']}/{pokemon['hp']['max']}\n"
            content.append({"type": "text", "text": pokemon_info})
        
        # Add inventory information
        if state['inventory']:
            inventory_info = "\nInventory:\n"
            for item in state['inventory']:
                inventory_info += f"- {item['item']}: {item['quantity']}\n"
            content.append({"type": "text", "text": inventory_info})
        
        # Add collision map and valid moves (if available)
        collision_map = state.get('collision_map')
        
        if collision_map:
            content.append({"type": "text", "text": f"\nCollision map:\n{collision_map}"})
        
        # Add message to history
        self.message_history.append({"role": "user", "content": content})
        
        # Get Claude's response with retry
        try:
            response = self._call_api_with_retry(
                self.client.messages.create,
                model=self.model_name,
                max_tokens=self.max_tokens,
                system=SYSTEM_PROMPT,
                messages=self.message_history,
                tools=AVAILABLE_TOOLS,
                temperature=self.temperature,
            )
        except Exception as e:
            logger.error(f"Failed to get response from Claude after retries: {e}")
            # Default to a simple action if API calls fail completely
            logger.warning("Falling back to default action (press A)")
            
            # Create a minimal response for logging
            response = type('obj', (object,), {
                'content': [
                    type('obj', (object,), {'type': 'text', 'text': 'API call failed, using default action'})
                ]
            })
            
            # Skip normal processing and return a default action
            next_state = self.take_action("press_key", keys=["a"])
            
            # Add a failure note to history
            self.message_history.append({
                "role": "assistant", 
                "content": [{"type": "text", "text": "API call failed, used default action (press A)"}]
            })
            
            return next_state
        
        # Extract tool calls
        tool_calls = [block for block in response.content if block.type == "tool_use"]
        
        # Collect Claude's response (but don't add to history yet, wait for tool_result)
        assistant_content = []
        for block in response.content:
            if block.type == "text":
                logger.info(f"[Claude] {block.text}")
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                logger.info(f"[Claude] Using tool: {block.name}")
                assistant_content.append({"type": "tool_use", **dict(block)})
        
        # Prepare action data
        action_data = {}
        if tool_calls:
            tool_call = tool_calls[0]
            tool_name = tool_call.name
            tool_input = tool_call.input
            
            if tool_name == "press_key":
                button = tool_input.get("button")
                action_data = {"action_type": "press_key", "button": button}
            elif tool_name == "wait":
                frames = tool_input.get("frames")
                action_data = {"action_type": "wait", "frames": frames}
        else:
            # Default action if no tool call
            action_data = {"action_type": "press_key", "button": "a"}
        
        # Log the Claude response and action before executing
        self.log_step_data(
            step_num=self.step_count,
            user_message=content,
            assistant_response=response,
            action_taken=action_data
        )
        
        # Execute the action
        next_state = self._process_response(response)
        
        # Add Claude's response (with tool_use) to history
        self.message_history.append({"role": "assistant", "content": assistant_content})
        
        # Create tool_result response
        tool_result_content = []
        
        # Add a tool result for each tool call
        for tool_call in tool_calls:
            tool_id = tool_call.id
            tool_name = tool_call.name
            
            # Create appropriate result message based on tool type
            if tool_name == "press_key":
                button = tool_call.input.get("button")
                result_message = f"Button '{button}' pressed successfully. New location: {next_state['location']}, Coordinates: {next_state['coordinates']}"
            elif tool_name == "wait":
                frames = tool_call.input.get("frames")
                result_message = f"Waited for {frames} frames. New location: {next_state['location']}, Coordinates: {next_state['coordinates']}"
            else:
                result_message = f"Action executed. New location: {next_state['location']}, Coordinates: {next_state['coordinates']}"
            
            tool_result_content.append({
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": result_message
            })
        
        # Add screenshot
        tool_result_content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": next_state['screenshot_base64'],
            },
        })
        
        # Add tool result response to history
        self.message_history.append({"role": "user", "content": tool_result_content})
        
        # Check if history needs summarization
        if len(self.message_history) > self.max_history:
            self._summarize_history()
        
        return next_state
    
    def _process_response(self, response) -> Dict[str, Any]:
        """
        Process Claude's response and execute action
        
        Args:
            response: Claude API response
            
        Returns:
            Game state after executing the action
        """
        # Extract tool calls
        tool_calls = [block for block in response.content if block.type == "tool_use"]
        
        if not tool_calls:
            # No tool calls, default to pressing A
            logger.warning("No tool calls, defaulting to pressing A")
            next_state = self.take_action("press_key", keys=["a"])
            return next_state
        
        # Process the first tool call
        tool_call = tool_calls[0]
        tool_name = tool_call.name
        tool_input = tool_call.input
        
        if tool_name == "press_key":
            button = tool_input["button"]
            logger.info(f"Pressing button: {button}")
            
            return self.take_action("press_key", keys=[button])
        elif tool_name == "wait":
            frames = tool_input["frames"]
            logger.info(f"Waiting: {frames} frames")
            
            return self.take_action("wait", frames=frames)
        else:
            logger.error(f"Unknown tool: {tool_name}")
            return self.take_action("press_key", keys=["a"])  # Default to A
    
    def _summarize_history(self):
        """Summarize conversation history to save context space"""
        logger.info("Summarizing conversation history...")
        
        # Create summary request
        summary_messages = copy.deepcopy(self.message_history)
        summary_messages.append({
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Please create a detailed summary of our conversation history so far. This summary will replace the full conversation history to manage the context window."
                }
            ]
        })
        
        # Get Claude's summary with retry
        try:
            response = self._call_api_with_retry(
                self.client.messages.create,
                model=self.model_name,
                max_tokens=self.max_tokens,
                system=SYSTEM_PROMPT,
                messages=summary_messages,
                temperature=self.temperature
            )
            
            # Extract summary text
            summary_text = " ".join([block.text for block in response.content if block.type == "text"])
            
            logger.info(f"Generated summary:\n{summary_text}")
            
            # Log the summary
            with open(self.log_file, 'a', encoding='utf-8') as f:
                summary_entry = {
                    "step": f"summary_{self.step_count}",
                    "timestamp": datetime.datetime.now().isoformat(),
                    "summary": summary_text
                }
                f.write(json.dumps(summary_entry, ensure_ascii=False) + '\n')
            
            # Replace history with summary
            self.message_history = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"CONVERSATION HISTORY SUMMARY: {summary_text}"
                        },
                        {
                            "type": "text",
                            "text": "You may now continue playing Pokemon Red. Make your next decision based on the current game state."
                        }
                    ]
                }
            ]
            
            logger.info("Conversation history successfully summarized")
        except Exception as e:
            logger.error(f"Failed to summarize history: {e}")
            # Fallback to truncating history to avoid context issues
            logger.warning("Truncating history as fallback")
            # Keep a few most recent messages
            if len(self.message_history) > 6:
                self.message_history = self.message_history[-6:]
    
    def run(self, max_steps: int = 100) -> None:
        """
        Run the AI Agent
        
        Args:
            max_steps: Maximum number of steps to run
        """
        if not self.initialized:
            raise RuntimeError("Environment not initialized, please call initialize() first")
        
        logger.info(f"Starting AI Agent, max steps: {max_steps}")
        
        try:
            # Process initial state
            logger.info("Processing initial state...")
            current_state = self.current_state
            
            while self.running and self.step_count < max_steps:
                # Decide and execute action
                logger.info(f"Step {self.step_count+1}/{max_steps}")
                
                try:
                    current_state = self.decide_action(current_state)
                    
                    # Display current state information
                    location = current_state['location']
                    coords = current_state['coordinates']
                    party_size = len(current_state['pokemons'])
                    score = current_state.get('score', 0.0)
                    
                    logger.info(f"Location: {location}, Coordinates: {coords}, Party size: {party_size}, Score: {score:.1f}")
                    
                    # Small delay between steps to avoid overwhelming API
                    time.sleep(0.5)
                except Exception as e:
                    logger.error(f"Error in step {self.step_count+1}: {e}")
                    logger.warning("Attempting to continue with next step after error")
                    # Add a longer delay after error
                    time.sleep(2)
        
        except KeyboardInterrupt:
            logger.info("User interrupted, stopping run")
        except Exception as e:
            logger.error(f"Run error: {e}")
        finally:
            logger.info(f"Run ended, executed {self.step_count} steps")
            
            # Log final state
            with open(self.log_file, 'a', encoding='utf-8') as f:
                final_entry = {
                    "step": "final",
                    "timestamp": datetime.datetime.now().isoformat(),
                    "total_steps": self.step_count,
                    "final_location": self.current_state.get('location', '') if self.current_state else None,
                    "final_badges": self.current_state.get('badges', []) if self.current_state else None
                }
                f.write(json.dumps(final_entry, ensure_ascii=False) + '\n')
    
    def stop(self) -> Dict[str, Any]:
        """Stop the environment"""
        if not self.initialized:
            return {"status": "not_initialized"}
        
        try:
            response = self.session.post(f"{self.server_url}/stop")
            response.raise_for_status()
            self.initialized = False
            self.running = False
            logger.info("Environment stopped")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Environment stop error: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Server response: {e.response.text}")
            raise


def save_screenshot(screenshot_base64: str, filename: str) -> None:
    """
    Save a screenshot from base64 encoded image data
    
    Args:
        screenshot_base64: base64 encoded image data
        filename: filename to save
    """
    image_data = base64.b64decode(screenshot_base64)
    image = Image.open(io.BytesIO(image_data))
    
    # Upscale the image for better visibility
    width, height = image.size
    image = image.resize((width*3, height*3), Image.NEAREST)
    
    image.save(filename)
    logger.info(f"Screenshot saved to {filename}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Pokemon AI Agent")
    parser.add_argument("--server", type=str, default="http://localhost:8080", help="Evaluation server URL")
    parser.add_argument("--steps", type=int, default=1000000, help="Number of steps to run")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    parser.add_argument("--sound", action="store_true", help="Enable sound")
    parser.add_argument("--model", type=str, default="claude-3-5-sonnet-20241022", help="Claude model to use")
    parser.add_argument("--temperature", type=float, default=1.0, help="Temperature parameter for Claude")
    parser.add_argument("--max-tokens", type=int, default=4000, help="Maximum tokens for Claude to generate")
    parser.add_argument("--log-file", type=str, default="agent_log.jsonl", help="File to save agent logs")
    parser.add_argument("--max-retries", type=int, default=5, help="Maximum retries for API calls")
    parser.add_argument("--retry-delay", type=float, default=1.0, help="Base delay between retries in seconds")
    parser.add_argument("--load-state", type=str, help="Path to a saved state file to load")
    parser.add_argument("--load-autosave", action="store_true", help="Load the latest autosave")
    parser.add_argument("--session", type=str, help="Session ID to continue (e.g., session_20250404_180209)")
    
    args = parser.parse_args()
    
    # Create AI Agent
    agent = AIServerAgent(
        server_url=args.server,
        model_name=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        log_file=args.log_file,
        max_retries=args.max_retries,
        retry_delay=args.retry_delay
    )
    
    try:
        # Initialize environment
        initial_state = agent.initialize(
            headless=args.headless, 
            sound=args.sound,
            load_state_file=args.load_state,
            load_autosave=args.load_autosave,
            session_id=args.session
        )
        
        # Run AI Agent
        logger.info(f"Starting AI Agent, max steps: {args.steps}")
        agent.run(max_steps=args.steps)
        
    except KeyboardInterrupt:
        logger.info("User interrupted")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        # Ensure environment is stopped
        if agent.initialized:
            agent.stop()


if __name__ == "__main__":
    main() 