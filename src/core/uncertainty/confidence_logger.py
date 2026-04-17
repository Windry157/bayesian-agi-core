#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
置信度日志追踪模块
提供全链路日志记录和可追溯性功能
"""

import logging
import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from contextvars import ContextVar
from pathlib import Path
import threading

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 上下文变量用于追踪ID
trace_id_var: ContextVar[str] = ContextVar('trace_id', default='')
session_id_var: ContextVar[str] = ContextVar('session_id', default='')


class TraceRecord:
    """追踪记录"""

    def __init__(
        self,
        trace_id: str,
        operation: str,
        component: str,
        input_data: Dict[str, Any] = None,
        output_data: Any = None,
        metadata: Dict[str, Any] = None,
        error: str = None,
        duration_ms: float = None
    ):
        self.trace_id = trace_id
        self.operation = operation
        self.component = component
        self.input_data = input_data
        self.output_data = output_data
        self.metadata = metadata or {}
        self.error = error
        self.duration_ms = duration_ms
        self.timestamp = datetime.now()
        self.record_id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "record_id": self.record_id,
            "trace_id": self.trace_id,
            "operation": self.operation,
            "component": self.component,
            "input_data": self._truncate_data(self.input_data),
            "output_data": self._truncate_data(self.output_data),
            "metadata": self.metadata,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat()
        }

    def _truncate_data(self, data: Any, max_length: int = 500) -> Any:
        """截断数据以避免日志过大"""
        if data is None:
            return None
        
        if isinstance(data, dict):
            truncated = {}
            for key, value in data.items():
                if isinstance(value, str) and len(value) > max_length:
                    truncated[key] = value[:max_length] + "..."
                else:
                    truncated[key] = self._truncate_data(value, max_length)
            return truncated
        
        if isinstance(data, list):
            truncated = []
            for item in data[:10]:
                truncated.append(self._truncate_data(item, max_length))
            if len(data) > 10:
                truncated.append(f"... and {len(data) - 10} more items")
            return truncated
        
        if isinstance(data, str) and len(data) > max_length:
            return data[:max_length] + "..."
        
        return data


class ConfidenceLogger:
    """置信度日志记录器
    
    提供全链路日志记录和可追溯性功能
    """

    def __init__(self, log_dir: str = "memory/logs/confidence"):
        """初始化置信度日志记录器
        
        Args:
            log_dir: 日志存储目录
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self._trace_history: List[TraceRecord] = []
        self._max_history_size = 10000
        self._lock = threading.Lock()
        
        logger.info(f"置信度日志记录器初始化完成: {log_dir}")

    def create_trace_id(self) -> str:
        """创建追踪ID"""
        trace_id = str(uuid.uuid4())[:16]
        trace_id_var.set(trace_id)
        return trace_id

    def set_session_id(self, session_id: str):
        """设置会话ID"""
        session_id_var.set(session_id)

    def get_trace_id(self) -> str:
        """获取当前追踪ID"""
        return trace_id_var.get()

    def get_session_id(self) -> str:
        """获取当前会话ID"""
        return session_id_var.get()

    def log_operation(
        self,
        operation: str,
        component: str,
        input_data: Dict[str, Any] = None,
        output_data: Any = None,
        metadata: Dict[str, Any] = None,
        error: str = None,
        duration_ms: float = None
    ) -> TraceRecord:
        """记录操作日志
        
        Args:
            operation: 操作名称
            component: 组件名称
            input_data: 输入数据
            output_data: 输出数据
            metadata: 元数据
            error: 错误信息
            duration_ms: 耗时（毫秒）
            
        Returns:
            追踪记录
        """
        trace_id = self.get_trace_id() or self.create_trace_id()
        
        record = TraceRecord(
            trace_id=trace_id,
            operation=operation,
            component=component,
            input_data=input_data,
            output_data=output_data,
            metadata=metadata,
            error=error,
            duration_ms=duration_ms
        )
        
        with self._lock:
            self._trace_history.append(record)
            
            if len(self._trace_history) > self._max_history_size:
                self._trace_history = self._trace_history[-self._max_history_size:]
        
        self._save_to_file(record)
        
        log_message = f"[{trace_id}] {component}.{operation}"
        if error:
            logger.error(f"{log_message} - ERROR: {error}")
        else:
            logger.info(f"{log_message} - OK ({duration_ms:.2f}ms)")
        
        return record

    def _save_to_file(self, record: TraceRecord):
        """保存记录到文件"""
        try:
            date_str = datetime.now().strftime("%Y%m%d")
            log_file = self.log_dir / f"confidence_{date_str}.jsonl"
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
        
        except Exception as e:
            logger.warning(f"保存日志到文件失败: {e}")

    def get_trace(self, trace_id: str) -> List[TraceRecord]:
        """获取追踪记录
        
        Args:
            trace_id: 追踪ID
            
        Returns:
            追踪记录列表
        """
        with self._lock:
            return [r for r in self._trace_history if r.trace_id == trace_id]

    def get_traces_by_session(self, session_id: str) -> List[List[TraceRecord]]:
        """获取会话的所有追踪
        
        Args:
            session_id: 会话ID
            
        Returns:
            追踪记录分组列表
        """
        trace_groups = {}
        
        with self._lock:
            for record in self._trace_history:
                if record.metadata.get("session_id") == session_id:
                    if record.trace_id not in trace_groups:
                        trace_groups[record.trace_id] = []
                    trace_groups[record.trace_id].append(record)
        
        return list(trace_groups.values())

    def get_recent_traces(self, limit: int = 100) -> List[TraceRecord]:
        """获取最近的追踪记录
        
        Args:
            limit: 限制数量
            
        Returns:
            追踪记录列表
        """
        with self._lock:
            return self._trace_history[-limit:]

    def get_operation_stats(self) -> Dict[str, Any]:
        """获取操作统计
        
        Returns:
            操作统计信息
        """
        with self._lock:
            if not self._trace_history:
                return {"total_operations": 0}
            
            operation_counts = {}
            component_counts = {}
            error_count = 0
            total_duration = 0
            duration_count = 0
            
            for record in self._trace_history:
                operation_counts[record.operation] = operation_counts.get(record.operation, 0) + 1
                component_counts[record.component] = component_counts.get(record.component, 0) + 1
                
                if record.error:
                    error_count += 1
                
                if record.duration_ms is not None:
                    total_duration += record.duration_ms
                    duration_count += 1
            
            return {
                "total_operations": len(self._trace_history),
                "operation_counts": operation_counts,
                "component_counts": component_counts,
                "error_count": error_count,
                "error_rate": round(error_count / len(self._trace_history) * 100, 2),
                "avg_duration_ms": round(total_duration / duration_count, 2) if duration_count > 0 else 0,
                "unique_traces": len(set(r.trace_id for r in self._trace_history))
            }

    def search_traces(
        self,
        operation: str = None,
        component: str = None,
        error_only: bool = False,
        limit: int = 100
    ) -> List[TraceRecord]:
        """搜索追踪记录
        
        Args:
            operation: 操作名称
            component: 组件名称
            error_only: 仅返回错误记录
            limit: 限制数量
            
        Returns:
            匹配的追踪记录列表
        """
        with self._lock:
            results = self._trace_history.copy()
            
            if operation:
                results = [r for r in results if r.operation == operation]
            
            if component:
                results = [r for r in results if r.component == component]
            
            if error_only:
                results = [r for r in results if r.error is not None]
            
            return results[-limit:]

    def clear_history(self):
        """清空历史记录"""
        with self._lock:
            self._trace_history.clear()
        logger.info("追踪历史已清空")


class ConfidenceTracer:
    """置信度追踪器上下文管理器
    
    用于追踪代码块的执行
    """

    def __init__(
        self,
        logger_instance: ConfidenceLogger,
        operation: str,
        component: str,
        metadata: Dict[str, Any] = None
    ):
        """初始化追踪器
        
        Args:
            logger_instance: 日志记录器实例
            operation: 操作名称
            component: 组件名称
            metadata: 元数据
        """
        self.logger_instance = logger_instance
        self.operation = operation
        self.component = component
        self.metadata = metadata or {}
        self.start_time = None
        self.record = None

    def __enter__(self):
        """进入上下文"""
        self.start_time = datetime.now()
        self.record = self.logger_instance.log_operation(
            operation=self.operation,
            component=self.component,
            metadata=self.metadata,
            input_data=self.metadata.get("input_data")
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        duration_ms = (datetime.now() - self.start_time).total_seconds() * 1000
        
        if exc_type is not None:
            self.logger_instance.log_operation(
                operation=self.operation,
                component=self.component,
                metadata=self.metadata,
                error=str(exc_val),
                duration_ms=duration_ms
            )
            return False
        
        self.logger_instance.log_operation(
            operation=self.operation,
            component=self.component,
            metadata=self.metadata,
            duration_ms=duration_ms
        )
        return True

    def set_output(self, output_data: Any):
        """设置输出数据"""
        if self.record:
            self.record.output_data = output_data


# 全局日志记录器实例
confidence_logger = ConfidenceLogger()


def create_tracer(operation: str, component: str, metadata: Dict[str, Any] = None) -> ConfidenceTracer:
    """创建追踪器
    
    Args:
        operation: 操作名称
        component: 组件名称
        metadata: 元数据
        
    Returns:
        置信度追踪器
    """
    return ConfidenceTracer(confidence_logger, operation, component, metadata)