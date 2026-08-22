# 企业级功能使用指南 v2

## 目录

1. [性能优化](#性能优化)
2. [审计日志系统](#审计日志系统)
3. [权限控制系统](#权限控制系统)
4. [多租户支持](#多租户支持)
5. [综合应用示例](#综合应用示例)

---

## 性能优化

### LRU缓存

LRU (Least Recently Used) 缓存用于热点数据缓存，自动淘汰最久未使用的条目。

#### 基本使用

```python
from src.core.cache.lru_cache import LRUCache

# 创建缓存
cache = LRUCache(
    max_size=10000,          # 最大条目数
    default_ttl=3600,        # 默认过期时间(秒)
    cleanup_threshold=0.8    # 清理阈值
)

# 设置缓存
await cache.set("key1", "value1", ttl=300)

# 获取缓存
value = await cache.get("key1")

# 删除缓存
await cache.delete("key1")
```

#### 使用装饰器

```python
from src.core.cache.lru_cache import lru_cache_decorator

@lru_cache_decorator(ttl=300, key_prefix="my_func")
async def expensive_function(param1, param2):
    # 耗时操作
    return result
```

#### 获取统计信息

```python
stats = await cache.get_stats()
print(f"缓存命中率: {stats['hit_rate']}%")
print(f"缓存大小: {stats['size']}/{stats['max_size']}")
```

### 推理优化器

推理优化器用于缓存推理结果，减少重复计算。

#### 基本使用

```python
from src.core.cognition.reasoning_optimizer import ReasoningOptimizer

optimizer = ReasoningOptimizer(
    cache_ttl=300,          # 缓存过期时间
    max_cache_size=1000     # 最大缓存大小
)

async def my_reasoning(input_data):
    # 推理逻辑
    return result

# 使用缓存执行推理
result = await optimizer.cached_reasoning(
    my_reasoning,
    "reasoning_type",
    input_data
)
```

#### 使用装饰器

```python
from src.core.cognition.reasoning_optimizer import optimize_reasoning

@optimize_reasoning("complex_inference", cache_ttl=300)
async def complex_inference(data):
    # 复杂推理
    return result
```

#### 获取优化统计

```python
stats = optimizer.get_stats()
print(f"总推理次数: {stats['total_inferences']}")
print(f"缓存命中率: {stats['cache_hit_rate']}%")
print(f"平均推理时间: {stats['avg_compute_time']}s")
```

---

## 审计日志系统

审计日志系统用于记录关键操作和安全事件。

### 基本使用

```python
from src.core.monitoring.audit_logger import (
    AuditLogger,
    get_audit_logger,
    AuditEventType,
    AuditLevel
)

# 获取审计日志实例
audit_logger = get_audit_logger(
    log_file="audit.log",
    max_events_in_memory=10000
)

# 启动日志系统
await audit_logger.start()

# 记录事件
event_id = await audit_logger.log_event(
    event_type=AuditEventType.USER_LOGIN,
    event_level=AuditLevel.INFO,
    user_id="user123",
    user_name="张三",
    tenant_id="tenant456",
    resource_type="system",
    action="用户登录",
    ip_address="192.168.1.100",
    metadata={"app": "web"}
)
```

### 使用装饰器

```python
from src.core.monitoring.audit_logger import audit

@audit(
    event_type=AuditEventType.API_CALL,
    event_level=AuditLevel.INFO,
    resource_type="api"
)
async def sensitive_operation(user_id, data):
    # 敏感操作
    return result
```

### 查询审计日志

```python
# 查询最近的登录事件
events = audit_logger.query_events(
    event_type=AuditEventType.USER_LOGIN.value,
    limit=50
)

# 查询特定用户的事件
user_events = audit_logger.query_events(
    user_id="user123",
    event_level=AuditLevel.WARNING.value
)

# 按时间范围查询
import time
events = audit_logger.query_events(
    start_time=time.time() - 86400,  # 过去24小时
    end_time=time.time()
)
```

### 获取统计信息

```python
stats = audit_logger.get_stats()
print(f"总事件数: {stats['total_events']}")
print(f"最近1小时: {stats['events_last_hour']}")
print(f"按级别统计: {stats['by_level']}")
```

### 自定义输出处理器

```python
def custom_handler(event):
    # 发送到外部系统
    import requests
    requests.post(
        "https://audit-system.example.com/events",
        json=event.to_dict()
    )

audit_logger.add_output_handler(custom_handler)
```

---

## 权限控制系统

基于角色的访问控制(RBAC)系统。

### 基本使用

```python
from src.core.safety.permission_manager import (
    PermissionManager,
    get_permission_manager,
    Role,
    Permission
)

# 获取权限管理器
perm_manager = get_permission_manager()

# 创建用户
user = await perm_manager.create_user(
    user_id="user123",
    username="张三",
    roles=[Role.USER],
    tenant_id="tenant456",
    permissions=[Permission.RESOURCE_WRITE]
)
```

### 角色管理

```python
# 分配角色
await perm_manager.assign_role("user123", Role.MANAGER)

# 撤销角色
await perm_manager.revoke_role("user123", Role.MANAGER)

# 查看用户权限
user = await perm_manager.get_user("user123")
permissions = user.get_all_permissions()
```

### 权限检查

```python
# 检查单个权限
has_perm = await perm_manager.check_permission(
    "user123",
    Permission.MEMORY_WRITE,
    tenant_id="tenant456"
)

# 检查任一权限
has_any = await perm_manager.check_any_permission(
    "user123",
    [Permission.MEMORY_READ, Permission.MEMORY_WRITE]
)

# 检查所有权限
has_all = await perm_manager.check_all_permissions(
    "user123",
    [Permission.MEMORY_READ, Permission.MEMORY_WRITE]
)
```

### 资源保护

```python
# 注册受保护资源
await perm_manager.register_resource(
    resource_id="doc123",
    resource_type="document",
    owner_id="user123",
    tenant_id="tenant456",
    required_permissions=[Permission.RESOURCE_READ],
    is_public=False
)

# 检查资源访问
can_access = await perm_manager.check_resource_access(
    "user456",
    "doc123",
    Permission.RESOURCE_READ
)
```

### 使用装饰器

```python
from src.core.safety.permission_manager import require_permission

@require_permission(Permission.SYSTEM_ADMIN)
async def admin_operation(user_id, data):
    # 需要管理员权限的操作
    return result
```

---

## 多租户支持

### 基本使用

```python
from src.core.safety.multi_tenant import (
    TenantManager,
    get_tenant_manager,
    TenantStatus,
    QuotaType
)

# 获取租户管理器
tenant_manager = get_tenant_manager()

# 创建租户
tenant = await tenant_manager.create_tenant(
    tenant_id="tenant123",
    name="ABC公司",
    status=TenantStatus.ACTIVE,
    quota={
        QuotaType.API_CALLS: 10000,
        QuotaType.USERS: 50,
        QuotaType.STORAGE: 1024 * 1024 * 1024
    }
)
```

### 配额管理

```python
# 设置配额
await tenant_manager.set_tenant_quota(
    "tenant123",
    QuotaType.API_CALLS,
    20000
)

# 检查并增加配额使用量
success = await tenant_manager.check_and_increment_quota(
    "tenant123",
    QuotaType.API_CALLS,
    amount=1
)

if not success:
    print("配额已用完！")

# 获取配额使用情况
usage = await tenant_manager.get_tenant_usage("tenant123")
for quota_type, info in usage.items():
    print(f"{quota_type}: {info['usage']}/{info['limit']} ({info['percentage']}%)")

# 重置配额
await tenant_manager.reset_tenant_quota("tenant123")
```

### 用户管理

```python
# 添加用户到租户
await tenant_manager.add_user_to_tenant("tenant123", "user123")

# 从租户移除用户
await tenant_manager.remove_user_from_tenant("tenant123", "user123")
```

### 租户状态管理

```python
# 检查租户状态
status = await tenant_manager.check_tenant_status("tenant123")

# 检查是否活跃
is_active = await tenant_manager.is_tenant_active("tenant123")

# 更新租户信息
await tenant_manager.update_tenant(
    "tenant123",
    status=TenantStatus.SUSPENDED
)
```

---

## 综合应用示例

### 示例1: 带权限检查的API端点

```python
from src.core.safety.permission_manager import (
    get_permission_manager,
    Permission
)
from src.core.monitoring.audit_logger import (
    get_audit_logger,
    AuditEventType,
    AuditLevel
)
from src.core.safety.multi_tenant import (
    get_tenant_manager,
    QuotaType
)

perm_manager = get_permission_manager()
audit_logger = get_audit_logger()
tenant_manager = get_tenant_manager()

async def process_api_request(user_id, tenant_id, request_data):
    # 1. 检查租户状态
    if not await tenant_manager.is_tenant_active(tenant_id):
        raise Exception("租户已被禁用")
    
    # 2. 检查配额
    if not await tenant_manager.check_and_increment_quota(
        tenant_id,
        QuotaType.API_CALLS
    ):
        raise Exception("API调用配额已用完")
    
    # 3. 检查权限
    if not await perm_manager.check_permission(
        user_id,
        Permission.API_ACCESS,
        tenant_id
    ):
        # 记录失败事件
        await audit_logger.log_event(
            event_type=AuditEventType.AUTHORIZATION_DENIED,
            event_level=AuditLevel.WARNING,
            user_id=user_id,
            tenant_id=tenant_id,
            status="failure"
        )
        raise Exception("权限不足")
    
    # 4. 处理请求
    result = do_something(request_data)
    
    # 5. 记录成功事件
    await audit_logger.log_event(
        event_type=AuditEventType.API_CALL,
        event_level=AuditLevel.INFO,
        user_id=user_id,
        tenant_id=tenant_id,
        status="success"
    )
    
    return result
```

### 示例2: 缓存推理 + 审计

```python
from src.core.cognition.reasoning_optimizer import (
    get_reasoning_optimizer
)
from src.core.monitoring.audit_logger import (
    get_audit_logger,
    AuditEventType,
    AuditLevel
)

optimizer = get_reasoning_optimizer()
audit_logger = get_audit_logger()

async def cached_reasoning_with_audit(user_id, input_data):
    start_time = time.time()
    
    try:
        result = await optimizer.cached_reasoning(
            complex_reasoning_function,
            "user_query",
            input_data
        )
        
        duration = time.time() - start_time
        
        await audit_logger.log_event(
            event_type=AuditEventType.RESOURCE_ACCESS,
            event_level=AuditLevel.INFO,
            user_id=user_id,
            resource_type="reasoning",
            action="推理查询",
            status="success",
            duration=duration
        )
        
        return result
        
    except Exception as e:
        await audit_logger.log_event(
            event_type=AuditEventType.API_ERROR,
            event_level=AuditLevel.ERROR,
            user_id=user_id,
            status="failure",
            error_message=str(e)
        )
        raise
```

### 示例3: 启动所有企业功能

```python
import asyncio
from src.core.monitoring.audit_logger import get_audit_logger
from src.core.cache.lru_cache import get_lru_cache
from src.core.cognition.reasoning_optimizer import get_reasoning_optimizer
from src.core.safety.permission_manager import get_permission_manager
from src.core.safety.multi_tenant import get_tenant_manager

async def initialize_enterprise_features():
    # 1. 启动审计日志
    audit_logger = get_audit_logger(log_file="audit.log")
    await audit_logger.start()
    
    # 2. 初始化LRU缓存
    lru_cache = get_lru_cache(max_size=100000, default_ttl=3600)
    
    # 3. 初始化推理优化器
    reasoning_optimizer = get_reasoning_optimizer(cache_ttl=300, max_cache_size=10000)
    
    # 4. 初始化权限系统
    perm_manager = get_permission_manager()
    
    # 5. 初始化多租户系统
    tenant_manager = get_tenant_manager()
    
    print("✅ 所有企业级功能初始化完成")
    
    return {
        'audit_logger': audit_logger,
        'lru_cache': lru_cache,
        'reasoning_optimizer': reasoning_optimizer,
        'permission_manager': perm_manager,
        'tenant_manager': tenant_manager
    }

# 运行
if __name__ == "__main__":
    asyncio.run(initialize_enterprise_features())
```

---

## API参考

### LRUCache

| 方法 | 描述 |
|------|------|
| `async get(key)` | 获取缓存值 |
| `async set(key, value, ttl)` | 设置缓存值 |
| `async delete(key)` | 删除缓存 |
| `async clear()` | 清空所有缓存 |
| `async get_stats()` | 获取统计信息 |

### ReasoningOptimizer

| 方法 | 描述 |
|------|------|
| `async cached_reasoning(func, type, *args)` | 带缓存的推理执行 |
| `get_stats()` | 获取优化统计 |
| `async clear_cache()` | 清空推理缓存 |

### AuditLogger

| 方法 | 描述 |
|------|------|
| `async log_event(...)` | 记录审计事件 |
| `query_events(...)` | 查询审计事件 |
| `get_stats()` | 获取统计信息 |
| `add_output_handler(handler)` | 添加自定义输出 |
| `async start()` | 启动审计系统 |
| `async stop()` | 停止审计系统 |

### PermissionManager

| 方法 | 描述 |
|------|------|
| `async create_user(...)` | 创建用户 |
| `async get_user(user_id)` | 获取用户 |
| `async assign_role(user_id, role)` | 分配角色 |
| `async check_permission(user_id, perm, tenant)` | 检查权限 |
| `async register_resource(...)` | 注册受保护资源 |
| `async check_resource_access(user_id, res_id)` | 检查资源访问 |

### TenantManager

| 方法 | 描述 |
|------|------|
| `async create_tenant(...)` | 创建租户 |
| `async get_tenant(tenant_id)` | 获取租户 |
| `async set_tenant_quota(...)` | 设置配额 |
| `async check_and_increment_quota(...)` | 检查并增加配额 |
| `async get_tenant_usage(tenant_id)` | 获取配额使用情况 |
| `async add_user_to_tenant(tenant_id, user_id)` | 添加用户到租户 |
| `async is_tenant_active(tenant_id)` | 检查租户状态 |
