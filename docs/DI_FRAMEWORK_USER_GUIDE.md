# DI Container Framework - 用户手册

## 目录

1. [概述](#概述)
2. [快速开始](#快速开始)
3. [核心概念](#核心概念)
4. [使用指南](#使用指南)
5. [常见问题](#常见问题)

---

## 概述

### 什么是 DI 容器？

依赖注入（Dependency Injection）容器是一个用于管理对象依赖关系的框架。它可以帮助您：

- **解耦**：将对象的创建和使用分离
- **可测试**：轻松替换依赖进行单元测试
- **可维护**：集中管理对象生命周期
- **可扩展**：通过模块化配置组织代码

### 为什么使用 DI 容器？

| 传统方式 | 使用 DI 容器 |
|----------|--------------|
| 手动创建依赖 | 自动注入 |
| 硬编码依赖 | 配置化依赖 |
| 难以测试 | 易于 Mock |
| 代码耦合 | 松耦合 |

---

## 快速开始

### 环境要求

- Python 3.10+

### 安装

框架已集成到项目中，直接导入使用：

```python
from src.utils.dependency_injection_v2 import (
    DIContainer,
    ContainerBuilder,
    Scope,
)
```

### 5 分钟上手

#### 步骤 1: 定义接口

```python
from typing import Protocol

class IEmailService(Protocol):
    def send(self, to: str, subject: str, body: str) -> bool: ...
```

#### 步骤 2: 定义实现

```python
class SmtpEmailService:
    def send(self, to: str, subject: str, body: str) -> bool:
        print(f"Sending email to {to}: {subject}")
        return True
```

#### 步骤 3: 注册服务

```python
container = (
    ContainerBuilder()
    .bind(IEmailService, SmtpEmailService, Scope.SINGLETON)
    .build()
)
```

#### 步骤 4: 使用服务

```python
email_service = container.get(IEmailService)
email_service.send("user@example.com", "Hello", "World!")
```

---

## 核心概念

### 生命周期作用域

| 作用域 | 说明 | 使用场景 |
|--------|------|----------|
| `SINGLETON` | 应用唯一实例 | 配置服务、数据库连接池 |
| `SCOPED` | 请求/流程内唯一 | 用户上下文、事务 |
| `TRANSIENT` | 每次新建 | 工具类、DTO |

### 依赖解析

容器自动分析构造函数参数并注入依赖：

```python
class UserService:
    def __init__(self, db: IDatabase, cache: ICache):
        self.db = db
        self.cache = cache

# 容器自动注入 db 和 cache
container.get(UserService)
```

### 模块化配置

将相关服务组织到模块中：

```python
class DatabaseModule:
    def configure(self, builder):
        builder.bind(IDatabase, PostgresDatabase)
        builder.bind(ICache, RedisCache)

class BusinessModule:
    def configure(self, builder):
        builder.bind(IUserService, UserService)

container = (
    ContainerBuilder()
    .add_module(DatabaseModule())
    .add_module(BusinessModule())
    .build()
)
```

---

## 使用指南

### 场景 1: Web 应用

#### 用户服务配置

```python
from typing import Protocol

class IDatabase(Protocol):
    def query(self, sql: str) -> list: ...

class IUserRepository(Protocol):
    def find_by_id(self, user_id: int) -> dict: ...

class PostgresDatabase:
    def query(self, sql: str) -> list:
        # 实际数据库查询
        return []

class UserRepository:
    def __init__(self, db: IDatabase):
        self.db = db

    def find_by_id(self, user_id: int) -> dict:
        return self.db.query(f"SELECT * FROM users WHERE id = {user_id}")

# 配置
container = (
    ContainerBuilder()
    .bind(IDatabase, PostgresDatabase, Scope.SINGLETON)
    .bind(IUserRepository, UserRepository, Scope.SCOPED)
    .build()
)

# 使用（请求处理）
def handle_request(request):
    with container.create_scope() as scope:
        repo = scope.get(IUserRepository)
        user = repo.find_by_id(request.user_id)
        return user
```

### 场景 2: 单元测试

#### 使用 Mock 替换

```python
from unittest.mock import MagicMock

def test_user_service():
    # 创建 Mock
    mock_db = MagicMock()
    mock_db.query.return_value = [{"id": 1, "name": "Test"}]

    # 手动注入（测试用）
    container = (
        ContainerBuilder()
        .bind(IDatabase, lambda: mock_db)  # 工厂函数返回 Mock
        .bind(IUserRepository, UserRepository)
        .build()
    )

    # 测试
    repo = container.get(IUserRepository)
    user = repo.find_by_id(1)

    assert user["name"] == "Test"
    mock_db.query.assert_called_once()
```

### 场景 3: 微服务通信

```python
class IHttpClient(Protocol):
    def get(self, url: str) -> dict: ...

class IAuthService(Protocol):
    def authenticate(self, token: str) -> dict: ...

class HttpClient:
    def get(self, url: str) -> dict:
        # HTTP 请求
        return {}

class AuthService:
    def __init__(self, http: IHttpClient):
        self.http = http

    def authenticate(self, token: str) -> dict:
        return self.http.get(f"http://auth/api/verify?token={token}")

# 微服务容器
container = (
    ContainerBuilder()
    .bind(IHttpClient, HttpClient, Scope.SINGLETON)
    .bind(IAuthService, AuthService, Scope.SCOPED)
    .build()
)
```

### 场景 4: 插件系统

```python
class IPlugin(Protocol):
    name: str
    def execute(self, context: dict) -> None: ...

class LoggingPlugin:
    name = "logging"

    def execute(self, context: dict) -> None:
        print(f"Log: {context}")

class MetricsPlugin:
    name = "metrics"

    def execute(self, context: dict) -> None:
        # 记录指标
        pass

class PluginManager:
    def __init__(self, plugins: list[IPlugin]):
        self.plugins = plugins

    def run_all(self, context: dict):
        for plugin in self.plugins:
            plugin.execute(context)

# 插件容器
container = (
    ContainerBuilder()
    .bind(IPlugin, LoggingPlugin, Scope.TRANSIENT)
    .bind(IPlugin, MetricsPlugin, Scope.TRANSIENT)
    .bind(PluginManager, PluginManager, Scope.SINGLETON)
    .build()
)

manager = container.get(PluginManager)
manager.run_all({"event": "user_login"})
```

---

## 常见问题

### Q1: 如何处理可选依赖？

使用 `get_optional()` 方法：

```python
service = container.get_optional(IDatabase)
if service:
    result = service.query("SELECT 1")
```

### Q2: 如何调试依赖问题？

使用依赖图可视化：

```python
container = ContainerBuilder().bind(...).build()
print(container.print_dependency_graph())
```

输出示例：

```
Dependency Graph:
├── IDatabase
│   └── DatabaseImpl
├── IUserService
│   └── UserService
│       └── IDatabase (injected)
```

### Q3: 如何处理循环依赖？

**重新设计**：循环依赖通常意味着设计问题。

```python
# ❌ 循环依赖
class A:
    def __init__(self, b: B): self.b = b

class B:
    def __init__(self, a: A): self.a = a

# ✅ 重构：引入接口
class IA:
    def do_something(self): ...

class IB:
    def set_a(self, a: IA): ...

class A(IA):
    def __init__(self, b: IB):
        self.b = b
```

### Q4: 如何选择作用域？

| 问题 | 答案 |
|------|------|
| 状态需要跨请求共享？ | `SINGLETON` |
| 每个请求需要独立状态？ | `SCOPED` |
| 每次调用需要新实例？ | `TRANSIENT` |

### Q5: 如何添加日志/监控？

使用拦截器：

```python
import time
from src.utils.dependency_injection_v2 import IInterceptor, InvocationContext

class TimingInterceptor(IInterceptor):
    def intercept(self, context: InvocationContext) -> Any:
        start = time.perf_counter()
        result = context.proceed()
        elapsed = time.perf_counter() - start
        print(f"{context.method_name}: {elapsed*1000:.2f}ms")
        return result

container = (
    ContainerBuilder()
    .bind(IUserService, UserService)
    .add_interceptor(TimingInterceptor())
    .build()
)
```

---

## 性能提示

1. **优先使用 SINGLETON**：减少对象创建开销
2. **避免深度依赖链**：超过 5 层考虑重构
3. **使用工厂函数**：延迟创建重型对象
4. **定期验证**：使用 `validate_graph()` 检查循环依赖

---

## 错误处理

所有 DI 容器异常都继承自 `ContainerException`：

```python
from src.utils.di_exceptions import (
    MissingServiceException,
    CyclicDependencyException,
    InvalidRegistrationException,
)

try:
    container.get(IService)
except MissingServiceException:
    print("服务未注册，请先绑定")
except CyclicDependencyException:
    print("存在循环依赖，请检查设计")
except Exception as e:
    print(f"未知错误: {e}")
```

---

## 下一步

- 查看 [API 参考文档](./DI_FRAMEWORK_API.md) 获取完整 API
- 查看 [运维手册](./RUNBOOK.md) 了解部署和监控
- 查看 [设计决策记录](./adr/0002-di-container-design.md) 了解设计理念
