# ADR-0002: DI Container Framework 设计决策

## 状态

**已接受** - 2026-05-26

## 背景

我们需要为 Bayesian-AGI-Core 项目构建一个轻量级、高性能的依赖注入容器，用于管理服务间的依赖关系，提高代码的可测试性和可维护性。

## 决策

### 1. 选择 Python 原生实现

**选项:**
- A. 复用现有框架（dependency-injector, punq）
- B. 自研 DI 容器

**决策:** B - 自研 DI 容器

**理由:**
- 现有框架体积大、依赖多
- 需要与项目特定功能集成
- 学习自定义实现有助于团队成长
- 项目规模可控，无需企业级框架

### 2. 支持的生命周期类型

**选项:**
- A. 仅 SINGLETON
- B. SINGLETON + TRANSIENT
- C. SINGLETON + TRANSIENT + SCOPED

**决策:** C - 完整三种生命周期

**理由:**
- Web 应用需要请求级隔离（SCOPED）
- 工具类适合瞬态创建（TRANSIENT）
- 配置服务适合单例（SINGLETON）
- 完整支持满足各种场景

### 3. 依赖解析策略

**选项:**
- A. 手动注册所有依赖
- B. 自动扫描 + 自动注入
- C. 半自动（注册 + 自动注入构造函数）

**决策:** C - 半自动模式

**理由:**
- 显式注册更清晰
- 自动注入构造函数减少样板代码
- 支持循环依赖检测
- 性能可控

### 4. 模块化设计

**选项:**
- A. 单一注册表
- B. 模块化配置

**决策:** B - 模块化配置

**理由:**
- 大型项目需要分组管理
- 便于团队协作
- 支持功能开关
- 便于测试隔离

### 5. 异常处理策略

**选项:**
- A. 通用异常
- B. 细粒度异常体系

**决策:** B - 细粒度异常体系

**理由:**
- 便于错误处理
- 提供清晰的错误信息
- 便于日志记录和监控
- 遵循 Python 最佳实践

### 6. 拦截器/AOP 支持

**选项:**
- A. 不支持 AOP
- B. 基础拦截器
- C. 完整 AOP 框架

**决策:** B - 基础拦截器

**理由:**
- 满足横切关注点需求（日志、监控）
- 实现复杂度可控
- 不过度设计
- 便于后续扩展

## 实现细节

### 核心组件

```
DI Container
├── ContainerBuilder     # 构建器
├── DIContainer           # 容器核心
├── ServiceDescriptor     # 服务描述符
├── Scope                 # 作用域枚举
├── IModule               # 模块接口
└── IInterceptor          # 拦截器接口
```

### 类图

```python
ContainerBuilder
├── bind(interface, impl, scope) -> self
├── add_module(module) -> self
├── add_interceptor(interceptor) -> self
└── build() -> DIContainer

DIContainer
├── get(type) -> instance
├── get_optional(type) -> Optional[instance]
├── create_scope() -> ScopeContext
├── validate_graph() -> bool
└── get_registered_services() -> List[type]

ServiceDescriptor
├── interface_type: Type
├── implementation_type: Type
├── scope: Scope
├── instance: Optional[instance]
└── factory: Optional[Callable]
```

### 性能特性

| 操作 | 时间复杂度 | 说明 |
|------|----------|------|
| get() | O(1) | 已缓存直接返回 |
| 首次解析 | O(n) | n = 依赖深度 |
| 注册 | O(1) | 字典插入 |
| 循环检测 | O(n²) | DFS 遍历 |

### 线程安全

- 全局容器状态使用 `threading.Lock`
- 单例实例本身无需加锁
- 支持多线程并发访问

## 后果

### 正面

- 轻量级，无外部依赖
- API 简洁易用
- 支持企业级特性（模块、拦截器）
- 便于测试和扩展

### 负面

- 需要团队维护
- 缺少一些高级特性（如属性注入）
- 性能不如 C 扩展实现

### 中性

- 学习曲线（团队需要理解 DI 概念）
- 需要遵守使用规范

## 替代方案

### dependency-injector

**优点:** 功能完整，文档丰富

**缺点:**
- 依赖外部包
- 与项目集成需要适配
- 体积较大

### punq

**优点:** 轻量级

**缺点:**
- 功能有限
- 不支持 SCOPED
- 社区较小

## 验收标准

- [x] 支持 SINGLETON/SCOPED/TRANSIENT 生命周期
- [x] 自动解析构造函数依赖
- [x] 循环依赖检测
- [x] 模块化配置
- [x] 拦截器支持
- [x] 完整的异常体系
- [x] 线程安全
- [x] 压力测试通过

## 后续行动

1. 考虑添加属性注入支持
2. 评估性能优化空间
3. 收集使用反馈
4. 完善文档

## 参考

- [Martin Fowler - Inversion of Control](https://martinfowler.com/articles/injection.html)
- [Microsoft - Dependency Injection](https://docs.microsoft.com/en-us/dotnet/core/extensions/dependency-injection)
- [Python typing.Protocol](https://docs.python.org/3/library/typing.html#typing.Protocol)
