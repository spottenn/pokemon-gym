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
- `--server`: URL of the PokemonEval server (default: http://localhost:8000)
- `--sound`: Enable sound (optional)
- `--save-screenshots`: Save screenshots locally (optional)
- `--screenshot-dir`: Directory to save screenshots (default: "human_screenshots")

## Controls

The Human Agent maps keyboard keys to Game Boy buttons:

| Keyboard Key | Game Boy Button |
|--------------|-----------------|
| Arrow Up     | D-pad Up        |
| Arrow Down   | D-pad Down      |
| Arrow Left   | D-pad Left      |
| Arrow Right  | D-pad Right     |
| Z            | A button        |
| X            | B button        |
| Enter        | Start button    |
| Right Shift  | Select button   |
| Space        | Wait (30 frames)|
| Escape       | Quit            |

## Interface

The Human Agent provides a Pygame window with:

1. Game screen at 3x original size (480x432 pixels)
2. Current location and coordinates display at the top
3. Control information at the bottom
4. Step counter to track your progress

## Implementation Details

### Initialization

The Human Agent initializes the Pokemon environment through the server:

```python
def initialize(self, headless: bool = False, sound: bool = False):
    response = self.session.post(
        f"{self.server_url}/initialize",
        headers={"Content-Type": "application/json"},
        json={
            "headless": headless,
            "sound": sound
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
    
    # Display game information and controls
    # ...
    
    pygame.display.flip()
```

## Example Usage

Here's how to use the Human Agent in your own code:

```python
from human_agent import HumanAgent

# Create the agent
agent = HumanAgent(server_url="http://localhost:8000")

# Initialize and start the game
agent.initialize(headless=False, sound=True)

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
4. **Enjoyment**: Simply enjoy playing Pokemon Red through the evaluation framework

## Troubleshooting

- If the window doesn't appear, make sure pygame is installed correctly
- If the game doesn't respond to input, check if the server is running properly
- If the display is blank, ensure the server is returning valid screenshots
- If the game seems slow, reduce the server load or try running on a more powerful machine

## Next Steps

After playing with the Human Agent, you might want to:

1. Record your gameplay data for comparison with AI agents
2. Implement your own custom controls or interface
3. Add replay functionality to review your gameplay
4. Extend with additional visualization of game state information 