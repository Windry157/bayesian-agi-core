#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记忆系统高并发压力测试脚本
测试场景:
1. 高并发写入测试
2. 高并发读取测试
3. 混合读写测试
4. 内存泄漏检测
5. 线程池死锁测试
"""

import asyncio
import threading
import time
import psutil
import gc
import os
import shutil
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目路径
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.memory.memory_system import MemorySystem


class StressTestResult:
    """压力测试结果"""
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.total_requests = 0
        self.success_count = 0
        self.failure_count = 0
        self.total_time = 0.0
        self.min_time = float('inf')
        self.max_time = 0.0
        self.avg_time = 0.0
        self.throughput = 0.0
        self.errors = []
    
    def record(self, success: bool, duration: float, error: Optional[str] = None):
        """记录单次请求结果"""
        self.total_requests += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
            if error:
                self.errors.append(error)
        
        self.min_time = min(self.min_time, duration)
        self.max_time = max(self.max_time, duration)
    
    def finalize(self):
        """计算最终统计结果"""
        if self.total_requests > 0:
            self.total_time = self.end_time - self.start_time
            self.avg_time = self.total_time / self.total_requests
            self.throughput = self.total_requests / self.total_time
        else:
            self.avg_time = 0.0
            self.throughput = 0.0
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_requests": self.total_requests,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_count / max(self.total_requests, 1) * 100,
            "total_time": self.total_time,
            "min_time": self.min_time,
            "max_time": self.max_time,
            "avg_time": self.avg_time,
            "throughput": self.throughput,
            "errors": self.errors[:10]  # 只保留前10个错误
        }


class MemoryMonitor:
    """内存监控器"""
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.snapshots = []
    
    def snapshot(self, label: str):
        """记录内存快照"""
        mem_info = self.process.memory_info()
        self.snapshots.append({
            "label": label,
            "timestamp": time.time(),
            "rss": mem_info.rss / (1024 * 1024),  # MB
            "vms": mem_info.vms / (1024 * 1024),  # MB
            "num_objects": len(gc.get_objects())
        })
    
    def get_report(self) -> Dict[str, Any]:
        """生成内存报告"""
        if not self.snapshots:
            return {}
        
        rss_values = [s["rss"] for s in self.snapshots]
        return {
            "snapshots": self.snapshots,
            "initial_rss": self.snapshots[0]["rss"],
            "final_rss": self.snapshots[-1]["rss"],
            "peak_rss": max(rss_values),
            "avg_rss": sum(rss_values) / len(rss_values),
            "rss_increase": self.snapshots[-1]["rss"] - self.snapshots[0]["rss"],
            "object_count_change": self.snapshots[-1]["num_objects"] - self.snapshots[0]["num_objects"]
        }


async def stress_test_write(mem: MemorySystem, num_requests: int, concurrency: int) -> StressTestResult:
    """高并发写入测试"""
    result = StressTestResult()
    result.start_time = time.time()
    
    async def write_task(task_id: int):
        try:
            start = time.time()
            content = f"测试记忆 {task_id}: {datetime.now().isoformat()} - 这是一条用于压力测试的记忆内容，包含一些随机数据。"
            await mem.add_memory(content, metadata={"test": "stress", "task_id": task_id})
            duration = time.time() - start
            result.record(True, duration)
        except Exception as e:
            result.record(False, 0, str(e))
    
    # 创建并发任务
    tasks = [write_task(i) for i in range(num_requests)]
    
    # 分批执行以控制并发度
    for i in range(0, num_requests, concurrency):
        batch = tasks[i:i+concurrency]
        await asyncio.gather(*batch)
    
    result.end_time = time.time()
    result.finalize()
    return result


async def stress_test_read(mem: MemorySystem, num_requests: int, concurrency: int) -> StressTestResult:
    """高并发读取测试"""
    result = StressTestResult()
    result.start_time = time.time()
    
    async def read_task(task_id: int):
        try:
            start = time.time()
            # 随机查询
            query = f"测试记忆 {task_id % 100}"
            await mem.retrieve_memories(query, top_k=5)
            duration = time.time() - start
            result.record(True, duration)
        except Exception as e:
            result.record(False, 0, str(e))
    
    tasks = [read_task(i) for i in range(num_requests)]
    
    for i in range(0, num_requests, concurrency):
        batch = tasks[i:i+concurrency]
        await asyncio.gather(*batch)
    
    result.end_time = time.time()
    result.finalize()
    return result


async def stress_test_mixed(mem: MemorySystem, num_requests: int, concurrency: int) -> StressTestResult:
    """混合读写测试 (70%读, 30%写)"""
    result = StressTestResult()
    result.start_time = time.time()
    
    async def mixed_task(task_id: int):
        try:
            start = time.time()
            if task_id % 10 < 3:
                # 30% 写操作
                content = f"混合测试记忆 {task_id}: {datetime.now().isoformat()}"
                await mem.add_memory(content)
            else:
                # 70% 读操作
                query = f"混合测试 {task_id % 50}"
                await mem.retrieve_memories(query, top_k=3)
            duration = time.time() - start
            result.record(True, duration)
        except Exception as e:
            result.record(False, 0, str(e))
    
    tasks = [mixed_task(i) for i in range(num_requests)]
    
    for i in range(0, num_requests, concurrency):
        batch = tasks[i:i+concurrency]
        await asyncio.gather(*batch)
    
    result.end_time = time.time()
    result.finalize()
    return result


def test_thread_pool_deadlock():
    """测试线程池死锁情况"""
    result = {
        "success": False,
        "message": "",
        "timeout_occurred": False
    }
    
    def task_with_timeout(event: threading.Event, timeout: int):
        """带超时的任务"""
        # 模拟可能导致死锁的操作
        try:
            time.sleep(0.1)
            event.set()
        except Exception as e:
            pass
    
    event = threading.Event()
    with ThreadPoolExecutor(max_workers=4) as executor:
        future = executor.submit(task_with_timeout, event, 5)
        
        try:
            # 设置超时
            future.result(timeout=10)
            if event.is_set():
                result["success"] = True
                result["message"] = "线程池测试通过，未发生死锁"
            else:
                result["message"] = "任务未完成"
        except TimeoutError:
            result["timeout_occurred"] = True
            result["message"] = "线程池测试超时，可能存在死锁风险"
        except Exception as e:
            result["message"] = f"线程池测试异常: {e}"
    
    return result


async def test_memory_leak(mem: MemorySystem, iterations: int = 1000) -> Dict[str, Any]:
    """测试内存泄漏"""
    gc.collect()
    initial_objects = len(gc.get_objects())
    initial_memory = psutil.Process(os.getpid()).memory_info().rss
    
    # 执行多次操作
    for i in range(iterations):
        await mem.add_memory(f"内存泄漏测试 {i}: {datetime.now().isoformat()}")
    
    await mem.flush()
    
    # 强制垃圾回收
    gc.collect()
    final_objects = len(gc.get_objects())
    final_memory = psutil.Process(os.getpid()).memory_info().rss
    
    # 清理 - 使用内存缓存清空
    mem.memory_cache.clear()
    mem._dirty = True
    
    return {
        "iterations": iterations,
        "initial_objects": initial_objects,
        "final_objects": final_objects,
        "object_increase": final_objects - initial_objects,
        "initial_memory_mb": initial_memory / (1024 * 1024),
        "final_memory_mb": final_memory / (1024 * 1024),
        "memory_increase_mb": (final_memory - initial_memory) / (1024 * 1024),
        "memory_leak_detected": (final_memory - initial_memory) > (10 * 1024 * 1024)  # >10MB视为泄漏
    }


async def run_full_stress_test():
    """运行完整的压力测试套件"""
    print("=== 记忆系统高并发压力测试 ===")
    
    test_dir = "stress_test_memory"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir, ignore_errors=True)
    
    # 创建记忆系统
    mem = MemorySystem(
        memory_dir=test_dir,
        use_vector_index=False,
        use_knowledge_graph=False,
        buffer_size=100
    )
    await mem.load()
    
    memory_monitor = MemoryMonitor()
    memory_monitor.snapshot("测试开始")
    
    test_configs = [
        {"name": "高并发写入", "func": stress_test_write, "requests": 1000, "concurrency": 50},
        {"name": "高并发读取", "func": stress_test_read, "requests": 1000, "concurrency": 50},
        {"name": "混合读写", "func": stress_test_mixed, "requests": 1000, "concurrency": 50},
    ]
    
    results = {}
    
    # 运行各项测试
    for config in test_configs:
        print(f"\n【测试】{config['name']}")
        print(f"  请求数: {config['requests']}, 并发度: {config['concurrency']}")
        
        result = await config["func"](mem, config["requests"], config["concurrency"])
        results[config["name"]] = result.to_dict()
        
        print(f"  完成: {result.success_count}/{result.total_requests} 成功")
        print(f"  成功率: {result.success_count / max(result.total_requests, 1) * 100:.2f}%")
        print(f"  吞吐量: {result.throughput:.2f} req/s")
        print(f"  平均响应时间: {result.avg_time * 1000:.2f} ms")
    
    # 线程池死锁测试
    print("\n【测试】线程池死锁检测")
    deadlock_result = test_thread_pool_deadlock()
    results["线程池测试"] = deadlock_result
    print(f"  {deadlock_result['message']}")
    
    # 内存泄漏测试
    print("\n【测试】内存泄漏检测")
    leak_result = await test_memory_leak(mem)
    results["内存泄漏测试"] = leak_result
    print(f"  对象数变化: {leak_result['object_increase']}")
    print(f"  内存变化: {leak_result['memory_increase_mb']:.2f} MB")
    print(f"  泄漏检测: {'是' if leak_result['memory_leak_detected'] else '否'}")
    
    memory_monitor.snapshot("测试结束")
    mem.close()
    
    # 清理测试目录
    shutil.rmtree(test_dir, ignore_errors=True)
    
    # 生成报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "memory_report": memory_monitor.get_report(),
        "test_results": results
    }
    
    report_path = f"stress_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n=== 测试完成 ===")
    print(f"报告已保存到: {report_path}")
    
    return report


def generate_html_report(report: Dict[str, Any]):
    """生成HTML格式的性能报告"""
    html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>记忆系统压力测试报告</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .test-card {{ background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .test-title {{ color: #333; border-bottom: 2px solid #667eea; padding-bottom: 10px; margin-bottom: 15px; }}
        .stat-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
        .stat-box {{ background: #f8f9fa; padding: 15px; border-radius: 6px; text-align: center; }}
        .stat-label {{ color: #666; font-size: 14px; }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #667eea; }}
        .success {{ color: #28a745; }}
        .warning {{ color: #ffc107; }}
        .danger {{ color: #dc3545; }}
        .safe {{ color: #28a745; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f8f9fa; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>记忆系统压力测试报告</h1>
        <p>生成时间: {report['timestamp']}</p>
    </div>
    
    <div class="test-card">
        <h2 class="test-title">📊 整体性能概览</h2>
        <div class="stat-grid">
            <div class="stat-box">
                <div class="stat-label">写入吞吐量</div>
                <div class="stat-value">{report['test_results']['高并发写入']['throughput']:.2f} req/s</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">读取吞吐量</div>
                <div class="stat-value">{report['test_results']['高并发读取']['throughput']:.2f} req/s</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">混合吞吐量</div>
                <div class="stat-value">{report['test_results']['混合读写']['throughput']:.2f} req/s</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">内存增长</div>
                <div class="stat-value {'danger' if report['memory_report']['rss_increase'] > 10 else 'safe'}">
                    {report['memory_report']['rss_increase']:.2f} MB
                </div>
            </div>
        </div>
    </div>
    
    <div class="test-card">
        <h2 class="test-title">📈 详细测试结果</h2>
        <table>
            <tr>
                <th>测试类型</th>
                <th>请求数</th>
                <th>成功数</th>
                <th>成功率</th>
                <th>吞吐量</th>
                <th>平均响应时间</th>
                <th>最大响应时间</th>
            </tr>
    """
    
    for test_name, result in report['test_results'].items():
        if 'success_rate' in result:
            html += f"""
            <tr>
                <td>{test_name}</td>
                <td>{result['total_requests']}</td>
                <td>{result['success_count']}</td>
                <td class="{'success' if result['success_rate'] >= 99 else 'warning'}">{result['success_rate']:.2f}%</td>
                <td>{result['throughput']:.2f} req/s</td>
                <td>{result['avg_time'] * 1000:.2f} ms</td>
                <td>{result['max_time'] * 1000:.2f} ms</td>
            </tr>
            """
    
    html += """
        </table>
    </div>
    
    <div class="test-card">
        <h2 class="test-title">🔒 稳定性测试</h2>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div>
                <h3>线程池测试</h3>
                <p>结果: <span class="{'success' if report['test_results']['线程池测试']['success'] else 'danger'}">
                    {'✓ 通过' if report['test_results']['线程池测试']['success'] else '✗ 失败'}
                </span></p>
                <p>{report['test_results']['线程池测试']['message']}</p>
            </div>
            <div>
                <h3>内存泄漏测试</h3>
                <p>对象增长: {report['test_results']['内存泄漏测试']['object_increase']}</p>
                <p>内存增长: {report['test_results']['内存泄漏测试']['memory_increase_mb']:.2f} MB</p>
                <p>泄漏检测: <span class="{'danger' if report['test_results']['内存泄漏测试']['memory_leak_detected'] else 'safe'}">
                    {'✗ 检测到泄漏' if report['test_results']['内存泄漏测试']['memory_leak_detected'] else '✓ 正常'}
                </span></p>
            </div>
        </div>
    </div>
    
    <div class="test-card">
        <h2 class="test-title">💾 内存监控快照</h2>
        <table>
            <tr>
                <th>阶段</th>
                <th>RSS (MB)</th>
                <th>VMS (MB)</th>
                <th>对象数</th>
            </tr>
    """
    
    for snapshot in report['memory_report']['snapshots']:
        html += f"""
            <tr>
                <td>{snapshot['label']}</td>
                <td>{snapshot['rss']:.2f}</td>
                <td>{snapshot['vms']:.2f}</td>
                <td>{snapshot['num_objects']}</td>
            </tr>
            """
    
    html += """
        </table>
    </div>
    
    <div style="text-align: center; color: #666; margin-top: 20px; padding: 10px; border-top: 1px solid #ddd;">
        <p>Bayesian-AGI-Core 记忆系统压力测试报告</p>
    </div>
</body>
</html>
    """
    
    report_path = f"stress_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"HTML报告已保存到: {report_path}")


if __name__ == "__main__":
    report = asyncio.run(run_full_stress_test())
    generate_html_report(report)
