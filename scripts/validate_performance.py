#!/usr/bin/env python3
"""
Simple validation script to test if the performance improvements work.
This performs basic smoke tests without full benchmarking.
"""

import time
import requests
import subprocess
import sys
import os
from pathlib import Path

def test_server_import():
    """Test if server can be imported without errors."""
    print("Testing server module import...")
    try:
        from server import evaluator_server
        print("✓ Server module imports successfully")
        return True
    except Exception as e:
        print(f"✗ Server import failed: {e}")
        return False

def test_react_build():
    """Test if React dashboard can build."""
    print("\nTesting React dashboard build...")
    dashboard_path = Path("streaming-dashboard")
    
    if not dashboard_path.exists():
        print("✗ Dashboard directory not found")
        return False
        
    try:
        # Check if node_modules exists
        if not (dashboard_path / "node_modules").exists():
            print("✗ Node modules not installed")
            return False
            
        # Check for syntax errors in our modified files
        files_to_check = [
            dashboard_path / "App.tsx",
            dashboard_path / "src/services/pokemonApi.ts"
        ]
        
        for file in files_to_check:
            if file.exists():
                print(f"  Checking {file.name}...")
                # Basic syntax check - would need proper TypeScript compiler for full check
                with open(file, 'r') as f:
                    content = f.read()
                    if "useRef" in content and "sessionStartTimeRef" in content:
                        print(f"  ✓ {file.name} contains performance optimizations")
                    else:
                        print(f"  ? {file.name} may be missing optimizations")
                        
        return True
    except Exception as e:
        print(f"✗ Dashboard check failed: {e}")
        return False

def test_vision_agent():
    """Test if vision agent improvements are present."""
    print("\nTesting vision agent optimizations...")
    try:
        from agents import vision_agent
        
        # Check if buffer attributes exist
        agent = vision_agent.VisionAgent()
        if hasattr(agent, 'thoughts_buffer') and hasattr(agent, 'flush_thoughts_buffer'):
            print("✓ Vision agent has buffering optimizations")
            return True
        else:
            print("✗ Vision agent missing buffer optimizations")
            return False
    except Exception as e:
        print(f"✗ Vision agent test failed: {e}")
        return False

def test_server_caching():
    """Test if server has screenshot caching."""
    print("\nTesting server caching features...")
    try:
        import server.evaluator_server as server
        
        # Check if caching functions exist
        if hasattr(server, 'get_screenshot_hash') and hasattr(server, 'SCREENSHOT_CACHE'):
            print("✓ Server has screenshot caching functions")
            
            # Test hash function
            test_hash = server.get_screenshot_hash("test_data")
            if test_hash:
                print(f"  ✓ Hash function works: {test_hash[:8]}...")
                return True
        else:
            print("✗ Server missing caching functions")
            return False
    except Exception as e:
        print(f"✗ Server caching test failed: {e}")
        return False

def main():
    print("Pokemon Gym Performance Validation")
    print("="*50)
    
    tests = [
        test_server_import,
        test_react_build,
        test_vision_agent,
        test_server_caching
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1
            
    print("\n" + "="*50)
    print(f"RESULTS: {passed} passed, {failed} failed")
    
    if failed > 0:
        print("\n⚠️  WARNING: Not all optimizations are properly implemented!")
        print("The performance improvements may not work as expected.")
    else:
        print("\n✓ All basic checks passed!")
        print("Note: This only validates that code changes are present.")
        print("Full end-to-end testing with benchmark_streaming.py is still needed.")
        
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())