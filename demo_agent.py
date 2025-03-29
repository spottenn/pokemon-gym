import argparse
import logging
import random
import time
from typing import Dict, List, Any, Optional

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
                 max_history: int = 20):
        """
        Initialize the AI Agent
        
        Args:
            server_url: URL of the evaluation server
            model_name: Claude model to use
            temperature: Temperature parameter for Claude
            max_tokens: Maximum tokens for Claude to generate
            max_history: Maximum number of messages to keep in history
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
        
        # Chat history
        self.message_history = []
        self.current_state = None
        self.running = True
        self.step_count = 0
    
    def initialize(self, headless: bool = True, sound: bool = False) -> Dict[str, Any]:
        """
        Initialize the game environment
        
        Args:
            headless: Whether to run without a GUI
            sound: Whether to enable sound
            
        Returns:
            Initial game state
        """
        try:
            logger.info("Initializing environment...")
            
            response = self.session.post(
                f"{self.server_url}/initialize",
                headers={"Content-Type": "application/json"},
                json={
                    "headless": headless,
                    "sound": sound
                }
            )
            
            response.raise_for_status()
            self.current_state = response.json()
            
            # Set initialization flag
            self.initialized = True
            
            # Create initial conversation history
            self.message_history = [{"role": "user", "content": "You may now begin playing Pokemon Red."}]
            
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
            {"type": "text", "text": f"Valid moves: {state['valid_moves']}"},
            {"type": "text", "text": f"Money: {state['money']}"},
            {"type": "text", "text": f"Badges: {state['badges']}"},
        ]
        
        # Add dialog information if available
        if state['dialog']:
            content.append({"type": "text", "text": f"Dialog: {state['dialog']}"})
        
        # Add party pokemon information
        if state['party_pokemon']:
            pokemon_info = "\nParty Pokemon:\n"
            for i, pokemon in enumerate(state['party_pokemon']):
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
        
        # Get Claude's response
        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=self.max_tokens,
            system=SYSTEM_PROMPT,
            messages=self.message_history,
            tools=AVAILABLE_TOOLS,
            temperature=self.temperature,
        )
        
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
        
        # Execute tool call and get result
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
        
        # Get Claude's summary
        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=self.max_tokens,
            system=SYSTEM_PROMPT,
            messages=summary_messages,
            temperature=self.temperature
        )
        
        # Extract summary text
        summary_text = " ".join([block.text for block in response.content if block.type == "text"])
        
        logger.info(f"Generated summary:\n{summary_text}")
        
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
                current_state = self.decide_action(current_state)
                
                # Display current state information
                location = current_state['location']
                coords = current_state['coordinates']
                party_size = len(current_state['party_pokemon'])
                
                logger.info(f"Location: {location}, Coordinates: {coords}, Party size: {party_size}")
        
        except KeyboardInterrupt:
            logger.info("User interrupted, stopping run")
        except Exception as e:
            logger.error(f"Run error: {e}")
        finally:
            logger.info(f"Run ended, executed {self.step_count} steps")
    
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
    parser.add_argument("--steps", type=int, default=100, help="Number of steps to run")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    parser.add_argument("--sound", action="store_true", help="Enable sound")
    parser.add_argument("--model", type=str, default="claude-3-5-sonnet-20240620", help="Claude model to use")
    parser.add_argument("--temperature", type=float, default=1.0, help="Temperature parameter for Claude")
    parser.add_argument("--max-tokens", type=int, default=4000, help="Maximum tokens for Claude to generate")
    parser.add_argument("--save-screenshots", action="store_true", help="Save game screenshots")
    
    args = parser.parse_args()
    
    # Create AI Agent
    agent = AIServerAgent(
        server_url=args.server,
        model_name=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens
    )
    
    try:
        # Initialize environment
        initial_state = agent.initialize(headless=args.headless, sound=args.sound)
        
        # Save initial screenshot
        if args.save_screenshots:
            save_screenshot(initial_state['screenshot_base64'], "screenshot_initial.png")
        
        # Run AI Agent
        logger.info(f"Starting AI Agent, max steps: {args.steps}")
        agent.run(max_steps=args.steps)
        
        # Save final screenshot
        if args.save_screenshots and agent.current_state:
            save_screenshot(agent.current_state['screenshot_base64'], "screenshot_final.png")
        
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