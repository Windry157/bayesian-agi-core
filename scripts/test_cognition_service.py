#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试认知服务的API端点
"""

import requests
import json

# 测试做出决策
def test_make_decision():
    url = "http://localhost:8003/api/decision"
    data = {
        "possible_actions": ["行动1", "行动2", "行动3"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=data, headers=headers)
    print("做出决策 - Status code:", response.status_code)
    print("做出决策 - Response:", response.text)
    assert response.status_code == 200

# 测试健康检查
def test_health_check():
    url = "http://localhost:8003/health"
    response = requests.get(url)
    print("健康检查 - Status code:", response.status_code)
    print("健康检查 - Response:", response.text)
    assert response.status_code == 200

# 测试监控端点
def test_metrics():
    url = "http://localhost:8003/health/metrics"
    response = requests.get(url)
    print("监控端点 - Status code:", response.status_code)
    print("监控端点 - Response:", response.text)
    assert response.status_code == 200

if __name__ == "__main__":
    print("测试认知服务...")
    test_health_check()
    test_make_decision()
    test_metrics()
    print("认知服务测试完成")
