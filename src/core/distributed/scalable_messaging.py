#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高并发消息分区与流控 (Scalable Messaging)
实现 Kafka 风格分区策略、消息 Key 分区、批量处理
"""
import hashlib
import time
import logging
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import deque, defaultdict
from threading import Lock
from datetime import datetime

logger = logging.getLogger(__name__)

# ============================================
# 1. 消息分区策略 (Message Partitioning)
# ============================================


class PartitionStrategy(Enum):
    """分区策略"""
    ROUND_ROBIN = "round_robin"
    KEY_HASH = "key_hash"
    RANDOM = "random"
    CONSISTENT_HASH = "consistent_hash"


@dataclass
class Partitioner:
    """消息分区器
    
    支持多种分区策略，确保同一业务实体的消息顺序性
    """
    
    num_partitions: int = 8
    strategy: PartitionStrategy = PartitionStrategy.KEY_HASH
    current_round_robin: int = 0
    _lock: Lock = field(default_factory=Lock)
    
    def get_partition(self, key: Optional[str] = None, 
                     message: Optional[Dict] = None) -> int:
        """获取消息应分配到的分区
        
        Args:
            key: 业务键（如用户ID、订单ID）
            message: 消息内容
        
        Returns:
            partition_id: 分区编号 (0..num_partitions-1)
        """
        with self._lock:
            if self.strategy == PartitionStrategy.ROUND_ROBIN:
                part = self.current_round_robin
                self.current_round_robin = (self.current_round_robin + 1) % self.num_partitions
                return part
                
            elif self.strategy == PartitionStrategy.KEY_HASH and key:
                return self._hash_partition(key)
                
            elif self.strategy == PartitionStrategy.CONSISTENT_HASH and key:
                return self._consistent_hash_partition(key)
                
            else:
                # 默认轮询
                part = self.current_round_robin
                self.current_round_robin = (self.current_round_robin + 1) % self.num_partitions
                return part
    
    def _hash_partition(self, key: str) -> int:
        """基于 Key 哈希分区"""
        hash_val = int(hashlib.md5(str(key).encode()).hexdigest(), 16)
        return hash_val % self.num_partitions
        
    def _consistent_hash_partition(self, key: str) -> int:
        """一致性哈希分区（简化版）"""
        # 简化实现：普通哈希分区
        return self._hash_partition(key)


@dataclass
class MessageQueuePartition:
    """单个分区的消息队列"""
    partition_id: int
    messages: deque = field(default_factory=deque)
    max_size: int = 10000
    _lock: Lock = field(default_factory=Lock)
    
    def enqueue(self, message: Dict) -> bool:
        """入队"""
        with self._lock:
            if len(self.messages) >= self.max_size:
                logger.warning(f"分区 {self.partition_id} 队列已满")
                return False
            self.messages.append(message)
            return True
            
    def dequeue(self, count: int = 10) -> List[Dict]:
        """批量出队"""
        with self._lock:
            batch = []
            for _ in range(min(count, len(self.messages))):
                batch.append(self.messages.popleft())
            return batch
            
    def size(self) -> int:
        """队列大小"""
        with self._lock:
            return len(self.messages)


class PartitionedMessageQueue:
    """分区化消息队列
    
    特点：
    - 多分区并行消费
    - 同一 Key 的消息顺序性保证
    - 支持分区扩展
    """
    
    def __init__(self, num_partitions: int = 8, 
                 partition_strategy: PartitionStrategy = PartitionStrategy.KEY_HASH):
        self.num_partitions = num_partitions
        self.partitioner = Partitioner(num_partitions, partition_strategy)
        self.partitions: List[MessageQueuePartition] = [
            MessageQueuePartition(partition_id=i) 
            for i in range(num_partitions)
        ]
        
    def publish(self, key: Optional[str], message: Dict) -> Tuple[int, bool]:
        """发布消息
        
        Returns:
            (partition_id, success)
        """
        partition_id = self.partitioner.get_partition(key, message)
        success = self.partitions[partition_id].enqueue(message)
        
        if success:
            logger.debug(f"[PMQ] 消息发布到分区 {partition_id} (key: {key})")
            
        return (partition_id, success)
        
    def consume_from_partition(self, partition_id: int, 
                               count: int = 10) -> List[Dict]:
        """从特定分区消费"""
        if 0 <= partition_id < self.num_partitions:
            return self.partitions[partition_id].dequeue(count)
        return []
        
    def consume_all(self, per_partition_count: int = 10) -> Dict[int, List[Dict]]:
        """从所有分区消费"""
        result = {}
        for i in range(self.num_partitions):
            batch = self.partitions[i].dequeue(per_partition_count)
            if batch:
                result[i] = batch
        return result
        
    def get_partition_stats(self) -> Dict[int, int]:
        """获取各分区大小"""
        return {p.partition_id: p.size() for p in self.partitions}


# ============================================
# 2. 批量处理器 (Batch Processing)
# ============================================


@dataclass
class BatchConfig:
    """批量配置"""
    max_batch_size: int = 100
    max_wait_ms: float = 1000.0  # 最多等待 1 秒
    min_batch_size: int = 1


class BatchProcessor:
    """批量消息处理器
    
    自动攒批，批量提交给下游处理
    """
    
    def __init__(self, process_func: Callable[[List[Dict]], Any],
                 config: BatchConfig = None):
        self.process_func = process_func
        self.config = config or BatchConfig()
        self.current_batch: List[Dict] = []
        self.last_flush_time = time.time()
        self._lock = Lock()
        
    def add(self, message: Dict):
        """添加单条消息"""
        with self._lock:
            self.current_batch.append(message)
            
            if len(self.current_batch) >= self.config.max_batch_size:
                self._flush()
            elif time.time() - self.last_flush_time >= self.config.max_wait_ms / 1000:
                if len(self.current_batch) >= self.config.min_batch_size:
                    self._flush()
                    
    def add_batch(self, messages: List[Dict]):
        """批量添加"""
        with self._lock:
            self.current_batch.extend(messages)
            if len(self.current_batch) >= self.config.max_batch_size:
                self._flush()
                
    def flush(self):
        """强制刷新"""
        with self._lock:
            self._flush()
            
    def _flush(self):
        """实际执行（外部需加锁）"""
        if not self.current_batch:
            return
            
        batch = self.current_batch.copy()
        self.current_batch.clear()
        self.last_flush_time = time.time()
        
        try:
            logger.debug(f"[Batch] 执行批量处理 {len(batch)} 条消息")
            self.process_func(batch)
        except Exception as e:
            logger.error(f"[Batch] 批量处理失败: {str(e)}")


# ============================================
# 3. 流量控制 (Traffic Shaping)
# ============================================


class TokenBucket:
    """令牌桶限流器"""
    
    def __init__(self, capacity: int = 1000, fill_rate: float = 100.0):
        """
        Args:
            capacity: 桶容量（最大突发量）
            fill_rate: 每秒补充的令牌数
        """
        self.capacity = capacity
        self.tokens = capacity
        self.fill_rate = fill_rate
        self.last_refill = time.time()
        self._lock = Lock()
        
    def acquire(self, tokens: int = 1) -> bool:
        """获取指定数量令牌"""
        with self._lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
            
    def acquire_wait(self, tokens: int = 1, timeout_ms: float = 1000.0) -> bool:
        """尝试获取，等待到超时"""
        start = time.time()
        while time.time() - start < timeout_ms / 1000:
            if self.acquire(tokens):
                return True
            time.sleep(0.001)
        return False
            
    def _refill(self):
        """补充令牌"""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.fill_rate)
        self.last_refill = now
        
    def get_available(self) -> float:
        """获取可用令牌数"""
        with self._lock:
            self._refill()
            return self.tokens


class LeakyBucket:
    """漏桶限流器 - 恒定速率流出"""
    
    def __init__(self, capacity: int = 1000, leak_rate: float = 100.0):
        self.capacity = capacity
        self.leak_rate = leak_rate
        self.water = 0.0
        self.last_leak = time.time()
        self._lock = Lock()
        
    def add(self, amount: float = 1.0) -> bool:
        """加水（请求）
        
        Returns:
            False 表示桶满，拒绝
        """
        with self._lock:
            self._leak()
            
            if self.water + amount <= self.capacity:
                self.water += amount
                return True
            return False
            
    def _leak(self):
        """漏水"""
        now = time.time()
        elapsed = now - self.last_leak
        leaked = elapsed * self.leak_rate
        self.water = max(0, self.water - leaked)
        self.last_leak = now


# ============================================
# 4. 消息压缩与序列化 (Serialization)
# ============================================


class MessageSerializer:
    """消息序列化与压缩"""
    
    def __init__(self, compression: bool = False):
        self.compression = compression
        
    def serialize(self, data: Dict) -> bytes:
        """序列化"""
        import json
        
        json_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
        
        if self.compression:
            import gzip
            return gzip.compress(json_bytes)
        else:
            return json_bytes
            
    def deserialize(self, data: bytes) -> Dict:
        """反序列化"""
        import json
        
        try:
            # 尝试解压
            import gzip
            decompressed = gzip.decompress(data)
            return json.loads(decompressed)
        except:
            # 不是 gzip，直接解析
            return json.loads(data)


# ============================================
# 5. 综合流控与分区的完整队列
# ============================================


class EnterpriseMessageQueue:
    """企业级消息队列
    
    整合：
    - 分区策略
    - 批量处理
    - 流量控制
    - 背压处理
    """
    
    def __init__(self, 
                 num_partitions: int = 8,
                 max_message_rate: float = 10000.0,
                 max_concurrent_consumers: int = 32):
        self.partitioned_queue = PartitionedMessageQueue(num_partitions)
        self.rate_limiter = TokenBucket(capacity=10000, fill_rate=max_message_rate)
        self.serializer = MessageSerializer()
        self.consumers: List[Callable] = []
        
    def publish_with_key(self, key: str, message: Dict) -> Tuple[int, bool]:
        """带 Key 发布（确保顺序性）"""
        if not self.rate_limiter.acquire():
            logger.warning("[EMQ] 限流触发，拒绝消息")
            return (-1, False)
            
        return self.partitioned_queue.publish(key, message)
        
    def subscribe_partitioned(self, consumer_func: Callable, 
                             partition_id: Optional[int] = None):
        """订阅消费者
        
        可以指定特定分区，或订阅全部
        """
        self.consumers.append( (consumer_func, partition_id) )
        
    def process(self):
        """处理队列中的消息"""
        stats = self.partitioned_queue.get_partition_stats()
        
        for consumer, part_id in self.consumers:
            if part_id is not None:
                # 消费特定分区
                messages = self.partitioned_queue.consume_from_partition(part_id, 100)
                if messages:
                    consumer(messages)
            else:
                # 消费全部
                partitions = self.partitioned_queue.consume_all(100)
                for pid, msgs in partitions.items():
                    consumer(msgs)
                    
    def get_stats(self) -> Dict[str, Any]:
        """获取队列统计"""
        return {
            "partitions": self.partitioned_queue.get_partition_stats(),
            "available_tokens": self.rate_limiter.get_available(),
        }
