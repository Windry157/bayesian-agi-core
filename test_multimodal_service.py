#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试多模态服务的API端点
"""

import requests
import os

# 测试处理文本输入
def test_process_text():
    url = "http://localhost:8005/api/multimodal/text"
    data = {
        "text": "这是一个测试文本",
        "task": "summarize"
    }
    response = requests.post(url, data=data)
    print("处理文本 - Status code:", response.status_code)
    print("处理文本 - Response:", response.text)
    assert response.status_code == 200

# 测试处理图像输入
def test_process_image():
    url = "http://localhost:8005/api/multimodal/image"
    # 使用一个简单的测试图像
    # 注意：这里需要替换为实际的图像路径
    test_image_path = "test_image.jpg"
    if os.path.exists(test_image_path):
        with open(test_image_path, "rb") as f:
            files = {"file": f}
            data = {"task": "classify"}
            response = requests.post(url, data=data, files=files)
            print("处理图像 - Status code:", response.status_code)
            print("处理图像 - Response:", response.text)
            assert response.status_code == 200
    else:
        print(f"测试图像 {test_image_path} 不存在，跳过图像处理测试")

# 测试处理音频输入
def test_process_audio():
    url = "http://localhost:8005/api/multimodal/audio"
    # 使用一个简单的测试音频
    # 注意：这里需要替换为实际的音频路径
    test_audio_path = "test_audio.wav"
    if os.path.exists(test_audio_path):
        with open(test_audio_path, "rb") as f:
            files = {"file": f}
            data = {"task": "transcribe"}
            response = requests.post(url, data=data, files=files)
            print("处理音频 - Status code:", response.status_code)
            print("处理音频 - Response:", response.text)
            assert response.status_code == 200
    else:
        print(f"测试音频 {test_audio_path} 不存在，跳过音频处理测试")

# 测试获取支持的输入类型
def test_get_supported_input_types():
    url = "http://localhost:8005/api/multimodal/supported-input-types"
    response = requests.get(url)
    print("获取支持的输入类型 - Status code:", response.status_code)
    print("获取支持的输入类型 - Response:", response.text)
    assert response.status_code == 200

# 测试获取支持的任务类型
def test_get_supported_tasks():
    url = "http://localhost:8005/api/multimodal/supported-tasks"
    response = requests.get(url)
    print("获取支持的任务类型 - Status code:", response.status_code)
    print("获取支持的任务类型 - Response:", response.text)
    assert response.status_code == 200

# 测试健康检查
def test_health_check():
    url = "http://localhost:8005/health"
    response = requests.get(url)
    print("健康检查 - Status code:", response.status_code)
    print("健康检查 - Response:", response.text)
    assert response.status_code == 200

# 测试监控端点
def test_metrics():
    url = "http://localhost:8005/health/metrics"
    response = requests.get(url)
    print("监控端点 - Status code:", response.status_code)
    print("监控端点 - Response:", response.text)
    assert response.status_code == 200

if __name__ == "__main__":
    print("测试多模态服务...")
    test_health_check()
    test_process_text()
    test_process_image()
    test_process_audio()
    test_get_supported_input_types()
    test_get_supported_tasks()
    test_metrics()
    print("多模态服务测试完成")
