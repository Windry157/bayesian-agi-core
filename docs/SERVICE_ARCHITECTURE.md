# Bayesian-AGI-Core 服务架构说明
# Service Architecture Documentation

## 📋 概述

本文档说明 `main.py` 和 `api_gateway.py` 两个服务入口的职责和用途。

## 🏗️ 服务入口对比

### `src/main.py` - 主应用入口 (Primary Application)

**职责**: 单体架构的主应用入口

**用途**:
- 用于**单体架构**模式运行
- 提供完整的 Bayesian-AGI 智能助理功能
- 包含 WebSocket、REST API、微信/飞书集成
- 集成所有核心服务（LLM、Memory、Cognition）
- 已启用健壮性特性（熔断器、限流、结构化日志）

**启动方式**:
```bash
python -c "import uvicorn; uvicorn.run('src.main:app', host='0.0.0.0', port=8001)"
```

**特点**:
- ✅ 功能完整，适合开发和小型部署
- ✅ 包含所有核心功能
- ✅ 已集成健壮性特性
- ❌ 所有服务运行在一个进程中

---

### `src/api_gateway.py` - API网关入口 (Gateway Application)

**职责**: API 网关模式的服务入口

**用途**:
- 用于**微服务架构**模式运行
- 作为统一的 API 网关
- 代理请求到后端微服务
- 负载均衡和请求路由
- 支持服务发现

**启动方式**:
```bash
python -c "import uvicorn; uvicorn.run('src.api_gateway:app', host='0.0.0.0', port=8000)"
```

**特点**:
- ✅ 可作为微服务的统一入口
- ✅ 支持请求路由和负载均衡
- ✅ 便于服务扩展
- ❌ 需要配合其他微服务运行

---

## 🔄 何时使用哪个？

### 使用 `main.py` 的场景

1. **开发环境**: 快速开发和测试
2. **小型部署**: 单机或小规模部署
3. **演示用途**: 快速演示功能
4. **单体优先**: 不想引入微服务复杂度

```bash
# 开发模式
cd E:\laowut\Trae CN\bayesian-agi-core
python -c "import uvicorn; uvicorn.run('src.main:app', host='0.0.0.0', port=8001, reload=True)"
```

### 使用 `api_gateway.py` 的场景

1. **微服务架构**: 大规模分布式部署
2. **负载均衡**: 需要多实例扩展
3. **服务隔离**: 不同服务独立部署
4. **API 管理**: 需要统一网关

```bash
# 网关模式
cd E:\laowut\Trae CN\bayesian-agi-core
python -c "import uvicorn; uvicorn.run('src.api_gateway:app', host='0.0.0.0', port=8000)"
```

---

## 📊 功能对比

| 功能 | main.py | api_gateway.py |
|------|---------|---------------|
| WebSocket | ✅ | ✅ |
| REST API | ✅ | ✅ |
| 微信集成 | ✅ | ✅ |
| 飞书集成 | ✅ | ✅ |
| LLM 服务 | ✅ | ✅ |
| Memory 服务 | ✅ | ✅ |
| Cognition 服务 | ✅ | ✅ |
| 熔断器 | ✅ | ✅ |
| 限流 | ✅ | ✅ |
| 结构化日志 | ✅ | ✅ |
| Prometheus 指标 | ✅ | ✅ |
| 健康检查 | ✅ | ✅ |
| OpenClaw 兼容 | ✅ | ✅ |

---

## 🐳 Docker Compose 部署

在 `docker-compose.yml` 中，根据架构模式选择：

### 单体模式 (使用 main.py)
```yaml
services:
  bayesian-agi:
    build: .
    ports:
      - "8001:8001"
    environment:
      - OLLAMA_URL=http://host.docker.internal:11434
```

### 微服务模式 (使用 api_gateway.py)
```yaml
services:
  api-gateway:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - llm-service
      - memory-service
      - cognition-service

  llm-service:
    build: .
    command: python -m src.llm_service

  memory-service:
    build: .
    command: python -m src.memory_service

  cognition-service:
    build: .
    command: python -m src.cognition_service
```

---

## 🔧 配置

两个入口都使用相同的 `config.yaml`:

```bash
# 设置 WebSocket 认证密钥（生产环境必须修改！）
export WEBSOCKET_AUTH_SECRET="your-secure-secret-key"

# 启动服务
python -c "import uvicorn; uvicorn.run('src.main:app', host='0.0.0.0', port=8001)"
```

---

## 📝 建议

### 开发环境
使用 `main.py`，方便调试和快速迭代。

### 生产环境
根据规模选择：
- **小型 (< 100 用户)**: 使用 `main.py`
- **中型 (100-1000 用户)**: 使用 `api_gateway.py` + 微服务
- **大型 (> 1000 用户)**: 完整微服务架构 + Kubernetes

### 迁移路径
```
单体 (main.py)
    ↓
API Gateway (api_gateway.py)
    ↓
微服务分离 (独立 LLM/Memory/Cognition 服务)
    ↓
Kubernetes 集群
```

---

## 🚨 常见问题

### Q: 应该使用哪个？
A: 开发和小型部署用 `main.py`，大规模分布式部署用 `api_gateway.py`。

### Q: 两个可以同时运行吗？
A: 可以，但需要不同的端口。建议通过环境变量或命令行参数配置端口。

### Q: WebSocket 认证密钥在哪里设置？
A: 在 `config.yaml` 的 `websocket.auth_secret` 字段，或通过环境变量 `WEBSOCKET_AUTH_SECRET`。

### Q: 如何切换架构？
A: 修改启动命令中的 `src.main:app` 或 `src.api_gateway:app`。

---

## 📚 相关文档

- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - 项目总体概述
- [ROBUSTNESS_GUIDE.md](ROBUSTNESS_GUIDE.md) - 健壮性功能使用指南
- [RUNBOOK.md](RUNBOOK.md) - 生产故障响应手册

---

*Last Updated: 2026-05-26*
