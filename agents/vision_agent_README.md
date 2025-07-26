# Pokemon Red Vision Agent with LiteLLM Tool Calling

## Overview

The Vision Agent is a completely reengineered Pokemon Red AI agent that uses modern LiteLLM tool calling and structured chain-of-thought reasoning. This agent represents a significant advancement in AI gameplay through:

- **LiteLLM Tool Calling**: Proper function calling instead of manual parsing
- **Structured Chain of Thought**: Dynamic reasoning depth based on game context
- **Multi-turn Context**: Maintains conversation history for better decision making
- **Image Upscaling**: Enhances screenshots for improved vision model performance

## Key Features

### 1. LiteLLM Tool Integration
The agent uses LiteLLM's native tool calling capabilities with two defined tools:
- `press_button`: Press Game Boy buttons (A, B, start, select, up, down, left, right)
- `wait`: Wait for specified frames (60 frames = 1 second)

### 2. Structured Chain of Thought Protocol
Before every action, the agent outputs:
- **COT_effort**: [LOW/MEDIUM/HIGH] - How much thinking the situation requires
- **COT_length**: [50-500] - Expected reasoning length in words
- **COT**: Detailed step-by-step reasoning

#### Effort Guidelines:
- **LOW**: Simple navigation, dialogue reading (50-100 words)
- **MEDIUM**: Battle moves, Pokemon catching, item usage (100-250 words)
- **HIGH**: Complex battles, team composition, puzzles (250-500 words)

### 3. Enhanced Vision Processing
- Automatic image upscaling (default 2x) for better model performance
- Base64 image handling with PIL for preprocessing
- Optimized for vision models that perform better with larger images

### 4. Conversation History
- Maintains up to 10 turns of conversation history
- Provides context for better sequential decision making
- Prevents repetitive actions through memory of past attempts

## Usage

### Basic Usage
```bash
python agents/vision_agent.py --provider ollama --model PetrosStav/gemma3-tools:4b
```

### Advanced Options
```bash
python agents/vision_agent.py \
    --provider ollama \
    --model PetrosStav/gemma3-tools:4b \
    --temperature 0.7 \
    --max-tokens 2000 \
    --upscale-factor 2.0 \
    --history-limit 10 \
    --headless \
    --max-steps 1000
```

### Command Line Arguments
- `--provider`: LLM provider (ollama, openai, claude, gemini)
- `--model`: Model name
- `--temperature`: Generation temperature (default: 0.7)
- `--max-tokens`: Maximum tokens per response (default: 2000)
- `--upscale-factor`: Image upscaling factor (default: 2.0)
- `--history-limit`: Conversation history limit (default: 10)
- `--headless`: Run without game window
- `--sound`: Enable game audio
- `--max-steps`: Maximum game steps (default: 1000)

## Architecture

### Agent Identity
The agent is prompted as an expert Pokemon Red player with:
- Decades of experience and strategic thinking
- Patient, persistent approach to long-term gameplay
- Ability to learn from mistakes and plan ahead

### Decision Flow
1. **Screenshot Analysis**: Receives game screenshot
2. **Context Building**: Considers conversation history
3. **Reasoning Generation**: Outputs COT_effort, COT_length, and detailed reasoning
4. **Tool Calling**: Uses LiteLLM to call appropriate tool
5. **Action Execution**: Sends action to game server
6. **Memory Update**: Stores reasoning and action in history

### Logging
The agent creates detailed logs in `logs/vision_agent_thoughts_TIMESTAMP.log` containing:
- Step number and timestamp
- Thinking effort level
- Expected reasoning length
- Full chain of thought reasoning
- Action taken

## Example Output

```
============================================================
Step 42 - 2025-07-26 15:23:41
============================================================

THINKING EFFORT: HIGH
REASONING LENGTH: 287 words

CHAIN OF THOUGHT:
I can see a Pokemon battle screen. My Charmander is facing a wild Pidgey. 
Looking at the HP bars, my Charmander has about 75% health remaining while 
the Pidgey appears to be at full health. I need to analyze the type matchup 
and available moves. Charmander is Fire-type while Pidgey is Normal/Flying. 
Neither has a type advantage here. I should check Charmander's available moves 
by selecting FIGHT. Given this is an early-game encounter and Pidgey is a 
common Pokemon that could be useful for my team, I might want to try catching 
it. However, I need to weaken it first. The best strategy would be to use a 
physical attack like Scratch to deal damage without risking a critical hit 
that might knock it out. After weakening it to about 30% health, I can throw 
a Poke Ball. For now, I'll press A to select the FIGHT option.

ACTION TAKEN: press_key a
============================================================
```

## Performance Optimizations

1. **Token Efficiency**: Structured output minimizes wasted tokens
2. **Image Upscaling**: Improves vision model accuracy
3. **Conversation Pruning**: Keeps only recent relevant history
4. **Retry Logic**: Handles transient failures gracefully
5. **Session Management**: Automatic resume from last session

## Requirements

- Python 3.11+
- LiteLLM
- PIL (Pillow) for image processing
- Pokemon Red ROM file
- Running evaluator server

## Future Enhancements

- [ ] Parallel tool calling for complex actions
- [ ] Dynamic image preprocessing based on scene type
- [ ] Advanced memory consolidation for long sessions
- [ ] Real-time strategy adaptation based on game progress
- [ ] Integration with streaming dashboard for live broadcasts