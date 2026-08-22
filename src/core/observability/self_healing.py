#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自愈能力模块 - 高级自动故障修复和弹性恢复系统

设计理念：
1. 模块化设计 - 动作、剧本、执行器分离
2. 安全授权 - RBAC权限控制
3. 异步执行 - 支持异步和同步动作
4. 可观测性 - 详细日志和指标
5. 可扩展性 - 插件化架构
6. 可靠性 - 重试、超时、回滚机制
"""

import logging
import time
import subprocess
import os
import asyncio
import threading
from typing import Dict, List, Optional, Callable, Any, Union, Type
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor, Future
from contextlib import contextmanager
from collections.abc import Coroutine

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ==================== 枚举定义 ====================

class RemediationStatus(Enum):
    """修复状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class RemediationPriority(Enum):
    """修复优先级"""
    CRITICAL = "critical"  # 立即执行，影响核心功能
    HIGH = "high"          # 高优先级，需要尽快处理
    MEDIUM = "medium"      # 中等优先级，常规处理
    LOW = "low"            # 低优先级，可以延迟处理


class ActionType(Enum):
    """动作类型"""
    SYNC = "sync"       # 同步执行
    ASYNC = "async"     # 异步执行
    THREAD = "thread"   # 线程执行


# ==================== 核心数据结构 ====================

@dataclass
class ExecutionContext:
    """执行上下文"""
    request_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: float = field(default_factory=time.time)
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RemediationAction(ABC):
    """修复动作抽象基类"""
    id: str
    name: str
    description: str
    priority: RemediationPriority
    action_type: ActionType = ActionType.SYNC
    timeout: int = 30
    retries: int = 3
    retry_delay: int = 2  # 重试间隔（秒）
    dependencies: List[str] = field(default_factory=list)
    required_permissions: List[str] = field(default_factory=list)
    
    @abstractmethod
    async def execute(self, context: ExecutionContext, **kwargs) -> bool:
        """执行动作（异步接口）"""
        pass
    
    @abstractmethod
    def execute_sync(self, context: ExecutionContext, **kwargs) -> bool:
        """执行动作（同步接口）"""
        pass


@dataclass
class RemediationExecution:
    """修复执行记录"""
    id: str
    action_id: str
    action_name: str
    status: RemediationStatus
    context: ExecutionContext
    started_at: float
    completed_at: Optional[float] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    result: Optional[Any] = None


@dataclass
class RemediationPlaybook:
    """修复剧本"""
    id: str
    name: str
    description: str
    actions: List[str]  # 动作ID列表
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    priority: RemediationPriority = RemediationPriority.MEDIUM


# ==================== 安全授权系统 ====================

class PermissionDeniedError(Exception):
    """权限拒绝异常"""
    pass


class RBACManager:
    """基于角色的访问控制管理器"""
    
    def __init__(self):
        self.roles: Dict[str, List[str]] = {}  # role -> permissions
        self.user_roles: Dict[str, List[str]] = {}  # user -> roles
    
    def add_role(self, role_name: str, permissions: List[str]):
        """添加角色"""
        self.roles[role_name] = permissions
    
    def assign_role(self, user_id: str, role_name: str):
        """为用户分配角色"""
        if user_id not in self.user_roles:
            self.user_roles[user_id] = []
        if role_name not in self.user_roles[user_id]:
            self.user_roles[user_id].append(role_name)
    
    def check_permission(self, user_id: str, permission: str) -> bool:
        """检查用户是否有指定权限"""
        if user_id not in self.user_roles:
            return False
        
        for role in self.user_roles[user_id]:
            if role in self.roles and permission in self.roles[role]:
                return True
        
        return False
    
    def check_permissions(self, user_id: str, permissions: List[str]) -> bool:
        """检查用户是否有所有指定权限"""
        for permission in permissions:
            if not self.check_permission(user_id, permission):
                return False
        return True


# ==================== 动作实现基类 ====================

class ShellAction(RemediationAction):
    """Shell命令执行动作"""
    
    def __init__(self, id: str, name: str, description: str, command: str,
                 priority: RemediationPriority = RemediationPriority.MEDIUM,
                 timeout: int = 60, retries: int = 3):
        super().__init__(
            id=id,
            name=name,
            description=description,
            priority=priority,
            action_type=ActionType.THREAD,
            timeout=timeout,
            retries=retries,
            required_permissions=["execute_shell"]
        )
        self.command = command
    
    async def execute(self, context: ExecutionContext, **kwargs) -> bool:
        """异步执行"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.execute_sync,
            context,
            **kwargs
        )
    
    def execute_sync(self, context: ExecutionContext, **kwargs) -> bool:
        """同步执行"""
        logger.info(f"🔧 执行Shell命令: {self.command}")
        
        try:
            result = subprocess.run(
                self.command,
                shell=True,
                timeout=self.timeout,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info(f"✅ Shell命令执行成功: {result.stdout}")
                return True
            else:
                logger.error(f"❌ Shell命令执行失败: {result.stderr}")
                return False
        
        except subprocess.TimeoutExpired:
            logger.error(f"⏰ Shell命令超时")
            return False
        except Exception as e:
            logger.error(f"❌ Shell命令异常: {e}")
            return False


class PythonAction(RemediationAction):
    """Python函数执行动作"""
    
    def __init__(self, id: str, name: str, description: str,
                 func: Union[Callable, Coroutine],
                 priority: RemediationPriority = RemediationPriority.MEDIUM,
                 timeout: int = 30, retries: int = 3):
        super().__init__(
            id=id,
            name=name,
            description=description,
            priority=priority,
            action_type=ActionType.ASYNC if asyncio.iscoroutinefunction(func) else ActionType.SYNC,
            timeout=timeout,
            retries=retries
        )
        self.func = func
    
    async def execute(self, context: ExecutionContext, **kwargs) -> bool:
        """异步执行"""
        if asyncio.iscoroutinefunction(self.func):
            return await self.func(context=context, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.execute_sync, context, **kwargs)
    
    def execute_sync(self, context: ExecutionContext, **kwargs) -> bool:
        """同步执行"""
        logger.info(f"🔧 执行Python函数: {self.name}")
        try:
            result = self.func(context=context, **kwargs)
            return bool(result)
        except Exception as e:
            logger.error(f"❌ Python函数执行异常: {e}")
            return False


# ==================== 自愈引擎核心 ====================

class SelfHealingEngine(ABC):
    """自愈引擎抽象基类"""
    
    @abstractmethod
    def register_action(self, action: RemediationAction):
        """注册修复动作"""
        pass
    
    @abstractmethod
    def register_playbook(self, playbook: RemediationPlaybook):
        """注册修复剧本"""
        pass
    
    @abstractmethod
    async def execute_action(self, action_id: str, context: ExecutionContext, **kwargs) -> RemediationExecution:
        """执行修复动作"""
        pass
    
    @abstractmethod
    async def execute_playbook(self, playbook_id: str, context: ExecutionContext, **kwargs) -> List[RemediationExecution]:
        """执行修复剧本"""
        pass


class DefaultSelfHealingEngine(SelfHealingEngine):
    """默认自愈引擎实现"""
    
    def __init__(self, rbac_manager: Optional[RBACManager] = None):
        self.actions: Dict[str, RemediationAction] = {}
        self.playbooks: Dict[str, RemediationPlaybook] = {}
        self.executions: Dict[str, RemediationExecution] = {}
        self.executing_actions: set = set()
        self.rbac_manager = rbac_manager or RBACManager()
        self.executor = ThreadPoolExecutor(max_workers=10)
        self._lock = threading.RLock()
        
        # 初始化默认角色和权限
        self._init_default_rbac()
    
    def _init_default_rbac(self):
        """初始化默认RBAC配置"""
        # 添加默认角色
        self.rbac_manager.add_role("admin", [
            "execute_shell",
            "restart_service",
            "modify_config",
            "scale_service",
            "access_database"
        ])
        
        self.rbac_manager.add_role("operator", [
            "execute_shell",
            "restart_service",
            "modify_config"
        ])
        
        self.rbac_manager.add_role("viewer", [])
    
    def register_action(self, action: RemediationAction):
        """注册修复动作"""
        with self._lock:
            self.actions[action.id] = action
        logger.info(f"📝 注册修复动作: [{action.priority.value}] {action.id} - {action.name}")
    
    def register_playbook(self, playbook: RemediationPlaybook):
        """注册修复剧本"""
        with self._lock:
            self.playbooks[playbook.id] = playbook
        logger.info(f"📋 注册修复剧本: [{playbook.priority.value}] {playbook.id} - {playbook.name}")
    
    async def execute_action(self, action_id: str, context: ExecutionContext, **kwargs) -> RemediationExecution:
        """执行修复动作"""
        # 检查动作是否存在
        if action_id not in self.actions:
            raise ValueError(f"未知的修复动作: {action_id}")
        
        action = self.actions[action_id]
        
        # 检查权限
        if action.required_permissions and context.user_id:
            if not self.rbac_manager.check_permissions(context.user_id, action.required_permissions):
                raise PermissionDeniedError(f"用户 {context.user_id} 没有执行动作 {action_id} 的权限")
        
        # 检查是否正在执行
        if action_id in self.executing_actions:
            logger.warning(f"⚠️ 动作 {action_id} 正在执行中，跳过")
            return RemediationExecution(
                id=f"exec-{context.request_id[:8]}",
                action_id=action_id,
                action_name=action.name,
                status=RemediationStatus.PENDING,
                context=context,
                started_at=time.time()
            )
        
        # 创建执行记录
        execution = RemediationExecution(
            id=f"exec-{context.request_id[:8]}-{int(time.time())}",
            action_id=action_id,
            action_name=action.name,
            status=RemediationStatus.RUNNING,
            context=context,
            started_at=time.time()
        )
        
        with self._lock:
            self.executions[execution.id] = execution
            self.executing_actions.add(action_id)
        
        logger.info(f"🚀 开始执行动作: {action_id} (优先级: {action.priority.value})")
        
        success = False
        last_error = None
        
        # 执行重试循环
        for attempt in range(action.retries):
            try:
                # 根据动作类型执行
                if action.action_type == ActionType.ASYNC:
                    result = await asyncio.wait_for(
                        action.execute(context, **kwargs),
                        timeout=action.timeout
                    )
                elif action.action_type == ActionType.THREAD:
                    future = self.executor.submit(action.execute_sync, context, **kwargs)
                    result = await asyncio.get_event_loop().run_in_executor(
                        None,
                        future.result,
                        action.timeout
                    )
                else:
                    # 同步执行（带超时）
                    result = await asyncio.wait_for(
                        asyncio.to_thread(action.execute_sync, context, **kwargs),
                        timeout=action.timeout
                    )
                
                if result:
                    success = True
                    logger.info(f"✅ 动作执行成功: {action_id} (尝试 {attempt + 1}/{action.retries})")
                    break
                else:
                    last_error = "动作返回失败"
                    logger.warning(f"⚠️ 动作执行失败: {action_id} (尝试 {attempt + 1}/{action.retries})")
            
            except asyncio.TimeoutError:
                last_error = f"执行超时 ({action.timeout}s)"
                logger.warning(f"⏰ 动作执行超时: {action_id} (尝试 {attempt + 1}/{action.retries})")
            except PermissionDeniedError as e:
                last_error = str(e)
                logger.error(f"🔒 权限拒绝: {e}")
                break
            except Exception as e:
                last_error = str(e)
                logger.error(f"❌ 动作执行异常: {action_id} (尝试 {attempt + 1}/{action.retries}): {e}")
            
            # 重试延迟（指数退避）
            if attempt < action.retries - 1:
                delay = action.retry_delay * (2 ** attempt)
                logger.info(f"⏳ 等待 {delay}s 后重试...")
                await asyncio.sleep(delay)
        
        # 更新执行状态
        with self._lock:
            self.executing_actions.remove(action_id)
            execution.completed_at = time.time()
            
            if success:
                execution.status = RemediationStatus.SUCCESS
                execution.result = True
            else:
                execution.status = RemediationStatus.FAILED
                execution.error_message = last_error
                execution.result = False
        
        logger.info(f"🏁 动作执行完成: {action_id} - {execution.status.value}")
        return execution
    
    async def execute_playbook(self, playbook_id: str, context: ExecutionContext, **kwargs) -> List[RemediationExecution]:
        """执行修复剧本"""
        if playbook_id not in self.playbooks:
            raise ValueError(f"未知的修复剧本: {playbook_id}")
        
        playbook = self.playbooks[playbook_id]
        
        # 检查条件
        if playbook.condition:
            if not playbook.condition(kwargs.get('metrics', {})):
                logger.info(f"📋 剧本条件不满足，跳过执行: {playbook_id}")
                return []
        
        logger.info(f"📋 开始执行修复剧本: {playbook_id} - {playbook.name}")
        
        results = []
        
        for action_id in playbook.actions:
            if action_id not in self.actions:
                logger.error(f"❌ 剧本中的动作不存在: {action_id}")
                continue
            
            try:
                result = await self.execute_action(action_id, context, **kwargs)
                results.append(result)
                
                # 如果关键动作失败，停止执行
                if result.status == RemediationStatus.FAILED:
                    action = self.actions[action_id]
                    if action.priority in [RemediationPriority.CRITICAL, RemediationPriority.HIGH]:
                        logger.error(f"🛑 高优先级动作失败，停止剧本执行: {action_id}")
                        break
            
            except Exception as e:
                logger.error(f"❌ 执行动作失败: {action_id}: {e}")
        
        logger.info(f"📋 修复剧本执行完成: {playbook_id} - {len(results)} 个动作")
        return results
    
    def get_execution(self, execution_id: str) -> Optional[RemediationExecution]:
        """获取执行记录"""
        return self.executions.get(execution_id)
    
    def get_execution_history(self, limit: int = 50) -> List[RemediationExecution]:
        """获取执行历史"""
        with self._lock:
            return sorted(
                self.executions.values(),
                key=lambda x: x.started_at,
                reverse=True
            )[:limit]
    
    def get_running_actions(self) -> List[str]:
        """获取正在执行的动作"""
        with self._lock:
            return list(self.executing_actions)
    
    def shutdown(self):
        """关闭引擎"""
        self.executor.shutdown(wait=True)
        logger.info("🔌 自愈引擎已关闭")


# ==================== 预定义的修复动作工厂 ====================

class RemediationActionFactory:
    """修复动作工厂"""
    
    @staticmethod
    def create_restart_service_action(service_name: str) -> ShellAction:
        """创建重启服务动作"""
        return ShellAction(
            id=f"restart-{service_name}",
            name=f"重启{service_name}服务",
            description=f"重启 {service_name} 服务进程",
            command=f"systemctl restart {service_name}",
            priority=RemediationPriority.CRITICAL,
            timeout=60,
            retries=2,
            required_permissions=["restart_service"]
        )
    
    @staticmethod
    def create_cleanup_cache_action(cache_type: str = "redis") -> ShellAction:
        """创建清理缓存动作"""
        commands = {
            "redis": "redis-cli FLUSHALL",
            "memcached": "echo 'flush_all' | nc localhost 11211",
            "local": "rm -rf /tmp/cache/*"
        }
        
        return ShellAction(
            id=f"cleanup-{cache_type}-cache",
            name=f"清理{cache_type}缓存",
            description=f"清理 {cache_type} 缓存数据",
            command=commands.get(cache_type, commands["redis"]),
            priority=RemediationPriority.LOW,
            timeout=30,
            retries=1
        )
    
    @staticmethod
    def create_scale_action(direction: str, service_name: str, replicas: int) -> ShellAction:
        """创建扩缩容动作"""
        return ShellAction(
            id=f"{direction}-{service_name}-{replicas}",
            name=f"{direction} {service_name}",
            description=f"{direction} {service_name} 到 {replicas} 副本",
            command=f"kubectl scale deployment {service_name} --replicas={replicas}",
            priority=RemediationPriority.HIGH if direction == "scale-up" else RemediationPriority.LOW,
            timeout=120,
            retries=2,
            required_permissions=["scale_service"]
        )
    
    @staticmethod
    def create_python_action(id: str, name: str, description: str, func: Callable,
                             priority: RemediationPriority = RemediationPriority.MEDIUM) -> PythonAction:
        """创建Python动作"""
        return PythonAction(
            id=id,
            name=name,
            description=description,
            func=func,
            priority=priority
        )


# ==================== 预定义的修复剧本 ====================

class RemediationPlaybookLibrary:
    """修复剧本库"""
    
    @staticmethod
    def create_high_error_rate_playbook() -> RemediationPlaybook:
        """高错误率修复剧本"""
        return RemediationPlaybook(
            id="high-error-rate",
            name="高错误率处理",
            description="当API错误率超过阈值时的修复流程",
            actions=[
                "cleanup-redis-cache",
                "refresh-config",
                "restart-api"
            ],
            condition=lambda metrics: metrics.get("error_rate", 0) > 0.05,
            priority=RemediationPriority.CRITICAL
        )
    
    @staticmethod
    def create_high_latency_playbook() -> RemediationPlaybook:
        """高延迟修复剧本"""
        return RemediationPlaybook(
            id="high-latency",
            name="高延迟处理",
            description="当P95延迟超过阈值时的修复流程",
            actions=[
                "cleanup-redis-cache",
                "scale-up-api-2",
                "cleanup-local-cache"
            ],
            condition=lambda metrics: metrics.get("latency_p95", 0) > 0.5,
            priority=RemediationPriority.HIGH
        )
    
    @staticmethod
    def create_db_connection_issue_playbook() -> RemediationPlaybook:
        """数据库连接问题修复剧本"""
        return RemediationPlaybook(
            id="db-connection-issue",
            name="数据库连接问题处理",
            description="当数据库连接池耗尽时的修复流程",
            actions=[
                "switch-to-standby-db",
                "cleanup-redis-cache"
            ],
            condition=lambda metrics: metrics.get("db_connection_errors", 0) > 10,
            priority=RemediationPriority.CRITICAL
        )
    
    @staticmethod
    def create_memory_exhaustion_playbook() -> RemediationPlaybook:
        """内存耗尽修复剧本"""
        return RemediationPlaybook(
            id="memory-exhaustion",
            name="内存耗尽处理",
            description="当内存使用率超过阈值时的修复流程",
            actions=[
                "cleanup-redis-cache",
                "cleanup-local-cache",
                "cleanup-temp-files",
                "scale-up-api-2"
            ],
            condition=lambda metrics: metrics.get("memory_usage", 0) > 0.9,
            priority=RemediationPriority.HIGH
        )
    
    @staticmethod
    def create_circuit_breaker_open_playbook() -> RemediationPlaybook:
        """熔断器打开修复剧本"""
        return RemediationPlaybook(
            id="circuit-breaker-open",
            name="熔断器打开处理",
            description="当熔断器打开时的修复流程",
            actions=[
                "restart-api",
                "cleanup-redis-cache",
                "refresh-config"
            ],
            condition=lambda metrics: metrics.get("circuit_breaker_state", 0) == 1,
            priority=RemediationPriority.CRITICAL
        )


# ==================== 全局实例管理 ====================

class EngineFactory:
    """引擎工厂"""
    
    _engines: Dict[str, DefaultSelfHealingEngine] = {}
    _lock = threading.Lock()
    
    @classmethod
    def get_engine(cls, name: str = "default") -> DefaultSelfHealingEngine:
        """获取或创建引擎实例"""
        with cls._lock:
            if name not in cls._engines:
                cls._engines[name] = cls._create_engine()
            return cls._engines[name]
    
    @classmethod
    def _create_engine(cls) -> DefaultSelfHealingEngine:
        """创建新的引擎实例"""
        engine = DefaultSelfHealingEngine()
        
        # 注册默认动作
        cls._register_default_actions(engine)
        
        # 注册默认剧本
        cls._register_default_playbooks(engine)
        
        return engine
    
    @classmethod
    def _register_default_actions(cls, engine: DefaultSelfHealingEngine):
        """注册默认动作"""
        # 缓存清理动作
        engine.register_action(RemediationActionFactory.create_cleanup_cache_action("redis"))
        engine.register_action(RemediationActionFactory.create_cleanup_cache_action("local"))
        
        # 创建清理临时文件的Python动作
        def cleanup_temp_files(context: ExecutionContext, **kwargs) -> bool:
            import shutil
            temp_dir = kwargs.get('temp_dir', '/tmp')
            logger.info(f"🗑️ 清理临时文件: {temp_dir}")
            for item in os.listdir(temp_dir):
                item_path = os.path.join(temp_dir, item)
                try:
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                except Exception as e:
                    logger.warning(f"无法删除 {item_path}: {e}")
            return True
        
        engine.register_action(RemediationActionFactory.create_python_action(
            id="cleanup-temp-files",
            name="清理临时文件",
            description="清理系统临时文件",
            func=cleanup_temp_files,
            priority=RemediationPriority.LOW
        ))
        
        # 创建刷新配置的Python动作
        def refresh_config(context: ExecutionContext, **kwargs) -> bool:
            logger.info("🔄 刷新配置")
            # 实际实现中这里会重新加载配置
            return True
        
        engine.register_action(RemediationActionFactory.create_python_action(
            id="refresh-config",
            name="刷新配置",
            description="重新加载配置文件",
            func=refresh_config,
            priority=RemediationPriority.MEDIUM,
        ))
        
        # 创建切换数据库的Python动作
        def switch_to_standby_db(context: ExecutionContext, **kwargs) -> bool:
            logger.info("🔀 切换到备用数据库")
            return True
        
        engine.register_action(RemediationActionFactory.create_python_action(
            id="switch-to-standby-db",
            name="切换备用数据库",
            description="切换到备用数据库",
            func=switch_to_standby_db,
            priority=RemediationPriority.CRITICAL,
        ))
    
    @classmethod
    def _register_default_playbooks(cls, engine: DefaultSelfHealingEngine):
        """注册默认剧本"""
        engine.register_playbook(RemediationPlaybookLibrary.create_high_error_rate_playbook())
        engine.register_playbook(RemediationPlaybookLibrary.create_high_latency_playbook())
        engine.register_playbook(RemediationPlaybookLibrary.create_db_connection_issue_playbook())
        engine.register_playbook(RemediationPlaybookLibrary.create_memory_exhaustion_playbook())
        engine.register_playbook(RemediationPlaybookLibrary.create_circuit_breaker_open_playbook())
    
    @classmethod
    def shutdown_all(cls):
        """关闭所有引擎"""
        with cls._lock:
            for engine in cls._engines.values():
                engine.shutdown()
            cls._engines.clear()


# ==================== 便捷接口 ====================

def get_engine(name: str = "default") -> DefaultSelfHealingEngine:
    """获取自愈引擎实例"""
    return EngineFactory.get_engine(name)


async def execute_action(action_id: str, user_id: Optional[str] = None, **kwargs) -> RemediationExecution:
    """执行修复动作（便捷接口）"""
    engine = get_engine()
    context = ExecutionContext(user_id=user_id)
    return await engine.execute_action(action_id, context, **kwargs)


async def execute_playbook(playbook_id: str, user_id: Optional[str] = None, **kwargs) -> List[RemediationExecution]:
    """执行修复剧本（便捷接口）"""
    engine = get_engine()
    context = ExecutionContext(user_id=user_id)
    return await engine.execute_playbook(playbook_id, context, **kwargs)


# ==================== 示例用法 ====================

async def main():
    """示例用法"""
    # 获取引擎
    engine = get_engine()
    
    # 注册用户
    engine.rbac_manager.assign_role("admin-user", "admin")
    
    # 创建执行上下文
    context = ExecutionContext(user_id="admin-user")
    
    # 执行单个动作
    print("🔧 执行单个动作...")
    result = await engine.execute_action("cleanup-redis-cache", context)
    print(f"结果: {result.status.value}")
    
    # 执行修复剧本
    print("\n📋 执行高错误率修复剧本...")
    metrics = {"error_rate": 0.1}  # 模拟高错误率
    results = await engine.execute_playbook("high-error-rate", context, metrics=metrics)
    for r in results:
        print(f"  - {r.action_id}: {r.status.value}")
    
    # 获取执行历史
    print("\n📜 执行历史:")
    history = engine.get_execution_history(5)
    for exec in history:
        print(f"  [{exec.status.value}] {exec.action_name}")
    
    # 关闭引擎
    engine.shutdown()


if __name__ == "__main__":
    asyncio.run(main())