# MVP

#### **Step 1: The (Only) Code Change (5-10 Minutes)**

We will add a few lines to `agents/demo_agent.py` to write the LLM's raw response to the log file *before* it gets parsed.

1.  Open `agents/demo_agent.py`.
2.  Navigate to the `decide_action` method (around line 1300).
3.  Find the section that calls the LLM. It looks like this:

    ```python
    # ... inside decide_action method ...
    try:
        if self.provider == "claude":
            # ... claude call ...
        elif self.provider == "gemini":
            # ... gemini call ...
        else:
            # Use OpenAI-compatible call with _call_api_with_retry without args
            response = self._call_api_with_retry()
    except Exception as e:
        # ... error handling ...
    ```

4.  **Immediately after this `try...except` block, add the following code.** This new block will extract the text from the `response` object and write it to the file specified by `--log-file`.

    ```python
    # ... (code from above) ...
    # ADD THIS NEW BLOCK RIGHT HERE
    # --- START OF NEW CODE ---
    try:
        # Extract the raw text response from the LLM
        thought_text = ""
        if self.provider in ["openai", "openrouter", "grok"]: # Assuming 'grok' is like openai
            if hasattr(response, 'choices') and response.choices:
                thought_text = response.choices[0].message.content
        elif self.provider == "gemini":
             if hasattr(response, 'choices') and response.choices:
                thought_text = response.choices[0].message.content
        elif self.provider == "claude":
            if hasattr(response, 'content') and response.content:
                thought_text = response.content[0].text

        # Overwrite the log file with the latest thought
        if self.log_file and thought_text:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write(thought_text)
    except Exception as log_e:
        logger.error(f"Failed to write thought to log file: {log_e}")
    # --- END OF NEW CODE ---

    # The original code continues from here...
    action_data = {}
    assistant_content = []
    # ... etc
    ```
    **Why this works:** The `self.log_file` attribute is already set up in the agent's `__init__` method from the command-line arguments. By opening the file with `'w'` (write mode), we ensure it's completely overwritten every time, so it *only* ever contains the most recent thought.

#### **Step 2: How to Run It (1 Minute)**

This is now even simpler. The `--log-file` argument now controls our real-time thought display.

1.  **Start the Server (No Change):**
    ```bash
    python -m server.evaluator_server --sound
    ```

2.  **Start the Agent:** Use a simple `.txt` extension for the log file to make it clear.
    ```bash
    # Set your API key
    export GROK_API_KEY="your-grok-api-key"
    
    # Run the agent and tell it where to write its thoughts
    python agents/demo_agent.py --provider grok --log-file thoughts.txt
    ```
    A file named `thoughts.txt` will now be created in your project directory and will be updated with every decision Grok makes.

#### **Step 3: OBS Setup for the Stream (5 Minutes)**

This is the final piece to get your visuals working.

1.  **Game Capture:** Add a "Window Capture" source and select the PyBoy game window.

2.  **Thoughts Display (The "Tail"):**
    *   In OBS, add a new source: **"Text (GDI+)"**.
    *   Give it a name, like "AI Thoughts".
    *   In the properties for this new source, check the box that says **"Read from file"**.
    *   Click the "Browse" button and select the `thoughts.txt` file you created in Step 2.
    *   Click "OK".

3.  **Style and Position:**
    *   You will now see Grok's thoughts as text on your OBS canvas.
    *   You can drag it, resize it, and change the font, color, and add a background in the Text source properties to match your stream's aesthetic.

### Why This is the Perfect MVP Solution

*   **Zero Added Complexity:** We added ~15 lines of Python to one file. We didn't create any new scripts or dependencies.
*   **No Web Dev Needed:** You don't have to touch HTML, CSS, or JavaScript. OBS handles the display.
*   **Real-Time Updates:** OBS automatically polls the text file for changes. Since our script overwrites it with every new thought, your stream will always show the latest decision instantly.
*   **Extremely Robust:** This method is dead simple and very hard to break.

This approach gets you 95% of the visual impact of a full dashboard with about 5% of the engineering effort. You can now focus entirely on prompt engineering and getting the agent playing for your first stream.