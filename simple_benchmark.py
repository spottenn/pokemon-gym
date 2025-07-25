#!/usr/bin/env python3
"""Simple benchmark script to test Pokemon streaming system performance quickly."""

import time
import requests
import statistics
import json

def test_server_performance():
    server_url = "http://localhost:8082"
    results = {
        "init_streaming_time": None,
        "init_non_streaming_time": None,
        "game_state_times": [],
        "action_times": []
    }
    
    print("Testing Pokemon Streaming System Performance")
    print("=" * 50)
    
    # Test server connectivity
    try:
        response = requests.get(f"{server_url}/status", timeout=5)
        if response.status_code != 200:
            print(f"Error: Server not responding at {server_url}")
            return
    except Exception as e:
        print(f"Error: Cannot connect to server at {server_url}: {e}")
        return
    
    print(f"✓ Connected to server at {server_url}")
    
    # Test initialization times
    print("\n1. Testing initialization times...")
    
    # Test non-streaming initialization
    start_time = time.time()
    response = requests.post(
        f"{server_url}/initialize",
        json={"headless": True, "sound": False, "streaming": False},
        timeout=30
    )
    if response.status_code == 200:
        init_time = (time.time() - start_time) * 1000
        results["init_non_streaming_time"] = init_time
        print(f"  Non-streaming init: {init_time:.2f}ms")
    
    # Test streaming initialization  
    start_time = time.time()
    response = requests.post(
        f"{server_url}/initialize",
        json={"headless": True, "sound": False, "streaming": True},
        timeout=30
    )
    if response.status_code == 200:
        init_time = (time.time() - start_time) * 1000
        results["init_streaming_time"] = init_time
        print(f"  Streaming init: {init_time:.2f}ms")
    
    # Test game state requests
    print("\n2. Testing game state performance (10 requests)...")
    for i in range(10):
        start_time = time.time()
        response = requests.get(f"{server_url}/game_state", timeout=5)
        if response.status_code == 200:
            elapsed = (time.time() - start_time) * 1000
            results["game_state_times"].append(elapsed)
            print(f"  Request {i+1}: {elapsed:.2f}ms")
    
    # Test action requests
    print("\n3. Testing action performance (5 requests)...")
    actions = [
        {"action_type": "press_key", "keys": ["a"]},
        {"action_type": "press_key", "keys": ["up"]},
        {"action_type": "wait", "frames": 30},
    ]
    
    for i in range(5):
        action = actions[i % len(actions)]
        start_time = time.time()
        response = requests.post(
            f"{server_url}/action",
            json=action,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        if response.status_code == 200:
            elapsed = (time.time() - start_time) * 1000
            results["action_times"].append(elapsed)
            print(f"  Action {i+1}: {elapsed:.2f}ms")
    
    # Print summary
    print("\n" + "="*50)
    print("PERFORMANCE SUMMARY")
    print("="*50)
    
    if results["init_non_streaming_time"]:
        print(f"Non-streaming initialization: {results['init_non_streaming_time']:.2f}ms")
    if results["init_streaming_time"]:
        print(f"Streaming initialization: {results['init_streaming_time']:.2f}ms")
    
    if results["game_state_times"]:
        times = results["game_state_times"]
        avg_time = statistics.mean(times)
        print(f"\nGame state requests ({len(times)} samples):")
        print(f"  Average: {avg_time:.2f}ms")
        print(f"  Min:     {min(times):.2f}ms")
        print(f"  Max:     {max(times):.2f}ms")
        
        # Check streaming target
        if avg_time < 100:
            print(f"  ✓ PASSED: Average latency {avg_time:.2f}ms < 100ms target")
        else:
            print(f"  ✗ FAILED: Average latency {avg_time:.2f}ms > 100ms target")
    
    if results["action_times"]:
        times = results["action_times"]
        avg_time = statistics.mean(times)
        print(f"\nAction requests ({len(times)} samples):")
        print(f"  Average: {avg_time:.2f}ms")
        print(f"  Min:     {min(times):.2f}ms")
        print(f"  Max:     {max(times):.2f}ms")
    
    # Save results
    with open("simple_benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to simple_benchmark_results.json")

if __name__ == "__main__":
    test_server_performance()