#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP客户端模块
负责管理HTTP连接池，减少网络连接建立时间
"""

import httpx
from typing import Dict, Optional, Any


class HttpClientManager:
    """HTTP客户端管理器
    
    管理HTTP连接池，减少网络连接建立时间
    """
    
    def __init__(self):
        """初始化HTTP客户端管理器"""
        self.clients: Dict[str, httpx.AsyncClient] = {}
        self.sync_clients: Dict[str, httpx.Client] = {}
    
    async def get_client(self, base_url: Optional[str] = None) -> httpx.AsyncClient:
        """获取异步HTTP客户端
        
        Args:
            base_url: 基础URL
            
        Returns:
            异步HTTP客户端
        """
        key = base_url or "default"
        if key not in self.clients:
            self.clients[key] = httpx.AsyncClient(
                base_url=base_url,
                timeout=30.0,
                follow_redirects=True,
                limits=httpx.Limits(
                    max_connections=100,
                    max_keepalive_connections=20,
                    keepalive_expiry=300.0
                )
            )
        return self.clients[key]
    
    def get_sync_client(self, base_url: Optional[str] = None) -> httpx.Client:
        """获取同步HTTP客户端
        
        Args:
            base_url: 基础URL
            
        Returns:
            同步HTTP客户端
        """
        key = base_url or "default"
        if key not in self.sync_clients:
            self.sync_clients[key] = httpx.Client(
                base_url=base_url,
                timeout=30.0,
                follow_redirects=True,
                limits=httpx.Limits(
                    max_connections=100,
                    max_keepalive_connections=20,
                    keepalive_expiry=300.0
                )
            )
        return self.sync_clients[key]
    
    async def close(self):
        """关闭所有HTTP客户端"""
        for client in self.clients.values():
            await client.aclose()
        self.clients.clear()
        
        for client in self.sync_clients.values():
            client.close()
        self.sync_clients.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取HTTP客户端的统计信息
        
        Returns:
            HTTP客户端的统计信息
        """
        stats = {
            "async_clients": list(self.clients.keys()),
            "sync_clients": list(self.sync_clients.keys())
        }
        return stats


# 全局HTTP客户端管理器实例
http_client_manager = HttpClientManager()