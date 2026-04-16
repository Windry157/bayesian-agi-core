#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试视觉服务的API端点
"""

import requests
import os

# 测试图像分类
def test_classify_image():
    url = "http://localhost:8004/api/vision/classify"
    # 使用一个简单的测试图像
    # 注意：这里需要替换为实际的图像路径
    test_image_path = "test_image.jpg"
    if os.path.exists(test_image_path):
        with open(test_image_path, "rb") as f:
            files = {"file": f}
            response = requests.post(url, files=files)
            print("图像分类 - Status code:", response.status_code)
            print("图像分类 - Response:", response.text)
            assert response.status_code == 200
    else:
        print(f"测试图像 {test_image_path} 不存在，跳过图像分类测试")

# 测试目标检测
def test_detect_objects():
    url = "http://localhost:8004/api/vision/detect"
    # 使用一个简单的测试图像
    # 注意：这里需要替换为实际的图像路径
    test_image_path = "test_image.jpg"
    if os.path.exists(test_image_path):
        with open(test_image_path, "rb") as f:
            files = {"file": f}
            response = requests.post(url, files=files)
            print("目标检测 - Status code:", response.status_code)
            print("目标检测 - Response:", response.text)
            assert response.status_code == 200
    else:
        print(f"测试图像 {test_image_path} 不存在，跳目标检测测试")

# 测试图像描述
def test_describe_image():
    url = "http://localhost:8004/api/vision/describe"
    # 使用一个简单的测试图像
    # 注意：这里需要替换为实际的图像路径
    test_image_path = "test_image.jpg"
    if os.path.exists(test_image_path):
        with open(test_image_path, "rb") as f:
            files = {"file": f}
            response = requests.post(url, files=files)
            print("图像描述 - Status code:", response.status_code)
            print("图像描述 - Response:", response.text)
            assert response.status_code == 200
    else:
        print(f"测试图像 {test_image_path} 不存在，跳过图像描述测试")

# 测试健康检查
def test_health_check():
    url = "http://localhost:8004/health"
    response = requests.get(url)
    print("健康检查 - Status code:", response.status_code)
    print("健康检查 - Response:", response.text)
    assert response.status_code == 200

# 测试监控端点
def test_metrics():
    url = "http://localhost:8004/health/metrics"
    response = requests.get(url)
    print("监控端点 - Status code:", response.status_code)
    print("监控端点 - Response:", response.text)
    assert response.status_code == 200

if __name__ == "__main__":
    print("测试视觉服务...")
    test_health_check()
    test_classify_image()
    test_detect_objects()
    test_describe_image()
    test_metrics()
    print("视觉服务测试完成")
