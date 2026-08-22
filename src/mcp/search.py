import json
import math
from collections import defaultdict, Counter
from typing import Any, Dict, List, Optional, Tuple
from src.mcp.common import tokenize, cosine_similarity


class TfidfIndex:
    def __init__(self):
        self.documents: List[Optional[Dict[str, Any]]] = []
        self.doc_vectors: List[Dict[str, float]] = []
        self.doc_norms: List[float] = []
        self.idf: Dict[str, float] = {}
        self.inverted_index: Dict[str, List[Tuple[int, float]]] = {}
        self._dirty = False

    def add_document(self, doc: Dict[str, Any]) -> int:
        doc_id = len(self.documents)
        self.documents.append(doc)
        self._dirty = True
        return doc_id

    def remove_document(self, doc_id: int):
        if doc_id < len(self.documents):
            self.documents[doc_id] = None
            self._dirty = True

    def _rebuild_index(self):
        self.doc_vectors = []
        self.doc_norms = []
        self.inverted_index = defaultdict(list)
        doc_count = sum(1 for d in self.documents if d is not None)
        df: Dict[str, int] = defaultdict(int)
        doc_token_sets = []
        for doc in self.documents:
            if doc is None:
                doc_token_sets.append(set())
                continue
            text = json.dumps(doc)
            tokens = set(tokenize(text))
            doc_token_sets.append(tokens)
            for token in tokens:
                df[token] += 1
        self.idf = {}
        for token, doc_freq in df.items():
            self.idf[token] = math.log((doc_count + 1) / (doc_freq + 1)) + 1
        for doc_id, tokens in enumerate(doc_token_sets):
            tf = Counter(tokens)
            max_tf = max(tf.values()) if tf else 1
            vec = {}
            for token, count in tf.items():
                weight = (count / max_tf) * self.idf.get(token, 1)
                vec[token] = weight
                self.inverted_index[token].append((doc_id, weight))
            self.doc_vectors.append(vec)
            self.doc_norms.append(math.sqrt(sum(v*v for v in vec.values())))
        self._dirty = False

    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        if self._dirty:
            self._rebuild_index()
        query_tokens = Counter(tokenize(query))
        max_qf = max(query_tokens.values()) if query_tokens else 1
        query_vec = {}
        for token, count in query_tokens.items():
            query_vec[token] = (count / max_qf) * self.idf.get(token, 1)
        query_norm = math.sqrt(sum(v*v for v in query_vec.values()))
        if query_norm == 0:
            return []
        candidate_scores: Dict[int, float] = defaultdict(float)
        for token, q_weight in query_vec.items():
            for doc_id, d_weight in self.inverted_index.get(token, []):
                if self.documents[doc_id] is None:
                    continue
                candidate_scores[doc_id] += q_weight * d_weight
        scores = []
        for doc_id, dot in candidate_scores.items():
            doc_norm = self.doc_norms[doc_id]
            if doc_norm == 0:
                continue
            score = dot / (query_norm * doc_norm)
            if score > 0:
                scores.append((doc_id, score))
        remaining = top_k - len(scores)
        if remaining > 0:
            seen = set(candidate_scores.keys())
            for doc_id, vec in enumerate(self.doc_vectors):
                if doc_id in seen or self.documents[doc_id] is None:
                    continue
                score = cosine_similarity(query_vec, vec)
                if score > 0:
                    scores.append((doc_id, score))
        scores.sort(key=lambda x: -x[1])
        return scores[:top_k]

    def snapshot(self) -> Dict:
        return {
            "total_documents": sum(1 for d in self.documents if d is not None),
            "indexed_terms": len(self.idf),
        }
