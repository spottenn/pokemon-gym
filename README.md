# PokemonEval

A benchmark environment for evaluating AI agents on Pokemon Red gameplay.

## Overview

PokemonEval is a framework for evaluating AI agents on Pokemon Red. The framework provides:
- A clean interface for agents to interact with Pokemon Red via the PyBoy emulator
- Tools for measuring agent performance and collecting metrics
- A separation of the environment from agent logic, allowing for fair comparisons
- A server-client architecture for remote agent evaluation

## Project Structure

```
PokemonEval/
├── agent/                   # Agent implementations
│   ├── __init__.py
│   ├── base_agent.py        # Abstract base class for agents
│   ├── simple_agent.py      # A simple Claude-based agent
│   ├── client.py            # Client for connecting to the evaluator server
│   └── server_agent.py      # Agent that interacts with the evaluator server
├── benchmark/               # Benchmarking utilities
│   ├── __init__.py
│   └── evaluator.py         # Agent evaluation
├── pokemon_env/             # Pokemon environment
│   ├── __init__.py
│   ├── action.py            # Action classes (PressKey, Wait)
│   ├── emulator.py          # Low-level emulator interface
│   ├── environment.py       # High-level environment interface
│   └── memory_reader.py     # Read game state from memory
├── server/                  # Server components
│   ├── __init__.py
│   ├── evaluator_server.py  # FastAPI server for remote evaluation
│   └── README.md            # Server documentation
├── main.py                  # Main application entry point
├── run_benchmark.py         # Script to run benchmarks
├── server.py                # Script to run the evaluator server
├── config.py                # Configuration
└── requirements.txt         # Dependencies
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/PokemonEval.git
cd PokemonEval
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Place a Pokemon Red ROM file in the root directory (or specify its path with `--rom`).

## Running an Agent

```bash
python main.py --rom pokemon.gb --steps 100 --display
```

Command-line arguments:
- `--rom`: Path to the Pokemon ROM file (default: "pokemon.gb")
- `--steps`: Number of agent steps to run (default: 10)
- `--display`: Run with display (not headless)
- `--sound`: Enable sound (only applicable with display)
- `--model`: Claude model to use (default: "claude-3-7-sonnet-20250219")
- `--temperature`: Temperature parameter for Claude (default: 1.0)
- `--max-tokens`: Maximum number of tokens for Claude (default: 4000)

## Running Benchmarks

```bash
python run_benchmark.py --rom pokemon.gb --steps 50 --output-dir results
```

Command-line arguments:
- `--rom`: Path to the Pokemon ROM file (default: "pokemon.gb")
- `--steps`: Number of steps to run for evaluation (default: 50)
- `--display`: Run with display (not headless)
- `--sound`: Enable sound (only applicable with display)
- `--output-dir`: Directory to save benchmark results (default: "benchmark_results")
- `--model`: Claude model to use (default: "claude-3-7-sonnet-20250219")

## Running the Evaluator Server

The evaluator server provides a RESTful API for remote agent evaluation:

```bash
python server.py --host 0.0.0.0 --port 8000 --rom pokemon.gb
```

Command-line arguments:
- `--host`: Host address to bind the server to (default: 0.0.0.0)
- `--port`: Port to listen on (default: 8000)
- `--rom`: Path to the Pokemon ROM file (default: "pokemon.gb")
- `--reload`: Enable auto-reload for development

Once the server is running, you can interact with it using the provided client:

```bash
python -m agent.server_agent --steps 10 --server http://localhost:8000
```

For more details about the server API and client usage, see the [server documentation](server/README.md).

## Creating Your Own Agent

To create your own agent, extend the `BaseAgent` class:

```python
from agent.base_agent import BaseAgent
from pokemon_env.environment import GameState
from pokemon_env.action import Action, PressKey

class MyAgent(BaseAgent):
    def __init__(self):
        # Initialize your agent
        pass
    
    def get_action(self, state: GameState) -> Action:
        # Process the game state and decide on an action
        return PressKey(keys=["a"])
    
    def on_episode_start(self) -> None:
        # Called when a new episode starts
        pass
    
    def on_episode_end(self) -> None:
        # Called when an episode ends
        pass
```

### Using the Server Client

To create an agent that interacts with the evaluator server:

```python
from agent.client import PokemonServerClient

# Create client
client = PokemonServerClient(server_url="http://localhost:8000")

# Initialize environment
state = client.initialize(headless=True, sound=False)

# Press buttons
state = client.press_buttons(keys=["a"])

# Wait for frames
state = client.wait(frames=30)

# Stop the environment
client.stop()
```

## License

[MIT License](LICENSE)