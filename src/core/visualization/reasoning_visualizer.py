#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
推理过程可视化模块
用于可视化树状思维、图推理等过程
"""
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class VisualizationType(Enum):
    """可视化类型"""
    TREE = "tree"
    GRAPH = "graph"
    CHAIN = "chain"
    CHART = "chart"


@dataclass
class VisualizationNode:
    """可视化节点"""
    id: str
    label: str
    type: str = "default"
    value: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VisualizationEdge:
    """可视化边"""
    source: str
    target: str
    type: str = "default"
    weight: float = 1.0
    label: str = ""


@dataclass
class VisualizationData:
    """可视化数据"""
    type: VisualizationType
    nodes: List[VisualizationNode] = field(default_factory=list)
    edges: List[VisualizationEdge] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReasoningVisualizer:
    """推理可视化器"""
    
    def __init__(self):
        self.history: List[VisualizationData] = []
    
    def visualize_tree_of_thought(self, tree_data: Dict[str, Any]) -> VisualizationData:
        """
        可视化树状思维
        
        Args:
            tree_data: 树数据，包含nodes和structure信息
        
        Returns:
            VisualizationData 对象
        """
        viz_data = VisualizationData(
            type=VisualizationType.TREE,
            metadata={"title": "Tree of Thought Reasoning"}
        )
        
        # 解析树结构并创建节点和边
        if "tree_structure" in tree_data:
            self._recursive_build_tree(
                tree_data["tree_structure"],
                viz_data,
                parent_id=None
            )
        
        self.history.append(viz_data)
        return viz_data
    
    def _recursive_build_tree(self, node_data: Dict[str, Any], 
                            viz_data: VisualizationData, 
                            parent_id: Optional[str] = None):
        """递归构建树"""
        node = VisualizationNode(
            id=node_data["id"],
            label=node_data.get("content", "")[:30] + "..." 
                  if len(node_data.get("content", "")) > 30 
                  else node_data.get("content", ""),
            type=node_data.get("type", "default"),
            value=node_data.get("value", 0.0),
            metadata={
                "depth": node_data.get("depth", 0),
                "confidence": node_data.get("confidence", 0.0)
            }
        )
        
        viz_data.nodes.append(node)
        
        if parent_id is not None:
            edge = VisualizationEdge(
                source=parent_id,
                target=node.id,
                type="parent-child"
            )
            viz_data.edges.append(edge)
        
        # 处理子节点
        for child in node_data.get("children", []):
            self._recursive_build_tree(child, viz_data, node.id)
    
    def visualize_graph_reasoning(self, graph_engine) -> VisualizationData:
        """
        可视化图推理
        
        Args:
            graph_engine: 图推理引擎实例
        
        Returns:
            VisualizationData 对象
        """
        viz_data = VisualizationData(
            type=VisualizationType.GRAPH,
            metadata={"title": "Graph Reasoning"}
        )
        
        # 添加实体节点
        for entity_id, entity in graph_engine.entities.items():
            node = VisualizationNode(
                id=entity_id,
                label=entity.name,
                type=entity.type,
                metadata=entity.properties
            )
            viz_data.nodes.append(node)
        
        # 添加关系边
        for relation in graph_engine.relations.values():
            edge = VisualizationEdge(
                source=relation.source_id,
                target=relation.target_id,
                type=relation.type.value,
                weight=relation.weight,
                label=relation.type.value
            )
            viz_data.edges.append(edge)
        
        self.history.append(viz_data)
        return viz_data
    
    def visualize_causal_reasoning(self, causal_engine) -> VisualizationData:
        """
        可视化因果推理
        
        Args:
            causal_engine: 因果推理引擎实例
        
        Returns:
            VisualizationData 对象
        """
        viz_data = VisualizationData(
            type=VisualizationType.GRAPH,
            metadata={"title": "Causal Reasoning"}
        )
        
        # 添加变量节点
        for var_id, var in causal_engine.graph.variables.items():
            node = VisualizationNode(
                id=var_id,
                label=var.name,
                type="variable",
                value=var.probability_dist.get(True, 0.5) 
                      if var.probability_dist else 0.5,
                metadata={
                    "observed": var.is_observed,
                    "current_value": var.current_value
                }
            )
            viz_data.nodes.append(node)
        
        # 添加因果关系边
        for relation in causal_engine.graph.relations:
            edge = VisualizationEdge(
                source=relation.cause_id,
                target=relation.effect_id,
                type="causes",
                weight=relation.strength.value,
                label=f"causes ({relation.strength.value:.2f})"
            )
            viz_data.edges.append(edge)
        
        self.history.append(viz_data)
        return viz_data
    
    def to_json(self, viz_data: VisualizationData) -> str:
        """转换为JSON格式"""
        data = {
            "type": viz_data.type.value,
            "nodes": [
                {
                    "id": n.id,
                    "label": n.label,
                    "type": n.type,
                    "value": n.value,
                    "metadata": n.metadata
                }
                for n in viz_data.nodes
            ],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "type": e.type,
                    "weight": e.weight,
                    "label": e.label
                }
                for e in viz_data.edges
            ],
            "metadata": viz_data.metadata
        }
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    def export_to_file(self, viz_data: VisualizationData, filepath: str):
        """导出到文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_json(viz_data))
        logger.info(f"Visualization exported to {filepath}")
    
    def get_history(self) -> List[VisualizationData]:
        """获取历史可视化数据"""
        return self.history
    
    def clear_history(self):
        """清除历史"""
        self.history.clear()
