# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is **Pokemon-Gym**, a platform for evaluating AI agents on Pokemon Red gameplay that is being converted from a benchmarking tool into a **streaming-ready system** by spottenn with AI assistance. The project allows AI agents to play Pokemon Red through a server-client architecture with real-time streaming capabilities for live content creation.

## Key Architecture Components

### Core System
- **Server** (`server/evaluator_server.py`): FastAPI server controlling Pokemon Red emulation via PyBoy
- **Environment** (`pokemon_env/`): Pokemon Red environment wrapper and game state management  
- **Evaluator** (`evaluator/`): Scoring system and milestone tracking for Pokemon Red gameplay

### Agent Systems
- **Vision Agent** (`agents/vision_agent.py`): WIP custom vision only agent designed by spottenn, intended for streaming
- **Demo Agent** (`agents/demo_agent.py`): Traditional single-step AI agent for various LLM providers
- **LangGraph Agent** (`agents/langgraph_agent.py`): Advanced agent built with LangGraph for complex decision-making workflows
- **Human Agent** (`agents/human_agent.py`): Human-playable interface with keyboard controls

### Streaming Infrastructure
- **Streaming Mode**: Emulator kept at 1x continuous speed for live content (see MVP plan)
- **Session Management**: Automatic saves every 50 steps with session continuation support
- **React Dashboard** (`streaming-dashboard/`): Real-time web interface for OBS streaming integration
- **Progress Tracking**: See `PENDING_AUDIT_PROGRESS_REPORT.md` for latest development status

## Environment Setup

### Virtual Environment
This project uses `.venv` for dependency isolation. 

For the first setup with new instances of the repo (likely already done for you):

```bash
py -3.11 -m venv .venv

# Install dependencies
pip install -r requirements.txt
```

The virtual environment is automatically activated via Claude Code hooks configuration.


### Environment Variables
Copy `.env.example` to `.env` and configure API keys:
- `ANTHROPIC_API_KEY`: For Claude models
- `OPENAI_API_KEY`: For OpenAI GPT models  
- `OPENROUTER_API_KEY`: For OpenRouter models
- `GOOGLE_API_KEY`: For Google Gemini models
- `XAI_API_KEY`: For XAI models

### Local Development with Ollama
For testing without API keys, use Ollama running on Windows (accessible from WSL):
- Recommended model: `PetrosStav/gemma3-tools:4b` (pull with `ollama pull PetrosStav/gemma3-tools:4b`)
- **Dynamic endpoint detection**: The system automatically detects the Windows host IP from WSL (commonly `172.31.160.1:11434`)
- Use provider `ollama` when running agents - no additional configuration required

### ROM Setup
Place `Pokemon_Red.gb` ROM file in the project root directory.

## Common Development Commands

### Traditional Server
```bash
# Start evaluator server
python -m server.evaluator_server

# With options
python -m server.evaluator_server --host 0.0.0.0 --port 8080 --sound
```

### Running Agents
```bash
# LangGraph agent (recommended for complex gameplay)
python agents/langgraph_agent.py --provider claude --headless

# Demo agent with streaming thoughts
python agents/demo_agent.py --provider claude 

# Human agent
python agents/human_agent.py --sound

# vision agent WIP
python agents/vision_agent.py --placeholder-arg
```

### Testing and Linting
```bash
# Run tests
python -m pytest

# Lint code  
python -m ruff check .

# Format code
python -m ruff format .
```

## Development Workflow

### LangGraph Agent Development
The `langgraph_agent.py` represents an alternative next-generation agent architecture that might be used for the vision agent:
- **State Management**: Uses `PokemonAgentState` with short-term memory, task tracking, and location knowledge
- **Graph-Based**: LangGraph workflow with nodes for observe → construct_prompt → think → execute
- **Memory System**: 20-step short-term memory with automatic consolidation
- **Visual Analysis**: Screenshot analysis integrated into decision-making
- **Error Handling**: Robust retry logic and recovery strategies

### Development Workflow
For development, use PyCharm debug configuration to restart components as needed. No live reloading is used.

### Streaming Setup (Production)
For live streaming Pokemon gameplay with AI thoughts and real-time dashboard:

**Automated Setup (Recommended):**
```bash
# Start all components (server, agent, dashboard)
powershell -ExecutionPolicy Bypass -File start_streaming.ps1

# Stop all components
powershell -ExecutionPolicy Bypass -File stop_streaming.ps1
```

**Manual Setup:**
1. Start evaluator server: `python -m server.evaluator_server --port 8081`
2. Start vision agent: `python agents/vision_agent.py`  
3. Start React dashboard: `cd streaming-dashboard && yarn dev --port 5174`
4. Configure OBS to capture dashboard at `http://localhost:5174`

### Session Management
- Sessions auto-save every 50 steps to `gameplay_sessions/`
- Use `--session` to continue previous sessions
- State files can be loaded with `--load-state` or `--load-autosave`
- Visual agent will automatically resumes latest session

## Key Files for Understanding

### Agent Logic
- `agents/langgraph_agent.py:542-583`: Core agent prompt and decision-making logic
- `agents/langgraph_agent.py:1061-1209`: Game state analysis and prompt construction  
- `agents/langgraph_agent.py:1211-1374`: LLM response parsing and action extraction

### Server Integration
- `server/evaluator_server.py:66-82`: API request/response models

### Streaming Architecture
- `Create_Channel_Plan_MVP.md`: Detailed streaming implementation plan
- `agents/vision_agent.py`: Includes streaming thought output capabilities

## Dependencies and Requirements

- **Python**: 3.11+ (tested on 3.11.9)
- **Core**: FastAPI, PyBoy, LangGraph, LangChain
- **AI Providers**: Anthropic, OpenAI, Google GenerativeAI, OpenRouter, Groq Cloud (soon)
- **Utilities**: Pillow, NumPy, Pandas, OpenCV

## Important Notes

- Use PyCharm debug configurations for development
- The LangGraph agent is the preferred implementation for complex gameplay
- Sessions save automatically every 10 steps to `gameplay_sessions/`
- ROM file (`Pokemon_Red.gb`) must be present in project root
- All agents support multiple LLM providers (Claude, OpenAI, Gemini, OpenRouter)