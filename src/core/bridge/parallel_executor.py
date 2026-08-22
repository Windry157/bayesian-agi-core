"""
并行执行器模块

提供通用的异步并行执行能力，基于 asyncio.gather() 包装，支持任务包装、状态跟踪、错误隔离。

主要组件:
    - AsyncParallelExecutor: 并行执行器，支持最大并发数控制
    - TaskResult: 单个任务执行结果
    - ParallelResult: 并行执行聚合结果
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, List, Optional, Tuple

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class TaskResult:
    """单个任务执行结果"""
    task_id: int
    status: TaskStatus
    result: Optional[Any] = None
    error: Optional[Exception] = None
    execution_time: float = 0.0

    def is_success(self) -> bool:
        """判断任务是否成功"""
        return self.status == TaskStatus.SUCCESS

    def is_failed(self) -> bool:
        """判断任务是否失败"""
        return self.status == TaskStatus.FAILED


@dataclass
class ParallelResult:
    """并行执行聚合结果"""
    task_results: List[TaskResult] = field(default_factory=list)
    total_execution_time: float = 0.0

    @property
    def success_count(self) -> int:
        """成功任务数量"""
        return sum(1 for tr in self.task_results if tr.is_success())

    @property
    def failed_count(self) -> int:
        """失败任务数量"""
        return sum(1 for tr in self.task_results if tr.is_failed())

    @property
    def all_success(self) -> bool:
        """是否所有任务都成功"""
        return self.failed_count == 0 and len(self.task_results) > 0

    @property
    def all_failed(self) -> bool:
        """是否所有任务都失败"""
        return self.success_count == 0 and len(self.task_results) > 0

    @property
    def partial_failed(self) -> bool:
        """是否部分任务失败"""
        return self.success_count > 0 and self.failed_count > 0

    def get_success_results(self) -> List[Any]:
        """获取所有成功任务的结果"""
        return [tr.result for tr in self.task_results if tr.is_success() and tr.result is not None]

    def get_failed_errors(self) -> List[Exception]:
        """获取所有失败任务的错误"""
        return [tr.error for tr in self.task_results if tr.is_failed() and tr.error is not None]


class AsyncParallelExecutor:
    """
    异步并行执行器

    基于 asyncio.gather() 包装，提供任务包装、状态跟踪、错误隔离能力。
    支持最大并发数控制，避免资源耗尽。
    """

    def __init__(self, max_concurrency: Optional[int] = None):
        """
        初始化并行执行器

        Args:
            max_concurrency: 最大并发数，None 表示无限制
        """
        self.max_concurrency = max_concurrency

    async def execute(
        self,
        tasks: List[Callable[[], Awaitable[Any]]]
    ) -> ParallelResult:
        """
        并行执行任务列表

        Args:
            tasks: 任务列表，每个元素是一个返回协程的可调用对象

        Returns:
            ParallelResult: 包含所有任务结果的聚合对象
        """
        if not tasks:
            logger.info("No tasks to execute")
            return ParallelResult()

        task_count = len(tasks)
        logger.info(f"Starting parallel execution of {task_count} tasks")
        
        total_start = time.time()

        # 包装任务，添加状态跟踪和计时
        wrapped_tasks = [
            self._wrap_task(task_id, task)
            for task_id, task in enumerate(tasks)
        ]

        # 根据是否有最大并发数选择执行策略
        if self.max_concurrency is None:
            logger.info("Executing without concurrency limit")
            results = await asyncio.gather(*wrapped_tasks, return_exceptions=True)
        else:
            logger.info(f"Executing with max concurrency: {self.max_concurrency}")
            results = await self._execute_with_concurrency_limit(wrapped_tasks)

        total_time = time.time() - total_start

        # 处理结果
        task_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # 任务包装器本身抛出异常的情况
                task_results.append(TaskResult(
                    task_id=i,
                    status=TaskStatus.FAILED,
                    error=result,
                    execution_time=0.0
                ))
            else:
                task_results.append(result)

        parallel_result = ParallelResult(
            task_results=task_results,
            total_execution_time=total_time
        )
        
        # 记录详细日志
        logger.info(f"Parallel execution completed in {total_time:.4f}s")
        logger.info(f"Total tasks: {task_count}, Success: {parallel_result.success_count}, Failed: {parallel_result.failed_count}")
        
        for task_result in task_results:
            if task_result.is_success():
                logger.debug(f"Task {task_result.task_id} succeeded in {task_result.execution_time:.4f}s")
            else:
                logger.warning(f"Task {task_result.task_id} failed in {task_result.execution_time:.4f}s: {str(task_result.error) if task_result.error else 'Unknown error'}")

        return parallel_result

    async def _wrap_task(
        self,
        task_id: int,
        task: Callable[[], Awaitable[Any]]
    ) -> TaskResult:
        """
        包装单个任务，添加状态跟踪和计时

        Args:
            task_id: 任务 ID
            task: 任务可调用对象

        Returns:
            TaskResult: 任务执行结果
        """
        start = time.time()
        try:
            result = await task()
            execution_time = time.time() - start
            return TaskResult(
                task_id=task_id,
                status=TaskStatus.SUCCESS,
                result=result,
                execution_time=execution_time
            )
        except Exception as e:
            execution_time = time.time() - start
            return TaskResult(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error=e,
                execution_time=execution_time
            )

    async def _execute_with_concurrency_limit(
        self,
        wrapped_tasks: List[Awaitable[TaskResult]]
    ) -> List[TaskResult]:
        """
        使用 Semaphore 控制并发数执行任务

        Args:
            wrapped_tasks: 已包装的任务列表

        Returns:
            任务结果列表
        """
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def limited_task(wrapped_task: Awaitable[TaskResult]) -> TaskResult:
            async with semaphore:
                return await wrapped_task

        # 创建带并发限制的任务
        limited_tasks = [limited_task(wt) for wt in wrapped_tasks]
        return await asyncio.gather(*limited_tasks, return_exceptions=True)
