#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试API Gateway的add_memory和search_memory端点
"""

import requests
import json

# 测试添加记忆
url = "http://localhost:8000/api/memory"
data = {
    "content": "这是一个测试记忆"
}

headers = {
    "Content-Type": "application/json"
}

response = requests.post(url, json=data, headers=headers)
print("添加记忆 - Status code:", response.status_code)
print("添加记忆 - Response:", response.text)

# 测试检索记忆
search_url = "http://localhost:8000/api/memory/search"
params = {
    "query": "测试"
}

search_response = requests.get(search_url, params=params)
print("\n检索记忆 - Status code:", search_response.status_code)
print("检索记忆 - Response:", search_response.text)