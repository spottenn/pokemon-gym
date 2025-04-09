# PokemonGym   
<div align="center">
  <a href="https://discord.gg/mZ9Rc8q8W3" target="_blank">
    <img src="https://img.shields.io/badge/Join%20our%20Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Join our Discord">
  </a>
  <p>
    A server for evaluating AI agents on Pokemon Red gameplay.
  </p>
  
</div>




![Group 1 (1)](https://github.com/user-attachments/assets/25f3da86-0335-4324-8dab-f64f0d6791bf)

## Overview

PokemonEval is a platform that allows AI agents to play Pokemon Red through a server-client architecture. The system includes:

- **Server**: A FastAPI server that controls Pokemon Red emulation and exposes game state via API
- **Human Agent**: A UI that allows humans to play the game through keyboard controls
- **Demo Agent**: An AI agent powered by Claude that can play the game autonomously
- **Evaluation System**: A scoring system that rewards progress in the game (collecting Pokemon, badges, visiting locations)
- **State Management**: Save and load game states for continued gameplay across sessions

## Installation

### Prerequisites

- Python 3.8+
- PyBoy and its dependencies
- Pokemon Red ROM file (not included)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/PokemonEval.git
cd PokemonEval
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Place your Pokemon Red ROM file in the root directory and name it `Pokemon_Red.gb`

## Running the Server

Start the evaluation server:

```bash
python -m server.evaluator_server
```

The server will start at http://localhost:8080 by default.

Options:
- `--host`: Host to run the server on (default: 0.0.0.0)
- `--port`: Port to run the server on (default: 8080)
- `--rom`: Path to the Pokemon ROM file (default: Pokemon_Red.gb)
- `--log-file`: Custom CSV filename (optional)

## Running Multiple AI Agents Simultaneously

You can run multiple AI agents simultaneously using the provided bash script. This allows you to compare the performance of different AI models side by side.

### ROM File Setup

First, you need to prepare separate ROM files for each agent:

1. Copy your Pokemon Red ROM file to create separate instances for each AI:
```bash
cp Pokemon_Red.gb Pokemon_Red_llama4.gb
cp Pokemon_Red.gb Pokemon_Red_claude.gb
cp Pokemon_Red.gb Pokemon_Red_openai.gb
cp Pokemon_Red.gb Pokemon_Red_gemini.gb
```

### Set Required Environment Variables

The script requires API keys for all supported AI providers:

```bash
export ANTHROPIC_API_KEY=your_anthropic_key_here
export OPENAI_API_KEY=your_openai_key_here
export OPENROUTER_API_KEY=your_openrouter_key_here
export GOOGLE_API_KEY=your_google_key_here
```

### Running the Servers

Start all AI agents with:

```bash
bash run_pokemon_servers.sh
```

This will start four separate emulation servers on different ports (8080-8083) and launch each AI agent connected to its respective server.

### Command Options

You can choose to run only specific AI agent combinations:

```bash
# Run only Llama 4
bash run_pokemon_servers.sh --llama-only

# Run only Claude
bash run_pokemon_servers.sh --claude-only

# Run only OpenAI
bash run_pokemon_servers.sh --openai-only

# Run only Gemini
bash run_pokemon_servers.sh --gemini-only
```

The script will:
1. Start each server on a dedicated port
2. Wait for the server to initialize
3. Launch the corresponding AI agent
4. Save all process IDs for easy termination

### Stopping the Servers

To stop all servers and agents:

```bash
bash stop_pokemon_servers.sh
```

Or press Enter in the terminal where you started the servers.

## Playing as a Human

You can play Pokemon Red yourself with keyboard controls:

```bash
python human_agent.py
```

Options:
- `--server`: Server URL (default: http://localhost:8080)
- `--sound`: Enable sound (requires non-headless mode)
- `--load-state`: Path to a saved state file to load
- `--load-autosave`: Load the latest autosave
- `--session`: Session ID to continue a previous session (e.g., session_20250404_180209)

### Controls

- Arrow Keys: Move
- Z: A button
- X: B button
- Enter: Start button
- Right Shift: Select button
- Space: Wait (advances a few frames)
- F5: Save current state
- F7: Load last saved state

## Running the AI Agent

The demo AI agent uses Claude to make decisions based on the game screen:

```bash
python demo_agent.py
```

First, set your Anthropic API key:
```bash
export ANTHROPIC_API_KEY=your_api_key_here
```

Options:
- `--server`: Server URL (default: http://localhost:8080)
- `--steps`: Number of steps to run (default: 1000000)
- `--headless`: Run in headless mode
- `--sound`: Enable sound (requires non-headless mode)
- `--model`: Claude model to use (default: claude-3-5-sonnet-20241022)
- `--temperature`: Temperature for Claude (default: 1.0)
- `--max-tokens`: Max tokens for Claude (default: 4000)
- `--log-file`: File to save agent logs (default: agent_log.jsonl)
- `--load-state`: Path to a saved state file to load
- `--load-autosave`: Load the latest autosave
- `--session`: Session ID to continue a previous session

## Game State Management

### Automatic Saving

The server automatically saves the game state every 50 steps to an `autosave.state` file in the session directory. Additionally, the final state is saved when stopping a session, and on timeout events.

### Manual Saving

When playing as a human, you can save the current state at any time by pressing F5. This creates a state file that you can load later.

### Loading and Continuing Sessions

You can continue from a previous session by specifying the session ID:

```bash
# Human agent with session
python human_agent.py --session session_20250404_180209

# AI agent with session
python demo_agent.py --session session_20250404_180209
```

When continuing a session:
- The system will automatically load the final state (`final_state.state`)
- The CSV file will be appended to instead of overwritten
- The evaluation score will be preserved from the previous session

### Manual State Loading

You can manually load states in several ways:

1. **During Gameplay**: Human players can press F7 to load the most recently saved state
2. **Session Parameter**: Use the `--session` parameter to continue from a specific session directory
3. **State File Parameter**: Use `--load-state` to load from a specific state file path
4. **Autosave Parameter**: Use `--load-autosave` to load the most recent autosave

## Evaluation System

The evaluation system tracks and scores your gameplay progress based on:

- **Pokemon Collection**: Points for each unique Pokemon caught
- **Badges Earned**: Points for each gym badge obtained
- **Locations Visited**: Points for discovering new areas
- **Game Progression**: Points for key game events and milestones

The score is persistently tracked and displayed during gameplay. When continuing from a previous session, the evaluation state is loaded to maintain score continuity.

## Session Data

For each gameplay session, the following data is stored in the `gameplay_sessions/[session_id]` directory:

- `gameplay_data.csv`: Game state data for each step
- `evaluation_summary.txt`: Final evaluation scores and achievements
- `images/`: Screenshots of each step
- `autosave.state`: Most recent automatic save (every 50 steps)
- `final_state.state`: State saved when the session ends normally
- `timeout_state.state`: State saved if the session times out

## API Endpoints

The server provides the following API endpoints:

- `POST /initialize`: Initialize the environment
  - Parameters: `headless`, `sound`, `load_state_file`, `load_autosave`, `session_id`
- `POST /action`: Take an action in the environment
  - Action types: `press_key` (with keys), `wait` (with frames)
- `GET /status`: Get the current status of the environment
- `POST /stop`: Stop the environment and save final state
- `GET /evaluate`: Get the current evaluation summary
- `POST /save_state`: Save the current state to a file
- `POST /load_state`: Load a state from a file

## 

## Creating Your Own Agents

You can create your own agents by implementing a client that communicates with the server API. Refer to `human_agent.py` or `demo_agent.py` for examples.

### Implementing an Agent

Your agent should:

1. **Initialize**: Call the `/initialize` endpoint to start a session
2. **Observe**: Process the returned game state (image, location, party, etc.)
3. **Decide**: Determine the next action to take
4. **Act**: Call the `/action` endpoint with your chosen action
5. **Repeat**: Continue the observe-decide-act loop
6. **Stop**: Call the `/stop` endpoint when finished

### Example Minimal Agent

```python
import requests

class MinimalAgent:
    def __init__(self, server_url="http://localhost:8080"):
        self.server_url = server_url
        self.session = requests.Session()
        
    def initialize(self):
        response = self.session.post(
            f"{self.server_url}/initialize",
            json={"headless": True, "sound": False}
        )
        return response.json()
        
    def take_action(self, action_type, **kwargs):
        response = self.session.post(
            f"{self.server_url}/action",
            json={"action_type": action_type, **kwargs}
        )
        return response.json()
        
    def stop(self):
        self.session.post(f"{self.server_url}/stop")
        
    def run(self):
        # Initialize
        state = self.initialize()
        
        # Take 10 random actions
        for i in range(10):
            # Press the A button
            state = self.take_action("press_key", keys=["a"])
            
            # Wait 30 frames
            state = self.take_action("wait", frames=30)
            
        # Stop the environment
        self.stop()

# Use the agent
if __name__ == "__main__":
    agent = MinimalAgent()
    agent.run()
```
