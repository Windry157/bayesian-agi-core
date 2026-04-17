#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端到端测试框架
测试完整的系统工作流程
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from src.api_gateway import app
from src.core.assistant import Assistant


class TestE2E:
    """端到端测试类"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)
    
    @pytest.fixture
    def assistant(self):
        """创建智能助理实例"""
        return Assistant()
    
    @pytest.mark.asyncio
    async def test_full_contextual_loop(self, client, assistant):
        """测试完整的上下文循环
        
        测试复杂的多步骤任务，验证系统是否能够：
        1. 使用记忆检索单元 (MRU) 进行检索
        2. 使用目标引擎进行分解
        3. 使用响应生成器生成最终输出
        """
        # 测试场景：计划周末西雅图之旅，关注历史，提供预算明细
        test_session_id = "test_trip_planning"
        test_prompt = "计划一个周末去西雅图的旅行，重点关注历史景点，并提供预算明细"
        
        # 1. 初始化上下文
        await assistant.context_bridge.update_session_context(test_session_id, {
            "messages": [],
            "metadata": {"topic": "trip planning", "location": "Seattle"}
        })
        
        # 2. 处理请求
        response = client.post("/api/context/process", json={
            "input": test_prompt,
            "session_id": test_session_id
        })
        
        # 3. 验证响应
        assert response.status_code == 200
        result = response.json()
        assert "response" in result
        
        # 4. 检查响应内容
        response_text = result["response"]
        assert "西雅图" in response_text or "Seattle" in response_text
        assert "历史" in response_text or "history" in response_text
        assert "预算" in response_text or "budget" in response_text
        
        # 5. 验证上下文更新
        context = await assistant.context_bridge.load_relevant_context(test_session_id)
        assert len(context.get("session_context", {}).get("messages", [])) >= 2
        
        # 6. 验证认知状态更新
        cognitive_state = await assistant.state_persistence.load_cognitive_state()
        assert cognitive_state.get("knowledge", {}).get("domains", [])
        
        print(f"✓ 完整上下文循环测试通过: {response_text[:100]}...")
    
    @pytest.mark.asyncio
    async def test_inter_module_failure_simulation(self, client, assistant):
        """测试模块间故障模拟
        
        故意"破坏"一个系统组件，验证周围模块是否能优雅失败
        """
        test_session_id = "test_failure_simulation"
        
        # 1. 模拟记忆系统故障
        original_retrieve = assistant.memory_system.retrieve_memories
        
        def mock_failed_retrieve(*args, **kwargs):
            raise Exception("Memory retrieval timeout")
        
        # 2. 注入故障
        assistant.memory_system.retrieve_memories = mock_failed_retrieve
        
        try:
            # 3. 处理请求
            response = client.post("/api/context/process", json={
                "input": "请告诉我关于人工智能的最新进展",
                "session_id": test_session_id
            })
            
            # 4. 验证系统能够优雅处理故障
            assert response.status_code == 200
            result = response.json()
            assert "response" in result
            
            print(f"✓ 模块故障模拟测试通过: 系统能够优雅处理内存检索故障")
            
        finally:
            # 5. 恢复原始方法
            assistant.memory_system.retrieve_memories = original_retrieve
    
    @pytest.mark.asyncio
    async def test_long_term_coherence(self, client, assistant):
        """测试长期一致性
        
        维护一个多天的对话线程，测试系统能够保留初始约束和上下文细微差别
        """
        test_session_id = "test_long_term_coherence"
        
        # 1. 初始请求：设置约束
        initial_prompt = "我计划下个月去日本旅行，预算有限，喜欢历史和美食"
        
        response1 = client.post("/api/context/process", json={
            "input": initial_prompt,
            "session_id": test_session_id
        })
        
        assert response1.status_code == 200
        
        # 2. 后续请求：依赖初始约束
        follow_up_prompt = "推荐一些东京的历史景点"
        
        response2 = client.post("/api/context/process", json={
            "input": follow_up_prompt,
            "session_id": test_session_id
        })
        
        assert response2.status_code == 200
        result2 = response2.json()
        
        # 3. 验证响应包含相关信息
        response_text = result2["response"]
        assert "东京" in response_text or "Tokyo" in response_text
        assert "历史" in response_text or "history" in response_text
        
        # 4. 再次测试，确保上下文保持
        second_follow_up = "这些景点的大致费用是多少？"
        
        response3 = client.post("/api/context/process", json={
            "input": second_follow_up,
            "session_id": test_session_id
        })
        
        assert response3.status_code == 200
        result3 = response3.json()
        response_text3 = result3["response"]
        
        # 5. 验证响应包含预算相关信息
        assert "费用" in response_text3 or "cost" in response_text3
        
        print(f"✓ 长期一致性测试通过: 系统能够保持多轮对话的上下文")
    
    @pytest.mark.asyncio
    async def test_system_health(self, client):
        """测试系统健康状态"""
        response = client.get("/api/system/health")
        assert response.status_code == 200
        health_data = response.json()
        
        # 验证健康状态包含所有必要的组件
        assert "meta_learning" in health_data
        assert "intrinsic_motivation" in health_data
        assert "cognitive_state" in health_data
        assert "context_bridge" in health_data
        
        print(f"✓ 系统健康状态测试通过")


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v"])
