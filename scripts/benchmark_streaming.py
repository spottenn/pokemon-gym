#!/usr/bin/env python3
"""
Performance benchmark script for Pokemon streaming system.
Tests server response times, React dashboard fetch patterns, and overall latency.
"""

import time
import requests
import statistics
import json
import asyncio
import aiohttp
from typing import List, Dict, Tuple
import argparse


class StreamingBenchmark:
    def __init__(self, server_url: str = "http://localhost:8081"):
        self.server_url = server_url
        self.results = {
            "game_state_times": [],
            "screenshot_fetch_times": [],
            "action_times": [],
            "cache_hits": 0,
            "cache_misses": 0,
        }
        
    async def benchmark_game_state(self, session: aiohttp.ClientSession, iterations: int = 100) -> None:
        """Benchmark /game_state endpoint performance."""
        print(f"Benchmarking /game_state endpoint ({iterations} iterations)...")
        
        screenshot_hashes = set()
        
        for i in range(iterations):
            start_time = time.time()
            
            async with session.get(f"{self.server_url}/game_state") as response:
                if response.status == 200:
                    data = await response.json()
                    elapsed = time.time() - start_time
                    self.results["game_state_times"].append(elapsed)
                    
                    # Track screenshot hashes for cache testing
                    if "screenshot_hash" in data:
                        screenshot_hashes.add(data["screenshot_hash"])
                    
                    if i % 20 == 0:
                        print(f"  Iteration {i}: {elapsed*1000:.2f}ms")
                        
        print(f"  Unique screenshot hashes: {len(screenshot_hashes)}")
        
    async def benchmark_screenshot_cache(self, session: aiohttp.ClientSession) -> None:
        """Test screenshot caching performance."""
        print("\nBenchmarking screenshot cache...")
        
        # First, get a game state to get a screenshot hash
        async with session.get(f"{self.server_url}/game_state") as response:
            if response.status == 200:
                data = await response.json()
                if "screenshot_hash" in data:
                    screenshot_hash = data["screenshot_hash"]
                    
                    # Test cache hit
                    start_time = time.time()
                    async with session.get(f"{self.server_url}/screenshot/{screenshot_hash}") as resp:
                        if resp.status == 200:
                            elapsed = time.time() - start_time
                            self.results["screenshot_fetch_times"].append(elapsed)
                            self.results["cache_hits"] += 1
                            print(f"  Cache hit time: {elapsed*1000:.2f}ms")
                            
                    # Test cache miss (fake hash)
                    start_time = time.time()
                    async with session.get(f"{self.server_url}/screenshot/fakehash123") as resp:
                        if resp.status == 404:
                            elapsed = time.time() - start_time
                            self.results["cache_misses"] += 1
                            print(f"  Cache miss time: {elapsed*1000:.2f}ms")
                            
    async def benchmark_actions(self, session: aiohttp.ClientSession, iterations: int = 50) -> None:
        """Benchmark action processing times."""
        print(f"\nBenchmarking action processing ({iterations} iterations)...")
        
        actions = [
            {"action_type": "press_key", "keys": ["a"]},
            {"action_type": "press_key", "keys": ["up"]},
            {"action_type": "wait", "frames": 30},
        ]
        
        for i in range(iterations):
            action = actions[i % len(actions)]
            start_time = time.time()
            
            async with session.post(
                f"{self.server_url}/action",
                json=action,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    elapsed = time.time() - start_time
                    self.results["action_times"].append(elapsed)
                    
                    if i % 10 == 0:
                        print(f"  Iteration {i}: {elapsed*1000:.2f}ms")
                        
    def print_summary(self) -> None:
        """Print benchmark summary statistics."""
        print("\n" + "="*60)
        print("BENCHMARK SUMMARY")
        print("="*60)
        
        if self.results["game_state_times"]:
            times = self.results["game_state_times"]
            print(f"\n/game_state endpoint ({len(times)} requests):")
            print(f"  Average: {statistics.mean(times)*1000:.2f}ms")
            print(f"  Median:  {statistics.median(times)*1000:.2f}ms")
            print(f"  Min:     {min(times)*1000:.2f}ms")
            print(f"  Max:     {max(times)*1000:.2f}ms")
            print(f"  Std Dev: {statistics.stdev(times)*1000:.2f}ms")
            
        if self.results["action_times"]:
            times = self.results["action_times"]
            print(f"\n/action endpoint ({len(times)} requests):")
            print(f"  Average: {statistics.mean(times)*1000:.2f}ms")
            print(f"  Median:  {statistics.median(times)*1000:.2f}ms")
            print(f"  Min:     {min(times)*1000:.2f}ms")
            print(f"  Max:     {max(times)*1000:.2f}ms")
            
        if self.results["screenshot_fetch_times"]:
            times = self.results["screenshot_fetch_times"]
            print(f"\nScreenshot cache performance:")
            print(f"  Cache hits:   {self.results['cache_hits']}")
            print(f"  Cache misses: {self.results['cache_misses']}")
            print(f"  Fetch time:   {statistics.mean(times)*1000:.2f}ms")
            
        # Check if we meet streaming latency targets
        print(f"\nStreaming Latency Target: < 100ms")
        if self.results["game_state_times"]:
            avg_latency = statistics.mean(self.results["game_state_times"]) * 1000
            if avg_latency < 100:
                print(f"✓ PASSED: Average latency {avg_latency:.2f}ms")
            else:
                print(f"✗ FAILED: Average latency {avg_latency:.2f}ms")
                
    async def run_benchmark(self, game_state_iterations: int = 100, action_iterations: int = 50) -> None:
        """Run the complete benchmark suite."""
        # Check server connectivity
        try:
            response = requests.get(f"{self.server_url}/status")
            if response.status_code != 200:
                print(f"Error: Server not responding at {self.server_url}")
                return
        except Exception as e:
            print(f"Error: Cannot connect to server at {self.server_url}: {e}")
            return
            
        print(f"Connected to server at {self.server_url}")
        
        # Initialize environment
        print("\nInitializing environment...")
        response = requests.post(
            f"{self.server_url}/initialize",
            json={"headless": True, "sound": False, "streaming": True}
        )
        
        if response.status_code != 200:
            print(f"Error initializing environment: {response.text}")
            return
            
        # Run benchmarks
        async with aiohttp.ClientSession() as session:
            await self.benchmark_game_state(session, game_state_iterations)
            await self.benchmark_screenshot_cache(session)
            await self.benchmark_actions(session, action_iterations)
            
        # Print results
        self.print_summary()
        
        # Save results to file
        with open("benchmark_results.json", "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\nDetailed results saved to benchmark_results.json")


async def main():
    parser = argparse.ArgumentParser(description="Benchmark Pokemon streaming system performance")
    parser.add_argument("--server-url", default="http://localhost:8081", help="Server URL")
    parser.add_argument("--game-state-iterations", type=int, default=100, help="Number of game state requests")
    parser.add_argument("--action-iterations", type=int, default=50, help="Number of action requests")
    
    args = parser.parse_args()
    
    benchmark = StreamingBenchmark(args.server_url)
    await benchmark.run_benchmark(args.game_state_iterations, args.action_iterations)


if __name__ == "__main__":
    asyncio.run(main())