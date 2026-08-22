#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
关系抽取模块 - 从文本中抽取实体关系
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

class RelationType(Enum):
    """关系类型枚举"""
    WORKS_AT = "WORKS_AT"
    LOCATED_IN = "LOCATED_IN"
    PART_OF = "PART_OF"
    CREATED_BY = "CREATED_BY"
    USES = "USES"
    RELATED_TO = "RELATED_TO"
    DEPENDS_ON = "DEPENDS_ON"
    IMPLEMENTS = "IMPLEMENTS"
    INHERITS_FROM = "INHERITS_FROM"
    CALLS = "CALLS"
    HAS_PROPERTY = "HAS_PROPERTY"
    SIMILAR_TO = "SIMILAR_TO"
    BEFORE = "BEFORE"
    AFTER = "AFTER"
    CAUSES = "CAUSES"
    OTHER = "OTHER"

@dataclass
class Relation:
    """关系"""
    subject: str
    relation_type: RelationType
    object: str
    confidence: float = 0.8
    context: str = ""
    source: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Triple:
    """三元组 - 主体-关系-客体"""
    head: str
    relation: str
    tail: str
    confidence: float = 1.0
    
    def to_string(self) -> str:
        """转换为字符串"""
        return f"({self.head}) - [{self.relation}] -> ({self.tail})"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'head': self.head,
            'relation': self.relation,
            'tail': self.tail,
            'confidence': self.confidence
        }


class RelationExtractor:
    """关系抽取器"""
    
    def __init__(self, ollama_url: str = "http://192.168.3.105:11434"):
        self.ollama_url = ollama_url
        self._init_patterns()
    
    def _init_patterns(self):
        """初始化关系模式"""
        self.relation_patterns = {
            RelationType.WORKS_AT: [
                (r'([^\s,，,]+)就职于|在\s*([^\s,，,]+)\s*(?:工作|任职)', 0.85),
                (r'([^\s,，,]+)加入了|是\s*([^\s,，,]+)\s*(?:的成员|员工)', 0.8),
            ],
            RelationType.LOCATED_IN: [
                (r'([^\s,，,]+)位于|坐落于\s*([^\s,，,]+)', 0.9),
                (r'([^\s,，,]+)在\s*([^\s,，,]+)', 0.7),
            ],
            RelationType.CREATED_BY: [
                (r'([^\s,，,]+)由\s*([^\s,，,]+)\s*创建', 0.9),
                (r'([^\s,，,]+)由\s*([^\s,，,]+)\s*开发', 0.85),
                (r'([^\s,，,]+)是\s*([^\s,，,]+)\s*(?:开发|创建|创建)', 0.8),
            ],
            RelationType.USES: [
                (r'([^\s,，,]+)使用\s*([^\s,，,]+)', 0.85),
                (r'([^\s,，,]+)采用\s*([^\s,，,]+)\s*技术', 0.8),
            ],
            RelationType.IMPLEMENTS: [
                (r'([^\s,，,]+)实现\s*([^\s,，,]+)', 0.9),
                (r'([^\s,，,]+)使用\s*([^\s,，,]+)\s*实现', 0.85),
            ],
            RelationType.DEPENDS_ON: [
                (r'([^\s,，,]+)依赖\s*([^\s,，,]+)', 0.85),
                (r'([^\s,，,]+)基于\s*([^\s,，,]+)', 0.8),
            ],
            RelationType.CALLS: [
                (r'([^\s,，,]+)调用\s*([^\s,，,]+)', 0.9),
                (r'([^\s,，,]+)引用\s*([^\s,，,]+)', 0.85),
            ],
        }
        
        self.relation_keywords = {
            RelationType.WORKS_AT: ['就职于', '任职于', '工作于', '加入', '是...的成员'],
            RelationType.LOCATED_IN: ['位于', '坐落于', '在...', '地处'],
            RelationType.CREATED_BY: ['创建', '开发', '设计', '构建'],
            RelationType.USES: ['使用', '采用', '运用', '基于'],
            RelationType.IMPLEMENTS: ['实现', '遵循', '基于...实现'],
            RelationType.DEPENDS_ON: ['依赖', '基于', '需要', '依据'],
            RelationType.CALLS: ['调用', '引用', '使用'],
        }
    
    def extract_by_rules(self, text: str) -> List[Relation]:
        """基于规则的关系抽取"""
        relations = []
        
        for relation_type, patterns in self.relation_patterns.items():
            for pattern, base_confidence in patterns:
                matches = re.finditer(pattern, text)
                for match in matches:
                    groups = match.groups()
                    groups = [g for g in groups if g]
                    
                    if len(groups) >= 2:
                        subject = groups[0].strip()
                        obj = groups[-1].strip()
                        
                        if len(subject) >= 1 and len(obj) >= 1:
                            relation = Relation(
                                subject=subject,
                                relation_type=relation_type,
                                object=obj,
                                confidence=base_confidence,
                                context=text[max(0, match.start()-50):match.end()+50],
                                source='rule'
                            )
                            relations.append(relation)
        
        return self._deduplicate_relations(relations)
    
    def _deduplicate_relations(self, relations: List[Relation]) -> List[Relation]:
        """去重关系"""
        seen = set()
        result = []
        
        for relation in relations:
            key = (relation.subject, relation.relation_type.value, relation.object)
            if key not in seen:
                seen.add(key)
                result.append(relation)
        
        return result
    
    async def extract_by_llm(self, text: str) -> List[Relation]:
        """基于 LLM 的关系抽取"""
        prompt = f"""请从以下文本中抽取实体关系三元组。

要求：
1. 只抽取明确的实体关系
2. 关系类型包括: {', '.join([r.value for r in RelationType])}
3. 返回 JSON 格式
4. 每个三元组包含：subject(主体), relation(关系), object(客体), confidence(置信度)

文本：
{text[:2000]}

输出格式：
[
  {{"subject": "主体", "relation": "关系类型", "object": "客体", "confidence": 0.9}},
  ...
]
"""
        
        try:
            import httpx
            async with httpx.AsyncClient(timeout=60) as client:
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
                
                return self._parse_llm_result(result, text)
        except Exception as e:
            print(f"LLM 关系抽取失败: {e}")
            return self.extract_by_rules(text)
    
    def _parse_llm_result(self, result: str, context: str) -> List[Relation]:
        """解析 LLM 关系抽取结果"""
        relations = []
        
        try:
            import json
            import re
            
            json_match = re.search(r'\[.*\]', result, re.DOTALL)
            if json_match:
                items = json.loads(json_match.group())
                
                for item in items:
                    try:
                        relation_type_str = item.get('relation', 'OTHER')
                        try:
                            relation_type = RelationType(relation_type_str)
                        except:
                            relation_type = RelationType.OTHER
                        
                        relation = Relation(
                            subject=item['subject'],
                            relation_type=relation_type,
                            object=item['object'],
                            confidence=item.get('confidence', 0.8),
                            context=context,
                            source='llm'
                        )
                        relations.append(relation)
                    except:
                        continue
        except:
            pass
        
        return relations
    
    async def extract(self, text: str, use_llm: bool = True) -> List[Relation]:
        """综合关系抽取"""
        if use_llm:
            llm_relations = await self.extract_by_llm(text)
            rule_relations = self.extract_by_rules(text)
            return self._merge_relations(llm_relations, rule_relations)
        else:
            return self.extract_by_rules(text)
    
    def _merge_relations(self, llm_relations: List[Relation], rule_relations: List[Relation]) -> List[Relation]:
        """合并 LLM 和规则抽取的关系"""
        seen = set()
        result = []
        
        for relation in llm_relations + rule_relations:
            key = (relation.subject, relation.relation_type.value, relation.object)
            if key not in seen:
                seen.add(key)
                result.append(relation)
        
        result.sort(key=lambda x: x.confidence, reverse=True)
        return result
    
    def extract_triples(self, relations: List[Relation]) -> List[Triple]:
        """将关系转换为三元组"""
        return [
            Triple(
                head=r.subject,
                relation=r.relation_type.value,
                tail=r.object,
                confidence=r.confidence
            )
            for r in relations
        ]
    
    def get_relation_summary(self, relations: List[Relation]) -> Dict[str, int]:
        """获取关系类型统计"""
        summary = {}
        for relation in relations:
            type_name = relation.relation_type.value
            summary[type_name] = summary.get(type_name, 0) + 1
        return summary


class CoReferenceResolver:
    """共指消解器 - 解决代词和同义词的指代问题"""
    
    def __init__(self):
        self.entity_aliases: Dict[str, Set[str]] = {}
        self.entity_representations: Dict[str, str] = {}
    
    def add_alias(self, entity: str, alias: str):
        """添加实体别名"""
        if entity not in self.entity_aliases:
            self.entity_aliases[entity] = set()
        self.entity_aliases[entity].add(alias)
    
    def resolve(self, text: str, entities: List) -> List[str]:
        """消解文本中的共指"""
        resolved = []
        
        for entity in entities:
            if entity.name in self.entity_aliases:
                resolved.append(self.entity_representations.get(entity.name, entity.name))
            else:
                resolved.append(entity.name)
        
        return resolved
    
    def link_aliases(self, entity1: str, entity2: str):
        """链接两个实体为同一实体"""
        if entity1 not in self.entity_aliases:
            self.entity_aliases[entity1] = set()
        if entity2 not in self.entity_aliases:
            self.entity_aliases[entity2] = set()
        
        self.entity_aliases[entity1].add(entity2)
        self.entity_aliases[entity2].add(entity1)
    
    def get_representation(self, entity: str) -> str:
        """获取实体的标准表示"""
        return self.entity_representations.get(entity, entity)
