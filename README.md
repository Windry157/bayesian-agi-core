# Bayesian-AGI-Core

基于自由能原理、主动推理与大语言模型构建的下一代认知智能体内核。

## 核心特性

- **生成式世界模型**：利用LLM动态评估似然概率并生成无限的行动空间
- **主动推理**：基于香农熵和预期信息增益，驱动Agent主动探索环境
- **双系统架构**：System 1（基于ChromaDB的毫秒级语义缓存）和System 2（基于LLM的批处理推理）
- **动态剪枝**：自动忽略低概率假设，降低算力消耗
- **多模态融合**：支持视觉信息和语言理解的融合
- **知识图谱记忆**：构建和管理实体与关系的知识网络

## 技术栈

- **后端框架**：FastAPI
- **数据存储**：
  - ChromaDB（向量存储）
  - JSON文件（知识图谱持久化）
- **图像处理**：Pillow (PIL) + Base64
- **并发处理**：asyncio
- **模型集成**：Ollama本地模型、云端API

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置

编辑 `config.yaml` 文件，设置模型和服务器配置：

```yaml
app:
  debug: false
  name: Bayesian-AGI-Core
  version: 1.0.0

models:
  default: "minimax-m2.7:cloud"
  ollama_url: http://localhost:11434
  refresh_interval: 300

  providers:
    ollama:
      enabled: true
      models:
        - deepseek-r1:7b
        - gemma3:4b
        - qwen3-vl:4b

    openai:
      enabled: false
      api_key: ""
      models:
        - gpt-3.5-turbo
        - gpt-4

server:
  host: 0.0.0.0
  port: 8000
  workers: 4

memory:
  directory: memory
  vector_model: "ollama:nomic-embed-text"
```

### 启动服务

```bash
python -m src.main
```

或

```bash
uvicorn src.main:app --reload
```

### 访问API文档

启动服务后，访问 `http://127.0.0.1:8000/docs` 查看API文档。

## 核心功能

### 1. 健康检查
- **端点**：`GET /health`
- **功能**：检查服务状态

### 2. 模型管理
- **端点**：`GET /api/models`
- **功能**：获取可用模型列表

### 3. 记忆管理
- **端点**：`POST /api/memory`
- **功能**：添加记忆

- **端点**：`GET /api/memory/search`
- **功能**：检索记忆

### 4. 决策系统
- **端点**：`POST /api/decision`
- **功能**：基于主动推理做出决策

## 项目结构

```
bayesian-agi-core/
├── src/
│   ├── core/
│   │   ├── llm/          # 语言模型集成
│   │   ├── memory/       # 记忆系统
│   │   ├── cognition/    # 认知核心
│   │   ├── skills/       # 技能模块
│   │   └── tools/        # 工具模块
│   ├── services/         # 外部服务集成
│   ├── api/              # API路由
│   ├── utils/            # 工具函数
│   └── main.py           # 应用主入口
├── configs/              # 配置文件
├── data/                 # 数据文件
├── docs/                 # 文档
├── memory/               # 记忆存储
├── models/               # 模型文件
├── plugins/              # 插件
├── tests/                # 测试
├── scripts/              # 脚本
├── requirements.txt      # 依赖
├── config.yaml           # 配置
└── README.md             # 项目说明
```

## 设计理念

1. **自由能原理**：最小化预测误差，优化世界模型
2. **主动推理**：基于信息增益驱动探索
3. **双系统架构**：快速响应与深度思考的结合
4. **知识图谱**：结构化存储和管理知识
5. **向量存储**：高效的语义检索

## 未来规划

- [ ] 实现多模态输入（图像、语音）
- [ ] 集成更多LLM提供商
- [ ] 优化记忆系统性能
- [ ] 实现更复杂的认知推理
- [ ] 开发可视化工具

## 贡献

欢迎提交Issue和Pull Request！

## 许可证

MIT License
