#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
思维链模块
实现 LLM 驱动的思维链推理（Chain-of-Thought Reasoning）
支持多种 CoT 策略：标准 CoT、Self-Consistency CoT、Least-to-Most、Plan-and-Solve
"""

import asyncio
import logging
import time
import re
import statistics
from typing import Dict, List, Optional, Any, Callable, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

from .budget import ReasoningBudget, ReasoningBudgetExceeded, BudgetState

logger = logging.getLogger(__name__)


class ChainStrategy(Enum):
    """思维链策略"""
    STANDARD = "standard"             # 标准 CoT: 逐步推理
    SELF_CONSISTENCY = "self_consistency"  # 自洽性 CoT: 多次采样后投票
    LEAST_TO_MOST = "least_to_most"   # 从易到难: 先解子问题
    PLAN_AND_SOLVE = "plan_and_solve" # 先规划再求解: Plan-and-Solve


@dataclass
class ReasoningStep:
    """推理步骤"""
    step_number: int
    description: str
    content: str
    confidence: float = 0.5
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChainResult:
    """思维链结果"""
    problem: str
    steps: List[ReasoningStep]
    conclusion: str
    confidence: float = 0.0
    strategy: str = "standard"
    total_duration: float = 0.0
    all_candidates: List[str] = field(default_factory=list)  # Self-Consistency 候选
    degraded: bool = False
    degradation_reason: Optional[str] = None


class ChainOfThought:
    """思维链（CoT）推理引擎

    支持多种推理策略：
    - STANDARD: 标准逐步推理
    - SELF_CONSISTENCY: 多次采样后投票选最优
    - LEAST_TO_MOST: 先分解子问题，逐一解决
    - PLAN_AND_SOLVE: 先制定计划再执行
    """

    def __init__(self, llm: Any = None, config: Dict[str, Any] = None):
        """初始化思维链

        Args:
            llm: LLM 实例（可选），需有 generate(prompt) 或 chat(messages) 方法
            config: 配置字典
                max_chain_length: 最大链长（默认 10）
                default_strategy: 默认策略（默认 "standard"）
                consistency_samples: Self-Consistency 采样数（默认 3）
                temperature: LLM 温度（默认 0.7）
        """
        self.llm = llm
        self.config = config or {}
        self.max_chain_length = self.config.get("max_chain_length", 10)
        self.default_strategy = ChainStrategy(self.config.get("default_strategy", "standard"))
        self.consistency_samples = self.config.get("consistency_samples", 3)
        self.temperature = self.config.get("temperature", 0.7)

        # 推理预算配置（用于创建请求级 BudgetState）
        self._budget_config = None
        if isinstance(self.config, dict):
            self._budget_config = self.config.get("budget")
        if self._budget_config is None:
            self._budget_config = ReasoningBudget()
        # 每个 reason() 创建一个新的 BudgetState
        self._budget_state: Optional[BudgetState] = None

        # 思维链历史
        self.chain_history: List[ChainResult] = []

        # ----- 兼容旧版接口的状态 -----
        self._old_chain: List[Dict] = []

    # ================================================================
    # 新版 LLM 驱动接口
    # ================================================================

    async def reason(
        self,
        problem: str,
        context: Optional[Dict[str, Any]] = None,
        strategy: Optional[ChainStrategy] = None,
        llm: Optional[Any] = None,
        budget_state: Optional[BudgetState] = None,
    ) -> ChainResult:
        """使用 LLM 执行思维链推理

        Args:
            problem: 问题描述
            context: 上下文信息
            strategy: 推理策略
            llm: 可选的 LLM 实例覆盖
            budget_state: 请求级预算状态，不传则内部创建

        Returns:
            ChainResult: 推理结果
        """
        llm = llm or self.llm
        strategy = strategy or self.default_strategy
        start_time = time.time()
        # 每个 reason() 创建独立的请求级 BudgetState
        if budget_state is None:
            budget_state = BudgetState(self._budget_config)

        if not llm:
            logger.warning("无 LLM 可用，回退到模板推理")
            steps = [ReasoningStep(1, "分析问题", f"分析问题：{problem[:100]}", 0.5)]
            result = ChainResult(
                problem=problem, steps=steps,
                conclusion=f"基于问题直接回答：{problem}", confidence=0.2,
                degraded=True,
                degradation_reason="无 LLM 实例，回退到模板推理",
            )
            result.total_duration = time.time() - start_time
            return result

        try:
            if strategy == ChainStrategy.SELF_CONSISTENCY:
                result = await self._self_consistency_reason(problem, context, llm)
            elif strategy == ChainStrategy.LEAST_TO_MOST:
                result = await self._least_to_most_reason(problem, context, llm)
            elif strategy == ChainStrategy.PLAN_AND_SOLVE:
                result = await self._plan_and_solve_reason(problem, context, llm)
            else:
                result = await self._standard_reason(problem, context, llm)

            result.total_duration = time.time() - start_time
            result.strategy = strategy.value

            # 记录历史
            self._record_chain(problem, result)

            return result

        except Exception as e:
            logger.error(f"CoT 推理失败: {e}")
            # 降级到模板
            steps = [ReasoningStep(1, "回退推理", f"LLM 不可用: {str(e)[:200]}", 0.3)]
            result = ChainResult(
                problem=problem, steps=steps,
                conclusion=str(e)[:500], confidence=0.2,
                degraded=True,
                degradation_reason=f"LLM 异常: {str(e)[:200]}",
            )
            result.total_duration = time.time() - start_time
            return result

    async def _standard_reason(
        self, problem: str, context: Optional[Dict], llm: Any,
        budget_state: Optional[BudgetState] = None
    ) -> ChainResult:
        """标准 CoT：逐步推理"""
        prompt = self._build_cot_prompt(problem, context)
        logger.debug(f"标准 CoT 推理: {problem[:60]}...")

        response = await self._call_llm(llm, prompt, temperature=self.temperature, budget_state=budget_state)
        steps, conclusion = self._parse_response(response)

        return ChainResult(
            problem=problem,
            steps=steps or self._make_fallback_steps(problem),
            conclusion=conclusion or response,
            confidence=self._infer_confidence(steps, conclusion),
        )

    async def _self_consistency_reason(
        self, problem: str, context: Optional[Dict], llm: Any,
        budget_state: Optional[BudgetState] = None
    ) -> ChainResult:
        """Self-Consistency CoT：多次采样后投票"""
        prompt = self._build_cot_prompt(problem, context)
        logger.debug(f"Self-Consistency CoT (n={self.consistency_samples}): {problem[:60]}...")

        candidates = []
        for i in range(self.consistency_samples):
            temp = min(0.3 + i * 0.2, 1.0)  # 略微变化温度
            response = await self._call_llm(llm, prompt, temperature=temp, budget_state=budget_state)
            conclusion = self._extract_conclusion(response)
            candidates.append(conclusion)

        # 投票选出最一致的结论
        best = self._majority_vote(candidates)
        agreement = candidates.count(best) / len(candidates)

        steps, _ = self._parse_response(candidates[0])  # 用第一次的步骤

        return ChainResult(
            problem=problem,
            steps=steps or self._make_fallback_steps(problem),
            conclusion=best,
            confidence=agreement,
            all_candidates=candidates,
        )

    async def _least_to_most_reason(
        self, problem: str, context: Optional[Dict], llm: Any,
        budget_state: Optional[BudgetState] = None
    ) -> ChainResult:
        """Least-to-Most CoT：分解子问题，逐一解决"""
        logger.debug(f"Least-to-Most CoT: {problem[:60]}...")

        # 第一步：分解子问题
        decomposition_prompt = (
            f"将以下问题分解为更小的子问题（每行一个子问题）。\n"
            f"问题：{problem}\n"
            f"子问题列表："
        )
        decomp_response = await self._call_llm(llm, decomposition_prompt, temperature=0.3, budget_state=budget_state)
        sub_questions = self._parse_sub_questions(decomp_response)

        if not sub_questions:
            sub_questions = [problem]  # 降级

        # 第二步：逐一解决子问题
        steps = []
        accumulated_context = ""

        for i, sub_q in enumerate(sub_questions):
            step_prompt = (
                f"原问题：{problem}\n"
                f"已解决：\n{accumulated_context}\n"
                f"现在解决子问题 {i+1}/{len(sub_questions)}：{sub_q}\n"
                f"逐步推理："
            )
            answer = await self._call_llm(llm, step_prompt, temperature=0.5, budget_state=budget_state)
            accumulated_context += f"子问题 {i+1}: {sub_q}\n答案: {answer}\n"

            step = ReasoningStep(
                step_number=i + 1,
                description=f"子问题: {sub_q}",
                content=answer,
                confidence=0.7,
            )
            steps.append(step)

        # 第三步：综合
        synthesis_prompt = (
            f"基于以上子问题的答案，请给出原问题的最终结论。\n"
            f"原问题：{problem}\n"
            f"{accumulated_context}\n"
            f"最终结论："
        )
        conclusion = await self._call_llm(llm, synthesis_prompt, temperature=0.3, budget_state=budget_state)

        return ChainResult(
            problem=problem,
            steps=steps,
            conclusion=conclusion or problem,
            confidence=0.8 if len(sub_questions) > 0 else 0.5,
        )

    async def _plan_and_solve_reason(
        self, problem: str, context: Optional[Dict], llm: Any,
        budget_state: Optional[BudgetState] = None
    ) -> ChainResult:
        """Plan-and-Solve CoT：先规划再求解"""
        logger.debug(f"Plan-and-Solve CoT: {problem[:60]}...")

        # 第一步：制定计划
        plan_prompt = (
            f"在回答问题之前，先制定一个逐步的计划。\n"
            f"问题：{problem}\n"
            f"请以 '计划：' 开头列出你的执行步骤。\n"
            f"计划："
        )
        plan = await self._call_llm(llm, plan_prompt, temperature=0.5, budget_state=budget_state)

        # 第二步：按计划执行
        solve_prompt = (
            f"问题：{problem}\n"
            f"计划：\n{plan}\n\n"
            f"请严格按照上述计划逐步执行，给出最终答案。\n"
            f"逐步执行结果："
        )
        solution = await self._call_llm(llm, solve_prompt, temperature=0.5, budget_state=budget_state)

        steps = [
            ReasoningStep(step_number=1, description="制定计划", content=plan, confidence=0.8),
            ReasoningStep(step_number=2, description="按计划执行", content=solution, confidence=0.7),
        ]
        conclusion = self._extract_conclusion(solution)

        return ChainResult(
            problem=problem,
            steps=steps,
            conclusion=conclusion or solution,
            confidence=0.75,
        )

    async def _call_llm(self, llm: Any, prompt: str, temperature: float = 0.7,
                       budget_state: Optional[BudgetState] = None) -> str:
        """调用 LLM 生成文本（带请求级预算检查）"""
        if budget_state is not None:
            budget_state.reserve_llm_call()

        if hasattr(llm, 'generate'):
            # BaseLLM 接口
            import asyncio
            if asyncio.iscoroutinefunction(llm.generate):
                resp = await llm.generate(prompt, temperature=temperature)
            else:
                resp = llm.generate(prompt, temperature=temperature)
            return resp.content if hasattr(resp, 'content') else str(resp)

        elif hasattr(llm, 'chat'):
            from ..llm.base_llm import Message
            messages = [Message(role="user", content=prompt)]
            if asyncio.iscoroutinefunction(llm.chat):
                resp = await llm.chat(messages, temperature=temperature)
            else:
                resp = llm.chat(messages, temperature=temperature)
            return resp.content if hasattr(resp, 'content') else str(resp)

        elif callable(llm):
            # 纯函数
            result = llm(prompt)
            if asyncio.iscoroutine(result):
                result = await result
            return str(result)

        else:
            raise TypeError(f"不支持的 LLM 类型: {type(llm)}")

    # ================================================================
    # 提示词构建
    # ================================================================

    def _build_cot_prompt(self, problem: str, context: Optional[Dict] = None) -> str:
        """构建 CoT 提示词"""
        ctx_str = ""
        if context:
            ctx_str = f"上下文信息：\n{self._format_context(context)}\n\n"

        return (
            f"请逐步推理并回答以下问题。\n"
            f"先给出推理过程（每步以 '步骤 N:' 开头），最后给出结论（以 '结论：' 开头）。\n\n"
            f"{ctx_str}"
            f"问题：{problem}\n\n"
            f"推理过程：\n"
            f"步骤 1："
        )

    def _format_context(self, context: Dict) -> str:
        """格式化上下文"""
        lines = []
        for key, val in context.items():
            if isinstance(val, str) and len(val) > 200:
                val = val[:200] + "..."
            lines.append(f"  {key}: {val}")
        return "\n".join(lines)

    # ================================================================
    # 解析与后处理
    # ================================================================

    def _parse_response(self, text: str) -> Tuple[List[ReasoningStep], str]:
        """从 LLM 回复中提取步骤和结论"""
        if not text:
            return [], ""

        steps = []
        conclusion = ""

        # 匹配 "步骤 N:" 模式
        step_pattern = re.compile(r'(?:步骤|Step)\s*(\d+)\s*[:：]\s*(.*?)(?=(?:步骤|Step)\s*\d+\s*[:：]|结论|Conclusion|$)', re.DOTALL | re.IGNORECASE)
        for match in step_pattern.finditer(text):
            num = int(match.group(1))
            content = match.group(2).strip()
            if content:
                steps.append(ReasoningStep(
                    step_number=num,
                    description=f"步骤 {num}",
                    content=content,
                    confidence=0.7,
                ))

        # 提取结论
        conclusion_match = re.search(r'(?:结论|Conclusion|最终答案|Final Answer)\s*[:：]\s*(.*?)$', text, re.DOTALL | re.IGNORECASE)
        if conclusion_match:
            conclusion = conclusion_match.group(1).strip()
        elif not steps:
            # 没有结构化输出，整段作为结论
            conclusion = text.strip()

        return steps, conclusion

    def _extract_conclusion(self, text: str) -> str:
        """从文本中提取结论"""
        _, conclusion = self._parse_response(text)
        if conclusion:
            return conclusion
        # 取最后一段
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        return paragraphs[-1] if paragraphs else text

    def _infer_confidence(self, steps: List[ReasoningStep], conclusion: str) -> float:
        """根据推理步骤推断置信度"""
        if not steps:
            return 0.3
        if not conclusion:
            return 0.4
        # 步骤越多、信息越丰富，置信度越高
        base = 0.6
        bonus = min(len(steps) * 0.05, 0.3)
        content_len = sum(len(s.content) for s in steps)
        if content_len > 200:
            bonus += 0.1
        return min(base + bonus, 0.99)

    def _majority_vote(self, candidates: List[str]) -> str:
        """多数投票（Self-Consistency）"""
        if not candidates:
            return ""
        # 按频率排序
        from collections import Counter
        counter = Counter(candidates)
        return counter.most_common(1)[0][0]

    def _parse_sub_questions(self, text: str) -> List[str]:
        """解析子问题列表"""
        lines = []
        for line in text.split("\n"):
            line = line.strip()
            # 匹配 "- 子问题" "1. 子问题" "• 子问题" 等格式
            line = re.sub(r'^[\d\-*•·]+\.?\s*', '', line).strip()
            if line and len(line) >= 2:  # 至少2个字符
                lines.append(line)
        return lines

    # ================================================================
    # 旧版兼容接口
    # ================================================================

    def generate_chain(
        self, problem: str, context: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """生成思维链（旧版同步接口 — 仅模板，不调用 LLM）

        确定返回 5 步模板链。如需 LLM 驱动结果请使用:
          await generate_chain_async()
          或
          await reason()
        """
        return self._make_old_chain(problem, context)

    async def generate_chain_async(
        self, problem: str, context: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """生成思维链（异步接口，推荐使用）

        调用底层的 LLM 驱动 reason() 并转换为旧版字典格式。
        """
        result = await self.reason(problem, context)
        return self._chain_result_to_old(result)

    def _make_old_chain(self, problem: str, context: Dict = None) -> List[Dict]:
        """生成旧格式的思维链（模板回退）"""
        chain = [
            self._understand_problem(problem, context),
            self._analyze_problem(problem, context),
            self._generate_solutions(problem, context),
            self._evaluate_solutions(problem, context),
            self._make_decision(problem, context),
        ]
        self._record_old_chain(problem, chain)
        return chain

    def _chain_result_to_old(self, result: ChainResult) -> List[Dict]:
        """将新 ChainResult 转换为旧版字典格式"""
        chain = []
        for i, step in enumerate(result.steps):
            chain.append({
                "step": step.step_number,
                "type": f"reasoning_step_{i}",
                "content": step.content,
                "confidence": step.confidence,
            })
        if result.conclusion:
            chain.append({
                "step": len(result.steps) + 1,
                "type": "decision",
                "content": result.conclusion,
                "confidence": result.confidence,
            })
        return chain

    def _make_fallback_steps(self, problem: str) -> List[ReasoningStep]:
        """创建回退步骤"""
        return [
            ReasoningStep(step_number=1, description="分析问题", content=f"分析问题：{problem[:100]}", confidence=0.5),
            ReasoningStep(step_number=2, description="给出结论", content=problem, confidence=0.3),
        ]

    # ================================================================
    # 旧版明细方法（保持兼容性）
    # ================================================================

    def _understand_problem(self, problem, context=None):
        return {"step": 1, "type": "understanding",
                "content": f"我需要理解问题：{problem}",
                "context": context, "confidence": 0.9}

    def _analyze_problem(self, problem, context=None, prev=None):
        return {"step": 2, "type": "analysis",
                "content": f"我需要分析问题的各个方面：{problem}",
                "context": context, "previous_step": prev, "confidence": 0.8}

    def _generate_solutions(self, problem, context=None, prev=None):
        return {"step": 3, "type": "solution_generation",
                "content": f"我需要生成可能的解决方案：{problem}",
                "solutions": [f"方案1", f"方案2", f"方案3"],
                "context": context, "previous_step": prev, "confidence": 0.7}

    def _evaluate_solutions(self, problem, context=None, prev=None):
        evaluations = []
        if prev and "solutions" in prev:
            for i, sol in enumerate(prev["solutions"]):
                evaluations.append({"solution": sol, "score": 0.8 - i * 0.1, "reason": f"评估方案{i+1}"})
        return {"step": 4, "type": "solution_evaluation",
                "content": f"我需要评估解决方案：{problem}",
                "evaluations": evaluations, "context": context,
                "previous_step": prev, "confidence": 0.8}

    def _make_decision(self, problem, context=None, prev=None):
        best_solution, best_score = None, 0
        if prev and "evaluations" in prev:
            for ev in prev["evaluations"]:
                if ev["score"] > best_score:
                    best_score = ev["score"]
                    best_solution = ev["solution"]
        return {"step": 5, "type": "decision",
                "content": f"我需要做出决策：{problem}",
                "best_solution": best_solution, "best_score": best_score,
                "context": context, "previous_step": prev, "confidence": 0.9}

    def _record_old_chain(self, problem, chain):
        self.chain_history.append({
            "problem": problem, "chain": chain, "timestamp": time.time()
        })
        if len(self.chain_history) > self.max_chain_length:
            self.chain_history = self.chain_history[-self.max_chain_length:]

    def _record_chain(self, problem: str, result: ChainResult):
        """记录新版 ChainResult 历史"""
        self.chain_history.append(result)
        if len(self.chain_history) > self.max_chain_length:
            self.chain_history = self.chain_history[-self.max_chain_length:]

    def get_chain_history(self) -> List[Any]:
        """获取思维链历史"""
        return self.chain_history

    def set_max_chain_length(self, length: int):
        """设置最大思维链长度"""
        self.max_chain_length = max(1, length)
