#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实体抽取模块 - 从文本中抽取实体
支持规则抽取和基于LLM的抽取
"""

import re
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

class EntityType(Enum):
    """实体类型枚举"""
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    LOCATION = "LOCATION"
    TIME = "TIME"
    TECHNOLOGY = "TECHNOLOGY"
    PRODUCT = "PRODUCT"
    CONCEPT = "CONCEPT"
    EVENT = "EVENT"
    OTHER = "OTHER"

@dataclass
class Entity:
    """实体"""
    name: str
    type: EntityType
    start_pos: int
    end_pos: int
    confidence: float = 1.0
    aliases: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EntityMention:
    """实体提及"""
    text: str
    entity: Entity
    context: str = ""
    sentence: str = ""

MAX_TEXT_LENGTH = 5000


class EntityExtractor:
    """实体抽取器"""
    
    def __init__(self, use_llm: bool = False, ollama_url: str = "http://192.168.3.105:11434"):
        self.use_llm = use_llm
        self.ollama_url = ollama_url
        self._init_patterns()
    
    def _init_patterns(self):
        """初始化正则表达式模式"""
        self.patterns = {
            EntityType.PERSON: [
                r'(?:[A-Z][a-z]+ ){1,3}[A-Z][a-z]+',
                r'张[\u4e00-\u9fa5]{1,3}',
                r'王[\u4e00-\u9fa5]{1,3}',
                r'李[\u4e00-\u9fa5]{1,3}',
                r'刘[\u4e00-\u9fa5]{1,3}',
                r'陈[\u4e00-\u9fa5]{1,3}',
                r'杨[\u4e00-\u9fa5]{1,3}',
                r'黄[\u4e00-\u9fa5]{1,3}',
                r'赵[\u4e00-\u9fa5]{1,3}',
                r'周[\u4e00-\u9fa5]{1,3}',
            ],
            EntityType.ORGANIZATION: [
                r'[A-Z][a-zA-Z]*(?:公司|集团|企业|机构|组织)',
                r'[\u4e00-\u9fa5]+(?:公司|集团|企业|机构|组织|银行|医院|学校)',
                r'[A-Z][a-zA-Z]+(?:Inc|Ltd|Corp|Co)',
            ],
            EntityType.LOCATION: [
                r'[\u4e00-\u9fa5]+(?:市|省|县|区|镇|村|街|路|道)',
                r'[\u4e00-\u9fa5]+(?:国|州|省)',
                r'(?:北京|上海|深圳|广州|杭州|成都|武汉|西安|南京|重庆)',
            ],
            EntityType.TIME: [
                r'\d{4}年\d{1,2}月\d{1,2}日',
                r'\d{4}年\d{1,2}月',
                r'\d{4}年',
                r'\d+天前',
                r'\d+小时前',
                r'(?:昨天|今天|明天|上周|下周|上个月|下个月)',
            ],
            EntityType.TECHNOLOGY: [
                r'[A-Za-z]+(?:Net|AI|ML|LLM|NLP|CV|CNN|RNN|GAN|API|SDK)',
                r'[\u4e00-\u9fa5]+(?:技术|算法|模型|框架|平台|系统)',
            ],
            EntityType.PRODUCT: [
                r'[\u4e00-\u9fa5]+(?:产品|软件|工具|系统|应用)',
                r'[A-Z][a-zA-Z]+(?:Pro|Max|Plus)',
            ],
        }
        
        self.stopwords = {'的', '是', '在', '和', '与', '或', '以及', '等', '了', '着', '过'}
    
    def extract_by_rules(self, text: str) -> List[Entity]:
        """基于规则的实体抽取"""
        if len(text) > MAX_TEXT_LENGTH:
            return self._extract_chunked(text)

        entities = []
        
        for entity_type, patterns in self.patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text):
                    entity_text = match.group()
                    if len(entity_text) >= 2 and entity_text not in self.stopwords:
                        entity = Entity(
                            name=entity_text,
                            type=entity_type,
                            start_pos=match.start(),
                            end_pos=match.end(),
                            confidence=0.8
                        )
                        entities.append(entity)
        
        entities = self._deduplicate_entities(entities)
        return entities

    def _extract_chunked(self, text: str) -> List[Entity]:
        all_entities = []
        chunk_size = MAX_TEXT_LENGTH
        overlap = 100
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk = text[start:end]
            for entity_type, patterns in self.patterns.items():
                for pattern in patterns:
                    for match in re.finditer(pattern, chunk):
                        entity_text = match.group()
                        if len(entity_text) >= 2 and entity_text not in self.stopwords:
                            entity = Entity(
                                name=entity_text, type=entity_type,
                                start_pos=match.start() + start,
                                end_pos=match.end() + start,
                                confidence=0.8
                            )
                            all_entities.append(entity)
            start = end - overlap if end < len(text) else end
        return self._deduplicate_entities(all_entities)

    def _deduplicate_entities(self, entities: List[Entity]) -> List[Entity]:
        """去重实体"""
        seen = {}
        result = []
        
        for entity in entities:
            key = (entity.name, entity.type)
            if key not in seen:
                seen[key] = entity
                result.append(entity)
            else:
                existing = seen[key]
                if entity.confidence > existing.confidence:
                    seen[key] = entity
                    result[result.index(existing)] = entity
        
        return result
    
    async def extract_by_llm(self, text: str, entity_types: Optional[List[EntityType]] = None) -> List[Entity]:
        """基于 LLM 的实体抽取"""
        if not self.use_llm:
            return self.extract_by_rules(text)
        
        type_names = [et.value for et in (entity_types or list(EntityType))]
        type_list = ', '.join(type_names)
        
        prompt = f"""请从以下文本中抽取实体。

要求：
1. 只抽取{type_list}类型的实体
2. 返回 JSON 格式的实体列表
3. 每个实体包含：name(名称), type(类型), confidence(置信度0-1)

文本：
{text[:2000]}

输出格式：
[
  {{"name": "实体名称", "type": "实体类型", "confidence": 0.9}},
  ...
]
"""
        
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/chat",
                    json={
                        "model": "llama3.1:8b",
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False
                    }
                )
                response.raise_for_status()
                data = response.json()
                result = data.get("message", {}).get("content", "")
                
                return self._parse_llm_result(result)
        except Exception as e:
            print(f"LLM 实体抽取失败: {e}")
            return self.extract_by_rules(text)
    
    def _parse_llm_result(self, result: str) -> List[Entity]:
        """解析 LLM 实体抽取结果"""
        entities = []
        
        try:
            import json
            import re
            
            json_match = re.search(r'\[.*\]', result, re.DOTALL)
            if json_match:
                items = json.loads(json_match.group())
                
                for item in items:
                    try:
                        entity_type = EntityType(item.get('type', 'OTHER'))
                        entity = Entity(
                            name=item['name'],
                            type=entity_type,
                            start_pos=0,
                            end_pos=0,
                            confidence=item.get('confidence', 0.8)
                        )
                        entities.append(entity)
                    except:
                        continue
        except:
            pass
        
        return entities
    
    async def extract(self, text: str, use_llm: bool = False) -> List[Entity]:
        """综合实体抽取"""
        if use_llm and self.use_llm:
            return await self.extract_by_llm(text)
        else:
            return self.extract_by_rules(text)
    
    def extract_from_sentences(self, sentences: List[str]) -> List[Entity]:
        """从多个句子中抽取实体"""
        all_entities = []
        
        for sentence in sentences:
            entities = self.extract_by_rules(sentence)
            all_entities.extend(entities)
        
        return self._deduplicate_entities(all_entities)
    
    def get_entity_types_summary(self, entities: List[Entity]) -> Dict[str, int]:
        """获取实体类型统计"""
        summary = {}
        for entity in entities:
            type_name = entity.type.value
            summary[type_name] = summary.get(type_name, 0) + 1
        return summary


class SimpleEntityLinker:
    """简单实体链接器 - 将实体链接到知识库"""
    
    def __init__(self):
        self.entity_cache: Dict[str, Dict[str, Any]] = {}
    
    def add_entity(self, entity: Entity, knowledge_id: str, properties: Optional[Dict[str, Any]] = None):
        """添加实体到知识库"""
        key = f"{entity.name}_{entity.type.value}"
        self.entity_cache[key] = {
            'entity': entity,
            'knowledge_id': knowledge_id,
            'properties': properties or {},
            'linked_count': 0
        }
    
    def link_entity(self, entity: Entity) -> Optional[Dict[str, Any]]:
        """链接实体到知识库"""
        key = f"{entity.name}_{entity.type.value}"
        
        if key in self.entity_cache:
            self.entity_cache[key]['linked_count'] += 1
            return self.entity_cache[key]
        
        return None
    
    def get_entity_info(self, name: str, entity_type: EntityType) -> Optional[Dict[str, Any]]:
        """获取实体信息"""
        key = f"{name}_{entity_type.value}"
        return self.entity_cache.get(key)
    
    def get_related_entities(self, entity: Entity) -> List[Dict[str, Any]]:
        """获取相关实体"""
        related = []
        
        for key, data in self.entity_cache.items():
            if key != f"{entity.name}_{entity.type.value}":
                related.append({
                    'entity': data['entity'],
                    'knowledge_id': data['knowledge_id'],
                    'properties': data['properties']
                })
        
        return related[:10]
