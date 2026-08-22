#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版 RAG 检索器 - 集成知识图谱
"""

import uuid
from typing import List, Dict, Any, Optional

from src.core.knowledge.document_processor import DocumentProcessor
from src.core.knowledge.rag_retriever import RAGRetriever
from src.core.knowledge_graph import KnowledgeGraph, GraphQueryEngine

class EnhancedRAGRetriever:
    """增强版 RAG 检索器 - 结合向量检索和知识图谱"""
    
    def __init__(self, vector_index, knowledge_graph: Optional[KnowledgeGraph] = None):
        self.vector_index = vector_index
        self.rag_retriever = RAGRetriever(vector_index)
        self.knowledge_graph = knowledge_graph or KnowledgeGraph()
        self.graph_query_engine = GraphQueryEngine(self.knowledge_graph)
    
    async def add_document_with_graph(
        self,
        file_path: str,
        use_graph: bool = True
    ) -> Dict[str, Any]:
        """添加文档并构建知识图谱"""
        doc_result = await self.rag_retriever.add_document(file_path)
        
        if use_graph and doc_result.get('success'):
            doc_text = DocumentProcessor.extract_text(file_path)
            doc_id = doc_result.get('doc_id', str(uuid.uuid4()))
            
            graph_result = await self.knowledge_graph.add_from_text(
                doc_text,
                document_id=doc_id,
                use_llm=True
            )
            
            return {
                **doc_result,
                'graph_nodes_added': graph_result.get('nodes_added', 0),
                'graph_edges_added': graph_result.get('edges_added', 0)
            }
        
        return doc_result
    
    async def enhanced_query(
        self,
        query: str,
        top_k: int = 5,
        use_graph: bool = True
    ) -> Dict[str, Any]:
        """增强查询 - 结合向量检索和图谱查询"""
        vector_results = await self.vector_index.query(query, top_k=top_k)
        
        graph_results = []
        if use_graph and self.knowledge_graph.nodes:
            graph_results = self._query_graph_for_entities(query)
        
        combined_context = self._combine_contexts(vector_results, graph_results)
        
        sources = []
        for r in vector_results:
            sources.append({
                'type': 'document',
                'source': r.get('metadata', {}).get('source', '未知'),
                'content': r.get('content', '')[:200],
                'score': r.get('score', 0)
            })
        
        for gr in graph_results[:5]:
            sources.append({
                'type': 'graph',
                'source': gr.get('entity', '未知'),
                'content': f"关系: {gr.get('relation', '未知')}",
                'distance': gr.get('distance', 0)
            })
        
        return {
            'query': query,
            'context': combined_context,
            'sources': sources,
            'vector_results_count': len(vector_results),
            'graph_results_count': len(graph_results),
            'has_graph_data': len(self.knowledge_graph.nodes) > 0
        }
    
    def _query_graph_for_entities(self, query: str) -> List[Dict[str, Any]]:
        """从图谱中查询相关实体"""
        results = []
        
        entity_types = ['PERSON', 'ORGANIZATION', 'TECHNOLOGY', 'PRODUCT', 'CONCEPT']
        
        for entity_type in entity_types:
            entities = self.graph_query_engine.find_entities_by_type(entity_type)
            for entity in entities:
                if any(word.lower() in entity.name.lower() for word in query.split()):
                    related = self.graph_query_engine.find_related_entities(entity.name, max_depth=2)
                    results.extend(related)
        
        return results
    
    def _combine_contexts(
        self,
        vector_results: List[Dict[str, Any]],
        graph_results: List[Dict[str, Any]]
    ) -> str:
        """合并向量检索和图谱检索的上下文"""
        contexts = []
        
        if vector_results:
            contexts.append("【文档内容】")
            for r in vector_results[:3]:
                source = r.get('metadata', {}).get('source', '未知来源')
                contexts.append(f"来源: {source}")
                contexts.append(r.get('content', '')[:300])
                contexts.append("")
        
        if graph_results:
            contexts.append("\n【知识图谱关系】")
            seen_paths = set()
            for gr in graph_results[:5]:
                path = f"{gr.get('entity', '')} --[{gr.get('relation', '')}]--> 相关实体"
                if path not in seen_paths:
                    seen_paths.add(path)
                    contexts.append(path)
        
        return "\n".join(contexts) if contexts else "未找到相关信息"
    
    async def query_with_graph_reasoning(
        self,
        query: str,
        entity1: Optional[str] = None,
        entity2: Optional[str] = None
    ) -> Dict[str, Any]:
        """图谱推理查询"""
        if entity1 and entity2:
            relationship_result = self.graph_query_engine.answer_relationship_query(entity1, entity2)
            return relationship_result
        
        if self.knowledge_graph.nodes:
            related = self.graph_query_engine.find_related_entities(query, max_depth=2)
            
            if related:
                answer = f"关于 '{query}' 的相关信息：\n"
                for r in related[:5]:
                    answer += f"- 与 '{r['entity']}' 存在 '{r['relation']}' 关系\n"
                
                return {
                    'found': True,
                    'type': 'entity_related',
                    'answer': answer,
                    'related_entities': related[:5]
                }
        
        return {
            'found': False,
            'type': 'no_graph_data',
            'answer': '未找到图谱相关数据'
        }
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """获取图谱统计信息"""
        return self.knowledge_graph.get_stats()
    
    def get_triples_summary(self) -> str:
        """获取三元组摘要"""
        triples = self.knowledge_graph.query_triples()
        
        if not triples:
            return "知识图谱为空"
        
        summary = f"知识图谱包含 {len(triples)} 条关系：\n\n"
        
        relation_counts = {}
        for triple in triples:
            rel = triple.relation
            relation_counts[rel] = relation_counts.get(rel, 0) + 1
        
        for rel, count in sorted(relation_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            summary += f"- {rel}: {count} 条\n"
        
        return summary
    
    def export_graph_as_text(self) -> str:
        """导出图谱为文本格式"""
        triples = self.knowledge_graph.query_triples()
        
        if not triples:
            return "知识图谱为空"
        
        lines = ["# 知识图谱", "", "## 实体关系三元组", ""]
        
        for triple in triples:
            lines.append(f"({triple.head}) - [{triple.relation}] -> ({triple.tail})")
        
        return "\n".join(lines)
