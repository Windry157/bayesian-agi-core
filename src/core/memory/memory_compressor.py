#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记忆压缩器
提供记忆压缩、合并和优化功能。
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class CompressionResult:
    """压缩结果"""
    original_count: int
    compressed_count: int
    compression_ratio: float
    merged_items: List[Tuple[str, str]]  # (kept_id, removed_id)
    details: Dict[str, Any]


class MemoryCompressor:
    """记忆压缩器

    提供多种压缩策略：
    - 内容相似度合并
    - 重要性筛选
    - 时间衰减清理
    """

    def __init__(self, similarity_threshold: float = 0.85):
        """初始化压缩器

        Args:
            similarity_threshold: 相似度阈值，超过此值则合并
        """
        self.similarity_threshold = similarity_threshold
        logger.info(f"MemoryCompressor initialized with threshold={similarity_threshold}")

    def compress(
        self,
        memories: List[Dict[str, Any]],
        strategy: str = "similarity",
        keep_ratio: float = 0.5
    ) -> CompressionResult:
        """压缩记忆列表

        Args:
            memories: 记忆列表
            strategy: 压缩策略 ("similarity", "importance", "hybrid")
            keep_ratio: 保留比例 (0-1)

        Returns:
            CompressionResult: 压缩结果
        """
        if not memories:
            return CompressionResult(0, 0, 0.0, [], {})

        original_count = len(memories)
        logger.info(f"Starting compression of {original_count} memories, strategy={strategy}")

        if strategy == "similarity":
            result = self._compress_by_similarity(memories)
        elif strategy == "importance":
            result = self._compress_by_importance(memories, keep_ratio)
        elif strategy == "hybrid":
            result = self._compress_hybrid(memories, keep_ratio)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        logger.info(f"Compression complete: {original_count} -> {result.compressed_count} "
                   f"({result.compression_ratio:.1%} reduction)")
        return result

    def _compress_by_similarity(
        self,
        memories: List[Dict[str, Any]]
    ) -> CompressionResult:
        """基于内容相似度压缩

        Args:
            memories: 记忆列表

        Returns:
            CompressionResult
        """
        from collections import defaultdict

        # 计算记忆指纹
        fingerprints = {}
        for mem in memories:
            content = mem.get('content', '')
            fp = self._compute_fingerprint(content)
            fingerprints[mem['id']] = fp

        # 分组相似记忆
        groups = defaultdict(list)
        for mem in memories:
            fp = fingerprints[mem['id']]
            groups[fp].append(mem)

        # 合并每组
        merged = []
        merged_items = []
        for group in groups.values():
            if len(group) > 1:
                # 合并相似记忆
                kept = self._merge_memories(group)
                merged.append(kept)
                # 记录合并关系
                for m in group:
                    if m['id'] != kept['id']:
                        merged_items.append((kept['id'], m['id']))
            else:
                merged.append(group[0])

        compression_ratio = 1 - (len(merged) / len(memories)) if memories else 0.0

        return CompressionResult(
            original_count=len(memories),
            compressed_count=len(merged),
            compression_ratio=compression_ratio,
            merged_items=merged_items,
            details={"strategy": "similarity", "groups": len(groups)}
        )

    def _compress_by_importance(
        self,
        memories: List[Dict[str, Any]],
        keep_ratio: float
    ) -> CompressionResult:
        """基于重要性压缩

        Args:
            memories: 记忆列表
            keep_ratio: 保留比例

        Returns:
            CompressionResult
        """
        # 按重要性排序
        sorted_memories = sorted(
            memories,
            key=lambda m: m.get('importance', 0.5),
            reverse=True
        )

        # 保留前 keep_ratio
        keep_count = max(1, int(len(sorted_memories) * keep_ratio))
        kept = sorted_memories[:keep_count]
        removed = sorted_memories[keep_count:]

        compression_ratio = 1 - (len(kept) / len(memories)) if memories else 0.0

        return CompressionResult(
            original_count=len(memories),
            compressed_count=len(kept),
            compression_ratio=compression_ratio,
            merged_items=[],
            details={
                "strategy": "importance",
                "keep_ratio": keep_ratio,
                "removed_importance_avg": sum(
                    m.get('importance', 0.5) for m in removed
                ) / len(removed) if removed else 0
            }
        )

    def _compress_hybrid(
        self,
        memories: List[Dict[str, Any]],
        keep_ratio: float
    ) -> CompressionResult:
        """混合压缩策略

        先合并相似内容，再按重要性筛选。

        Args:
            memories: 记忆列表
            keep_ratio: 保留比例

        Returns:
            CompressionResult
        """
        # 第一步：相似度合并
        sim_result = self._compress_by_similarity(memories)
        # 第二步：重要性筛选
        imp_result = self._compress_by_importance(
            [mem for mem in memories if mem not in
             [removed for (kept, removed) in sim_result.merged_items]],
            keep_ratio
        )

        return CompressionResult(
            original_count=len(memories),
            compressed_count=imp_result.compressed_count,
            compression_ratio=1 - (imp_result.compressed_count / len(memories)),
            merged_items=sim_result.merged_items + imp_result.merged_items,
            details={"strategy": "hybrid"}
        )

    def _compute_fingerprint(self, content: str) -> str:
        """计算内容指纹

        使用简化的特征提取方法。

        Args:
            content: 文本内容

        Returns:
            str: 指纹字符串
        """
        # 简单的基于词频和哈希的指纹
        import re
        from collections import Counter

        # 提取关键词
        words = re.findall(r'\w+', content.lower())
        # 统计词频
        word_counts = Counter(words)
        # 取前N个高频词
        top_words = sorted(word_counts.items(), key=lambda x: (-x[1], x[0]))[:10]
        # 生成指纹
        fingerprint_str = '|'.join(f"{w}:{c}" for w, c in top_words)
        # 哈希
        return hashlib.md5(fingerprint_str.encode()).hexdigest()[:16]

    def _merge_memories(self, memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合并多个记忆

        Args:
            memories: 要合并的记忆列表

        Returns:
            Dict[str, Any]: 合并后的记忆
        """
        if not memories:
            raise ValueError("No memories to merge")

        # 选择重要性最高的作为主记忆
        main_mem = max(memories, key=lambda m: m.get('importance', 0.5))

        # 合并内容
        contents = [m.get('content', '') for m in memories]
        merged_content = '\n\n---\n\n'.join(contents)

        # 合并元数据
        merged_metadata = {}
        for m in memories:
            meta = m.get('metadata', {})
            for k, v in meta.items():
                if k in merged_metadata:
                    if isinstance(merged_metadata[k], list):
                        merged_metadata[k].append(v)
                    else:
                        merged_metadata[k] = [merged_metadata[k], v]
                else:
                    merged_metadata[k] = v

        # 计算合并后的重要性
        avg_importance = sum(m.get('importance', 0.5) for m in memories) / len(memories)
        max_importance = max(m.get('importance', 0.5) for m in memories)

        return {
            **main_mem,
            'content': merged_content,
            'importance': max_importance,
            'access_count': sum(m.get('access_count', 0) for m in memories),
            'metadata': {
                **merged_metadata,
                'merged_from': [m['id'] for m in memories if m['id'] != main_mem['id']],
                'merged_count': len(memories)
            },
            'updated_at': datetime.now().isoformat()
        }

    def merge_similar(
        self,
        memory1: Dict[str, Any],
        memory2: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """合并两个相似记忆

        Args:
            memory1: 记忆1
            memory2: 记忆2

        Returns:
            Optional[Dict[str, Any]]: 合并后的记忆，或None如果不相似
        """
        sim = self._compute_similarity(
            memory1.get('content', ''),
            memory2.get('content', '')
        )

        if sim >= self.similarity_threshold:
            return self._merge_memories([memory1, memory2])
        return None

    def _compute_similarity(self, text1: str, text2: str) -> float:
        """计算两个文本的相似度

        使用简单的集合相似度。

        Args:
            text1: 文本1
            text2: 文本2

        Returns:
            float: 相似度 (0-1)
        """
        if not text1 or not text2:
            return 0.0

        # 简单的词集相似度
        set1 = set(text1.lower().split())
        set2 = set(text2.lower().split())

        if not set1 and not set2:
            return 1.0

        intersection = set1 & set2
        union = set1 | set2

        return len(intersection) / len(union)
