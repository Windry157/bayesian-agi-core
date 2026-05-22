# Bayesian AGI Core - Code Wiki

## 1. 项目概述

### 1.1 项目简介

**项目名称**: bayesian-agi-core

**项目定位**: 基于自由能原理（Free Energy Principle）、主动推理（Active Inference）与大语言模型（LLM）构建的下一代认知智能体内核。

**核心目标**: 打造一个能够进行自主感知、推理、决策和学习的人工通用智能系统，使其具备类人认知能力。

### 1.2 技术背景

| 理论基础 | 描述 |
|---------|------|
| **自由能原理** | 由Karl Friston提出，认为所有自适应系统都会最小化其内部状态的自由能，即对环境的预测误差 |
| **主动推理** | 智能体通过行动来改变环境，使感官输入与内部模型预测保持一致 |
| **大语言模型** | 提供强大的语言理解和生成能力，作为智能体的"思维"引擎 |

### 1.3 项目愿景

- 构建一个统一的认知架构
- 实现自主学习和知识发现
- 支持多模态感知与交互
- 具备长期记忆与持续学习能力

---

## 2. 架构设计

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                     Bayesian AGI Core                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │   Perception│    │   Inference │    │   Action    │        │
│  │   感知模块  │───>│   推理模块  │───>│   行动模块  │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│         │                  │                  │                 │
│         v                  v                  v                 │
│  ┌─────────────────────────────────────────────┐               │
│  │            Internal Model                   │               │
│  │           (内部生成模型)                     │               │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐       │               │
│  │  │  Prior  │ │ Likelihood│ │   Bayes  │      │               │
│  │  │  先验   │ │   似然   │ │ 推理引擎 │      │               │
│  │  └─────────┘ └─────────┘ └─────────┘       │               │
│  └─────────────────────────────────────────────┘               │
│         │                  │                                   │
│         v                  v                                   │
│  ┌─────────────┐    ┌─────────────┐                            │
│  │   Memory    │    │    LLM      │                            │
│  │   记忆系统  │    │  语言模型   │                            │
│  └─────────────┘    └─────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 核心模块

| 模块 | 职责 | 状态 |
|------|------|------|
| **Perception** | 感官输入处理与特征提取 | 规划中 |
| **Inference** | 主动推理引擎，执行贝叶斯更新 | 规划中 |
| **Action** | 动作选择与执行 | 规划中 |
| **Internal Model** | 生成模型，包含先验和似然 | 规划中 |
| **Memory** | 长期记忆与短期记忆管理 | 规划中 |
| **LLM Interface** | 大语言模型集成 | 规划中 |

### 2.3 数据流

1. **感知阶段**: 外部输入 → 特征提取 → 传入推理模块
2. **推理阶段**: 当前状态 + 感官输入 → 计算预测误差 → 更新内部模型
3. **决策阶段**: 基于最小化自由能原则 → 选择最优行动
4. **行动阶段**: 执行动作 → 改变环境 → 产生新的感官输入

---

## 3. 关键概念与理论

### 3.1 自由能原理

自由能（Free Energy）定义为：

```
F = D[Q(s|o) || P(s)] - ln P(o|s)
```

其中：
- `F` = 自由能
- `Q(s|o)` = 变分后验（对隐藏状态的信念）
- `P(s)` = 先验分布
- `P(o|s)` = 似然（给定状态下观察的概率）

### 3.2 主动推理循环

主动推理包含两个互补的过程：

1. **感知推理**（Perceptual Inference）: 通过更新内部模型参数来最小化预测误差
2. **主动学习**（Active Learning）: 通过选择行动来获取信息，减少不确定性

### 3.3 预测编码

智能体通过预测编码机制工作：
- 生成对感官输入的预测
- 计算预测与实际输入的误差
- 通过调整内部模型来减少误差

---

## 4. 模块详细设计

### 4.1 感知模块 (Perception)

**职责**: 
- 接收多模态感官输入
- 特征提取与预处理
- 噪声过滤与数据归一化

**设计要点**:
- 支持多种输入模态（视觉、语言、音频等）
- 可扩展的特征提取器接口
- 实时数据流处理能力

### 4.2 推理模块 (Inference)

**职责**:
- 执行贝叶斯推理
- 计算预测误差
- 更新内部信念状态

**核心算法**:
- 变分贝叶斯推理
- 期望最大化
- 消息传递算法

### 4.3 行动模块 (Action)

**职责**:
- 动作空间定义
- 动作选择策略
- 动作执行与反馈

**动作选择原则**:
- 最小化预期自由能
- 平衡探索与利用
- 考虑长期回报

### 4.4 内部模型 (Internal Model)

**职责**:
- 维护环境的生成模型
- 存储先验知识
- 计算似然估计

**模型组成**:
- **先验模型**: 对隐藏状态的预期
- **似然模型**: 状态到观察的映射
- **转换模型**: 状态转移动态

### 4.5 记忆系统 (Memory)

**职责**:
- 长期记忆存储
- 短期记忆缓存
- 记忆检索与更新

**记忆类型**:
- **情景记忆**: 事件序列存储
- **语义记忆**: 事实知识存储
- **程序记忆**: 技能与过程存储

### 4.6 LLM接口 (LLM Interface)

**职责**:
- 与外部大语言模型交互
- 自然语言理解与生成
- 作为高级推理引擎

**设计要点**:
- 支持多种LLM后端（GPT、LLaMA等）
- 上下文管理
- 思维链推理支持

---

## 5. 依赖关系

### 5.1 核心依赖

| 依赖 | 用途 | 版本 |
|------|------|------|
| Python | 主编程语言 | 3.10+ |
| PyTorch | 深度学习框架 | 2.0+ |
| NumPy | 数值计算 | 1.24+ |
| SciPy | 科学计算 | 1.10+ |
| LangChain | LLM集成框架 | 0.1+ |
| Transformers | 预训练模型 | 4.30+ |

### 5.2 可选依赖

| 依赖 | 用途 |
|------|------|
| matplotlib | 可视化 |
| tensorboard | 实验记录 |
| pytest | 测试框架 |

### 5.3 环境要求

- Python 3.10 或更高版本
- CUDA 支持（推荐用于深度学习加速）
- 至少 8GB 内存（建议 16GB+）

---

## 6. 项目结构

```
bayesian-agi-core/
├── LICENSE
├── README.md
├── CODE_WIKI.md
├── requirements.txt
├── setup.py
├── src/
│   └── bayesian_agi/
│       ├── __init__.py
│       ├── perception/          # 感知模块
│       │   ├── __init__.py
│       │   ├── feature_extractor.py
│       │   └── input_processor.py
│       ├── inference/          # 推理模块
│       │   ├── __init__.py
│       │   ├── bayesian_inference.py
│       │   └── variational_inference.py
│       ├── action/             # 行动模块
│       │   ├── __init__.py
│       │   ├── action_selector.py
│       │   └── action_executor.py
│       ├── model/              # 内部模型
│       │   ├── __init__.py
│       │   ├── generative_model.py
│       │   ├── prior.py
│       │   └── likelihood.py
│       ├── memory/             # 记忆系统
│       │   ├── __init__.py
│       │   ├── long_term_memory.py
│       │   └── short_term_memory.py
│       ├── llm/                # LLM接口
│       │   ├── __init__.py
│       │   └── llm_interface.py
│       └── utils/              # 工具函数
│           ├── __init__.py
│           ├── math_utils.py
│           └── logging_utils.py
├── tests/                      # 测试代码
│   ├── test_perception.py
│   ├── test_inference.py
│   ├── test_action.py
│   └── test_memory.py
├── examples/                   # 示例代码
│   ├── basic_agent.py
│   └── interactive_demo.py
└── docs/                       # 文档
    ├── architecture.md
    ├── api_reference.md
    └── tutorials.md
```

---

## 7. 运行方式

### 7.1 环境安装

```bash
# 克隆仓库
git clone https://github.com/your-username/bayesian-agi-core.git
cd bayesian-agi-core

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 安装项目
pip install -e .
```

### 7.2 基本使用

```python
from bayesian_agi import Agent

# 创建智能体
agent = Agent()

# 设置初始状态
agent.initialize()

# 运行主动推理循环
for _ in range(100):
    # 感知
    observation = agent.perceive()
    
    # 推理
    agent.infer(observation)
    
    # 行动
    action = agent.act()
    
    # 执行动作并获取反馈
    environment.update(action)
```

### 7.3 测试运行

```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_inference.py

# 生成测试覆盖率报告
pytest --cov=src tests/
```

---

## 8. 开发指南

### 8.1 代码规范

- 遵循 PEP 8 代码风格
- 使用类型提示（Type Hints）
- 编写单元测试
- 保持函数和类的单一职责

### 8.2 分支策略

- `main`: 主分支，稳定版本
- `develop`: 开发分支，日常开发
- `feature/*`: 功能特性分支
- `bugfix/*`: Bug修复分支

### 8.3 贡献流程

1. Fork 仓库
2. 创建特性分支
3. 实现功能
4. 编写测试
5. 提交 Pull Request

---

## 9. 未来规划

### 9.1 短期目标（0-6个月）

- 完成核心模块的基础实现
- 实现基本的主动推理循环
- 集成主流LLM模型
- 提供基础API文档

### 9.2 中期目标（6-12个月）

- 支持多模态感知
- 实现记忆系统
- 提供完整的示例和教程
- 优化推理性能

### 9.3 长期目标（1-3年）

- 实现端到端的AGI系统
- 支持持续学习
- 提供可视化工具
- 构建社区生态

---

## 附录

### A. 参考文献

1. Friston, K. (2010). The free-energy principle: a unified brain theory? Nature Reviews Neuroscience.
2. Friston, K., et al. (2016). Active inference and learning. Neural Computation.
3. Millidge, B., et al. (2022). Active Inference: The Free Energy Principle in Mind, Brain, and Behavior. MIT Press.

### B. 术语表

| 术语 | 定义 |
|------|------|
| **Free Energy** | 自由能，衡量预测误差的度量 |
| **Active Inference** | 主动推理，智能体通过行动最小化自由能 |
| **Generative Model** | 生成模型，智能体对环境的内部表征 |
| **Variational Inference** | 变分推理，近似贝叶斯后验的方法 |
| **Predictive Coding** | 预测编码，通过预测误差进行学习的框架 |

---

**文档版本**: 1.0  
**生成日期**: 2026-05-22  
**项目状态**: 规划阶段