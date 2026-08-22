import statistics
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional
from src.mcp.memory import MemoryStore
from src.mcp.bug_db import BugDatabase


class InsightGenerator:
    @staticmethod
    def generate(topic: str, memory_store: MemoryStore, bug_db: BugDatabase, depth: str = "deep") -> Dict[str, Any]:
        patterns = []
        insights = []
        recommendations = []
        memory_results = memory_store.search(topic, top_k=10)
        bug_results = bug_db.search(topic, top_k=10)
        if memory_results:
            layers = [item.layer for item, _ in memory_results]
            layer_dist = Counter(layers)
            patterns.append({
                "type": "memory_distribution",
                "description": f"记忆分布: 短期 {layer_dist.get('short_term', 0)}条, 中期 {layer_dist.get('medium_term', 0)}条, 长期 {layer_dist.get('long_term', 0)}条",
                "confidence": 0.8,
                "evidence": ["记忆检索结果"]
            })
        if bug_results:
            severities = Counter(b.get("severity", "unknown") for b in bug_results)
            patterns.append({
                "type": "bug_severity_distribution",
                "description": f"Bug严重程度分布: {dict(severities)}",
                "confidence": 0.75,
                "evidence": ["Bug数据库检索"]
            })
        if len(memory_results) >= 3:
            importance_trend = [item.importance for item, _ in memory_results]
            avg_imp = statistics.mean(importance_trend)
            patterns.append({
                "type": "importance_trend",
                "description": f"相关记忆平均重要度: {avg_imp:.2f}" + (" (较高关注度)" if avg_imp > 0.6 else " (一般关注度)"),
                "confidence": 0.7,
                "evidence": ["记忆重要性分析"]
            })
        if depth in ("deep", "comprehensive") and memory_results and bug_results:
            insights.append({
                "type": "cross_domain",
                "description": f"'{topic}' 同时出现在记忆和 Bug 数据库中，可能存在关联问题",
                "confidence": round(0.6 + 0.2 * min(len(memory_results), 5) / 5, 2),
                "evidence": ["记忆检索", "Bug检索"],
                "implications": ["建议检查相关代码", "可能需要预防性修复"]
            })
        if patterns:
            top_pattern = Counter(p["type"] for p in patterns).most_common(1)[0][0]
            insights.append({
                "type": "dominant_pattern",
                "description": f"最主要的模式类型: {top_pattern}",
                "confidence": 0.75,
                "evidence": ["模式分析"],
                "implications": ["可据此优化关注方向"]
            })
        if not insights:
            insights.append({
                "type": "basic_analysis",
                "description": f"主题 '{topic}' 的基础分析（数据有限或无匹配结果）",
                "confidence": 0.5,
                "evidence": ["查询分析"],
                "implications": ["建议补充更多数据以获取更深入的洞察"]
            })
        if bug_results:
            recommendations.append("审查相关 Bug 并实施修复")
        if memory_results and any(item.importance < 0.3 for item, _ in memory_results):
            recommendations.append("清理低价值记忆以降低认知负载")
        recommendations.append("持续监控相关模式的变化趋势")
        overall_confidence = round(min(max(0.5 + 0.1 * len(insights) + 0.05 * len(patterns) - 0.02 * len(recommendations), 0.1), 0.95), 2)
        return {
            "topic": topic,
            "depth": depth,
            "overall_confidence": overall_confidence,
            "patterns_identified": patterns,
            "insights": insights[:5],
            "recommendations": recommendations[:5],
            "data_sources": {"memory_matches": len(memory_results), "bug_matches": len(bug_results)},
            "generated_at": datetime.now().isoformat()
        }
