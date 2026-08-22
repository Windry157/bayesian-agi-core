# DI Container Framework - 运维手册

## 目录

1. [部署指南](#部署指南)
2. [健康检查](#健康检查)
3. [监控指标](#监控指标)
4. [故障排查](#故障排查)
5. [性能调优](#性能调优)
6. [应急预案](#应急预案)

---

## 部署指南

### 前提条件

- Python 3.10+
- 依赖包已安装（见 requirements.txt）

### 部署步骤

#### 1. 代码部署

```bash
# 拉取代码
git clone <repository>
cd bayesian-agi-core

# 安装依赖
pip install -r requirements.txt

# 运行测试
python -m pytest tests/ -v
```

#### 2. 环境配置

创建 `config.yaml`：

```yaml
app:
  name: bayesian-agi-core
  environment: production
  debug: false

server:
  host: 0.0.0.0
  port: 8001

logging:
  level: INFO
  format: json
  file: logs/app.log
```

#### 3. 启动服务

```bash
# 使用 uvicorn
python -m uvicorn src.main:app --host 0.0.0.0 --port 8001

# 或使用 Docker
docker build -t bayesian-agi-core .
docker run -p 8001:8001 bayesian-agi-core
```

---

## 健康检查

### 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 基础健康检查 |
| `/health/ready` | GET | 就绪检查（依赖服务） |
| `/health/live` | GET | 存活检查 |

### 健康检查实现

```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "bayesian-agi-core",
        "version": "2.2.0"
    }

@router.get("/health/ready")
async def readiness_check():
    try:
        # 检查容器状态
        container.validate_graph()
        return {"status": "ready"}
    except Exception as e:
        return {"status": "not_ready", "reason": str(e)}

@router.get("/health/live")
async def liveness_check():
    return {"status": "alive"}
```

### 手动健康检查

```bash
# 基础检查
curl http://localhost:8001/health

# 详细检查
curl http://localhost:8001/health/ready
```

---

## 监控指标

### Prometheus 指标

框架内置 Prometheus 指标导出。

| 指标名 | 类型 | 说明 |
|--------|------|------|
| `di_container_resolutions_total` | Counter | 依赖解析总次数 |
| `di_container_resolution_errors_total` | Counter | 解析错误总次数 |
| `di_container_resolution_duration_seconds` | Histogram | 解析耗时分布 |
| `di_container_instances_total` | Gauge | 当前实例数 |
| `di_container_scope_depth` | Gauge | 当前作用域深度 |

### 查看指标

```bash
# Prometheus 格式
curl http://localhost:8001/metrics

# 示例输出
# HELP di_container_resolutions_total Total resolutions
# TYPE di_container_resolutions_total counter
di_container_resolutions_total{service="IService"} 12345
```

### Grafana 仪表板

建议创建以下仪表板：

1. **容器健康概览**
   - 总解析次数
   - 错误率
   - P99 延迟

2. **作用域监控**
   - 活跃作用域数量
   - 每个作用域的实例数

3. **性能趋势**
   - 解析延迟 P50/P95/P99
   - 吞吐量变化

---

## 故障排查

### 常见问题

#### 问题 1: 服务未找到

**症状:**
```
MissingServiceException: Service 'IService' not found in container
```

**排查步骤:**

1. 检查服务是否注册：
```python
if container.has_service(IService):
    print("Service registered")
else:
    print("Service NOT registered")
```

2. 查看已注册服务：
```python
print(container.get_registered_services())
```

3. 检查依赖图：
```python
print(container.print_dependency_graph())
```

**解决方案:**
```python
# 添加缺失的绑定
container = (
    ContainerBuilder()
    .bind(IService, ServiceImpl, Scope.SINGLETON)  # 添加这行
    .build()
)
```

#### 问题 2: 循环依赖

**症状:**
```
CyclicDependencyException: Cycle detected: A -> B -> C -> A
```

**排查步骤:**

1. 查看循环路径：
```python
try:
    container.validate_graph()
except CyclicDependencyException as e:
    print(f"Cycle: {e.cycle}")
```

2. 可视化依赖图：
```python
print(container.print_dependency_graph())
```

**解决方案:**
- 重新设计依赖关系
- 引入接口打破循环
- 使用事件/消息传递

#### 问题 3: 作用域错误

**症状:**
```
ScopeNotActiveException: Scope is not active for SCOPED service
```

**排查步骤:**

1. 检查是否在作用域内：
```python
with container.create_scope() as scope:
    # 在作用域内
    service = scope.get(IService)
```

2. 确保作用域正确结束：
```python
container.end_scope()  # 显式结束
# 或使用 with 语句自动结束
```

**解决方案:**
```python
# 使用 with 确保正确管理
with container.create_scope() as scope:
    service = scope.get(IService)
    # 作用域自动结束
```

#### 问题 4: 性能下降

**症状:**
- 响应时间增加
- CPU 使用率升高

**排查步骤:**

1. 检查实例数量：
```python
stats = container.get_stats()
print(f"Instances: {stats['total_instances']}")
```

2. 分析延迟分布：
```bash
curl http://localhost:8001/metrics | grep di_container_resolution_duration
```

3. 检查是否有内存泄漏：
```python
# 运行内存测试
python tests/test_2_2_stress.py
```

**解决方案:**
- 优化依赖链深度
- 增加 SINGLETON 使用
- 重构重型服务

---

## 性能调优

### 1. 优化实例数量

**问题:** 瞬态服务过多导致 GC 压力

**解决方案:**
```python
# 优先使用单例
.bind(IDatabase, PostgresDatabase, Scope.SINGLETON)
.bind(ICache, RedisCache, Scope.SINGLETON)

# 减少瞬态使用
.bind(IValidator, EmailValidator, Scope.SINGLETON)  # 替代 TRANSIENT
```

### 2. 延迟加载

**问题:** 启动时加载过多服务

**解决方案:**
```python
# 使用工厂函数延迟创建
container.bind(
    IHeavyService,
    HeavyService,
    Scope.SINGLETON,
    factory=lambda: HeavyService(lazy_init=True)
)
```

### 3. 缓存依赖解析

**问题:** 重复解析相同依赖

**解决方案:**
```python
# 框架已内置缓存，无需额外配置
# 解析结果自动缓存
service1 = container.get(IService)  # 首次解析
service2 = container.get(IService)  # 使用缓存
```

### 4. 并发优化

**问题:** 多线程访问容器

**解决方案:**
```python
# 框架已内置线程锁
# 建议使用连接池管理并发访问
```

---

## 应急预案

### 预案 1: 服务启动失败

**触发条件:**
- 容器初始化失败
- 依赖服务连接失败

**处理步骤:**

1. 检查日志：
```bash
tail -f logs/app.log | grep ERROR
```

2. 验证配置：
```bash
python -c "from src.utils.config import load_config; print(load_config())"
```

3. 检查依赖：
```bash
python -c "from src.utils.dependency_injection_v2 import *; print('Import OK')"
```

4. 重启服务：
```bash
# 优雅重启
kill -SIGTERM <pid>
python -m uvicorn src.main:app
```

### 预案 2: 内存泄漏

**触发条件:**
- 内存持续增长
- GC 频率异常

**处理步骤:**

1. 诊断：
```python
# 添加内存监控
import psutil
process = psutil.Process()
print(f"Memory: {process.memory_info().rss / 1024 / 1024} MB")
```

2. 分析：
```bash
# 运行内存测试
python tests/test_2_2_stress.py
```

3. 修复：
- 清理未使用的绑定
- 检查缓存实现
- 优化作用域管理

### 预案 3: 循环依赖

**触发条件:**
- 服务调用超时
- CPU 100%

**处理步骤:**

1. 立即检查：
```bash
python -c "
from src.utils.dependency_injection_v2 import *
container = ContainerBuilder().bind(...).build()
container.validate_graph()
"
```

2. 识别问题：
```python
print(container.print_dependency_graph())
```

3. 修复设计（见上文"故障排查"）

---

## 运维命令

### 查看容器状态

```bash
python -c "
from src.utils.dependency_injection_v2 import *
container = ContainerBuilder().bind(...).build()
print('Registered:', container.get_registered_services())
print('Graph:', container.print_dependency_graph())
"
```

### 运行测试

```bash
# 单元测试
python -m pytest tests/ -v

# 压力测试
python tests/test_2_2_stress.py

# 性能测试
python tests/test_singleton_performance.py
```

### 清理环境

```bash
# 清理日志
rm -rf logs/*.log

# 清理缓存
find . -type d -name __pycache__ -exec rm -rf {} +

# 重置测试环境
python -c "from src.utils.dependency_injection_v2 import *; ContainerBuilder().build().clear()"
```

---

## 联系支持

- **文档**: `docs/DI_FRAMEWORK_API.md`
- **用户指南**: `docs/DI_FRAMEWORK_USER_GUIDE.md`
- **设计决策**: `docs/adr/`
- **测试套件**: `tests/`

---

## 版本升级

### 升级检查清单

- [ ] 阅读发布说明
- [ ] 运行完整测试套件
- [ ] 更新文档
- [ ] 灰度部署
- [ ] 监控指标观察
- [ ] 回滚计划准备
