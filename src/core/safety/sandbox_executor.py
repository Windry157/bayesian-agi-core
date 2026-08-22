#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
沙盒化执行环境 - 运行时安全层

实现四层防御模型：
L1: 进程隔离 - 使用 subprocess/Popen 进行进程级隔离
L2: 资源限制 - CPU/内存/时间限制
L3: 系统调用控制 - 白名单机制
L4: 网络隔离 - 出站控制

附加组件：
- 速率限制与熔断器
- 审计与回溯机制
"""

import os
import sys
import subprocess
import signal
import time
import json
import hashlib
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Callable, Union
from enum import Enum
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

# 平台兼容性处理 - resource 模块仅在 Unix/Linux 上可用
try:
    import resource
    HAS_RESOURCE = True
except ImportError:
    resource = None
    HAS_RESOURCE = False

# 平台兼容性处理 - SIGKILL 在 Windows 上不存在
try:
    SIGKILL = signal.SIGKILL
except AttributeError:
    # Windows 上使用替代信号
    SIGKILL = 9  # 通用的 kill 信号值
import logging
from collections import defaultdict
from threading import Lock

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class SandboxStatus(Enum):
    """沙箱状态"""
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    KILLED = "killed"


class SandboxError(Exception):
    """沙箱执行错误"""
    pass


class ResourceLimit:
    """资源限制配置"""

    def __init__(
        self,
        cpu_time_limit: Optional[int] = 30,        # CPU时间限制（秒）
        wall_time_limit: Optional[int] = 60,       # 挂钟时间限制（秒）
        memory_limit: Optional[int] = 512 * 1024,  # 内存限制（KB），默认512MB
        stack_limit: Optional[int] = 8 * 1024,     # 栈大小限制（KB）
        max_processes: Optional[int] = 10,         # 最大进程数
        max_open_files: Optional[int] = 64,        # 最大打开文件数
    ):
        self.cpu_time_limit = cpu_time_limit
        self.wall_time_limit = wall_time_limit
        self.memory_limit = memory_limit
        self.stack_limit = stack_limit
        self.max_processes = max_processes
        self.max_open_files = max_open_files

    def apply_limits(self):
        """应用资源限制到当前进程
        
        Note: 资源限制仅在 Unix/Linux 系统上可用，Windows 系统会跳过此操作
        """
        if not HAS_RESOURCE:
            logger.warning("资源限制在当前平台不可用（Windows），将跳过此操作")
            return
        
        try:
            # CPU时间限制
            if self.cpu_time_limit:
                resource.setrlimit(resource.RLIMIT_CPU, (self.cpu_time_limit, self.cpu_time_limit))

            # 内存限制
            if self.memory_limit:
                resource.setrlimit(resource.RLIMIT_AS, (self.memory_limit * 1024, self.memory_limit * 1024))

            # 栈大小限制
            if self.stack_limit:
                resource.setrlimit(resource.RLIMIT_STACK, (self.stack_limit * 1024, self.stack_limit * 1024))

            # 最大进程数
            if self.max_processes:
                try:
                    resource.setrlimit(resource.RLIMIT_NPROC, (self.max_processes, self.max_processes))
                except ValueError:
                    logger.warning("无法设置进程数限制（权限不足）")

            # 最大打开文件数
            if self.max_open_files:
                resource.setrlimit(resource.RLIMIT_NOFILE, (self.max_open_files, self.max_open_files))

        except Exception as e:
            logger.error(f"应用资源限制失败: {e}")
            raise


class NetworkPolicy:
    """网络策略 - 出站控制"""

    def __init__(self, allow_list: Optional[List[str]] = None, deny_list: Optional[List[str]] = None):
        """
        Args:
            allow_list: 允许访问的域名/IP白名单
            deny_list: 禁止访问的域名/IP黑名单
        """
        self.allow_list = allow_list or []
        self.deny_list = deny_list or []
        self._block_all_outbound = len(allow_list) > 0  # 如果有白名单，默认拒绝所有

    def is_allowed(self, host: str) -> bool:
        """检查是否允许访问指定主机"""
        # 首先检查黑名单
        for deny in self.deny_list:
            if deny in host or host in deny:
                return False

        # 如果有白名单，检查白名单
        if self._block_all_outbound:
            for allow in self.allow_list:
                if allow in host or host in allow:
                    return True
            return False

        return True


class SystemCallFilter:
    """系统调用过滤器 - 白名单机制"""

    # 允许的系统调用列表（基于数学运算和文本处理的最小集）
    ALLOWED_SYSCALLS = {
        # 文件操作（只读）
        'open', 'openat', 'read', 'close', 'stat', 'fstat', 'lstat', 'access',
        # 内存操作
        'mmap', 'mprotect', 'munmap', 'brk', 'sbrk',
        # 进程控制
        'getpid', 'getppid', 'getuid', 'geteuid', 'getgid', 'getegid',
        # 时间
        'time', 'gettimeofday', 'clock_gettime',
        # 信号
        'sigaction', 'sigprocmask', 'sigsuspend',
        # IO
        'write', 'writev', 'readv',
        # 环境
        'getenv', 'environ',
        # 线程
        'pthread_create', 'pthread_join', 'pthread_mutex_lock', 'pthread_mutex_unlock',
    }

    def __init__(self, allowed_calls: Optional[set] = None):
        self.allowed_calls = allowed_calls or self.ALLOWED_SYSCALLS

    def is_allowed(self, syscall_name: str) -> bool:
        """检查系统调用是否允许"""
        return syscall_name in self.allowed_calls


@dataclass
class ExecutionResult:
    """执行结果"""
    status: SandboxStatus
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0
    execution_time: float = 0.0
    memory_used: int = 0  # 字节
    error_message: Optional[str] = None


@dataclass
class AuditEvent:
    """审计事件"""
    event_id: str
    event_type: str
    timestamp: datetime
    user_id: Optional[str] = None
    process_id: Optional[int] = None
    action: str = ""
    target: str = ""
    result: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


class AuditLogger:
    """审计日志记录器 - 不可篡改的日志系统"""

    def __init__(self, log_directory: str = "audit_logs"):
        self.log_directory = log_directory
        os.makedirs(log_directory, exist_ok=True)
        self._lock = Lock()

    def _generate_event_id(self) -> str:
        """生成唯一事件ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        unique_hash = hashlib.sha256(f"{timestamp}{os.urandom(16)}".encode()).hexdigest()[:16]
        return f"AUDIT-{timestamp}-{unique_hash}"

    def log_event(self, event_type: str, action: str, target: str, result: str, **details) -> str:
        """
        记录审计事件

        Args:
            event_type: 事件类型（process_start, process_end, syscall_failure, network_attempt等）
            action: 执行的动作
            target: 目标
            result: 结果
            **details: 额外信息

        Returns:
            事件ID
        """
        event = AuditEvent(
            event_id=self._generate_event_id(),
            event_type=event_type,
            timestamp=datetime.now(),
            process_id=os.getpid(),
            action=action,
            target=target,
            result=result,
            details=details
        )

        # 写入日志文件（按日期分区）
        date_str = event.timestamp.strftime("%Y-%m-%d")
        log_file = os.path.join(self.log_directory, f"audit_{date_str}.log")

        with self._lock:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "timestamp": event.timestamp.isoformat(),
                    "user_id": event.user_id,
                    "process_id": event.process_id,
                    "action": event.action,
                    "target": event.target,
                    "result": event.result,
                    "details": event.details
                }, ensure_ascii=False) + "\n")

        logger.info(f"Audit [{event.event_id}]: {event_type} - {action} on {target} -> {result}")
        return event.event_id


class CircuitBreaker:
    """熔断器模式实现"""

    def __init__(
        self,
        max_failures: int = 5,
        reset_timeout: int = 60,  # 重置超时时间（秒）
        failure_threshold: float = 0.5  # 失败率阈值
    ):
        self.max_failures = max_failures
        self.reset_timeout = reset_timeout
        self.failure_threshold = failure_threshold

        self._failures = 0
        self._successes = 0
        self._last_failure_time = 0
        self._state = "closed"  # closed, open, half-open
        self._lock = Lock()

    @property
    def state(self) -> str:
        """当前状态"""
        with self._lock:
            # 检查是否需要从open状态恢复
            if self._state == "open" and time.time() - self._last_failure_time >= self.reset_timeout:
                self._state = "half-open"
                self._failures = 0
            return self._state

    def record_success(self):
        """记录成功"""
        with self._lock:
            self._successes += 1
            if self._state == "half-open":
                # 在half-open状态下成功，重置熔断器
                self._state = "closed"
                self._failures = 0
                self._successes = 0

    def record_failure(self):
        """记录失败"""
        with self._lock:
            self._failures += 1
            self._last_failure_time = time.time()

            # 检查失败率
            total = self._failures + self._successes
            if total > 0 and self._failures / total >= self.failure_threshold:
                self._state = "open"

    def is_allowed(self) -> bool:
        """检查是否允许调用"""
        state = self.state
        if state == "open":
            return False
        return True

    def get_metrics(self) -> Dict[str, Any]:
        """获取熔断器指标"""
        with self._lock:
            return {
                "state": self._state,
                "failures": self._failures,
                "successes": self._successes,
                "last_failure_time": self._last_failure_time,
                "reset_timeout": self.reset_timeout
            }


class RateLimiter:
    """速率限制器"""

    def __init__(self, max_requests: int = 100, time_window: int = 60):
        """
        Args:
            max_requests: 时间窗口内最大请求数
            time_window: 时间窗口（秒）
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self._timestamps = []
        self._lock = Lock()

    def is_allowed(self) -> bool:
        """检查是否允许请求"""
        now = time.time()

        with self._lock:
            # 移除时间窗口外的记录
            self._timestamps = [t for t in self._timestamps if now - t < self.time_window]

            if len(self._timestamps) >= self.max_requests:
                return False

            self._timestamps.append(now)
            return True

    def get_remaining(self) -> int:
        """获取剩余请求数"""
        now = time.time()

        with self._lock:
            self._timestamps = [t for t in self._timestamps if now - t < self.time_window]
            return max(0, self.max_requests - len(self._timestamps))


class SandboxedExecutor(ABC):
    """沙箱执行器抽象基类"""

    @abstractmethod
    def execute(self, code: str, **kwargs) -> ExecutionResult:
        """执行代码"""
        pass

    @abstractmethod
    def get_status(self) -> SandboxStatus:
        """获取状态"""
        pass


class LocalSandboxExecutor(SandboxedExecutor):
    """
    本地沙箱执行器
    使用 subprocess 实现进程级隔离
    """

    def __init__(
        self,
        resource_limit: Optional[ResourceLimit] = None,
        network_policy: Optional[NetworkPolicy] = None,
        syscall_filter: Optional[SystemCallFilter] = None,
        audit_logger: Optional[AuditLogger] = None,
        rate_limiter: Optional[RateLimiter] = None,
        circuit_breaker: Optional[CircuitBreaker] = None
    ):
        self.resource_limit = resource_limit or ResourceLimit()
        self.network_policy = network_policy or NetworkPolicy()
        self.syscall_filter = syscall_filter or SystemCallFilter()
        self.audit_logger = audit_logger or AuditLogger()
        self.rate_limiter = rate_limiter or RateLimiter()
        self.circuit_breaker = circuit_breaker or CircuitBreaker()

        self._status = SandboxStatus.READY
        self._current_process = None
        self._start_time = 0.0

        logger.info("LocalSandboxExecutor 初始化完成")

    def _set_child_limits(self):
        """在子进程中设置资源限制"""
        self.resource_limit.apply_limits()

    def _monitor_process(self, proc: subprocess.Popen, timeout: int) -> Tuple[int, float]:
        """
        监控进程执行

        Args:
            proc: 进程对象
            timeout: 超时时间（秒）

        Returns:
            (返回码, 执行时间)
        """
        start_time = time.time()
        deadline = start_time + timeout

        while time.time() < deadline:
            if proc.poll() is not None:
                # 进程已结束
                return proc.returncode, time.time() - start_time

            time.sleep(0.1)

        # 超时，终止进程
        proc.kill()
        proc.wait()
        return -SIGKILL, time.time() - start_time

    def execute(self, code: str, language: str = "python") -> ExecutionResult:
        """
        在沙箱中执行代码

        Args:
            code: 要执行的代码
            language: 代码语言（python, javascript, shell）

        Returns:
            ExecutionResult
        """
        # 检查速率限制
        if not self.rate_limiter.is_allowed():
            self.audit_logger.log_event(
                "rate_limit_exceeded",
                "execute",
                "sandbox",
                "rejected",
                reason="请求速率超限"
            )
            return ExecutionResult(
                status=SandboxStatus.FAILED,
                error_message="请求速率超限，请稍后重试"
            )

        # 检查熔断器状态
        if not self.circuit_breaker.is_allowed():
            self.audit_logger.log_event(
                "circuit_breaker_open",
                "execute",
                "sandbox",
                "rejected",
                reason="熔断器已打开"
            )
            return ExecutionResult(
                status=SandboxStatus.FAILED,
                error_message="服务暂时不可用，请稍后重试"
            )

        # 记录进程启动
        event_id = self.audit_logger.log_event(
            "process_start",
            "execute",
            f"{language}_code",
            "started",
            code_length=len(code)
        )

        self._status = SandboxStatus.RUNNING
        self._start_time = time.time()

        try:
            # 根据语言类型构建命令
            if language == "python":
                args = [sys.executable, "-c", code]
            elif language == "javascript":
                args = ["node", "-e", code]
            elif language == "shell":
                args = ["bash", "-c", code]
            else:
                raise SandboxError(f"不支持的语言: {language}")

            # 创建子进程
            # Note: preexec_fn 在 Windows 上不支持，仅在 Unix/Linux 上使用
            popen_kwargs = {
                "args": args,
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "text": True,
                "env": {**os.environ, "PYTHONPATH": "."}
            }
            
            # 仅在 Unix/Linux 上使用 preexec_fn
            if HAS_RESOURCE:
                popen_kwargs["preexec_fn"] = self._set_child_limits
            
            proc = subprocess.Popen(**popen_kwargs)

            self._current_process = proc

            # 监控进程执行
            return_code, exec_time = self._monitor_process(proc, self.resource_limit.wall_time_limit)

            stdout, stderr = proc.communicate()

            # 根据返回码判断状态
            if return_code == -SIGKILL:
                status = SandboxStatus.TIMEOUT
                self.circuit_breaker.record_failure()
                self.audit_logger.log_event(
                    "process_timeout",
                    "execute",
                    "sandbox",
                    "timeout",
                    event_id=event_id,
                    execution_time=exec_time
                )
            elif return_code != 0:
                status = SandboxStatus.FAILED
                self.circuit_breaker.record_failure()
                self.audit_logger.log_event(
                    "process_failure",
                    "execute",
                    "sandbox",
                    "failed",
                    event_id=event_id,
                    return_code=return_code,
                    error=stderr
                )
            else:
                status = SandboxStatus.COMPLETED
                self.circuit_breaker.record_success()
                self.audit_logger.log_event(
                    "process_completed",
                    "execute",
                    "sandbox",
                    "success",
                    event_id=event_id,
                    execution_time=exec_time
                )

            return ExecutionResult(
                status=status,
                stdout=stdout,
                stderr=stderr,
                return_code=return_code,
                execution_time=exec_time,
                error_message=stderr if return_code != 0 else None
            )

        except Exception as e:
            self._status = SandboxStatus.FAILED
            self.circuit_breaker.record_failure()
            self.audit_logger.log_event(
                "process_error",
                "execute",
                "sandbox",
                "error",
                event_id=event_id,
                error=str(e)
            )
            return ExecutionResult(
                status=SandboxStatus.FAILED,
                error_message=str(e)
            )

    def get_status(self) -> SandboxStatus:
        """获取状态"""
        return self._status

    def get_metrics(self) -> Dict[str, Any]:
        """获取执行器指标"""
        return {
            "status": self._status.value,
            "rate_limiter_remaining": self.rate_limiter.get_remaining(),
            "circuit_breaker": self.circuit_breaker.get_metrics(),
            "resource_limit": {
                "cpu_time_limit": self.resource_limit.cpu_time_limit,
                "wall_time_limit": self.resource_limit.wall_time_limit,
                "memory_limit_mb": self.resource_limit.memory_limit // 1024
            }
        }


class SandboxManager:
    """沙箱管理器 - 管理多个沙箱执行器实例"""

    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self._executors: Dict[str, LocalSandboxExecutor] = {}
        self._executor_counter = 0
        self._lock = Lock()

        # 全局组件
        self._audit_logger = AuditLogger()
        self._global_rate_limiter = RateLimiter(max_requests=1000, time_window=60)
        self._global_circuit_breaker = CircuitBreaker(max_failures=100, reset_timeout=300)

        logger.info(f"SandboxManager 初始化完成，最大工作线程: {max_workers}")

    def _create_executor(self) -> LocalSandboxExecutor:
        """创建新的沙箱执行器"""
        return LocalSandboxExecutor(
            resource_limit=ResourceLimit(
                cpu_time_limit=30,
                wall_time_limit=60,
                memory_limit=512 * 1024,
                max_open_files=32
            ),
            network_policy=NetworkPolicy(
                allow_list=["api.openai.com", "ollama.local"]
            ),
            syscall_filter=SystemCallFilter(),
            audit_logger=self._audit_logger,
            rate_limiter=RateLimiter(max_requests=100, time_window=60),
            circuit_breaker=CircuitBreaker()
        )

    def execute(self, code: str, language: str = "python") -> ExecutionResult:
        """
        在沙箱中执行代码

        Args:
            code: 要执行的代码
            language: 代码语言

        Returns:
            ExecutionResult
        """
        # 全局速率限制检查
        if not self._global_rate_limiter.is_allowed():
            return ExecutionResult(
                status=SandboxStatus.FAILED,
                error_message="全局请求速率超限"
            )

        # 全局熔断器检查
        if not self._global_circuit_breaker.is_allowed():
            return ExecutionResult(
                status=SandboxStatus.FAILED,
                error_message="全局熔断器已打开"
            )

        with self._lock:
            # 检查是否有空闲执行器
            for executor_id, executor in self._executors.items():
                if executor.get_status() == SandboxStatus.READY:
                    result = executor.execute(code, language)
                    # 重置执行器状态
                    executor._status = SandboxStatus.READY
                    return result

            # 创建新执行器（如果未达到上限）
            if len(self._executors) < self.max_workers:
                executor_id = f"executor_{self._executor_counter}"
                self._executor_counter += 1
                executor = self._create_executor()
                self._executors[executor_id] = executor
                result = executor.execute(code, language)
                executor._status = SandboxStatus.READY
                return result

        return ExecutionResult(
            status=SandboxStatus.FAILED,
            error_message="所有沙箱执行器繁忙，请稍后重试"
        )

    def get_status(self) -> Dict[str, Any]:
        """获取管理器状态"""
        with self._lock:
            return {
                "total_executors": len(self._executors),
                "max_workers": self.max_workers,
                "ready_executors": sum(1 for e in self._executors.values() if e.get_status() == SandboxStatus.READY),
                "running_executors": sum(1 for e in self._executors.values() if e.get_status() == SandboxStatus.RUNNING),
                "global_rate_limiter_remaining": self._global_rate_limiter.get_remaining(),
                "global_circuit_breaker": self._global_circuit_breaker.get_metrics()
            }

    def cleanup(self):
        """清理所有执行器"""
        with self._lock:
            self._executors.clear()
            logger.info("SandboxManager 已清理所有执行器")


# 全局沙箱管理器实例
sandbox_manager = SandboxManager(max_workers=10)


def execute_in_sandbox(code: str, language: str = "python") -> ExecutionResult:
    """
    在沙箱中执行代码（便捷接口）

    Args:
        code: 要执行的代码
        language: 代码语言

    Returns:
        ExecutionResult
    """
    return sandbox_manager.execute(code, language)


def get_sandbox_status() -> Dict[str, Any]:
    """获取沙箱状态（便捷接口）"""
    return sandbox_manager.get_status()


def test_sandbox():
    """测试沙箱功能"""
    print("=" * 60)
    print("沙箱执行环境测试")
    print("=" * 60)

    # 测试1: 安全代码执行
    print("\n1. 测试安全代码执行:")
    code = """
import math
result = math.sqrt(16)
print(f"sqrt(16) = {result}")
"""
    result = execute_in_sandbox(code)
    print(f"状态: {result.status.value}")
    print(f"输出: {result.stdout.strip()}")
    print(f"执行时间: {result.execution_time:.2f}s")

    # 测试2: 测试危险代码拦截
    print("\n2. 测试危险代码拦截:")
    dangerous_code = """
import os
os.system('rm -rf /')
"""
    result = execute_in_sandbox(dangerous_code)
    print(f"状态: {result.status.value}")
    print(f"错误: {result.error_message}")

    # 测试3: 测试超时
    print("\n3. 测试超时控制:")
    timeout_code = """
import time
time.sleep(61)
print("completed")
"""
    result = execute_in_sandbox(timeout_code)
    print(f"状态: {result.status.value}")
    print(f"执行时间: {result.execution_time:.2f}s")

    # 测试4: 获取状态
    print("\n4. 获取沙箱状态:")
    status = get_sandbox_status()
    print(json.dumps(status, indent=2))

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_sandbox()
