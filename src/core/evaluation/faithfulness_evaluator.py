#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
忠实度评估器 - 评估回答是否完全基于提供的上下文
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import httpx
import json


@dataclass
class FaithfulnessScore:
    """忠实度评分"""
    overall_score: float
    context_usage_score: float
    hallucination_score: float
    groundedness_score: float
    explanation: str
    issues_found: List[str] = field(default_factory=list)
    evidence_used: List[str] = field(default_factory=list)


class FaithfulnessEvaluator:
    """忠实度评估器"""

    def __init__(self, ollama_url: str = "http://192.168.3.105:11434"):
        self.ollama_url = ollama_url

    async def evaluate(
        self,
        question: str,
        context: str,
        answer: str
    ) -> FaithfulnessScore:
        """
        评估回答的忠实度

        Args:
            question: 用户问题
            context: 提供的上下文
            answer: 生成的回答

        Returns:
            FaithfulnessScore: 评分结果
        """
        # 提取回答中的主张
        claims = self._extract_claims(answer)

        # 评估每个主张是否在上下文中有根据
        grounded_claims = []
        hallucinated_claims = []

        for claim in claims:
            is_grounded = await self._check_claim_grounded(claim, context)
            if is_grounded:
                grounded_claims.append(claim)
            else:
                hallucinated_claims.append(claim)

        # 计算各种分数
        total_claims = len(claims)
        context_usage_score = len(grounded_claims) / max(1, total_claims)
        hallucination_score = 1.0 - (len(hallucinated_claims) / max(1, total_claims))
        groundedness_score = self._calculate_groundedness(answer, context)

        # 综合得分
        overall_score = (
            context_usage_score * 0.4 +
            hallucination_score * 0.4 +
            groundedness_score * 0.2
        )

        explanation = self._generate_explanation(
            overall_score,
            len(grounded_claims),
            len(hallucinated_claims),
            total_claims
        )

        return FaithfulnessScore(
            overall_score=overall_score,
            context_usage_score=context_usage_score,
            hallucination_score=hallucination_score,
            groundedness_score=groundedness_score,
            explanation=explanation,
            issues_found=hallucinated_claims,
            evidence_used=grounded_claims
        )

    def _extract_claims(self, answer: str) -> List[str]:
        """从回答中提取主张"""
        # 简单分割句子作为主张
        sentences = re.split(r'[。！？.!?]', answer)
        claims = []

        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 5:
                claims.append(sentence)

        return claims

    async def _check_claim_grounded(self, claim: str, context: str) -> bool:
        """检查主张是否在上下文中有根据"""
        if not context or not claim:
            return False

        # 检查关键词匹配
        claim_keywords = self._extract_keywords(claim)
        context_lower = context.lower()

        # 如果主张中的关键词至少有50%在上下文中，则认为有根据
        match_count = 0
        for keyword in claim_keywords:
            if keyword.lower() in context_lower:
                match_count += 1

        return match_count >= max(1, len(claim_keywords) * 0.3)

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单实现：提取名词和动词
        words = re.findall(r'\b[\w\u4e00-\u9fa5]+\b', text)
        keywords = [word for word in words if len(word) > 1]
        return keywords[:10]

    def _calculate_groundedness(self, answer: str, context: str) -> float:
        """计算接地性分数"""
        if not context or not answer:
            return 0.0

        # 计算回答与上下文的词汇重叠
        answer_words = set(self._extract_keywords(answer.lower()))
        context_words = set(self._extract_keywords(context.lower()))

        if not answer_words:
            return 0.0

        intersection = answer_words & context_words
        return len(intersection) / len(answer_words)

    def _generate_explanation(
        self,
        score: float,
        grounded_count: int,
        hallucinated_count: int,
        total_claims: int
    ) -> str:
        """生成解释"""
        if score >= 0.9:
            return "回答完全基于提供的上下文，没有幻觉。"
        elif score >= 0.7:
            return "回答主要基于上下文，但有少量不确定的内容。"
        elif score >= 0.5:
            return f"回答部分基于上下文，但有 {hallucinated_count} 条主张缺乏证据。"
        else:
            return "回答可能包含大量未在上下文中验证的信息。"

    async def evaluate_with_llm(
        self,
        question: str,
        context: str,
        answer: str
    ) -> FaithfulnessScore:
        """
        使用 LLM 评估忠实度（更精确但更慢）
        """
        prompt = f"""作为一个回答质量评估专家，请评估以下回答是否完全基于提供的上下文。

问题：{question}

上下文：
{context}

回答：
{answer}

请从以下三个方面评估：
1. 忠实度：回答是否完全基于上下文（0-1）
2. 上下文使用率：回答中有多少内容来自上下文（0-1）
3. 幻觉程度：回答中有多少内容是凭空生成的（0-1，1表示无幻觉）

请以JSON格式返回：
{{
    "overall_score": 0-1,
    "context_usage_score": 0-1,
    "hallucination_score": 0-1,
    "groundedness_score": 0-1,
    "explanation": "简短解释",
    "issues_found": ["问题1", "问题2"],
    "evidence_used": ["证据1", "证据2"]
}}
"""

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/chat",
                    json={
                        "model": "llama3.1:8b",
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False
                    }
                )
                data = response.json()
                result_text = data.get("message", {}).get("content", "")

                # 尝试解析 JSON
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    return FaithfulnessScore(
                        overall_score=result.get("overall_score", 0.5),
                        context_usage_score=result.get("context_usage_score", 0.5),
                        hallucination_score=result.get("hallucination_score", 0.5),
                        groundedness_score=result.get("groundedness_score", 0.5),
                        explanation=result.get("explanation", ""),
                        issues_found=result.get("issues_found", []),
                        evidence_used=result.get("evidence_used", [])
                    )
        except Exception as e:
            print(f"LLM 评估失败: {e}")

        # LLM 失败时回退到规则评估
        return await self.evaluate(question, context, answer)
