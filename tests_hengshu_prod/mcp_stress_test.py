#!/usr/bin/env python3
"""
MCP 服务并发压测脚本
测试多 WebSocket 长连接下 MCP 工具调用稳定性
版本: 1.0.0
"""
import asyncio
import time
import json
import random
import statistics
import os
from typing import List, Dict
from dataclasses import dataclass
from datetime import datetime

@dataclass
class TestResult:
    """测试结果"""
    connection_id: int
    success: bool
    latency_ms: float
    error: str = ""

class MCPStressTester:
    """MCP 压测器"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8090):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.results: List[TestResult] = []
        
    async def test_single_connection(self, conn_id: int, num_requests: int = 10) -> List[TestResult]:
        """测试单个连接的多次请求"""
        results = []
        import aiohttp
        
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for req_id in range(num_requests):
                start_time = time.time()
                try:
                    payload = {
                        "jsonrpc": "2.0",
                        "id": f"conn_{conn_id}_req_{req_id}",
                        "method": "tools/list"
                    }
                    
                    async with session.post(
                        f"{self.base_url}/mcp",
                        json=payload,
                        headers={"Content-Type": "application/json"}
                    ) as response:
                        data = await response.json()
                        success = response.status == 200 and "result" in data
                        
                        latency = (time.time() - start_time) * 1000
                        results.append(TestResult(
                            connection_id=conn_id,
                            success=success,
                            latency_ms=latency,
                            error="" if success else f"HTTP {response.status}"
                        ))
                        
                except Exception as e:
                    latency = (time.time() - start_time) * 1000
                    results.append(TestResult(
                        connection_id=conn_id,
                        success=False,
                        latency_ms=latency,
                        error=str(e)[:100]
                    ))
                
                await asyncio.sleep(random.uniform(0.01, 0.1))
        
        return results
    
    async def run_stress_test(self, num_connections: int = 50, requests_per_conn: int = 10):
        """运行并发压测"""
        print("=" * 70)
        print(" MCP 并发压测开始")
        print("=" * 70)
        print(f"  并发连接数: {num_connections}")
        print(f"  单连接请求数: {requests_per_conn}")
        print(f"  总请求数: {num_connections * requests_per_conn}")
        print(f"  目标服务: {self.base_url}")
        print("=" * 70)
        print()
        
        start_time = time.time()
        
        tasks = [
            self.test_single_connection(i, requests_per_conn)
            for i in range(num_connections)
        ]
        
        all_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for results in all_results:
            if isinstance(results, list):
                self.results.extend(results)
        
        total_time = time.time() - start_time
        self.generate_report(total_time, num_connections, requests_per_conn)
    
    def generate_report(self, total_time: float, num_connections: int, requests_per_conn: int):
        """生成测试报告"""
        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]
        latencies = [r.latency_ms for r in successful]
        
        print()
        print("=" * 70)
        print(" 压测报告")
        print("=" * 70)
        print()
        print(f"  总耗时: {total_time:.2f} 秒")
        print(f"  总请求: {len(self.results)}")
        print(f"  成功: {len(successful)}")
        print(f"  失败: {len(failed)}")
        print(f"  成功率: {len(successful)/len(self.results)*100:.2f}%")
        print()
        print("  延迟统计 (毫秒):")
        if latencies:
            print(f"     平均: {statistics.mean(latencies):.2f} ms")
            print(f"     中位数: {statistics.median(latencies):.2f} ms")
            print(f"     P95: {sorted(latencies)[int(len(latencies)*0.95)]:.2f} ms")
            print(f"     P99: {sorted(latencies)[int(len(latencies)*0.99)]:.2f} ms")
            print(f"     最小: {min(latencies):.2f} ms")
            print(f"     最大: {max(latencies):.2f} ms")
        print()
        print(f"  吞吐量: {len(self.results)/total_time:.2f} 请求/秒")
        print()
        
        if failed:
            print("  失败请求统计:")
            error_types = {}
            for f in failed:
                err = f.error[:50] or "Unknown"
                error_types[err] = error_types.get(err, 0) + 1
            for err, count in error_types.items():
                print(f"     {count} 次: {err}")
            print()
        
        print("=" * 70)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "test_config": {
                "num_connections": num_connections,
                "requests_per_conn": requests_per_conn
            },
            "results": {
                "total_time": round(total_time, 2),
                "success_count": len(successful),
                "failure_count": len(failed),
                "success_rate": round(len(successful)/len(self.results)*100, 2) if self.results else 0,
                "throughput_rps": round(len(self.results)/total_time, 2)
            }
        }
        
        report_file = f"./logs/stress_test/report_{int(time.time())}.json"
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f" 报告已保存: {report_file}")
        print("=" * 70)

async def main():
    import sys
    conns = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    reqs = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    tester = MCPStressTester()
    await tester.run_stress_test(num_connections=conns, requests_per_conn=reqs)

if __name__ == "__main__":
    asyncio.run(main())
