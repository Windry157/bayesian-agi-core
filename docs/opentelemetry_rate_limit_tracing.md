# OpenTelemetry 限流追踪配置指南

## 概述

本指南介绍如何配置 OpenTelemetry 来追踪限流触发的链路，帮助您在生产环境中监控和分析速率限制事件。

## 配置步骤

### 1. 安装依赖

```bash
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-console
```

### 2. 初始化 OpenTelemetry

创建配置文件 `src/core/observability/otel_config.py`:

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
from opentelemetry.sdk.resources import Resource

def init_otel(service_name: str = "bayesian-agi-core"):
    """初始化 OpenTelemetry 配置"""
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    
    # 添加控制台导出器（用于调试）
    processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    
    # 设置全局追踪器提供者
    trace.set_tracer_provider(provider)
    
    return trace.get_tracer(service_name)
```

### 3. 在应用启动时初始化

```python
from src.core.observability.otel_config import init_otel
from src.core.observability.rate_limiter import setup_default_rate_limits

# 初始化 OpenTelemetry
init_otel("bayesian-agi-core")

# 设置默认限流规则
setup_default_rate_limits()
```

## 追踪属性说明

### 限流检查 Span

| 属性 | 说明 |
|------|------|
| `rate_limit.key` | 限流规则的键名 |
| `rate_limit.blocked` | 是否被限流 |
| `rate_limit.blocked_by` | 被哪种策略限流 (token_bucket/sliding_window) |
| `rate_limit.retry_after` | 需要等待的秒数 |

### 令牌桶限流 Span

| 属性 | 说明 |
|------|------|
| `rate_limit.type` | 限流类型 (token_bucket) |
| `rate_limit.capacity` | 令牌桶容量 |
| `rate_limit.rate` | 令牌生成速率 |
| `rate_limit.tokens` | 当前令牌数 |
| `rate_limit.retry_after` | 需要等待的秒数 |
| `rate_limit.blocked` | 是否被限流 |

### 滑动窗口限流 Span

| 属性 | 说明 |
|------|------|
| `rate_limit.type` | 限流类型 (sliding_window) |
| `rate_limit.window_seconds` | 窗口大小（秒） |
| `rate_limit.max_requests` | 窗口内最大请求数 |
| `rate_limit.current_count` | 当前窗口内请求数 |
| `rate_limit.retry_after` | 需要等待的秒数 |
| `rate_limit.blocked` | 是否被限流 |

## 测试验证

创建测试脚本 `scripts/test_otel_rate_limit.py`:

```python
import asyncio
import sys
sys.path.insert(0, "e:\\laowut\\Trae CN\\bayesian-agi-core")

from src.core.observability.otel_config import init_otel
from src.core.observability.rate_limiter import (
    rate_limiter,
    rate_limit,
    RateLimitExceededError
)

# 初始化 OpenTelemetry
init_otel("rate-limit-test")

# 配置严格的限流规则
rate_limiter.configure_token_bucket("test_api", capacity=2, rate=1)
rate_limiter.configure_sliding_window("test_api", window_seconds=5, max_requests=3)

@rate_limit("test_api")
async def test_endpoint():
    return "success"

async def main():
    # 发送多个请求触发限流
    for i in range(10):
        try:
            result = await test_endpoint()
            print(f"请求 {i+1}: {result}")
        except RateLimitExceededError as e:
            print(f"请求 {i+1}: 限流触发，需要等待 {e.retry_after:.2f}s")
            await asyncio.sleep(e.retry_after + 0.1)

if __name__ == "__main__":
    asyncio.run(main())
```

## 生产环境配置

### 添加 Jaeger 导出器（推荐）

```bash
pip install opentelemetry-exporter-jaeger-thrift
```

```python
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

def init_otel_with_jaeger(service_name: str = "bayesian-agi-core"):
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    
    # Jaeger 导出器
    jaeger_exporter = JaegerExporter(
        agent_host_name="localhost",
        agent_port=6831,
    )
    
    processor = BatchSpanProcessor(jaeger_exporter)
    provider.add_span_processor(processor)
    
    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)
```

### 添加 Prometheus 指标（可选）

```bash
pip install opentelemetry-exporter-prometheus
```

## 可视化分析

### Jaeger UI

在 Jaeger 中搜索 `rate_limit` 相关的 span，可以看到：

1. **限流触发频率**：通过搜索 `rate_limit.blocked=true` 查看被限流的请求
2. **限流类型分布**：分析是令牌桶还是滑动窗口触发的限流
3. **重试等待时间**：查看 `rate_limit.retry_after` 属性分析等待时间分布
4. **热点接口识别**：通过 `rate_limit.key` 识别哪些接口被频繁限流

### 日志集成

配合日志系统，可以通过以下关键字搜索限流事件：

```bash
# 搜索所有限流触发日志
grep "限流触发" application.log

# 搜索特定接口的限流
grep "memory_write" application.log | grep "限流触发"
```

## 注意事项

1. **性能影响**：OpenTelemetry 追踪会有轻微性能开销，建议在生产环境使用采样策略
2. **采样策略**：可以配置采样率来平衡追踪完整性和性能
3. **安全考虑**：确保追踪数据不包含敏感信息
4. **存储策略**：根据需要配置合适的追踪数据保留时间

## 故障排查

### 问题：追踪数据未显示

1. 确认 OpenTelemetry 已正确初始化
2. 检查是否安装了必要的依赖
3. 确认导出器配置正确
4. 检查日志中是否有相关错误信息

### 问题：限流触发但追踪缺失

1. 确认 `HAS_OPENTELEMETRY` 为 `True`
2. 检查 RateLimiter 的 `_tracer` 是否为 `None`
3. 确认在限流触发前已初始化 OpenTelemetry

---

**总结**：通过配置 OpenTelemetry，您可以完整追踪限流触发的链路，实现：
- 实时监控限流事件
- 分析限流原因和频率
- 识别热点接口
- 优化限流策略
