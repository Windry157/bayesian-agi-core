import json
import math
import hashlib
import heapq
import statistics
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict, Counter
from pathlib import Path
from src.mcp.common import tokenize
from src.mcp.search import TfidfIndex


@dataclass
class MemoryItem:
    id: str
    content: str
    layer: str
    importance: float
    access_count: int
    created_at: str
    last_accessed: str
    metadata: Dict[str, Any]


class MemoryStore:
    LAYER_CONFIG = {
        "short_term": {"capacity": 100, "decay_hours": 24, "promotion_threshold": 0.7, "demotion_threshold": 0.3},
        "medium_term": {"capacity": 500, "decay_hours": 168, "promotion_threshold": 0.8, "demotion_threshold": 0.2},
        "long_term": {"capacity": 2000, "decay_hours": 8760, "promotion_threshold": 0.9, "demotion_threshold": 0.1},
    }

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.items: Dict[str, MemoryItem] = {}
        self.index = TfidfIndex()
        self._dirty = False
        self._load()

    def _item_path(self) -> Path:
        return self.data_dir / "memory_store.json"

    def _save_sync(self):
        data = {"items": {k: asdict(v) for k, v in self.items.items()}}
        self._item_path().write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def _load(self):
        path = self._item_path()
        if path.exists():
            try:
                data = json.loads(path.read_text())
                for k, v in data["items"].items():
                    self.items[k] = MemoryItem(**v)
                    self.index.add_document({"id": k, "content": v["content"], **v.get("metadata", {})})
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Failed to load memory: {e}")

    def add(self, content: str, layer: str = "short_term", importance: Optional[float] = None,
            metadata: Optional[Dict] = None) -> MemoryItem:
        if importance is None:
            importance = self._estimate_importance(content)
        item_id = hashlib.sha256(f"{content}{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        now = datetime.now().isoformat()
        item = MemoryItem(
            id=item_id, content=content,
            layer=layer if layer in self.LAYER_CONFIG else "short_term",
            importance=importance, access_count=0,
            created_at=now, last_accessed=now,
            metadata=metadata or {}
        )
        self.items[item_id] = item
        self.index.add_document({"id": item_id, "content": content, **(metadata or {})})
        self._enforce_capacity()
        self._dirty = True
        return item

    def get(self, item_id: str) -> Optional[MemoryItem]:
        item = self.items.get(item_id)
        if item:
            item.access_count += 1
            item.last_accessed = datetime.now().isoformat()
        return item

    def search(self, query: str, layers: Optional[List[str]] = None, top_k: int = 5) -> List[Tuple[MemoryItem, float]]:
        results = self.index.search(query, top_k=top_k * 3)
        filtered = []
        for doc_id, score in results:
            doc = self.index.documents[doc_id]
            if doc is None:
                continue
            item_id = doc.get("id")
            item = self.items.get(item_id)
            if item is None:
                continue
            if layers and item.layer not in layers:
                continue
            filtered.append((item, score))
            if len(filtered) >= top_k:
                break
        return filtered

    def _estimate_importance(self, content: str) -> float:
        score = 0.5
        score += min(len(content) / 1000, 0.2)
        important_keywords = ["critical", "error", "bug", "fix", "important", "urgent",
                             "security", "vulnerability", "crash", "严重", "紧急", "安全"]
        for kw in important_keywords:
            if kw.lower() in content.lower():
                score += 0.05
        return min(score, 1.0)

    def _enforce_capacity(self):
        for layer, config in self.LAYER_CONFIG.items():
            layer_items = [item for item in self.items.values() if item.layer == layer]
            if len(layer_items) <= config["capacity"]:
                continue
            now = datetime.now()
            scored = []
            for item in layer_items:
                age_hours = (now - datetime.fromisoformat(item.last_accessed)).total_seconds() / 3600
                decay = math.exp(-age_hours / config["decay_hours"])
                score = item.importance * 0.5 + (item.access_count / 100) * 0.3 + decay * 0.2
                scored.append((score, item))
            to_remove = len(layer_items) - config["capacity"]
            lowest = heapq.nsmallest(to_remove, scored, key=lambda x: x[0])
            for _, item in lowest:
                if item.importance < config["demotion_threshold"]:
                    del self.items[item.id]

    def optimize(self, action: str, criteria: Optional[Dict] = None) -> Dict[str, Any]:
        now = datetime.now()
        criteria = criteria or {}
        if action == "compact":
            merged_count = 0
            items_list = list(self.items.values())
            for i in range(len(items_list)):
                for j in range(i + 1, len(items_list)):
                    a, b = items_list[i], items_list[j]
                    if a.id == b.id:
                        continue
                    tokens_a = set(tokenize(a.content))
                    tokens_b = set(tokenize(b.content))
                    jaccard = len(tokens_a & tokens_b) / max(len(tokens_a | tokens_b), 1)
                    if jaccard > 0.85:
                        if a.importance >= b.importance:
                            a.access_count += b.access_count
                            a.metadata.setdefault("merged_from", []).append(b.id)
                            del self.items[b.id]
                        else:
                            b.access_count += a.access_count
                            b.metadata.setdefault("merged_from", []).append(a.id)
                            del self.items[a.id]
                        merged_count += 1
                        break
            energy_reduction = merged_count * 0.02
        elif action == "reinforce":
            reinforced = 0
            for item in self.items.values():
                age_hours = (now - datetime.fromisoformat(item.last_accessed)).total_seconds() / 3600
                if age_hours < 24 and item.access_count > 5:
                    item.importance = min(item.importance + 0.1, 1.0)
                    reinforced += 1
            energy_reduction = reinforced * 0.01
        elif action == "prune":
            min_importance = criteria.get("min_importance", 0.15)
            max_items = criteria.get("max_items", 5000)
            before = len(self.items)
            to_delete = []
            for item in self.items.values():
                age_hours = (now - datetime.fromisoformat(item.last_accessed)).total_seconds() / 3600
                if item.importance < min_importance and age_hours > 720:
                    to_delete.append(item.id)
            for item_id in to_delete:
                del self.items[item_id]
            if len(self.items) > max_items:
                sorted_items = sorted(self.items.values(), key=lambda x: x.importance)
                for item in sorted_items[:len(self.items) - max_items]:
                    del self.items[item.id]
            pruned = before - len(self.items)
            energy_reduction = pruned * 0.03
        elif action == "snapshot":
            energy_reduction = 0.0
        else:
            raise ValueError(f"Unknown action: {action}")
        total_items = len(self.items)
        free_energy = self._calculate_free_energy()
        layer_counts: Dict[str, int] = defaultdict(int)
        for item in self.items.values():
            layer_counts[item.layer] += 1
        self._dirty = True
        return {
            "action_taken": action,
            "items_before": total_items,
            "items_after": len(self.items),
            "free_energy_before": round(free_energy + energy_reduction, 3),
            "free_energy_after": round(free_energy, 3),
            "energy_reduction_percent": round(energy_reduction * 100, 1) if energy_reduction > 0 else 0,
            "memory_stats": {
                "short_term_count": layer_counts.get("short_term", 0),
                "medium_term_count": layer_counts.get("medium_term", 0),
                "long_term_count": layer_counts.get("long_term", 0),
                "total_items": total_items
            },
            "optimization_detail": {"action": action, "criteria": criteria, "timestamp": now.isoformat()}
        }

    def _calculate_free_energy(self) -> float:
        if not self.items:
            return 0.0
        layer_dist = Counter(item.layer for item in self.items.values())
        total = sum(layer_dist.values())
        entropy = 0.0
        for count in layer_dist.values():
            p = count / total
            entropy -= p * math.log2(p) if p > 0 else 0
        surprise = entropy / math.log2(len(self.LAYER_CONFIG))
        complexity = min(len(self.items) / 5000, 1.0)
        access_ratio = sum(item.access_count for item in self.items.values()) / max(len(self.items), 1)
        accuracy = min(access_ratio / 10, 1.0)
        free_energy = surprise * 0.4 + complexity * 0.3 + (1 - accuracy) * 0.3
        return round(min(free_energy, 1.0), 3)

    def get_stats(self) -> Dict[str, Any]:
        layer_counts: Dict[str, int] = defaultdict(int)
        for item in self.items.values():
            layer_counts[item.layer] += 1
        avg_importance = statistics.mean([item.importance for item in self.items.values()]) if self.items else 0
        return {
            "total_items": len(self.items),
            "short_term_count": layer_counts.get("short_term", 0),
            "medium_term_count": layer_counts.get("medium_term", 0),
            "long_term_count": layer_counts.get("long_term", 0),
            "avg_importance": round(avg_importance, 3),
            "free_energy": self._calculate_free_energy(),
            "index_stats": self.index.snapshot()
        }
