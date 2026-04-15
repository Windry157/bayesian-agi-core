#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bayesian-AGI-Core Python SDK Exceptions
"""


class BayesianAGIError(Exception):
    """Bayesian-AGI-Core 基础异常"""
    pass


class APIError(BayesianAGIError):
    """API 错误异常
    
    当API返回非200状态码时抛出
    """
    
    def __init__(self, message: str, status_code: int):
        """初始化API错误异常
        
        Args:
            message: 错误信息
            status_code: 状态码
        """
        self.message = message
        self.status_code = status_code
        super().__init__(f"API Error {status_code}: {message}")