#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
离线模式支持模块
提供网络不可用时的降级方案
"""

import os
import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps

logger = logging.getLogger(__name__)

# 默认离线配置
OFFLINE_CONFIG = {
    "use_offline_mode": False,
    "allow_fallback": True,
    "skip_network_checks": False,
    "cached_models_dir": "models_cache"
}


class OfflineMode:
    """离线模式管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.offline_mode = os.environ.get("OFFLINE_MODE", "false").lower() == "true"
        self.fallback_enabled = True
        self._load_config()
        logger.info(f"离线模式: {'启用' if self.offline_mode else '禁用'}")
    
    def _load_config(self):
        """加载离线配置"""
        config_path = os.environ.get("OFFLINE_CONFIG", "config/offline-mode.json")
        if os.path.exists(config_path):
            try:
                import json
                with open(config_path, 'r', encoding='utf-8') as f:
                    OFFLINE_CONFIG.update(json.load(f))
                self.offline_mode = OFFLINE_CONFIG.get("use_offline_mode", self.offline_mode)
                logger.info(f"离线配置已加载: {config_path}")
            except Exception as e:
                logger.warning(f"加载离线配置失败: {e}")
    
    def is_offline(self) -> bool:
        """检查是否离线模式"""
        return self.offline_mode
    
    def enable_offline(self):
        """启用离线模式"""
        self.offline_mode = True
        logger.info("离线模式已启用")
    
    def disable_offline(self):
        """禁用离线模式"""
        self.offline_mode = False
        logger.info("离线模式已禁用")
    
    def require_network(self, component: str, fallback_func=None):
        """
        装饰器：需要网络的组件
        
        Args:
            component: 组件名称
            fallback_func: 降级函数
        """
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                if self.offline_mode:
                    logger.warning(f"离线模式: 跳过 {component}")
                    if fallback_func:
                        if asyncio.iscoroutinefunction(fallback_func):
                            return await fallback_func(*args, **kwargs)
                        else:
                            return fallback_func(*args, **kwargs)
                    return None
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"{component} 网络错误: {e}")
                    if self.fallback_enabled and fallback_func:
                        logger.info(f"使用降级方案: {component}")
                        if asyncio.iscoroutinefunction(fallback_func):
                            return await fallback_func(*args, **kwargs)
                        else:
                            return fallback_func(*args, **kwargs)
                    raise
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                if self.offline_mode:
                    logger.warning(f"离线模式: 跳过 {component}")
                    if fallback_func:
                        return fallback_func(*args, **kwargs)
                    return None
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"{component} 网络错误: {e}")
                    if self.fallback_enabled and fallback_func:
                        logger.info(f"使用降级方案: {component}")
                        return fallback_func(*args, **kwargs)
                    raise
            
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        return decorator
    
    @staticmethod
    def create_fallback_vector_index():
        """创建降级向量索引（简单关键词匹配）"""
        class SimpleVectorIndex:
            def __init__(self, persist_dir=None, *args, **kwargs):
                self.memories = []
                self.persist_dir = persist_dir
            
            def add(self, texts, metadatas=None, ids=None):
                """添加记忆"""
                if isinstance(texts, str):
                    texts = [texts]
                if metadatas is None:
                    metadatas = [{} for _ in texts]
                if ids is None:
                    import uuid
                    ids = [str(uuid.uuid4()) for _ in texts]
                
                for i, text in enumerate(texts):
                    self.memories.append({
                        "id": ids[i],
                        "text": text,
                        "metadata": metadatas[i] if i < len(metadatas) else {}
                    })
            
            def query(self, query_texts, n_results=5, *args, **kwargs):
                """查询记忆"""
                if isinstance(query_texts, str):
                    query_texts = [query_texts]
                
                all_results = []
                for query in query_texts:
                    results = []
                    query_lower = query.lower()
                    
                    for memory in self.memories:
                        score = 0.0
                        # 简单关键词匹配评分
                        if query_lower in memory["text"].lower():
                            score = 1.0
                        else:
                            # 部分词匹配
                            query_words = set(query_lower.split())
                            text_words = set(memory["text"].lower().split())
                            if query_words and text_words:
                                overlap = len(query_words & text_words)
                                score = overlap / len(query_words)
                        
                        if score > 0:
                            results.append({
                                "id": memory["id"],
                                "text": memory["text"],
                                "metadata": memory["metadata"],
                                "score": score
                            })
                    
                    # 按分数排序
                    results.sort(key=lambda x: x["score"], reverse=True)
                    all_results.append(results[:n_results])
                
                return {
                    "ids": [[r["id"] for r in results] for results in all_results],
                    "documents": [[r["text"] for r in results] for results in all_results],
                    "metadatas": [[r["metadata"] for r in results] for results in all_results],
                    "distances": [[1.0 - r["score"] for r in results] for results in all_results]
                }
            
            def delete(self, ids):
                """删除记忆"""
                if isinstance(ids, str):
                    ids = [ids]
                self.memories = [m for m in self.memories if m["id"] not in ids]
            
            def persist(self):
                """持久化（简单实现）"""
                if self.persist_dir:
                    import json
                    os.makedirs(self.persist_dir, exist_ok=True)
                    with open(os.path.join(self.persist_dir, "simple_index.json"), 'w', encoding='utf-8') as f:
                        json.dump(self.memories, f, ensure_ascii=False, indent=2)
        
        return SimpleVectorIndex
    
    @staticmethod
    def create_fallback_entity_extractor():
        """创建降级实体抽取器（仅规则）"""
        try:
            from src.core.knowledge_graph.entity_extractor import EntityExtractor
            return EntityExtractor(use_llm=False)
        except ImportError:
            # 如果没有模块，返回简单抽取器
            class SimpleEntityExtractor:
                def __init__(self, *args, **kwargs):
                    pass
                
                def extract(self, text):
                    """简单抽取：返回空列表"""
                    return []
            
            return SimpleEntityExtractor()


# 全局实例
offline_mode = OfflineMode()
