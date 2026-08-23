#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上下文桥接器
负责跨会话上下文管理和桥接
"""

import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils.data_cache import DataCache

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ContextBridge:
    """上下文桥接器
    
    负责跨会话的上下文管理和桥接，打破会话隔离
    """
    
    def __init__(self):
        """初始化上下文桥接器"""
        # 会话上下文缓存
        self.session_contexts: Dict[str, Dict[str, Any]] = {}
        # 全局上下文图谱
        self.global_context: Dict[str, Any] = {}
        # 上下文缓存
        self.context_cache = DataCache(max_size=1000, ttl=3600)
        # 上下文相似度阈值
        self.similarity_threshold = 0.7
        
        logger.info("上下文桥接器初始化完成")
    
    async def load_relevant_context(self, session_id: str, query: Optional[str] = None) -> Dict[str, Any]:
        """加载相关上下文
        
        Args:
            session_id: 会话ID
            query: 当前查询（用于相似度匹配）
            
        Returns:
            相关上下文信息
        """
        try:
            # 1. 加载会话上下文
            session_context = self.session_contexts.get(session_id, {})
            
            # 2. 加载全局上下文
            global_context = self.global_context.copy()
            
            # 3. 基于查询获取相关历史上下文
            relevant_history = []
            if query:
                relevant_history = await self._find_relevant_history(query)
            
            # 4. 整合上下文
            combined_context = {
                "session_context": session_context,
                "global_context": global_context,
                "relevant_history": relevant_history,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"为会话 {session_id} 加载上下文")
            return combined_context
            
        except Exception as e:
            logger.error(f"加载上下文失败: {e}")
            return {"error": str(e)}
    
    async def update_session_context(self, session_id: str, context: Dict[str, Any]):
        """更新会话上下文
        
        Args:
            session_id: 会话ID
            context: 要更新的上下文
        """
        try:
            if session_id not in self.session_contexts:
                self.session_contexts[session_id] = {
                    "messages": [],
                    "metadata": {},
                    "last_updated": datetime.now().isoformat()
                }
            
            # 更新会话上下文
            self.session_contexts[session_id].update({
                "messages": context.get("messages", []),
                "metadata": context.get("metadata", {}),
                "last_updated": datetime.now().isoformat()
            })
            
            # 更新全局上下文
            self._update_global_context(context)
            
            logger.info(f"更新会话 {session_id} 的上下文")
            
        except Exception as e:
            logger.error(f"更新上下文失败: {e}")
    
    async def _find_relevant_history(self, query: str) -> List[Dict[str, Any]]:
        """查找相关历史上下文

        Args:
            query: 查询文本

        Returns:
            相关历史上下文列表
        """
        relevant_history = []

        # 1. 首先检查缓存
        cache_key = f"relevant_history:{query[:50]}"
        cached_result = self.context_cache.get(cache_key)
        if cached_result:
            return cached_result

        # 2. 遍历所有会话的上下文
        for session_id, session_context in self.session_contexts.items():
            messages = session_context.get("messages", [])
            for message in messages:
                content = message.get("content", "")
                if content:
                    # 计算相似度
                    similarity = self._calculate_similarity(query, content)
                    if similarity > self.similarity_threshold:
                        relevant_history.append({
                            "session_id": session_id,
                            "message": message,
                            "timestamp": message.get("timestamp", datetime.now().isoformat()),
                            "similarity": similarity
                        })

        # 3. 按相似度排序
        relevant_history.sort(key=lambda x: x.get("similarity", 0), reverse=True)

        # 4. 限制返回数量
        result = relevant_history[:5]

        # 5. 缓存结果
        self.context_cache.set(cache_key, result, ttl=600)  # 缓存10分钟

        return result
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度

        Args:
            text1: 文本1
            text2: 文本2

        Returns:
            相似度得分（0-1）
        """
        # 简单的词袋相似度计算
        set1 = set(self._extract_keywords(text1))
        set2 = set(self._extract_keywords(text2))
        
        if not set1 and not set2:
            return 0.0
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def _update_global_context(self, context: Dict[str, Any]):
        """更新全局上下文

        Args:
            context: 上下文信息
        """
        # 提取关键信息更新全局上下文
        messages = context.get("messages", [])
        for message in messages:
            content = message.get("content", "")
            role = message.get("role", "")
            if content:
                # 1. 提取关键词
                keywords = self._extract_keywords(content)
                
                # 2. 更新关键词统计
                for keyword in keywords:
                    if keyword not in self.global_context:
                        self.global_context[keyword] = {
                            "count": 0,
                            "last_seen": datetime.now().isoformat(),
                            "roles": {"user": 0, "assistant": 0}
                        }
                    self.global_context[keyword]["count"] += 1
                    self.global_context[keyword]["last_seen"] = datetime.now().isoformat()
                    if role in ["user", "assistant"]:
                        self.global_context[keyword]["roles"][role] += 1
                
                # 3. 提取实体（如果有）
                entities = self._extract_entities(content)
                for entity in entities:
                    entity_key = f"entity:{entity}"
                    if entity_key not in self.global_context:
                        self.global_context[entity_key] = {
                            "count": 0,
                            "last_seen": datetime.now().isoformat(),
                            "type": "unknown"
                        }
                    self.global_context[entity_key]["count"] += 1
                    self.global_context[entity_key]["last_seen"] = datetime.now().isoformat()
        
        # 4. 清理过期的全局上下文
        self._cleanup_global_context()
    
    def _extract_entities(self, text: str) -> List[str]:
        """提取实体

        Args:
            text: 文本内容

        Returns:
            实体列表
        """
        # 简单的实体提取
        import re
        # 提取可能的实体（大写开头的词、带空格的短语等）
        entities = []
        
        # 提取大写开头的词
        proper_nouns = re.findall(r'\b[A-Z][a-z]+\b', text)
        entities.extend(proper_nouns)
        
        # 提取连续的大写开头的词（如"New York"）
        noun_phrases = re.findall(r'\b([A-Z][a-z]+(\s+[A-Z][a-z]+)+)\b', text)
        for phrase, _ in noun_phrases:
            entities.append(phrase)
        
        return entities[:5]  # 限制数量
    
    def _cleanup_global_context(self):
        """清理过期的全局上下文
        
        移除低频和过期的上下文信息
        """
        current_time = datetime.now()
        to_remove = []
        
        for key, value in self.global_context.items():
            # 移除计数小于3的项
            if value.get("count", 0) < 3:
                to_remove.append(key)
                continue
            
            # 移除超过7天未更新的项
            last_seen = datetime.fromisoformat(value.get("last_seen", datetime.now().isoformat()))
            if (current_time - last_seen).days > 7:
                to_remove.append(key)
        
        for key in to_remove:
            del self.global_context[key]
        
        # 限制全局上下文大小
        if len(self.global_context) > 1000:
            # 按计数排序，保留前1000个
            sorted_items = sorted(
                self.global_context.items(),
                key=lambda x: x[1].get("count", 0),
                reverse=True
            )
            self.global_context = dict(sorted_items[:1000])
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词
        
        Args:
            text: 文本内容
            
        Returns:
            关键词列表
        """
        # 简化实现，实际应该使用NLP库
        import re
        # 提取长度大于2的词
        words = re.findall(r'\b\w{3,}\b', text.lower())
        # 过滤常见停用词
        stop_words = set(["the", "and", "is", "in", "to", "of", "for", "with", "on"])
        return [word for word in words if word not in stop_words][:10]
    
    def get_session_contexts(self) -> Dict[str, Dict[str, Any]]:
        """获取所有会话上下文
        
        Returns:
            会话上下文字典
        """
        return self.session_contexts
    
    def clear_session_context(self, session_id: str):
        """清除会话上下文
        
        Args:
            session_id: 会话ID
        """
        if session_id in self.session_contexts:
            del self.session_contexts[session_id]
            logger.info(f"清除会话 {session_id} 的上下文")
    
    def get_global_context(self) -> Dict[str, Any]:
        """获取全局上下文
        
        Returns:
            全局上下文
        """
        return self.global_context


# 全局上下文桥接器实例
context_bridge = ContextBridge()