#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bayesian-AGI-Core Python SDK Client
"""

import httpx
import json
from typing import List, Dict, Optional, Any

class BayesianAGICoreClient:
    """Bayesian-AGI-Core Python SDK Client"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """初始化客户端
        
        Args:
            base_url: API Gateway的基础URL
        """
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url, timeout=30.0)
    
    async def __aenter__(self):
        """进入异步上下文管理器"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出异步上下文管理器"""
        await self.close()
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()
    
    async def health_check(self) -> Dict[str, str]:
        """健康检查
        
        Returns:
            健康检查结果
        """
        response = await self.client.get("/health")
        response.raise_for_status()
        return response.json()
    
    async def get_models(self) -> List[Dict[str, Any]]:
        """获取模型列表
        
        Returns:
            模型列表
        """
        response = await self.client.get("/api/models")
        response.raise_for_status()
        return response.json().get("models", [])
    
    async def add_memory(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """添加记忆
        
        Args:
            content: 记忆内容
            metadata: 记忆元数据
            
        Returns:
            记忆ID
        """
        data = {"content": content}
        if metadata:
            data["metadata"] = metadata
        response = await self.client.post("/api/memory", json=data)
        response.raise_for_status()
        return response.json().get("id")
    
    async def search_memory(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """检索记忆
        
        Args:
            query: 查询内容
            top_k: 返回的记忆数量
            
        Returns:
            检索到的记忆列表
        """
        response = await self.client.get("/api/memory/search", params={"query": query, "top_k": top_k})
        response.raise_for_status()
        return response.json().get("memories", [])
    
    async def make_decision(self, possible_actions: List[str]) -> str:
        """做出决策
        
        Args:
            possible_actions: 可能的行动列表
            
        Returns:
            选择的行动
        """
        response = await self.client.post("/api/decision", json={"possible_actions": possible_actions})
        response.raise_for_status()
        return response.json().get("decision")
    
    async def classify_image(self, image_path: str) -> Dict[str, Any]:
        """图像分类
        
        Args:
            image_path: 图像路径
            
        Returns:
            分类结果
        """
        with open(image_path, "rb") as f:
            files = {"file": (image_path.split("/")[-1], f.read())}
            response = await self.client.post("/api/vision/classify", files=files)
            response.raise_for_status()
            return response.json()
    
    async def detect_objects(self, image_path: str) -> Dict[str, Any]:
        """目标检测
        
        Args:
            image_path: 图像路径
            
        Returns:
            检测结果
        """
        with open(image_path, "rb") as f:
            files = {"file": (image_path.split("/")[-1], f.read())}
            response = await self.client.post("/api/vision/detect", files=files)
            response.raise_for_status()
            return response.json()
    
    async def describe_image(self, image_path: str) -> Dict[str, Any]:
        """图像描述
        
        Args:
            image_path: 图像路径
            
        Returns:
            描述结果
        """
        with open(image_path, "rb") as f:
            files = {"file": (image_path.split("/")[-1], f.read())}
            response = await self.client.post("/api/vision/describe", files=files)
            response.raise_for_status()
            return response.json()
