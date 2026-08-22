#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认知系统包
包含贝叶斯大脑、双系统认知、思维链等核心认知功能
"""

from .bayesian_brain import BayesianBrain
from .cognition_coordinator import CognitionCoordinator
from .system1 import System1
from .system2 import System2
from .chain_of_thought import ChainOfThought
from .multi_agent_orchestrator import MultiAgentOrchestrator

# 生产实践验证的 LLM 预算管理（自由能/推理预算控制）
from .llm_budget import (
    ReasoningBudget,
    LLMResult,
    LLMInvoker,
    FallbackPolicy,
    AsyncLLMProvider,
    SyncLLMProvider,
    BudgetExhaustedError,
)

# 尝试导入高级推理模块，如果依赖不可用则跳过
try:
    from .advanced_reasoning_coordinator import AdvancedReasoningCoordinator, ReasoningStrategy
    from .causal_reasoning import CausalReasoningEngine, CausalStrength, CausalGraph
    from .graph_reasoning import GraphReasoningEngine, RelationType, Entity
    from .tree_of_thought import TreeOfThought, TreeOfThoughtReasoner, TreeSearchConfig
    
    __all__ = [
        "BayesianBrain",
        "CognitionCoordinator",
        "System1",
        "System2",
        "ChainOfThought",
        "MultiAgentOrchestrator",
        "ReasoningBudget",
        "LLMResult",
        "LLMInvoker",
        "FallbackPolicy",
        "AsyncLLMProvider",
        "SyncLLMProvider",
        "BudgetExhaustedError",
        "AdvancedReasoningCoordinator",
        "ReasoningStrategy",
        "CausalReasoningEngine",
        "CausalStrength",
        "CausalGraph",
        "GraphReasoningEngine",
        "RelationType",
        "Entity",
        "TreeOfThought",
        "TreeOfThoughtReasoner",
        "TreeSearchConfig"
    ]
except ImportError as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"高级推理模块导入失败（某些功能可能不可用）: {e}")
    
    __all__ = [
        "BayesianBrain",
        "CognitionCoordinator",
        "System1",
        "System2",
        "ChainOfThought",
        "MultiAgentOrchestrator",
        "ReasoningBudget",
        "LLMResult",
        "LLMInvoker",
        "FallbackPolicy",
        "AsyncLLMProvider",
        "SyncLLMProvider",
        "BudgetExhaustedError",
    ]
