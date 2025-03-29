# PokemonEval Server

A server for evaluating AI agents on Pokemon Red gameplay.

## Overview

The PokemonEval server provides a RESTful API for agents to interact with Pokemon Red via the PyBoy emulator. This server component handles game state management, action execution, and provides a clean interface for remote evaluation of agents.

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

3. Place a Pokemon Red ROM file in the root directory or specify its path with `--rom`.

## Starting the Server

Run the server with:

```bash
python server.py --host 0.0.0.0 --port 8000 --rom pokemon.gb
```

Command-line arguments:
- `--host`: Host address to bind the server to (default: 0.0.0.0)
- `--port`: Port to listen on (default: 8000)
- `--rom`: Path to the Pokemon ROM file (default: "pokemon.gb")
- `--reload`: Enable auto-reload for development

## Server API

### Initialize Environment

```
POST /initialize
```

Request body:
```json
{
  "headless": true,
  "sound": false
}
```

Response:
```json
{
  "player_name": "RED",
  "rival_name": "BLUE",
  "money": 3000,
  "location": "PALLET TOWN",
  "coordinates": [5, 6],
  "badges": ["BOULDER", "CASCADE"],
  "valid_moves": ["up", "down", "left", "right"],
  "inventory": [
    {"item": "POTION", "quantity": 3},
    {"item": "POKEBALL", "quantity": 5}
  ],
  "dialog": "PROF.OAK: Hello, welcome to the world of POKEMON!",
  "party_pokemon": [
    {
      "nickname": "PIKACHU",
      "species": "PIKACHU",
      "level": 5,
      "hp": {"current": 20, "max": 20},
      "moves": [{"name": "TACKLE", "pp": {"current": 35, "max": 35}}]
    }
  ],
  "screenshot_base64": "base64_encoded_image_data",
  "collision_map": "text_representation_of_collision_map",
  "step_number": 0,
  "execution_time": 0.123
}
```

### Take Action

```
POST /action
```

Request body (for pressing a key):
```json
{
  "action_type": "press_key",
  "keys": ["a"]
}
```

Request body (for waiting):
```json
{
  "action_type": "wait",
  "frames": 60
}
```

Response: Same format as the initialize endpoint

### Check Status

```
GET /status
```

Response:
```json
{
  "status": "running",
  "steps_taken": 42,
  "average_action_time": 0.156
}
```

### Stop Environment

```
POST /stop
```

Response:
```json
{
  "status": "stopped",
  "steps_taken": 42
}
```

## Action Types

The server supports two types of actions:

### 1. Press Key

Used to press one or more Game Boy buttons in sequence.

```json
{
  "action_type": "press_key",
  "keys": ["a"]
}
```

Valid keys:
- `"a"` - A button
- `"b"` - B button
- `"start"` - Start button
- `"select"` - Select button
- `"up"` - D-pad Up
- `"down"` - D-pad Down
- `"left"` - D-pad Left
- `"right"` - D-pad Right

You can send multiple keys in a sequence:
```json
{
  "action_type": "press_key",
  "keys": ["up", "up", "a"]
}
```

### 2. Wait

Used to wait for a specified number of frames.

```json
{
  "action_type": "wait",
  "frames": 60
}
```

Where:
- `frames` is the number of frames to wait (at 60 FPS, 60 frames = 1 second)

## Game State Response

Each action returns a game state response with the following information:

- `player_name`: Player character name
- `rival_name`: Rival character name
- `money`: Current money
- `location`: Current location name
- `coordinates`: Player [x, y] coordinates
- `badges`: List of obtained badges
- `valid_moves`: List of valid movement directions
- `inventory`: List of items and quantities
- `dialog`: Any active dialog text
- `party_pokemon`: List of Pokemon in the party with stats
- `screenshot_base64`: Base64-encoded screenshot
- `collision_map`: Text representation of collision map
- `step_number`: Current step number
- `execution_time`: Time taken to execute the action

## Client Implementation Example

Here's a simple Python example for interacting with the server:

```python
import requests

# Server URL
SERVER_URL = "http://localhost:8000"

# Initialize environment
response = requests.post(
    f"{SERVER_URL}/initialize",
    json={"headless": True, "sound": False}
)
state = response.json()

# Press a button
response = requests.post(
    f"{SERVER_URL}/action",
    json={"action_type": "press_key", "keys": ["a"]}
)
state = response.json()

# Wait for frames
response = requests.post(
    f"{SERVER_URL}/action",
    json={"action_type": "wait", "frames": 60}
)
state = response.json()

# Stop environment
requests.post(f"{SERVER_URL}/stop")
```

## Notes

- The server maintains session data and images in the `gameplay_sessions` directory
- All screenshots are saved in the session's `images` folder
- Gameplay data is logged to a CSV file in the session directory 