#!/bin/bash

# Check if PID file exists
if [ ! -f pokemon_pids.txt ]; then
    echo "pokemon_pids.txt file not found, cannot stop processes."
    echo "If processes are still running, use ps aux | grep 'evaluator_server\|demo_agent' to find PIDs and terminate manually."
    exit 1
fi

# Read PID file
PIDS=$(cat pokemon_pids.txt)
echo "Found the following processes: $PIDS"

# Stop all processes
echo "Stopping all processes..."
kill $PIDS

# Confirm processes are stopped
sleep 2
for PID in $PIDS; do
    if ps -p $PID > /dev/null; then
        echo "Process $PID is still running, attempting force termination..."
        kill -9 $PID
    fi
done

# Delete PID file
rm pokemon_pids.txt
echo "All processes have been stopped" 