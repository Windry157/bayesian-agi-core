#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bayesian-AGI-Core Python SDK Client
"""

import httpx
from typing import Dict, List, Optional, Any
from .exceptions import APIError


class BayesianAGIClient:
    """Bayesian-AGI-Core Python SDK Client
    
    用于与Bayesian-AGI-Core的API进行交互
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """初始化客户端
        
        Args:
            base_url: API Gateway的基础URL
        """
        self.base_url = base_url
        self.client = httpx.Client(timeout=30.0)
    
    def get_models(self) -> Dict[str, Any]:
        """获取模型列表
        
        Returns:
            模型列表
        """
        response = self.client.get(f"{self.base_url}/api/models")
        if response.status_code == 200:
            return response.json()
        raise APIError(f"Failed to get models: {response.text}", response.status_code)
    
    def add_memory(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """添加记忆
        
        Args:
            content: 记忆内容
            metadata: 记忆元数据
            
        Returns:
            添加记忆的结果
        """
        data = {"content": content}
        if metadata:
            data["metadata"] = metadata
        response = self.client.post(f"{self.base_url}/api/memory", json=data)
        if response.status_code == 200:
            return response.json()
        raise APIError(f"Failed to add memory: {response.text}", response.status_code)
    
    def search_memory(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """检索记忆
        
        Args:
            query: 查询内容
            top_k: 返回的记忆数量
            
        Returns:
            检索到的记忆列表
        """
        params = {"query": query, "top_k": top_k}
        response = self.client.get(f"{self.base_url}/api/memory/search", params=params)
        if response.status_code == 200:
            return response.json()
        raise APIError(f"Failed to search memory: {response.text}", response.status_code)
    
    def make_decision(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """做出决策
        
        Args:
            data: 决策数据
            
        Returns:
            决策结果
        """
        response = self.client.post(f"{self.base_url}/api/decision", json=data)
        if response.status_code == 200:
            return response.json()
        raise APIError(f"Failed to make decision: {response.text}", response.status_code)
    
    def classify_image(self, image_path: str) -> Dict[str, Any]:
        """图像分类
        
        Args:
            image_path: 图像路径
            
        Returns:
            分类结果
        """
        with open(image_path, "rb") as f:
            files = {"file": f}
            response = self.client.post(f"{self.base_url}/api/vision/classify", files=files)
            if response.status_code == 200:
                return response.json()
            raise APIError(f"Failed to classify image: {response.text}", response.status_code)
    
    def detect_objects(self, image_path: str) -> Dict[str, Any]:
        """目标检测
        
        Args:
            image_path: 图像路径
            
        Returns:
            检测结果
        """
        with open(image_path, "rb") as f:
            files = {"file": f}
            response = self.client.post(f"{self.base_url}/api/vision/detect", files=files)
            if response.status_code == 200:
                return response.json()
            raise APIError(f"Failed to detect objects: {response.text}", response.status_code)
    
    def describe_image(self, image_path: str) -> Dict[str, Any]:
        """图像描述
        
        Args:
            image_path: 图像路径
            
        Returns:
            描述结果
        """
        with open(image_path, "rb") as f:
            files = {"file": f}
            response = self.client.post(f"{self.base_url}/api/vision/describe", files=files)
            if response.status_code == 200:
                return response.json()
            raise APIError(f"Failed to describe image: {response.text}", response.status_code)
    
    def process_text(self, text: str, task: str) -> Dict[str, Any]:
        """处理文本输入
        
        Args:
            text: 文本内容
            task: 任务类型
            
        Returns:
            处理结果
        """
        data = {"text": text, "task": task}
        response = self.client.post(f"{self.base_url}/api/multimodal/text", data=data)
        if response.status_code == 200:
            return response.json()
        raise APIError(f"Failed to process text: {response.text}", response.status_code)
    
    def process_image(self, image_path: str, task: str) -> Dict[str, Any]:
        """处理图像输入
        
        Args:
            image_path: 图像路径
            task: 任务类型
            
        Returns:
            处理结果
        """
        with open(image_path, "rb") as f:
            files = {"file": f}
            data = {"task": task}
            response = self.client.post(f"{self.base_url}/api/multimodal/image", data=data, files=files)
            if response.status_code == 200:
                return response.json()
            raise APIError(f"Failed to process image: {response.text}", response.status_code)
    
    def process_audio(self, audio_path: str, task: str) -> Dict[str, Any]:
        """处理音频输入
        
        Args:
            audio_path: 音频路径
            task: 任务类型
            
        Returns:
            处理结果
        """
        with open(audio_path, "rb") as f:
            files = {"file": f}
            data = {"task": task}
            response = self.client.post(f"{self.base_url}/api/multimodal/audio", data=data, files=files)
            if response.status_code == 200:
                return response.json()
            raise APIError(f"Failed to process audio: {response.text}", response.status_code)
    
    def get_supported_input_types(self) -> Dict[str, Any]:
        """获取支持的输入类型
        
        Returns:
            支持的输入类型
        """
        response = self.client.get(f"{self.base_url}/api/multimodal/supported-input-types")
        if response.status_code == 200:
            return response.json()
        raise APIError(f"Failed to get supported input types: {response.text}", response.status_code)
    
    def get_supported_tasks(self) -> Dict[str, Any]:
        """获取支持的任务类型
        
        Returns:
            支持的任务类型
        """
        response = self.client.get(f"{self.base_url}/api/multimodal/supported-tasks")
        if response.status_code == 200:
            return response.json()
        raise APIError(f"Failed to get supported tasks: {response.text}", response.status_code)
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查
        
        Returns:
            健康检查结果
        """
        response = self.client.get(f"{self.base_url}/health")
        if response.status_code == 200:
            return response.json()
        raise APIError(f"Failed to health check: {response.text}", response.status_code)
    
    def services_health_check(self) -> Dict[str, Any]:
        """服务健康检查
        
        Returns:
            服务健康检查结果
        """
        response = self.client.get(f"{self.base_url}/health/services")
        if response.status_code == 200:
            return response.json()
        raise APIError(f"Failed to services health check: {response.text}", response.status_code)
    
    def close(self):
        """关闭客户端"""
        self.client.close()