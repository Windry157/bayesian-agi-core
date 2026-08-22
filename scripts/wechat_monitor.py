#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信监控客户端
测试 WebSocket 连接和握手协议
"""

import asyncio
import websockets
import json
import uuid
import sys

async def send_test_message(websocket, content):
    """发送测试消息"""
    session_id = str(uuid.uuid4())[:8]
    await websocket.send(json.dumps({
        "type": "message",
        "session_id": session_id,
        "content": content
    }))
    print(f"\n📤 发送消息 (会话: {session_id}): {content[:50]}...")

async def main():
    """主函数"""
    url = "ws://localhost:8001/ws"
    
    print("✅ 正在连接到 WebSocket 服务器...")
    
    try:
        async with websockets.connect(url) as websocket:
            print("✅ WebSocket 通道已打开，等待挑战握手")
            
            # 发送连接请求
            await websocket.send(json.dumps({
                "type": "connect",
                "client": "wechat-monitor-python"
            }))
            print("📤 发送连接请求")
            
            # 接收挑战
            response = await websocket.recv()
            data = json.loads(response)
            
            if data.get("type") == "challenge":
                nonce = data.get("nonce", "")
                print(f"🔑 获取到挑战 Nonce: {nonce}")
                
                # 发送挑战响应（反转 nonce）
                challenge_response = nonce[::-1]
                await websocket.send(json.dumps({
                    "type": "challenge-response",
                    "nonce": nonce,
                    "response": challenge_response,
                    "client": "wechat-monitor-python"
                }))
                print(f"📤 发送挑战响应: {challenge_response}")
                
                # 接收握手结果
                result = await websocket.recv()
                result_data = json.loads(result)
                
                if result_data.get("type") == "connected" and result_data.get("success"):
                    print("✅ 握手成功！已建立安全连接")
                    
                    # 发送测试消息
                    test_messages = [
                        "你好，我是微信用户",
                        "今天天气怎么样？",
                        "介绍一下 Bayesian-AGI-Core"
                    ]
                    
                    for msg in test_messages:
                        await send_test_message(websocket, msg)
                        # 等待响应
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=60)
                            msg_data = json.loads(response)
                            if msg_data.get("type") == "message-response":
                                print(f"📥 收到响应:")
                                print(f"   会话ID: {msg_data.get('session_id')}")
                                print(f"   内容: {msg_data.get('content', '')[:200]}...")
                                print(f"   置信度: {msg_data.get('confidence', 0)}")
                        except asyncio.TimeoutError:
                            print("⏰ 响应超时")
                    
                    print("\n✅ 测试完成！")
                    
                else:
                    print(f"❌ 握手失败: {result_data}")
                    
            else:
                print(f"❌ 未收到挑战，收到: {data}")
                
    except websockets.exceptions.ConnectionClosed:
        print("❌ 连接已关闭")
    except ConnectionRefusedError:
        print("❌ 无法连接到服务器，请确保服务已启动")
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())