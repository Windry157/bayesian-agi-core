#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
状态持久化模块
负责认知状态的持久化和加载
"""

import json
import logging
import asyncio
import os
from datetime import datetime
from typing import Dict, Optional, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class StatePersistence:
    """状态持久化
    
    负责认知状态的持久化和加载
    """
    
    def __init__(self, persistence_dir: str = "memory/cognitive_state"):
        """初始化状态持久化
        
        Args:
            persistence_dir: 状态持久化目录
        """
        self.persistence_dir = persistence_dir
        self.cognitive_state: Dict[str, Any] = {}
        
        # 确保持久化目录存在
        os.makedirs(self.persistence_dir, exist_ok=True)
        
        # 加载已有的认知状态
        self._load_state()
        
        logger.info("状态持久化模块初始化完成")
    
    async def load_cognitive_state(self) -> Dict[str, Any]:
        """加载认知状态
        
        Returns:
            认知状态
        """
        try:
            # 加载状态
            self._load_state()
            
            # 如果状态为空，初始化默认状态
            if not self.cognitive_state:
                self._initialize_default_state()
            
            logger.info("加载认知状态完成")
            return self.cognitive_state
            
        except Exception as e:
            logger.error(f"加载认知状态失败: {e}")
            # 返回默认状态
            return self._initialize_default_state()
    
    async def update_state(self, response: Dict[str, Any]):
        """更新认知状态
        
        Args:
            response: 响应数据
        """
        try:
            # 更新认知状态
            self._update_from_response(response)
            
            # 持久化状态
            self._save_state()
            
            logger.info("更新认知状态完成")
            
        except Exception as e:
            logger.error(f"更新认知状态失败: {e}")
    
    def _load_state(self):
        """从文件加载状态"""
        state_file = os.path.join(self.persistence_dir, "cognitive_state.json")
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    self.cognitive_state = json.load(f)
                logger.info("从文件加载认知状态")
            except Exception as e:
                logger.error(f"从文件加载状态失败: {e}")
                self.cognitive_state = {}
    
    def _save_state(self):
        """保存状态到文件"""
        state_file = os.path.join(self.persistence_dir, "cognitive_state.json")
        try:
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(self.cognitive_state, f, ensure_ascii=False, indent=2)
            logger.info("保存认知状态到文件")
        except Exception as e:
            logger.error(f"保存状态失败: {e}")
    
    def _initialize_default_state(self) -> Dict[str, Any]:
        """初始化默认状态
        
        Returns:
            默认认知状态
        """
        self.cognitive_state = {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "personality": {
                "traits": {
                    "curiosity": 0.7,
                    "creativity": 0.6,
                    "consistency": 0.8
                },
                "mood": "neutral",
                "energy": 0.8
            },
            "knowledge": {
                "domains": [],
                "skills": [],
                "confidence": {}
            },
            "preferences": {
                "learning_style": "active",
                "communication_style": "direct",
                "topics": []
            },
            "performance": {
                "recent_accuracy": 0.8,
                "learning_rate": 0.1,
                "success_rate": 0.75
            },
            "goals": {
                "short_term": [],
                "medium_term": [],
                "long_term": []
            }
        }
        return self.cognitive_state
    
    def _update_from_response(self, response: Dict[str, Any]):
        """从响应更新状态
        
        Args:
            response: 响应数据
        """
        # 更新最后更新时间
        self.cognitive_state["last_updated"] = datetime.now().isoformat()
        
        # 更新性能指标
        if "accuracy" in response:
            self.cognitive_state["performance"]["recent_accuracy"] = response["accuracy"]
        
        # 更新知识领域
        if "domains" in response:
            for domain in response["domains"]:
                if domain not in self.cognitive_state["knowledge"]["domains"]:
                    self.cognitive_state["knowledge"]["domains"].append(domain)
        
        # 更新技能
        if "skills" in response:
            for skill in response["skills"]:
                if skill not in self.cognitive_state["knowledge"]["skills"]:
                    self.cognitive_state["knowledge"]["skills"].append(skill)
        
        # 更新目标
        if "goals" in response:
            if "short_term" in response["goals"]:
                self.cognitive_state["goals"]["short_term"] = response["goals"]["short_term"]
            if "medium_term" in response["goals"]:
                self.cognitive_state["goals"]["medium_term"] = response["goals"]["medium_term"]
            if "long_term" in response["goals"]:
                self.cognitive_state["goals"]["long_term"] = response["goals"]["long_term"]
    
    def get_state_summary(self) -> Dict[str, Any]:
        """获取状态摘要
        
        Returns:
            状态摘要
        """
        return {
            "last_updated": self.cognitive_state.get("last_updated", "N/A"),
            "personality": self.cognitive_state.get("personality", {}),
            "knowledge_domains": len(self.cognitive_state.get("knowledge", {}).get("domains", [])),
            "skills": len(self.cognitive_state.get("knowledge", {}).get("skills", [])),
            "performance": self.cognitive_state.get("performance", {})
        }
    
    def reset_state(self):
        """重置认知状态"""
        self._initialize_default_state()
        self._save_state()
        logger.info("重置认知状态")


# 全局状态持久化实例
state_persistence = StatePersistence()