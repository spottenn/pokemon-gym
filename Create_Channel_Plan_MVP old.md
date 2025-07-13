## **Analysis Summary & Strategic Direction**

You're right to focus on speed and entertainment. The existing "AI Plays" streams are often slow, and a faster, more decisive agent would be a significant differentiator. Your goal to eventually measure steps-to-completion is a fantastic long-term research angle.

**Key Decisions for the MVP:**

1.  **Agent Choice:** We will use `demo_agent.py` for the MVP. It is far simpler to modify for Grok integration and prompt engineering. The `langgraph_agent.py` is powerful but too complex to adapt in an hour. We'll migrate to it post-MVP.
2.  **Vision-Only Approach:** A true vision-only harness requires significant re-engineering of the agent's decision loop. For the MVP, we will simulate this by **aggressively prompting** the model to prioritize the image and ignore the provided text state, even though we'll still send it. This is a classic "prompt-over-code" shortcut that will get you 90% of the way there immediately.
3.  **Visuals:** For the MVP, we'll use a simple, effective method to display the AI's thoughts that requires zero web development.

---

## **The MVP Plan: Go Live in Under 2 Hours**

**Goal:** A live Twitch stream showing the game, Grok's thoughts, and the current Pokémon party. The agent should be playing at a reasonable speed.

###**Step 1: Server Modifications (5 Minutes)**

The server has a hardcoded 4-hour timeout which will kill your stream. Let's fix that.

1.  Open `server/evaluator_server.py`.
2.  Go to **line 33** (or search for `MAX_SESSION_DURATION`).
3.  Change this value to something very large, or a full day in seconds.
    *   **Change this:**
        ```python
        MAX_SESSION_DURATION = 4 * 60 * 60  # 4 hours in seconds
        ```
    *   **To this (for 24 hours):**
        ```python
        MAX_SESSION_DURATION = 24 * 60 * 600 # 240 hours in seconds
        ```

###**Step 2: Agent Modifications (`demo_agent.py`) (20-30 Minutes)**

This is the core of the work. We need to add Grok support, adjust the speed, and implement the vision-first prompt.

1.  **Add Grok as a Provider:**
    *   Open `agents/demo_agent.py`.
    *   In the `__init__` method (around line 140), add a new `elif` block for Grok. Since it's OpenAI compatible, you can just reuse the `OpenAI` client but point it to the Grok API endpoint.

    ```python
    # Find this section around line 170
    elif self.provider == "gemini":
        # ... gemini setup ...
        logger.info(f"Using Gemini provider with model: {self.model_name}")
    # ADD THIS NEW BLOCK RIGHT AFTER
    elif self.provider == "grok":
        api_key = os.getenv("GROK_API_KEY") # Or however you store your key
        if not api_key:
            raise ValueError("GROK_API_KEY environment variable not set")
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1" # This is the Groq API URL
        )
        self.model_name = model_name or "gemma-7b-it" # Or whichever Grok model you want
        logger.info(f"Using Grok provider with model: {self.model_name}")
    # And modify the final else
    else:
        raise ValueError(f"Unsupported provider: {self.provider}. Choose 'claude', 'openai', 'openrouter', 'gemini', or 'grok'")
    ```
    *   In the `main` function at the bottom (around line 1740), add `"grok"` to the `choices` list for the `--provider` argument.

2.  **Implement the Vision-First, Low-Token Prompt:**
    *   Still in `demo_agent.py`, find the `OPENAI_SYSTEM_PROMPT` (around line 43). We will create a new one for Grok.
    *   **Replace the existing `OPENAI_SYSTEM_PROMPT` with this:**
        ```python
        GROK_SYSTEM_PROMPT = """You are Grok, an AI playing Pokemon Red. Your ONLY input is the game screen image. Your goal is to beat the game as fast as possible.
        
        Analyze the image and decide the single most logical button to press next.
        Available buttons: A, B, START, SELECT, UP, DOWN, LEFT, RIGHT.
        
        Respond with ONLY the button press and a brief, 2-5 word justification. Your entire response must be extremely short.
        
        Examples:
        - "UP # Go to door"
        - "A # Talk to NPC"
        - "B # Cancel menu"
        - "START # Open Pokemon menu"
        
        Do not greet. Do not explain your long-term plan. Just the single action.
        """
        
        # ... then find where SYSTEM_PROMPT is set and adjust logic if needed, or just replace OPENAI_SYSTEM_PROMPT.
        # For simplicity in the MVP, just replace the string for OPENAI_SYSTEM_PROMPT with the one above.
        ```
    *   In the `_call_api_with_retry` method (around line 650), ensure the new Grok prompt is used. The existing logic for `"openai"` should work for `"grok"` as well. Make sure it selects `OPENAI_SYSTEM_PROMPT` (which you've now customized for Grok).

3.  **Increase Agent Speed:**
    *   In the `run` method (around line 1700), find and **delete or comment out** this line:
        ```python
        # time.sleep(0.5) # DELETE THIS LINE
        ```

4.  **Parse the New, Simple Response:**
    *   The prompt asks for a very simple response like `UP # Justification`. We need to update the parser.
    *   Go to the `_extract_action_from_text` method (around line 850).
    *   **Replace the complex regex logic with this much simpler version for the MVP:**
        ```python
        def _extract_action_from_text(self, text):
            text_upper = text.strip().upper()
            
            # Look for the first word, which should be the button
            parts = text_upper.split()
            if not parts:
                logger.warning("Empty response from Grok, defaulting to A.")
                return {"action_type": "press_key", "button": "a"}
            
            button = parts[0]
            
            # Validate the button
            valid_buttons = ["A", "B", "START", "SELECT", "UP", "DOWN", "LEFT", "RIGHT"]
            if button in valid_buttons:
                logger.info(f"Grok decided: {text}")
                return {"action_type": "press_key", "button": button.lower()}
            
            # Fallback if the response is not a valid button
            logger.warning(f"Grok response '{text}' was not a valid button. Defaulting to A.")
            return {"action_type": "press_key", "button": "a"}
        ```

###**Step 3: Running and Streaming (15 Minutes)**

1.  **Start the Server:** Open a terminal and run the server in non-headless mode.
    ```bash
    python -m server.evaluator_server --sound
    ```
    A PyBoy window with the game will appear.

2.  **Start the Agent:** Open a *second* terminal. Set your API key and run the modified agent.
    ```bash
    # Make sure you have the API key for your Grok provider
    export GROK_API_KEY="your-grok-api-key"
    
    # Run the agent, pointing it to your new 'grok' provider
    python agents/demo_agent.py --provider grok --log-file grok_thoughts.log
    ```
    Notice the `--log-file grok_thoughts.log`. This is where the AI's raw thoughts will be saved.

3.  **Set up OBS for Streaming:**
    *   **Game Capture:** Add a "Window Capture" source and select the PyBoy game window.
    *   **Thoughts Display:** Add a "Text (GDI+)" source. Set it to "Read from file" and point it to the `grok_thoughts.log` file you created in the agent command. It will now automatically update on stream with Grok's reasoning! You can style the font and color as you like.
    *   **Pokemon Party (Simple MVP version):** For the MVP, you can manually add text or images of the starting Pokemon. We will automate this later.
    *   **Audio:** Add an audio source to capture the game's sound.
