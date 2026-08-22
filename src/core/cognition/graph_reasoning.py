#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图推理引擎
基于知识图谱的推理系统
"""
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import networkx as nx
import json

logger = logging.getLogger(__name__)


class RelationType(Enum):
    """关系类型"""
    IS_A = "is_a"
    PART_OF = "part_of"
    CAUSED_BY = "caused_by"
    LEADS_TO = "leads_to"
    SIMILAR_TO = "similar_to"
    USES = "uses"
    DEPENDS_ON = "depends_on"
    EXAMPLE_OF = "example_of"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"


@dataclass
class Entity:
    """实体"""
    id: str
    name: str
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Relation:
    """关系"""
    id: str
    source_id: str
    target_id: str
    type: RelationType
    weight: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasoningPath:
    """推理路径"""
    nodes: List[Entity]
    relations: List[Relation]
    confidence: float = 0.0
    explanation: str = ""


class GraphReasoningEngine:
    """图推理引擎"""

    def __init__(self):
        self.graph = nx.DiGraph()
        self.entities: Dict[str, Entity] = {}
        self.relations: Dict[str, Relation] = {}
        self.relation_counter = 0

    def add_entity(self, entity: Entity) -> str:
        """添加实体"""
        self.entities[entity.id] = entity
        self.graph.add_node(entity.id, **entity.properties, **entity.metadata)
        logger.debug(f"Added entity: {entity.name}")
        return entity.id

    def add_relation(self, source_id: str, target_id: str, 
                   rel_type: RelationType,
                   weight: float = 1.0,
                   properties: Dict = None) -> str:
        """添加关系"""
        if source_id not in self.entities or target_id not in self.entities:
            raise ValueError("Source or target entity not found")
        
        rel_id = f"rel_{self.relation_counter}"
        self.relation_counter += 1
        
        relation = Relation(
            id=rel_id,
            source_id=source_id,
            target_id=target_id,
            type=rel_type,
            weight=weight,
            properties=properties or {}
        )
        
        self.relations[rel_id] = relation
        self.graph.add_edge(
            source_id, target_id,
            relation_type=rel_type.value,
            weight=weight,
            relation_id=rel_id,
            **(properties or {})
        )
        
        logger.debug(f"Added relation: {source_id} -> {target_id}")
        return rel_id

    def find_path(self, start_id: str, end_id: str, 
                  max_depth: int = 5,
                  min_confidence: float = 0.0) -> Optional[ReasoningPath]:
        """查找两个实体间的推理路径"""
        try:
            # 使用网络X 最短路径
            paths = list(nx.all_simple_paths(
                self.graph, start_id, end_id, cutoff=max_depth
            ))
            
            best_path = None
            best_score = 0.0
            
            for path_nodes in paths:
                path_score = self._score_path(path_nodes)
                if path_score > best_score and path_score >= min_confidence:
                    best_score = path_score
                    best_path = path_nodes
            
            if best_path:
                return self._build_reasoning_path(best_path, best_score)
            
            return None
            
        except nx.NetworkXNoPath:
            return None

    def _score_path(self, node_ids: List[str]) -> float:
        """评分路径"""
        if len(node_ids) < 2:
            return 0.0
        
        total_weight = 0.0
        for i in range(len(node_ids) - 1):
            u, v = node_ids[i], node_ids[i + 1]
            edge_data = self.graph.get_edge_data(u, v)
            if edge_data:
                total_weight += edge_data.get('weight', 1.0)
        
        return total_weight / (len(node_ids) - 1)

    def _build_reasoning_path(self, node_ids: List[str], confidence: float) -> ReasoningPath:
        """构建推理路径对象"""
        entities = [self.entities[nid] for nid in node_ids]
        relations = []
        
        for i in range(len(node_ids) - 1):
            u, v = node_ids[i], node_ids[i + 1]
            edge_data = self.graph.get_edge_data(u, v)
            if edge_data and 'relation_id' in edge_data:
                relations.append(self.relations[edge_data['relation_id']])
        
        explanation = " -> ".join(e.name for e in entities)
        return ReasoningPath(
            nodes=entities,
            relations=relations,
            confidence=confidence,
            explanation=explanation
        )

    def get_neighbors(self, entity_id: str, 
                      relation_types: List[RelationType] = None,
                      max_distance: int = 1) -> List[Tuple[Entity, float]]:
        """获取邻居实体"""
        if entity_id not in self.entities:
            return []
        
        neighbors = []
        
        if max_distance == 1:
            neighbor_ids = list(self.graph.successors(entity_id)) + list(self.graph.predecessors(entity_id))
        else:
            subgraph = nx.ego_graph(self.graph, entity_id, radius=max_distance)
            neighbor_ids = list(subgraph.nodes())
        
        for nid in neighbor_ids:
            if nid == entity_id:
                continue
            
            try:
                if self.graph.has_edge(entity_id, nid):
                    weight = self.graph[entity_id][nid].get('weight', 1.0)
                    neighbors.append((self.entities[nid], weight))
            except (KeyError, nx.NetworkXError):
                continue
        
        return neighbors

    def reasoning_chain(self, start_id: str, question: str) -> List[ReasoningPath]:
        """推理链"""
        results = []
        
        # BFS 探索
        visited = set()
        queue = deque([(start_id, [start_id])])
        
        while queue:
            current_id, path = queue.popleft()
            
            if current_id in visited:
                continue
            
            visited.add(current_id)
            
            # 检查当前实体是否相关
            if self._is_relevant_to_question(current_id, question):
                reasoning_path = self._build_reasoning_path(path, 0.8)
                results.append(reasoning_path)
            
            # 继续探索
            for neighbor in self.graph.successors(current_id):
                if neighbor not in visited:
                    new_path = path + [neighbor]
                    if len(new_path) <= 5:
                        queue.append((neighbor, new_path))
        
        return sorted(results, key=lambda p: p.confidence, reverse=True)[:5]

    def _is_relevant_to_question(self, entity_id: str, question: str) -> bool:
        """检查实体是否与问题相关"""
        entity = self.entities.get(entity_id)
        if not entity:
            return False
        
        question_lower = question.lower()
        name_lower = entity.name.lower()
        
        return any(word in name_lower for word in question_lower.split())

    def get_subgraph(self, entity_ids: List[str]) -> 'GraphReasoningEngine':
        """获取子图"""
        sub_engine = GraphReasoningEngine()
        subgraph = self.graph.subgraph(entity_ids)
        
        for nid in subgraph.nodes():
            if nid in self.entities:
                sub_engine.add_entity(self.entities[nid])
        
        for u, v, data in subgraph.edges(data=True):
            if 'relation_id' in data:
                rel = self.relations[data['relation_id']]
                sub_engine.add_relation(u, v, rel.type, rel.weight, rel.properties)
        
        return sub_engine

    def export_graph(self, filename: str):
        """导出图"""
        data = {
            'entities': [
                {
                    'id': e.id,
                    'name': e.name,
                    'type': e.type,
                    'properties': e.properties
                }
                for e in self.entities.values()
            ],
            'relations': [
                {
                    'id': r.id,
                    'source': r.source_id,
                    'target': r.target_id,
                    'type': r.type.value,
                    'weight': r.weight
                }
                for r in self.relations.values()
            ]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Graph exported to {filename}")

    @classmethod
    def import_graph(cls, filename: str) -> 'GraphReasoningEngine':
        """导入图"""
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        engine = cls()
        
        for e_data in data['entities']:
            entity = Entity(
                id=e_data['id'],
                name=e_data['name'],
                type=e_data['type'],
                properties=e_data.get('properties', {})
            )
            engine.add_entity(entity)
        
        for r_data in data['relations']:
            engine.add_relation(
                r_data['source'],
                r_data['target'],
                RelationType(r_data['type']),
                r_data['weight']
            )
        
        return engine

    def get_statistics(self) -> Dict[str, Any]:
        """获取图统计"""
        return {
            'entities_count': len(self.entities),
            'relations_count': len(self.relations),
            'density': nx.density(self.graph),
            'components': nx.number_connected_components(self.graph.to_undirected()),
            'avg_degree': sum(d for n, d in self.graph.degree()) / max(1, len(self.graph))
        }
