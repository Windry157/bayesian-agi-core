from collections import OrderedDict
from typing import Any, Dict, List, Optional


class MemorySystem:
    def __init__(self, memory_dir: str = "./memory", vector_model: Optional[str] = None, ollama_url: str = "http://localhost:11434"):
        self.memory_dir = memory_dir
        self.vector_model = vector_model
        self.ollama_url = ollama_url
        self.cache: OrderedDict = OrderedDict()
        self.cache_size = 100

    async def load(self): ...

    async def add_memory(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        return ""

    async def retrieve_memories(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        return []

    def clear_memory(self): ...

    def get_memory_count(self) -> int:
        return 0

    async def _save_to_disk(self): ...

    def _update_cache(self, key: str, content: Any):
        entry = {"content": content}
        if key in self.cache:
            self.cache[key] = entry
            self.cache.move_to_end(key)
        else:
            self.cache[key] = entry
            if len(self.cache) > self.cache_size:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
