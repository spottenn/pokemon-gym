#!/usr/bin/env python3
"""
Test script to verify the PyBoy dual instance fix with log capture.
"""
import subprocess
import time
import requests
import json
import os
import tempfile

def test_with_logs():
    """Test the dual PyBoy fix and capture server logs."""
    print("=== Testing PyBoy Dual Instance Fix (with logs) ===\n")
    
    # Create temporary log file
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.log', delete=False) as logfile:
        log_path = logfile.name
    
    print(f"Server logs will be written to: {log_path}")
    
    # Start server with log capture
    print("\n1. Starting evaluator server...")
    with open(log_path, 'w') as log_file:
        server = subprocess.Popen([
            'python', '-m', 'server.evaluator_server', '--port', '8083'
        ], stdout=log_file, stderr=subprocess.STDOUT, cwd=os.getcwd())
    
    try:
        # Wait for server to start
        time.sleep(5)
        
        # Check if server is responding
        try:
            response = requests.get('http://localhost:8083/status', timeout=5)
            if response.status_code != 200:
                print("❌ Server not responding")
                return False
            print("✅ Server started successfully")
        except requests.exceptions.RequestException:
            print("❌ Server not responding")
            return False
        
        # First initialization
        print("\n2. First initialization (streaming mode)...")
        init_payload = {
            "headless": True,
            "sound": False,
            "streaming": True
        }
        
        response = requests.post('http://localhost:8083/initialize', 
                               json=init_payload, timeout=10)
        if response.status_code == 200:
            print("✅ First initialization successful")
        else:
            print(f"❌ First initialization failed: {response.status_code}")
            return False
        
        time.sleep(2)
        
        # Second initialization (should be blocked)
        print("\n3. Second initialization (should be blocked)...")
        response = requests.post('http://localhost:8083/initialize', 
                               json=init_payload, timeout=10)
        if response.status_code == 200:
            print("✅ Second initialization handled")
        else:
            print(f"❌ Second initialization failed: {response.status_code}")
        
        time.sleep(2)
        
        # Read and analyze logs
        print("\n4. Analyzing server logs...")
        with open(log_path, 'r') as f:
            logs = f.read()
        
        # Look for key log messages
        init_messages = []
        warning_messages = []
        
        for line in logs.split('\n'):
            if 'Initializing emulator' in line:
                init_messages.append(line.strip())
            elif 'already initialized' in line:
                warning_messages.append(line.strip())
        
        print("\n=== ANALYSIS ===")
        print(f"Initialization messages found: {len(init_messages)}")
        for msg in init_messages:
            print(f"  {msg}")
        
        print(f"\nWarning messages found: {len(warning_messages)}")
        for msg in warning_messages:
            print(f"  {msg}")
        
        # Determine success
        if len(init_messages) == 1 and len(warning_messages) >= 1:
            print("\n✅ SUCCESS: Found exactly 1 initialization and 1+ warnings")
            print("✅ Fix is working correctly!")
            success = True
        elif len(init_messages) == 1 and len(warning_messages) == 0:
            print("\n⚠️  PARTIAL: Only one initialization (good) but no warning (might be OK)")
            print("   This could happen if the second call was blocked at a higher level")
            success = True
        else:
            print(f"\n❌ FAILURE: Found {len(init_messages)} initializations (expected 1)")
            success = False
        
        return success
            
    finally:
        # Clean up
        print("\n5. Cleaning up...")
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
        
        # Show last few log lines
        print("\n=== Last few server log lines ===")
        with open(log_path, 'r') as f:
            lines = f.readlines()
            for line in lines[-10:]:
                print(f"  {line.strip()}")
        
        # Clean up log file
        os.unlink(log_path)
        print("✅ Cleanup complete")

if __name__ == "__main__":
    import sys
    sys.path.insert(0, '.')
    
    success = test_with_logs()
    sys.exit(0 if success else 1)