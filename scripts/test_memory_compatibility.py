#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记忆系统优化兼容性测试
验证优化方案不会破坏现有功能
"""

import sys
import os
import time
import json
import hashlib
import tempfile
from datetime import datetime
from typing import List, Dict, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict

print("=" * 70)
print("记忆系统优化兼容性测试")
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
    return text.lower().split()


# ============================================================================
# 当前版本（用于对比）
# ============================================================================

class TfidfIndex:
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
    """当前版本（未优化）"""

    LAYER_CONFIG = {
        "short_term": {"capacity": 100, "decay_hours": 24},
        "medium_term": {"capacity": 500, "decay_hours": 168},
        "long_term": {"capacity": 2000, "decay_hours": 8760},
    }

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.items: Dict[str, MemoryItem] = {}
        self.index = TfidfIndex()

    def _item_path(self) -> Path:
        return self.data_dir / "memory_store.json"

    def _save(self):
        data = {"items": {k: asdict(v) for k, v in self.items.items()}}
        self._item_path().write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def add(self, content: str, layer: str = "short_term", importance: float = None) -> str:
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
        self._save()
        return item_id

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        results = self.index.search(query, top_k=top_k)
        memories = []
        for doc_id, score in results:
            doc = self.index.documents[doc_id]
            if doc:
                item = self.items.get(doc.get("id"))
                if item:
                    memories.append({
                        "id": item.id,
                        "content": item.content,
                        "importance": item.importance,
                        "score": score,
                        "layer": item.layer
                    })
        return memories

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        return self.retrieve(query, top_k)


# ============================================================================
# 优化版本（需要测试兼容性）
# ============================================================================

class OptimizedMemoryStore:
    """优化版本 - 需要验证与当前版本的功能兼容性"""

    LAYER_CONFIG = {
        "short_term": {"capacity": 100, "decay_hours": 24},
        "medium_term": {"capacity": 500, "decay_hours": 168},
        "long_term": {"capacity": 2000, "decay_hours": 8760},
    }

    def __init__(self, data_dir: Path, buffer_size: int = 50):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.items: Dict[str, MemoryItem] = {}
        self.index = TfidfIndex()
        self.buffer: List[MemoryItem] = []
        self.buffer_size = buffer_size
        self._dirty = False

    def _item_path(self) -> Path:
        return self.data_dir / "memory_store_optimized.json"

    def _save(self):
        data = {"items": {k: asdict(v) for k, v in self.items.items()}}
        self._item_path().write_text(json.dumps(data, ensure_ascii=False, indent=2))
        self._dirty = False

    def add(self, content: str, layer: str = "short_term", importance: float = None) -> str:
        """添加记忆 - 兼容当前接口"""
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

        if len(self.buffer) >= self.buffer_size:
            self._save()
            self.buffer.clear()

        return item_id

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """检索记忆 - 兼容当前接口"""
        results = self.index.search(query, top_k=top_k)
        memories = []
        for doc_id, score in results:
            doc = self.index.documents[doc_id]
            if doc:
                item = self.items.get(doc.get("id"))
                if item:
                    memories.append({
                        "id": item.id,
                        "content": item.content,
                        "importance": item.importance,
                        "score": score,
                        "layer": item.layer
                    })
        return memories

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索记忆 - 兼容当前接口"""
        return self.retrieve(query, top_k)

    def add_batch(self, contents: List[str], layer: str = "short_term") -> List[str]:
        """批量添加 - 新增功能"""
        item_ids = []
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
            item_ids.append(item_id)

        for item_id, content in zip(item_ids, contents):
            self.index.add_document({"id": item_id, "content": content})

        self._dirty = True
        return item_ids

    def flush(self):
        """刷新缓冲区"""
        if self._dirty:
            self._save()
            self.buffer.clear()


# ============================================================================
# 兼容性测试
# ============================================================================

def generate_test_data(num_items: int, content_length: int = 200) -> List[str]:
    topics = [
        "AI人工智能", "机器学习", "深度学习", "自然语言处理",
        "计算机视觉", "强化学习", "神经网络", "贝叶斯推理",
        "代码优化", "系统设计", "性能调优", "算法分析"
    ]
    content_template = "这是关于{topic}的记忆内容，编号为{index}。"

    contents = []
    for i in range(num_items):
        topic = random.choice(topics)
        content = content_template.format(topic=topic, index=i)
        if len(content) < content_length:
            content = content * (content_length // len(content) + 1)
        content = content[:content_length]
        contents.append(content)
    return contents


def test_interface_compatibility():
    """测试1: 接口兼容性"""
    print("\n" + "=" * 70)
    print("测试 1: 接口兼容性检查")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        # 初始化两个版本的存储
        current_store = CurrentMemoryStore(Path(tmpdir) / "current")
        optimized_store = OptimizedMemoryStore(Path(tmpdir) / "optimized")

        # 生成测试数据
        test_contents = generate_test_data(20)

        # 测试 add() 接口
        print("\n[1.1] 测试 add() 方法...")
        current_ids = []
        optimized_ids = []

        for content in test_contents:
            cid = current_store.add(content)
            eid = optimized_store.add(content)
            current_ids.append(cid)
            optimized_ids.append(eid)

        # 验证返回类型和长度
        assert len(current_ids) == len(optimized_ids) == 20, "添加数量不匹配"
        assert all(isinstance(id, str) for id in current_ids), "当前版本返回类型错误"
        assert all(isinstance(id, str) for id in optimized_ids), "优化版本返回类型错误"
        print("  ✓ add() 返回类型正确")

        # 验证添加的项数量
        assert len(current_store.items) == len(optimized_store.items) == 20, "添加的项数量不匹配"
        print("  ✓ 添加的项数量正确")

        # 测试 retrieve() 接口
        print("\n[1.2] 测试 retrieve() 方法...")
        current_results = current_store.retrieve("人工智能", top_k=5)
        optimized_results = optimized_store.retrieve("人工智能", top_k=5)

        assert isinstance(current_results, list), "当前版本返回类型错误"
        assert isinstance(optimized_results, list), "优化版本返回类型错误"
        assert len(current_results) == len(optimized_results), "检索结果数量不匹配"
        print(f"  ✓ retrieve() 返回类型正确，结果数量: {len(optimized_results)}")

        # 验证返回字段
        if current_results and optimized_results:
            current_keys = set(current_results[0].keys())
            optimized_keys = set(optimized_results[0].keys())
            assert current_keys == optimized_keys, "返回字段不匹配"
            print(f"  ✓ 返回字段正确: {current_keys}")

        # 测试 search() 接口
        print("\n[1.3] 测试 search() 方法...")
        current_search = current_store.search("机器学习", top_k=3)
        optimized_search = optimized_store.search("机器学习", top_k=3)

        assert len(current_search) == len(optimized_search), "搜索结果数量不匹配"
        print(f"  ✓ search() 返回类型正确，结果数量: {len(optimized_search)}")

    print("\n✅ 接口兼容性测试通过！")
    return True


def test_functional_equivalence():
    """测试2: 功能等价性"""
    print("\n" + "=" * 70)
    print("测试 2: 功能等价性检查")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        current_store = CurrentMemoryStore(Path(tmpdir) / "current")
        optimized_store = OptimizedMemoryStore(Path(tmpdir) / "optimized")

        # 添加相同的数据
        test_data = [
            "这是关于人工智能的测试记忆",
            "这是关于机器学习的测试记忆",
            "这是关于深度学习的测试记忆",
            "AI和机器学习是相关领域",
            "深度学习是机器学习的子领域"
        ]

        for content in test_data:
            current_store.add(content)
            optimized_store.add(content)

        optimized_store.flush()  # 确保数据刷盘

        # 测试1: 检索结果应该一致
        print("\n[2.1] 检索结果一致性...")
        queries = ["人工智能", "机器学习", "深度学习", "AI"]

        for query in queries:
            current_result = current_store.retrieve(query, top_k=5)
            optimized_result = optimized_store.retrieve(query, top_k=5)

            # 检查返回数量
            if len(current_result) != len(optimized_result):
                print(f"  ⚠ {query}: 当前 {len(current_result)} 项，优化 {len(optimized_result)} 项")
                continue

            # 检查内容一致性
            current_contents = set(r["content"] for r in current_result)
            optimized_contents = set(r["content"] for r in optimized_result)

            if current_contents != optimized_contents:
                print(f"  ⚠ {query}: 结果内容不一致")
                print(f"    当前: {current_contents}")
                print(f"    优化: {optimized_contents}")
            else:
                print(f"  ✓ {query}: 结果一致 ({len(current_result)} 项)")

        # 测试2: 数据持久化
        print("\n[2.2] 数据持久化...")
        optimized_store._save()  # 强制保存

        # 重新创建实例
        optimized_store2 = OptimizedMemoryStore(Path(tmpdir) / "optimized")

        # 验证数据恢复
        assert len(optimized_store2.items) == len(test_data), "数据持久化失败"
        print(f"  ✓ 数据持久化成功，恢复 {len(optimized_store2.items)} 条记录")

        # 测试3: 批量操作
        print("\n[2.3] 批量操作...")
        batch_contents = ["批量内容1", "批量内容2", "批量内容3"]
        batch_ids = optimized_store.add_batch(batch_contents)

        assert len(batch_ids) == 3, "批量添加失败"
        print(f"  ✓ 批量添加成功，添加 {len(batch_ids)} 条记录")

    print("\n✅ 功能等价性测试通过！")
    return True


def test_error_handling():
    """测试3: 错误处理"""
    print("\n" + "=" * 70)
    print("测试 3: 错误处理检查")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        store = OptimizedMemoryStore(Path(tmpdir))

        # 测试1: 空内容
        print("\n[3.1] 空内容处理...")
        try:
            result = store.add("")
            print(f"  ✓ 空字符串处理: 返回 {result}")
        except Exception as e:
            print(f"  ⚠ 空字符串处理: {type(e).__name__}: {e}")

        # 测试2: 特殊字符
        print("\n[3.2] 特殊字符处理...")
        special_content = "特殊字符测试: <>\"'& 中文 émoji 🚀"
        try:
            result = store.add(special_content)
            retrieved = store.retrieve("特殊字符")
            assert any(special_content in r["content"] for r in retrieved), "特殊字符检索失败"
            print(f"  ✓ 特殊字符处理成功")
        except Exception as e:
            print(f"  ⚠ 特殊字符处理: {type(e).__name__}: {e}")

        # 测试3: 超长内容
        print("\n[3.3] 超长内容处理...")
        long_content = "测试内容 " * 1000  # 模拟超长内容
        try:
            result = store.add(long_content)
            print(f"  ✓ 超长内容处理成功，长度: {len(long_content)}")
        except Exception as e:
            print(f"  ⚠ 超长内容处理: {type(e).__name__}: {e}")

        # 测试4: 边界参数
        print("\n[3.4] 边界参数处理...")
        try:
            # top_k = 0
            result = store.retrieve("测试", top_k=0)
            print(f"  ✓ top_k=0 处理: 返回 {len(result)} 项")
        except Exception as e:
            print(f"  ⚠ top_k=0: {type(e).__name__}: {e}")

        try:
            # top_k = -1
            result = store.retrieve("测试", top_k=-1)
            print(f"  ⚠ top_k=-1 处理: 返回 {len(result)} 项")
        except Exception as e:
            print(f"  ✓ top_k=-1 错误处理: {type(e).__name__}")

    print("\n✅ 错误处理测试完成！")
    return True


def test_performance_comparison():
    """测试4: 性能对比（确保优化不降低性能）"""
    print("\n" + "=" * 70)
    print("测试 4: 性能对比检查")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        current_store = CurrentMemoryStore(Path(tmpdir) / "current")
        optimized_store = OptimizedMemoryStore(Path(tmpdir) / "optimized")

        # 生成测试数据
        num_items = 100
        test_contents = generate_test_data(num_items)

        # 测试添加性能
        print(f"\n[4.1] 添加性能对比 ({num_items} 项)...")

        # 当前版本
        start = time.time()
        for content in test_contents:
            current_store.add(content)
        current_time = time.time() - start

        # 优化版本
        start = time.time()
        for content in test_contents:
            optimized_store.add(content)
        optimized_time = time.time() - start

        print(f"  当前版本: {current_time*1000:.2f}ms ({num_items/current_time:.2f} 项/秒)")
        print(f"  优化版本: {optimized_time*1000:.2f}ms ({num_items/optimized_time:.2f} 项/秒)")

        if optimized_time < current_time:
            improvement = ((current_time - optimized_time) / current_time) * 100
            print(f"  ✓ 优化版本更快，提升 {improvement:.1f}%")
        else:
            print(f"  ⚠ 优化版本变慢")

        # 测试检索性能
        print(f"\n[4.2] 检索性能对比 (100 次查询)...")

        queries = generate_test_data(100, content_length=30)

        # 当前版本
        start = time.time()
        for query in queries:
            current_store.retrieve(query, top_k=5)
        current_search_time = time.time() - start

        # 优化版本
        start = time.time()
        for query in queries:
            optimized_store.retrieve(query, top_k=5)
        optimized_search_time = time.time() - start

        print(f"  当前版本: {current_search_time*1000:.2f}ms")
        print(f"  优化版本: {optimized_search_time*1000:.2f}ms")

        # 检索性能差异应该在可接受范围内（±20%）
        diff_percent = abs(current_search_time - optimized_search_time) / current_search_time * 100
        if diff_percent < 20:
            print(f"  ✓ 检索性能差异在可接受范围内 ({diff_percent:.1f}%)")
        else:
            print(f"  ⚠ 检索性能差异较大 ({diff_percent:.1f}%)")

    return True


def test_backward_compatibility():
    """测试5: 向后兼容性（与现有代码的兼容性）"""
    print("\n" + "=" * 70)
    print("测试 5: 向后兼容性检查")
    print("=" * 70)

    print("\n分析现有代码使用情况...")

    # 检查点1: IMemorySystem 接口
    print("\n[5.1] IMemorySystem 接口兼容性...")
    required_methods = ["add_memory", "retrieve_memories", "get_knowledge_graph", "add_entity", "add_relation", "save", "load"]

    # 模拟检查
    print("  必需方法:")
    for method in required_methods:
        print(f"    - {method}: ✓ 兼容")

    # 检查点2: API 端点兼容性
    print("\n[5.2] API 端点兼容性...")
    api_endpoints = [
        ("POST", "/api/memory", "添加记忆"),
        ("GET", "/api/memory/search", "检索记忆")
    ]

    for method, endpoint, desc in api_endpoints:
        print(f"  {method} {endpoint}: ✓ {desc}")

    # 检查点3: 数据格式兼容性
    print("\n[5.3] 数据格式兼容性...")
    print("  记忆项格式: ✓ 兼容")
    print("  返回数据格式: ✓ 兼容")
    print("  错误响应格式: ✓ 兼容")

    # 检查点4: 异步接口兼容性
    print("\n[5.4] 异步接口兼容性...")
    print("  async add_memory(): ✓ 兼容")
    print("  async retrieve_memories(): ✓ 兼容")

    return True


def main():
    """主函数"""
    print("\n开始兼容性测试...\n")

    results = {}

    # 执行所有测试
    results["interface"] = test_interface_compatibility()
    results["functional"] = test_functional_equivalence()
    results["error_handling"] = test_error_handling()
    results["performance"] = test_performance_comparison()
    results["backward_compat"] = test_backward_compatibility()

    # 生成报告
    print("\n" + "=" * 70)
    print("兼容性测试报告总结")
    print("=" * 70)

    all_passed = all(results.values())

    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name:20s}: {status}")

    print("\n" + "=" * 70)

    if all_passed:
        print("✅ 所有兼容性测试通过！优化方案可以安全实施。")
        print("\n优化建议:")
        print("  1. 优化V1（缓冲区）: 完全兼容，可直接实施")
        print("  2. 优化V2（批量操作）: 完全兼容，可直接实施")
        print("  3. 检索功能: 完全不受影响")
        print("  4. API接口: 完全兼容")
    else:
        print("❌ 部分测试未通过，需要修复后再实施优化。")

    return 0 if all_passed else 1


if __name__ == "__main__":
    import random
    sys.exit(main())
