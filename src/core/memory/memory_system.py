#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记忆系统
负责管理智能体的记忆

优化版本: Phase 5
- Phase 1: 内存缓冲写入，批量刷新到磁盘
- Phase 1: 批量添加方法 add_batch()
- Phase 1: 手动刷新方法 flush()
- Phase 2: MessagePack 高效存储格式
- Phase 3: 真正异步IO优化 (aiofiles)
- Phase 4: 向量索引集成 (ChromaDB)，支持语义检索
- Phase 5: 知识图谱集成 (实体抽取 + 关系推理)
"""

import json
import logging
import asyncio
import os
import re
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 尝试导入 msgpack，如果不可用则回退到 JSON
try:
    import msgpack
    HAS_MSGPACK = True
    logger.info("MessagePack 已加载，将使用高效二进制存储")
except ImportError:
    HAS_MSGPACK = False
    logger.warning("MessagePack 未安装，将使用 JSON 作为后备存储")

# 尝试导入 aiofiles，实现真正的异步IO
try:
    import aiofiles
    HAS_AIOFILES = True
    logger.info("aiofiles 已加载，将使用异步文件IO")
except ImportError:
    HAS_AIOFILES = False
    logger.warning("aiofiles 未安装，将使用同步文件IO")

# 尝试导入向量索引
try:
    from .vector_index import VectorIndex
    HAS_VECTOR_INDEX = True
    logger.info("向量索引模块已加载，将支持语义检索")
except ImportError:
    HAS_VECTOR_INDEX = False
    logger.warning("向量索引模块未加载，将使用简单文本匹配")

# 尝试导入实体抽取器
try:
    from .entity_extractor import EntityExtractor, entity_extractor
    HAS_ENTITY_EXTRACTOR = True
    logger.info("实体抽取模块已加载，将支持实体识别")
except ImportError:
    HAS_ENTITY_EXTRACTOR = False
    logger.warning("实体抽取模块未加载")

# 尝试导入知识图谱
try:
    from .knowledge_graph import KnowledgeGraph, knowledge_graph
    HAS_KNOWLEDGE_GRAPH = True
    logger.info("知识图谱模块已加载，将支持关系推理")
except ImportError:
    HAS_KNOWLEDGE_GRAPH = False
    logger.warning("知识图谱模块未加载")


def _tokenize_to_keywords(text: str) -> Set[str]:
    tokens = set(re.findall(r'\w+', text.lower()))
    return {t for t in tokens if len(t) >= 3}


class MemorySystem:
    """记忆系统
    
    管理智能体的记忆，包括短期记忆和长期记忆
    
    优化特性:
    - Phase 1: 内存缓冲写入，批量刷新到磁盘
    - Phase 1: 批量添加方法 add_batch()
    - Phase 1: 手动刷新方法 flush()
    - Phase 2: MessagePack 高效存储 (可选，JSON 后备)
    - Phase 3: 真正异步IO优化 (aiofiles)
    - Phase 4: 向量索引集成 (ChromaDB)，支持语义检索
    - Phase 5: 知识图谱集成 (实体抽取 + 关系推理)
    """
    
    def __init__(self, memory_dir: str = "memory", vector_model: str = "ollama:nomic-embed-text", ollama_url: str = "http://localhost:11434", buffer_size: int = 50, use_msgpack: bool = True, use_vector_index: bool = True, use_knowledge_graph: bool = True):
        """初始化记忆系统
        
        Args:
            memory_dir: 记忆存储目录
            vector_model: 向量模型
            ollama_url: Ollama服务地址
            buffer_size: 写入缓冲区大小（默认50）
            use_msgpack: 是否使用MessagePack（默认True）
            use_vector_index: 是否使用向量索引（默认True）
            use_knowledge_graph: 是否使用知识图谱（默认True）
        """
        self.memory_dir = memory_dir
        self.vector_model = vector_model
        self.ollama_url = ollama_url
        self.buffer_size = buffer_size
        self.use_msgpack = use_msgpack and HAS_MSGPACK
        self.use_vector_index = use_vector_index and HAS_VECTOR_INDEX
        self.use_knowledge_graph = use_knowledge_graph and HAS_KNOWLEDGE_GRAPH
        
        # 确保持久化目录存在
        os.makedirs(self.memory_dir, exist_ok=True)
        
        # 内存缓存
        self.memory_cache = {}
        
        # 倒排关键词索引（Phase 6优化）
        self.keyword_index: Dict[str, Set[str]] = {}
        
        # 写入缓冲区（Phase 1优化）
        self._dirty = False
        
        # 存储文件路径
        self._memory_file_json = os.path.join(self.memory_dir, "memories.json")
        self._memory_file_msgpack = os.path.join(self.memory_dir, "memories.msgpack")
        
        # 向量索引（Phase 4优化）
        self.vector_index = None
        if self.use_vector_index:
            vector_db_dir = os.path.join(self.memory_dir, "vector_db")
            self.vector_index = VectorIndex(persist_dir=vector_db_dir)
        
        # 知识图谱（Phase 5优化）
        self.knowledge_graph = None
        if self.use_knowledge_graph:
            kg_dir = os.path.join(self.memory_dir, "knowledge_graph")
            self.knowledge_graph = KnowledgeGraph(persist_dir=kg_dir)
        
        logger.info(f"记忆系统初始化完成 (Phase 6 优化已启用, MessagePack={'已' if self.use_msgpack else '未'}使用, AsyncIO={'已' if HAS_AIOFILES else '未'}使用, VectorIndex={'已' if self.use_vector_index else '未'}使用, KnowledgeGraph={'已' if self.use_knowledge_graph else '未'}使用)")
    
    def _rebuild_keyword_index(self):
        self.keyword_index = {}
        for memory_id, memory in self.memory_cache.items():
            for kw in _tokenize_to_keywords(memory["content"]):
                self.keyword_index.setdefault(kw, set()).add(memory_id)
    
    async def load(self):
        """加载记忆 (Phase 2优化: 支持MessagePack和JSON)"""
        try:
            # 尝试从 MessagePack 加载
            if self.use_msgpack and os.path.exists(self._memory_file_msgpack):
                await self._load_from_disk_msgpack()
            # 否则从 JSON 加载
            elif os.path.exists(self._memory_file_json):
                await self._load_from_disk_json()
            else:
                logger.info("未找到现有记忆文件，将创建新的记忆存储")
        except Exception as e:
            logger.error(f"加载记忆失败: {e}")
        self._rebuild_keyword_index()
    
    async def add_memory(self, content: str, metadata: Optional[Dict[str, Any]] = None, importance: float = 1.0) -> str:
        """添加记忆
        
        Args:
            content: 记忆内容
            metadata: 记忆元数据
            importance: 初始重要性权重 (0.1-5.0, 默认1.0)
            
        Returns:
            记忆ID
        """
        try:
            memory_id = f"mem_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            
            memory = {
                "id": memory_id,
                "content": content,
                "metadata": metadata or {},
                "created_at": datetime.now().isoformat(),
                "last_accessed": datetime.now().isoformat(),
                "access_count": 1,
                "importance": max(0.1, min(5.0, importance)),  # 基础重要性权重
                "decay_rate": 0.95  # 时间衰减率 (每天)
            }
            
            self.memory_cache[memory_id] = memory
            
            for kw in _tokenize_to_keywords(content):
                self.keyword_index.setdefault(kw, set()).add(memory_id)
            
            self._dirty = True
            
            if len(self.memory_cache) % self.buffer_size == 0:
                await self._save_to_disk()
            
            # Phase 4优化: 同步更新向量索引
            if self.use_vector_index and self.vector_index:
                await self.vector_index.add_documents(
                    documents=[content],
                    ids=[memory_id],
                    metadatas=[metadata]
                )
            
            # Phase 5优化: 实体抽取和知识图谱构建
            entities = []
            if self.use_knowledge_graph and self.knowledge_graph:
                entities = self._extract_and_index_entities(memory_id, content)
            
            logger.info(f"添加记忆成功: {memory_id}, 重要性: {importance}, 抽取实体数: {len(entities)}")
            return memory_id
            
        except Exception as e:
            logger.error(f"添加记忆失败: {e}")
            raise
    
    async def add_batch(self, contents: List[str], metadata_list: Optional[List[Optional[Dict[str, Any]]]] = None) -> List[str]:
        """批量添加记忆 (Phase 1优化新增)
        
        Args:
            contents: 记忆内容列表
            metadata_list: 元数据列表（可选，与内容一一对应）
            
        Returns:
            记忆ID列表
        """
        try:
            memory_ids = []
            metadatas = []
            
            for idx, content in enumerate(contents):
                memory_id = f"mem_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{idx}"
                
                metadata = None
                if metadata_list and idx < len(metadata_list):
                    metadata = metadata_list[idx]
                
                memory = {
                    "id": memory_id,
                    "content": content,
                    "metadata": metadata or {},
                    "created_at": datetime.now().isoformat(),
                    "last_accessed": datetime.now().isoformat(),
                    "access_count": 1
                }
                
                self.memory_cache[memory_id] = memory
                memory_ids.append(memory_id)
                metadatas.append(metadata)
                for kw in _tokenize_to_keywords(content):
                    self.keyword_index.setdefault(kw, set()).add(memory_id)
            
            self._dirty = True
            await self._save_to_disk()
            
            # Phase 4优化: 批量更新向量索引
            if self.use_vector_index and self.vector_index:
                await self.vector_index.add_documents(
                    documents=contents,
                    ids=memory_ids,
                    metadatas=metadatas if metadata_list else None
                )
            
            logger.info(f"批量添加记忆成功: {len(memory_ids)} 条")
            return memory_ids
            
        except Exception as e:
            logger.error(f"批量添加记忆失败: {e}")
            raise
    
    async def flush(self) -> None:
        """手动刷新缓冲区，确保所有数据写入磁盘 (Phase 1优化新增)
        
        """
        if self._dirty:
            await self._save_to_disk()
            logger.info("缓冲区已刷新到磁盘")
    
    async def retrieve_memories(self, query: str, top_k: int = 5, use_semantic: bool = True) -> List[Dict[str, Any]]:
        """检索记忆
        
        Args:
            query: 查询内容
            top_k: 返回的记忆数量
            use_semantic: 是否使用语义检索（向量索引）
            
        Returns:
            检索到的记忆列表
        """
        try:
            # Phase 4优化: 优先使用向量索引进行语义检索
            if use_semantic and self.use_vector_index and self.vector_index:
                return await self._retrieve_semantic(query, top_k)
            
            # 回退到简单文本匹配
            return await self._retrieve_text_match(query, top_k)
            
        except Exception as e:
            logger.error(f"检索记忆失败: {e}")
            return []
    
    async def _retrieve_semantic(self, query: str, top_k: int = 5, score_threshold: float = 0.2, use_weight: bool = True) -> List[Dict[str, Any]]:
        """使用向量索引进行语义检索 (Phase 4优化 + 权重排序)
        
        Args:
            query: 查询文本
            top_k: 返回数量
            score_threshold: 相似度阈值
            use_weight: 是否使用权重排序
            
        Returns:
            匹配结果列表（按综合分数排序）
        """
        logger.info(f"开始语义检索: 查询='{query}', top_k={top_k}, 阈值={score_threshold}, 权重排序={use_weight}")
        
        results = await self.vector_index.query(query, top_k * 2, score_threshold=score_threshold)  # 获取双倍结果用于权重排序
        
        # 更新访问信息并计算综合分数
        enhanced_results = []
        for result in results:
            memory_id = result['id']
            semantic_score = result.get('score', 0.0)
            
            # 获取记忆详情（如果存在）
            memory = self.memory_cache.get(memory_id)
            
            if memory:
                memory["last_accessed"] = datetime.now().isoformat()
                memory["access_count"] += 1
                
                result['last_accessed'] = memory["last_accessed"]
                result['access_count'] = memory["access_count"]
                result['importance'] = memory.get("importance", 1.0)
                
                # 计算综合分数 = 语义相似度 × 记忆权重
                if use_weight:
                    weight = self._calculate_weight(memory)
                    result['weight'] = weight
                    result['combined_score'] = semantic_score * weight
                else:
                    result['weight'] = 1.0
                    result['combined_score'] = semantic_score
            else:
                result['weight'] = 1.0
                result['combined_score'] = semantic_score
            
            enhanced_results.append(result)
        
        # 按综合分数排序
        enhanced_results.sort(key=lambda x: x.get('combined_score', 0.0), reverse=True)
        
        # 限制返回数量
        final_results = enhanced_results[:top_k]
        
        # 记录详细日志
        for idx, result in enumerate(final_results):
            content_preview = result['content'][:50] + "..." if len(result['content']) > 50 else result['content']
            logger.info(f"语义检索匹配 [{idx+1}/{len(final_results)}]: id={result['id'][:12]}..., 语义分数={result.get('score', 0.0):.4f}, 权重={result.get('weight', 1.0):.4f}, 综合分数={result.get('combined_score', 0.0):.4f}, 内容预览='{content_preview}'")
        
        # 记录检索统计
        if final_results:
            scores = [r.get('combined_score', 0.0) for r in final_results]
            avg_score = sum(scores) / len(scores)
            max_score = max(scores)
            min_score = min(scores)
            logger.info(f"语义检索统计: 总匹配={len(final_results)}, 平均综合分数={avg_score:.4f}, 最高={max_score:.4f}, 最低={min_score:.4f}")
        else:
            logger.info("语义检索完成: 未找到匹配结果")
        
        return final_results
    
    async def _retrieve_text_match(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """使用关键词索引进行文本匹配检索（Phase 6优化）"""
        query_keywords = _tokenize_to_keywords(query)
        if not query_keywords:
            return []
        
        candidate_ids: Optional[Set[str]] = None
        for kw in query_keywords:
            ids = self.keyword_index.get(kw, set())
            if not ids:
                return []
            if candidate_ids is None:
                candidate_ids = set(ids)
            else:
                candidate_ids &= ids
            if not candidate_ids:
                break
        
        if candidate_ids is None:
            candidate_ids = set(self.memory_cache.keys())
        
        results = []
        for memory_id in candidate_ids:
            memory = self.memory_cache.get(memory_id)
            if memory is None:
                continue
            if query.lower() in memory["content"].lower():
                memory["last_accessed"] = datetime.now().isoformat()
                memory["access_count"] += 1
                
                results.append({
                    "id": memory["id"],
                    "content": memory["content"],
                    "metadata": memory["metadata"],
                    "score": 0.9,
                    "last_accessed": memory["last_accessed"],
                    "access_count": memory["access_count"]
                })
        
        results.sort(key=lambda x: x.get("access_count", 0), reverse=True)
        results = results[:top_k]
        
        logger.info(f"文本匹配检索完成: {len(results)} 条匹配 (关键词候选: {len(candidate_ids)})")
        return results
    
    def _calculate_weight(self, memory: Dict[str, Any]) -> float:
        """计算记忆的综合权重（考虑时间衰减和访问增强）
        
        权重计算公式:
            weight = importance × decay_factor × access_boost
        
        Args:
            memory: 记忆对象
            
        Returns:
            综合权重值
        """
        try:
            # 获取基础重要性
            importance = memory.get("importance", 1.0)
            
            # 计算时间衰减因子
            created_at = datetime.fromisoformat(memory.get("created_at", datetime.now().isoformat()))
            now = datetime.now()
            days_since_creation = (now - created_at).days
            
            decay_rate = memory.get("decay_rate", 0.95)
            decay_factor = decay_rate ** days_since_creation
            
            # 计算访问增强因子 (访问次数越多，权重越高)
            access_count = memory.get("access_count", 1)
            access_boost = 1.0 + (access_count - 1) * 0.1  # 每次访问增加10%
            
            # 综合权重
            weight = importance * decay_factor * access_boost
            
            logger.debug(f"权重计算: id={memory['id'][:10]}..., importance={importance:.3f}, decay={decay_factor:.3f}, boost={access_boost:.3f}, weight={weight:.3f}")
            
            return weight
        except Exception as e:
            logger.error(f"计算权重失败: {e}")
            return 1.0
    
    def _apply_time_decay(self):
        """对所有记忆应用时间衰减（定期调用）"""
        try:
            for memory_id, memory in self.memory_cache.items():
                # 重新计算权重（隐式应用时间衰减）
                weight = self._calculate_weight(memory)
                # 可以选择直接更新记忆的有效权重
                memory["_current_weight"] = weight
            
            logger.info(f"时间衰减已应用，共 {len(self.memory_cache)} 条记忆")
        except Exception as e:
            logger.error(f"应用时间衰减失败: {e}")
    
    async def set_importance(self, memory_id: str, importance: float):
        """设置记忆的重要性权重
        
        Args:
            memory_id: 记忆ID
            importance: 重要性权重 (0.1-5.0)
        """
        if memory_id in self.memory_cache:
            self.memory_cache[memory_id]["importance"] = max(0.1, min(5.0, importance))
            self._dirty = True
            await self._save_to_disk()
            logger.info(f"设置记忆重要性成功: {memory_id}, importance={importance}")
        else:
            logger.warning(f"记忆不存在: {memory_id}")
    
    async def prune_low_weight_memories(self, min_weight: float = 0.1):
        """清理低权重记忆（遗忘机制）
        
        Args:
            min_weight: 最小权重阈值，低于此值的记忆将被删除
        """
        try:
            to_delete = []
            for memory_id, memory in self.memory_cache.items():
                weight = self._calculate_weight(memory)
                if weight < min_weight:
                    to_delete.append(memory_id)
            
            if to_delete:
                for memory_id in to_delete:
                    # 从向量索引中删除
                    if self.use_vector_index and self.vector_index:
                        await self.vector_index.delete([memory_id])
                    # 从缓存中删除
                    del self.memory_cache[memory_id]
                
                self._dirty = True
                await self._save_to_disk()
                logger.info(f"清理低权重记忆: 删除 {len(to_delete)} 条")
            else:
                logger.info("没有需要清理的低权重记忆")
        except Exception as e:
            logger.error(f"清理低权重记忆失败: {e}")
    
    async def get_memory_weight(self, memory_id: str) -> float:
        """获取记忆的当前权重
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            当前权重值
        """
        if memory_id in self.memory_cache:
            return self._calculate_weight(self.memory_cache[memory_id])
        return 0.0
    
    # ========== 知识图谱相关方法 (Phase 5优化) ==========
    
    def _extract_and_index_entities(self, memory_id: str, content: str) -> List[Dict[str, Any]]:
        """从记忆内容中抽取实体并添加到知识图谱
        
        Args:
            memory_id: 记忆ID
            content: 记忆内容
            
        Returns:
            抽取的实体列表
        """
        entities = []
        
        if not HAS_ENTITY_EXTRACTOR or not entity_extractor:
            return entities
        
        try:
            entities = entity_extractor.extract_entities(content)
            
            if entities and self.knowledge_graph:
                # 添加实体到知识图谱
                for ent in entities:
                    entity_id = f"ent_{uuid.uuid4().hex[:8]}"
                    ent["entity_id"] = entity_id
                    
                    # 添加实体节点
                    self.knowledge_graph.add_entity(
                        entity_id=entity_id,
                        entity_type=ent.get("type", "CONCEPT"),
                        name=ent.get("text", ""),
                        attributes={
                            "source_memory": memory_id,
                            "start": ent.get("start"),
                            "end": ent.get("end"),
                            "extractor": ent.get("source", "unknown")
                        }
                    )
                
                # 在同一记忆中的实体之间建立"相关于"关系
                for i, ent1 in enumerate(entities):
                    for j, ent2 in enumerate(entities):
                        if i < j:
                            self.knowledge_graph.add_relation(
                                source_id=ent1["entity_id"],
                                target_id=ent2["entity_id"],
                                relation_type="相关于",
                                attributes={"memory_id": memory_id}
                            )
            
            logger.info(f"实体抽取完成: {memory_id} -> {len(entities)} 个实体")
        except Exception as e:
            logger.error(f"实体抽取失败: {e}")
        
        return entities
    
    async def infer_knowledge(self, query: str) -> List[Dict[str, Any]]:
        """基于知识图谱进行关系推理
        
        Args:
            query: 查询文本
            
        Returns:
            推理结果列表
        """
        results = []
        
        if not self.use_knowledge_graph or not self.knowledge_graph:
            return results
        
        try:
            # 先抽取查询中的实体
            query_entities = []
            if HAS_ENTITY_EXTRACTOR and entity_extractor:
                query_entities = entity_extractor.extract_entities(query)
            
            # 对每个查询实体进行推理
            for ent in query_entities:
                # 查找知识图谱中相关的实体
                # 这里简化处理，实际可以更复杂
                inferences = self.knowledge_graph.infer_relations(ent.get("text", ""))
                results.extend(inferences)
            
            logger.info(f"知识推理完成: 查询'{query}' -> {len(results)} 个推理结果")
        except Exception as e:
            logger.error(f"知识推理失败: {e}")
        
        return results
    
    async def get_entity_relations(self, entity_name: str) -> List[Dict[str, Any]]:
        """获取实体的关系
        
        Args:
            entity_name: 实体名称
            
        Returns:
            关系列表
        """
        if not self.use_knowledge_graph or not self.knowledge_graph:
            return []
        
        try:
            relations = []
            
            # 使用知识图谱的内置方法获取关系
            # 遍历所有节点查找匹配的实体
            if hasattr(self.knowledge_graph.graph, 'nodes') and callable(getattr(self.knowledge_graph.graph, 'nodes', None)):
                # NetworkX 格式
                for node_id, data in self.knowledge_graph.graph.nodes(data=True):
                    if entity_name in str(data.get("name", "")):
                        node_relations = self.knowledge_graph.get_relations(node_id)
                        relations.extend(node_relations)
            elif isinstance(self.knowledge_graph.graph, dict) and "nodes" in self.knowledge_graph.graph:
                # 字典格式
                for node_id, data in self.knowledge_graph.graph["nodes"].items():
                    if entity_name in str(data.get("name", "")):
                        for edge in self.knowledge_graph.graph["edges"]:
                            if edge["source"] == node_id or edge["target"] == node_id:
                                relations.append(edge)
            
            logger.info(f"获取实体关系: '{entity_name}' -> {len(relations)} 条关系")
            return relations
        except Exception as e:
            logger.error(f"获取实体关系失败: {e}")
            return []
    
    async def save_knowledge_graph(self):
        """保存知识图谱"""
        if self.use_knowledge_graph and self.knowledge_graph:
            self.knowledge_graph.save_graph()
    
    # ========== 知识图谱相关方法结束 ==========
    
    async def _load_from_disk_json(self):
        """从磁盘加载记忆 (JSON 格式) (Phase 3优化: 异步IO)"""
        try:
            if HAS_AIOFILES:
                async with aiofiles.open(self._memory_file_json, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    self.memory_cache = json.loads(content)
            else:
                with open(self._memory_file_json, 'r', encoding='utf-8') as f:
                    self.memory_cache = json.load(f)
            logger.info(f"从磁盘加载记忆 (JSON): {len(self.memory_cache)} 条")
        except Exception as e:
            logger.error(f"从磁盘加载记忆失败 (JSON): {e}")
            self.memory_cache = {}
    
    async def _load_from_disk_msgpack(self):
        """从磁盘加载记忆 (MessagePack 格式) (Phase 3优化: 异步IO)"""
        try:
            if HAS_AIOFILES:
                async with aiofiles.open(self._memory_file_msgpack, 'rb') as f:
                    content = await f.read()
                    self.memory_cache = msgpack.unpackb(content)
            else:
                with open(self._memory_file_msgpack, 'rb') as f:
                    self.memory_cache = msgpack.unpack(f)
            logger.info(f"从磁盘加载记忆 (MessagePack): {len(self.memory_cache)} 条")
        except Exception as e:
            logger.error(f"从磁盘加载记忆失败 (MessagePack): {e}")
            # 尝试回退到 JSON
            if os.path.exists(self._memory_file_json):
                logger.info("回退到 JSON 格式加载")
                await self._load_from_disk_json()
            else:
                self.memory_cache = {}
    
    async def _save_to_disk(self):
        """保存记忆到磁盘 (Phase 3优化: 优先使用MessagePack，真正异步IO)"""
        if not self._dirty:
            return
            
        try:
            if self.use_msgpack:
                await self._save_to_disk_msgpack()
            else:
                await self._save_to_disk_json()
            self._dirty = False
            logger.info(f"保存记忆到磁盘: {len(self.memory_cache)} 条")
        except Exception as e:
            logger.error(f"保存记忆到磁盘失败: {e}")
    
    async def _save_to_disk_json(self):
        """保存记忆到磁盘 (JSON 格式) (Phase 3优化: 异步IO)"""
        content = json.dumps(self.memory_cache, ensure_ascii=False, indent=2)
        if HAS_AIOFILES:
            async with aiofiles.open(self._memory_file_json, 'w', encoding='utf-8') as f:
                await f.write(content)
        else:
            with open(self._memory_file_json, 'w', encoding='utf-8') as f:
                f.write(content)
    
    async def _save_to_disk_msgpack(self):
        """保存记忆到磁盘 (MessagePack 格式) (Phase 3优化: 异步IO)"""
        content = msgpack.packb(self.memory_cache)
        if HAS_AIOFILES:
            async with aiofiles.open(self._memory_file_msgpack, 'wb') as f:
                await f.write(content)
        else:
            with open(self._memory_file_msgpack, 'wb') as f:
                f.write(content)
        
        # 可选：保留 JSON 作为备份
        # 这里不保存 JSON 以获得最大性能
    
    def get_memory_count(self) -> int:
        """获取记忆数量
        
        Returns:
            记忆数量
        """
        return len(self.memory_cache)
    
    async def clear_memory(self):
        """清除所有记忆 (Phase 1优化: 立即刷新确保清理可见)"""
        self.memory_cache.clear()
        self._dirty = True
        await self._save_to_disk()
        
        # Phase 4优化: 同步清空向量索引
        if self.use_vector_index and self.vector_index:
            self.vector_index.clear()
        
        logger.info("清除所有记忆")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出 - 确保数据保存"""
        await self.flush()
    
    def close(self):
        """关闭记忆系统，释放资源"""
        if self.use_vector_index and self.vector_index:
            self.vector_index.close()
        logger.info("记忆系统已关闭")
    
    def __del__(self):
        """析构函数: 确保程序退出时刷新缓存到磁盘"""
        try:
            if self._dirty:
                logger.warning("析构时发现未保存的更改，尝试同步保存")
                try:
                    if os.path.exists(self._memory_file_json):
                        with open(self._memory_file_json, 'w', encoding='utf-8') as f:
                            json.dump(self.memory_cache, f, ensure_ascii=False, indent=2)
                except:
                    pass
            # 关闭向量索引
            if self.use_vector_index and self.vector_index:
                try:
                    self.vector_index.close()
                except:
                    pass
        except:
            pass


# 全局记忆系统实例
memory_system = MemorySystem()
