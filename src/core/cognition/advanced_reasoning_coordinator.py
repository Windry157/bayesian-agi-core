#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级推理协调器
整合多种推理方法：树状思维（ToT）、图推理、因果推理、混合策略
支持 LLM 驱动的生成器和评估器
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Callable, Tuple, Union
from enum import Enum
from dataclasses import dataclass, field

from .tree_of_thought import TreeOfThoughtReasoner, TreeSearchConfig
from .graph_reasoning import GraphReasoningEngine, Entity, RelationType
from .causal_reasoning import CausalReasoningEngine
from .budget import ReasoningBudget, ReasoningBudgetExceeded, BudgetState
from .score_parser import parse_evaluation_score, ScoreParseError

logger = logging.getLogger(__name__)


class ReasoningStrategy(Enum):
    """推理策略"""
    TREE_OF_THOUGHT = "tree_of_thought"
    GRAPH_REASONING = "graph_reasoning"
    CAUSAL_REASONING = "causal_reasoning"
    HYBRID = "hybrid"





@dataclass
class ReasoningResult:
    """推理结果"""
    strategy: str
    solution: Any = None
    confidence: float = 0.0
    duration: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    degraded: bool = False
    degradation_reason: Optional[str] = None


class AdvancedReasoningCoordinator:
    """高级推理协调器

    整合多种推理方法：
    - TREE_OF_THOUGHT: 树状思维，MCTS + LLM 生成/评估
    - GRAPH_REASONING: 知识图谱路径推理
    - CAUSAL_REASONING: 因果关系推理（ATE、后门调整、反事实）
    - HYBRID: 混合策略，融合多种推理结果
    """

    def __init__(self, llm: Any = None, budget: Optional[ReasoningBudget] = None):
        """初始化推理协调器

        Args:
            llm: LLM 实例（可选），用于 ToT 的生成和评估
            budget: 推理预算配置（可选），每个 solve_problem() 据此创建 BudgetState
        """
        self.llm = llm
        self._budget_config = budget or ReasoningBudget()
        self.tot_reasoner = TreeOfThoughtReasoner()
        self.graph_engine = GraphReasoningEngine()
        self.causal_engine = CausalReasoningEngine()
        self.strategy_stats: Dict[str, int] = {}

    # ================================================================
    # 主入口
    # ================================================================

    async def solve_problem(
        self,
        problem: str,
        strategy: ReasoningStrategy = ReasoningStrategy.HYBRID,
        llm: Optional[Any] = None,
        budget: Optional[ReasoningBudget] = None,
        **kwargs,
    ) -> ReasoningResult:
        """使用指定策略解决问题

        Args:
            problem: 问题描述
            strategy: 推理策略
            llm: LLM 实例覆盖
            budget: 本次调用的预算覆盖（不传则用初始化时的配置）
            **kwargs: 策略特定参数

        Returns:
            ReasoningResult: 推理结果
        """
        llm = llm or self.llm
        budget_state = BudgetState(budget or self._budget_config)
        _request_start = time.time()

        self.strategy_stats[strategy.value] = self.strategy_stats.get(strategy.value, 0) + 1

        logger.info(f"问题解决 - 策略: {strategy.value} - 问题: {problem[:80]}...")

        try:
            if strategy == ReasoningStrategy.TREE_OF_THOUGHT:
                result = await self._solve_with_tot(problem, llm, budget_state=budget_state, **kwargs)
            elif strategy == ReasoningStrategy.GRAPH_REASONING:
                result = self._solve_with_graph(problem, **kwargs)
            elif strategy == ReasoningStrategy.CAUSAL_REASONING:
                result = self._solve_with_causal(problem, **kwargs)
            else:
                result = await self._solve_hybrid(problem, llm, budget_state=budget_state, **kwargs)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"推理失败 [{strategy.value}]: {e}")
            result = ReasoningResult(
                strategy=strategy.value,
                error=str(e),
                confidence=0.0,
                degraded=True,
                degradation_reason=str(e)[:300],
            )

        # 附加预算报告
        result.details.setdefault("budget", {})
        result.details["budget"]["llm_calls"] = budget_state.llm_calls

        result.duration = time.time() - _request_start
        logger.info(
            f"推理完成 - 策略: {result.strategy}, "
            f"置信度: {result.confidence:.2f}, "
            f"耗时: {result.duration:.2f}s"
        )
        return result

    # ================================================================
    # Tree of Thought
    # ================================================================

    async def _solve_with_tot(
        self, problem: str, llm: Optional[Any],
        budget_state: Optional[BudgetState] = None, **kwargs
    ) -> ReasoningResult:
        """用 LLM 驱动的树状思维解决问题"""
        if not llm:
            logger.warning("无 LLM 可用，使用默认生成器/评估器")
            # 回退到随机评估
            import random
            def generator(x: str) -> List[str]:
                return [f"思路 A: {x} 的解决方案 1", f"思路 B: {x} 的解决方案 2", f"思路 C: {x} 的解决方案 3"]
            def evaluator(x: str) -> float:
                return 0.5 + random.random() * 0.5

            result = self.tot_reasoner.reason(problem, generator, evaluator)
            return ReasoningResult(
                strategy="tree_of_thought",
                solution=result.get("best_solution"),
                confidence=result.get("best_value", 0.5),
                degraded=True,
                degradation_reason="无 LLM，使用随机评估器",
                details={
                    "paths": result.get("best_paths", []),
                    "tree_size": result.get("total_nodes", 0),
                },
            )

        # LLM 驱动的生成器
        async def llm_generator(state: str) -> List[str]:
            prompt = (
                f"你正在解决以下问题：{problem}\n"
                f"当前思考状态：{state}\n\n"
                f"请生成 {kwargs.get('branch_factor', 3)} 个不同的后续思考方向或步骤。\n"
                f"每行一个，用 '-' 开头。"
            )
            response = await self._call_llm(llm, prompt, temperature=0.8,
                                           budget_state=budget_state)
            thoughts = []
            for line in response.split("\n"):
                line = line.strip().lstrip("- *•").strip()
                if line and len(line) > 10:
                    thoughts.append(line)
            return thoughts[:kwargs.get("branch_factor", 3)]

        # LLM 驱动的评估器 — 结构化输出优先
        async def llm_evaluator(state: str) -> float:
            prompt = (
                f"评估以下思考方向对解决以下问题的价值（0-1 分）。\n"
                f"问题：{problem}\n"
                f"思考方向：{state}\n\n"
                f"请只返回如下 JSON 格式（不要包含其他文字）：\n"
                f'{{"score": 0.75, "reason": "简短理由"}}'
            )
            response = await self._call_llm(llm, prompt, temperature=0.3,
                                           budget_state=budget_state)
            try:
                return parse_evaluation_score(response)
            except ScoreParseError as e:
                logger.error(f"ToT 评估器解析失败: {e}")
                raise

        # 使用异步 reason_async() — generator/evaluator 会被正确 await
        # 每次请求创建独立的 TreeOfThoughtReasoner，避免搜索树跨请求污染
        from .tree_of_thought import TreeOfThoughtReasoner
        tot = TreeOfThoughtReasoner(self.tot_reasoner.config)
        result = await tot.reason_async(problem, llm_generator, llm_evaluator)

        return ReasoningResult(
            strategy="tree_of_thought",
            solution=result.get("best_solution"),
            confidence=result.get("best_value", 0.5),
            details={
                "paths": result.get("best_paths", []),
                "tree_structure": result.get("tree_structure", {}),
                "tree_size": result.get("total_nodes", 0),
            },
        )

    # ================================================================
    # Graph Reasoning
    # ================================================================

    def _solve_with_graph(
        self, problem: str, **kwargs
    ) -> ReasoningResult:
        """用图推理解决问题"""
        entities_data = kwargs.get("entities", [])
        relations_data = kwargs.get("relations", [])
        source_entity = kwargs.get("source")
        target_entity = kwargs.get("target")

        # 添加实体
        entity_map = {}
        for i, e in enumerate(entities_data):
            if isinstance(e, str):
                entity = Entity(id=f"e_{i}", name=e, type="concept")
            elif isinstance(e, dict):
                entity = Entity(
                    id=e.get("id", f"e_{i}"),
                    name=e.get("name", f"entity_{i}"),
                    type=e.get("type", "concept"),
                    properties=e.get("properties", {}),
                )
            else:
                continue
            self.graph_engine.add_entity(entity)
            entity_map[entity.name] = entity.id

        # 添加关系
        for r in relations_data:
            if isinstance(r, dict) and "source" in r and "target" in r:
                try:
                    src = entity_map.get(r["source"], r["source"])
                    tgt = entity_map.get(r["target"], r["target"])
                    rtype = RelationType(r.get("type", "related_to"))
                    self.graph_engine.add_relation(
                        src, tgt, rtype, r.get("weight", 1.0)
                    )
                except (ValueError, KeyError) as e:
                    logger.warning(f"添加关系失败: {e}")

        details = {
            "statistics": self.graph_engine.get_statistics(),
        }

        # 如果指定了源和目标，找路径
        if source_entity and target_entity:
            src_id = entity_map.get(source_entity, source_entity)
            tgt_id = entity_map.get(target_entity, target_entity)
            path = self.graph_engine.find_path(src_id, tgt_id)
            if path:
                details["path"] = {
                    "entities": [e.name for e in path.nodes],
                    "confidence": path.confidence,
                    "explanation": path.explanation,
                }
                return ReasoningResult(
                    strategy="graph_reasoning",
                    solution=path.explanation,
                    confidence=path.confidence,
                    details=details,
                )

        return ReasoningResult(
            strategy="graph_reasoning",
            confidence=0.5,
            details=details,
        )

    # ================================================================
    # Causal Reasoning
    # ================================================================

    def _solve_with_causal(
        self, problem: str, **kwargs
    ) -> ReasoningResult:
        """用因果推理解决问题"""
        variables = kwargs.get("variables", [])
        relations = kwargs.get("relations", [])

        # 添加变量
        for v in variables:
            if isinstance(v, dict):
                self.causal_engine.add_variable(
                    v["id"], v.get("name", v["id"]),
                    v.get("possible_values"),
                )

        # 添加因果关系
        for r in relations:
            if isinstance(r, dict):
                self.causal_engine.add_causal_relation(
                    r["cause"], r["effect"],
                    r.get("strength", 0.5),
                    r.get("cond_probs"),
                )

        # 如果指定了观察值
        observations = kwargs.get("observations", {})
        for var_id, value in observations.items():
            self.causal_engine.observe(var_id, value)

        details = {"variables": len(variables), "relations": len(relations)}

        # 因果效应推断
        if kwargs.get("cause") and kwargs.get("effect"):
            effect = self.causal_engine.causal_effect(
                kwargs["cause"], kwargs["effect"]
            )
            details["causal_effect"] = effect

            explanation = (
                f"因果效应(ATE)={effect['ate']:.3f}: "
                f"P(Y|do(X=1))={effect['prob_true']:.3f}, "
                f"P(Y|do(X=0))={effect['prob_false']:.3f}"
            )

            return ReasoningResult(
                strategy="causal_reasoning",
                solution=explanation,
                confidence=min(0.5 + abs(effect["ate"]) * 0.3, 0.95),
                details=details,
            )

        # 反事实推理
        if kwargs.get("counterfactual_target") and kwargs.get("counterfactual_condition"):
            result = self.causal_engine.counterfactual_query(
                kwargs["counterfactual_target"],
                kwargs["counterfactual_condition"],
            )
            details["counterfactual_result"] = result

            return ReasoningResult(
                strategy="causal_reasoning",
                solution=f"反事实推理结果: {result:.3f}",
                confidence=0.6,
                details=details,
            )

        return ReasoningResult(
            strategy="causal_reasoning",
            confidence=0.5,
            details=details,
        )

    # ================================================================
    # Hybrid
    # ================================================================

    async def _solve_hybrid(
        self, problem: str, llm: Optional[Any],
        budget_state: Optional[BudgetState] = None, **kwargs
    ) -> ReasoningResult:
        """混合策略：同时运行 ToT + Graph + Causal，融合结果

        每个分支独立超时，异常不拖垮其他分支。
        """
        branch_timeout = kwargs.get("branch_timeout", 15.0)

        async def _run_with_timeout(coro, name: str):
            """带超时的分支执行，超时返回降级结果"""
            try:
                return await asyncio.wait_for(coro, timeout=branch_timeout)
            except asyncio.TimeoutError:
                logger.warning(f"Hybrid 分支 [{name}] 超时 ({branch_timeout}s)")
                return ReasoningResult(
                    strategy=name, error=f"超时 ({branch_timeout}s)",
                    confidence=0.0, degraded=True,
                    degradation_reason=f"分支超时 ({branch_timeout}s)",
                )
            except asyncio.CancelledError:
                logger.warning(f"Hybrid 分支 [{name}] 被取消")
                raise
            except Exception as e:
                logger.warning(f"Hybrid 分支 [{name}] 异常: {e}")
                return ReasoningResult(
                    strategy=name, error=str(e),
                    confidence=0.0, degraded=True,
                    degradation_reason=f"分支异常: {str(e)[:200]}",
                )

        import functools
        tot_coro = self._solve_with_tot(problem, llm, budget_state=budget_state, **kwargs)
        loop = asyncio.get_event_loop()
        graph_coro = loop.run_in_executor(
            None, functools.partial(self._solve_with_graph, problem, **kwargs)
        )
        causal_coro = loop.run_in_executor(
            None, functools.partial(self._solve_with_causal, problem, **kwargs)
        )

        # 各分支独立超时
        tot_result = await _run_with_timeout(tot_coro, "tree_of_thought")
        graph_result = await _run_with_timeout(graph_coro, "graph_reasoning")
        causal_result = await _run_with_timeout(causal_coro, "causal_reasoning")

        # 融合结果
        scores = [
            (tot_result.confidence, tot_result.solution),
            (graph_result.confidence, graph_result.solution),
            (causal_result.confidence, causal_result.solution),
        ]
        # 按置信度排序
        scores.sort(key=lambda x: x[0], reverse=True)

        # 选择最高置信度的
        best_solution = scores[0][1] if scores[0][1] else problem
        combined_confidence = sum(s[0] for s in scores) / len(scores)

        return ReasoningResult(
            strategy="hybrid",
            solution=best_solution,
            confidence=combined_confidence,
            details={
                "tree_of_thought": {
                    "solution": tot_result.solution,
                    "confidence": tot_result.confidence,
                },
                "graph_reasoning": {
                    "solution": graph_result.solution,
                    "confidence": graph_result.confidence,
                },
                "causal_reasoning": {
                    "solution": causal_result.solution,
                    "confidence": causal_result.confidence,
                },
                "voting": {
                    "method": "confidence_weighted",
                    "scores": [
                        {"strategy": "tot", "confidence": tot_result.confidence},
                        {"strategy": "graph", "confidence": graph_result.confidence},
                        {"strategy": "causal", "confidence": causal_result.confidence},
                    ],
                },
            },
        )

    # ================================================================
    # 工具
    # ================================================================

    async def _call_llm(self, llm: Any, prompt: str, temperature: float = 0.7,
                       budget_state: Optional[BudgetState] = None) -> str:
        """调用 LLM（带预算检查）"""
        if budget_state is not None:
            budget_state.reserve_llm_call()

        if hasattr(llm, 'generate'):
            resp = llm.generate(prompt, temperature=temperature)
            if asyncio.iscoroutine(resp):
                resp = await resp
            return resp.content if hasattr(resp, 'content') else str(resp)

        if hasattr(llm, 'chat'):
            from ..llm.base_llm import Message
            messages = [Message(role="user", content=prompt)]
            resp = llm.chat(messages, temperature=temperature)
            if asyncio.iscoroutine(resp):
                resp = await resp
            return resp.content if hasattr(resp, 'content') else str(resp)

        if callable(llm):
            result = llm(prompt)
            if asyncio.iscoroutine(result):
                result = await result
            return str(result)

        raise TypeError(f"不支持的 LLM 类型: {type(llm)}")

    def get_statistics(self) -> Dict[str, Any]:
        """获取推理统计"""
        return {
            "strategy_usage": dict(self.strategy_stats),
            "graph_entities": len(self.graph_engine.entities),
            "graph_relations": len(self.graph_engine.relations),
            "causal_variables": len(self.causal_engine.graph.variables),
            "causal_relations": len(self.causal_engine.graph.relations),
        }

    def reset(self):
        """重置所有引擎状态"""
        self.graph_engine = GraphReasoningEngine()
        self.causal_engine = CausalReasoningEngine()
        self.strategy_stats.clear()
        logger.info("高级推理协调器状态已重置")
