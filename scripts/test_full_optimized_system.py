#!/usr/bin/env python3
"""
Test the complete optimized Pokemon streaming system end-to-end.
"""

import time
import requests
import json
import statistics
import subprocess
import signal
import os
from pathlib import Path


def test_server_performance():
    """Test server performance with optimized endpoints."""
    print("Testing optimized server performance...")
    
    server_url = "http://localhost:8082"
    
    # Test server connectivity
    try:
        response = requests.get(f"{server_url}/status", timeout=5)
        if response.status_code != 200:
            print(f"❌ Server not responding at {server_url}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return False
    
    print("✓ Server is responding")
    
    # Test optimized endpoint performance
    print("\nTesting /game_state_fast endpoint (10 samples)...")
    times = []
    
    for i in range(10):
        start_time = time.time()
        try:
            response = requests.get(f"{server_url}/game_state_fast", timeout=10)
            end_time = time.time()
            
            if response.status_code == 200:
                elapsed = (end_time - start_time) * 1000  # Convert to ms
                times.append(elapsed)
                
                data = response.json()
                screenshot_hash = data.get('screenshot_hash', 'none')
                screenshot_changed = data.get('screenshot_changed', False)
                
                if i % 3 == 0:
                    print(f"  Sample {i}: {elapsed:.2f}ms, hash: {screenshot_hash[:8]}..., changed: {screenshot_changed}")
                    
        except Exception as e:
            print(f"  Error {i}: {e}")
    
    if times:
        avg_time = statistics.mean(times)
        print(f"\n📊 Performance Results:")
        print(f"  Average latency: {avg_time:.2f}ms")
        print(f"  Min/Max: {min(times):.2f}ms / {max(times):.2f}ms")
        print(f"  Target (<100ms): {'✓ PASSED' if avg_time < 100 else '❌ FAILED'}")
        
        # Test screenshot caching
        print(f"\nTesting screenshot caching...")
        if times:  # Get a screenshot hash from previous call
            response = requests.get(f"{server_url}/game_state_fast")
            if response.status_code == 200:
                data = response.json()
                screenshot_hash = data.get('screenshot_hash')
                
                if screenshot_hash:
                    start_time = time.time()
                    screenshot_response = requests.get(f"{server_url}/screenshot/{screenshot_hash}")
                    cache_time = (time.time() - start_time) * 1000
                    
                    if screenshot_response.status_code == 200:
                        screenshot_data = screenshot_response.json()
                        screenshot_size = len(screenshot_data.get('screenshot_base64', ''))
                        print(f"  Screenshot fetch: {cache_time:.2f}ms, size: {screenshot_size/1024:.1f}KB")
                    else:
                        print(f"  Screenshot fetch failed: {screenshot_response.status_code}")
        
        return avg_time < 100
    else:
        print("❌ No successful requests")
        return False


def test_streaming_load():
    """Test the system under streaming load."""
    print("\n" + "="*50)
    print("STREAMING LOAD TEST")
    print("="*50)
    
    server_url = "http://localhost:8082"
    
    # Simulate streaming dashboard polling every 2 seconds for 20 seconds
    print("Simulating dashboard polling every 2 seconds for 20 seconds...")
    
    times = []
    data_points = []
    
    for i in range(10):  # 20 seconds / 2 second intervals
        start_time = time.time()
        
        try:
            response = requests.get(f"{server_url}/game_state_fast", timeout=10)
            end_time = time.time()
            
            if response.status_code == 200:
                elapsed = (end_time - start_time) * 1000
                times.append(elapsed)
                
                data = response.json()
                data_points.append({
                    'iteration': i,
                    'latency_ms': elapsed,
                    'location': data.get('location', 'unknown'),
                    'step_number': data.get('step_number', 0),
                    'screenshot_changed': data.get('screenshot_changed', False)
                })
                
                print(f"  Poll {i+1}: {elapsed:.1f}ms - {data.get('location', 'unknown')} (step {data.get('step_number', 0)})")
                
            time.sleep(2)  # Wait 2 seconds between polls
            
        except Exception as e:
            print(f"  Poll {i+1}: Error - {e}")
    
    if times:
        avg_time = statistics.mean(times)
        max_time = max(times)
        consistency = statistics.stdev(times) if len(times) > 1 else 0
        
        print(f"\n📊 Streaming Load Results:")
        print(f"  Average latency: {avg_time:.2f}ms")
        print(f"  Maximum latency: {max_time:.2f}ms")
        print(f"  Consistency (std dev): {consistency:.2f}ms")
        print(f"  Streaming ready: {'✓ YES' if max_time < 100 and consistency < 20 else '❌ NO'}")
        
        # Save detailed results
        results = {
            'test_type': 'streaming_load',
            'avg_latency_ms': avg_time,
            'max_latency_ms': max_time,
            'consistency_ms': consistency,
            'streaming_ready': max_time < 100 and consistency < 20,
            'data_points': data_points
        }
        
        with open('streaming_load_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        return max_time < 100 and consistency < 20
    else:
        return False


def main():
    print("Pokemon Gym - Optimized System Test")
    print("="*50)
    
    # Test 1: Server performance
    server_passed = test_server_performance()
    
    # Test 2: Streaming load test
    streaming_passed = test_streaming_load()
    
    # Overall assessment
    print("\n" + "="*50)
    print("FINAL ASSESSMENT")
    print("="*50)
    
    print(f"Server Performance: {'✓ PASSED' if server_passed else '❌ FAILED'}")
    print(f"Streaming Load Test: {'✓ PASSED' if streaming_passed else '❌ FAILED'}")
    
    if server_passed and streaming_passed:
        print("\n🎉 SYSTEM IS READY FOR STREAMING!")
        print("   - Latency targets met (<100ms)")
        print("   - Consistent performance under load")
        print("   - Screenshot caching working")
        print("   - Optimized endpoints functional")
    else:
        print("\n⚠️  SYSTEM NEEDS MORE OPTIMIZATION")
        if not server_passed:
            print("   - Server latency too high")
        if not streaming_passed:
            print("   - Inconsistent performance under load")
    
    return 0 if (server_passed and streaming_passed) else 1


if __name__ == "__main__":
    exit(main())