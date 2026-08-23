#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识图谱模块
存储实体和实体之间的关系
"""

import logging
import json
import os
from typing import List, Dict, Any, Optional

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

try:
    import networkx as nx
    HAS_NETWORKX = True
    logger.info("NetworkX 已加载，将使用图结构存储知识图谱")
except ImportError:
    HAS_NETWORKX = False
    logger.warning("NetworkX 未安装，将使用字典存储")


class KnowledgeGraph:
    """知识图谱
    使用图结构存储实体和关系
    """
    
    RELATION_TYPES = [
        "属于", "位于", "发生于", "相关于", "包含", 
        "导致", "由...组成", "使用", "创建", "工作于"
    ]
    
    def __init__(self, persist_dir: str = "knowledge_graph"):
        """初始化知识图谱
        
        Args:
            persist_dir: 持久化目录
        """
        self.persist_dir = persist_dir
        os.makedirs(self.persist_dir, exist_ok=True)
        self._graph_file = os.path.join(persist_dir, "graph.json")
        
        if HAS_NETWORKX:
            self.graph = nx.DiGraph()
        else:
            self.graph = {
                "nodes": {},
                "edges": []
            }
        
        self._load_graph()
    
    def add_entity(self, entity_id: str, entity_type: str, name: str, attributes: Optional[Dict[str, Any]] = None):
        """添加实体
        
        Args:
            entity_id: 实体ID
            entity_type: 实体类型
            name: 实体名称
            attributes: 实体属性
        """
        if HAS_NETWORKX:
            self.graph.add_node(entity_id, type=entity_type, name=name, attributes=attributes or {})
        else:
            self.graph["nodes"][entity_id] = {
                "type": entity_type,
                "name": name,
                "attributes": attributes or {}
            }
        
        logger.info(f"添加实体: {entity_id} ({entity_type}) = '{name}'")
    
    def add_relation(self, source_id: str, target_id: str, relation_type: str, attributes: Optional[Dict[str, Any]] = None):
        """添加关系
        
        Args:
            source_id: 源实体ID
            target_id: 目标实体ID
            relation_type: 关系类型
            attributes: 关系属性
        """
        if HAS_NETWORKX:
            self.graph.add_edge(source_id, target_id, relation=relation_type, attributes=attributes or {})
        else:
            self.graph["edges"].append({
                "source": source_id,
                "target": target_id,
                "relation": relation_type,
                "attributes": attributes or {}
            })
        
        logger.info(f"添加关系: {source_id} -{relation_type}-> {target_id}")
    
    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """获取实体信息
        
        Args:
            entity_id: 实体ID
            
        Returns:
            实体信息
        """
        if HAS_NETWORKX:
            if entity_id in self.graph.nodes:
                return dict(self.graph.nodes[entity_id])
            return None
        else:
            return self.graph["nodes"].get(entity_id)
    
    def get_relations(self, entity_id: str, direction: str = "both") -> List[Dict[str, Any]]:
        """获取实体的关系
        
        Args:
            entity_id: 实体ID
            direction: 方向 (in, out, both)
            
        Returns:
            关系列表
        """
        relations = []
        
        if HAS_NETWORKX:
            if direction in ("out", "both"):
                for target_id, data in self.graph.out_edges(entity_id, data=True):
                    relations.append({
                        "source": entity_id,
                        "target": target_id,
                        "relation": data.get("relation"),
                        "attributes": data.get("attributes", {})
                    })
            
            if direction in ("in", "both"):
                for source_id, data in self.graph.in_edges(entity_id, data=True):
                    relations.append({
                        "source": source_id,
                        "target": entity_id,
                        "relation": data.get("relation"),
                        "attributes": data.get("attributes", {})
                    })
        else:
            for edge in self.graph["edges"]:
                if direction in ("out", "both") and edge["source"] == entity_id:
                    relations.append(edge)
                if direction in ("in", "both") and edge["target"] == entity_id:
                    relations.append(edge)
        
        return relations
    
    def query_path(self, source_id: str, target_id: str, max_depth: int = 3) -> List[List[str]]:
        """查询两个实体之间的路径
        
        Args:
            source_id: 源实体ID
            target_id: 目标实体ID
            max_depth: 最大路径深度
            
        Returns:
            路径列表
        """
        paths = []
        
        if HAS_NETWORKX:
            try:
                for path in nx.all_simple_paths(self.graph, source_id, target_id, cutoff=max_depth):
                    paths.append(path)
            except nx.NetworkXNoPath:
                pass
        else:
            # 简化的路径查找（BFS）
            visited = {source_id}
            queue = [(source_id, [source_id])]
            
            while queue:
                current, path = queue.pop(0)
                
                if current == target_id:
                    paths.append(path)
                    continue
                
                if len(path) > max_depth:
                    continue
                
                for edge in self.graph["edges"]:
                    if edge["source"] == current and edge["target"] not in visited:
                        visited.add(edge["target"])
                        queue.append((edge["target"], path + [edge["target"]]))
        
        return paths
    
    def infer_relations(self, entity_id: str) -> List[Dict[str, Any]]:
        """推理实体的隐含关系
        
        Args:
            entity_id: 实体ID
            
        Returns:
            推理出的关系列表
        """
        inferences = []
        
        # 获取所有直接关系
        relations = self.get_relations(entity_id, direction="both")
        
        # 简单推理规则：传递性推理
        # 如果 A -> B 且 B -> C，则可能 A -> C
        if HAS_NETWORKX:
            for path in nx.all_simple_paths(self.graph, entity_id, None, cutoff=2):
                if len(path) == 3:
                    a, b, c = path
                    # 获取关系
                    ab_rel = self.graph.get_edge_data(a, b)
                    bc_rel = self.graph.get_edge_data(b, c)
                    
                    if ab_rel and bc_rel:
                        inferences.append({
                            "source": a,
                            "target": c,
                            "relation": f"间接{ab_rel['relation']}",
                            "via": b,
                            "confidence": 0.7
                        })
        
        logger.info(f"推理完成: {entity_id} 发现 {len(inferences)} 个隐含关系")
        return inferences
    
    def get_entity_count(self) -> int:
        """获取实体数量"""
        if HAS_NETWORKX:
            return self.graph.number_of_nodes()
        return len(self.graph["nodes"])
    
    def get_relation_count(self) -> int:
        """获取关系数量"""
        if HAS_NETWORKX:
            return self.graph.number_of_edges()
        return len(self.graph["edges"])
    
    def save_graph(self):
        """保存知识图谱"""
        try:
            if HAS_NETWORKX:
                # 转换为可序列化格式
                graph_data = {
                    "nodes": [
                        {"id": node, **dict(data)} 
                        for node, data in self.graph.nodes(data=True)
                    ],
                    "edges": [
                        {"source": u, "target": v, **dict(data)} 
                        for u, v, data in self.graph.edges(data=True)
                    ]
                }
            else:
                graph_data = self.graph
            
            with open(self._graph_file, 'w', encoding='utf-8') as f:
                json.dump(graph_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"知识图谱已保存，实体数: {self.get_entity_count()}, 关系数: {self.get_relation_count()}")
        except Exception as e:
            logger.error(f"保存知识图谱失败: {e}")
    
    def _load_graph(self):
        """加载知识图谱"""
        try:
            if os.path.exists(self._graph_file):
                with open(self._graph_file, 'r', encoding='utf-8') as f:
                    graph_data = json.load(f)
                
                if HAS_NETWORKX:
                    for node in graph_data.get("nodes", []):
                        node_id = node.pop("id")
                        self.graph.add_node(node_id, **node)
                    
                    for edge in graph_data.get("edges", []):
                        source = edge.pop("source")
                        target = edge.pop("target")
                        self.graph.add_edge(source, target, **edge)
                else:
                    self.graph = graph_data
                
                logger.info(f"知识图谱已加载，实体数: {self.get_entity_count()}, 关系数: {self.get_relation_count()}")
        except Exception as e:
            logger.error(f"加载知识图谱失败: {e}")
    
    def clear(self):
        """清空知识图谱"""
        if HAS_NETWORKX:
            self.graph.clear()
        else:
            self.graph = {"nodes": {}, "edges": []}
        logger.info("知识图谱已清空")


# 全局知识图谱实例
knowledge_graph = KnowledgeGraph()
