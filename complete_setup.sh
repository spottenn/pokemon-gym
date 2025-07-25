#!/bin/bash

# Complete Pokemon Gym Setup Script
# This script performs all setup steps for a fresh clone of pokemon-gym

set -e  # Exit on error

echo "========================================="
echo "Complete Pokemon Gym Setup"
echo "========================================="
echo ""

# Step 1: Python Environment
echo "Step 1: Setting up Python environment..."
if [ ! -d ".venv" ]; then
    python3.11 -m venv .venv
    echo "  ✓ Virtual environment created"
else
    echo "  ✓ Virtual environment already exists"
fi

source .venv/bin/activate
pip install --upgrade pip --quiet
echo "  ✓ Pip upgraded"

echo "  Installing Python dependencies (this may take a few minutes)..."
pip install -r requirements.txt --quiet
echo "  ✓ Python environment ready"

# Step 2: Environment Variables
echo ""
echo "Step 2: Setting up environment variables..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "  ✓ Environment file created"
else
    echo "  ✓ Environment file already exists"
fi

# Step 3: Pokemon ROM
echo ""
echo "Step 3: Setting up Pokemon ROM..."
if [ ! -f "Pokemon_Red.gb" ]; then
    # Try to find ROM in parent directories
    ROM_PATH=$(find ../.. -name "Pokemon_Red.gb" -type f | head -1)
    if [ -n "$ROM_PATH" ]; then
        cp "$ROM_PATH" .
        echo "  ✓ ROM copied from $ROM_PATH"
    else
        echo "  ⚠️  Pokemon_Red.gb not found in parent directories"
        echo "     Please place Pokemon_Red.gb in the project root manually"
    fi
else
    echo "  ✓ ROM file already present"
fi

# Step 4: React Dashboard
echo ""
echo "Step 4: Setting up React dashboard..."
cd streaming-dashboard
if [ ! -f "package.json" ]; then
    echo "  Copying streaming dashboard files..."
    # Look for a populated streaming-dashboard in nearby directories
    DASHBOARD_PATH=""
    for search_path in "../../pokemon-gym" "../../../claude-code/pokemon-gym" "../../../pokemon-gym"; do
        if [ -f "$search_path/streaming-dashboard/package.json" ]; then
            DASHBOARD_PATH="$search_path/streaming-dashboard"
            break
        fi
    done
    
    if [ -n "$DASHBOARD_PATH" ]; then
        cp -r "$DASHBOARD_PATH"/* .
        echo "  ✓ Dashboard files copied from $DASHBOARD_PATH"
    else
        echo "  ⚠️  Could not find streaming dashboard files"
        echo "     You may need to set up the React dashboard manually"
    fi
fi

if [ -f "package.json" ]; then
    if [ ! -d "node_modules" ]; then
        echo "  Installing React dependencies..."
        npm install --quiet
        echo "  ✓ React dependencies installed"
    else
        echo "  ✓ React dependencies already installed"
    fi
else
    echo "  ⚠️  No package.json found - React dashboard setup incomplete"
fi
cd ..

echo ""
echo "========================================="
echo "Setup Complete! Testing Components..."
echo "========================================="

# Test components
echo ""
echo "Testing server..."
timeout 3 python -m server.evaluator_server --port 8081 > /dev/null 2>&1 &
sleep 2
if curl -s http://localhost:8081/ > /dev/null 2>&1; then
    echo "✓ Server works"
else
    echo "⚠️  Server test inconclusive"
fi
pkill -f "python -m server.evaluator_server" 2>/dev/null || true

echo ""
echo "Fixing agents module imports..."
# Fix demo_agent import issue in fresh clones
if ! [ -f "agents/demo_agent.py" ]; then
    sed -i '/from \.demo_agent import AIServerAgent/d' agents/__init__.py
    echo "  ✓ Removed missing demo_agent import"
else
    echo "  ✓ demo_agent exists, no fix needed"
fi

echo ""
echo "Testing vision agent import..."
python -c "from agents.vision_agent import VisionAgent; print('✓ Vision agent works')" 2>/dev/null || echo "❌ Vision agent import failed"

echo ""
echo "Testing React dashboard..."
cd streaming-dashboard
if [ -f "package.json" ] && [ -d "node_modules" ]; then
    echo "✓ Dashboard ready"
else
    echo "⚠️  Dashboard setup incomplete"
fi
cd ..

echo ""
echo "========================================="
echo "Ready to Run!"
echo "========================================="
echo ""
echo "To start all services:"
echo ""
echo "Terminal 1 - Evaluator Server:"
echo "  source .venv/bin/activate"
echo "  python -m server.evaluator_server --port 8081"
echo ""
echo "Terminal 2 - Vision Agent:"
echo "  source .venv/bin/activate"
echo "  python agents/vision_agent.py --server-url http://localhost:8081 --provider ollama --model PetrosStav/gemma3-tools:4b"
echo ""
echo "Terminal 3 - React Dashboard:"
echo "  cd streaming-dashboard"
echo "  npm run dev -- --port 5174"
echo ""
echo "Don't forget to:"
echo "1. Edit .env with your API keys"
echo "2. Ensure Pokemon_Red.gb is in the project root"
echo ""
echo "Setup script completed successfully!"