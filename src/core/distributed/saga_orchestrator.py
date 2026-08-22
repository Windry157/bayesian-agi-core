#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Saga Orchestrator - 分布式事务编排器
实现幂等性补偿、最终一致性保证、状态机驱动的事务流程
"""
import uuid
import time
import logging
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class SagaState(Enum):
    """Saga 事务状态"""
    INITIATED = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    COMPENSATING = auto()
    COMPENSATED = auto()
    ABORTED = auto()


class StepState(Enum):
    """单个步骤状态"""
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()
    COMPENSATED = auto()
    SKIPPED = auto()


@dataclass
class SagaStep:
    """Saga 单个步骤"""
    step_id: str
    step_name: str
    execute_fn: Callable
    compensate_fn: Optional[Callable] = None
    params: Dict[str, Any] = field(default_factory=dict)
    state: StepState = StepState.PENDING
    result: Any = None
    error: Optional[Exception] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    retries: int = 0
    max_retries: int = 3
    executed_at: Optional[str] = None


@dataclass
class SagaTransaction:
    """Saga 事务记录"""
    transaction_id: str
    saga_name: str
    state: SagaState = SagaState.INITIATED
    steps: List[SagaStep] = field(default_factory=list)
    current_step_index: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Exception] = None
    compensation_started: Optional[str] = None


class SagaOrchestrator:
    """Saga 编排器 - 分布式事务管理"""
    
    def __init__(self, idempotency_service: Optional['IdempotencyService'] = None):
        self.transactions: Dict[str, SagaTransaction] = {}
        self.transaction_log: List[Dict[str, Any]] = []
        self.idempotency = idempotency_service or IdempotencyService()
        self.compensation_callbacks: List[Callable] = []
        self.completion_callbacks: List[Callable] = []
    
    def create_transaction(self, saga_name: str, metadata: Optional[Dict] = None) -> str:
        """
        创建一个新的 Saga 事务
        
        Args:
            saga_name: Saga 名称
            metadata: 元数据
            
        Returns:
            transaction_id: 全局事务 ID
        """
        transaction_id = str(uuid.uuid4())
        
        transaction = SagaTransaction(
            transaction_id=transaction_id,
            saga_name=saga_name,
            metadata=metadata or {}
        )
        
        self.transactions[transaction_id] = transaction
        self._log_transaction(transaction, "TRANSACTION_CREATED")
        
        logger.info(f"Created Saga transaction: {transaction_id} ({saga_name})")
        return transaction_id
    
    def add_step(self, transaction_id: str, step_name: str,
                 execute_fn: Callable, compensate_fn: Optional[Callable] = None,
                 params: Optional[Dict] = None, max_retries: int = 3) -> str:
        """
        添加一个 Saga 步骤
        
        Args:
            transaction_id: 事务 ID
            step_name: 步骤名称
            execute_fn: 执行函数
            compensate_fn: 补偿函数（可选）
            params: 参数
            max_retries: 最大重试次数
            
        Returns:
            step_id: 步骤 ID
        """
        transaction = self._get_transaction(transaction_id)
        step_id = f"{transaction_id}_{len(transaction.steps)}"
        
        step = SagaStep(
            step_id=step_id,
            step_name=step_name,
            execute_fn=execute_fn,
            compensate_fn=compensate_fn,
            params=params or {},
            max_retries=max_retries
        )
        
        transaction.steps.append(step)
        self._log_transaction(transaction, "STEP_ADDED", {"step_id": step_id})
        
        return step_id
    
    def execute(self, transaction_id: str) -> Dict[str, Any]:
        """
        执行 Saga 事务
        
        Args:
            transaction_id: 事务 ID
            
        Returns:
            执行结果
        """
        transaction = self._get_transaction(transaction_id)
        
        # 幂等性检查
        if self.idempotency.check(transaction_id, "saga_execution"):
            logger.warning(f"Transaction {transaction_id} already processed (idempotent)")
            return self._get_saved_result(transaction_id)
        
        try:
            transaction.state = SagaState.RUNNING
            self._update_transaction(transaction)
            
            # 执行步骤
            for i, step in enumerate(transaction.steps):
                transaction.current_step_index = i
                result = self._execute_step(transaction, step)
                
                if not result['success']:
                    # 执行失败，开始补偿
                    logger.error(f"Step {step.step_name} failed, starting compensation")
                    self._compensate(transaction)
                    return {
                        "success": False,
                        "transaction_id": transaction_id,
                        "state": transaction.state.value,
                        "error": str(result['error'])
                    }
                
                step.result = result['result']
            
            transaction.state = SagaState.COMPLETED
            self._update_transaction(transaction)
            
            # 保存幂等性结果
            final_result = {
                "success": True,
                "transaction_id": transaction_id,
                "state": transaction.state.value,
                "results": [s.result for s in transaction.steps]
            }
            self.idempotency.store(transaction_id, "saga_execution", final_result)
            
            # 触发完成回调
            self._trigger_completion_callbacks(transaction)
            
            logger.info(f"Saga completed successfully: {transaction_id}")
            return final_result
            
        except Exception as e:
            logger.error(f"Saga failed with exception: {str(e)}")
            transaction.error = e
            transaction.state = SagaState.FAILED
            self._update_transaction(transaction)
            self._compensate(transaction)
            
            return {
                "success": False,
                "transaction_id": transaction_id,
                "state": transaction.state.value,
                "error": str(e)
            }
    
    def _execute_step(self, transaction: SagaTransaction, step: SagaStep) -> Dict[str, Any]:
        """执行单个步骤（含重试和幂等性）"""
        idempotency_key = f"{transaction.transaction_id}_{step.step_id}"
        
        # 幂等性检查
        if self.idempotency.check(idempotency_key, "step_execution"):
            logger.info(f"Step {step.step_id} already executed (idempotent)")
            return self.idempotency.retrieve(idempotency_key, "step_execution")
        
        step.state = StepState.IN_PROGRESS
        step.start_time = time.time()
        step.retries = 0
        
        last_error = None
        
        for attempt in range(step.max_retries + 1):
            try:
                step.retries = attempt
                logger.info(f"Executing step {step.step_name} (attempt {attempt + 1}/{step.max_retries})")
                
                result = step.execute_fn(**step.params)
                
                step.state = StepState.COMPLETED
                step.end_time = time.time()
                step.executed_at = datetime.now().isoformat()
                
                success_result = {
                    "success": True,
                    "result": result
                }
                
                self.idempotency.store(idempotency_key, "step_execution", success_result)
                self._log_transaction(transaction, "STEP_COMPLETED", {"step_id": step.step_id})
                
                return success_result
                
            except Exception as e:
                last_error = e
                logger.warning(f"Step {step.step_name} failed attempt {attempt + 1}: {str(e)}")
                
                if attempt < step.max_retries:
                    backoff_time = (2 ** attempt) * 0.1
                    time.sleep(backoff_time)
        
        step.state = StepState.FAILED
        step.error = last_error
        step.end_time = time.time()
        
        self._log_transaction(transaction, "STEP_FAILED", {"step_id": step.step_id})
        
        return {
            "success": False,
            "error": last_error
        }
    
    def _compensate(self, transaction: SagaTransaction) -> None:
        """执行补偿流程（反向执行已完成步骤的补偿函数）"""
        transaction.state = SagaState.COMPENSATING
        transaction.compensation_started = datetime.now().isoformat()
        self._update_transaction(transaction)
        
        logger.info(f"Starting compensation for transaction {transaction.transaction_id}")
        
        # 反向补偿：从失败的步骤往回执行
        for i in range(transaction.current_step_index, -1, -1):
            step = transaction.steps[i]
            
            if step.state != StepState.COMPLETED:
                continue
            
            if step.compensate_fn is None:
                logger.info(f"Step {step.step_name} has no compensation, skipping")
                step.state = StepState.SKIPPED
                continue
            
            try:
                logger.info(f"Compensating step {step.step_name}")
                step.compensate_fn(**step.params)
                step.state = StepState.COMPENSATED
                
                self._log_transaction(transaction, "STEP_COMPENSATED", {"step_id": step.step_id})
                
            except Exception as e:
                logger.error(f"Compensation failed for step {step.step_name}: {str(e)}")
                # 补偿失败通常需要人工介入
                self._trigger_compensation_failure(transaction, step, e)
        
        transaction.state = SagaState.COMPENSATED
        self._update_transaction(transaction)
        self._trigger_compensation_callbacks(transaction)
    
    def on_completion(self, callback: Callable) -> None:
        """注册事务完成回调"""
        self.completion_callbacks.append(callback)
    
    def on_compensation_failure(self, callback: Callable) -> None:
        """注册补偿失败回调"""
        self.compensation_callbacks.append(callback)
    
    def get_transaction_status(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """获取事务状态"""
        transaction = self.transactions.get(transaction_id)
        if not transaction:
            return None
        
        return {
            "transaction_id": transaction.transaction_id,
            "saga_name": transaction.saga_name,
            "state": transaction.state.value,
            "current_step": transaction.current_step_index,
            "created_at": transaction.created_at,
            "steps": [
                {
                    "step_id": s.step_id,
                    "name": s.step_name,
                    "state": s.state.value,
                    "retries": s.retries
                }
                for s in transaction.steps
            ]
        }
    
    def _get_transaction(self, transaction_id: str) -> SagaTransaction:
        if transaction_id not in self.transactions:
            raise ValueError(f"Transaction {transaction_id} not found")
        return self.transactions[transaction_id]
    
    def _update_transaction(self, transaction: SagaTransaction) -> None:
        transaction.updated_at = datetime.now().isoformat()
        self.transaction_log.append({
            "timestamp": datetime.now().isoformat(),
            "transaction_id": transaction.transaction_id,
            "state": transaction.state.value
        })
    
    def _log_transaction(self, transaction: SagaTransaction, event: str, 
                         metadata: Optional[Dict] = None) -> None:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "transaction_id": transaction.transaction_id,
            "event": event,
            "metadata": metadata or {}
        }
        self.transaction_log.append(log_entry)
    
    def _get_saved_result(self, transaction_id: str) -> Dict[str, Any]:
        return self.idempotency.retrieve(transaction_id, "saga_execution")
    
    def _trigger_completion_callbacks(self, transaction: SagaTransaction) -> None:
        for callback in self.completion_callbacks:
            try:
                callback(transaction)
            except Exception as e:
                logger.error(f"Completion callback failed: {str(e)}")
    
    def _trigger_compensation_failure(self, transaction: SagaTransaction,
                                      step: SagaStep, error: Exception) -> None:
        for callback in self.compensation_callbacks:
            try:
                callback(transaction, step, error)
            except Exception as e:
                logger.error(f"Compensation callback failed: {str(e)}")

    def _trigger_compensation_callbacks(self, transaction: SagaTransaction) -> None:
        for callback in self.compensation_callbacks:
            try:
                callback(transaction, None, None)
            except Exception as e:
                logger.error(f"Compensation callback failed: {str(e)}")


class IdempotencyService:
    """幂等性服务 - 确保操作可以安全重试"""
    
    def __init__(self):
        self.operation_cache: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self.timestamps: Dict[Tuple[str, str], float] = {}
        self.ttl_seconds: float = 3600 * 24  # 24小时 TTL
    
    def check(self, key: str, operation_type: str) -> bool:
        """
        检查操作是否已执行过
        
        Args:
            key: 幂等键 (通常是业务ID + 步骤ID + 事务ID的组合)
            operation_type: 操作类型
            
        Returns:
            是否已执行
        """
        cache_key = (key, operation_type)
        
        if cache_key in self.operation_cache:
            # 检查 TTL
            if time.time() - self.timestamps[cache_key] < self.ttl_seconds:
                return True
            else:
                # 过期清理
                del self.operation_cache[cache_key]
                del self.timestamps[cache_key]
        
        return False
    
    def store(self, key: str, operation_type: str, result: Dict[str, Any]) -> None:
        """
        存储操作结果
        
        Args:
            key: 幂等键
            operation_type: 操作类型
            result: 结果
        """
        cache_key = (key, operation_type)
        self.operation_cache[cache_key] = result
        self.timestamps[cache_key] = time.time()
    
    def retrieve(self, key: str, operation_type: str) -> Optional[Dict[str, Any]]:
        """
        检索已存储的操作结果
        
        Args:
            key: 幂等键
            operation_type: 操作类型
            
        Returns:
            存储的结果，或 None
        """
        cache_key = (key, operation_type)
        return self.operation_cache.get(cache_key)
    
    def invalidate(self, key: str, operation_type: str) -> None:
        """使缓存失效"""
        cache_key = (key, operation_type)
        if cache_key in self.operation_cache:
            del self.operation_cache[cache_key]
            del self.timestamps[cache_key]
    
    def cleanup_expired(self) -> int:
        """清理过期条目，返回清理数量"""
        expired = []
        current_time = time.time()
        
        for (key, op_type), ts in self.timestamps.items():
            if current_time - ts >= self.ttl_seconds:
                expired.append((key, op_type))
        
        for key, op_type in expired:
            del self.operation_cache[(key, op_type)]
            del self.timestamps[(key, op_type)]
        
        return len(expired)
