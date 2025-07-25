#!/usr/bin/env python3
"""
Test the optimized game state endpoints for performance improvements.
"""

import time
import requests
import json
import statistics


def test_endpoint_performance(endpoint_url: str, endpoint_name: str, iterations: int = 10) -> dict:
    """Test an endpoint and return performance metrics."""
    print(f"\nTesting {endpoint_name} ({iterations} iterations)...")
    
    times = []
    sizes = []
    
    for i in range(iterations):
        start_time = time.time()
        try:
            response = requests.get(endpoint_url, timeout=10)
            end_time = time.time()
            
            if response.status_code == 200:
                elapsed = (end_time - start_time) * 1000  # Convert to ms
                times.append(elapsed)
                
                # Get response size
                response_size = len(response.content)
                sizes.append(response_size)
                
                if i % 5 == 0:
                    print(f"  Iteration {i}: {elapsed:.2f}ms, {response_size} bytes")
            else:
                print(f"  Error {i}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"  Error {i}: {e}")
    
    if times:
        return {
            "endpoint": endpoint_name,
            "samples": len(times),
            "avg_time_ms": statistics.mean(times),
            "min_time_ms": min(times),
            "max_time_ms": max(times),
            "std_dev_ms": statistics.stdev(times) if len(times) > 1 else 0,
            "avg_size_bytes": statistics.mean(sizes),
            "total_size_kb": sum(sizes) / 1024
        }
    else:
        return {"endpoint": endpoint_name, "error": "No successful requests"}


def main():
    server_url = "http://localhost:8082"
    
    # Test server connectivity
    try:
        response = requests.get(f"{server_url}/status", timeout=5)
        if response.status_code != 200:
            print(f"Server not responding at {server_url}")
            return
    except Exception as e:
        print(f"Cannot connect to server: {e}")
        return
    
    print("Testing Pokemon Server Optimized Endpoints")
    print("=" * 50)
    
    # Test different endpoints
    endpoints = [
        (f"{server_url}/game_state", "Original /game_state"),
        (f"{server_url}/game_state_fast", "Optimized /game_state_fast"),
        (f"{server_url}/game_state_no_screenshot", "No Screenshot /game_state_no_screenshot"),
    ]
    
    results = []
    
    for url, name in endpoints:
        result = test_endpoint_performance(url, name, iterations=10)
        results.append(result)
    
    # Print comparison
    print("\n" + "=" * 50)
    print("PERFORMANCE COMPARISON")
    print("=" * 50)
    
    for result in results:
        if "error" not in result:
            endpoint = result["endpoint"]
            avg_time = result["avg_time_ms"]
            avg_size = result["avg_size_bytes"]
            target_met = "✓" if avg_time < 100 else "❌"
            
            print(f"\n{endpoint}:")
            print(f"  Average latency: {avg_time:.2f}ms {target_met}")
            print(f"  Response size: {avg_size/1024:.1f}KB")
            print(f"  Min/Max: {result['min_time_ms']:.2f}ms / {result['max_time_ms']:.2f}ms")
        else:
            print(f"\n{result['endpoint']}: {result['error']}")
    
    # Save results
    with open("optimized_endpoint_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to optimized_endpoint_results.json")
    
    # Summary
    successful_results = [r for r in results if "error" not in r]
    if successful_results:
        fastest = min(successful_results, key=lambda x: x["avg_time_ms"])
        smallest = min(successful_results, key=lambda x: x["avg_size_bytes"])
        
        print(f"\nFastest endpoint: {fastest['endpoint']} ({fastest['avg_time_ms']:.2f}ms)")
        print(f"Smallest response: {smallest['endpoint']} ({smallest['avg_size_bytes']/1024:.1f}KB)")
        
        target_met = any(r["avg_time_ms"] < 100 for r in successful_results)
        print(f"\n<100ms Target: {'✓ MET' if target_met else '❌ NOT MET'}")


if __name__ == "__main__":
    main()