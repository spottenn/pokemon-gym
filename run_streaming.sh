#!/bin/bash

# Pokemon Gym Streaming Runner
# This script runs all components needed for streaming

set -e

echo "========================================="
echo "Pokemon Gym Streaming Setup"
echo "========================================="
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Error: Virtual environment not found. Please run setup_pokemon_gym.sh first"
    exit 1
fi

# Check if Pokemon ROM exists
if [ ! -f "Pokemon_Red.gb" ]; then
    echo "Error: Pokemon_Red.gb not found. Please place it in the project root"
    exit 1
fi

# Function to cleanup background processes on exit
cleanup() {
    echo ""
    echo "Shutting down services..."
    pkill -f "python -m server.evaluator_server" 2>/dev/null || true
    pkill -f "python agents/vision_agent.py" 2>/dev/null || true
    pkill -f "npm run dev" 2>/dev/null || true
    echo "Services stopped."
}

# Set trap to cleanup on script exit
trap cleanup EXIT

echo "Starting services..."
echo ""

# Start evaluator server
echo "1. Starting evaluator server on port 8081..."
source .venv/bin/activate
python -m server.evaluator_server --port 8081 &
SERVER_PID=$!
sleep 3

# Check if server started successfully
if ! curl -s http://localhost:8081/ > /dev/null 2>&1; then
    echo "⚠️  Server may still be starting..."
fi
echo "✓ Evaluator server running on http://localhost:8081"

# Start vision agent
echo ""
echo "2. Starting vision agent..."
python agents/vision_agent.py --server-url http://localhost:8081 --provider ollama --model PetrosStav/gemma3-tools:4b &
AGENT_PID=$!
sleep 2
echo "✓ Vision agent started"

# Start React dashboard
echo ""
echo "3. Starting streaming dashboard..."
cd streaming-dashboard
npm run dev -- --port 5174 &
DASHBOARD_PID=$!
cd ..
sleep 5
echo "✓ Streaming dashboard running on http://localhost:5174"

echo ""
echo "========================================="
echo "All services are running!"
echo "========================================="
echo ""
echo "- Evaluator Server: http://localhost:8081"
echo "- Vision Agent: Running (check logs/vision_agent_thoughts_*.log)"
echo "- Streaming Dashboard: http://localhost:5174"
echo ""
echo "Configure OBS to capture the dashboard at http://localhost:5174"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for user to stop
wait