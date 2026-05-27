#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结构化日志系统
- 支持 trace_id 追踪
- 支持 JSON 格式输出
- 支持日志级别过滤
- 支持日志轮转
"""

from datetime import UTC
import os
import sys
import json
import time
import uuid
import logging
from datetime import datetime
from contextvars import ContextVar
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

# 全局上下文变量
_trace_id_var: ContextVar[str] = ContextVar('trace_id', default='')


def get_trace_id() -> str:
    """获取当前追踪 ID"""
    trace_id = _trace_id_var.get()
    if not trace_id:
        trace_id = str(uuid.uuid4())[:16]
        _trace_id_var.set(trace_id)
    return trace_id


def set_trace_id(trace_id: str) -> None:
    """设置追踪 ID"""
    _trace_id_var.set(trace_id)


def new_trace_id() -> str:
    """生成新的追踪 ID"""
    trace_id = str(uuid.uuid4())[:16]
    _trace_id_var.set(trace_id)
    return trace_id


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""
    
    def __init__(self, json_format: bool = False):
        super().__init__()
        self.json_format = json_format
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.now(UTC).isoformat() + 'Z',
            'level': record.levelname,
            'message': record.getMessage(),
            'logger': record.name,
            'trace_id': get_trace_id(),
            'pathname': record.pathname,
            'lineno': record.lineno,
        }
        
        if record.exc_info:
            log_data['exc_info'] = self.formatException(record.exc_info)
        
        if hasattr(record, 'extra_data'):
            log_data['extra'] = record.extra_data
        
        if self.json_format:
            return json.dumps(log_data, ensure_ascii=False)
        else:
            return f"[{log_data['timestamp']}] [{log_data['level']}] [trace_id={log_data['trace_id']}] {log_data['message']}"


class StructuredLogger:
    """结构化日志器"""
    
    _instance = None
    _loggers = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        
        self.log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
        self.log_dir.mkdir(exist_ok=True)
        
        # 根日志器
        self.root_logger = logging.getLogger("bayesian_agi")
        self.root_logger.setLevel(logging.INFO)
        self.root_logger.propagate = False
        
        # 控制台输出
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = StructuredFormatter(json_format=False)
        console_handler.setFormatter(console_formatter)
        self.root_logger.addHandler(console_handler)
        
        # 文件输出 - 按大小轮转
        file_handler = RotatingFileHandler(
            self.log_dir / "app.log",
            maxBytes=100 * 1024 * 1024,  # 100MB
            backupCount=10,
            encoding='utf-8'
        )
        file_formatter = StructuredFormatter(json_format=True)
        file_handler.setFormatter(file_formatter)
        self.root_logger.addHandler(file_handler)
        
        # 按日期轮转
        date_handler = TimedRotatingFileHandler(
            self.log_dir / "daily.log",
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        date_formatter = StructuredFormatter(json_format=False)
        date_handler.setFormatter(date_formatter)
        self.root_logger.addHandler(date_handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """获取命名日志器"""
        if name not in self._loggers:
            logger = self.root_logger.getChild(name)
            self._loggers[name] = logger
        return self._loggers[name]
    
    def log_with_extra(self, logger: logging.Logger, level: int, message: str, **extra):
        """带额外信息的日志记录"""
        record = logger.makeRecord(
            logger.name,
            level,
            logger.name,
            0,
            message,
            (),
            None,
            func=None
        )
        record.extra_data = extra
        logger.handle(record)


# 全局单例
_logger_instance = StructuredLogger()


def get_logger(name: str) -> logging.Logger:
    """获取结构化日志器"""
    return _logger_instance.get_logger(name)


def logger():
    """获取默认日志器"""
    return _logger_instance.get_logger("root")


def debug(msg: str, **extra):
    _logger_instance.log_with_extra(logger(), logging.DEBUG, msg, **extra)


def info(msg: str, **extra):
    _logger_instance.log_with_extra(logger(), logging.INFO, msg, **extra)


def warning(msg: str, **extra):
    _logger_instance.log_with_extra(logger(), logging.WARNING, msg, **extra)


def error(msg: str, **extra):
    _logger_instance.log_with_extra(logger(), logging.ERROR, msg, **extra)


def critical(msg: str, **extra):
    _logger_instance.log_with_extra(logger(), logging.CRITICAL, msg, **extra)


def exception(msg: str, **extra):
    _logger_instance.log_with_extra(logger(), logging.ERROR, msg, **extra)
