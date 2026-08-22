#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
树状思维推理引擎 (Tree of Thought, ToT)
基于论文 "Tree of Thoughts: Deliberate Problem Solving with Large Language Models"
"""
import random
import math
from typing import List, Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class ThoughtType(Enum):
    """思维节点类型"""
    INITIAL = "initial"
    IDEA = "idea"
    REASONING = "reasoning"
    EVALUATION = "evaluation"
    FINAL = "final"


@dataclass
class ThoughtNode:
    """思维节点"""
    id: str
    content: str
    depth: int
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    value: float = 0.0
    confidence: float = 0.5
    node_type: ThoughtType = ThoughtType.IDEA
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    visits: int = 0


@dataclass
class TreeSearchConfig:
    """树搜索配置"""
    max_depth: int = 4
    branch_factor: int = 3
    temperature: float = 0.7
    pruning_threshold: float = 0.3
    exploration_weight: float = 0.5
    use_beam_width: int = 3


class TreeOfThought:
    """树状思维推理引擎"""

    def __init__(self, config: Optional[TreeSearchConfig] = None):
        self.config = config or TreeSearchConfig()
        self.nodes: Dict[str, ThoughtNode] = {}
        self.root_id: Optional[str] = None
        self.node_counter = 0
        self.visits = defaultdict(int)

    def create_root(self, problem: str) -> ThoughtNode:
        """创建根节点"""
        root_id = f"root_{self.node_counter}"
        self.node_counter += 1
        
        root = ThoughtNode(
            id=root_id,
            content=problem,
            depth=0,
            node_type=ThoughtType.INITIAL,
            value=0.5,
            confidence=0.5
        )
        
        self.nodes[root_id] = root
        self.root_id = root_id
        logger.info(f"Created root node for problem: {problem[:50]}...")
        return root

    def expand_node(self, node_id: str, thoughts: List[str]) -> List[ThoughtNode]:
        """扩展节点，生成子节点"""
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} not found")
        
        parent = self.nodes[node_id]
        
        if parent.depth >= self.config.max_depth:
            logger.warning(f"Max depth reached for node {node_id}")
            return []
        
        new_nodes = []
        for i, thought in enumerate(thoughts[:self.config.branch_factor]):
            child_id = f"node_{self.node_counter}"
            self.node_counter += 1
            
            child = ThoughtNode(
                id=child_id,
                content=thought,
                depth=parent.depth + 1,
                parent_id=node_id,
                node_type=ThoughtType.IDEA,
                value=0.0,
                confidence=0.5
            )
            
            self.nodes[child_id] = child
            parent.children_ids.append(child_id)
            new_nodes.append(child)
        
        logger.debug(f"Expanded node {node_id} with {len(new_nodes)} children")
        return new_nodes

    def evaluate_node(self, node_id: str, score: float, confidence: float = 0.5):
        """评估节点"""
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} not found")
        
        node = self.nodes[node_id]
        node.value = score
        node.confidence = confidence
        node.visits += 1
        logger.debug(f"Evaluated node {node_id}: value={score}, confidence={confidence}")

    def select_best_paths(self, k: int = None) -> List[List[ThoughtNode]]:
        """选择最佳的 k 条路径"""
        if not self.root_id:
            return []
        
        k = k or self.config.use_beam_width
        
        # 收集所有完整路径
        all_paths = self._collect_paths(self.root_id)
        
        # 按路径价值排序
        scored_paths = []
        for path in all_paths:
            path_value = sum(n.value for n in path)
            scored_paths.append((path_value, path))
        
        scored_paths.sort(key=lambda x: x[0], reverse=True)
        
        return [path for _, path in scored_paths[:k]]

    def _collect_paths(self, node_id: str, current_path: List[ThoughtNode] = None) -> List[List[ThoughtNode]]:
        """收集从节点开始的所有路径"""
        if current_path is None:
            current_path = []
        
        node = self.nodes[node_id]
        current_path.append(node)
        
        if not node.children_ids:
            return [list(current_path)]
        
        all_paths = []
        for child_id in node.children_ids:
            child_paths = self._collect_paths(child_id, list(current_path))
            all_paths.extend(child_paths)
        
        return all_paths

    def mcts_selection(self) -> str:
        """蒙特卡洛树搜索选择"""
        if not self.root_id:
            raise ValueError("Tree not initialized")
        
        # 使用 UCT 公式选择
        def uct_score(node: ThoughtNode, parent_visits: int) -> float:
            if node.visits == 0:
                return float('inf')
            exploitation = node.value
            exploration = self.config.exploration_weight * math.sqrt(
                math.log(max(1, parent_visits)) / max(1, node.visits)
            )
            return exploitation + exploration

        current_id = self.root_id
        path = [current_id]
        
        while self.nodes[current_id].children_ids:
            parent = self.nodes[current_id]
            children = [self.nodes[cid] for cid in parent.children_ids]
            
            best_child = max(children, key=lambda c: uct_score(c, parent.visits))
            current_id = best_child.id
            path.append(current_id)
        
        return current_id

    def prune_tree(self, threshold: float = None) -> int:
        """剪枝树，移除价值低的节点"""
        threshold = threshold or self.config.pruning_threshold
        pruned_count = 0
        
        # 从叶子节点开始递归剪枝
        def prune_node(node_id: str) -> bool:
            nonlocal pruned_count
            node = self.nodes.get(node_id)
            if not node:
                return False
            
            # 先处理子节点
            to_remove = []
            for child_id in node.children_ids:
                if prune_node(child_id):
                    to_remove.append(child_id)
            
            # 检查是否需要剪枝当前节点
            if node.value < threshold and node.depth > 0:
                if not node.children_ids:
                    pruned_count += 1
                    return True
            
            # 移除被剪枝的子节点
            for child_id in to_remove:
                node.children_ids.remove(child_id)
                self.nodes.pop(child_id, None)
            
            return False
        
        if self.root_id:
            prune_node(self.root_id)
        
        logger.info(f"Pruned {pruned_count} nodes from tree")
        return pruned_count

    def get_tree_structure(self) -> Dict[str, Any]:
        """获取树结构"""
        if not self.root_id:
            return {}
        
        def build_subtree(node_id: str) -> Dict[str, Any]:
            node = self.nodes[node_id]
            return {
                "id": node.id,
                "content": node.content,
                "depth": node.depth,
                "value": node.value,
                "confidence": node.confidence,
                "type": node.node_type.value,
                "children": [build_subtree(cid) for cid in node.children_ids]
            }
        
        return build_subtree(self.root_id)

    def get_best_solution(self) -> Optional[ThoughtNode]:
        """获取最佳解决方案"""
        if not self.root_id:
            return None
        
        # 找到价值最高的节点
        best_node = max(self.nodes.values(), key=lambda n: n.value)
        return best_node


class TreeOfThoughtReasoner:
    """树状思维推理器"""

    def __init__(self, config: TreeSearchConfig = None):
        self.config = config or TreeSearchConfig()
        self.tree = TreeOfThought(self.config)

    def reason(self, problem: str, 
               generator: Callable[[str], List[str]],
               evaluator: Callable[[str], float]) -> Dict[str, Any]:
        """执行树状思维推理（同步版）

        传入的 generator/evaluator 必须是同步函数。
        对于异步回调，请使用 reason_async()。
        """
        logger.info(f"Starting ToT reasoning for problem: {problem[:50]}...")
        
        root = self.tree.create_root(problem)
        
        for depth in range(self.config.max_depth):
            current_id = self.tree.mcts_selection()
            node = self.tree.nodes[current_id]
            new_thoughts = generator(node.content)
            children = self.tree.expand_node(current_id, new_thoughts)
            
            for child in children:
                score = evaluator(child.content)
                self.tree.evaluate_node(child.id, score)
        
        self.tree.prune_tree()
        return self._collect_results()

    async def reason_async(self, problem: str,
                           generator: Callable[[str], Awaitable[List[str]]],
                           evaluator: Callable[[str], Awaitable[float]]) -> Dict[str, Any]:
        """执行树状思维推理（异步版）

        传入的 generator/evaluator 应为 async def，返回 Awaitable。
        要求 Python 3.11+（asyncio 稳定）。
        """
        logger.info(f"Starting async ToT reasoning for problem: {problem[:50]}...")

        root = self.tree.create_root(problem)

        for depth in range(self.config.max_depth):
            current_id = self.tree.mcts_selection()
            node = self.tree.nodes[current_id]

            # 异步生成
            new_thoughts = await generator(node.content)
            children = self.tree.expand_node(current_id, new_thoughts)

            # 异步评估
            for child in children:
                score = await evaluator(child.content)
                self.tree.evaluate_node(child.id, score)

        self.tree.prune_tree()
        return self._collect_results()

    def _collect_results(self) -> Dict[str, Any]:
        """从树中收集最终结果"""
        best_paths = self.tree.select_best_paths(k=3)
        best_node = self.tree.get_best_solution()
        return {
            "best_solution": best_node.content if best_node else None,
            "best_value": best_node.value if best_node else 0.0,
            "best_paths": [[n.content for n in path] for path in best_paths],
            "tree_structure": self.tree.get_tree_structure(),
            "total_nodes": len(self.tree.nodes),
        }


class BeamSearchConfig:
    """束搜索配置"""
    beam_width: int = 3
    max_depth: int = 5


class BeamSearchTree:
    """束搜索树"""

    def __init__(self, config: BeamSearchConfig = None):
        self.config = config or BeamSearchConfig()
        self.layers: List[List[ThoughtNode]] = []

    def search(self, initial_state: str, 
               generator: Callable, evaluator: Callable) -> List[ThoughtNode]:
        """束搜索"""
        # 初始层
        initial_node = ThoughtNode(
            id="beam_0_0",
            content=initial_state,
            depth=0,
            value=0.5
        )
        
        self.layers.append([initial_node])
        
        for depth in range(self.config.max_depth):
            current_layer = self.layers[depth]
            next_layer = []
            
            for node in current_layer:
                new_thoughts = generator(node.content)
                
                for thought in new_thoughts:
                    child = ThoughtNode(
                        id=f"beam_{depth+1}_{len(next_layer)}",
                        content=thought,
                        depth=depth+1,
                        value=0.0
                    )
                    child.value = evaluator(thought)
                    next_layer.append(child)
            
            # 排序并取 top-k
            next_layer.sort(key=lambda n: n.value, reverse=True)
            self.layers.append(next_layer[:self.config.beam_width])
        
        return self.layers[-1]
