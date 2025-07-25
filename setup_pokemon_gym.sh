#!/bin/bash

# Pokemon Gym Setup Script
# This script sets up a fresh clone of the pokemon-gym repository

set -e  # Exit on error

echo "========================================="
echo "Pokemon Gym Setup Script"
echo "========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "Error: This script must be run from the pokemon-gym directory"
    exit 1
fi

echo "Step 1: Setting up Python virtual environment..."
if [ ! -d ".venv" ]; then
    python3.11 -m venv .venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
source .venv/bin/activate

echo ""
echo "Step 2: Upgrading pip..."
pip install --upgrade pip --quiet

echo ""
echo "Step 3: Installing Python dependencies..."
pip install -r requirements.txt --quiet
echo "✓ Python dependencies installed"

echo ""
echo "Step 4: Setting up environment variables..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✓ Created .env file from template"
    echo "⚠️  Please edit .env and add your API keys"
else
    echo "✓ .env file already exists"
fi

echo ""
echo "Step 5: Checking for Pokemon ROM..."
if [ ! -f "Pokemon_Red.gb" ]; then
    # Try to find ROM in parent directories
    ROM_PATH=$(find ../.. -name "Pokemon_Red.gb" -type f | head -1)
    if [ -n "$ROM_PATH" ]; then
        cp "$ROM_PATH" .
        echo "✓ Copied Pokemon ROM from $ROM_PATH"
    else
        echo "⚠️  Pokemon_Red.gb not found. Please place it in the project root."
    fi
else
    echo "✓ Pokemon ROM already present"
fi

echo ""
echo "Step 6: Setting up React streaming dashboard..."
cd streaming-dashboard

# Check if dashboard files exist
if [ ! -f "package.json" ]; then
    echo "⚠️  Streaming dashboard is empty. Copying from existing installation..."
    # Try to find a populated streaming-dashboard
    DASHBOARD_PATH=$(find ../../.. -path "*/pokemon-gym*/streaming-dashboard/package.json" -type f | head -1)
    if [ -n "$DASHBOARD_PATH" ]; then
        DASHBOARD_DIR=$(dirname "$DASHBOARD_PATH")
        cp -r "$DASHBOARD_DIR"/* .
        echo "✓ Copied dashboard files from $DASHBOARD_DIR"
    else
        echo "❌ Could not find streaming dashboard files"
    fi
fi

# Install dependencies
if [ -f "package.json" ]; then
    echo "Installing React dependencies..."
    if command -v yarn &> /dev/null; then
        yarn install
    else
        npm install
    fi
    echo "✓ React dependencies installed"
else
    echo "⚠️  No package.json found in streaming-dashboard"
fi

cd ..

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "To run the system:"
echo ""
echo "1. Edit .env file with your API keys (if not already done)"
echo ""
echo "2. Terminal 1 - Start the evaluator server:"
echo "   source .venv/bin/activate"
echo "   python -m server.evaluator_server"
echo ""
echo "3. Terminal 2 - Start an agent:"
echo "   source .venv/bin/activate"
echo "   python agents/demo_agent.py --provider ollama --model PetrosStav/gemma3-tools:4b"
echo "   # OR for vision agent:"
echo "   python agents/vision_agent.py --provider ollama --model PetrosStav/gemma3-tools:4b"
echo ""
echo "4. Terminal 3 - Start React dashboard (optional):"
echo "   cd streaming-dashboard"
echo "   npm run dev"
echo ""
echo "For streaming setup with all components:"
echo "   ./run_streaming.sh"
echo ""