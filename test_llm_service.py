#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试LLM服务的API端点
"""

import requests

# 测试获取模型列表
def test_get_models():
    url = "http://localhost:8001/api/models"
    response = requests.get(url)
    print("获取模型列表 - Status code:", response.status_code)
    print("获取模型列表 - Response:", response.text)
    assert response.status_code == 200

# 测试健康检查
def test_health_check():
    url = "http://localhost:8001/health"
    response = requests.get(url)
    print("健康检查 - Status code:", response.status_code)
    print("健康检查 - Response:", response.text)
    assert response.status_code == 200

# 测试监控端点
def test_metrics():
    url = "http://localhost:8001/health/metrics"
    response = requests.get(url)
    print("监控端点 - Status code:", response.status_code)
    print("监控端点 - Response:", response.text)
    assert response.status_code == 200

if __name__ == "__main__":
    print("测试LLM服务...")
    test_health_check()
    test_get_models()
    test_metrics()
    print("LLM服务测试完成")
