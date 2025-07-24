#!/usr/bin/env python3
"""
Test script to verify the PyBoy dual instance fix.
Simulates what happens when server starts and vision agent connects.
"""
import subprocess
import time
import requests
import json
import os
import signal

def count_pyboy_processes():
    """Count processes that contain PyBoy or are running the evaluator server."""
    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
    lines = result.stdout.split('\n')
    count = 0
    for line in lines:
        if ('server.evaluator_server' in line or 'PyBoy' in line) and 'grep' not in line:
            count += 1
            print(f"  Process: {line}")
    return count

def test_dual_pyboy_fix():
    """Test the dual PyBoy instance fix."""
    print("=== Testing PyBoy Dual Instance Fix ===\n")
    
    # Start server
    print("1. Starting evaluator server...")
    server = subprocess.Popen([
        'python', '-m', 'server.evaluator_server', '--port', '8082'
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=os.getcwd())
    
    try:
        # Wait for server to start
        time.sleep(5)
        
        # Check if server is responding
        try:
            response = requests.get('http://localhost:8082/status', timeout=5)
            if response.status_code != 200:
                print("❌ Server not responding")
                return False
            print("✅ Server started successfully")
        except requests.exceptions.RequestException:
            print("❌ Server not responding")
            return False
        
        # Count initial processes
        print("\n2. Checking initial process count...")
        initial_count = count_pyboy_processes()
        print(f"   Initial process count: {initial_count}")
        
        # Simulate vision agent connecting - call initialize
        print("\n3. Simulating vision agent initialization...")
        init_payload = {
            "headless": True,
            "sound": False,
            "streaming": True
        }
        
        response = requests.post('http://localhost:8082/initialize', 
                               json=init_payload, timeout=10)
        if response.status_code == 200:
            print("✅ First initialization successful")
        else:
            print(f"❌ First initialization failed: {response.status_code}")
            return False
        
        # Wait a moment
        time.sleep(2)
        
        # Count processes after first init
        print("\n4. Checking process count after first initialization...")
        after_first_count = count_pyboy_processes()
        print(f"   Process count after first init: {after_first_count}")
        
        # Simulate second initialization (should be blocked)
        print("\n5. Attempting duplicate initialization...")
        response = requests.post('http://localhost:8082/initialize', 
                               json=init_payload, timeout=10)
        if response.status_code == 200:
            print("✅ Second initialization handled (should be blocked internally)")
        else:
            print(f"❌ Second initialization failed: {response.status_code}")
            return False
        
        # Wait a moment
        time.sleep(2)
        
        # Count final processes
        print("\n6. Checking final process count...")
        final_count = count_pyboy_processes()
        print(f"   Final process count: {final_count}")
        
        # Analyze results
        print("\n=== RESULTS ===")
        print(f"Initial processes: {initial_count}")
        print(f"After first init: {after_first_count}")  
        print(f"After second init: {final_count}")
        
        if final_count == after_first_count:
            print("✅ SUCCESS: Process count unchanged on duplicate initialization")
            print("✅ Fix is working correctly!")
            return True
        else:
            print("❌ FAILURE: Process count increased on duplicate initialization")
            print("❌ Fix may not be working")
            return False
            
    finally:
        # Clean up
        print("\n7. Cleaning up...")
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
        print("✅ Server stopped")

if __name__ == "__main__":
    import sys
    sys.path.insert(0, '.')
    
    # Activate virtual environment
    activate_script = os.path.join('.venv', 'bin', 'activate')
    if os.path.exists(activate_script):
        print("Using virtual environment")
    
    success = test_dual_pyboy_fix()
    sys.exit(0 if success else 1)