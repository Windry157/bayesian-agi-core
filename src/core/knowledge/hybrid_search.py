#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混合检索器 - 结合向量搜索和关键词搜索
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter
import math

class HybridSearchEngine:
    """混合搜索引擎 - 结合向量搜索和 BM25 关键词搜索"""
    
    def __init__(self, vector_index=None):
        self.vector_index = vector_index
        self.documents = {}
        self.doc_term_freq = {}
        self.doc_count = 0
        self.avg_doc_len = 0
        self.k1 = 1.5
        self.b = 0.75
    
    def index_documents(self, documents: List[Dict[str, Any]]):
        """索引文档用于 BM25 搜索"""
        self.documents = {str(i): doc for i, doc in enumerate(documents)}
        self._calculate_bm25_params()
    
    def _calculate_bm25_params(self):
        """计算 BM25 参数"""
        total_terms = 0
        for doc_id, doc in self.documents.items():
            text = doc.get('content', '')
            terms = self._tokenize(text)
            self.doc_term_freq[doc_id] = Counter(terms)
            total_terms += len(terms)
        
        self.doc_count = len(self.documents)
        self.avg_doc_len = total_terms / self.doc_count if self.doc_count > 0 else 0
    
    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        text = text.lower()
        tokens = re.findall(r'\w+', text)
        return tokens
    
    def _calculate_idf(self, term: str) -> float:
        """计算 IDF"""
        doc_freq = sum(1 for doc_tf in self.doc_term_freq.values() if term in doc_tf)
        if doc_freq == 0:
            return 0
        return math.log((self.doc_count - doc_freq + 0.5) / (doc_freq + 0.5) + 1)
    
    def _bm25_score(self, query_terms: List[str], doc_id: str) -> float:
        """计算单个文档的 BM25 分数"""
        doc_tf = self.doc_term_freq.get(doc_id, Counter())
        doc_len = sum(doc_tf.values())
        
        score = 0.0
        for term in query_terms:
            if term not in doc_tf:
                continue
            
            tf = doc_tf[term]
            idf = self._calculate_idf(term)
            
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / self.avg_doc_len))
            
            score += idf * (numerator / denominator)
        
        return score
    
    def search_bm25(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """BM25 关键词搜索"""
        query_terms = self._tokenize(query)
        
        scores = []
        for doc_id in self.documents:
            score = self._bm25_score(query_terms, doc_id)
            if score > 0:
                scores.append((doc_id, score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for doc_id, score in scores[:top_k]:
            doc = self.documents[doc_id].copy()
            doc['score'] = score
            doc['doc_id'] = doc_id
            results.append(doc)
        
        return results
    
    async def hybrid_search(
        self, 
        query: str, 
        top_k: int = 5,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """混合搜索 - 结合向量搜索和关键词搜索"""
        vector_results = []
        if self.vector_index:
            vector_results = await self.vector_index.query(query, top_k=top_k * 2)
        
        bm25_results = self.search_bm25(query, top_k=top_k * 2)
        
        all_doc_ids = set()
        for r in vector_results:
            all_doc_ids.add(r.get('id', ''))
        for r in bm25_results:
            all_doc_ids.add(r.get('doc_id', ''))
        
        max_vector_score = max([r.get('score', 0) for r in vector_results], default=1)
        max_bm25_score = max([r.get('score', 0) for r in bm25_results], default=1)
        
        combined_scores = {}
        
        for result in vector_results:
            doc_id = result.get('id', '')
            normalized_score = result.get('score', 0) / max_vector_score
            combined_scores[doc_id] = {
                'content': result.get('content', ''),
                'metadata': result.get('metadata', {}),
                'vector_score': normalized_score,
                'bm25_score': 0,
                'combined_score': normalized_score * vector_weight
            }
        
        for result in bm25_results:
            doc_id = result.get('doc_id', '')
            normalized_score = result.get('score', 0) / max_bm25_score
            
            if doc_id in combined_scores:
                combined_scores[doc_id]['bm25_score'] = normalized_score
                combined_scores[doc_id]['combined_score'] += normalized_score * keyword_weight
            else:
                combined_scores[doc_id] = {
                    'content': result.get('content', ''),
                    'metadata': result.get('metadata', {}),
                    'vector_score': 0,
                    'bm25_score': normalized_score,
                    'combined_score': normalized_score * keyword_weight
                }
        
        sorted_results = sorted(
            combined_scores.items(),
            key=lambda x: x[1]['combined_score'],
            reverse=True
        )
        
        final_results = []
        for doc_id, data in sorted_results[:top_k]:
            final_results.append({
                'content': data['content'],
                'metadata': data['metadata'],
                'vector_score': data['vector_score'],
                'bm25_score': data['bm25_score'],
                'combined_score': data['combined_score'],
                'source': data['metadata'].get('source', '未知来源'),
                'doc_id': doc_id
            })
        
        return final_results
