#!/usr/bin/env python3
"""
Performance benchmark script for Car Wash Mixer
Measures the impact of optimizations on response times, memory usage, and throughput.
"""

import time
import psutil
import requests
import json
import concurrent.futures
import statistics
from pathlib import Path


class PerformanceBenchmark:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.results = {}
        
    def measure_memory_usage(self):
        """Measure current memory usage."""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024  # MB
        
    def measure_response_time(self, endpoint, method="GET", data=None, iterations=10):
        """Measure average response time for an endpoint."""
        times = []
        
        for _ in range(iterations):
            start_time = time.time()
            
            try:
                if method == "GET":
                    response = requests.get(f"{self.base_url}{endpoint}")
                elif method == "POST":
                    response = requests.post(f"{self.base_url}{endpoint}", json=data)
                    
                response.raise_for_status()
                end_time = time.time()
                times.append(end_time - start_time)
                
            except requests.RequestException as e:
                print(f"Request failed: {e}")
                
        if times:
            return {
                "avg_response_time": statistics.mean(times),
                "min_response_time": min(times),
                "max_response_time": max(times),
                "std_dev": statistics.stdev(times) if len(times) > 1 else 0
            }
        return None
        
    def measure_concurrent_throughput(self, endpoint, method="GET", data=None, 
                                    concurrent_requests=10, total_requests=100):
        """Measure throughput under concurrent load."""
        def make_request():
            try:
                if method == "GET":
                    response = requests.get(f"{self.base_url}{endpoint}")
                elif method == "POST":
                    response = requests.post(f"{self.base_url}{endpoint}", json=data)
                response.raise_for_status()
                return True
            except:
                return False
        
        start_time = time.time()
        successful_requests = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            futures = [executor.submit(make_request) for _ in range(total_requests)]
            for future in concurrent.futures.as_completed(futures):
                if future.result():
                    successful_requests += 1
                    
        end_time = time.time()
        total_time = end_time - start_time
        
        return {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "requests_per_second": successful_requests / total_time,
            "total_time": total_time,
            "success_rate": successful_requests / total_requests * 100
        }
        
    def test_compression(self):
        """Test if gzip compression is working."""
        try:
            response = requests.get(f"{self.base_url}/health", 
                                  headers={"Accept-Encoding": "gzip"})
            response.raise_for_status()
            
            compressed = response.headers.get("Content-Encoding") == "gzip"
            content_length = len(response.content)
            
            return {
                "compression_enabled": compressed,
                "response_size_bytes": content_length
            }
        except requests.RequestException:
            return {"compression_enabled": False, "response_size_bytes": 0}
            
    def test_caching(self):
        """Test if caching is working by making identical requests."""
        test_data = {
            "lyrics": "test.lrc",
            "bpm": 120,
            "output": "test_output.json"
        }
        
        # First request (should be processed)
        start_time = time.time()
        try:
            response1 = requests.post(f"{self.base_url}/map-lyrics", json=test_data)
            first_request_time = time.time() - start_time
            
            # Second request (should be cached)
            start_time = time.time()
            response2 = requests.post(f"{self.base_url}/map-lyrics", json=test_data)
            second_request_time = time.time() - start_time
            
            cache_speedup = first_request_time / second_request_time if second_request_time > 0 else 1
            
            return {
                "first_request_time": first_request_time,
                "second_request_time": second_request_time,
                "cache_speedup": cache_speedup,
                "caching_effective": cache_speedup > 1.5  # At least 50% faster
            }
        except requests.RequestException:
            return {"caching_effective": False, "error": "Could not test caching"}
    
    def run_benchmark(self):
        """Run complete performance benchmark."""
        print("🚀 Starting Performance Benchmark for Car Wash Mixer")
        print("=" * 60)
        
        # Test server availability
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            response.raise_for_status()
            print("✓ Server is running and responding")
        except requests.RequestException:
            print("❌ Server is not available. Please start the server first.")
            return
            
        # Initial memory measurement
        initial_memory = self.measure_memory_usage()
        print(f"📊 Initial memory usage: {initial_memory:.2f} MB")
        
        # Test compression
        print("\n🗜️  Testing Compression...")
        compression_results = self.test_compression()
        print(f"   Compression enabled: {compression_results['compression_enabled']}")
        print(f"   Response size: {compression_results['response_size_bytes']} bytes")
        
        # Test response times
        print("\n⏱️  Measuring Response Times...")
        health_check = self.measure_response_time("/health", iterations=20)
        if health_check:
            print(f"   Health check avg: {health_check['avg_response_time']*1000:.2f}ms")
            print(f"   Health check std dev: {health_check['std_dev']*1000:.2f}ms")
        
        # Test throughput
        print("\n🚄 Testing Concurrent Throughput...")
        throughput = self.measure_concurrent_throughput("/health", 
                                                       concurrent_requests=10, 
                                                       total_requests=50)
        print(f"   Requests per second: {throughput['requests_per_second']:.2f}")
        print(f"   Success rate: {throughput['success_rate']:.1f}%")
        
        # Test caching (if available)
        print("\n💾 Testing Caching...")
        cache_results = self.test_caching()
        if "error" not in cache_results:
            print(f"   Cache speedup: {cache_results['cache_speedup']:.2f}x")
            print(f"   Caching effective: {cache_results['caching_effective']}")
        else:
            print(f"   ⚠️  {cache_results['error']}")
        
        # Final memory measurement
        final_memory = self.measure_memory_usage()
        print(f"\n📊 Final memory usage: {final_memory:.2f} MB")
        print(f"📊 Memory delta: {final_memory - initial_memory:+.2f} MB")
        
        # Compile results
        self.results = {
            "timestamp": time.time(),
            "memory": {
                "initial_mb": initial_memory,
                "final_mb": final_memory,
                "delta_mb": final_memory - initial_memory
            },
            "compression": compression_results,
            "response_times": health_check,
            "throughput": throughput,
            "caching": cache_results
        }
        
        # Save results
        results_file = Path("benchmark_results.json")
        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2)
            
        print(f"\n📋 Results saved to {results_file}")
        print("\n✅ Benchmark completed!")
        
        return self.results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Performance benchmark for Car Wash Mixer")
    parser.add_argument("--url", default="http://localhost:5000", 
                       help="Base URL of the server (default: http://localhost:5000)")
    
    args = parser.parse_args()
    
    benchmark = PerformanceBenchmark(args.url)
    benchmark.run_benchmark()