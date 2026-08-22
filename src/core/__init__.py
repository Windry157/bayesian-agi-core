#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bayesian AGI Core - 核心模块
基于自由能原理和主动推理的认知智能体内核
"""

__version__ = "1.0.0"
__author__ = "Bayesian AGI Team"

# 导出主要模块
from . import assistant
from . import interfaces
from . import cognition
from . import memory
from . import learning
from . import llm
from . import knowledge
from . import knowledge_graph
from . import uncertainty
from . import safety
from . import plugins
from . import cache
from . import monitoring
from . import observability
from . import filesystem
from . import agent
from . import task_dispatcher
from . import code
from . import conversation
from . import evaluation
from . import multimodal
from . import distributed
from . import visualization

__all__ = [
    "assistant",
    "interfaces",
    "cognition",
    "memory",
    "learning",
    "llm",
    "knowledge",
    "knowledge_graph",
    "uncertainty",
    "safety",
    "plugins",
    "cache",
    "monitoring",
    "observability",
    "filesystem",
    "agent",
    "code",
    "conversation",
    "evaluation",
    "multimodal",
    "distributed",
    "visualization",
    "task_dispatcher"
]
