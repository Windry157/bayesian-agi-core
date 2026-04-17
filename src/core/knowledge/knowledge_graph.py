#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识图谱模块
负责管理系统的知识表示和推理
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set, Any
import re

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class KnowledgeGraph:
    """知识图谱
    
    实现实体识别、关系提取、索引和嵌入策略
    """
    
    def __init__(self):
        """初始化知识图谱"""
        # 实体集合
        self.entities: Dict[str, Dict[str, Any]] = {}
        # 关系集合
        self.relations: List[Dict[str, Any]] = []
        # 实体索引（用于快速查找）
        self.entity_index: Dict[str, List[str]] = {}
        # 关系索引（用于快速查找）
        self.relation_index: Dict[str, List[Dict[str, Any]]] = {}
        # 实体嵌入（用于相似度计算）
        self.entity_embeddings: Dict[str, List[float]] = {}
        # 关系嵌入
        self.relation_embeddings: Dict[str, List[float]] = {}
        
        logger.info("知识图谱初始化完成")
    
    async def add_entity(self, entity_id: str, entity_type: str, properties: Dict[str, Any]):
        """添加实体
        
        Args:
            entity_id: 实体ID
            entity_type: 实体类型
            properties: 实体属性
        """
        if entity_id not in self.entities:
            self.entities[entity_id] = {
                "type": entity_type,
                "properties": properties,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # 更新实体索引
            self._update_entity_index(entity_id, entity_type, properties)
            
            # 生成实体嵌入
            await self._generate_entity_embedding(entity_id)
            
            logger.info(f"添加实体: {entity_id} (类型: {entity_type})")
        else:
            # 更新现有实体
            self.entities[entity_id].update({
                "properties": properties,
                "updated_at": datetime.now().isoformat()
            })
            # 更新索引
            self._update_entity_index(entity_id, entity_type, properties)
            # 更新嵌入
            await self._generate_entity_embedding(entity_id)
            
            logger.info(f"更新实体: {entity_id}")
    
    async def add_relation(self, subject: str, predicate: str, object_: str, properties: Dict[str, Any] = None):
        """添加关系
        
        Args:
            subject: 主体实体ID
            predicate: 关系类型
            object_: 客体实体ID
            properties: 关系属性
        """
        if subject in self.entities and object_ in self.entities:
            relation = {
                "subject": subject,
                "predicate": predicate,
                "object": object_,
                "properties": properties or {},
                "created_at": datetime.now().isoformat()
            }
            
            self.relations.append(relation)
            
            # 更新关系索引
            self._update_relation_index(relation)
            
            # 生成关系嵌入
            await self._generate_relation_embedding(predicate)
            
            logger.info(f"添加关系: {subject} -[{predicate}]-> {object_}")
        else:
            logger.error(f"无法添加关系，主体或客体实体不存在: {subject} -[{predicate}]-> {object_}")
    
    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """获取实体
        
        Args:
            entity_id: 实体ID
            
        Returns:
            实体信息
        """
        return self.entities.get(entity_id)
    
    def get_relations(self, subject: str = None, predicate: str = None, object_: str = None) -> List[Dict[str, Any]]:
        """获取关系
        
        Args:
            subject: 主体实体ID
            predicate: 关系类型
            object_: 客体实体ID
            
        Returns:
            关系列表
        """
        result = []
        
        for relation in self.relations:
            if subject and relation["subject"] != subject:
                continue
            if predicate and relation["predicate"] != predicate:
                continue
            if object_ and relation["object"] != object_:
                continue
            result.append(relation)
        
        return result
    
    async def search_entities(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """搜索实体
        
        Args:
            query: 搜索查询
            top_k: 返回前k个结果
            
        Returns:
            实体ID和相似度列表
        """
        # 生成查询嵌入
        query_embedding = await self._generate_text_embedding(query)
        
        # 计算相似度
        similarities = []
        for entity_id, embedding in self.entity_embeddings.items():
            similarity = self._calculate_similarity(query_embedding, embedding)
            similarities.append((entity_id, similarity))
        
        # 排序并返回前k个结果
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    async def extract_entities(self, text: str) -> List[Tuple[str, str]]:
        """从文本中提取实体
        
        Args:
            text: 输入文本
            
        Returns:
            实体名称和类型列表
        """
        # 简单的实体提取
        # 实际应用中可以使用更复杂的NLP模型
        entities = []
        
        # 提取人物
        person_patterns = [
            r"(先生|女士|博士|教授)\s+([\u4e00-\u9fa5]{2,4})",
            r"([\u4e00-\u9fa5]{2,4})\s+(先生|女士|博士|教授)"
        ]
        
        for pattern in person_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                if len(match.groups()) == 2:
                    if match.group(1) in ["先生", "女士", "博士", "教授"]:
                        entities.append((match.group(2), "person"))
                    else:
                        entities.append((match.group(1), "person"))
        
        # 提取地点
        location_patterns = [
            r"(在|到|来自|前往)\s+([\u4e00-\u9fa5]{2,6})"
        ]
        
        for pattern in location_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                if len(match.groups()) == 2:
                    entities.append((match.group(2), "location"))
        
        # 提取组织
        organization_patterns = [
            r"(公司|大学|医院|机构|组织)\s+([\u4e00-\u9fa5]{2,10})",
            r"([\u4e00-\u9fa5]{2,10})\s+(公司|大学|医院|机构|组织)"
        ]
        
        for pattern in organization_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                if len(match.groups()) == 2:
                    if match.group(1) in ["公司", "大学", "医院", "机构", "组织"]:
                        entities.append((match.group(2), "organization"))
                    else:
                        entities.append((match.group(1), "organization"))
        
        return entities
    
    async def extract_relations(self, text: str, entities: List[Tuple[str, str]]) -> List[Tuple[str, str, str]]:
        """从文本中提取关系
        
        Args:
            text: 输入文本
            entities: 实体列表
            
        Returns:
            主体-关系-客体三元组列表
        """
        relations = []
        entity_names = [entity[0] for entity in entities]
        
        # 简单的关系提取
        # 实际应用中可以使用更复杂的NLP模型
        for i, (subject, _) in enumerate(entities):
            for j, (object_, _) in enumerate(entities):
                if i != j and subject in text and object_ in text:
                    # 查找连接词
                    subject_idx = text.find(subject)
                    object_idx = text.find(object_)
                    
                    if subject_idx < object_idx:
                        between_text = text[subject_idx + len(subject):object_idx].strip()
                        
                        # 识别关系类型
                        if "是" in between_text:
                            relations.append((subject, "is", object_))
                        elif "在" in between_text:
                            relations.append((subject, "located_at", object_))
                        elif "属于" in between_text:
                            relations.append((subject, "belongs_to", object_))
                        elif "喜欢" in between_text:
                            relations.append((subject, "likes", object_))
                        elif "工作于" in between_text or "就职于" in between_text:
                            relations.append((subject, "works_at", object_))
        
        return relations
    
    def _update_entity_index(self, entity_id: str, entity_type: str, properties: Dict[str, Any]):
        """更新实体索引
        
        Args:
            entity_id: 实体ID
            entity_type: 实体类型
            properties: 实体属性
        """
        # 按类型索引
        if entity_type not in self.entity_index:
            self.entity_index[entity_type] = []
        if entity_id not in self.entity_index[entity_type]:
            self.entity_index[entity_type].append(entity_id)
        
        # 按属性索引
        for key, value in properties.items():
            index_key = f"{key}:{value}"
            if index_key not in self.entity_index:
                self.entity_index[index_key] = []
            if entity_id not in self.entity_index[index_key]:
                self.entity_index[index_key].append(entity_id)
    
    def _update_relation_index(self, relation: Dict[str, Any]):
        """更新关系索引
        
        Args:
            relation: 关系信息
        """
        predicate = relation["predicate"]
        if predicate not in self.relation_index:
            self.relation_index[predicate] = []
        self.relation_index[predicate].append(relation)
    
    async def _generate_entity_embedding(self, entity_id: str):
        """生成实体嵌入
        
        Args:
            entity_id: 实体ID
        """
        entity = self.entities.get(entity_id)
        if entity:
            # 简单的嵌入生成
            # 实际应用中可以使用更复杂的模型
            embedding = []
            # 基于实体类型和属性生成嵌入
            type_hash = hash(entity["type"]) % 100 / 100.0
            embedding.append(type_hash)
            
            # 基于属性生成嵌入
            prop_count = len(entity["properties"])
            embedding.append(prop_count / 10.0)
            
            # 填充到固定长度
            while len(embedding) < 10:
                embedding.append(0.0)
            
            self.entity_embeddings[entity_id] = embedding
    
    async def _generate_relation_embedding(self, predicate: str):
        """生成关系嵌入
        
        Args:
            predicate: 关系类型
        """
        if predicate not in self.relation_embeddings:
            # 简单的嵌入生成
            embedding = []
            # 基于关系类型生成嵌入
            pred_hash = hash(predicate) % 100 / 100.0
            embedding.append(pred_hash)
            
            # 填充到固定长度
            while len(embedding) < 10:
                embedding.append(0.0)
            
            self.relation_embeddings[predicate] = embedding
    
    async def _generate_text_embedding(self, text: str) -> List[float]:
        """生成文本嵌入
        
        Args:
            text: 输入文本
            
        Returns:
            嵌入向量
        """
        # 简单的文本嵌入生成
        embedding = []
        # 基于文本长度生成嵌入
        length = len(text)
        embedding.append(min(length / 100.0, 1.0))
        
        # 基于字符分布生成嵌入
        char_count = len(set(text))
        embedding.append(char_count / 50.0)
        
        # 填充到固定长度
        while len(embedding) < 10:
            embedding.append(0.0)
        
        return embedding
    
    def _calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """计算嵌入相似度
        
        Args:
            embedding1: 嵌入向量1
            embedding2: 嵌入向量2
            
        Returns:
            相似度得分
        """
        # 计算余弦相似度
        if len(embedding1) != len(embedding2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        norm1 = sum(a * a for a in embedding1) ** 0.5
        norm2 = sum(b * b for b in embedding2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def get_statistics(self) -> Dict[str, int]:
        """获取知识图谱统计信息
        
        Returns:
            统计信息
        """
        return {
            "entities_count": len(self.entities),
            "relations_count": len(self.relations),
            "entity_types_count": len(self.entity_index),
            "relation_types_count": len(self.relation_index)
        }
    
    def clear(self):
        """清空知识图谱"""
        self.entities = {}
        self.relations = []
        self.entity_index = {}
        self.relation_index = {}
        self.entity_embeddings = {}
        self.relation_embeddings = {}
        logger.info("知识图谱已清空")


# 全局知识图谱实例
knowledge_graph = KnowledgeGraph()
