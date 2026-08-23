#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
向量索引模块
使用 ChromaDB 实现语义检索

Phase 4优化: 向量索引集成
- 基于向量相似度的语义检索
- 支持文档添加、查询、删除操作
- 自动处理嵌入向量生成
"""

import logging
import os
from typing import List, Dict, Optional, Any

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMADB = True
    logger.info("ChromaDB 已加载，将使用向量索引")
except ImportError:
    HAS_CHROMADB = False
    logger.warning("ChromaDB 未安装，向量索引功能不可用")


class VectorIndex:
    """向量索引类
    使用 ChromaDB 实现基于向量相似度的语义检索
    """
    
    def __init__(self, persist_dir: str = "vector_db", collection_name: str = "memories"):
        """初始化向量索引
        
        Args:
            persist_dir: 持久化目录
            collection_name: 集合名称
        """
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        
        if HAS_CHROMADB:
            self._init_chromadb()
    
    def _init_chromadb(self):
        """初始化 ChromaDB 客户端"""
        try:
            os.makedirs(self.persist_dir, exist_ok=True)
            self.client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=Settings(
                    anonymized_telemetry=False
                )
            )
            self.collection = self.client.get_or_create_collection(self.collection_name)
            logger.info(f"ChromaDB 集合 '{self.collection_name}' 初始化完成，持久化目录: {self.persist_dir}")
        except Exception as e:
            logger.error(f"初始化 ChromaDB 失败: {e}")
            self.client = None
            self.collection = None
    
    async def add_documents(self, documents: List[str], ids: List[str], metadatas: Optional[List[Dict[str, Any]]] = None):
        """添加文档到向量索引
        
        Args:
            documents: 文档内容列表
            ids: 文档ID列表
            metadatas: 元数据列表（可选）
        """
        if not HAS_CHROMADB or not self.collection:
            logger.warning("ChromaDB 不可用，跳过向量索引添加")
            return
        
        try:
            self.collection.add(
                documents=documents,
                ids=ids,
                metadatas=metadatas
            )
            logger.info(f"向量索引添加 {len(documents)} 条文档")
        except Exception as e:
            logger.error(f"向量索引添加失败: {e}")
    
    async def query(self, query_text: str, top_k: int = 5, where: Optional[Dict[str, Any]] = None, score_threshold: float = 0.2) -> List[Dict[str, Any]]:
        """查询向量索引
        
        Args:
            query_text: 查询文本
            top_k: 返回数量
            where: 筛选条件
            score_threshold: 相似度阈值，低于此阈值的结果将被过滤（默认0.2）
            
        Returns:
            匹配结果列表，包含id、content、score、metadata
        """
        if not HAS_CHROMADB or not self.collection:
            logger.warning("ChromaDB 不可用，返回空结果")
            return []
        
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=top_k,
                where=where
            )
            
            formatted_results = []
            filtered_count = 0
            filtered_details = []
            
            if results and results.get('documents'):
                logger.debug(f"原始检索结果数量: {len(results['documents'][0])}")
                
                for i in range(len(results['documents'][0])):
                    distance = results['distances'][0][i]
                    score = 1 - distance  # 转换为相似度分数（1 - 距离）
                    doc_id = results['ids'][0][i]
                    content = results['documents'][0][i]
                    
                    # 记录每条结果的相似度分数
                    logger.debug(f"检索结果 [{i+1}]: id={doc_id[:10]}..., score={score:.4f}, threshold={score_threshold}")
                    
                    # 过滤低于阈值的结果
                    if score >= score_threshold:
                        formatted_results.append({
                            'id': doc_id,
                            'content': content,
                            'score': score,
                            'metadata': results['metadatas'][0][i] if results.get('metadatas') else None
                        })
                    else:
                        filtered_count += 1
                        filtered_details.append(f"id={doc_id[:10]}..., score={score:.4f}")
            
            # 记录被过滤的条目
            if filtered_count > 0:
                logger.info(f"向量检索过滤: {filtered_count} 条低于阈值 {score_threshold} 的结果")
                logger.debug(f"过滤详情: {', '.join(filtered_details)}")
            
            logger.info(f"向量检索完成，查询: '{query_text}', 匹配: {len(formatted_results)} 条, 过滤: {filtered_count} 条, 阈值: {score_threshold}")
            return formatted_results
        except Exception as e:
            logger.error(f"向量检索失败: {e}")
            return []
    
    async def delete(self, ids: List[str]):
        """从向量索引中删除文档
        
        Args:
            ids: 要删除的文档ID列表
        """
        if not HAS_CHROMADB or not self.collection:
            logger.warning("ChromaDB 不可用，跳过删除")
            return
        
        try:
            self.collection.delete(ids=ids)
            logger.info(f"向量索引删除 {len(ids)} 条文档")
        except Exception as e:
            logger.error(f"向量索引删除失败: {e}")
    
    def get_count(self) -> int:
        """获取向量索引中文档数量
        
        Returns:
            文档数量
        """
        if not HAS_CHROMADB or not self.collection:
            return 0
        
        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f"获取向量索引文档数量失败: {e}")
            return 0
    
    def clear(self):
        """清空向量索引"""
        if not HAS_CHROMADB or not self.collection:
            logger.warning("ChromaDB 不可用，跳过清空")
            return
        
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.get_or_create_collection(self.collection_name)
            logger.info(f"向量索引已清空")
        except Exception as e:
            logger.error(f"清空向量索引失败: {e}")
    
    def close(self):
        """关闭ChromaDB客户端，释放资源"""
        if self.client:
            try:
                # ChromaDB PersistentClient 不需要显式关闭
                # 但我们可以清空引用帮助垃圾回收
                self.collection = None
                self.client = None
                logger.info("ChromaDB 客户端已关闭")
            except Exception as e:
                logger.error(f"关闭 ChromaDB 客户端失败: {e}")
