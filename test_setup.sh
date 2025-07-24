#!/bin/bash

# Test script to verify Pokemon Gym setup

echo "========================================="
echo "Pokemon Gym Setup Test"
echo "========================================="
echo ""

# Activate virtual environment
source .venv/bin/activate

echo "1. Testing evaluator server..."
python -m server.evaluator_server --port 8081 &
SERVER_PID=$!
sleep 5

# Test server endpoint
if curl -s http://localhost:8081/ > /dev/null 2>&1; then
    echo "✓ Server is running"
else
    echo "❌ Server not responding"
fi

# Kill server
kill $SERVER_PID 2>/dev/null

echo ""
echo "2. Testing vision agent..."
# Just test import
python -c "from agents.vision_agent import VisionAgent; print('✓ Vision agent imports successfully')" || echo "❌ Vision agent import failed"

echo ""
echo "3. Testing React dashboard..."
cd streaming-dashboard
if [ -f "package.json" ]; then
    echo "✓ Dashboard files present"
    # Test if dependencies are installed
    if [ -d "node_modules" ]; then
        echo "✓ Dependencies installed"
    else
        echo "⚠️  Dependencies not installed"
    fi
else
    echo "❌ Dashboard files missing"
fi
cd ..

echo ""
echo "4. Checking ROM file..."
if [ -f "Pokemon_Red.gb" ]; then
    echo "✓ ROM file present"
else
    echo "❌ ROM file missing"
fi

echo ""
echo "5. Checking environment file..."
if [ -f ".env" ]; then
    echo "✓ .env file present"
    # Check for API keys
    if grep -q "ANTHROPIC_API_KEY=" .env && ! grep -q "ANTHROPIC_API_KEY=$" .env; then
        echo "✓ ANTHROPIC_API_KEY appears to be set"
    else
        echo "⚠️  ANTHROPIC_API_KEY not set"
    fi
else
    echo "❌ .env file missing"
fi

echo ""
echo "========================================="
echo "Test complete!"
echo "========================================="