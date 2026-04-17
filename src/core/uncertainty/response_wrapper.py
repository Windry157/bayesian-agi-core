#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
响应包装器模块
提供统一的输出格式：(answer, confidence)
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ResponseWrapper:
    """响应包装器
    
    将各种响应格式统一为标准格式：(answer, confidence)
    """
    
    def __init__(self):
        """初始化响应包装器"""
        self.wrapping_history = []
        
        logger.info("响应包装器初始化完成")
    
    async def wrap_consciousness_response(
        self,
        consciousness_result: Dict[str, Any],
        input_text: str,
        session_id: str = "default"
    ) -> Dict[str, Any]:
        """包装意识系统响应
        
        Args:
            consciousness_result: 意识系统原始结果
            input_text: 原始输入文本
            session_id: 会话ID
            
        Returns:
            标准化响应格式
        """
        try:
            # 提取决策信息
            decision = consciousness_result.get("decision", {})
            thought_chain = consciousness_result.get("thought_chain", [])
            context_used = consciousness_result.get("context_used", {})
            
            # 生成文本答案
            answer_text = await self._generate_answer_from_decision(
                decision, thought_chain, input_text
            )
            
            # 计算置信度
            from .confidence_scorer import confidence_scorer
            
            # 准备决策上下文
            decision_context = {
                "input": input_text,
                "thought_chain": thought_chain,
                "context": context_used
            }
            
            # 评分决策置信度
            confidence_result = await confidence_scorer.score_decision_confidence(
                decision_context=decision_context,
                relevant_memories=[],  # 意识系统结果不包含实际记忆列表
                knowledge_coverage=self._estimate_knowledge_coverage(decision, thought_chain)
            )
            
            # 构建标准化响应
            standardized_response = {
                "answer": answer_text,
                "confidence": confidence_result["confidence_score"],
                "confidence_details": confidence_result,
                "thought_chain_summary": self._summarize_thought_chain(thought_chain),
                "decision_type": decision.get("type", "unknown"),
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "raw_response": consciousness_result
            }
            
            # 记录包装历史
            self._record_wrapping(standardized_response)
            
            logger.info(f"意识系统响应包装完成: 置信度={confidence_result['confidence_score']:.3f}")
            return standardized_response
            
        except Exception as e:
            logger.error(f"意识系统响应包装失败: {e}")
            return self._create_error_response(
                input_text=input_text,
                error=str(e),
                session_id=session_id
            )
    
    async def wrap_text_generation_response(
        self,
        generation_result: Dict[str, Any],
        input_text: str,
        session_id: str = "default"
    ) -> Dict[str, Any]:
        """包装文本生成响应
        
        Args:
            generation_result: 文本生成原始结果
            input_text: 原始输入文本
            session_id: 会话ID
            
        Returns:
            标准化响应格式
        """
        try:
            # 提取生成文本
            answer_text = generation_result.get("text", "")
            
            # 提取置信度信息
            confidence_info = generation_result.get("confidence", {})
            
            if confidence_info:
                confidence_score = confidence_info.get("confidence_score", 0.5)
                confidence_details = confidence_info
            else:
                # 如果没有置信度信息，计算一个简单置信度
                from .confidence_scorer import confidence_scorer
                
                confidence_result = await confidence_scorer.score_text_generation_confidence(
                    prompt=input_text,
                    generated_text=answer_text,
                    model_output=generation_result.get("raw_response")
                )
                
                confidence_score = confidence_result["confidence_score"]
                confidence_details = confidence_result
            
            # 构建标准化响应
            standardized_response = {
                "answer": answer_text,
                "confidence": confidence_score,
                "confidence_details": confidence_details,
                "model": generation_result.get("model", "unknown"),
                "generation_time": generation_result.get("generation_time", 0),
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "raw_response": generation_result
            }
            
            # 记录包装历史
            self._record_wrapping(standardized_response)
            
            logger.info(f"文本生成响应包装完成: 置信度={confidence_score:.3f}")
            return standardized_response
            
        except Exception as e:
            logger.error(f"文本生成响应包装失败: {e}")
            return self._create_error_response(
                input_text=input_text,
                error=str(e),
                session_id=session_id
            )
    
    async def wrap_decision_response(
        self,
        decision_result: Dict[str, Any],
        input_text: str,
        session_id: str = "default"
    ) -> Dict[str, Any]:
        """包装决策响应
        
        Args:
            decision_result: 决策原始结果
            input_text: 原始输入文本
            session_id: 会话ID
            
        Returns:
            标准化响应格式
        """
        try:
            # 提取决策信息
            decision_type = decision_result.get("type", "unknown")
            decision_content = decision_result.get("content", "")
            decision_confidence = decision_result.get("confidence", 0.5)
            
            # 生成答案文本
            if decision_type == "action":
                answer_text = f"我将执行操作: {decision_content}"
            elif decision_type == "clarification":
                answer_text = f"我需要澄清: {decision_content}"
            elif decision_type == "information":
                answer_text = decision_content
            else:
                answer_text = f"决策结果: {decision_content}"
            
            # 计算或使用现有置信度
            confidence_score = decision_confidence
            
            # 如果需要更详细的置信度分析
            if "confidence_details" not in decision_result:
                from .confidence_scorer import confidence_scorer
                
                confidence_result = await confidence_scorer.score_decision_confidence(
                    decision_context={"input": input_text, "decision": decision_result},
                    relevant_memories=decision_result.get("memories", []),
                    knowledge_coverage=decision_result.get("knowledge_coverage", 0.5)
                )
                
                confidence_score = confidence_result["confidence_score"]
                confidence_details = confidence_result
            else:
                confidence_details = decision_result.get("confidence_details", {})
            
            # 构建标准化响应
            standardized_response = {
                "answer": answer_text,
                "confidence": confidence_score,
                "confidence_details": confidence_details,
                "decision_type": decision_type,
                "decision_content": decision_content,
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "raw_response": decision_result
            }
            
            # 记录包装历史
            self._record_wrapping(standardized_response)
            
            logger.info(f"决策响应包装完成: 置信度={confidence_score:.3f}")
            return standardized_response
            
        except Exception as e:
            logger.error(f"决策响应包装失败: {e}")
            return self._create_error_response(
                input_text=input_text,
                error=str(e),
                session_id=session_id
            )
    
    async def _generate_answer_from_decision(
        self,
        decision: Dict[str, Any],
        thought_chain: List[Dict[str, Any]],
        input_text: str
    ) -> str:
        """从决策生成答案文本
        
        Args:
            decision: 决策信息
            thought_chain: 思维链
            input_text: 输入文本
            
        Returns:
            生成的答案文本
        """
        # 提取决策类型和内容
        decision_type = decision.get("type", "unknown")
        decision_content = decision.get("content", "")
        
        # 基于思维链和决策生成答案
        if decision_type == "information" and decision_content:
            # 信息型决策，直接使用内容
            answer = decision_content
        elif decision_type == "action":
            # 行动型决策
            action_desc = decision_content or "执行建议的操作"
            answer = f"根据我的分析，我将{action_desc}。"
        elif decision_type == "clarification":
            # 澄清型决策
            clarification_needed = decision_content or "更多信息"
            answer = f"为了提供更准确的回答，我需要澄清: {clarification_needed}"
        else:
            # 默认情况，生成基于思维链的答案
            if thought_chain:
                # 提取思维链的结论
                conclusions = []
                for thought in thought_chain:
                    if thought.get("type") == "conclusion":
                        conclusions.append(thought.get("content", ""))
                
                if conclusions:
                    answer = " ".join(conclusions[-2:])  # 使用最近的结论
                else:
                    # 从思维链中提取信息
                    thoughts_text = " ".join([t.get("content", "") for t in thought_chain[-3:] if t.get("content")])
                    answer = f"基于我的思考过程: {thoughts_text}"
            else:
                # 生成通用回答
                answer = f"我已经分析了您的问题: '{input_text}'，并做出了相应的决策。"
        
        # 确保答案不为空
        if not answer.strip():
            answer = f"对于您的问题: '{input_text}'，我的分析结果是: {decision_content or '需要进一步的信息'}"
        
        return answer
    
    def _estimate_knowledge_coverage(
        self,
        decision: Dict[str, Any],
        thought_chain: List[Dict[str, Any]]
    ) -> float:
        """估计知识覆盖率
        
        Args:
            decision: 决策信息
            thought_chain: 思维链
            
        Returns:
            知识覆盖率估计（0-1）
        """
        # 简单启发式估计
        factors = []
        
        # 因子1: 思维链长度
        chain_length = len(thought_chain)
        if chain_length >= 5:
            factors.append(0.8)
        elif chain_length >= 3:
            factors.append(0.6)
        elif chain_length >= 1:
            factors.append(0.4)
        else:
            factors.append(0.2)
        
        # 因子2: 决策置信度（如果有）
        decision_confidence = decision.get("confidence", 0.5)
        factors.append(decision_confidence)
        
        # 因子3: 决策类型
        decision_type = decision.get("type", "unknown")
        if decision_type == "information":
            factors.append(0.7)  # 信息型决策通常有较好知识覆盖
        elif decision_type == "clarification":
            factors.append(0.3)  # 澄清型决策表示知识不足
        
        # 计算平均值
        if factors:
            return sum(factors) / len(factors)
        else:
            return 0.5
    
    def _summarize_thought_chain(self, thought_chain: List[Dict[str, Any]]) -> Dict[str, Any]:
        """摘要思维链
        
        Args:
            thought_chain: 思维链
            
        Returns:
            思维链摘要
        """
        if not thought_chain:
            return {"steps": 0, "types": []}
        
        # 统计思维类型
        thought_types = {}
        for thought in thought_chain:
            thought_type = thought.get("type", "unknown")
            thought_types[thought_type] = thought_types.get(thought_type, 0) + 1
        
        # 提取关键内容
        key_thoughts = []
        for thought in thought_chain:
            if thought.get("type") in ["conclusion", "decision", "analysis"]:
                content = thought.get("content", "")
                if content and len(content) < 100:  # 只保留简短内容
                    key_thoughts.append({
                        "type": thought.get("type"),
                        "content_preview": content[:50] + ("..." if len(content) > 50 else "")
                    })
        
        return {
            "steps": len(thought_chain),
            "types": thought_types,
            "key_thoughts": key_thoughts[:3],  # 最多3个关键思维
            "has_conclusion": any(t.get("type") == "conclusion" for t in thought_chain)
        }
    
    def _record_wrapping(self, wrapped_response: Dict[str, Any]):
        """记录包装历史
        
        Args:
            wrapped_response: 包装后的响应
        """
        self.wrapping_history.append(wrapped_response)
        
        # 限制历史记录长度
        if len(self.wrapping_history) > 500:
            self.wrapping_history = self.wrapping_history[-500:]
    
    def _create_error_response(
        self,
        input_text: str,
        error: str,
        session_id: str = "default"
    ) -> Dict[str, Any]:
        """创建错误响应
        
        Args:
            input_text: 输入文本
            error: 错误信息
            session_id: 会话ID
            
        Returns:
            错误响应格式
        """
        return {
            "answer": f"抱歉，处理您的问题时出现错误: {error}",
            "confidence": 0.0,
            "confidence_details": {
                "confidence_score": 0.0,
                "confidence_level": "error",
                "error": error
            },
            "error": True,
            "error_message": error,
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id
        }
    
    def get_wrapping_history(self) -> List[Dict[str, Any]]:
        """获取包装历史
        
        Returns:
            包装历史列表
        """
        return self.wrapping_history
    
    async def wrap_any_response(
        self,
        raw_response: Dict[str, Any],
        input_text: str,
        response_type: str = "auto",
        session_id: str = "default"
    ) -> Dict[str, Any]:
        """包装任意响应
        
        Args:
            raw_response: 原始响应
            input_text: 输入文本
            response_type: 响应类型（auto/consciousness/text/decision）
            session_id: 会话ID
            
        Returns:
            标准化响应格式
        """
        # 自动检测响应类型
        if response_type == "auto":
            if "thought_chain" in raw_response and "decision" in raw_response:
                response_type = "consciousness"
            elif "text" in raw_response and "model" in raw_response:
                response_type = "text"
            elif "type" in raw_response and "content" in raw_response:
                response_type = "decision"
            else:
                response_type = "decision"  # 默认
        
        # 根据类型调用相应的包装方法
        if response_type == "consciousness":
            return await self.wrap_consciousness_response(raw_response, input_text, session_id)
        elif response_type == "text":
            return await self.wrap_text_generation_response(raw_response, input_text, session_id)
        elif response_type == "decision":
            return await self.wrap_decision_response(raw_response, input_text, session_id)
        else:
            logger.warning(f"未知响应类型: {response_type}, 使用决策包装")
            return await self.wrap_decision_response(raw_response, input_text, session_id)


# 全局响应包装器实例
response_wrapper = ResponseWrapper()