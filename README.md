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

The server automatically saves the game state every 50 steps to an `autosave.state` file in the session directory.

### Loading and Continuing Sessions

You can continue from a previous session by specifying the session ID:

```bash
# Human agent with session
python human_agent.py --session session_20250404_180209

# AI agent with session
python demo_agent.py --session session_20250404_180209
```

When continuing a session:
- The system will try to load the final state (`final_state.state`)
- The CSV file will be appended to instead of overwritten
- The evaluation score will be preserved from the previous session

### Manual State Management

You can manually save and load states:

1. **Human Agent**: Use F5 to save and F7 to load
2. **Session Management**: Use the `--session` parameter to continue from a specific session directory
3. **Custom States**: Use `--load-state` to load from a specific state file

## Session Data

For each gameplay session, the following data is stored in the `gameplay_sessions` directory:

- `gameplay_data.csv`: Game state data for each step
- `evaluation_summary.txt`: Final evaluation scores and achievements
- `images/`: Screenshots of each step
- `autosave.state`: Most recent automatic save
- `final_state.state`: State saved when the session ends

## Evaluation System

The evaluation system scores your gameplay based on:
- Pokemon collected
- Badges earned
- Locations visited

The score is persistently tracked and shown during gameplay.

## API Endpoints

The server provides the following API endpoints:

- `POST /initialize`: Initialize the environment
- `POST /action`: Take an action in the environment
- `GET /status`: Get the current status
- `POST /stop`: Stop the environment
- `GET /evaluate`: Get the current evaluation summary

## Creating Your Own Agents

You can create your own agents by implementing a client that communicates with the server API. Refer to `human_agent.py` or `demo_agent.py` for examples.
