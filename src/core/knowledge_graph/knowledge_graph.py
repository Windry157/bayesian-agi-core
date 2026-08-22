#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识图谱存储与查询模块
基于字典实现简单的图存储，支持节点和边的管理
"""

import json
import os
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from datetime import datetime
import asyncio

from .entity_extractor import Entity, EntityType, EntityExtractor
from .relation_extractor import Relation, RelationType, RelationExtractor, Triple

@dataclass
class GraphNode:
    """图节点"""
    id: str
    name: str
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class GraphEdge:
    """图边"""
    id: str
    source: str
    target: str
    relation: str
    properties: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    created_at: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class KnowledgeGraph:
    """知识图谱"""
    
    def __init__(self, storage_path: str = "memory/knowledge_graph"):
        self.storage_path = storage_path
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: Dict[str, GraphEdge] = {}
        self.adjacency_list: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
        self.entity_to_node: Dict[str, str] = {}
        
        os.makedirs(storage_path, exist_ok=True)
        self._load()
    
    def _get_timestamp(self) -> str:
        """获取时间戳"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _generate_id(self, prefix: str = "node") -> str:
        """生成唯一ID"""
        import uuid
        return f"{prefix}_{uuid.uuid4().hex[:8]}"
    
    def add_node(self, name: str, node_type: str, properties: Optional[Dict[str, Any]] = None) -> str:
        """添加节点"""
        node_id = self._generate_id("node")
        
        node = GraphNode(
            id=node_id,
            name=name,
            type=node_type,
            properties=properties or {},
            created_at=self._get_timestamp(),
            updated_at=self._get_timestamp()
        )
        
        self.nodes[node_id] = node
        self.entity_to_node[name] = node_id
        
        return node_id
    
    def add_edge(
        self,
        source: str,
        target: str,
        relation: str,
        properties: Optional[Dict[str, Any]] = None,
        weight: float = 1.0
    ) -> str:
        """添加边"""
        if source not in self.nodes or target not in self.nodes:
            return None
        
        edge_id = self._generate_id("edge")
        
        edge = GraphEdge(
            id=edge_id,
            source=source,
            target=target,
            relation=relation,
            properties=properties or {},
            weight=weight,
            created_at=self._get_timestamp()
        )
        
        self.edges[edge_id] = edge
        self.adjacency_list[source][relation].append(edge_id)
        
        return edge_id
    
    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """获取节点"""
        return self.nodes.get(node_id)
    
    def get_node_by_name(self, name: str) -> Optional[GraphNode]:
        """通过名称获取节点"""
        node_id = self.entity_to_node.get(name)
        return self.nodes.get(node_id) if node_id else None
    
    def get_neighbors(
        self,
        node_id: str,
        relation: Optional[str] = None
    ) -> List[Tuple[GraphNode, GraphEdge]]:
        """获取邻居节点"""
        neighbors = []
        
        if node_id not in self.adjacency_list:
            return neighbors
        
        relations = [relation] if relation else list(self.adjacency_list[node_id].keys())
        
        for rel in relations:
            for edge_id in self.adjacency_list[node_id].get(rel, []):
                edge = self.edges.get(edge_id)
                if edge:
                    target_node = self.nodes.get(edge.target)
                    if target_node:
                        neighbors.append((target_node, edge))
        
        return neighbors
    
    def find_path(
        self,
        start: str,
        end: str,
        max_depth: int = 3
    ) -> List[List[Tuple[str, str]]]:
        """查找两点间的路径"""
        if start not in self.nodes or end not in self.nodes:
            return []
        
        paths = []
        visited = set()
        
        def dfs(current: str, target: str, path: List[Tuple[str, str]], depth: int):
            if depth > max_depth:
                return
            
            if current == target and path:
                paths.append(path.copy())
                return
            
            for neighbor, edge in self.get_neighbors(current):
                edge_key = (current, neighbor.id, edge.relation)
                if edge_key not in visited:
                    visited.add(edge_key)
                    path.append((neighbor.id, edge.relation))
                    dfs(neighbor.id, target, path, depth + 1)
                    path.pop()
                    visited.remove(edge_key)
        
        dfs(start, end, [], 0)
        return paths
    
    def query_by_relation(self, relation: str) -> List[Tuple[GraphNode, GraphNode]]:
        """按关系类型查询"""
        results = []
        
        for edge in self.edges.values():
            if edge.relation == relation:
                source_node = self.nodes.get(edge.source)
                target_node = self.nodes.get(edge.target)
                if source_node and target_node:
                    results.append((source_node, target_node))
        
        return results
    
    def query_triples(self) -> List[Triple]:
        """查询所有三元组"""
        triples = []
        
        for edge in self.edges.values():
            source_node = self.nodes.get(edge.source)
            target_node = self.nodes.get(edge.target)
            if source_node and target_node:
                triples.append(Triple(
                    head=source_node.name,
                    relation=edge.relation,
                    tail=target_node.name,
                    confidence=edge.weight
                ))
        
        return triples
    
    async def add_from_text(
        self,
        text: str,
        document_id: str,
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """从文本构建知识图谱"""
        entity_extractor = EntityExtractor()
        relation_extractor = RelationExtractor()
        
        entities = await entity_extractor.extract(text, use_llm=use_llm)
        relations = await relation_extractor.extract(text, use_llm=use_llm)
        
        node_ids = set()
        for entity in entities:
            node_id = self.add_node(
                name=entity.name,
                node_type=entity.type.value,
                properties={
                    'confidence': entity.confidence,
                    'document_id': document_id,
                    'position': f"{entity.start_pos}-{entity.end_pos}"
                }
            )
            node_ids.add(node_id)
        
        for relation in relations:
            source_node_id = self.entity_to_node.get(relation.subject)
            target_node_id = self.entity_to_node.get(relation.object)
            
            if not source_node_id:
                source_node_id = self.add_node(
                    name=relation.subject,
                    node_type="UNKNOWN"
                )
            
            if not target_node_id:
                target_node_id = self.add_node(
                    name=relation.object,
                    node_type="UNKNOWN"
                )
            
            self.add_edge(
                source=source_node_id,
                target=target_node_id,
                relation=relation.relation_type.value,
                properties={
                    'confidence': relation.confidence,
                    'context': relation.context,
                    'source': relation.source
                },
                weight=relation.confidence
            )
        
        await self.save()
        
        return {
            'nodes_added': len(node_ids),
            'edges_added': len(relations),
            'total_nodes': len(self.nodes),
            'total_edges': len(self.edges)
        }
    
    async def save(self):
        """保存到文件"""
        data = {
            'nodes': {k: v.to_dict() for k, v in self.nodes.items()},
            'edges': {k: v.to_dict() for k, v in self.edges.items()},
            'entity_to_node': self.entity_to_node
        }
        
        filepath = os.path.join(self.storage_path, "graph_data.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _load(self):
        """从文件加载"""
        filepath = os.path.join(self.storage_path, "graph_data.json")
        
        if not os.path.exists(filepath):
            return
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.nodes = {k: GraphNode(**v) for k, v in data.get('nodes', {}).items()}
            self.edges = {k: GraphEdge(**v) for k, v in data.get('edges', {}).items()}
            self.entity_to_node = data.get('entity_to_node', {})
            
            for node_id, relations in self.adjacency_list.items():
                for edge_id in relations:
                    edge = self.edges.get(edge_id)
                    if edge:
                        self.adjacency_list[edge.source][edge.relation].append(edge_id)
        except Exception as e:
            print(f"加载知识图谱失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取图谱统计信息"""
        relation_counts = defaultdict(int)
        for edge in self.edges.values():
            relation_counts[edge.relation] += 1
        
        type_counts = defaultdict(int)
        for node in self.nodes.values():
            type_counts[node.type] += 1
        
        return {
            'total_nodes': len(self.nodes),
            'total_edges': len(self.edges),
            'node_types': dict(type_counts),
            'relation_types': dict(relation_counts),
            'density': len(self.edges) / (len(self.nodes) ** 2) if len(self.nodes) > 0 else 0
        }
    
    def clear(self):
        """清空图谱"""
        self.nodes.clear()
        self.edges.clear()
        self.adjacency_list.clear()
        self.entity_to_node.clear()
    
    def remove_node(self, node_id: str) -> bool:
        """删除节点及其关联边"""
        if node_id not in self.nodes:
            return False
        
        node = self.nodes[node_id]
        
        edges_to_remove = [
            edge_id for edge_id, edge in self.edges.items()
            if edge.source == node_id or edge.target == node_id
        ]
        
        for edge_id in edges_to_remove:
            self.remove_edge(edge_id)
        
        del self.nodes[node_id]
        if node.name in self.entity_to_node:
            del self.entity_to_node[node.name]
        
        return True
    
    def remove_edge(self, edge_id: str) -> bool:
        """删除边"""
        if edge_id not in self.edges:
            return False
        
        edge = self.edges[edge_id]
        
        if edge.source in self.adjacency_list:
            for rel in self.adjacency_list[edge.source]:
                if edge_id in self.adjacency_list[edge.source][rel]:
                    self.adjacency_list[edge.source][rel].remove(edge_id)
        
        del self.edges[edge_id]
        return True


class GraphQueryEngine:
    """图谱查询引擎"""
    
    def __init__(self, knowledge_graph: KnowledgeGraph):
        self.graph = knowledge_graph
    
    def find_entities_by_type(self, entity_type: str) -> List[GraphNode]:
        """按类型查找实体"""
        return [
            node for node in self.graph.nodes.values()
            if node.type == entity_type
        ]
    
    def find_related_entities(self, entity_name: str, max_depth: int = 2) -> List[Dict[str, Any]]:
        """查找相关实体"""
        node = self.graph.get_node_by_name(entity_name)
        if not node:
            return []
        
        related = []
        visited = {node.id}
        
        def traverse(current_id: str, depth: int, path: List[str]):
            if depth > max_depth:
                return
            
            for neighbor, edge in self.graph.get_neighbors(current_id):
                if neighbor.id not in visited:
                    visited.add(neighbor.id)
                    related.append({
                        'entity': neighbor.name,
                        'type': neighbor.type,
                        'relation': edge.relation,
                        'distance': depth,
                        'path': path + [neighbor.name]
                    })
                    traverse(neighbor.id, depth + 1, path + [neighbor.name])
        
        traverse(node.id, 1, [node.name])
        return related
    
    def find_shortest_path(self, entity1: str, entity2: str) -> Optional[List[str]]:
        """查找最短路径"""
        node1 = self.graph.get_node_by_name(entity1)
        node2 = self.graph.get_node_by_name(entity2)
        
        if not node1 or not node2:
            return None
        
        from collections import deque
        
        queue = deque([(node1.id, [node1.name])])
        visited = {node1.id}
        
        while queue:
            current_id, path = queue.popleft()
            
            if current_id == node2.id:
                return path
            
            for neighbor, edge in self.graph.get_neighbors(current_id):
                if neighbor.id not in visited:
                    visited.add(neighbor.id)
                    queue.append((neighbor.id, path + [neighbor.name]))
        
        return None
    
    def answer_relationship_query(self, entity1: str, entity2: str) -> Dict[str, Any]:
        """回答关系查询"""
        node1 = self.graph.get_node_by_name(entity1)
        node2 = self.graph.get_node_by_name(entity2)
        
        if not node1 or not node2:
            return {
                'found': False,
                'answer': f"未找到实体 '{entity1}' 或 '{entity2}'"
            }
        
        direct_edges = []
        for edge in self.graph.edges.values():
            if (edge.source == node1.id and edge.target == node2.id) or \
               (edge.source == node2.id and edge.target == node1.id):
                direct_edges.append(edge)
        
        if direct_edges:
            relations = [e.relation for e in direct_edges]
            return {
                'found': True,
                'type': 'direct',
                'answer': f"'{entity1}' 和 '{entity2}' 之间存在 {len(direct_edges)} 条直接关系：{', '.join(relations)}",
                'relations': direct_edges
            }
        
        paths = self.graph.find_path(node1.id, node2.id, max_depth=3)
        if paths:
            path_descriptions = []
            for path in paths[:3]:
                steps = []
                for i in range(0, len(path), 2):
                    if i + 1 < len(path):
                        steps.append(f"{path[i][0]} --[{path[i+1][1]}]--> {path[i+1][0]}")
                path_descriptions.append(" -> ".join(steps) if steps else "")
            
            return {
                'found': True,
                'type': 'indirect',
                'answer': f"'{entity1}' 和 '{entity2}' 之间存在间接关系路径",
                'paths': paths[:3],
                'path_descriptions': path_descriptions
            }
        
        return {
            'found': False,
            'answer': f"'{entity1}' 和 '{entity2}' 之间未发现关系"
        }
    
    def search_by_keyword(self, keyword: str) -> List[GraphNode]:
        """关键词搜索"""
        keyword_lower = keyword.lower()
        results = []
        
        for node in self.graph.nodes.values():
            if keyword_lower in node.name.lower():
                results.append(node)
            elif any(keyword_lower in str(v).lower() for v in node.properties.values()):
                results.append(node)
        
        return results
    
    def get_subgraph(self, center_entity: str, radius: int = 2) -> Dict[str, Any]:
        """获取子图"""
        center_node = self.graph.get_node_by_name(center_entity)
        if not center_node:
            return {'error': 'Entity not found'}
        
        nodes = {center_node}
        edges = []
        visited = {center_node.id}
        
        def expand(current_id: str, depth: int):
            if depth > radius:
                return
            
            for neighbor, edge in self.graph.get_neighbors(current_id):
                if neighbor.id not in visited:
                    visited.add(neighbor.id)
                    nodes.add(neighbor)
                    edges.append(edge)
                    expand(neighbor.id, depth + 1)
                else:
                    edge_obj = self.graph.edges.get(edge.id)
                    if edge_obj:
                        edges.append(edge_obj)
        
        expand(center_node.id, 1)
        
        return {
            'center': center_entity,
            'radius': radius,
            'nodes': [n.to_dict() for n in nodes],
            'edges': [e.to_dict() for e in edges],
            'stats': {
                'node_count': len(nodes),
                'edge_count': len(edges)
            }
        }
