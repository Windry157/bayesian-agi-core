# DI Container Framework - API Reference

## 目录

1. [快速开始](#快速开始)
2. [核心 API](#核心-api)
3. [异常体系](#异常体系)
4. [高级特性](#高级特性)
5. [最佳实践](#最佳实践)

---

## 快速开始

### 安装

```python
from src.utils.dependency_injection_v2 import (
    DIContainer,
    ContainerBuilder,
    Scope,
    IInterceptor,
)
```

### 最简示例

```python
from typing import Protocol

# 1. 定义接口
class IService(Protocol):
    def process(self, data: str) -> str: ...

# 2. 定义实现
class ServiceImpl:
    def process(self, data: str) -> str:
        return f"processed: {data}"

# 3. 创建容器并注册
container = (
    ContainerBuilder()
    .bind(IService, ServiceImpl, Scope.SINGLETON)
    .build()
)

# 4. 获取实例
service = container.get(IService)
result = service.process("hello")
print(result)  # "processed: hello"
```

---

## 核心 API

### 2.1 ContainerBuilder

容器构建器，支持链式调用。

#### `bind(interface_type, implementation_type, scope=Scope.SINGLETON)`

绑定接口到实现。

**参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `interface_type` | `Type[T]` | 必需 | 接口类型（Protocol 或类） |
| `implementation_type` | `Type[T]` | 必需 | 实现类类型 |
| `scope` | `Scope` | `SINGLETON` | 生命周期作用域 |
| `instance` | `T` | `None` | 预创建实例（仅 SINGLETON） |
| `factory` | `Callable` | `None` | 工厂函数 |

**示例:**

```python
# 单例绑定
container.bind(IService, ServiceImpl, Scope.SINGLETON)

# 瞬态绑定（每次创建新实例）
container.bind(IService, ServiceImpl, Scope.TRANSIENT)

# 作用域绑定
container.bind(IService, ServiceImpl, Scope.SCOPED)

# 使用预创建实例
service = ServiceImpl()
container.bind(IService, ServiceImpl, Scope.SINGLETON, instance=service)

# 使用工厂函数
container.bind(
    IService,
    ServiceImpl,
    Scope.SINGLETON,
    factory=lambda: ServiceImpl(config="config")
)
```

#### `build()`

构建并返回容器实例。

**返回:** `DIContainer`

**示例:**

```python
container = ContainerBuilder().bind(IService, ServiceImpl).build()
```

#### `add_module(module)`

添加模块配置。

**参数:**

| 参数 | 类型 | 说明 |
|------|------|------|
| `module` | `IModule` | DI 模块 |

**示例:**

```python
container = ContainerBuilder().add_module(MyModule()).build()
```

#### `add_interceptor(interceptor)`

添加全局拦截器。

**参数:**

| 参数 | 类型 | 说明 |
|------|------|------|
| `interceptor` | `IInterceptor` | 拦截器实例 |

---

### 2.2 DIContainer

依赖注入容器。

#### `get(service_type)`

获取服务实例。

**参数:**

| 参数 | 类型 | 说明 |
|------|------|------|
| `service_type` | `Type[T]` | 服务类型 |

**返回:** `T` - 服务实例

**示例:**

```python
service = container.get(IService)
```

#### `get_optional(service_type)`

尝试获取可选服务。

**参数:**

| 参数 | 类型 | 说明 |
|------|------|------|
| `service_type` | `Type[T]` | 服务类型 |

**返回:** `Optional[T]` - 服务实例或 None

**示例:**

```python
service = container.get_optional(IService)
if service:
    service.process()
```

#### `create_scope()`

创建新的作用域上下文。

**返回:** `ScopeContext` - 作用域上下文管理器

**示例:**

```python
with container.create_scope() as scope:
    service = scope.get(IService)
```

#### `end_scope()`

结束当前作用域。

**示例:**

```python
container.end_scope()
```

#### `get_registered_services()`

获取所有已注册的服务。

**返回:** `List[Type]` - 服务类型列表

#### `has_service(service_type)`

检查服务是否已注册。

**参数:**

| 参数 | 类型 | 说明 |
|------|------|------|
| `service_type` | `Type` | 服务类型 |

**返回:** `bool`

#### `clear()`

清除容器中的所有注册。

**示例:**

```python
container.clear()
```

#### `validate_graph()`

验证依赖图（检查循环依赖）。

**抛出:** `CyclicDependencyException` - 如果存在循环依赖

#### `print_dependency_graph()`

打印依赖关系图。

**返回:** `str` - 依赖图的可视化字符串

---

### 2.3 Scope

生命周期作用域枚举。

```python
from src.utils.di_types import Scope

class Scope(Enum):
    SINGLETON = "singleton"   # 应用生命周期唯一
    SCOPED = "scoped"         # 作用域内唯一
    TRANSIENT = "transient"   # 每次创建新实例
```

---

## 异常体系

### 3.1 ContainerException

容器基异常。

```python
from src.utils.di_exceptions import ContainerException
```

### 3.2 MissingServiceException

服务未注册异常。

**触发条件:** 调用 `container.get()` 但服务未注册

**示例:**

```python
try:
    container.get(IService)
except MissingServiceException as e:
    print(f"Service not found: {e}")
```

### 3.3 CyclicDependencyException

循环依赖异常。

**触发条件:** 存在 A→B→C→A 的依赖链

**示例:**

```python
try:
    container.validate_graph()
except CyclicDependencyException as e:
    print(f"Cyclic dependency detected: {e}")
```

### 3.4 ScopeNotActiveException

作用域未激活异常。

**触发条件:** 在无作用域上下文时获取 SCOPED 服务

**示例:**

```python
try:
    service = container.get(ScopedService)
except ScopeNotActiveException as e:
    print(f"Scope not active: {e}")
```

### 3.5 InvalidRegistrationException

无效注册异常。

**触发条件:** 注册时提供无效参数

**示例:**

```python
try:
    container.bind(None, ServiceImpl)  # 无效参数
except InvalidRegistrationException as e:
    print(f"Invalid registration: {e}")
```

### 3.6 ResolutionException

解析异常。

**触发条件:** 无法解析依赖

**示例:**

```python
try:
    container.get(IService)
except ResolutionException as e:
    print(f"Resolution failed: {e}")
```

---

## 高级特性

### 4.1 依赖链解析

自动解析多层依赖。

```python
class IConfig:
    pass

class IDatabase:
    pass

class IUserService:
    pass

class Config:
    pass

class Database:
    def __init__(self, config: IConfig):
        self.config = config

class UserService:
    def __init__(self, db: IDatabase):
        self.db = db

# 自动解析 Config → Database → UserService
container = (
    ContainerBuilder()
    .bind(IConfig, Config, Scope.SINGLETON)
    .bind(IDatabase, Database, Scope.SINGLETON)
    .bind(IUserService, UserService, Scope.SINGLETON)
    .build()
)

user_service = container.get(IUserService)  # 自动注入
```

### 4.2 模块化配置

使用 IModule 组织服务注册。

```python
from typing import Protocol

class IModule(Protocol):
    def configure(self, builder: ContainerBuilder) -> None:
        ...

class DatabaseModule:
    def configure(self, builder: ContainerBuilder) -> None:
        builder.bind(IConfig, Config, Scope.SINGLETON)
        builder.bind(IDatabase, Database, Scope.SINGLETON)

class ServiceModule:
    def configure(self, builder: ContainerBuilder) -> None:
        builder.bind(IUserService, UserService, Scope.SINGLETON)

# 使用模块
container = (
    ContainerBuilder()
    .add_module(DatabaseModule())
    .add_module(ServiceModule())
    .build()
)
```

### 4.3 拦截器 (AOP)

使用拦截器实现横切关注点。

```python
class LoggingInterceptor(IInterceptor):
    def intercept(self, context: InvocationContext) -> Any:
        print(f"Before: {context.method_name}")
        result = context.proceed()
        print(f"After: {context.method_name}")
        return result

container = (
    ContainerBuilder()
    .bind(IService, ServiceImpl, Scope.SINGLETON)
    .add_interceptor(LoggingInterceptor())
    .build()
)
```

### 4.4 作用域隔离

使用 SCOPED 实现请求级隔离。

```python
container = (
    ContainerBuilder()
    .bind(IService, ServiceImpl, Scope.SCOPED)
    .build()
)

# 请求 1
with container.create_scope() as scope:
    service1 = scope.get(IService)

# 请求 2
with container.create_scope() as scope:
    service2 = scope.get(IService)

# service1 和 service2 是不同的实例
assert service1 is not service2
```

### 4.5 输入校验

自动校验注册参数。

```python
from src.utils.di_input_validator import InputValidator

# 校验单个参数
InputValidator.validate_interface_type(IService)
InputValidator.validate_scope(Scope.SINGLETON)

# 校验完整注册
validated = InputValidator.validate_registration(
    interface_type=IService,
    implementation_type=ServiceImpl,
    scope=Scope.SINGLETON,
)
```

---

## 最佳实践

### 5.1 依赖倒置原则

始终依赖接口而非具体实现。

```python
# ✅ 推荐
container.bind(IService, ServiceImpl)

# ❌ 避免
container.bind(ServiceImpl, ServiceImpl)
```

### 5.2 单一职责

每个服务只做一件事。

```python
# ✅ 推荐
class UserValidator:
    def validate(self, user: User) -> bool: ...

class UserRepository:
    def save(self, user: User) -> None: ...

# ❌ 避免
class UserManager:
    def validate(self, user: User) -> bool: ...
    def save(self, user: User) -> None: ...
    def send_email(self, user: User) -> None: ...
```

### 5.3 生命周期选择

| 场景 | 推荐作用域 |
|------|-----------|
| 配置、连接池 | `SINGLETON` |
| 数据库连接 | `SCOPED` |
| 临时计算器 | `TRANSIENT` |

### 5.4 循环依赖检测

在构建后验证依赖图。

```python
container = ContainerBuilder().bind(...).build()

try:
    container.validate_graph()
    print("No cyclic dependencies")
except CyclicDependencyException as e:
    print(f"Fix dependency: {e}")
```

### 5.5 异常处理

使用具体的异常类型进行捕获。

```python
try:
    service = container.get(IService)
except MissingServiceException:
    # 服务未注册
    container.bind(IService, DefaultService).build()
    service = container.get(IService)
except CyclicDependencyException:
    # 循环依赖错误
    raise
except Exception:
    # 其他错误
    raise
```

---

## 错误码参考

| 错误码 | 异常类型 | 说明 |
|--------|----------|------|
| E001 | `MissingServiceException` | 服务未注册 |
| E002 | `CyclicDependencyException` | 循环依赖 |
| E003 | `ScopeNotActiveException` | 作用域未激活 |
| E004 | `InvalidRegistrationException` | 无效注册 |
| E005 | `ResolutionException` | 依赖解析失败 |
| E006 | `InterceptorException` | 拦截器执行失败 |

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 2.2 | 2026-05-26 | 添加输入校验、循环依赖检测 |
| 2.1 | 2026-05-26 | 添加模块化、拦截器支持 |
| 2.0 | 2026-05-26 | 企业级重构 |
| 1.0 | 2026-05-26 | 基础 DI 容器 |
