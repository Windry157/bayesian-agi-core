# Bayesian-AGI-Core 部署文档

## 1. 环境要求

- Docker and Docker Compose
- Python 3.14+
- Ollama (用于本地LLM集成)

## 2. 部署步骤

### 2.1 克隆代码库

```bash
git clone <repository-url>
cd bayesian-agi-core
```

### 2.2 配置环境变量

复制`.env.example`文件并根据需要修改配置：

```bash
cp .env.example .env
# 编辑.env文件，根据需要修改配置
```

### 2.3 启动服务

使用Docker Compose启动所有服务：

```bash
docker-compose up -d
```

这将启动以下服务：
- API Gateway (8000)
- LLM Service (8001)
- Memory Service (8002)
- Cognition Service (8003)
- Vision Service (8004)
- Multimodal Service (8005)
- RabbitMQ (5672, 15672)
- PostgreSQL (5432)
- Prometheus (9090)
- Grafana (3000)

### 2.4 验证服务

检查所有服务是否正常运行：

```bash
docker-compose ps
```

访问API Gateway的健康检查端点：

```bash
curl http://localhost:8000/health
```

### 2.5 访问服务

- API Gateway: http://localhost:8000
- API文档: http://localhost:8000/docs
- Grafana: http://localhost:3000 (默认用户名/密码: admin/admin)
- Prometheus: http://localhost:9090
- RabbitMQ管理界面: http://localhost:15672 (默认用户名/密码: guest/guest)

## 3. 本地开发

### 3.1 安装依赖

```bash
pip install -r requirements.txt
```

### 3.2 启动单个服务

启动API Gateway：

```bash
python -m src.api_gateway
```

启动LLM服务：

```bash
python -m src.llm_service
```

启动Memory服务：

```bash
python -m src.memory_service
```

启动Cognition服务：

```bash
python -m src.cognition_service
```

启动Vision服务：

```bash
python -m src.vision_service
```

启动Multimodal服务：

```bash
python -m src.multimodal_service
```

### 3.3 运行测试

```bash
python test_api.py
python test_llm_service.py
python test_cognition_service.py
python test_vision_service.py
python test_multimodal_service.py
```

## 4. 配置说明

### 4.1 环境变量

| 环境变量 | 描述 | 默认值 |
|---------|------|--------|
| API_GATEWAY_PORT | API Gateway端口 | 8000 |
| LLM_SERVICE_PORT | LLM服务端口 | 8001 |
| MEMORY_SERVICE_PORT | Memory服务端口 | 8002 |
| COGNITION_SERVICE_PORT | Cognition服务端口 | 8003 |
| VISION_SERVICE_PORT | Vision服务端口 | 8004 |
| MULTIMODAL_SERVICE_PORT | Multimodal服务端口 | 8005 |
| OLLAMA_URL | Ollama服务URL | http://localhost:11434 |
| RABBITMQ_URL | RabbitMQ URL | amqp://guest:guest@localhost:5672 |
| POSTGRES_HOST | PostgreSQL主机 | localhost |
| POSTGRES_PORT | PostgreSQL端口 | 5432 |
| POSTGRES_DATABASE | PostgreSQL数据库 | bayesian_agi |
| POSTGRES_USER | PostgreSQL用户 | postgres |
| POSTGRES_PASSWORD | PostgreSQL密码 | postgres |
| PROMETHEUS_PORT | Prometheus端口 | 9090 |
| GRAFANA_PORT | Grafana端口 | 3000 |
| GRAFANA_ADMIN_PASSWORD | Grafana管理员密码 | admin |

### 4.2 配置文件

项目使用`config.yaml`文件进行配置，主要配置项包括：

- app: 应用基本配置
- models: LLM模型配置
- server: 服务器配置
- memory: 记忆系统配置

## 5. 故障排查

### 5.1 常见问题

1. **服务启动失败**
   - 检查Docker Compose日志：`docker-compose logs <service-name>`
   - 检查端口是否被占用
   - 检查环境变量配置

2. **Ollama连接失败**
   - 确保Ollama服务已启动：`ollama serve`
   - 检查Ollama URL配置

3. **PostgreSQL连接失败**
   - 检查PostgreSQL服务是否正常运行
   - 检查PostgreSQL配置

4. **RabbitMQ连接失败**
   - 检查RabbitMQ服务是否正常运行
   - 检查RabbitMQ配置

### 5.2 日志管理

查看服务日志：

```bash
docker-compose logs <service-name>
```

查看所有服务日志：

```bash
docker-compose logs
```

## 6. 生产环境部署

### 6.1 安全配置

- 使用HTTPS加密通信
- 配置CORS来源为具体域名
- 实现认证和授权机制
- 定期更新依赖包

### 6.2 性能优化

- 调整服务实例数量
- 优化数据库配置
- 启用缓存
- 使用负载均衡

### 6.3 监控和告警

- 配置Grafana dashboard
- 设置监控告警
- 定期备份数据

## 7. 升级步骤

1. 停止服务：`docker-compose down`
2. 拉取最新代码：`git pull`
3. 更新依赖：`docker-compose build`
4. 启动服务：`docker-compose up -d`
