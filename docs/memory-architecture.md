# AgentFrame 记忆系统架构方案

| 属性 | 内容 |
|------|------|
| **文档版本** | V1.1 |
| **创建日期** | 2026-04-22 |
| **状态** | ✅ 已审核（V1.1） |

---

## 一、架构总览

```
AgentFrame Memory System
│
├── WorkingMemory (工作记忆)          L0层
│   └── 临时信息，TTL自动清理
│
├── EpisodicMemory (情景记忆)         L1层
│   └── 具体事件，时间序列
│
├── SemanticMemory (语义记忆)         L2层
│   └── 抽象知识，知识图谱
│
└── PerceptualMemory (感知记忆)        L3层
    └── 多模态数据
```

---

## 二、各层详细设计

### 2.1 WorkingMemory - 工作记忆

| 属性 | 设计 |
|------|------|
| **定位** | L0层，即时临时信息 |
| **存储** | 纯内存（dict/Redis） |
| **清理策略** | TTL（Time To Live）自动过期 |
| **检索方式** | TF-IDF向量化 → 失败回退关键词匹配 |
| **评分公式** | `(相似度 × 时间衰减) × (0.8 + 重要性 × 0.4)` |

**核心功能**：
- 当前会话的上下文信息
- 工具执行中间结果
- 临时计算状态

**时间衰减模型**：
```
衰减因子 = e^(-λ × t)
其中 λ = 0.1 (衰减系数), t = 距离上次访问的时间(小时)
```

---

### 2.2 EpisodicMemory - 情景记忆

| 属性 | 设计 |
|------|------|
| **定位** | L1层，具体事件经历 |
| **存储** | SQLite（结构化） + Qdrant（向量） |
| **清理策略** | 时间+重要性双维度淘汰 |
| **检索方式** | 向量相似度 + 时间近因性 |
| **评分公式** | `(向量相似度 × 0.8 + 时间近因性 × 0.2) × (0.8 + 重要性 × 0.4)` |

**核心功能**：
- 会话历史事件
- 用户交互序列
- 工具执行历史

**时间近因性计算**：
```
时间近因性 = e^(-β × Δt)
其中 β = 0.05 (近因系数), Δt = 距离现在的时间(天)
```

---

### 2.3 SemanticMemory - 语义记忆

| 属性 | 设计 |
|------|------|
| **定位** | L2层，抽象知识关系 |
| **存储** | Neo4j（图谱） + Qdrant（向量） |
| **清理策略** | 图关系稳定性判断 |
| **检索方式** | 向量检索 + 图关系推理 |
| **评分公式** | `(向量相似度 × 0.7 + 图相似度 × 0.3) × (0.8 + 重要性 × 0.4)` |

**核心功能**：
- 抽象概念和事实
- 知识图谱关系
- 学习到的模式

**图相似度计算**：
```
图相似度 = (共同邻居数 × 2) / (A的邻居数 + B的邻居数)
```

---

### 2.4 PerceptualMemory - 感知记忆 ❌ 留白

| 属性 | 设计 |
|------|------|
| **定位** | L3层，多模态数据存储 |
| **状态** | ⚠️ **留白，不实现** |
| **说明** | 多模态支持待后续版本扩展 |

**核心功能**（预留）：
- 多模态数据存储
- 图像/音频理解上下文
- 跨模态关联检索

**存储策略**（预留）：
```
PerceptualMemory/
├── text/      # 文本向量
├── image/     # 图像向量
└── audio/     # 音频向量
```

> ⚠️ **注意**：本版本不实现PerceptualMemory，留待后续扩展

---

## 三、通用评分公式汇总

| 记忆层 | 评分公式 | 权重说明 |
|--------|----------|----------|
| **Working** | `(相似度 × 时间衰减) × (0.8 + 重要性 × 0.4)` | 时间衰减为主 |
| **Episodic** | `(向量相似度 × 0.8 + 时间近因性 × 0.2) × (0.8 + 重要性 × 0.4)` | 向量相似度为主 |
| **Semantic** | `(向量相似度 × 0.7 + 图相似度 × 0.3) × (0.8 + 重要性 × 0.4)` | 图关系增强 |
| **Perceptual** | ⚠️ **留白** | - |

**通用公式解析**：
- `重要性 × 0.4`：基础放大系数，重要性越高评分越高
- `0.8 + 重要性 × 0.4`：重要性调整因子，范围 [0.8, 1.2]

---

## 四、时间近因性指数衰减模型

所有记忆层采用统一的指数衰减模型：

```
Decay(t) = e^(-λ × t)

参数说明：
- λ (衰减系数): 控制衰减速度
- t: 时间距离
```

| 记忆层 | λ 值 | t 的单位 |
|--------|------|----------|
| Working | 0.1 | 小时 |
| Episodic | 0.05 | 天 |
| Semantic | 0.02 | 周 |
| Perceptual | 0.05 | 天 |

---

## 五、技术依赖

| 组件 | 用途 | 阶段 |
|------|------|------|
| **内存/dict** | WorkingMemory存储 | ✅ 必需 |
| **SQLite** | EpisodicMemory结构化存储 | ✅ 必需 |
| **Qdrant** | 向量检索引擎 | ✅ 必需 |
| **Neo4j** | SemanticMemory知识图谱 | ✅ 必需 |
| **TF-IDF** | WorkingMemory语义检索 | ✅ 必需 |
| **多模态存储** | PerceptualMemory | ❌ 留空 |

**注意**：Qdrant需本地部署或使用Docker启动；Neo4j需本地部署或使用Neo4j Aura云服务。

---

## 六、实现计划

### 阶段一：基础层（L0-L1）

```python
agentframe/memory/
├── __init__.py
├── base.py                 # 统一基类
├── working.py             # 工作记忆 (内存+TTL)
├── episodic.py            # 情景记忆 (SQLite+Qdrant)
├── semantic.py           # 语义记忆 (Neo4j+Qdrant)
└── perceptual.py         # 感知记忆 (留白)
```

| 记忆层 | 存储 | 说明 |
|--------|------|------|
| WorkingMemory | 内存 + TF-IDF | L0层核心 |
| EpisodicMemory | SQLite + Qdrant | L1层完整实现 |

### 阶段二：知识层（L2）


| 记忆层 | 存储 | 说明 |
|--------|------|------|
| SemanticMemory | Neo4j + Qdrant | 知识图谱 |

### 阶段三：感知层（L3）


| 记忆层 | 存储 | 说明 |
|--------|------|------|
| PerceptualMemory | 留白 | 多模态待扩展 |

---

## 七、Write-Manage-Read 流程

```
┌─────────────────────────────────────────────────────────────┐
│                     Memory System                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐                 │
│   │  WRITE  │───►│  MANAGE │───►│  READ   │                 │
│   └─────────┘    └─────────┘    └─────────┘                 │
│        │              │              │                       │
│        ▼              ▼              ▼                       │
│   新信息写入      评分排序        相关记忆                  │
│   事件记录        淘汰低分        注入context               │
│   工具结果        自动摘要                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Manage阶段核心操作**：
1. 计算每条记忆的评分
2. 淘汰评分低于阈值的内容
3. 触发从L1→L2的记忆升级

---

## 八、数据流设计

```
User Input
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ L0: WorkingMemory                                           │
│ - 存储当前对话                                              │
│ - 计算TF-IDF向量                                            │
│ - TTL自动过期（默认1小时）                                   │
└─────────────────────────────────────────────────────────────┘
    │ 重要性 >= 0.7
    ▼
┌─────────────────────────────────────────────────────────────┐
│ L1: EpisodicMemory                                         │
│ - 持久化到SQLite                                            │
│ - 向量存入内存向量库                                        │
│ - 评分公式: (向量×0.8 + 时间×0.2) × (0.8 + 重要性×0.4)     │
└─────────────────────────────────────────────────────────────┘
    │ 重要性 >= 0.85 且 时间 >= 7天
    ▼
┌─────────────────────────────────────────────────────────────┐
│ L2: SemanticMemory                                        │
│ - 存入知识图谱                                              │
│ - 建立概念关联                                              │
│ - 评分公式: (向量×0.7 + 图×0.3) × (0.8 + 重要性×0.4)        │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
Query时跨层检索，评分合并排序
```

---

## 九、接口设计

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class MemoryItem:
    """记忆项基类"""
    id: str
    content: str
    importance: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class Memory(ABC):
    """记忆基类接口"""
    
    @abstractmethod
    async def add(self, content: str, metadata: Optional[Dict] = None) -> MemoryItem:
        """添加记忆"""
        pass
    
    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> List[MemoryItem]:
        """检索记忆"""
        pass
    
    @abstractmethod
    async def delete(self, item_id: str) -> bool:
        """删除记忆"""
        pass
    
    @abstractmethod
    def calculate_score(self, item: MemoryItem) -> float:
        """计算记忆评分"""
        pass


class WorkingMemory(Memory):
    """工作记忆实现"""
    
    async def add(self, content: str, metadata: Optional[Dict] = None) -> MemoryItem:
        ...
    
    async def search(self, query: str, limit: int = 10) -> List[MemoryItem]:
        """TF-IDF向量化检索"""
        ...
    
    def calculate_score(self, item: MemoryItem) -> float:
        """(相似度 × e^(-0.1×t)) × (0.8 + 重要性×0.4)"""
        ...


class EpisodicMemory(Memory):
    """情景记忆实现"""
    
    async def add(self, content: str, metadata: Optional[Dict] = None) -> MemoryItem:
        ...
    
    async def search(self, query: str, limit: int = 10) -> List[MemoryItem]:
        """向量+时间近因性检索"""
        ...
    
    def calculate_score(self, item: MemoryItem) -> float:
        """(向量×0.8 + 时间×0.2) × (0.8 + 重要性×0.4)"""
        ...


class SemanticMemory(Memory):
    """语义记忆实现（Neo4j + Qdrant）"""
    
    async def add(self, content: str, metadata: Optional[Dict] = None) -> MemoryItem:
        ...
    
    async def search(self, query: str, limit: int = 10) -> List[MemoryItem]:
        """向量+图关系检索"""
        ...
    
    def calculate_score(self, item: MemoryItem) -> float:
        """(向量×0.7 + 图×0.3) × (0.8 + 重要性×0.4)"""
        ...


class PerceptualMemory(Memory):
    """感知记忆实现 ⚠️ 留白，不实现"""
    
    async def add(self, content: str, metadata: Optional[Dict] = None) -> MemoryItem:
        raise NotImplementedError("PerceptualMemory暂未实现")
    
    async def search(self, query: str, limit: int = 10) -> List[MemoryItem]:
        raise NotImplementedError("PerceptualMemory暂未实现")
    
    def calculate_score(self, item: MemoryItem) -> float:
        raise NotImplementedError("PerceptualMemory暂未实现")
```

---

## 十、决策确认

| 问题 | 决定 |
|------|------|
| Neo4j依赖 | ✅ 必须，包含在完整架构中 |
| 向量引擎 | Qdrant（已确认） |
| 记忆层完整性 | 完整4层（Working/Episodic/Semantic/Perceptual） |
| 多模态支持 | ❌ 不包含，留白待后续扩展 |

---

*文档版本：V1.1*
*最后更新：2026-04-22*
*决策状态：已审核*
