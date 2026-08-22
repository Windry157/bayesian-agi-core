import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path
from src.mcp.search import TfidfIndex


class BugDatabase:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.bugs: List[Dict[str, Any]] = []
        self.index = TfidfIndex()
        self._dirty = False
        self._load()

    def _path(self) -> Path:
        return self.data_dir / "bugs.json"

    def _save_sync(self):
        self._path().write_text(json.dumps(self.bugs, ensure_ascii=False, indent=2))

    def _load(self):
        path = self._path()
        if path.exists():
            try:
                self.bugs = json.loads(path.read_text())
                for bug in self.bugs:
                    self.index.add_document(bug)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Failed to load bugs: {e}")

    def add_bug(self, bug: Dict[str, Any]) -> Dict[str, Any]:
        bug["id"] = f"BUG-{datetime.now().strftime('%Y%m%d')}-{len(self.bugs):04d}"
        bug["created_at"] = datetime.now().isoformat()
        self.bugs.append(bug)
        self.index.add_document(bug)
        self._dirty = True
        return bug

    def search(self, query: str, top_k: int = 5, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        results = self.index.search(query, top_k=top_k * 2)
        filtered = []
        for doc_id, score in results:
            doc = self.index.documents[doc_id]
            if doc is None:
                continue
            bug = self.bugs[doc_id]
            if filters:
                if "language" in filters and bug.get("language") != filters["language"]:
                    continue
                if "severity" in filters and bug.get("severity") != filters["severity"]:
                    continue
            filtered.append({**bug, "relevance_score": round(score, 4)})
            if len(filtered) >= top_k:
                break
        return filtered

    def get_stats(self) -> Dict[str, Any]:
        return {"total_bugs": len(self.bugs), "index_stats": self.index.snapshot()}
