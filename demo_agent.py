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
from openai import OpenAI

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
                 provider: str = "claude", 
                 model_name: str = None, 
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
            provider: LLM provider ("claude", "openrouter", or "gemini")
            model_name: Model name for the selected provider (defaults based on provider)
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
        
        # Provider and model config
        self.provider = provider.lower()
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_history = max_history
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Setup provider-specific clients and models
        if self.provider == "claude":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")
            self.client = Anthropic(api_key=api_key)
            self.model_name = model_name or "claude-3-5-sonnet-20240620"
            logger.info(f"Using Claude provider with model: {self.model_name}")
        elif self.provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            self.client = OpenAI(api_key=api_key)
            self.model_name = model_name or "gpt-4o"
            logger.info(f"Using OpenAI provider with model: {self.model_name}")
        elif self.provider == "openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY environment variable not set")
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1"
            )
            self.model_name = model_name or "meta-llama/llama-4-maverick"
            logger.info(f"Using OpenRouter provider with model: {self.model_name}")
        elif self.provider == "gemini":
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY environment variable not set")
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai"
            )
            self.model_name = model_name or "gemini-2.5-pro-preview-03-25"
            logger.info(f"Using Gemini provider with model: {self.model_name}")
        else:
            raise ValueError(f"Unsupported provider: {self.provider}. Choose 'claude', 'openai', 'openrouter', or 'gemini'")
        
        # Chat history
        self.message_history = []
        self.current_state = None
        self.running = True
        self.step_count = 0
        
        # Logging generated content
        self.log_file = log_file
        # Create log file with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = f"{os.path.splitext(self.log_file)[0]}_{self.provider}_{timestamp}.jsonl"
        # Create directory if it doesn't exist
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        logger.info(f"Will log all generated content to: {self.log_file}")
        
        # Added for OpenAI
        self.pending_tool_responses = []
        self.user_message_with_results = None
    
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
            
            # Initialize tools
            self._initialize_tools()
            
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
    
    def _prepare_tools(self):
        """Prepare tools format based on provider"""
        if self.provider == "claude":
            # Claude uses original tools format
            return AVAILABLE_TOOLS
        else:
            # OpenRouter and Gemini use OpenAI format
            return [
                {
                    "type": "function",
                    "function": {
                        "name": "press_key",
                        "description": "Press a single button on the Game Boy.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "button": {
                                    "type": "string",
                                    "enum": ["a", "b", "start", "select", "up", "down", "left", "right"],
                                    "description": "The button to press. Valid buttons: 'a', 'b', 'start', 'select', 'up', 'down', 'left', 'right'"
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
                        "description": "Wait for a specified number of frames.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "frames": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "description": "Number of frames to wait."
                                }
                            },
                            "required": ["frames"]
                        }
                    }
                }
            ]
    
    def _call_api_with_retry(self, api_func=None, *args, **kwargs):
        """
        Call an API function with retry mechanism
        
        Args:
            api_func: Function to call (only used for Claude)
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            API response
        """
        retries = 0
        last_exception = None
        
        while retries < self.max_retries:
            try:
                if self.provider == "claude":
                    # For Claude, use original API call style
                    if api_func:
                        return api_func(*args, **kwargs)
                    else:
                        # Direct call using message history and tools
                        messages = kwargs.get('messages', self.message_history)
                        return self.client.messages.create(
                            model=self.model_name,
                            max_tokens=self.max_tokens,
                            system=SYSTEM_PROMPT,
                            messages=messages,
                            tools=AVAILABLE_TOOLS,
                            temperature=self.temperature,
                        )
                else:
                    # For OpenAI, OpenRouter and Gemini, use OpenAI compatible API
                    # Extract important params from kwargs
                    messages = kwargs.get('messages', self.message_history)
                    
                    # Clean up message history to avoid duplicate tool messages
                    # This ensures we only keep the most relevant tool responses
                    cleaned_messages = self._clean_message_history(messages)
                    
                    # Convert to OpenAI format if needed
                    openai_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                    
                    for msg in cleaned_messages:
                        if msg["role"] == "user" and isinstance(msg["content"], list):
                            # Handle multimodal content (text + image)
                            content_list = []
                            for item in msg["content"]:
                                if isinstance(item, dict):
                                    if item.get("type") == "text":
                                        content_list.append({"type": "text", "text": item["text"]})
                                    elif item.get("type") == "image":
                                        # Convert Claude image format to OpenAI format
                                        src = item["source"]
                                        if src.get("type") == "base64":
                                            content_list.append({
                                                "type": "image_url",
                                                "image_url": {
                                                    "url": f"data:{src.get('media_type', 'image/png')};base64,{src['data']}"
                                                }
                                            })
                            openai_messages.append({"role": "user", "content": content_list})
                        elif msg["role"] == "assistant" and isinstance(msg["content"], list):
                            # Handle assistant's response (might include tool uses in Claude format)
                            # For simplicity, extract text only for OpenAI format
                            text_content = ""
                            for item in msg["content"]:
                                if isinstance(item, dict) and item.get("type") == "text":
                                    text_content += item.get("text", "") + "\n"
                            if text_content:
                                openai_messages.append({"role": "assistant", "content": text_content})
                        elif msg["role"] == "assistant" and "tool_calls" in msg:
                            # Handle assistant message with tool_calls
                            assistant_msg = {"role": "assistant", "content": msg.get("content", "")}
                            # Crucial: preserve tool_calls for proper chain
                            if "tool_calls" in msg:
                                assistant_msg["tool_calls"] = msg["tool_calls"]
                            openai_messages.append(assistant_msg)
                        elif msg["role"] == "tool":
                            # Ensure the tool response message contains the necessary fields
                            tool_msg = {
                                "role": "tool",
                                "tool_call_id": msg.get("tool_call_id"),
                                "content": msg.get("content", "")
                            }
                            # For Gemini, the name field is required
                            if self.provider == "gemini":
                                if "name" in msg:
                                    tool_msg["name"] = msg["name"]
                                    logger.info(f"Using provided tool name: {msg['name']}")
                                else:
                                    # If no name field is provided, use a default value
                                    tool_msg["name"] = "press_key" if "button" in msg.get("content", "") else "wait"
                                    logger.info(f"Using default tool name: {tool_msg['name']}")
                            elif "name" in msg:
                                tool_msg["name"] = msg["name"]
                            
                            logger.info(f"Tool message for {self.provider}: {tool_msg}")
                            openai_messages.append(tool_msg)
                        else:
                            # Simple text messages or other roles
                            openai_messages.append(msg)
                    
                    # For Gemini, log the complete message history
                    if self.provider == "gemini" and logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"OpenAI messages for Gemini: {json.dumps(openai_messages, indent=2)}")
                    
                    # For OpenAI, log message history for debugging
                    if (self.provider == "openai" or self.provider == "openrouter") and logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"Messages for {self.provider}: {json.dumps(openai_messages, indent=2)}")
                    
                    # Convert Claude tools to OpenAI function format
                    openai_tools = []
                    for tool in AVAILABLE_TOOLS:
                        openai_tools.append({
                            "type": "function",
                            "function": {
                                "name": tool["name"],
                                "description": tool["description"],
                                "parameters": tool["input_schema"]
                            }
                        })
                    
                    # Call OpenAI compatible API
                    return self.client.chat.completions.create(
                        model=self.model_name,
                        max_tokens=self.max_tokens,
                        messages=openai_messages,
                        tools=openai_tools,
                        temperature=self.temperature,
                    )
                    
            except Exception as e:
                last_exception = e
                retries += 1
                wait_time = self.retry_delay * (2 ** (retries - 1))  # Exponential backoff
                logger.warning(f"API call failed (attempt {retries}/{self.max_retries}): {e}")
                logger.info(f"Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
        
        logger.error(f"API call failed after {self.max_retries} attempts: {last_exception}")
        raise last_exception
    
    def _clean_message_history(self, messages):
        """
        Completely clean message history to avoid accumulation.
        This is a more aggressive approach to solve message accumulation issues.
        
        Args:
            messages: Original message history
            
        Returns:
            Cleaned message history
        """
        # Check if message list is empty
        if not messages:
            return []
            
        cleaned = []
        
        # Find the last sent user message
        last_user_msg = None
        for i in range(len(messages) - 1, -1, -1):
            if messages[i]["role"] == "user":
                last_user_msg = messages[i]
                break
        
        # If a user message is found, only keep it
        if last_user_msg:
            cleaned.append(last_user_msg)
            
            # Find possible tool calls and responses
            # Only keep the last tool call and response (if exists)
            for i in range(len(messages) - 1, -1, -1):
                # Find assistant messages with tool calls
                if messages[i]["role"] == "assistant" and "tool_calls" in messages[i]:
                    # Add this assistant message
                    cleaned.append(messages[i])
                    
                    # Find corresponding tool response (only process first tool call)
                    if "tool_calls" in messages[i] and messages[i]["tool_calls"]:
                        # Handle both object and dictionary access patterns
                        tool_call = messages[i]["tool_calls"][0]
                        tool_call_id = tool_call.id if hasattr(tool_call, 'id') else tool_call.get("id")
                        
                        # Find corresponding tool response
                        for j in range(i + 1, len(messages)):
                            if (messages[j]["role"] == "tool" and 
                                messages[j].get("tool_call_id") == tool_call_id):
                                cleaned.append(messages[j])
                                break
                    
                    # Process tool chain only once
                    break
        
        # If no message is found (extreme case), return the last message of the original list (if exists)
        if not cleaned and messages:
            return [messages[-1]]
            
        return cleaned
    
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
        
        # Create message content with the game state information (keep original format)
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
        
        # Add message to history - keep original format for all providers
        self.message_history.append({"role": "user", "content": content})
        
        # Get model response with retry
        try:
            if self.provider == "claude":
                # Use original Claude API call
                response = self._call_api_with_retry(
                    self.client.messages.create,
                    model=self.model_name,
                    max_tokens=self.max_tokens,
                    system=SYSTEM_PROMPT,
                    messages=self.message_history,
                    tools=AVAILABLE_TOOLS,
                    temperature=self.temperature,
                )
            else:
                # Use OpenAI-compatible call with _call_api_with_retry without args
                response = self._call_api_with_retry()
        except Exception as e:
            logger.error(f"Failed to get response from {self.provider} after retries: {e}")
            # Default to a simple action if API calls fail completely
            logger.warning("Falling back to default action (press A)")
            
            # Create a minimal response for logging
            if self.provider == "claude":
                response = type('obj', (object,), {
                    'content': [
                        type('obj', (object,), {'type': 'text', 'text': 'API call failed, using default action'})
                    ]
                })
            else:
                # Mock OpenAI format response
                response = type('obj', (object,), {
                    'choices': [
                        type('obj', (object,), {
                            'message': type('obj', (object,), {
                                'content': 'API call failed, using default action'
                            })
                        })
                    ]
                })
            
            # Skip normal processing and return a default action
            next_state = self.take_action("press_key", keys=["a"])
            
            # Add a failure note to history (keep format consistent with original)
            if self.provider == "claude":
                self.message_history.append({
                    "role": "assistant", 
                    "content": [{"type": "text", "text": "API call failed, used default action (press A)"}]
                })
            else:
                self.message_history.append({
                    "role": "assistant", 
                    "content": "API call failed, used default action (press A)"
                })
            
            # Add log entry
            self.log_step_data(
                step_num=self.step_count - 1,
                user_message=content,
                assistant_response=response,
                action_taken={"action_type": "press_key", "button": "a", "reason": "API failure fallback"}
            )
            
            return next_state
        
        # Extract action data and process response based on provider
        action_data = {}
        assistant_content = []
        
        if self.provider == "claude":
            # Process Claude response (keep original format)
            tool_calls = [block for block in response.content if block.type == "tool_use"]
            
            # Collect Claude's response
            for block in response.content:
                if block.type == "text":
                    logger.info(f"[Claude] {block.text}")
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    logger.info(f"[Claude] Using tool: {block.name}")
                    assistant_content.append({"type": "tool_use", **dict(block)})
            
            # Prepare action data
            if tool_calls:
                tool_call = tool_calls[0]
                tool_name = tool_call.name
                tool_input = tool_call.input
                
                if tool_name == "press_key":
                    button = tool_input.get("button")
                    action_data = {"action_type": "press_key", "button": button, "tool_id": tool_call.id}
                elif tool_name == "wait":
                    frames = tool_input.get("frames")
                    action_data = {"action_type": "wait", "frames": frames, "tool_id": tool_call.id}
            else:
                # Default action if no tool call
                action_data = {"action_type": "press_key", "button": "a", "reason": "No tool call found"}
        else:
            # Process OpenAI-compatible response (OpenRouter or Gemini)
            if hasattr(response, 'choices') and response.choices:
                message = response.choices[0].message
                
                # Get text content
                if message.content:
                    logger.info(f"[{self.provider}] {message.content}")
                    assistant_content = message.content
                
                # Extract tool calls if present
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    # Log all tool calls
                    if len(message.tool_calls) > 1:
                        logger.info(f"[{self.provider}] Multiple tool calls detected: {len(message.tool_calls)}")
                        for idx, tc in enumerate(message.tool_calls):
                            logger.info(f"Tool call {idx+1}: {tc.function.name}")
                    
                    # Process tool calls (may be multiple with OpenRouter)
                    tool_call = None
                    
                    # Try to find a 'press_key' or 'wait' tool call as they are higher priority
                    for tc in message.tool_calls:
                        if tc.function.name in ["press_key", "wait"]:
                            tool_call = tc
                            break
                    
                    # If no priority tool call found, use the first one
                    if not tool_call and message.tool_calls:
                        tool_call = message.tool_calls[0]
                    
                    if tool_call:
                        logger.info(f"[{self.provider}] Selected tool call: {tool_call.function.name}")
                        
                        try:
                            # Parse args
                            args = json.loads(tool_call.function.arguments)
                            
                            # Extract action
                            if tool_call.function.name == "press_key":
                                button = args.get("button")
                                if button:
                                    action_data = {"action_type": "press_key", "button": button, "tool_id": tool_call.id}
                            elif tool_call.function.name == "wait":
                                frames = args.get("frames")
                                if frames:
                                    action_data = {"action_type": "wait", "frames": frames, "tool_id": tool_call.id}
                            
                            # Log selected action
                            logger.info(f"Selected action: {action_data}")
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse tool arguments: {tool_call.function.arguments}")
                
                # Default action if no valid tool call found
                if not action_data:
                    action_data = {"action_type": "press_key", "button": "a", "reason": "No valid tool call found"}
            else:
                # Malformed response, default action
                action_data = {"action_type": "press_key", "button": "a", "reason": "Malformed response"}
        
        # Log the response and action before executing
        self.log_step_data(
            step_num=self.step_count,
            user_message=content,
            assistant_response=response,
            action_taken=action_data
        )
        
        # Execute the action
        if action_data["action_type"] == "press_key":
            next_state = self.take_action("press_key", keys=[action_data["button"]])
        elif action_data["action_type"] == "wait":
            next_state = self.take_action("wait", frames=action_data["frames"])
        else:
            # Fallback
            next_state = self.take_action("press_key", keys=["a"])
        
        # Add assistant's response to history (keep provider-specific format)
        if self.provider == "claude":
            # Claude format (list of content blocks)
            self.message_history.append({"role": "assistant", "content": assistant_content})
            
            # Create tool_result response
            tool_result_content = []
            
            # Add tool result if a tool was used
            if "tool_id" in action_data:
                tool_id = action_data["tool_id"]
                
                # Create result message
                if action_data["action_type"] == "press_key":
                    result_message = f"Button '{action_data['button']}' pressed successfully. New location: {next_state['location']}, Coordinates: {next_state['coordinates']}"
                elif action_data["action_type"] == "wait":
                    result_message = f"Waited for {action_data['frames']} frames. New location: {next_state['location']}, Coordinates: {next_state['coordinates']}"
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
        else:
            # OpenAI format (text content)
            self.message_history.append({"role": "assistant", "content": assistant_content})
            
            # Add tool result if tool was used (OpenAI format)
            if "tool_id" in action_data:
                if action_data["action_type"] == "press_key":
                    result_message = f"Button '{action_data['button']}' pressed successfully. New location: {next_state['location']}, Coordinates: {next_state['coordinates']}"
                elif action_data["action_type"] == "wait":
                    result_message = f"Waited for {action_data['frames']} frames. New location: {next_state['location']}, Coordinates: {next_state['coordinates']}"
                else:
                    result_message = f"Action executed. New location: {next_state['location']}, Coordinates: {next_state['coordinates']}"
                
                # Special handling for Gemini provider
                if self.provider == "gemini":
                    # Gemini may have special requirements for tool response format, skip tool response
                    logger.info(f"Gemini: Skipping tool response, adding result directly to user message")
                    # Directly add next user message with result and new image
                    self.message_history.append({
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"{result_message}\nCurrent location: {next_state['location']}, Coordinates: {next_state['coordinates']}"},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{next_state['screenshot_base64']}"}}
                        ]
                    })
                elif self.provider == "openai" or self.provider == "openrouter":
                    # For OpenAI/OpenRouter: tool messages must be responses to preceding messages with 'tool_calls'
                    # We need to add the tool message as a direct response to the assistant message
                    logger.info(f"{self.provider}: Adding tool response as a direct response to tool_calls")
                    
                    # Completely solve message accumulation issue: use new history method
                    # Only keep system role messages and recent user messages, delete all old assistant and tool messages
                    
                    # 1. Find the last user message
                    last_user_msg = None
                    for i in range(len(self.message_history) - 1, -1, -1):
                        if self.message_history[i]["role"] == "user":
                            last_user_msg = self.message_history[i]
                            break
                    
                    # 2. Clear history, only keep last user message
                    if last_user_msg:
                        new_history = [last_user_msg]
                        self.message_history = new_history
                    else:
                        # If no user message is found, clear history
                        self.message_history = []
                    
                    # 3. Add assistant message with tool calls - key fix: ensure correct tool_calls format
                    tool_calls_data = []
                    
                    # Find the current tool call being used
                    for tc in message.tool_calls:
                        # Check if tc is a dictionary or an object and access properties accordingly
                        tc_id = tc.id if hasattr(tc, 'id') else tc.get('id')
                        
                        if tc_id == action_data["tool_id"]:
                            # Create standardized format that meets OpenAI requirements
                            tool_call_obj = {
                                "id": tc_id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name if hasattr(tc, 'function') else tc["function"]["name"],
                                    "arguments": tc.function.arguments if hasattr(tc, 'function') else tc["function"]["arguments"]
                                }
                            }
                            tool_calls_data.append(tool_call_obj)
                            break
                    
                    # Make sure we found the tool call
                    if not tool_calls_data:
                        logger.warning(f"Could not find matching tool call with ID {action_data['tool_id']}")
                        # Add all tool calls as a fallback
                        for tc in message.tool_calls:
                            # Access properties based on object type
                            tc_id = tc.id if hasattr(tc, 'id') else tc.get('id')
                            
                            if tc_id:  # Only add if we have a valid ID
                                tool_call_obj = {
                                    "id": tc_id,
                                    "type": "function",
                                    "function": {
                                        "name": tc.function.name if hasattr(tc, 'function') else tc["function"]["name"],
                                        "arguments": tc.function.arguments if hasattr(tc, 'function') else tc["function"]["arguments"]
                                    }
                                }
                                tool_calls_data.append(tool_call_obj)
                    
                    # Add assistant message with standardized tool_calls format
                    assistant_msg = {
                        "role": "assistant", 
                        "content": assistant_content
                    }
                    
                    # Only add tool_calls field when we have tool call data
                    if tool_calls_data:
                        assistant_msg["tool_calls"] = tool_calls_data
                        
                    self.message_history.append(assistant_msg)
                    
                    # 4. Add single tool response message
                    tool_result = {
                        "role": "tool",
                        "tool_call_id": action_data["tool_id"],
                        "content": result_message
                    }
                    self.message_history.append(tool_result)
                    
                    # 5. Add new user message with result and new image
                    new_user_msg = {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"Current location: {next_state['location']}, Coordinates: {next_state['coordinates']}"},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{next_state['screenshot_base64']}"}}
                        ]
                    }
                    self.message_history.append(new_user_msg)
                    
                    # 6. Record detailed log for debugging
                    logger.info(f"Reset message history. Current size: {len(self.message_history)} messages")
                    logger.info(f"Message roles: {[msg['role'] for msg in self.message_history]}")
                    
                    # 7. Output full message history for debugging (only in DEBUG level)
                    if logger.isEnabledFor(logging.DEBUG):
                        debug_history = []
                        for msg in self.message_history:
                            msg_copy = msg.copy()
                            # Avoid including large base64 images in log
                            if msg["role"] == "user" and isinstance(msg["content"], list):
                                for item in msg_copy["content"]:
                                    if item.get("type") == "image_url" and "image_url" in item:
                                        item["image_url"]["url"] = "[BASE64_IMAGE]"
                            debug_history.append(msg_copy)
                        logger.debug(f"Full message history: {json.dumps(debug_history, indent=2)}")
                else:
                    # No tool call, just add assistant response and new game state/screenshot
                    self.message_history.append({"role": "assistant", "content": assistant_content})
                    self.message_history.append({
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"Current location: {next_state['location']}, Coordinates: {next_state['coordinates']}"},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{next_state['screenshot_base64']}"}}
                        ]
                    })
        
        # Check if history needs summarization
        if len(self.message_history) > self.max_history:
            self._summarize_history()
        
        return next_state
    
    def _summarize_history(self):
        """Summarize conversation history to save context space"""
        logger.info("Summarizing conversation history...")
        
        try:
            if self.provider == "claude":
                # Use original Claude summarization flow
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
            else:
                # OpenAI-compatible summarization
                # Simplify history for summarization request
                simplified_messages = []
                for msg in self.message_history:
                    if msg["role"] in ["user", "assistant"]:
                        if isinstance(msg["content"], list):
                            # Extract text from content blocks
                            text_parts = []
                            for item in msg["content"]:
                                if isinstance(item, dict) and item.get("type") == "text":
                                    text_parts.append(item.get("text", ""))
                            if text_parts:
                                simplified_messages.append({"role": msg["role"], "content": "\n".join(text_parts)})
                        else:
                            # Already text content
                            simplified_messages.append({"role": msg["role"], "content": msg["content"]})
                
                # Add summary request
                simplified_messages.append({
                    "role": "user", 
                    "content": "Please create a detailed summary of our conversation history so far. This summary will replace the full conversation history to manage the context window."
                })
                
                # Get summary using OpenAI-compatible API
                response = self._call_api_with_retry(messages=simplified_messages)
                
                # Extract summary text from OpenAI response
                summary_text = response.choices[0].message.content
            
            # Log the summary
            logger.info(f"Generated summary:\n{summary_text}")
            with open(self.log_file, 'a', encoding='utf-8') as f:
                summary_entry = {
                    "step": f"summary_{self.step_count}",
                    "timestamp": datetime.datetime.now().isoformat(),
                    "summary": summary_text
                }
                f.write(json.dumps(summary_entry, ensure_ascii=False) + '\n')
            
            # Keep recent messages
            recent_msgs = self.message_history[-2:] if len(self.message_history) >= 2 else []
            
            # Replace history with summary message
            if self.provider == "claude":
                # Claude format
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
                ] + recent_msgs
            else:
                # OpenAI format
                self.message_history = [
                    {
                        "role": "user",
                        "content": f"CONVERSATION HISTORY SUMMARY: {summary_text}\n\nYou may now continue playing Pokemon Red. Make your next decision based on the current game state."
                    }
                ] + recent_msgs
            
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

    def _initialize_tools(self):
        self.pending_tool_responses = []
        self.user_message_with_results = None


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
    parser.add_argument("--provider", type=str, default="claude", choices=["claude", "openai", "openrouter", "gemini"], 
                      help="LLM provider to use (claude, openai, openrouter, gemini)")
    parser.add_argument("--model", type=str, default=None, help="Model name for the selected provider")
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
        provider=args.provider,
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
        logger.info(f"Starting AI Agent using {args.provider}, max steps: {args.steps}")
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