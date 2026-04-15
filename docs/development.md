# Bayesian-AGI-Core 开发指南

## 1. 开发环境设置

### 1.1 安装依赖

```bash
pip install -r requirements.txt
```

### 1.2 配置开发环境

复制`.env.example`文件并根据需要修改配置：

```bash
cp .env.example .env
# 编辑.env文件，根据需要修改配置
```

### 1.3 启动开发服务

使用以下命令启动开发服务：

```bash
# 启动API Gateway
python -m src.api_gateway

# 启动LLM服务
python -m src.llm_service

# 启动Memory服务
python -m src.memory_service

# 启动Cognition服务
python -m src.cognition_service

# 启动Vision服务
python -m src.vision_service

# 启动Multimodal服务
python -m src.multimodal_service
```

## 2. 代码结构

```
bayesian-agi-core/
├── src/                # 源代码
│   ├── core/           # 核心功能
│   │   ├── cognition/  # 认知系统
│   │   ├── learning/   # 学习系统
│   │   ├── llm/        # LLM集成
│   │   ├── memory/     # 记忆系统
│   │   ├── multimodal/ # 多模态处理
│   │   ├── plugins/    # 插件系统
│   │   ├── assistant.py     # 智能助理
│   │   ├── interfaces.py     # 接口定义
│   │   └── monitoring.py     # 监控系统
│   ├── plugins/        # 插件
│   ├── utils/          # 工具函数
│   │   ├── config.py         # 配置管理
│   │   ├── data_cache.py     # 数据缓存
│   │   ├── http_client.py    # HTTP客户端
│   │   ├── message_queue.py  # 消息队列
│   │   └── model_cache.py    # 模型缓存
│   ├── api_gateway.py      # API网关
│   ├── cognition_service.py # 认知服务
│   ├── llm_service.py       # LLM服务
│   ├── main.py              # 主服务
│   ├── memory_service.py     # 记忆服务
│   ├── multimodal_service.py # 多模态服务
│   └── vision_service.py     # 视觉服务
├── sdk/                # SDK
│   └── python/         # Python SDK
├── docs/               # 文档
├── memory/             # 记忆存储
├── .env.example        # 环境变量示例
├── config.yaml         # 配置文件
├── docker-compose.yml  # Docker Compose配置
├── prometheus.yml      # Prometheus配置
├── requirements.txt    # 依赖包
└── test_*.py           # 测试文件
```

## 3. 核心模块开发

### 3.1 记忆系统

记忆系统位于`src/core/memory/`目录，包括：

- `memory_system.py`: 记忆系统主类，管理短期、中期和长期记忆
- `vector_store.py`: 向量存储，用于中期记忆
- `long_term_memory.py`: 长期记忆，使用PostgreSQL
- `knowledge_graph.py`: 知识图谱，用于存储实体和关系

### 3.2 认知系统

认知系统位于`src/core/cognition/`目录，包括：

- `bayesian_brain.py`: 贝叶斯大脑，处理概率推理
- `cognition_coordinator.py`: 认知协调器，协调不同认知模块
- `system1.py`: 系统1，快速、直觉的认知
- `system2.py`: 系统2，慢速、分析的认知
- `chain_of_thought.py`: 思维链，用于复杂推理

### 3.3 多模态处理

多模态处理位于`src/core/multimodal/`目录，包括：

- `multimodal_processor.py`: 多模态处理器，处理不同类型的输入

### 3.4 LLM集成

LLM集成位于`src/core/llm/`目录，包括：

- `base_llm.py`: LLM基类
- `ollama_service.py`: Ollama服务集成

## 4. 微服务开发

### 4.1 创建新服务

1. 在`src/`目录下创建新的服务文件，如`new_service.py`
2. 实现服务的基本结构，包括：
   - FastAPI应用初始化
   - CORS配置
   - 健康检查端点
   - 监控端点
   - 业务逻辑端点
3. 在`docker-compose.yml`中添加新服务的配置
4. 在`Dockerfile.new-service`中添加新服务的构建配置
5. 在API Gateway中添加新服务的路由

### 4.2 服务间通信

服务间通信可以通过以下方式：

1. **HTTP请求**：使用`src/utils/http_client.py`中的`http_client_manager`
2. **消息队列**：使用`src/utils/message_queue.py`中的`message_queue_manager`

## 5. 插件系统

### 5.1 创建插件

1. 在`src/plugins/`目录下创建新的插件文件，如`my_plugin.py`
2. 实现`PluginInterface`接口：
   ```python
   from src.core.plugins.plugin_interface import PluginInterface

   class MyPlugin(PluginInterface):
       def initialize(self, config):
           """初始化插件"""
           pass

       def process(self, data):
           """处理数据"""
           return data

       def get_name(self):
           """获取插件名称"""
           return "My Plugin"
   ```
3. 在`src/core/plugins/plugin_manager.py`中注册插件

### 5.2 使用插件

```python
from src.core.plugins.plugin_manager import plugin_manager

# 初始化插件管理器
plugin_manager.initialize(config)

# 处理数据
result = plugin_manager.process("my_plugin", data)
```

## 6. 测试开发

### 6.1 单元测试

在项目根目录创建测试文件，如`test_memory.py`，测试记忆系统的功能：

```python
import unittest
from src.core.memory.memory_system import MemorySystem

class TestMemorySystem(unittest.TestCase):
    def test_add_memory(self):
        memory_system = MemorySystem()
        memory_id = memory_system.add_memory("测试记忆")
        self.assertIsNotNone(memory_id)

if __name__ == "__main__":
    unittest.main()
```

### 6.2 集成测试

创建集成测试文件，如`test_integration.py`，测试多个模块的协作：

```python
import requests

# 测试添加记忆和检索记忆
def test_memory_integration():
    # 添加记忆
    add_response = requests.post("http://localhost:8000/api/memory", json={"content": "测试记忆"})
    assert add_response.status_code == 200
    
    # 检索记忆
    search_response = requests.get("http://localhost:8000/api/memory/search", params={"query": "测试"})
    assert search_response.status_code == 200
    assert len(search_response.json()["memories"]) > 0

if __name__ == "__main__":
    test_memory_integration()
    print("集成测试通过")
```

## 7. 代码风格

### 7.1 Python代码风格

- 遵循PEP 8代码风格
- 使用4空格缩进
- 类名使用大驼峰命名法
- 函数和变量名使用小写+下划线命名法
- 模块名使用小写+下划线命名法
- 每行不超过80个字符
- 使用类型注解
- 添加适当的文档字符串

### 7.2 文档风格

- 使用Markdown格式
- 为每个模块、类和函数添加文档字符串
- 文档字符串使用Google风格

## 8. 扩展指南

### 8.1 添加新的LLM模型

1. 在`src/core/llm/`目录下创建新的LLM实现文件，如`openai_service.py`
2. 实现`BaseLLM`接口
3. 在`src/core/assistant.py`中注册新的LLM服务

### 8.2 添加新的存储后端

1. 在`src/core/memory/`目录下创建新的存储实现文件，如`mongodb_memory.py`
2. 实现相应的存储接口
3. 在`memory_system.py`中集成新的存储后端

### 8.3 添加新的认知模块

1. 在`src/core/cognition/`目录下创建新的认知模块文件，如`planning.py`
2. 实现相应的认知功能
3. 在`cognition_coordinator.py`中集成新的认知模块

## 9. 调试技巧

### 9.1 日志调试

使用Python标准日志模块进行调试：

```python
import logging

logger = logging.getLogger(__name__)
logger.info("调试信息")
logger.error("错误信息")
```

### 9.2 断点调试

使用Python的`pdb`模块进行断点调试：

```python
import pdb

# 在需要调试的地方添加
pdb.set_trace()
```

### 9.3 Docker调试

查看Docker容器的日志：

```bash
docker-compose logs <service-name>
```

进入Docker容器进行调试：

```bash
docker exec -it <container-id> bash
```

## 10. 贡献指南

### 10.1 代码提交

- 提交前运行测试：`python -m pytest`
- 提交前检查代码风格：`flake8`
- 提交信息使用清晰的格式：`[模块] 描述`

### 10.2 分支管理

- `main`：主分支，稳定版本
- `develop`：开发分支，新功能开发
- `feature/xxx`：特性分支，特定功能开发
- `bugfix/xxx`：修复分支，bug修复

### 10.3 代码审查

- 提交Pull Request前进行自我审查
- 确保代码符合项目风格
- 提供清晰的PR描述
- 响应代码审查反馈
