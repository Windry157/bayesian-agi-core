"""
MCP 链路追踪工具
统计 perceive→reason→act→remember 各阶段时延
"""
import time
import json
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class TraceSpan:
    """追踪跨度"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    name: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = None

    def end(self):
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000

class MCPTracer:
    """MCP 链路追踪器"""
    
    def __init__(self):
        self.active_spans: Dict[str, TraceSpan] = {}
        self.trace_history: list = []
        self.max_history = 1000
    
    def start_trace(self, method: str, params: Dict = None) -> str:
        """开始新追踪"""
        trace_id = f"t{int(time.time() * 1000)}_{id(self) % 1000}"
        total_span = TraceSpan(
            trace_id=trace_id,
            span_id=f"{trace_id}_total",
            parent_span_id=None,
            name="mcp_request_total",
            start_time=time.time(),
            metadata={"method": method}
        )
        self.active_spans[total_span.span_id] = total_span
        return trace_id
    
    def start_phase(self, trace_id: str, phase: str, metadata: Dict = None) -> str:
        """开始阶段: perceive, reason, act, remember"""
        span_id = f"{trace_id}_{phase}"
        span = TraceSpan(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=f"{trace_id}_total",
            name=phase,
            start_time=time.time(),
            metadata=metadata or {}
        )
        self.active_spans[span_id] = span
        logger.debug(f"[{trace_id}] 开始阶段: {phase}")
        return span_id
    
    def end_phase(self, span_id: str) -> float:
        """结束阶段并返回耗时(ms)"""
        if span_id in self.active_spans:
            span = self.active_spans[span_id]
            span.end()
            logger.debug(f"[{span.trace_id}] {span.name}: {span.duration_ms:.2f}ms")
            return span.duration_ms
        return 0.0
    
    def end_trace(self, trace_id: str, success: bool = True) -> Dict:
        """结束追踪"""
        total_span_id = f"{trace_id}_total"
        if total_span_id in self.active_spans:
            self.active_spans[total_span_id].end()
        
        trace_spans = {
            k: asdict(v) 
            for k, v in self.active_spans.items() 
            if v.trace_id == trace_id
        }
        
        phases = {}
        total_duration = 0.0
        for span in trace_spans.values():
            if span["name"] != "mcp_request_total" and span.get("duration_ms"):
                phases[span["name"]] = round(span["duration_ms"], 2)
                total_duration += span["duration_ms"]
        
        result = {
            "trace_id": trace_id,
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "phase_durations_ms": phases,
            "total_duration_ms": round(total_duration, 2)
        }
        
        self.trace_history.append(result)
        if len(self.trace_history) > self.max_history:
            self.trace_history.pop(0)
        
        for k in list(self.active_spans.keys()):
            if self.active_spans[k].trace_id == trace_id:
                del self.active_spans[k]
        
        phase_str = " | ".join([f"{k}:{v}ms" for k, v in phases.items()])
        logger.info(f"[{trace_id}] 链路完成 - 总计:{total_duration:.2f}ms | {phase_str}")
        
        return result

tracer = MCPTracer()
