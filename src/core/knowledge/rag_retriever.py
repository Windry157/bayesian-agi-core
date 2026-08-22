#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG检索器模块 - 将文档向量化存储并进行语义检索
"""

import uuid
from typing import List, Dict, Any, Optional

from src.core.knowledge.document_processor import DocumentProcessor

class RAGRetriever:
    """RAG检索器"""
    
    def __init__(self, vector_index):
        self.vector_index = vector_index
        self.document_metadata = {}
    
    async def add_document(self, file_path: str) -> Dict[str, Any]:
        """处理并添加文档到知识库"""
        result = DocumentProcessor.process_document(file_path)
        
        if not result['success']:
            return result
        
        doc_id = str(uuid.uuid4())
        self.document_metadata[doc_id] = {
            'file_name': result['file_name'],
            'file_type': result['file_type'],
            'total_chars': result['total_chars'],
            'total_chunks': result['total_chunks']
        }
        
        for i, chunk in enumerate(result['chunks']):
            chunk_id = f"{doc_id}_{i}"
            await self.vector_index.add(
                documents=[chunk],
                metadatas=[{
                    'doc_id': doc_id,
                    'chunk_index': i,
                    'file_name': result['file_name'],
                    'source': result['file_name']
                }],
                ids=[chunk_id]
            )
        
        return {
            'success': True,
            'doc_id': doc_id,
            'file_name': result['file_name'],
            'total_chunks_added': result['total_chunks'],
            'message': f"文档 '{result['file_name']}' 已成功添加到知识库，共 {result['total_chunks']} 个片段"
        }
    
    async def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """检索相关文档片段"""
        results = await self.vector_index.query(query, top_k=top_k)
        
        formatted_results = []
        for result in results:
            source = result.get('metadata', {}).get('source', '未知来源')
            doc_id = result.get('metadata', {}).get('doc_id', '')
            
            formatted_results.append({
                'content': result.get('content', ''),
                'score': result.get('score', 0),
                'source': source,
                'doc_id': doc_id
            })
        
        return formatted_results
    
    async def query_with_context(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """检索并返回带上下文的结果（用于RAG）"""
        relevant_chunks = await self.retrieve(query, top_k)
        
        if not relevant_chunks:
            return {
                'has_context': False,
                'context': '',
                'sources': [],
                'retrieved_chunks': []
            }
        
        context = "\n\n".join([f"【{chunk['source']}】\n{chunk['content']}" for chunk in relevant_chunks])
        sources = list(set([chunk['source'] for chunk in relevant_chunks]))
        
        return {
            'has_context': True,
            'context': context,
            'sources': sources,
            'retrieved_chunks': relevant_chunks
        }
    
    def get_document_list(self) -> List[Dict[str, Any]]:
        """获取已添加的文档列表"""
        return [{'doc_id': k, **v} for k, v in self.document_metadata.items()]
    
    async def delete_document(self, doc_id: str) -> bool:
        """删除文档及其所有片段"""
        if doc_id not in self.document_metadata:
            return False
        
        chunk_ids = [f"{doc_id}_{i}" for i in range(self.document_metadata[doc_id]['total_chunks'])]
        await self.vector_index.delete(chunk_ids)
        del self.document_metadata[doc_id]
        
        return True
    
    async def clear_all(self):
        """清空所有文档"""
        self.document_metadata.clear()
        await self.vector_index.clear()