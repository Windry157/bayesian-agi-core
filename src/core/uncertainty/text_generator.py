#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本生成器模块
集成LLM生成文本响应，并支持置信度评分
"""

import logging
import json
import asyncio
import httpx
from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TextGenerator:
    """文本生成器
    
    集成LLM生成文本响应，支持多种生成策略
    """
    
    def __init__(self, ollama_url: str = "http://localhost:11434", default_model: str = "deepseek-r1:7b"):
        """初始化文本生成器
        
        Args:
            ollama_url: Ollama服务URL
            default_model: 默认模型名称
        """
        self.ollama_url = ollama_url
        self.default_model = default_model
        self.generation_history = []
        
        logger.info(f"文本生成器初始化完成: {ollama_url}, 模型: {default_model}")
    
    async def generate_response(
        self,
        prompt: str,
        context: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
        include_confidence: bool = True
    ) -> Dict[str, Any]:
        """生成文本响应
        
        Args:
            prompt: 输入提示
            context: 对话上下文
            model: 模型名称（默认为default_model）
            max_tokens: 最大token数
            temperature: 温度参数
            include_confidence: 是否包含置信度评分
            
        Returns:
            生成结果，包含文本和置信度信息
        """
        try:
            start_time = datetime.now()
            
            # 构建消息列表
            messages = self._build_messages(prompt, context)
            
            # 调用LLM生成
            model_name = model or self.default_model
            raw_response = await self._call_ollama_api(
                messages=messages,
                model=model_name,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            # 提取生成的文本
            generated_text = self._extract_generated_text(raw_response)
            
            # 构建响应结果
            result = {
                "text": generated_text,
                "model": model_name,
                "prompt": prompt,
                "generation_time": (datetime.now() - start_time).total_seconds(),
                "timestamp": datetime.now().isoformat(),
                "raw_response": raw_response if include_confidence else None
            }
            
            # 如果需要置信度评分，调用置信度评分器
            if include_confidence:
                from .confidence_scorer import confidence_scorer
                confidence_result = await confidence_scorer.score_text_generation_confidence(
                    prompt=prompt,
                    generated_text=generated_text,
                    model_output=raw_response
                )
                result["confidence"] = confidence_result
            
            # 记录生成历史
            self._record_generation(result)
            
            logger.info(f"文本生成完成: {len(generated_text)} 字符")
            return result
            
        except Exception as e:
            logger.error(f"文本生成失败: {e}")
            return {
                "text": f"抱歉，生成响应时出现错误: {str(e)}",
                "model": model or self.default_model,
                "prompt": prompt,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "confidence": {
                    "confidence_score": 0.0,
                    "confidence_level": "error",
                    "factor_scores": {}
                } if include_confidence else None
            }
    
    async def generate_with_uncertainty_handling(
        self,
        prompt: str,
        context: Optional[List[Dict[str, Any]]] = None,
        confidence_threshold: float = 0.6,
        fallback_response: str = "我不确定如何回答这个问题。您能提供更多背景信息吗？"
    ) -> Dict[str, Any]:
        """生成文本响应，并处理不确定性
        
        Args:
            prompt: 输入提示
            context: 对话上下文
            confidence_threshold: 置信度阈值
            fallback_response: 低置信度时的备用响应
            
        Returns:
            生成结果，包含不确定性处理
        """
        # 首先生成响应
        result = await self.generate_response(
            prompt=prompt,
            context=context,
            include_confidence=True
        )
        
        # 检查置信度
        confidence_score = result.get("confidence", {}).get("confidence_score", 0.0)
        
        if confidence_score < confidence_threshold:
            # 低置信度，使用备用响应
            uncertainty_type = self._determine_uncertainty_type(result.get("confidence", {}))
            
            result["original_text"] = result["text"]
            result["text"] = fallback_response
            result["uncertainty_handled"] = True
            result["uncertainty_type"] = uncertainty_type
            result["confidence_threshold"] = confidence_threshold
            result["original_confidence"] = confidence_score
            
            logger.info(f"低置信度处理: {confidence_score:.3f} < {confidence_threshold}, 类型: {uncertainty_type}")
        
        return result
    
    def _build_messages(self, prompt: str, context: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """构建消息列表
        
        Args:
            prompt: 当前提示
            context: 对话上下文
            
        Returns:
            消息列表
        """
        messages = []
        
        # 添加上下文消息
        if context:
            for msg in context[-10:]:  # 最多保留10条上下文
                if isinstance(msg, dict) and "role" in msg and "content" in msg:
                    messages.append({"role": msg["role"], "content": msg["content"]})
        
        # 添加当前提示
        messages.append({"role": "user", "content": prompt})
        
        return messages
    
    async def _call_ollama_api(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """调用Ollama API
        
        Args:
            messages: 消息列表
            model: 模型名称
            max_tokens: 最大token数
            temperature: 温度参数
            
        Returns:
            API响应
        """
        url = f"{self.ollama_url}/api/chat"
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
                "top_p": 0.9,
                "repeat_penalty": 1.1
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                data = response.json()
                
                # 记录API响应信息
                api_result = {
                    "message": data.get("message", {}),
                    "model": data.get("model", model),
                    "total_duration": data.get("total_duration", 0),
                    "load_duration": data.get("load_duration", 0),
                    "prompt_eval_count": data.get("prompt_eval_count", 0),
                    "prompt_eval_duration": data.get("prompt_eval_duration", 0),
                    "eval_count": data.get("eval_count", 0),
                    "eval_duration": data.get("eval_duration", 0)
                }
                
                return api_result
                
        except httpx.TimeoutException:
            logger.error(f"Ollama API请求超时: {url}")
            raise Exception("LLM服务响应超时，请检查模型是否正在运行")
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama API HTTP错误: {e.response.status_code}")
            raise Exception(f"LLM服务错误: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Ollama API调用失败: {e}")
            raise Exception(f"无法连接到LLM服务: {str(e)}")
    
    def _extract_generated_text(self, raw_response: Dict[str, Any]) -> str:
        """从原始响应提取生成文本
        
        Args:
            raw_response: 原始API响应
            
        Returns:
            生成的文本
        """
        if "message" in raw_response and "content" in raw_response["message"]:
            return raw_response["message"]["content"].strip()
        
        # 备用提取方法
        response_str = json.dumps(raw_response)
        if "content" in response_str:
            # 简单提取
            import re
            match = re.search(r'"content":\s*"([^"]+)"', response_str)
            if match:
                return match.group(1).strip()
        
        return "无法提取生成文本"
    
    def _determine_uncertainty_type(self, confidence_result: Dict[str, Any]) -> str:
        """确定不确定性类型
        
        Args:
            confidence_result: 置信度评分结果
            
        Returns:
            不确定性类型
        """
        factor_scores = confidence_result.get("factor_scores", {})
        
        # 找出最低的因子分数
        if factor_scores:
            min_factor = min(factor_scores.items(), key=lambda x: x[1])
            factor_name, factor_score = min_factor
            
            if factor_score < 0.3:
                if factor_name == "relevance":
                    return "prompt_relevance_low"
                elif factor_name == "consistency":
                    return "text_inconsistency"
                elif factor_name == "grammar":
                    return "grammar_issues"
                elif factor_name == "model_confidence":
                    return "model_uncertainty"
        
        # 基于总体置信度
        overall_score = confidence_result.get("confidence_score", 0.0)
        
        if overall_score < 0.3:
            return "very_low_confidence"
        elif overall_score < 0.5:
            return "low_confidence"
        else:
            return "medium_confidence"
    
    def _record_generation(self, generation_result: Dict[str, Any]):
        """记录生成结果
        
        Args:
            generation_result: 生成结果
        """
        self.generation_history.append(generation_result)
        
        # 限制历史记录长度
        if len(self.generation_history) > 500:
            self.generation_history = self.generation_history[-500:]
    
    def get_generation_history(self) -> List[Dict[str, Any]]:
        """获取生成历史
        
        Returns:
            生成历史列表
        """
        return self.generation_history
    
    def set_default_model(self, model: str):
        """设置默认模型
        
        Args:
            model: 模型名称
        """
        self.default_model = model
        logger.info(f"设置默认模型: {model}")
    
    def get_available_models(self) -> List[str]:
        """获取可用模型列表（同步）
        
        Returns:
            模型名称列表
        """
        try:
            url = f"{self.ollama_url}/api/tags"
            
            with httpx.Client() as client:
                response = client.get(url, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    return [model["name"] for model in data.get("models", [])]
                else:
                    logger.warning(f"获取模型列表失败: {response.status_code}")
                    return []
        except Exception as e:
            logger.warning(f"获取模型列表异常: {e}")
            return []


# 全局文本生成器实例
text_generator = TextGenerator()