# PokemonEval Demo Agent

A demonstration agent for interacting with the PokemonEval server.

## Overview

The Demo Agent provides a simple implementation that demonstrates how to connect to the PokemonEval server and interact with the Pokemon Red game. This agent includes:

- Basic server communication
- Game state processing
- Random action generation
- Claude integration for intelligent decisions

## Installation

1. Make sure you have installed the PokemonEval project and its dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your Anthropic API key as an environment variable:
```bash
export ANTHROPIC_API_KEY=your_api_key_here
```

## Running the Demo Agent

Run the demo agent with:

```bash
python demo_agent.py --server http://localhost:8000 --steps 100
```

Command-line arguments:
- `--server`: URL of the PokemonEval server (default: http://localhost:8000)
- `--steps`: Number of steps to run (default: 100)
- `--headless`: Run the server in headless mode (optional)
- `--sound`: Enable sound (optional, requires non-headless mode)
- `--model`: Claude model to use (default: claude-3-7-sonnet-20250219)
- `--temperature`: Temperature parameter for Claude (default: 1.0)
- `--max-tokens`: Maximum number of tokens for Claude response (default: 4000)
- `--save-screenshots`: Save screenshots locally (optional)
- `--screenshot-dir`: Directory to save screenshots (default: "screenshots")

## Agent Architecture

The demo agent has the following components:

### 1. Server Connection

The agent connects to the PokemonEval server via HTTP requests, sending action commands and receiving game state updates.

```python
# Initialize the environment
state = agent.initialize(headless=True, sound=False)

# Take actions
state = agent.take_action("press_key", keys=["a"])
state = agent.take_action("wait", frames=30)

# Stop the environment
agent.stop()
```

### 2. State Processing

The agent processes the game state received from the server, extracting relevant information like:
- Player position
- Current location
- Dialog text
- Party Pokemon
- Inventory items

### 3. Claude Integration

The agent sends the game state to Claude AI to make intelligent decisions about what action to take next.

```python
# Prepare state for Claude
content = [
    {"type": "text", "text": "Here is the current state of the game:"},
    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": screenshot_b64}},
    {"type": "text", "text": f"Location: {state['location']}"},
    # ... other state information
]

# Get Claude's response
response = client.messages.create(
    model=model_name,
    max_tokens=max_tokens,
    system=SYSTEM_PROMPT,
    messages=message_history,
    temperature=temperature
)
```

### 4. Action Execution

Based on Claude's analysis, the agent executes the appropriate action:

```python
# Extract tool calls from Claude's response
tool_calls = extract_tool_calls(response.content)

for tool_call in tool_calls:
    if tool_call["name"] == "press_key":
        state = agent.take_action("press_key", keys=[tool_call["parameters"]["button"]])
    elif tool_call["name"] == "wait":
        state = agent.take_action("wait", frames=tool_call["parameters"]["frames"])
```

## Customizing the Agent

You can customize the agent by:

1. Modifying the `SYSTEM_PROMPT` to change the behavior and goals of Claude
2. Implementing additional state processing logic
3. Adding more sophisticated action selection logic
4. Implementing domain-specific knowledge about Pokemon Red

## Example Code

Here's an example of using the demo agent in your own code:

```python
from demo_agent import AIServerAgent

# Create the agent
agent = AIServerAgent(
    server_url="http://localhost:8000",
    model_name="claude-3-7-sonnet-20250219",
    temperature=0.7,
    max_tokens=4000
)

# Initialize the environment
state = agent.initialize(headless=False, sound=True)

# Run for 50 steps
agent.run(max_steps=50)

# Stop the environment
agent.stop()
```

## Troubleshooting

- If you encounter connection errors, make sure the PokemonEval server is running
- If Claude does not make the expected decisions, try adjusting the temperature or system prompt
- If the agent gets stuck, try implementing more sophisticated recovery logic

## Next Steps

Once you're familiar with the demo agent, consider:
1. Implementing your own agent with more sophisticated gameplay strategies
2. Adding performance metrics and evaluation
3. Implementing reinforcement learning or other AI approaches
4. Extending the agent to handle more complex game scenarios 