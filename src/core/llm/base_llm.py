#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM基础接口
"""

from abc import ABC, abstractmethod
from typing import List, Dict, AsyncGenerator, Any


class BaseLLM(ABC):
    """LLM基础接口"""
    
    @abstractmethod
    async def stream_chat(self, messages: List[Dict], tools: List[Dict] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """流式聊天
        
        Args:
            messages: 消息列表
            tools: 工具列表
            
        Returns:
            流式生成的响应
        """
        pass
    
    @abstractmethod
    async def get_available_models(self) -> List[Dict[str, Any]]:
        """获取可用模型
        
        Returns:
            模型列表
        """
        pass
