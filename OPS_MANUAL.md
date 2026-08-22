# Bayesian-AGI-Core 运维手册

## 版本信息
- **文档版本**: v1.0.0
- **适用版本**: Bayesian-AGI-Core v1.0.0
- **创建日期**: 2026-05-21
- **最后更新**: 2026-05-21

---

## 目录

1. [系统概述](#1-系统概述)
2. [部署与配置](#2-部署与配置)
3. [日常运维流程](#3-日常运维流程)
4. [故障排查指南](#4-故障排查指南)
5. [常见问题及解决方案](#5-常见问题及解决方案)
6. [紧急响应流程](#6-紧急响应流程)
7. [监控与告警](#7-监控与告警)
8. [备份与恢复](#8-备份与恢复)

---

## 1. 系统概述

### 1.1 架构说明

Bayesian-AGI-Core 是一个基于自由能原理、主动推理与大语言模型构建的下一代认知智能体内核项目。

**核心组件**:
- **API Gateway**: 处理所有HTTP请求并路由到相应的微服务
- **LLM Service**: 处理与LLM相关的请求
- **Memory Service**: 处理与记忆相关的请求
- **Cognition Service**: 处理与认知相关的请求
- **Vision Service**: 处理与视觉相关的请求
- **Multimodal Service**: 处理多模态输入

**安全层**:
- 四层防御模型（进程隔离、资源限制、系统调用控制、网络隔离）
- 熔断器模式
- 速率限制器
- 审计日志系统

**可观测性**:
- 全链路追踪（OpenTelemetry）
- 成本监控（Token消耗、计算成本）
- Prometheus指标导出
- 告警系统（SLO/SLA）

### 1.2 服务端口

| 服务名称 | 端口 | 说明 |
|---------|------|------|
| API Gateway | 8000 | 主服务入口 |
| LLM Service | 8001 | LLM相关请求 |
| Memory Service | 8002 | 记忆相关请求 |
| Cognition Service | 8003 | 认知相关请求 |
| Vision Service | 8004 | 视觉相关请求 |
| Multimodal Service | 8005 | 多模态输入 |
| Prometheus | 9090 | 指标采集 |
| Grafana | 3000 | 可视化仪表盘 |

---

## 2. 部署与配置

### 2.1 环境要求

**硬件要求**:
- CPU: 4核以上
- 内存: 8GB以上
- 存储: 50GB以上可用空间

**软件要求**:
- Python 3.10+
- Docker 20.10+
- Docker Compose 2.0+

### 2.2 本地开发环境部署

```bash
# 克隆仓库
git clone https://github.com/your-username/bayesian-agi-core.git
cd bayesian-agi-core

# 设置环境变量
set PYTHONPATH=E:\laowut\Trae CN\bayesian-agi-core

# 安装依赖
pip install -r requirements.txt

# 启动服务
python -m src.main
```

### 2.3 Docker 部署

```bash
# 构建镜像
docker build -t bayesian-agi-core:latest .

# 运行容器
docker run -d \
  -p 8000:8000 \
  -v ./memory:/app/memory \
  -e APP_ENV=production \
  -e OLLAMA_URL=http://ollama:11434 \
  bayesian-agi-core:latest
```

### 2.4 Kubernetes 部署

```bash
# 创建命名空间
kubectl create namespace bayesian-agi

# 应用配置
kubectl apply -f k8s/configmap.yaml -n bayesian-agi
kubectl apply -f k8s/deployment.yaml -n bayesian-agi
kubectl apply -f k8s/service.yaml -n bayesian-agi
kubectl apply -f k8s/hpa.yaml -n bayesian-agi
kubectl apply -f k8s/ingress.yaml -n bayesian-agi
```

### 2.5 配置文件说明

**config.yaml**:

```yaml
server:
  host: 0.0.0.0
  port: 8000
  workers: 4

models:
  ollama_url: http://192.168.3.105:11434
  default: gemma4:e4b

security:
  level: strict

memory:
  backend: chromadb
  path: memory/
```

---

## 3. 日常运维流程

### 3.1 服务启动

**本地开发**:
```bash
python -m src.main
```

**Docker**:
```bash
docker-compose up -d
```

**Kubernetes**:
```bash
kubectl apply -f k8s/
```

### 3.2 服务停止

**本地开发**:
```bash
Ctrl + C
```

**Docker**:
```bash
docker-compose down
```

**Kubernetes**:
```bash
kubectl delete -f k8s/
```

### 3.3 服务重启

**Docker**:
```bash
docker-compose restart
```

**Kubernetes**:
```bash
kubectl rollout restart deployment bayesian-agi-core -n bayesian-agi
```

### 3.4 日志查看

**Docker**:
```bash
docker-compose logs -f
```

**Kubernetes**:
```bash
kubectl logs -n bayesian-agi -l app=bayesian-agi-core -f
```

### 3.5 健康检查

```bash
# 基础健康检查
curl http://localhost:8000/health

# 详细健康检查
curl http://localhost:8000/health/detailed

# 指标端点
curl http://localhost:8000/health/metrics
```

---

## 4. 故障排查指南

### 4.1 通用排查步骤

1. **检查服务状态**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **查看日志**:
   ```bash
   docker-compose logs -f  # Docker
   kubectl logs -n bayesian-agi -l app=bayesian-agi-core -f  # K8s
   ```

3. **检查资源使用**:
   ```bash
   docker stats  # Docker
   kubectl top pods -n bayesian-agi  # K8s
   ```

4. **检查网络连接**:
   ```bash
   curl http://localhost:8000/health  # 本地
   kubectl get svc -n bayesian-agi  # K8s Service
   ```

### 4.2 常见故障场景

#### 场景1: 服务无法启动

**现象**:
- 服务启动后立即退出
- 日志显示端口被占用

**排查步骤**:
1. 检查端口占用:
   ```bash
   netstat -ano | findstr :8000  # Windows
   lsof -i :8000  # Linux
   ```

2. 检查配置文件:
   - 确认 `config.yaml` 中的端口配置正确
   - 确认数据库连接配置正确

3. 检查依赖:
   ```bash
   pip check
   ```

#### 场景2: LLM 请求失败

**现象**:
- API 返回 500 错误
- 日志显示无法连接到 Ollama

**排查步骤**:
1. 检查 Ollama 服务状态:
   ```bash
   curl http://192.168.3.105:11434/api/tags
   ```

2. 检查网络连通性:
   ```bash
   ping 192.168.3.105
   telnet 192.168.3.105 11434
   ```

3. 检查配置文件中的 Ollama URL 是否正确

#### 场景3: 内存服务异常

**现象**:
- 记忆检索失败
- 日志显示 ChromaDB 连接错误

**排查步骤**:
1. 检查 ChromaDB 数据目录权限:
   ```bash
   ls -la memory/  # Linux
   dir memory/     # Windows
   ```

2. 检查磁盘空间:
   ```bash
   df -h  # Linux
   dir /   # Windows
   ```

3. 检查内存服务日志

#### 场景4: 高延迟

**现象**:
- API 响应时间超过 5 秒
- 用户报告服务卡顿

**排查步骤**:
1. 检查 CPU/内存使用:
   ```bash
   docker stats  # Docker
   kubectl top pods -n bayesian-agi  # K8s
   ```

2. 检查 HPA 状态:
   ```bash
   kubectl get hpa -n bayesian-agi
   ```

3. 检查延迟指标:
   ```bash
   curl http://localhost:8000/api/dashboard
   ```

#### 场景5: 熔断器打开

**现象**:
- 服务拒绝处理请求
- 日志显示 "Circuit breaker open"

**排查步骤**:
1. 检查熔断器状态:
   ```bash
   curl http://localhost:8000/api/dashboard
   ```

2. 检查上游服务状态

3. 手动重置熔断器（如需）:
   ```python
   from src.core.safety.sandbox_executor import sandbox_manager
   sandbox_manager._global_circuit_breaker._state = "closed"
   ```

---

## 5. 常见问题及解决方案

### 5.1 配置问题

**问题**: 配置文件无法加载
**原因**: 配置文件路径错误或格式错误
**解决方案**:
```bash
# 检查配置文件路径
ls config.yaml

# 检查配置文件格式
python -c "import yaml; yaml.safe_load(open('config.yaml'))"
```

### 5.2 依赖问题

**问题**: 模块导入错误
**原因**: 依赖包版本不兼容或缺失
**解决方案**:
```bash
# 重新安装依赖
pip install -r requirements.txt --force-reinstall

# 检查依赖版本
pip freeze | grep -i chromadb
```

### 5.3 网络问题

**问题**: 无法连接到外部服务
**原因**: 网络隔离或防火墙限制
**解决方案**:
```bash
# 检查网络连通性
ping api.openai.com
telnet api.openai.com 443

# 检查代理配置
echo %HTTP_PROXY%  # Windows
echo $HTTP_PROXY    # Linux
```

### 5.4 资源问题

**问题**: 内存不足
**原因**: 服务占用过多内存
**解决方案**:
```bash
# 检查内存使用
free -h  # Linux
systeminfo | findstr Memory  # Windows

# 增加内存限制（K8s）
kubectl edit deployment bayesian-agi-core -n bayesian-agi
```

### 5.5 数据问题

**问题**: 记忆数据丢失
**原因**: 数据目录被删除或损坏
**解决方案**:
```bash
# 检查数据目录
ls -la memory/vector_db/

# 从备份恢复
cp -r backup/memory/* memory/
```

---

## 6. 紧急响应流程

### 6.1 响应级别

| 级别 | 描述 | 响应时间 |
|------|------|----------|
| P0 | 系统完全不可用 | < 15分钟 |
| P1 | 核心功能故障 | < 1小时 |
| P2 | 次要功能故障 | < 4小时 |
| P3 | 性能问题或建议 | < 24小时 |

### 6.2 P0 紧急响应流程

1. **确认问题**:
   - 检查服务状态
   - 查看监控告警
   - 确认用户反馈

2. **快速恢复**:
   - 重启服务: `docker-compose restart` 或 `kubectl rollout restart`
   - 切换到备用实例
   - 启用降级模式

3. **根本原因分析**:
   - 查看日志
   - 检查资源使用
   - 检查依赖服务

4. **恢复验证**:
   - 运行健康检查
   - 验证核心功能
   - 通知用户

### 6.3 降级模式

当系统面临严重压力时，可以启用降级模式:

```python
# 启用降级模式
from src.core.safety.security_framework import SecurityFramework
framework = SecurityFramework()
framework.set_mode("degraded")
```

降级模式下:
- 禁用非核心功能
- 限制并发请求数
- 启用缓存优先策略

---

## 7. 监控与告警

### 7.1 监控仪表盘

**内置仪表盘**:
- 地址: http://localhost:8000/dashboard
- 功能: 实时监控系统性能、成本消耗、告警状态

**Grafana 仪表盘**:
- 地址: http://localhost:3000
- 用户名: admin
- 密码: admin

### 7.2 告警规则

| 告警 | 触发条件 | 级别 | 通知渠道 |
|------|----------|------|----------|
| 高延迟 | P95 > 5秒 | Critical | PagerDuty + Slack |
| 高错误率 | 错误率 > 10% | Warning | Slack |
| 高成本 | Token成本 > $10/hour | Warning | Email |
| 熔断器打开 | 熔断器状态为 open | Critical | PagerDuty |
| CPU过载 | CPU > 85% | Warning | Slack |

### 7.3 告警处理流程

1. **收到告警**: 通过 PagerDuty/Slack/Email 收到告警通知

2. **确认告警**: 登录监控系统查看详细信息

3. **定位问题**: 根据告警信息定位问题组件

4. **处理问题**: 执行相应的修复动作

5. **关闭告警**: 问题解决后关闭告警

---

## 8. 备份与恢复

### 8.1 数据备份

**手动备份**:
```bash
# 备份记忆数据
tar -czf backup_memory_$(date +%Y%m%d).tar.gz memory/

# 备份配置文件
cp config.yaml backup/config_$(date +%Y%m%d).yaml
```

**定时备份（Linux）**:
```bash
# crontab -e
0 2 * * * tar -czf /backup/backup_memory_$(date +\%Y\%m\%d).tar.gz /app/memory
```

### 8.2 数据恢复

```bash
# 停止服务
docker-compose down

# 解压备份文件
tar -xzf backup_memory_20260521.tar.gz -C /app/

# 启动服务
docker-compose up -d
```

### 8.3 灾难恢复

**步骤**:
1. 确认灾难范围
2. 停止受影响的服务
3. 从最近的备份恢复数据
4. 启动服务
5. 验证恢复结果
6. 通知用户

---

## 附录

### A. 常用命令

```bash
# 查看服务状态
curl http://localhost:8000/health

# 查看仪表盘数据
curl http://localhost:8000/api/dashboard

# 查看 Prometheus 指标
curl http://localhost:8000/health/metrics

# Docker 日志
docker-compose logs -f

# K8s 日志
kubectl logs -n bayesian-agi -l app=bayesian-agi-core -f

# K8s 资源使用
kubectl top pods -n bayesian-agi

# K8s HPA 状态
kubectl get hpa -n bayesian-agi
```

### B. 配置参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| server.host | 服务绑定地址 | 0.0.0.0 |
| server.port | 服务端口 | 8000 |
| server.workers | 工作进程数 | 4 |
| models.ollama_url | Ollama 服务地址 | http://localhost:11434 |
| models.default | 默认模型 | gemma4:e4b |
| security.level | 安全级别 | strict |
| memory.backend | 记忆后端 | chromadb |

### C. 联系人信息

| 角色 | 联系方式 | 职责 |
|------|----------|------|
| 运维值班 | ops@bayesian-agi-core.com | 24/7 紧急响应 |
| 技术负责人 | tech@bayesian-agi-core.com | 技术决策 |
| 产品负责人 | product@bayesian-agi-core.com | 产品决策 |

---

**文档版本**: v1.0.0  
**最后更新**: 2026-05-21  
**维护者**: DevOps Team