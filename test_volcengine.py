#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火山引擎方舟大模型测试脚本
验证集成是否正确
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.llm.base_llm import LLMFactory, LLMConfig
from core.llm.volcengine_llm import VolcEngineLLM


def test_volcengine_integration():
    """测试火山引擎集成"""
    print("=== 火山引擎方舟大模型集成测试 ===")
    print()

    api_key = os.getenv("VOLCENGINE_API_KEY")
    base_url = os.getenv("VOLCENGINE_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")

    if not api_key:
        print("❌ VOLCENGINE_API_KEY 环境变量未设置")
        print()
        print("请设置环境变量后重试:")
        print('  export VOLCENGINE_API_KEY="你的AccessKeyID/SecretKey"')
        print()
        print("或创建 .env 文件:")
        print("  VOLCENGINE_API_KEY=你的AccessKeyID/SecretKey")
        print("  VOLCENGINE_BASE_URL=https://ark.cn-beijing.volces.com/api/v3")
        print("  VOLCENGINE_MODEL=doubao-code")
        return

    print(f"✅ API Key: {api_key[:20]}...")
    print(f"✅ Base URL: {base_url}")
    print()

    try:
        config = LLMConfig(
            provider="volcengine",
            model="doubao-code",
            api_key=api_key,
            base_url=base_url,
            temperature=0.7,
            max_tokens=1024
        )

        llm = LLMFactory.create(config)
        print(f"✅ 创建LLM实例成功: {llm}")
        print()

        print("📋 模型信息:")
        info = llm.get_model_info()
        for key, value in info.items():
            print(f"  - {key}: {value}")
        print()

        print("🔍 检查模型可用性...")
        is_available = llm.is_available()
        if is_available:
            print("✅ 模型可用!")
        else:
            print("❌ 模型不可用，请检查API Key和网络连接")
            return

        print()
        print("🧪 测试对话功能...")
        from core.llm.base_llm import Message

        messages = [
            Message(role="user", content="写一个简单的Python函数，计算两个数的和")
        ]

        response = llm.chat(messages)
        print(f"✅ 响应成功!")
        print(f"模型: {response.model}")
        print(f"提供商: {response.provider}")
        print(f"内容: {response.content[:200]}...")
        if response.usage:
            print(f"Token使用: {response.usage}")
        print()

        print("🎉 火山引擎集成测试通过!")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_volcengine_integration()