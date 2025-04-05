# PokemonEval Human Agent

A human-controlled interface for playing Pokemon Red through the PokemonEval server.

## Overview

The Human Agent provides a pygame-based interface that allows humans to play Pokemon Red through the PokemonEval server. This gives researchers a way to generate human gameplay data for comparison with AI agents, or simply to enjoy playing Pokemon Red through the evaluation framework.

## Installation

1. Make sure you have installed the PokemonEval project and its dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure pygame is installed:
```bash
pip install pygame
```

## Running the Human Agent

Start the Human Agent with:

```bash
python human_agent.py 
```

Command-line arguments:
- `--server`: URL of the PokemonEval server (default: http://localhost:8080)
- `--sound`: Enable sound (optional)
- `--load-state`: Path to a saved state file to load
- `--load-autosave`: Load the latest autosave
- `--session`: Session ID to continue a previous session (e.g., session_20250404_180209)

## Controls

The Human Agent maps keyboard keys to Game Boy buttons:

| Keyboard Key | Function               |
|--------------|------------------------|
| Arrow Up     | D-pad Up               |
| Arrow Down   | D-pad Down             |
| Arrow Left   | D-pad Left             |
| Arrow Right  | D-pad Right            |
| Z            | A button               |
| X            | B button               |
| Enter        | Start button           |
| Right Shift  | Select button          |
| Space        | Wait (30 frames)       |
| F5           | Save state             |
| F7           | Load saved state       |
| Escape       | Quit                   |

## Interface

The Human Agent provides a Pygame window with:

1. Game screen at 3x original size (480x432 pixels)
2. Current location, coordinates, step count, and score display at the top
3. Control information at the bottom
4. Step counter to track your progress

## State Management

### Saving Game States

You can save the current game state at any time by pressing F5. This saves a state file in the current session directory that you can load later. Additionally, the server automatically saves the game state every 50 steps.

### Loading Game States

You can load a previously saved state by:

1. Pressing F7 during gameplay to load the most recently saved state
2. Using the `--load-state` parameter to load a specific state file
3. Using the `--load-autosave` parameter to load the automatic save

### Session Continuation

To continue a previous gameplay session:

```bash
python human_agent.py --session session_20250404_180209
```

When you continue a session:
- The system will automatically load the final state from the session
- All game progress and scores will be preserved
- New gameplay data will be appended to the existing record

## Implementation Details

### Initialization

The Human Agent initializes the Pokemon environment through the server:

```python
def initialize(self, headless: bool = False, sound: bool = False,
              load_state_file: str = None, load_autosave: bool = False,
              session_id: str = None):
    response = self.session.post(
        f"{self.server_url}/initialize",
        headers={"Content-Type": "application/json"},
        json={
            "headless": headless,
            "sound": sound,
            "load_state_file": load_state_file,
            "load_autosave": load_autosave,
            "session_id": session_id
        }
    )
    self.current_state = response.json()
    # Update display with initial state
    self.update_display(self.current_state)
```

### Input Handling

The agent captures keyboard input and translates it to server actions:

```python
# Inside the run loop
for event in pygame.event.get():
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            self.running = False
        elif event.key in KEY_MAPPING:
            key = KEY_MAPPING[event.key]
            
            if key == "wait":
                # Execute wait action
                self.take_action("wait", frames=DEFAULT_WAIT_FRAMES)
            elif key == "save":
                # Save game state
                self.save_state(DEFAULT_SAVE_FILENAME)
            elif key == "load":
                # Load saved game state
                if self.saved_state_path:
                    self.initialize(headless=False, sound=True, 
                                   load_state_file=self.saved_state_path)
            else:
                # Execute press key action
                self.take_action("press_key", keys=[key])
```

### Display Updates

After each action, the display is updated with the latest game state:

```python
def update_display(self, state):
    # Decode base64 image
    image_data = base64.b64decode(state['screenshot_base64'])
    image = Image.open(io.BytesIO(image_data))
    
    # Resize and display image
    image = image.resize((self.screen_width, self.screen_height), Image.NEAREST)
    pygame_image = pygame.image.fromstring(image.tobytes(), image.size, image.mode)
    self.screen.blit(pygame_image, (0, 0))
    
    # Display game information including score
    info_text = f"Location: {state['location']} | Coords: {state['coordinates']} | Step: {self.step_count} | Score: {self.score:.1f}"
    
    # Display controls with save/load options
    controls_text = "Controls: Arrows = Move | Z = A | X = B | Enter = Start | R-Shift = Select | Space = Wait | F5 = Save | F7 = Load"
    
    # Render and display text
    # ...
    
    pygame.display.flip()
```

## Example Usage

Here's how to use the Human Agent in your own code:

```python
from human_agent import HumanAgent

# Create the agent
agent = HumanAgent(server_url="http://localhost:8080")

# Initialize and start the game with a previous session
agent.initialize(
    headless=False, 
    sound=True,
    session_id="session_20250404_180209"
)

# Or load a specific saved state
agent.initialize(
    headless=False,
    sound=True,
    load_state_file="gameplay_sessions/session_20250404_180209/final_state.state"
)

# Run the game (this will start the pygame event loop)
agent.run()

# The game will run until the user presses Escape or closes the window
# When finished, the agent will automatically call stop()
```

## Use Cases

The Human Agent is useful for:

1. **Baseline Performance**: Establish human baseline performance for comparison with AI agents
2. **Data Collection**: Gather human gameplay data for training imitation learning agents
3. **Verification**: Verify that the environment works correctly with human input
4. **Progress Tracking**: Track your progress and scores across multiple sessions
5. **Enjoyment**: Simply enjoy playing Pokemon Red through the evaluation framework

## Troubleshooting

- If the window doesn't appear, make sure pygame is installed correctly
- If the game doesn't respond to input, check if the server is running properly
- If the display is blank, ensure the server is returning valid screenshots
- If the game seems slow, reduce the server load or try running on a more powerful machine
- If a save state fails to load, check that the file exists and path is correct

## Next Steps

After playing with the Human Agent, you might want to:

1. Record your gameplay data for comparison with AI agents
2. Implement your own custom controls or interface
3. Add replay functionality to review your gameplay
4. Extend with additional visualization of game state information 