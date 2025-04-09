#!/bin/bash

# Check for required environment variables
if [ -z "$ANTHROPIC_API_KEY" ] || [ -z "$OPENAI_API_KEY" ] || [ -z "$OPENROUTER_API_KEY" ] || [ -z "$GOOGLE_API_KEY" ]; then
    echo "Error: Environment variables not set. Please ensure the following are set:"
    echo "ANTHROPIC_API_KEY, OPENAI_API_KEY, OPENROUTER_API_KEY, GOOGLE_API_KEY"
    exit 1
fi

# Default all agents to enabled
RUN_LLAMA=true
RUN_CLAUDE=true
RUN_OPENAI=true
RUN_GEMINI=true

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --llama-only)
            RUN_LLAMA=true
            RUN_CLAUDE=false
            RUN_OPENAI=false
            RUN_GEMINI=false
            shift
            ;;
        --claude-only)
            RUN_LLAMA=false
            RUN_CLAUDE=true
            RUN_OPENAI=false
            RUN_GEMINI=false
            shift
            ;;
        --openai-only)
            RUN_LLAMA=false
            RUN_CLAUDE=false
            RUN_OPENAI=true
            RUN_GEMINI=false
            shift
            ;;
        --gemini-only)
            RUN_LLAMA=false
            RUN_CLAUDE=false
            RUN_OPENAI=false
            RUN_GEMINI=true
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --llama-only    Run only the Llama 4 server and agent"
            echo "  --claude-only   Run only the Claude server and agent"
            echo "  --openai-only   Run only the OpenAI server and agent"
            echo "  --gemini-only   Run only the Gemini server and agent"
            echo "  --help          Display this help message"
            echo "If no options are provided, all servers and agents will be started."
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information."
            exit 1
            ;;
    esac
done

# Create log directory
mkdir -p logs

echo "Starting Pokemon servers..."

# Track all started PIDs
SERVER_PIDS=""
AGENT_PIDS=""

# Function to start a server and agent pair
start_pair() {
    local model=$1
    local port=$2
    local rom=$3
    local provider=$4
    local model_name=$5
    
    # Start server
    python -m server.evaluator_server --host 0.0.0.0 --port $port --rom $rom > logs/server_$model.log 2>&1 &
    local server_pid=$!
    SERVER_PIDS="$SERVER_PIDS $server_pid"
    echo "Starting $model server (port $port), PID: $server_pid"
    
    # Wait for server to initialize
    echo "Waiting for server to start..."
    sleep 15
    
    # Start agent
    python demo_agent.py --provider $provider --model $model_name --server http://localhost:$port --headless --log-file logs/agent_$model.jsonl > logs/agent_$model.log 2>&1 &
    local agent_pid=$!
    AGENT_PIDS="$AGENT_PIDS $agent_pid"
    echo "Starting $model agent, PID: $agent_pid"
}

# Start selected server/agent pairs
if $RUN_LLAMA; then
    start_pair "llama4" 8080 "Pokemon_Red_llama4.gb" "openrouter" "meta-llama/llama-4-maverick"
    # Wait between starts to stagger them
    sleep 10
fi

if $RUN_CLAUDE; then
    start_pair "claude" 8081 "Pokemon_Red_claude.gb" "claude" "claude-3-7-sonnet-20250219"
    sleep 10
fi

if $RUN_OPENAI; then
    start_pair "openai" 8082 "Pokemon_Red_openai.gb" "openai" "gpt-4o-2024-11-20"
    sleep 10
fi

if $RUN_GEMINI; then
    start_pair "gemini" 8083 "Pokemon_Red_gemini.gb" "gemini" "gemini-2.5-pro-preview-03-25"
fi

echo "All selected servers and agents have been started."
echo "Server PIDs:$SERVER_PIDS"
echo "Agent PIDs:$AGENT_PIDS"

# Save PIDs to file for later termination
ALL_PIDS="$SERVER_PIDS $AGENT_PIDS"
echo $ALL_PIDS > pokemon_pids.txt

echo "To stop all processes, run: kill \$(cat pokemon_pids.txt)"

# Wait for user input to stop
echo "Press Enter to stop all processes..."
read

# Stop all processes
echo "Stopping all processes..."
kill $AGENT_PIDS
kill $SERVER_PIDS
rm pokemon_pids.txt

echo "All processes have been stopped."
