#!/usr/bin/env python3
"""
Bayesian-AGI-Core Load Testing Script
This script provides comprehensive performance testing capabilities
using multiple approaches: simple load test, Locust-ready, and advanced.
"""

import asyncio
import time
import random
import statistics
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    print("⚠️  httpx not installed - install with: pip install httpx")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


@dataclass
class RequestResult:
    """Result of a single request"""
    request_id: int
    timestamp: str
    url: str
    method: str
    status_code: Optional[int] = None
    latency_ms: float = 0.0
    success: bool = False
    error_message: Optional[str] = None
    trace_id: Optional[str] = None


@dataclass
class LoadTestResult:
    """Result of a load test run"""
    test_name: str
    start_time: str
    end_time: str
    duration_seconds: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    requests_per_second: float
    latency_avg_ms: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    latency_min_ms: float
    latency_max_ms: float
    results: List[RequestResult]


class LoadTester:
    """Load testing client"""

    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.results: List[RequestResult] = []

    async def make_request(self, request_id: int, url: str, method: str = "GET",
                         data: Optional[Dict] = None) -> RequestResult:
        """Make a single HTTP request"""
        start_time = time.time()
        result = RequestResult(
            request_id=request_id,
            timestamp=datetime.utcnow().isoformat(),
            url=url,
            method=method
        )

        try:
            if not HTTPX_AVAILABLE:
                raise ImportError("httpx library required")

            async with httpx.AsyncClient(timeout=30.0) as client:
                if method.upper() == "GET":
                    response = await client.get(url)
                elif method.upper() == "POST":
                    response = await client.post(url, json=data)
                else:
                    raise ValueError(f"Unsupported method: {method}")

                result.status_code = response.status_code
                result.success = 200 <= response.status_code < 300
                result.trace_id = response.headers.get("X-Trace-ID")

        except Exception as e:
            result.success = False
            result.error_message = str(e)

        end_time = time.time()
        result.latency_ms = (end_time - start_time) * 1000

        return result

    async def run_concurrent_test(self, test_name: str, num_requests: int,
                                 concurrency: int, endpoint: str = "/health") -> LoadTestResult:
        """Run a concurrent load test"""
        url = f"{self.base_url}{endpoint}"
        print(f"\n🚀 Starting Load Test: {test_name}")
        print(f"   Total Requests: {num_requests}")
        print(f"   Concurrency: {concurrency}")
        print(f"   Target: {url}")

        self.results = []
        start_time = time.time()

        semaphore = asyncio.Semaphore(concurrency)

        async def worker(request_id: int):
            async with semaphore:
                result = await self.make_request(request_id, url)
                self.results.append(result)
                if request_id % 100 == 0:
                    print(f"   ⏳ Completed {request_id}/{num_requests} requests...")

        tasks = [worker(i) for i in range(num_requests)]
        await asyncio.gather(*tasks)

        end_time = time.time()
        return self._analyze_results(test_name, start_time, end_time)

    async def run_spike_test(self, test_name: str, base_requests: int = 50,
                           spike_requests: int = 500, spike_duration: int = 10) -> LoadTestResult:
        """Run a spike test (sudden traffic increase)"""
        print(f"\n⚡ Starting Spike Test: {test_name}")
        print(f"   Baseline: {base_requests} req")
        print(f"   Spike: {spike_requests} req in {spike_duration}s")

        self.results = []
        start_time = time.time()

        url = f"{self.base_url}/health"

        # Phase 1: Baseline
        print("   Phase 1: Baseline traffic...")
        baseline_tasks = [self.make_request(i, url) for i in range(base_requests)]
        baseline_results = await asyncio.gather(*baseline_tasks)
        self.results.extend(baseline_results)

        # Phase 2: Spike
        print(f"   Phase 2: Spike ({spike_requests} req)...")
        spike_tasks = [self.make_request(base_requests + i, url)
                      for i in range(spike_requests)]
        spike_results = await asyncio.gather(*spike_tasks)
        self.results.extend(spike_results)

        # Phase 3: Cool down
        print("   Phase 3: Cooldown...")
        cooldown_tasks = [self.make_request(base_requests + spike_requests + i, url)
                         for i in range(base_requests)]
        cooldown_results = await asyncio.gather(*cooldown_tasks)
        self.results.extend(cooldown_results)

        end_time = time.time()
        return self._analyze_results(test_name, start_time, end_time)

    async def run_stress_test(self, test_name: str, max_concurrency: int = 200,
                            step_size: int = 20, duration_per_step: int = 10) -> LoadTestResult:
        """Run a stress test with increasing load"""
        print(f"\n🔥 Starting Stress Test: {test_name}")
        print(f"   Max Concurrency: {max_concurrency}")
        print(f"   Step Size: {step_size}")

        self.results = []
        start_time = time.time()
        url = f"{self.base_url}/health"
        request_counter = 0

        for concurrency in range(step_size, max_concurrency + 1, step_size):
            print(f"   Testing with concurrency: {concurrency}")

            num_requests = concurrency * (duration_per_step // 2)
            semaphore = asyncio.Semaphore(concurrency)

            async def worker(worker_id: int):
                async with semaphore:
                    nonlocal request_counter
                    result = await self.make_request(request_counter, url)
                    self.results.append(result)
                    request_counter += 1

            tasks = [worker(i) for i in range(num_requests)]
            await asyncio.gather(*tasks)

        end_time = time.time()
        return self._analyze_results(test_name, start_time, end_time)

    async def run_endurance_test(self, test_name: str, duration_minutes: int = 5,
                                requests_per_minute: int = 60) -> LoadTestResult:
        """Run an endurance test over a long period"""
        print(f"\n🏃 Starting Endurance Test: {test_name}")
        print(f"   Duration: {duration_minutes} minutes")
        print(f"   Rate: {requests_per_minute} req/min")

        self.results = []
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        request_counter = 0
        url = f"{self.base_url}/health"

        while time.time() < end_time:
            await asyncio.sleep(60 / requests_per_minute)
            result = await self.make_request(request_counter, url)
            self.results.append(result)
            request_counter += 1

            if request_counter % 100 == 0:
                elapsed = time.time() - start_time
                print(f"   ⏱️  {int(elapsed/60)}min elapsed, {request_counter} requests")

        return self._analyze_results(test_name, start_time, time.time())

    def _analyze_results(self, test_name: str, start_time: float,
                       end_time: float) -> LoadTestResult:
        """Analyze test results"""
        duration = end_time - start_time
        latencies = [r.latency_ms for r in self.results]
        successful = sum(1 for r in self.results if r.success)
        failed = len(self.results) - successful

        if latencies:
            avg_latency = statistics.mean(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)

            if NUMPY_AVAILABLE:
                p50 = np.percentile(latencies, 50)
                p95 = np.percentile(latencies, 95)
                p99 = np.percentile(latencies, 99)
            else:
                sorted_latencies = sorted(latencies)
                n = len(sorted_latencies)
                p50 = sorted_latencies[int(n * 0.5)]
                p95 = sorted_latencies[int(n * 0.95)] if n > 20 else sorted_latencies[-1]
                p99 = sorted_latencies[int(n * 0.99)] if n > 100 else sorted_latencies[-1]
        else:
            avg_latency = min_latency = max_latency = p50 = p95 = p99 = 0.0

        return LoadTestResult(
            test_name=test_name,
            start_time=datetime.fromtimestamp(start_time).isoformat(),
            end_time=datetime.fromtimestamp(end_time).isoformat(),
            duration_seconds=duration,
            total_requests=len(self.results),
            successful_requests=successful,
            failed_requests=failed,
            success_rate=(successful / len(self.results) * 100) if self.results else 0,
            requests_per_second=len(self.results) / duration if duration > 0 else 0,
            latency_avg_ms=avg_latency,
            latency_p50_ms=p50,
            latency_p95_ms=p95,
            latency_p99_ms=p99,
            latency_min_ms=min_latency,
            latency_max_ms=max_latency,
            results=self.results
        )


def print_result_summary(result: LoadTestResult):
    """Print a human-readable summary"""
    print("\n" + "="*80)
    print(f"📊 LOAD TEST RESULTS: {result.test_name}")
    print("="*80)
    print(f"Duration: {result.duration_seconds:.2f}s")
    print(f"Total Requests: {result.total_requests}")
    print(f"Successful: {result.successful_requests}")
    print(f"Failed: {result.failed_requests}")
    print(f"Success Rate: {result.success_rate:.2f}%")
    print(f"Throughput: {result.requests_per_second:.2f} req/s")
    print("\nLatency:")
    print(f"  Avg: {result.latency_avg_ms:.2f}ms")
    print(f"  Min: {result.latency_min_ms:.2f}ms")
    print(f"  Max: {result.latency_max_ms:.2f}ms")
    print(f"  P50: {result.latency_p50_ms:.2f}ms")
    print(f"  P95: {result.latency_p95_ms:.2f}ms")
    print(f"  P99: {result.latency_p99_ms:.2f}ms")
    print("="*80 + "\n")


def save_result_to_file(result: LoadTestResult, filename: Optional[str] = None):
    """Save results to JSON file"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"load_test_{result.test_name}_{timestamp}.json"

    # Don't save all request results in the JSON for large tests
    result_dict = asdict(result)
    if len(result.results) > 1000:
        result_dict["results"] = "Truncated - too many results"

    with open(filename, "w") as f:
        json.dump(result_dict, f, indent=2)

    print(f"💾 Results saved to: {filename}")
    return filename


async def main():
    """Run all load tests"""
    print("="*80)
    print("🚀 BAYESIAN-AGI-CORE - LOAD TESTING")
    print("="*80)

    if not HTTPX_AVAILABLE:
        print("❌ httpx library is required. Install with:")
        print("   pip install httpx")
        return

    tester = LoadTester()

    # Quick smoke test
    print("\n" + "="*80)
    print("1️⃣  SMOKE TEST - Quick verification")
    result = await tester.run_concurrent_test(
        "smoke_test",
        num_requests=20,
        concurrency=5
    )
    print_result_summary(result)
    save_result_to_file(result)

    if result.success_rate < 95:
        print("⚠️  Smoke test failed - please check the service is running")
        return

    # Normal load test
    print("\n" + "="*80)
    print("2️⃣  NORMAL LOAD TEST - Typical traffic")
    result = await tester.run_concurrent_test(
        "normal_load",
        num_requests=200,
        concurrency=20
    )
    print_result_summary(result)
    save_result_to_file(result)

    # Spike test
    print("\n" + "="*80)
    print("3️⃣  SPIKE TEST - Sudden traffic burst")
    result = await tester.run_spike_test(
        "spike_test",
        base_requests=20,
        spike_requests=200,
        spike_duration=5
    )
    print_result_summary(result)
    save_result_to_file(result)

    # Stress test (optional - takes longer)
    print("\n" + "="*80)
    print("4️⃣  STRESS TEST - Find breaking point (quick version)")
    result = await tester.run_stress_test(
        "stress_test",
        max_concurrency=50,
        step_size=10,
        duration_per_step=5
    )
    print_result_summary(result)
    save_result_to_file(result)

    print("\n" + "="*80)
    print("✅ ALL TESTS COMPLETED!")
    print("="*80)
    print("\n💡 Next steps:")
    print("   - Review the JSON result files")
    print("   - Check logs/app.log for detailed trace information")
    print("   - Check rate limiter statistics via API")
    print("   - Use Locust for advanced distributed testing")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
