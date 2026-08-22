# 企业级功能使用指南

## 概述

本文档介绍了 Bayesian-AGI-Core 中的企业级增强功能，包括分布式系统组件、高级认知推理、增强记忆系统、可视化和监控等模块。

## 目录

1. [分布式系统模块](#分布式系统模块)
2. [高级认知推理模块](#高级认知推理模块)
3. [增强记忆模块](#增强记忆模块)
4. [可视化模块](#可视化模块)
5. [监控模块](#监控模块)

---

## 分布式系统模块

### 1. Saga 编排器 (Saga Orchestrator)

Saga 编排器用于管理分布式事务，确保数据一致性。

#### 基本使用

```python
from src.core.distributed.saga_orchestrator import SagaOrchestrator

# 创建编排器
orchestrator = SagaOrchestrator()

# 创建事务
tx_id = orchestrator.create_transaction("order_processing", metadata={"order_id": "123"})

# 添加步骤
def debit_account():
    print("借记账户")
    return True

def debit_compensate():
    print("撤销借记")

orchestrator.add_step(
    transaction_id=tx_id,
    step_name="debit_account",
    execute_fn=debit_account,
    compensate_fn=debit_compensate
)

def reserve_inventory():
    print("预留库存")
    return True

def inventory_compensate():
    print("释放库存")

orchestrator.add_step(
    tx_id,
    "reserve_inventory",
    reserve_inventory,
    inventory_compensate
)

# 执行事务
result = orchestrator.execute(tx_id)
if result["success"]:
    print("事务成功!")
else:
    print("事务失败，已回滚")
```

#### 幂等性服务

```python
from src.core.distributed.saga_orchestrator import IdempotencyService

service = IdempotencyService(ttl_seconds=3600)  # 1小时过期

key = f"payment_{order_id}"
if not service.check_and_mark(key):
    # 第一次处理
    process_payment()
else:
    # 已处理过，直接返回
    return get_previous_result()
```

### 2. 事件总线 (Event Bus)

事件驱动架构的核心组件。

#### 发布订阅

```python
from src.core.distributed.event_bus import EventBus, DomainEvent

bus = EventBus()

# 订阅事件
def order_handler(event):
    print(f"收到订单事件: {event.data}")

bus.subscribe("order.created", order_handler)

# 发布事件
event = DomainEvent(
    event_type="order.created",
    source="order_service",
    data={"order_id": "123", "amount": 99.99}
)

bus.publish(event)
```

#### 死信队列 (DLQ)

```python
from src.core.distributed.event_bus import DeadLetterQueue

dlq = DeadLetterQueue()

# 添加失败事件到 DLQ
dlq.add(failed_event, reason="Processing failed after 3 retries")

# 获取待处理的失败事件
pending = dlq.get_pending()

# 标记为已处理
dlq.mark_processed(pending[0]["id"])
```

### 3. 熔断器 (Circuit Breaker)

防止级联故障的模式。

```python
from src.core.distributed.enterprise_resilience import CircuitBreaker

cb = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=30,
    half_open_max_calls=3
)

def call_external_service():
    # 调用外部服务
    return external_api.call()

try:
    result = cb.call(call_external_service)
except Exception as e:
    print(f"调用失败: {e}")

# 检查状态
print(f"熔断器状态: {cb.state}")  # closed, open, half_open
```

### 4. 事务性发件箱 (Transactional Outbox)

确保数据库操作和消息发布的原子性。

```python
from src.core.distributed.enterprise_resilience import TransactionalOutbox

outbox = TransactionalOutbox()

# 在事务中添加消息
def create_order(order_data):
    # 1. 保存订单到数据库
    order = save_to_db(order_data)
    
    # 2. 将事件添加到发件箱（本地事务）
    event = DomainEvent("order.created", "order_service", order_data)
    outbox.add(event, aggregate_id=f"order_{order.id}")
    
    return order

# 后台投递进程
def deliver_outbox_messages():
    pending = outbox.get_pending()
    for item in pending:
        try:
            event_bus.publish(item["event"])
            outbox.mark_delivered(item["id"])
        except Exception:
            pass  # 稍后重试
```

### 5. 限流组件

#### 令牌桶 (Token Bucket)

```python
from src.core.distributed.scalable_messaging import TokenBucket

bucket = TokenBucket(capacity=100, refill_rate=10)  # 每秒10个令牌

if bucket.try_consume(tokens=1):
    process_request()
else:
    return_rate_limited_response()
```

#### 漏桶 (Leaky Bucket)

```python
from src.core.distributed.scalable_messaging import LeakyBucket

bucket = LeakyBucket(capacity=100, leak_rate=5)

if bucket.try_add():
    queue_request()
else:
    drop_request()
```

### 6. 批量处理 (Batch Processor)

```python
from src.core.distributed.scalable_messaging import BatchProcessor

def process_batch(items):
    print(f"处理 {len(items)} 个项目")
    # 批量写入数据库或发送请求

processor = BatchProcessor(
    batch_size=50,
    max_wait_seconds=5,
    process_fn=process_batch
)

# 添加项目
for item in data:
    processor.add(item)

# 程序结束时刷新剩余项目
processor.flush()
```

---

## 高级认知推理模块

### 1. 树状思维推理 (Tree of Thought)

用于需要多步骤探索的复杂问题。

```python
from src.core.cognition.tree_of_thought import TreeOfThoughtReasoner, ThoughtNode

reasoner = TreeOfThoughtReasoner(max_depth=3, branching_factor=2)

def generate_thoughts(current_thought, depth):
    # 根据当前想法生成下一步的可能性
    thoughts = []
    for i in range(2):
        node = ThoughtNode(
            node_id=f"thought_{depth}_{i}",
            content=f"{current_thought} -> 分支 {i}",
            depth=depth + 1
        )
        thoughts.append(node)
    return thoughts

def evaluate_thought(node):
    # 评估想法的质量（0-1）
    return 0.7  # 示例评分

# 执行推理
tree = reasoner.reason(
    initial_thought="如何解决这个问题？",
    generate_fn=generate_thoughts,
    evaluate_fn=evaluate_thought
)

# 获取最佳路径
best_path = tree.get_best_path()
for node in best_path:
    print(f"{node.content} (score: {node.score})")
```

### 2. 图推理 (Graph Reasoning)

用于分析实体间关系的推理。

```python
from src.core.cognition.graph_reasoning import (
    GraphReasoningEngine,
    Entity,
    Relation
)

engine = GraphReasoningEngine()

# 添加实体
alice = Entity("e1", "Alice", "Person")
bob = Entity("e2", "Bob", "Person")
charlie = Entity("e3", "Charlie", "Person")
company = Entity("c1", "TechCorp", "Company")

engine.add_entity(alice)
engine.add_entity(bob)
engine.add_entity(charlie)
engine.add_entity(company)

# 添加关系
engine.add_relation(Relation("e1", "e2", "friends_with", 0.9))
engine.add_relation(Relation("e2", "e3", "colleague", 0.8))
engine.add_relation(Relation("e1", "c1", "works_at", 1.0))
engine.add_relation(Relation("e2", "c1", "works_at", 1.0))

# 查找路径
paths = engine.find_paths("e1", "e3", max_depth=3)
for path in paths:
    print(f"路径分数: {path.score}")
    for node in path.nodes:
        print(f"  - {node.name}")
```

### 3. 因果推理 (Causal Reasoning)

用于分析因果关系。

```python
from src.core.cognition.causal_reasoning import (
    CausalReasoningEngine,
    CausalGraph,
    CausalVariable,
    CausalStrength
)

engine = CausalReasoningEngine()

# 添加变量
temperature = CausalVariable("temp", "温度", [0, 100])
humidity = CausalVariable("humidity", "湿度", [0, 100])
rain = CausalVariable("rain", "降雨", [0, 1])
comfort = CausalVariable("comfort", "舒适度", [0, 1])

engine.add_variable(temperature)
engine.add_variable(humidity)
engine.add_variable(rain)
engine.add_variable(comfort)

# 添加因果关系
engine.add_causal_relation("temp", "comfort", CausalStrength.MODERATE)
engine.add_causal_relation("humidity", "comfort", CausalStrength.MODERATE)
engine.add_causal_relation("rain", "humidity", CausalStrength.STRONG)

# 推理
inference = engine.perform_inference(
    evidence={"rain": 1},  # 观察到降雨
    target=["comfort"]     # 预测舒适度
)

print(f"预测舒适度: {inference['comfort']}")
```

### 4. 高级推理协调器

自动选择最佳推理策略。

```python
from src.core.cognition.advanced_reasoning_coordinator import AdvancedReasoningCoordinator

coordinator = AdvancedReasoningCoordinator()

# 自动选择策略并推理
question = "解决这个问题需要哪些步骤？"
result = coordinator.reason(question)

print(f"使用策略: {result['strategy']}")
print(f"推理结果: {result['conclusion']}")
```

---

## 增强记忆模块

### 1. 记忆压缩 (Memory Compressor)

减少冗余记忆，优化存储空间。

```python
from src.core.memory.memory_compressor import MemoryCompressor

compressor = MemoryCompressor(similarity_threshold=0.85)

# 准备记忆列表
memories = [
    {
        "id": "m1",
        "content": "机器学习是AI的分支",
        "importance": 0.8,
        "created_at": "...",
        "access_count": 10
    },
    {
        "id": "m2", 
        "content": "ML是人工智能的一个分支领域",
        "importance": 0.7,
        "created_at": "...",
        "access_count": 5
    },
    # ... 更多记忆
]

# 压缩记忆
result = compressor.compress(
    memories,
    strategy="hybrid",  # similarity, importance, hybrid
    keep_ratio=0.7
)

print(f"压缩前: {result.original_count}, 压缩后: {result.compressed_count}")
print(f"压缩率: {result.compression_ratio:.1%}")
```

### 2. 记忆生命周期管理

管理短期、中期、长期记忆的迁移。

```python
from src.core.memory.lifecycle_manager import (
    MemoryLifecycleManager,
    MemoryLayer,
    LayerConfig
)

manager = MemoryLifecycleManager()

# 或使用自定义配置
custom_configs = {
    MemoryLayer.SHORT_TERM: LayerConfig(
        capacity=100,
        retention_hours=24,
        promotion_threshold=0.7,
        demotion_threshold=0.0
    ),
    MemoryLayer.MEDIUM_TERM: LayerConfig(
        capacity=500,
        retention_hours=168,  # 7天
        promotion_threshold=0.85,
        demotion_threshold=0.3
    ),
    MemoryLayer.LONG_TERM: LayerConfig(
        capacity=2000,
        retention_hours=8760,  # 1年
        promotion_threshold=1.0,
        demotion_threshold=0.1
    )
}
manager = MemoryLifecycleManager(configs=custom_configs)

# 处理记忆生命周期
memories_by_layer = {
    MemoryLayer.SHORT_TERM: short_term_memories,
    MemoryLayer.MEDIUM_TERM: medium_term_memories,
    MemoryLayer.LONG_TERM: long_term_memories
}

changes = manager.process_lifecycle(memories_by_layer)

# 应用变更
for mem, from_layer, to_layer in changes["promoted"]:
    move_to_layer(mem, to_layer)
for mem, layer in changes["deleted"]:
    delete_memory(mem)
```

### 3. 索引优化 (Index Optimizer)

优化向量搜索索引配置。

```python
from src.core.memory.index_optimizer import (
    IndexOptimizer,
    IndexType,
    IndexConfig
)

optimizer = IndexOptimizer()

# 获取推荐配置
config = optimizer.get_recommended_config(
    num_vectors=500000,
    query_performance_requirement="balanced"  # speed, balanced, memory
)

print(f"推荐 HNSW M: {config.hnsw_m}")
print(f"推荐 efConstruction: {config.hnsw_ef_construction}")
print(f"推荐 efSearch: {config.hnsw_ef_search}")

# 优化现有索引（模拟）
result = optimizer.optimize(index_object, method="auto")
print(f"延迟改进: {result.query_latency_improvement:.1%}")
```

---

## 可视化模块

### 推理过程可视化

```python
from src.core.visualization.reasoning_visualizer import (
    ReasoningVisualizer,
    VisualizationNode,
    VisualizationEdge,
    VisualizationType
)

visualizer = ReasoningVisualizer()

# 1. 树状可视化
nodes = [
    VisualizationNode("root", "问题根节点", "root", 1.0),
    VisualizationNode("c1", "方案A", "thought", 0.8),
    VisualizationNode("c2", "方案B", "thought", 0.6),
    VisualizationNode("c1a", "方案A-1", "thought", 0.9),
]

edges = [
    VisualizationEdge("root", "c1", "探索", 0.8),
    VisualizationEdge("root", "c2", "探索", 0.6),
    VisualizationEdge("c1", "c1a", "细化", 0.9),
]

tree_data = visualizer.create_tree_data(nodes, edges, title="推理树")

# 2. 图可视化
graph_data = visualizer.create_graph_data(entities, relations, title="知识图谱")

# 3. 图表可视化
chart_data = visualizer.create_chart_data(
    data_points=[
        {"x": "Step 1", "y": 0.5},
        {"x": "Step 2", "y": 0.7},
        {"x": "Step 3", "y": 0.9}
    ],
    title="置信度变化",
    x_label="步骤",
    y_label="置信度"
)

# 导出为 JSON
json_str = visualizer.export_json(tree_data)
```

---

## 监控模块

### 1. 指标收集

```python
from src.core.monitoring.metrics import MetricsCollector

collector = MetricsCollector()

# 记录指标
collector.record_metric("cpu_usage", 65.5, tags={"host": "server-1"})
collector.record_metric("memory_usage", 4096, unit="MB")

# 记录性能
collector.record_performance(
    operation="db_query",
    duration=0.125,  # 秒
    success=True
)

# 获取统计
stats = collector.get_statistics("db_query")
print(f"平均延迟: {stats['avg_duration']:.3f}s")
print(f"P95: {stats['p95']:.3f}s")
print(f"成功率: {stats['success_rate']:.1%}")

# 获取最近指标
recent = collector.get_recent_metrics("cpu_usage", limit=100)
```

### 2. 监控仪表盘

```python
from src.core.monitoring.dashboard import MonitoringDashboard, get_dashboard

# 获取单例
dashboard = get_dashboard()

# 获取系统概览
overview = dashboard.get_overview()
print(f"总请求数: {overview['total_requests']}")
print(f"运行时间: {overview['uptime']}")
print(f"错误率: {overview['error_rate']:.1%}")

# 获取告警
alerts = dashboard.get_alerts()
for alert in alerts:
    print(f"[{alert['level']}] {alert['message']}")

# 获取详细指标
metrics = dashboard.get_metrics(time_range="1h")
```

---

## 最佳实践

### 分布式系统

1. **总是使用幂等性**: 对所有可能重复的操作使用 `IdempotencyService`
2. **设置合理的超时**: 熔断器和 Saga 步骤都应有超时机制
3. **监控 DLQ**: 定期检查和处理死信队列中的消息
4. **批量操作**: 对数据库和网络操作使用 `BatchProcessor` 提高效率

### 认知推理

1. **选择合适策略**: 使用 `AdvancedReasoningCoordinator` 自动选择，或根据问题类型手动选择
   - 多步骤探索 → Tree of Thought
   - 关系查询 → Graph Reasoning
   - 因果分析 → Causal Reasoning
2. **限制深度**: 树状推理设置合理的 `max_depth` 避免无限扩展
3. **缓存结果**: 对重复查询的推理结果进行缓存

### 记忆系统

1. **定期压缩**: 根据使用频率每周/每月运行一次记忆压缩
2. **监控生命周期**: 观察各层记忆的分布，调整配置参数
3. **索引优化**: 向量数量大幅变化时重新评估索引配置

### 监控

1. **关键指标**: 确保监控所有外部 API 调用、数据库操作
2. **设置告警**: 对错误率、延迟异常配置告警
3. **保留历史**: 保存足够长时间的指标数据用于趋势分析
