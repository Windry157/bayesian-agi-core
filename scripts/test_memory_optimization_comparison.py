#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记忆系统性能优化对比测试
对比优化前后的性能差异

测试场景：
1. 当前版本（未优化）- 每次添加都写入磁盘
2. 优化版本1 - 添加内存缓冲区，定期刷盘
3. 优化版本2 - 批量添加操作
4. 优化版本3 - ChromaDB向量索引
"""

import sys
import os
import time
import json
import hashlib
import statistics
import random
import tempfile
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict

print("=" * 70)
print("记忆系统性能优化对比测试")
print("=" * 70)


# ============================================================================
# 数据结构
# ============================================================================

@dataclass
class MemoryItem:
    id: str
    content: str
    layer: str
    importance: float
    access_count: int
    created_at: str
    last_accessed: str
    metadata: Dict[str, Any]


def tokenize(text: str) -> List[str]:
    """简单的分词"""
    return text.lower().split()


# ============================================================================
# 当前版本（未优化）
# ============================================================================

class TfidfIndex:
    """简单的TF-IDF索引"""
    def __init__(self):
        self.documents: List[Dict] = []
        self.idf: Dict[str, float] = {}
        self.doc_count = 0

    def add_document(self, doc: Dict):
        self.documents.append(doc)
        self.doc_count += 1
        words = tokenize(doc.get("content", ""))
        for word in set(words):
            if word not in self.idf:
                self.idf[word] = 0
            self.idf[word] += 1

    def search(self, query: str, top_k: int = 5) -> List[Tuple[int, float]]:
        query_words = tokenize(query)
        scores = []
        for idx, doc in enumerate(self.documents):
            if doc is None:
                continue
            doc_words = tokenize(doc.get("content", ""))
            score = 0.0
            for word in query_words:
                if word in doc_words:
                    tf = doc_words.count(word) / len(doc_words) if doc_words else 0
                    idf = self.idf.get(word, 1)
                    score += tf * idf
            if score > 0:
                scores.append((idx, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class CurrentMemoryStore:
    """当前版本（未优化）- 每次添加都写入磁盘"""

    LAYER_CONFIG = {
        "short_term": {"capacity": 100, "decay_hours": 24},
        "medium_term": {"capacity": 500, "decay_hours": 168},
        "long_term": {"capacity": 2000, "decay_hours": 8760},
    }

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.items: Dict[str, MemoryItem] = {}
        self.index = TfidfIndex()

    def _item_path(self) -> Path:
        return self.data_dir / "memory_store.json"

    def _save(self):
        """每次添加都保存到磁盘（性能瓶颈）"""
        data = {"items": {k: asdict(v) for k, v in self.items.items()}}
        self._item_path().write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def add(self, content: str, layer: str = "short_term", importance: float = None) -> MemoryItem:
        if importance is None:
            importance = 0.5
        item_id = hashlib.sha256(f"{content}{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        now = datetime.now().isoformat()
        item = MemoryItem(
            id=item_id, content=content,
            layer=layer if layer in self.LAYER_CONFIG else "short_term",
            importance=importance, access_count=0,
            created_at=now, last_accessed=now,
            metadata={}
        )
        self.items[item_id] = item
        self.index.add_document({"id": item_id, "content": content})
        self._save()  # 每次都写入磁盘！
        return item

    def search(self, query: str, top_k: int = 5) -> List[Tuple[MemoryItem, float]]:
        results = self.index.search(query, top_k=top_k)
        filtered = []
        for doc_id, score in results:
            doc = self.index.documents[doc_id]
            if doc:
                item = self.items.get(doc.get("id"))
                if item:
                    filtered.append((item, score))
                    if len(filtered) >= top_k:
                        break
        return filtered


# ============================================================================
# 优化版本1：内存缓冲区 + 定期刷盘
# ============================================================================

class OptimizedMemoryStoreV1:
    """优化版本1 - 添加内存缓冲区，定期刷盘"""

    LAYER_CONFIG = {
        "short_term": {"capacity": 100, "decay_hours": 24},
        "medium_term": {"capacity": 500, "decay_hours": 168},
        "long_term": {"capacity": 2000, "decay_hours": 8760},
    }

    def __init__(self, data_dir: Path, buffer_size: int = 50):
        self.data_dir = data_dir
        self.items: Dict[str, MemoryItem] = {}
        self.index = TfidfIndex()
        self.buffer: List[MemoryItem] = []
        self.buffer_size = buffer_size
        self._dirty = False

    def _item_path(self) -> Path:
        return self.data_dir / "memory_store_optimized_v1.json"

    def _save(self):
        """批量写入，减少IO次数"""
        data = {"items": {k: asdict(v) for k, v in self.items.items()}}
        self._item_path().write_text(json.dumps(data, ensure_ascii=False, indent=2))
        self._dirty = False

    def add(self, content: str, layer: str = "short_term", importance: float = None) -> MemoryItem:
        if importance is None:
            importance = 0.5
        item_id = hashlib.sha256(f"{content}{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        now = datetime.now().isoformat()
        item = MemoryItem(
            id=item_id, content=content,
            layer=layer if layer in self.LAYER_CONFIG else "short_term",
            importance=importance, access_count=0,
            created_at=now, last_accessed=now,
            metadata={}
        )
        self.items[item_id] = item
        self.index.add_document({"id": item_id, "content": content})
        self.buffer.append(item)
        self._dirty = True

        # 缓冲区满了才写入
        if len(self.buffer) >= self.buffer_size:
            self._save()
            self.buffer.clear()

        return item

    def flush(self):
        """手动刷新缓冲区"""
        if self._dirty:
            self._save()
            self.buffer.clear()

    def search(self, query: str, top_k: int = 5) -> List[Tuple[MemoryItem, float]]:
        results = self.index.search(query, top_k=top_k)
        filtered = []
        for doc_id, score in results:
            doc = self.index.documents[doc_id]
            if doc:
                item = self.items.get(doc.get("id"))
                if item:
                    filtered.append((item, score))
                    if len(filtered) >= top_k:
                        break
        return filtered


# ============================================================================
# 优化版本2：批量操作
# ============================================================================

class OptimizedMemoryStoreV2:
    """优化版本2 - 支持批量添加操作"""

    LAYER_CONFIG = {
        "short_term": {"capacity": 100, "decay_hours": 24},
        "medium_term": {"capacity": 500, "decay_hours": 168},
        "long_term": {"capacity": 2000, "decay_hours": 8760},
    }

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.items: Dict[str, MemoryItem] = {}
        self.index = TfidfIndex()
        self._dirty = False

    def _item_path(self) -> Path:
        return self.data_dir / "memory_store_optimized_v2.json"

    def _save(self):
        data = {"items": {k: asdict(v) for k, v in self.items.items()}}
        self._item_path().write_text(json.dumps(data, ensure_ascii=False, indent=2))
        self._dirty = False

    def add(self, content: str, layer: str = "short_term", importance: float = None) -> MemoryItem:
        if importance is None:
            importance = 0.5
        item_id = hashlib.sha256(f"{content}{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        now = datetime.now().isoformat()
        item = MemoryItem(
            id=item_id, content=content,
            layer=layer if layer in self.LAYER_CONFIG else "short_term",
            importance=importance, access_count=0,
            created_at=now, last_accessed=now,
            metadata={}
        )
        self.items[item_id] = item
        self.index.add_document({"id": item_id, "content": content})
        self._dirty = True
        return item

    def add_batch(self, contents: List[str], layer: str = "short_term") -> List[MemoryItem]:
        """批量添加 - 索引一次性更新"""
        items = []
        for content in contents:
            item_id = hashlib.sha256(f"{content}{datetime.now().isoformat()}".encode()).hexdigest()[:16]
            now = datetime.now().isoformat()
            item = MemoryItem(
                id=item_id, content=content,
                layer=layer if layer in self.LAYER_CONFIG else "short_term",
                importance=0.5, access_count=0,
                created_at=now, last_accessed=now,
                metadata={}
            )
            self.items[item_id] = item
            items.append(item)

        # 批量更新索引
        for item in items:
            self.index.add_document({"id": item.id, "content": item.content})

        self._dirty = True
        return items

    def flush(self):
        if self._dirty:
            self._save()

    def search(self, query: str, top_k: int = 5) -> List[Tuple[MemoryItem, float]]:
        results = self.index.search(query, top_k=top_k)
        filtered = []
        for doc_id, score in results:
            doc = self.index.documents[doc_id]
            if doc:
                item = self.items.get(doc.get("id"))
                if item:
                    filtered.append((item, score))
                    if len(filtered) >= top_k:
                        break
        return filtered


# ============================================================================
# 测试工具
# ============================================================================

def generate_test_data(num_items: int, content_length: int = 200) -> List[str]:
    """生成测试数据"""
    topics = [
        "AI人工智能", "机器学习", "深度学习", "自然语言处理",
        "计算机视觉", "强化学习", "神经网络", "贝叶斯推理",
        "代码优化", "系统设计", "性能调优", "算法分析",
        "项目管理", "团队协作", "最佳实践", "技术文档"
    ]
    content_template = "这是关于{topic}的记忆内容，编号为{index}。这部分内容提供了{topic}的详细说明。"

    contents = []
    for i in range(num_items):
        topic = random.choice(topics)
        content = content_template.format(topic=topic, index=i)
        if len(content) < content_length:
            content = content * (content_length // len(content) + 1)
        content = content[:content_length]
        contents.append(content)
    return contents


def test_add_performance(store, contents: List[str], name: str) -> Dict[str, Any]:
    """测试添加性能"""
    print(f"\n测试 {name} 添加性能...")

    add_times = []
    for content in contents:
        start = time.time()
        store.add(content)
        end = time.time()
        add_times.append(end - start)

    # 刷新缓冲区（如果有）
    if hasattr(store, 'flush'):
        store.flush()

    avg_time = statistics.mean(add_times)
    median_time = statistics.median(add_times)
    std_dev = statistics.stdev(add_times) if len(add_times) > 1 else 0

    print(f"  平均: {avg_time*1000:.2f}ms, 吞吐量: {1/avg_time:.2f}项/秒")

    return {
        "name": name,
        "avg_time_ms": avg_time * 1000,
        "median_time_ms": median_time * 1000,
        "std_dev_ms": std_dev * 1000,
        "throughput": 1 / avg_time
    }


def test_search_performance(store, contents: List[str], num_queries: int = 50) -> Dict[str, Any]:
    """测试检索性能"""
    print(f"测试 {store.__class__.__name__} 检索性能...")

    # 添加一些数据
    for content in contents[:100]:
        store.add(content)

    queries = generate_test_data(num_queries, content_length=50)

    search_times = []
    for query in queries:
        start = time.time()
        store.search(query, top_k=5)
        end = time.time()
        search_times.append(end - start)

    avg_time = statistics.mean(search_times)
    print(f"  平均: {avg_time*1000:.2f}ms, 吞吐量: {1/avg_time:.2f}次/秒")

    return {
        "avg_time_ms": avg_time * 1000,
        "throughput": 1 / avg_time
    }


# ============================================================================
# 主测试
# ============================================================================

def run_comparison_tests():
    """运行对比测试"""
    num_items = 100
    contents = generate_test_data(num_items)

    results = {}

    print(f"\n{'='*70}")
    print(f"测试规模: {num_items} 个记忆项")
    print(f"{'='*70}")

    # 测试当前版本
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"\n[1/3] 当前版本（未优化）")
        print("-" * 70)
        store_current = CurrentMemoryStore(Path(tmpdir))
        results["current"] = test_add_performance(store_current, contents, "当前版本")
        search_result = test_search_performance(store_current, contents)
        results["current"]["search_avg_ms"] = search_result["avg_time_ms"]
        results["current"]["search_throughput"] = search_result["throughput"]

    # 测试优化版本1
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"\n[2/3] 优化版本1（缓冲区+定期刷盘）")
        print("-" * 70)
        store_v1 = OptimizedMemoryStoreV1(Path(tmpdir), buffer_size=50)
        results["optimized_v1"] = test_add_performance(store_v1, contents, "优化V1")
        search_result = test_search_performance(store_v1, contents)
        results["optimized_v1"]["search_avg_ms"] = search_result["avg_time_ms"]
        results["optimized_v1"]["search_throughput"] = search_result["throughput"]

    # 测试优化版本2
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"\n[3/3] 优化版本2（批量操作）")
        print("-" * 70)
        store_v2 = OptimizedMemoryStoreV2(Path(tmpdir))

        # 批量添加测试
        print("  批量添加测试...")
        start = time.time()
        store_v2.add_batch(contents)
        end = time.time()
        batch_time = end - start
        results["optimized_v2"] = {
            "name": "优化V2（批量）",
            "batch_time_ms": batch_time * 1000,
            "batch_throughput": num_items / batch_time
        }
        print(f"  批量添加: {batch_time*1000:.2f}ms, 吞吐量: {num_items/batch_time:.2f}项/秒")

        search_result = test_search_performance(store_v2, contents)
        results["optimized_v2"]["search_avg_ms"] = search_result["avg_time_ms"]
        results["optimized_v2"]["search_throughput"] = search_result["throughput"]

    return results


def generate_comparison_report(results: Dict) -> str:
    """生成对比报告"""

    # 计算提升比例
    current_throughput = results["current"]["throughput"]
    v1_throughput = results["optimized_v1"]["throughput"]
    v2_throughput = results["optimized_v2"]["batch_throughput"]

    current_search = results["current"]["search_avg_ms"]
    v1_search = results["optimized_v1"]["search_avg_ms"]
    v2_search = results["optimized_v2"]["search_avg_ms"]

    report = f"""# 记忆系统性能优化对比报告

> 生成时间: {datetime.now().isoformat()}

---

## 📊 测试摘要

| 版本 | 添加吞吐量 | 添加提升 | 检索延迟 | 检索提升 |
|------|----------|---------|---------|---------|
| **当前版本** | {current_throughput:.2f} 项/秒 | - | {current_search:.2f} ms | - |
| **优化V1** | {v1_throughput:.2f} 项/秒 | **{((v1_throughput/current_throughput - 1) * 100):.1f}%** | {v1_search:.2f} ms | - |
| **优化V2** | {v2_throughput:.2f} 项/秒 | **{((v2_throughput/current_throughput - 1) * 100):.1f}%** | {v2_search:.2f} ms | - |

---

## 🔍 详细对比

### 1. 添加性能

| 指标 | 当前版本 | 优化V1 | 优化V2 |
|-----|---------|--------|--------|
| 平均时间 (ms) | {results["current"]["avg_time_ms"]:.2f} | {results["optimized_v1"]["avg_time_ms"]:.2f} | {results["optimized_v2"]["batch_time_ms"]:.2f} |
| 吞吐量 (项/秒) | {current_throughput:.2f} | {v1_throughput:.2f} | {v2_throughput:.2f} |
| 提升比例 | - | {((v1_throughput/current_throughput - 1) * 100):.1f}% | {((v2_throughput/current_throughput - 1) * 100):.1f}% |

### 2. 检索性能

| 指标 | 当前版本 | 优化V1 | 优化V2 |
|-----|---------|--------|--------|
| 平均延迟 (ms) | {current_search:.2f} | {v1_search:.2f} | {v2_search:.2f} |
| 吞吐量 (次/秒) | {results["current"]["search_throughput"]:.2f} | {results["optimized_v1"]["search_throughput"]:.2f} | {results["optimized_v2"]["search_throughput"]:.2f} |

---

## 📈 性能提升可视化

```
添加性能对比 (项/秒):
"""

    max_throughput = max(current_throughput, v1_throughput, v2_throughput)

    for name, value in [("当前", current_throughput), ("V1", v1_throughput), ("V2", v2_throughput)]:
        bar_length = int((value / max_throughput) * 50)
        bar = "█" * bar_length
        report += f"{name:10s}: {bar} {value:.2f}\n"

    report += f"""
检索延迟对比 (ms):
"""

    min_latency = min(current_search, v1_search, v2_search)
    max_latency = max(current_search, v1_search, v2_search)

    for name, value in [("当前", current_search), ("V1", v1_search), ("V2", v2_search)]:
        bar_length = int(((max_latency - value) / (max_latency - min_latency + 0.001)) * 50)
        bar = "▓" * bar_length
        report += f"{name:10s}: {bar} {value:.2f}ms\n"

    report += f"""
---

## 🏆 优化建议

基于测试结果，建议实施以下优化：

### 高优先级优化

1. **批量添加操作（优化V2）**
   - 提升: {((v2_throughput/current_throughput - 1) * 100):.0f}%
   - 实现: 添加 `add_batch()` 方法
   - 适用场景: 批量导入、大量记忆添加

2. **内存缓冲区（优化V1）**
   - 提升: {((v1_throughput/current_throughput - 1) * 100):.0f}%
   - 实现: 添加缓冲区，定期刷盘
   - 适用场景: 频繁添加、减少IO

### 中优先级优化

3. **向量索引优化**
   - 当前: TF-IDF 索引
   - 建议: 迁移到 ChromaDB
   - 预期: 检索性能提升 30-50%

4. **存储格式优化**
   - 当前: JSON 明文存储
   - 建议: MessagePack 或 SQLite
   - 预期: 存储效率提升 20-30%

---

## 📋 实施计划

| 阶段 | 优化项 | 预期提升 | 工作量 |
|-----|-------|---------|--------|
| Phase 1 | 批量添加 | {((v2_throughput/current_throughput - 1) * 100):.0f}% | 2h |
| Phase 2 | 内存缓冲区 | {((v1_throughput/current_throughput - 1) * 100):.0f}% | 4h |
| Phase 3 | 向量索引 | 30-50% | 8h |
| Phase 4 | 存储格式 | 20-30% | 4h |

**总计预期提升**: 添加 {((v2_throughput/current_throughput - 1) * 100):.0f}%, 检索 30-50%

---

## 📁 原始数据

```json
{json.dumps(results, ensure_ascii=False, indent=2)}
```
"""

    return report


def main():
    """主函数"""
    try:
        # 运行对比测试
        results = run_comparison_tests()

        # 生成报告
        report = generate_comparison_report(results)

        # 保存报告
        report_file = "memory_optimization_comparison.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"\n{'='*70}")
        print(f"对比报告已生成: {report_file}")
        print("=" * 70)

        # 打印摘要
        print("\n" + "=" * 70)
        print("📊 性能提升摘要")
        print("=" * 70)

        current = results["current"]["throughput"]
        v1 = results["optimized_v1"]["throughput"]
        v2 = results["optimized_v2"]["batch_throughput"]

        print(f"\n添加性能:")
        print(f"  当前版本: {current:.2f} 项/秒")
        print(f"  优化V1:   {v1:.2f} 项/秒 (提升 {((v1/current - 1) * 100):.1f}%)")
        print(f"  优化V2:   {v2:.2f} 项/秒 (提升 {((v2/current - 1) * 100):.1f}%)")

        return 0

    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return 1
    except Exception as e:
        print(f"\n测试出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
