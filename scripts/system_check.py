#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bayesian-AGI-Core 系统状态检查工具
"""

import os
import sys
import json
import subprocess
import requests

def check_ollama():
    """检查 Ollama 服务"""
    try:
        response = requests.get("http://192.168.3.105:11434/api/tags", timeout=10)
        if response.status_code == 200:
            data = response.json()
            models = [m["name"] for m in data.get("models", [])]
            return {"status": "ok", "models": models}
        else:
            return {"status": "error", "message": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def check_server(host="localhost", port=8001):
    """检查服务状态"""
    try:
        response = requests.get(f"http://{host}:{port}/health", timeout=10)
        if response.status_code == 200:
            return {"status": "ok", "response": response.json()}
        else:
            return {"status": "error", "message": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def check_websocket(host="localhost", port=8001):
    """检查 WebSocket 服务"""
    try:
        import websockets
        import asyncio
        
        async def test_ws():
            url = f"ws://{host}:{port}/ws"
            async with websockets.connect(url) as ws:
                await ws.send(json.dumps({"type": "connect", "client": "system-check"}))
                response = await ws.recv()
                data = json.loads(response)
                if data.get("type") == "challenge":
                    return {"status": "ok", "message": "WebSocket handshake successful"}
                else:
                    return {"status": "error", "message": f"Unexpected response: {data}"}
        
        result = asyncio.run(test_ws())
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

def check_config():
    """检查配置文件"""
    config_path = "config.yaml"
    if os.path.exists(config_path):
        return {"status": "ok", "message": "配置文件存在"}
    else:
        return {"status": "error", "message": "配置文件不存在"}

def check_dependencies():
    """检查依赖"""
    required = ["fastapi", "uvicorn", "requests", "websockets"]
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    
    if missing:
        return {"status": "error", "message": f"缺少依赖: {', '.join(missing)}"}
    else:
        return {"status": "ok", "message": "所有依赖已安装"}

def main():
    print("🔍 Bayesian-AGI-Core 系统状态检查")
    print("=" * 50)
    
    checks = [
        ("配置文件", check_config),
        ("Python 依赖", check_dependencies),
        ("Ollama 服务", check_ollama),
        ("HTTP 服务", check_server),
        ("WebSocket 服务", check_websocket),
    ]
    
    all_passed = True
    
    for name, check_func in checks:
        print(f"\n📋 {name}")
        result = check_func()
        
        if result["status"] == "ok":
            print(f"  ✅ {result.get('message', '检查通过')}")
            if "models" in result:
                print(f"     可用模型: {', '.join(result['models'][:3])}...")
            if "response" in result:
                print(f"     响应: {result['response'].get('message', '')}")
        else:
            print(f"  ❌ {result.get('message', '检查失败')}")
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 所有检查通过！系统运行正常")
    else:
        print("⚠️ 部分检查未通过，请检查相关服务")
        sys.exit(1)

if __name__ == "__main__":
    main()