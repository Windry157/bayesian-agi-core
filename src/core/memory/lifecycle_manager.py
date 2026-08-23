#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记忆生命周期管理器
管理记忆的短期、中期、长期存储和自动迁移。
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class MemoryLayer(Enum):
    """记忆层级"""
    SHORT_TERM = "short_term"
    MEDIUM_TERM = "medium_term"
    LONG_TERM = "long_term"


@dataclass
class LayerConfig:
    """层级配置"""
    capacity: int
    retention_hours: float
    promotion_threshold: float  # 晋升到上一层的重要性阈值
    demotion_threshold: float   # 降级到下一层的重要性阈值


@dataclass
class LifecycleEvent:
    """生命周期事件"""
    event_type: str  # "promote", "demote", "expire", "create"
    memory_id: str
    from_layer: Optional[str]
    to_layer: Optional[str]
    timestamp: str
    reason: str


class MemoryLifecycleManager:
    """记忆生命周期管理器

    管理记忆在不同层级间的自动迁移：
    - 短期记忆 -> 中期记忆 (通过访问频率和重要性)
    - 中期记忆 -> 长期记忆 (通过持续访问)
    - 过期清理
    """

    DEFAULT_CONFIGS = {
        MemoryLayer.SHORT_TERM: LayerConfig(
            capacity=100,
            retention_hours=24,
            promotion_threshold=0.7,
            demotion_threshold=0.0  # 短期记忆不会降级
        ),
        MemoryLayer.MEDIUM_TERM: LayerConfig(
            capacity=500,
            retention_hours=168,  # 7天
            promotion_threshold=0.85,
            demotion_threshold=0.3
        ),
        MemoryLayer.LONG_TERM: LayerConfig(
            capacity=2000,
            retention_hours=8760,  # 1年
            promotion_threshold=1.0,  # 长期记忆不会晋升
            demotion_threshold=0.1
        )
    }

    def __init__(self, configs: Optional[Dict[MemoryLayer, LayerConfig]] = None):
        """初始化生命周期管理器

        Args:
            configs: 层级配置，None则使用默认配置
        """
        self.configs = configs or self.DEFAULT_CONFIGS
        self.events: List[LifecycleEvent] = []
        logger.info("MemoryLifecycleManager initialized")

    def should_promote(
        self,
        memory: Dict[str, Any],
        current_layer: MemoryLayer
    ) -> bool:
        """检查记忆是否应该晋升到上一层

        Args:
            memory: 记忆数据
            current_layer: 当前层级

        Returns:
            bool: 是否应该晋升
        """
        if current_layer == MemoryLayer.LONG_TERM:
            return False  # 已经是最高层

        config = self.configs[current_layer]
        importance = memory.get('importance', 0.5)
        access_count = memory.get('access_count', 0)

        # 晋升条件：重要性足够高 或者 访问频繁
        should_promote = (
            importance >= config.promotion_threshold or
            access_count >= 10
        )

        if should_promote:
            logger.debug(f"Memory {memory['id']} qualifies for promotion")

        return should_promote

    def should_demote(
        self,
        memory: Dict[str, Any],
        current_layer: MemoryLayer
    ) -> bool:
        """检查记忆是否应该降级到下一层

        Args:
            memory: 记忆数据
            current_layer: 当前层级

        Returns:
            bool: 是否应该降级
        """
        if current_layer == MemoryLayer.SHORT_TERM:
            return False  # 已经是最低层

        config = self.configs[current_layer]
        importance = memory.get('importance', 0.5)
        last_accessed = memory.get('last_accessed')

        # 计算年龄
        if last_accessed:
            try:
                age_hours = (
                    datetime.now() - datetime.fromisoformat(last_accessed)
                ).total_seconds() / 3600
            except (ValueError, TypeError):
                age_hours = 0
        else:
            age_hours = float('inf')

        # 降级条件：重要性低 且 很久没访问
        should_demote = (
            importance < config.demotion_threshold and
            age_hours > config.retention_hours / 2
        )

        if should_demote:
            logger.debug(f"Memory {memory['id']} qualifies for demotion")

        return should_demote

    def should_expire(
        self,
        memory: Dict[str, Any],
        layer: MemoryLayer
    ) -> bool:
        """检查记忆是否应该过期删除

        Args:
            memory: 记忆数据
            layer: 当前层级

        Returns:
            bool: 是否应该过期
        """
        config = self.configs[layer]
        created_at = memory.get('created_at')

        if not created_at:
            return False

        try:
            age_hours = (
                datetime.now() - datetime.fromisoformat(created_at)
            ).total_seconds() / 3600
        except (ValueError, TypeError):
            return False

        # 过期条件：超过保留时间 且 重要性低
        importance = memory.get('importance', 0.5)
        should_expire = (
            age_hours > config.retention_hours and
            importance < 0.3
        )

        if should_expire:
            logger.debug(f"Memory {memory['id']} qualifies for expiration")

        return should_expire

    def get_next_layer(
        self,
        current_layer: MemoryLayer
    ) -> Optional[MemoryLayer]:
        """获取上一层级

        Args:
            current_layer: 当前层级

        Returns:
            Optional[MemoryLayer]: 上一层级，None如果已到顶
        """
        layers = list(MemoryLayer)
        idx = layers.index(current_layer)
        if idx < len(layers) - 1:
            return layers[idx + 1]
        return None

    def get_previous_layer(
        self,
        current_layer: MemoryLayer
    ) -> Optional[MemoryLayer]:
        """获取下一层级

        Args:
            current_layer: 当前层级

        Returns:
            Optional[MemoryLayer]: 下一层级，None如果已到底
        """
        layers = list(MemoryLayer)
        idx = layers.index(current_layer)
        if idx > 0:
            return layers[idx - 1]
        return None

    def process_lifecycle(
        self,
        memories_by_layer: Dict[MemoryLayer, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """处理一批记忆的生命周期

        Args:
            memories_by_layer: 按层级分组的记忆

        Returns:
            Dict[str, Any]: 处理结果，包含迁移和删除的记忆
        """
        events = []
        to_promote = []  # (memory, from_layer, to_layer)
        to_demote = []   # (memory, from_layer, to_layer)
        to_delete = []   # (memory, layer)

        # 检查每个层级的记忆
        for layer in MemoryLayer:
            memories = memories_by_layer.get(layer, [])

            for mem in memories:
                # 检查过期
                if self.should_expire(mem, layer):
                    to_delete.append((mem, layer))
                    events.append(LifecycleEvent(
                        event_type="expire",
                        memory_id=mem['id'],
                        from_layer=layer.value,
                        to_layer=None,
                        timestamp=datetime.now().isoformat(),
                        reason="expired"
                    ))
                    continue

                # 检查晋升
                if self.should_promote(mem, layer):
                    next_layer = self.get_next_layer(layer)
                    if next_layer:
                        to_promote.append((mem, layer, next_layer))
                        events.append(LifecycleEvent(
                            event_type="promote",
                            memory_id=mem['id'],
                            from_layer=layer.value,
                            to_layer=next_layer.value,
                            timestamp=datetime.now().isoformat(),
                            reason="high_importance"
                        ))
                    continue

                # 检查降级
                if self.should_demote(mem, layer):
                    prev_layer = self.get_previous_layer(layer)
                    if prev_layer:
                        to_demote.append((mem, layer, prev_layer))
                        events.append(LifecycleEvent(
                            event_type="demote",
                            memory_id=mem['id'],
                            from_layer=layer.value,
                            to_layer=prev_layer.value,
                            timestamp=datetime.now().isoformat(),
                            reason="low_usage"
                        ))

        self.events.extend(events)

        return {
            "promoted": to_promote,
            "demoted": to_demote,
            "deleted": to_delete,
            "events": events
        }

    def enforce_capacity(
        self,
        memories: List[Dict[str, Any]],
        layer: MemoryLayer
    ) -> List[Dict[str, Any]]:
        """强制层级容量限制

        当超过容量时，删除最不重要的记忆。

        Args:
            memories: 记忆列表
            layer: 层级

        Returns:
            List[Dict[str, Any]]: 过滤后的记忆列表
        """
        config = self.configs[layer]

        if len(memories) <= config.capacity:
            return memories

        # 按重要性和最近访问排序
        def sort_key(m: Dict[str, Any]) -> float:
            importance = m.get('importance', 0.5)
            last_accessed = m.get('last_accessed')
            if last_accessed:
                try:
                    recency = 1.0 / (
                        1 + (datetime.now() - datetime.fromisoformat(last_accessed)).total_seconds() / 3600
                    )
                except (ValueError, TypeError):
                    recency = 0
            else:
                recency = 0
            return importance * 0.7 + recency * 0.3

        sorted_memories = sorted(memories, key=sort_key, reverse=True)
        kept = sorted_memories[:config.capacity]

        removed_count = len(memories) - len(kept)
        if removed_count > 0:
            logger.info(
                f"Removed {removed_count} memories from {layer.value} "
                f"due to capacity limit ({config.capacity})"
            )

        return kept

    def get_stats(self) -> Dict[str, Any]:
        """获取生命周期统计

        Returns:
            Dict[str, Any]: 统计信息
        """
        event_counts = {}
        for event in self.events:
            et = event.event_type
            event_counts[et] = event_counts.get(et, 0) + 1

        return {
            "total_events": len(self.events),
            "event_counts": event_counts,
            "configs": {
                layer.value: {
                    "capacity": cfg.capacity,
                    "retention_hours": cfg.retention_hours
                }
                for layer, cfg in self.configs.items()
            }
        }

    def clear_events(self):
        """清空事件历史"""
        self.events.clear()
        logger.info("Lifecycle events cleared")
