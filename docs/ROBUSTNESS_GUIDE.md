# Bayesian-AGI-Core 健壮性指南

## 📋 概述

本文档介绍了 Bayesian-AGI-Core 项目中实现的健壮性功能，包括：

- 结构化日志系统
- 熔断器模式
- 速率限制器
- 请求追踪
- 全局异常处理

这些功能让系统从"能跑"的 MVP 变成"能稳定运行"的生产级应用。

## 🏗️ 架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Gateway                               │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 1. Trace ID Middleware  (请求追踪)                           │  │
│  │ 2. Rate Limiter         (速率限制)                           │  │
│  │ 3. Circuit Breaker      (熔断器)                             │  │
│  │ 4. Business Logic       (业务逻辑)                           │  │
│  │ 5. Global Exception Handler (全局异常处理)                   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 📝 结构化日志系统

### 功能特性

- 自动生成 trace ID 追踪请求
- 支持 JSON 和文本格式输出
- 日志文件轮转（大小和时间）
- 多命名空间支持

### 使用示例

```python
from src.utils.structured_logging import (
    get_logger, info, warning, error,
    get_trace_id, set_trace_id, new_trace_id
)

# 获取命名空间日志器
logger = get_logger("my_module")

# 记录日志
info("操作成功")
warning("警告信息")
error("错误信息")

# 追踪 ID 管理
trace_id = new_trace_id()  # 生成新 ID
current_trace = get_trace_id()  # 获取当前 ID
```

### 配置

日志文件存储在 `logs/` 目录：

- `app.log` - 主日志文件（JSON格式）
- `daily.log` - 每日日志（文本格式）

## 🔌 熔断器模式

### 功能特性

- 失败阈值检测
- 自动恢复机制
- 状态监控
- 降级支持

### 使用示例

```python
from src.utils.circuit_breaker import (
    get_circuit_breaker, circuit_breaker
)

# 方法 1：直接使用
breaker = get_circuit_breaker(
    'ollama_service',
    failure_threshold=3,  # 连续 3 次失败熔断
    recovery_timeout=30,  # 30 秒后尝试恢复
    fallback_function=lambda: "fallback"
)

result = breaker.execute(llm_call, prompt="hello")

# 方法 2：装饰器
@circuit_breaker('llm_generation')
def generate_text(prompt):
    return llm_call(prompt)
```

### 状态

| 状态 | 说明 |
|------|------|
| CLOSED | 正常运行，允许请求 |
| OPEN | 熔断，拒绝所有请求 |
| HALF_OPEN | 恢复中，允许部分请求 |

## ⚡ 速率限制器

### 功能特性

- 滑动窗口算法
- 令牌桶算法
- 固定窗口算法
- 灵活配置

### 使用示例

```python
from src.utils.rate_limiter import (
    get_rate_limiter_manager, rate_limit
)

manager = get_rate_limiter_manager()

# 注册限流器
manager.register_limiter(
    'per_user',
    'sliding_window',
    requests=100,
    period_seconds=60,
    burst_size=20
)

# 获取令牌
allowed = await manager.acquire('per_user', user_id)

# 获取统计信息
stats = manager.get_stats('per_user', user_id)
```

### 算法对比

| 算法 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| 滑动窗口 | 精确，平滑 | 内存消耗大 | 高频限流 |
| 令牌桶 | 支持突发，灵活 | 实现复杂 | API网关 |
| 固定窗口 | 简单高效 | 边界问题 | 低精度限流 |

## 🔍 请求追踪

### 功能特性

- 自动生成 trace ID
- 通过 HTTP 头传递
- 日志关联
- 响应头返回

### 使用方式

```python
# 客户端发送请求时可附带 trace ID
headers = {
    "X-Trace-ID": "user-provided-trace-id"
}

# 服务器返回响应时包含 trace ID
response.headers["X-Trace-ID"]  # 服务端生成或透传
response.headers["X-Process-Time"]  # 处理耗时（毫秒）
```

## 🛡️ 全局异常处理

### 功能特性

- 统一错误响应格式
- 完整错误日志
- 安全返回（隐藏敏感信息）
- Trace ID 包含

### 响应格式

```json
{
    "status": "error",
    "code": 500,
    "message": "Internal server error",
    "trace_id": "abc123..."
}
```

## 🔧 API 端点

### 熔断器管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/circuit-breakers` | GET | 获取所有熔断器状态 |
| `/api/circuit-breakers/{name}/reset` | POST | 重置指定熔断器 |
| `/api/circuit-breakers/reset-all` | POST | 重置所有熔断器 |

### 限流器管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/rate-limiters` | GET | 获取所有限流器列表 |
| `/api/rate-limiters/{name}/stats` | GET | 获取限流器统计 |

### 健康检查

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/health/robustness` | GET | 健壮性系统健康状态 |

## 📊 监控与运维

### 健康检查响应

```json
{
    "status": "healthy",  // healthy 或 degraded
    "circuit_breakers": {
        "total": 3,
        "open": 0,
        "closed": 3,
        "details": {}
    },
    "rate_limiters": {
        "total": 2,
        "details": {}
    }
}
```

### 告警规则

| 指标 | 阈值 | 级别 |
|------|------|------|
| 熔断器 OPEN 数量 | >0 | WARNING |
| 熔断比例 | >50% | CRITICAL |
| 限流拒绝率 | >20% | WARNING |

## 🧪 测试

运行健壮性功能测试：

```bash
python scripts/test_robustness.py
```

## 📈 性能优化建议

1. 熔断器恢复超时不应太短（建议 >30秒）
2. 限流器配置应与业务需求匹配
3. 日志级别生产环境设置为 INFO 或 WARNING
4. 定期清理日志文件（已自动处理）

## 🔗 集成到现有代码

### 1. 导入模块

```python
from src.utils.structured_logging import get_logger
from src.utils.circuit_breaker import circuit_breaker
from src.utils.rate_limiter import rate_limit
```

### 2. 添加追踪 ID

```python
# 在请求开始时设置
new_trace_id()
```

### 3. 使用熔断器保护外部调用

```python
@circuit_breaker('external_api')
def call_external_service():
    pass
```

### 4. 添加限流

```python
@rate_limit('per_user')
def handle_user_request(user_id):
    pass
```

## 📚 参考资料

- [熔断器模式](https://martinfowler.com/bliki/CircuitBreaker.html)
- [令牌桶算法](https://en.wikipedia.org/wiki/Token_bucket)
- [结构化日志最佳实践](https://cloud.google.com/logging/docs/structured-logging)
