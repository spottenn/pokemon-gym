# PokemonEval Demo Agent

This document explains how to use the demo agent for the Pokemon Red evaluation framework.

## Overview

The Demo Agent is a Claude-powered AI agent that can play Pokemon Red through the PokemonEval server. It demonstrates how to build an AI agent that can:

1. Connect to the PokemonEval server
2. Observe the game state
3. Make decisions based on the observed state
4. Take actions to play the game
5. Track performance metrics and scores

## Installation

1. Make sure you have installed the PokemonEval project and its dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your Claude API key:
```bash
export ANTHROPIC_API_KEY=your-api-key
```

## Running the Demo Agent

Start the Demo Agent with:

```bash
python demo_agent.py
```

Command-line arguments:
- `--server`: URL of the PokemonEval server (default: http://localhost:8080)
- `--headless`: Run without displaying the game (default: False)
- `--sound`: Enable sound (default: False)
- `--load-state`: Path to a saved state file to load
- `--load-autosave`: Load the latest autosave
- `--session`: Session ID to continue a previous session

## Architecture

The Demo Agent has the following components:

1. **AIServerAgent**: Main class that:
   - Communicates with the PokemonEval server
   - Manages the game state
   - Calls Claude for decision making
   - Executes actions based on Claude's decisions

2. **Decision Loop**:
   - Observe the current state
   - Send state information to Claude
   - Parse Claude's response
   - Execute the chosen action
   - Repeat

3. **State Representation**:
   - Game screenshot (base64 encoded)
   - Current location
   - Coordinates in the game world
   - Player's party information
   - Current score and performance metrics

## State Management

The Demo Agent supports several state management features:

### Loading Game States

You can load a previously saved state by:

```bash
python demo_agent.py --load-state gameplay_sessions/session_20250404_180209/final_state.state
```

Or load the latest autosave:

```bash
python demo_agent.py --load-autosave
```

### Session Continuation

To continue a previous gameplay session:

```bash
python demo_agent.py --session session_20250404_180209
```

When you continue a session:
- The system will automatically load the final state from the session
- All game progress and scores will be preserved
- New gameplay data will be appended to the existing record

## Implementation Details

### Initialization

```python
def initialize(self, headless: bool = False, sound: bool = False,
              load_state_file: str = None, load_autosave: bool = False,
              session_id: str = None):
    """Initialize the environment."""
    # Log when loading a state file or using session ID
    if load_state_file:
        logging.info(f"Loading state file: {load_state_file}")
    if session_id:
        logging.info(f"Using session ID: {session_id}")
        
    # Prepare initialization parameters
    init_params = {
        "headless": headless,
        "sound": sound,
        "load_state_file": load_state_file,
        "load_autosave": load_autosave,
        "session_id": session_id
    }
    
    response = self.session.post(
        f"{self.server_url}/initialize",
        headers={"Content-Type": "application/json"},
        json=init_params
    )
    self.current_state = response.json()
```

### Decision Making

The demo agent constructs messages for Claude that include:

```python
def decide_action(self, state):
    """Decide the next action to take based on the current state."""
    # Construct the content to be sent to Claude
    content = [
        human_message(f"You are an AI playing Pokémon Red. Here is the current game state:"),
        human_message(f"Screenshot: [visual information from the game]"),
        human_message(f"Location: {state['location']}"),
        human_message(f"Coordinates: {state['coordinates']}"),
        human_message(f"Party: {state['party']}"),
        human_message(f"Score: {state.get('score', 0)}"),
        human_message(f"Think about the current state and decide what action to take next. You have these actions available: {AVAILABLE_ACTIONS}"),
    ]
    
    # Call Claude to get a decision
    response = call_claude(content)
    
    # Parse the response and extract the action
    # ...
    
    return action, params
```

### Execution Loop

```python
def run(self, max_steps=1000):
    """Run the agent for a specified number of steps."""
    self.initialize(headless=False, sound=True)
    
    for step in range(max_steps):
        # Get the current state
        state = self.current_state
        
        # Log information about the current state
        logging.info(f"Step {step}: Location: {state['location']}, "
                    f"Coords: {state['coordinates']}, "
                    f"Party size: {len(state.get('party', []))}, "
                    f"Score: {state.get('score', 0)}")
        
        # Decide what action to take
        action, params = self.decide_action(state)
        
        # Execute the action
        self.take_action(action, **params)
        
        # Check if we should continue
        if not self.running:
            break
```

## Example Usage

Here's how to use the Demo Agent in your own code:

```python
from demo_agent import AIServerAgent

# Create the agent
agent = AIServerAgent(server_url="http://localhost:8080")

# Initialize with a specific saved state
agent.initialize(
    headless=False,
    sound=True,
    load_state_file="gameplay_sessions/session_20250404_180209/checkpoint_50.state"
)

# Or continue from a previous session
agent.initialize(
    headless=False,
    sound=True,
    session_id="session_20250404_180209"
)

# Run the agent for 500 steps
agent.run(max_steps=500)
```

## Customization

You can customize the Demo Agent by:

1. **Modifying the system message**: Change the instructions given to Claude
2. **Adding memory**: Implement a history of previous states and actions
3. **Implementing specialized behavior**: Add specific strategies for different game phases
4. **Improving state representation**: Add more details about the game state

## Troubleshooting

- If Claude doesn't make good decisions, try improving the state representation or system message
- If actions aren't being executed correctly, check the parsing logic
- If the agent gets stuck, implement a detection mechanism for repetitive states
- If API rate limits are hit, add rate limiting or batching
- If state loading fails, verify the state file path and format

## Next Steps

After experimenting with the Demo Agent:

1. Collect performance metrics and compare with human gameplay
2. Implement more sophisticated decision-making algorithms
3. Add reinforcement learning capabilities
4. Train a more specialized agent for specific game tasks
5. Develop a multi-agent system for collaborative play 