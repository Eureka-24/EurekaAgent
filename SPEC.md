# AgentFrame 技术规格说明书 (SPEC)

| 属性 | 内容 |
|------|------|
| **文档版本** | V1.3 |
| **创建日期** | 2026-04-22 |
| **关联文档** | AgentFrame-PRD.md |
| **状态** | 待评审 |

---

## 1. 文档概述

### 1.1 目的

本文档是AgentFrame开发团队的技术规格说明书，详细描述了每个模块的技术实现方案、接口定义、数据结构，与PRD形成"需求-实现-验证"的闭环。

### 1.2 与PRD的对应关系

```
PRD (产品需求) ──► SPEC (技术规格) ──► TODO (开发任务) ──► 验收标准 (PRD第13章)
     │                   │                  │                    │
     │  定义"做什么"      │  定义"怎么做"      │  定义"谁来做"        │  定义"做到什么程度"
     └───────────────────┴──────────────────┴────────────────────┘
```

---

## 2. 技术栈与依赖

### 2.1 核心技术栈

| 层级 | 技术选型 | 版本 | 说明 |
|------|---------|------|------|
| **语言** | Python | >= 3.10 | 主要开发语言 |
| **类型标注** | TypeScript | >= 5.0 | SDK类型定义 |
| **异步框架** | asyncio | 内置 | 异步编程基础 |
| **Web框架** | FastAPI | >= 0.100 | API服务 |
| **向量数据库** | Qdrant | >= 1.0 | 向量存储/检索 |
| **知识图谱** | Neo4j | >= 5.0 | 语义记忆存储 |
| **任务队列** | Celery | >= 5.3 | 异步任务处理 |

### 2.2 第三方依赖

| 依赖 | 用途 | 许可证 |
|------|------|--------|
| openai | OpenAI API调用 | Apache 2.0 |
| anthropic | Claude API调用 | Apache 2.0 |
| google-generativeai | Gemini API调用 | Apache 2.0 |
| tiktoken | Token计数 | MIT |
| qdrant-client | 向量检索 | Apache 2.0 |
| neo4j | 知识图谱 | GPLv3 |
| langchain-core | 核心抽象 | MIT |
| pydantic | 数据验证 | MIT |

---

## 3. 项目结构

```
agentframe/
├── agentframe/                    # 主包
│   ├── __init__.py
│   ├── core/                      # 核心模块
│   │   ├── __init__.py
│   │   ├── agent.py              # Agent主类
│   │   ├── session.py             # 会话管理
│   │   ├── context.py             # 上下文管理
│   │   └── executor.py            # 执行引擎
│   ├── llm/                       # LLM适配层
│   │   ├── __init__.py
│   │   ├── base.py               # 基础接口
│   │   ├── openai.py             # OpenAI适配器
│   │   ├── anthropic.py          # Anthropic适配器
│   │   ├── gemini.py             # Google适配器
│   │   └── registry.py           # 模型注册表
│   ├── tools/                     # 工具系统
│   │   ├── __init__.py
│   │   ├── registry.py           # 工具注册中心
│   │   ├── executor.py           # 工具执行器
│   │   ├── validator.py          # 参数验证
│   │   └── builtins/             # 内置工具
│   │       ├── __init__.py
│   │       ├── web_search.py
│   │       ├── calculator.py
│   │       └── file_ops.py
│   ├── memory/                    # 记忆管理（四层架构）
│   │   ├── __init__.py
│   │   ├── base.py               # 记忆基类/评分公式
│   │   ├── working.py            # L0: 工作记忆 (TTL+TF-IDF)
│   │   ├── episodic.py           # L1: 情景记忆 (SQLite+Qdrant)
│   │   ├── semantic.py           # L2: 语义记忆 (Neo4j+Qdrant)
│   │   ├── perceptual.py         # L3: 感知记忆 (留白)
│   │   └── manager.py            # 统一记忆管理层
│   ├── rag/                       # RAG模块
│   │   ├── __init__.py
│   │   ├── document.py           # 文档处理
│   │   ├── chunker.py            # 分块策略
│   │   ├── embedder.py           # 嵌入模型
│   │   └── retriever.py          # 检索器
│   ├── storage/                   # 存储层
│   │   ├── __init__.py
│   │   ├── vector.py             # 向量存储
│   │   ├── kv.py                 # KV存储
│   │   └── file.py               # 文件存储
│   └── api/                       # API层
│       ├── __init__.py
│       ├── routes/
│       │   ├── sessions.py
│       │   ├── tools.py
│       │   ├── memories.py
│       │   └── documents.py
│       ├── schemas/               # Pydantic模型
│       └── middleware.py
├── sdk/                           # SDK
│   ├── python/                    # Python SDK
│   │   ├── agentframe/
│   │   └── pyproject.toml
│   └── typescript/                # TS SDK
│       ├── src/
│       └── package.json
├── tests/                         # 测试
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/                          # 文档
├── examples/                      # 示例
├── pyproject.toml
├── uv.lock
└── README.md
```

---

## 4. 核心接口规范

### 4.1 LLM适配层

#### 4.1.1 基础接口

```python
# agentframe/llm/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, List, Optional, Any
from enum import Enum

class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

@dataclass
class Message:
    role: MessageRole
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List['ToolCall']] = None

@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict

@dataclass
class ToolCallResult:
    tool_call_id: str
    content: str
    is_error: bool = False

@dataclass
class GenerationConfig:
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    top_k: int = 50
    stop: Optional[List[str]] = None
    tools: Optional[List['ToolDefinition']] = None
    stream: bool = False

@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict  # JSON Schema

@dataclass
class ModelInfo:
    name: str
    provider: str
    max_tokens: int
    supports_tools: bool
    supports_streaming: bool

@dataclass
class Response:
    content: str
    tool_calls: Optional[List[ToolCall]] = None
    usage: Optional['UsageInfo'] = None
    model: Optional[str] = None
    finish_reason: Optional[str] = None

@dataclass
class ResponseChunk:
    content: str
    is_final: bool = False

@dataclass
class UsageInfo:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class LLMAdapter(ABC):
    """LLM适配器基类"""
    
    @property
    @abstractmethod
    def provider(self) -> str:
        """提供商名称"""
        pass
    
    @property
    @abstractmethod
    def default_model(self) -> str:
        """默认模型"""
        pass
    
    @abstractmethod
    async def generate(
        self,
        messages: List[Message],
        config: GenerationConfig
    ) -> Response:
        """同步生成"""
        pass
    
    @abstractmethod
    async def stream(
        self,
        messages: List[Message],
        config: GenerationConfig
    ) -> AsyncIterator[ResponseChunk]:
        """流式生成"""
        pass
    
    @abstractmethod
    def get_model_info(self, model: Optional[str] = None) -> ModelInfo:
        """获取模型信息"""
        pass
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Token计数"""
        pass
```

#### 4.1.2 OpenAI适配器实现

```python
# agentframe/llm/openai.py

from agentframe.llm.base import (
    LLMAdapter, Message, MessageRole, GenerationConfig,
    Response, ResponseChunk, ModelInfo, UsageInfo, ToolCall, ToolCallResult
)
from openai import AsyncOpenAI, NotFoundError, RateLimitError
import json
from typing import AsyncIterator, List, Optional
import structlog

logger = structlog.get_logger()

class OpenAIAdapter(LLMAdapter):
    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 3
    ):
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries
        )
        self._models = {
            "gpt-4o": ModelInfo(
                name="gpt-4o",
                provider="openai",
                max_tokens=128000,
                supports_tools=True,
                supports_streaming=True
            ),
            "gpt-4-turbo": ModelInfo(
                name="gpt-4-turbo",
                provider="openai",
                max_tokens=128000,
                supports_tools=True,
                supports_streaming=True
            ),
            "gpt-3.5-turbo": ModelInfo(
                name="gpt-3.5-turbo",
                provider="openai",
                max_tokens=16385,
                supports_tools=True,
                supports_streaming=True
            )
        }
    
    @property
    def provider(self) -> str:
        return "openai"
    
    @property
    def default_model(self) -> str:
        return "gpt-4o"
    
    async def generate(
        self,
        messages: List[Message],
        config: GenerationConfig
    ) -> Response:
        # 实现细节...
        pass
    
    async def stream(
        self,
        messages: List[Message],
        config: GenerationConfig
    ) -> AsyncIterator[ResponseChunk]:
        # 实现细节...
        pass
    
    def get_model_info(self, model: Optional[str] = None) -> ModelInfo:
        model = model or self.default_model
        if model not in self._models:
            raise ValueError(f"Unknown model: {model}")
        return self._models[model]
    
    def count_tokens(self, text: str) -> int:
        # 使用tiktoken计算
        import tiktoken
        enc = tiktoken.encoding_for_model("gpt-4o")
        return len(enc.encode(text))
```

### 4.2 工具系统

#### 4.2.1 工具定义

```python
# agentframe/tools/registry.py

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type
from enum import Enum
import inspect
import structlog

logger = structlog.get_logger()

class ToolCategory(Enum):
    UTILITY = "utility"
    MEMORY = "memory"
    RAG = "rag"
    WEB = "web"
    COMPUTATION = "computation"
    CUSTOM = "custom"

@dataclass
class ToolMetadata:
    version: str = "1.0.0"
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    category: ToolCategory = ToolCategory.CUSTOM
    dependencies: List[str] = field(default_factory=list)
    description: str = ""

@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict  # JSON Schema
    handler: Callable
    metadata: ToolMetadata = field(default_factory=ToolMetadata)

class ToolRegistry:
    """工具注册中心"""
    
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._lock = asyncio.Lock()
    
    def register(
        self,
        name: str = None,
        description: str = None,
        metadata: ToolMetadata = None
    ):
        """装饰器注册工具"""
        def decorator(func: Callable) -> Callable:
            tool_name = name or func.__name__
            tool_def = ToolDefinition(
                name=tool_name,
                description=description or func.__doc__ or "",
                parameters=self._extract_parameters(func),
                handler=func,
                metadata=metadata or ToolMetadata()
            )
            self._tools[tool_name] = tool_def
            logger.info("tool_registered", tool_name=tool_name)
            return func
        return decorator
    
    async def execute(
        self,
        name: str,
        arguments: dict,
        timeout: float = 30.0
    ) -> ToolCallResult:
        """执行工具"""
        if name not in self._tools:
            return ToolCallResult(
                tool_call_id=arguments.get("id", ""),
                content=f"Tool not found: {name}",
                is_error=True
            )
        
        tool = self._tools[name]
        try:
            # 参数验证
            validated_args = self._validate_arguments(
                arguments, tool.parameters
            )
            
            # 执行
            if asyncio.iscoroutinefunction(tool.handler):
                result = await asyncio.wait_for(
                    tool.handler(**validated_args),
                    timeout=timeout
                )
            else:
                result = tool.handler(**validated_args)
            
            return ToolCallResult(
                tool_call_id=arguments.get("id", ""),
                content=str(result),
                is_error=False
            )
        except Exception as e:
            logger.error("tool_execution_error", tool=name, error=str(e))
            return ToolCallResult(
                tool_call_id=arguments.get("id", ""),
                content=f"Error: {str(e)}",
                is_error=True
            )
    
    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)
    
    def list_tools(
        self,
        category: Optional[ToolCategory] = None,
        tag: Optional[str] = None
    ) -> List[ToolDefinition]:
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t.metadata.category == category]
        if tag:
            tools = [t for t in tools if tag in t.metadata.tags]
        return tools
    
    def _extract_parameters(self, func: Callable) -> dict:
        """从函数签名提取参数Schema"""
        sig = inspect.signature(func)
        properties = {}
        required = []
        
        for name, param in sig.parameters.items():
            if name in ("self", "cls"):
                continue
            
            param_type = "string"
            if param.annotation == int:
                param_type = "integer"
            elif param.annotation == float:
                param_type = "number"
            elif param.annotation == bool:
                param_type = "boolean"
            elif param.annotation == list:
                param_type = "array"
            elif param.annotation == dict:
                param_type = "object"
            
            prop = {"type": param_type}
            if param.default != inspect.Parameter.empty:
                prop["default"] = param.default
            else:
                required.append(name)
            
            properties[name] = prop
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
```

#### 4.2.2 内置工具示例

```python
# agentframe/tools/builtins/web_search.py

from agentframe.tools.registry import ToolRegistry, ToolMetadata, ToolCategory
import httpx
import structlog

logger = structlog.get_logger()
registry = ToolRegistry()

@registry.register(
    name="web_search",
    description="Search the web for information",
    metadata=ToolMetadata(
        version="1.0.0",
        category=ToolCategory.WEB,
        tags=["search", "web", "information"]
    )
)
async def web_search(query: str, max_results: int = 5) -> list:
    """
    Search the web for the given query.
    
    Args:
        query: The search query string
        max_results: Maximum number of results (default: 5)
    
    Returns:
        List of search results with title, url, and snippet
    """
    logger.info("web_search", query=query, max_results=max_results)
    
    # 实际实现调用搜索API
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.search.example.com/search",
            params={"q": query, "limit": max_results}
        )
        results = response.json()
        
        return [
            {
                "title": r["title"],
                "url": r["url"],
                "snippet": r["snippet"]
            }
            for r in results["items"]
        ]
```

### 4.3 记忆系统

采用四层记忆架构：L0工作记忆 → L1情景记忆 → L2语义记忆 → L3感知记忆（留白）。

#### 4.3.1 记忆类型枚举

```python
class MemoryType(Enum):
    WORKING = "working"           # L0: 工作记忆
    EPISODIC = "episodic"         # L1: 情景记忆
    SEMANTIC = "semantic"         # L2: 语义记忆
    PERCEPTUAL = "perceptual"     # L3: 感知记忆（留白）

class MemoryLevel(Enum):
    L0 = 0   # 工作记忆
    L1 = 1   # 情景记忆
    L2 = 2   # 语义记忆
    L3 = 3   # 感知记忆
```

#### 4.3.2 记忆评分公式

```python
import math
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class MemoryItem:
    """"记忆项"""
    id: str
    content: str
    memory_type: MemoryType
    importance: float = 1.0  # 重要性 0-1
    timestamp: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)

def calculate_working_score(item: MemoryItem, similarity: float, lambda_decay: float = 0.1) -> float:
    """"工作记忆评分: (相似度 × 时间衰减) × (0.8 + 重要性 × 0.4)"""
    hours_elapsed = (datetime.now() - item.accessed_at).total_seconds() / 3600
    time_decay = math.exp(-lambda_decay * hours_elapsed)
    return (similarity * time_decay) * (0.8 + item.importance * 0.4)

def calculate_episodic_score(item: MemoryItem, vector_sim: float, lambda_recency: float = 0.05) -> float:
    """情景记忆评分: (向量相似度 × 0.8 + 时间近因性 × 0.2) × (0.8 + 重要性 × 0.4)"""
    days_elapsed = (datetime.now() - item.timestamp).total_seconds() / 86400
    recency = math.exp(-lambda_recency * days_elapsed)
    return (vector_sim * 0.8 + recency * 0.2) * (0.8 + item.importance * 0.4)

def calculate_semantic_score(item: MemoryItem, vector_sim: float, graph_sim: float) -> float:
    """语义记忆评分: (向量相似度 × 0.7 + 图相似度 × 0.3) × (0.8 + 重要性 × 0.4)"""
    return (vector_sim * 0.7 + graph_sim * 0.3) * (0.8 + item.importance * 0.4)
```

#### 4.3.3 WorkingMemory - 工作记忆 (L0)

```python
# agentframe/memory/working.py

from agentframe.memory.base import MemoryItem, Memory, MemoryType
from typing import Optional, List, Dict, Any
from collections import OrderedDict
import asyncio
import tfidf

class WorkingMemory(Memory):
    """L0层工作记忆 - TTL自动清理"""
    
    def __init__(
        self,
        max_size: int = 100,
        ttl_seconds: int = 3600,
        lambda_decay: float = 0.1
    ):
        self._cache: OrderedDict[str, MemoryItem] = OrderedDict()
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._lambda_decay = lambda_decay
        self._tfidf = tfidf.TFIDF()
    
    async def add(self, content: str, metadata: Optional[Dict] = None) -> MemoryItem:
        """添加记忆（TTL自动过期）"""
        item = MemoryItem(
            id=str(uuid.uuid4()),
            content=content,
            memory_type=MemoryType.WORKING,
            metadata=metadata or {}
        )
        self._cache[item.id] = item
        self._tfidf.add_document(item.id, content)
        await self._evict_if_needed()
        return item
    
    async def search(self, query: str, limit: int = 10) -> List[MemoryItem]:
        """TF-IDF向量化检索，失败回退关键词匹配"""
        results = self._tfidf.search(query, limit)
        if not results:
            # 回退到关键词匹配
            query_lower = query.lower()
            results = [
                item for item in self._cache.values()
                if query_lower in item.content.lower()
            ][:limit]
        return results
    
    async def _evict_if_needed(self):
        """LRU淘汰超出容量的记忆"""
        while len(self._cache) > self._max_size:
            oldest_id = next(iter(self._cache))
            await self.delete(oldest_id)
```

#### 4.3.4 EpisodicMemory - 情景记忆 (L1)


```python
# agentframe/memory/episodic.py

from agentframe.memory.base import MemoryItem, Memory, MemoryType
from qdrant_client import QdrantClient
import sqlite3

class EpisodicMemory(Memory):
    """L1层情景记忆 - SQLite + Qdrant"""
    
    def __init__(
        self,
        db_path: str = "episodic.db",
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        lambda_recency: float = 0.05
    ):
        self._db = sqlite3.connect(db_path)
        self._qdrant = QdrantClient(host=qdrant_host, port=qdrant_port)
        self._lambda_recency = lambda_recency
        self._init_db()
    
    def _init_db(self):
        """初始化SQLite表"""
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                importance REAL DEFAULT 0.5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    async def add(self, content: str, metadata: Optional[Dict] = None) -> MemoryItem:
        """添加记忆，存入SQLite和Qdrant"""
        item = MemoryItem(
            id=str(uuid.uuid4()),
            content=content,
            memory_type=MemoryType.EPISODIC,
            metadata=metadata or {}
        )
        # 存入SQLite
        self._db.execute(
            "INSERT INTO memories VALUES (?, ?, ?, ?)",
            (item.id, content, item.importance, item.timestamp)
        )
        # 存入Qdrant向量
        embedding = self._embed(content)
        self._qdrant.upsert("episodic", [{"id": item.id, "vector": embedding}])
        return item
    
    async def search(self, query: str, limit: int = 10) -> List[MemoryItem]:
        """向量检索 + 时间近因性评分"""
        query_embedding = self._embed(query)
        results = self._qdrant.search("episodic", query_embedding, limit=limit)
        return [self._get_from_db(r["id"]) for r in results]
```

#### 4.3.5 SemanticMemory - 语义记忆 (L2)


```python
# agentframe/memory/semantic.py

from agentframe.memory.base import MemoryItem, Memory, MemoryType
from neo4j import GraphDatabase
from qdrant_client import QdrantClient

class SemanticMemory(Memory):
    """L2层语义记忆 - Neo4j + Qdrant"""
    
    def __init__(
        self,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "password",
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333
    ):
        self._neo4j = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self._qdrant = QdrantClient(host=qdrant_host, port=qdrant_port)
    
    async def add(self, content: str, metadata: Optional[Dict] = None) -> MemoryItem:
        """添加记忆，建立知识图谱关系"""
        item = MemoryItem(
            id=str(uuid.uuid4()),
            content=content,
            memory_type=MemoryType.SEMANTIC,
            metadata=metadata or {}
        )
        # 存入Neo4j图谱
        with self._neo4j.session() as session:
            session.run(
                "CREATE (m:Memory {id: $id, content: $content})",
                id=item.id, content=content
            )
        # 存入Qdrant向量
        embedding = self._embed(content)
        self._qdrant.upsert("semantic", [{"id": item.id, "vector": embedding}])
        return item
    
    async def search(self, query: str, limit: int = 10) -> List[MemoryItem]:
        """向量检索 + 图关系推理"""
        query_embedding = self._embed(query)
        results = self._qdrant.search("semantic", query_embedding, limit=limit)
        # 图相似度增强
        scored_results = []
        for r in results:
            graph_sim = await self._calculate_graph_similarity(r["id"], query)
            score = calculate_semantic_score(r["item"], r["score"], graph_sim)
            scored_results.append((score, r["item"]))
        return [item for _, item in sorted(scored_results, reverse=True)[:limit]]
```

#### 4.3.6 PerceptualMemory - 感知记忆 (L3) ❌ 留白

```python
# agentframe/memory/perceptual.py

class PerceptualMemory(Memory):
    """L3层感知记忆 - 多模态数据 ⚠️ 留白"""
    
    async def add(self, content: str, metadata: Optional[Dict] = None) -> MemoryItem:
        raise NotImplementedError("PerceptualMemory暂未实现")
    
    async def search(self, query: str, limit: int = 10) -> List[MemoryItem]:
        raise NotImplementedError("PerceptualMemory暂未实现")
```

#### 4.3.7 记忆管理层

```python
class MemoryManager:
    """统一记忆管理层，协调四层记忆"""
    
    def __init__(
        self,
        working: WorkingMemory,
        episodic: EpisodicMemory,
        semantic: SemanticMemory
    ):
        self._working = working
        self._episodic = episodic
        self._semantic = semantic
        self._upgrade_thresholds = {
            "working_to_episodic": 0.7,   # 重要性>=0.7升级
            "episodic_to_semantic": 0.85,  # 重要性>=0.85升级
        }
    
    async def add(self, content: str, importance: float = 0.5) -> MemoryItem:
        """添加记忆，根据重要性自动分层"""
        item = await self._working.add(content, {"importance": importance})
        
        # 检查是否需要升级
        if importance >= self._upgrade_thresholds["working_to_episodic"]:
            await self._upgrade_to_episodic(item)
        
        return item
    
    async def search_cross_layer(self, query: str, limit: int = 10) -> List[MemoryItem]:
        """跨层检索"""
        results = []
        results.extend(await self._working.search(query, limit))
        results.extend(await self._episodic.search(query, limit))
        results.extend(await self._semantic.search(query, limit))
        # 按评分排序
        return sorted(results, key=lambda x: x.score, reverse=True)[:limit]
```
```

### 4.4 RAG模块

```python
# agentframe/rag/document.py

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

class DocumentFormat(Enum):
    PDF = "pdf"
    WORD = "word"
    MARKDOWN = "markdown"
    TXT = "txt"
    HTML = "html"

@dataclass
class Chunk:
    id: str
    content: str
    index: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    embeddings: Optional[List[float]] = None

@dataclass
class DocumentMetadata:
    source: str
    title: str = ""
    format: DocumentFormat = DocumentFormat.TXT
    author: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    custom: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Document:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    chunks: List[Chunk] = field(default_factory=list)
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    created_at: datetime = field(default_factory=datetime.now)

# agentframe/rag/chunker.py

from agentframe.rag.document import Document, Chunk, DocumentMetadata, DocumentFormat
from typing import List, Protocol
import re

class ChunkingStrategy(Protocol):
    """分块策略接口"""
    def chunk(self, text: str, metadata: dict) -> List[Chunk]:
        ...

class RecursiveChunker(ChunkingStrategy):
    """递归分块策略"""
    
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        separators: List[str] = None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or [
            "\n\n", "\n", "。", "！", "？", " ", ""
        ]
    
    def chunk(self, text: str, metadata: dict) -> List[Chunk]:
        chunks = []
        
        # 递归分割
        def split_text(text: str) -> List[str]:
            if len(text) <= self.chunk_size:
                return [text]
            
            for separator in self.separators:
                if separator in text:
                    parts = text.split(separator)
                    return self._merge_chunks(parts, separator)
            
            # 到达最后一级，按大小硬切
            return [
                text[i:i+self.chunk_size]
                for i in range(0, len(text), self.chunk_size - self.chunk_overlap)
            ]
        
        def _merge_chunks(parts: List[str], separator: str) -> List[str]:
            merged = []
            current = ""
            
            for part in parts:
                test = current + separator + part if current else part
                if len(test) <= self.chunk_size:
                    current = test
                else:
                    if current:
                        merged.append(current)
                    current = part
            
            if current:
                merged.append(current)
            
            return merged
        
        texts = split_text(text)
        
        for i, text in enumerate(texts):
            chunks.append(Chunk(
                id=str(uuid.uuid4()),
                content=text.strip(),
                index=i,
                metadata={**metadata, "chunk_index": i, "total_chunks": len(texts)}
            ))
        
        return chunks
```

### 4.5 Agent核心

```python
# agentframe/core/agent.py

from agentframe.llm.base import (
    LLMAdapter, Message, MessageRole, GenerationConfig,
    Response, ToolCall, ToolCallResult
)
from agentframe.tools.registry import ToolRegistry
from agentframe.memory.base import MemoryManager, MemoryType
from dataclasses import dataclass, field
from typing import List, Optional, AsyncIterator, Dict, Any
from enum import Enum
import structlog
import asyncio

logger = structlog.get_logger()

class AgentState(Enum):
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    WAITING_TOOL = "waiting_tool"

@dataclass
class Session:
    id: str
    user_id: str
    messages: List[Message] = field(default_factory=list)
    memory: List[Memory] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    state: AgentState = AgentState.IDLE

class Agent:
    """Agent主类"""
    
    def __init__(
        self,
        llm: LLMAdapter,
        tools: ToolRegistry,
        memory: MemoryManager,
        system_prompt: str = None,
        max_iterations: int = 10,
        tool_timeout: float = 30.0
    ):
        self._llm = llm
        self._tools = tools
        self._memory = memory
        self._system_prompt = system_prompt or "You are a helpful AI assistant."
        self._max_iterations = max_iterations
        self._tool_timeout = tool_timeout
        
        self._sessions: Dict[str, Session] = {}
    
    async def create_session(self, user_id: str, metadata: dict = None) -> Session:
        """创建会话"""
        session = Session(
            id=str(uuid.uuid4()),
            user_id=user_id,
            metadata=metadata or {}
        )
        self._sessions[session.id] = session
        
        # 添加系统消息
        session.messages.append(Message(
            role=MessageRole.SYSTEM,
            content=self._system_prompt
        ))
        
        logger.info("session_created", session_id=session.id)
        return session
    
    async def chat(
        self,
        session_id: str,
        message: str,
        stream: bool = False
    ) -> Response | AsyncIterator[ResponseChunk]:
        """聊天"""
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        session.state = AgentState.THINKING
        
        # 添加用户消息
        session.messages.append(Message(
            role=MessageRole.USER,
            content=message
        ))
        
        # ReAct循环
        try:
            response = await self._react_loop(session)
        except Exception as e:
            logger.error("chat_error", session_id=session_id, error=str(e))
            raise
        
        session.state = AgentState.IDLE
        return response
    
    async def _react_loop(self, session: Session) -> Response:
        """ReAct推理循环"""
        for iteration in range(self._max_iterations):
            # 生成
            config = GenerationConfig(
                tools=self._get_available_tools(),
                temperature=0.7
            )
            
            # 注入记忆上下文
            context_messages = await self._inject_memory(session)
            
            response = await self._llm.generate(
                context_messages,
                config
            )
            
            # 检查工具调用
            if response.tool_calls:
                session.state = AgentState.ACTING
                
                # 执行工具
                tool_results = []
                for tool_call in response.tool_calls:
                    result = await self._tools.execute(
                        tool_call.name,
                        tool_call.arguments,
                        timeout=self._tool_timeout
                    )
                    
                    # 添加工具结果消息
                    session.messages.append(Message(
                        role=MessageRole.TOOL,
                        content=result.content,
                        name=tool_call.name
                    ))
                    
                    tool_results.append(result)
                
                # 继续循环
                continue
            
            # 无工具调用，返回结果
            return response
        
        # 达到最大迭代次数
        return Response(
            content="抱歉，我无法在规定步骤内完成您的请求。",
            finish_reason="max_iterations"
        )
    
    async def _inject_memory(self, session: Session) -> List[Message]:
        """注入记忆到上下文"""
        # 检索相关记忆
        last_message = session.messages[-1] if session.messages else None
        if last_message and last_message.role == MessageRole.USER:
            memories = await self._memory.search(
                last_message.content,
                limit=5,
                memory_type=MemoryType.LONG_TERM
            )
            
            if memories:
                memory_context = "\n\n".join([
                    f"[相关记忆] {m.content}"
                    for m in memories
                ])
                
                # 在系统消息后注入
                injected_messages = session.messages.copy()
                if len(injected_messages) > 1:
                    injected_messages.insert(
                        1,
                        Message(
                            role=MessageRole.SYSTEM,
                            content=f"【记忆上下文】\n{memory_context}"
                        )
                    )
                return injected_messages
        
        return session.messages
    
    def _get_available_tools(self) -> List[ToolDefinition]:
        """获取可用工具列表"""
        tools = self._tools.list_tools()
        return [
            ToolDefinition(
                name=t.name,
                description=t.description,
                parameters=t.parameters
            )
            for t in tools
        ]
```

---

## 5. API接口规范

### 5.1 REST API

#### 5.1.1 会话管理

```yaml
# POST /api/v1/sessions
Request:
  body:
    user_id: string (required)
    metadata: object (optional)

Response:
  201:
    id: string
    user_id: string
    created_at: datetime
    metadata: object

# POST /api/v1/sessions/{id}/message
Request:
  body:
    content: string (required)
    stream: boolean (optional, default: false)

Response:
  200 (non-stream):
    id: string
    content: string
    tool_calls: array
    usage: object

  200 (stream):
    content-type: text/event-stream
    data:
      chunk: string
      is_final: boolean
```

#### 5.1.2 工具管理

```yaml
# GET /api/v1/tools
Query:
  category: string (optional)
  tag: string (optional)

Response:
  200:
    tools: array
    total: integer

# POST /api/v1/tools
Request:
  body:
    name: string (required)
    description: string (required)
    parameters: object (JSON Schema)
    code: string (required, Python function code)

Response:
  201:
    tool: object
```

### 5.2 WebSocket API

```yaml
# WS /api/v1/sessions/{id}/stream

Client -> Server:
  {
    "type": "message",
    "content": "你好"
  }
  
  {
    "type": "abort"
  }

Server -> Client:
  {
    "type": "chunk",
    "content": "你",
    "is_final": false
  }
  
  {
    "type": "chunk", 
    "content": "好！",
    "is_final": true
  }
  
  {
    "type": "tool_call",
    "tool": "web_search",
    "arguments": {...}
  }
```

---

## 6. 数据模型

### 6.1 数据库Schema

```sql
-- PostgreSQL

-- 会话表
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    state VARCHAR(50) DEFAULT 'idle'
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_updated_at ON sessions(updated_at);

-- 消息表
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    tool_calls JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);

-- 记忆表 (长期记忆)
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embeddings VECTOR(1536),
    type VARCHAR(20) NOT NULL,
    importance FLOAT DEFAULT 0.5,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    accessed_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_memories_embeddings ON memories USING ivfflat(embeddings);
CREATE INDEX idx_memories_session_id ON memories(session_id);

-- 文档表
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 文档块表
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    index INTEGER NOT NULL,
    embeddings VECTOR(1536),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_chunks_embeddings ON document_chunks USING ivfflat(embeddings);
```

### 6.2 Redis数据结构

```
# 会话状态
session:{session_id}:state = "thinking"
session:{session_id}:lock = "locked"

# 短期记忆
memory:short_term:{user_id} = [list of memory_ids]

# Token计数
token_count:{session_id} = 1234

# 限流
rate_limit:{user_id}:{minute} = count
```

---

## 7. 错误处理规范

### 7.1 错误码体系

| 错误码 | 说明 | HTTP状态码 |
|--------|------|-----------|
| AF-0001 | 通用错误 | 500 |
| AF-0002 | 无效参数 | 400 |
| AF-0003 | 未授权 | 401 |
| AF-0004 | 禁止访问 | 403 |
| AF-0005 | 资源不存在 | 404 |
| AF-0006 | 会话不存在 | 404 |
| AF-0007 | 工具不存在 | 404 |
| AF-0008 | 工具执行失败 | 500 |
| AF-0009 | LLM调用失败 | 502 |
| AF-0010 | 限流 | 429 |
| AF-0011 | 超时 | 504 |
| AF-0012 | 工具注册冲突 | 409 |

### 7.2 错误响应格式

```json
{
  "error": {
    "code": "AF-0008",
    "message": "Tool execution failed",
    "details": {
      "tool": "web_search",
      "reason": "API rate limit exceeded"
    },
    "request_id": "req-123456"
  }
}
```

---

## 8. 安全规范

### 8.1 密钥管理

- API密钥存储在环境变量或密钥管理服务
- 密钥不写入日志
- 支持密钥轮换

### 8.2 输入验证

- 所有用户输入必须经过Pydantic验证
- SQL注入防护：参数化查询
- XSS防护：输出转义

### 8.3 访问控制

```python
# 简化的RBAC模型
class Permission(Enum):
    SESSION_CREATE = "session:create"
    SESSION_READ = "session:read"
    SESSION_DELETE = "session:delete"
    TOOL_REGISTER = "tool:register"
    TOOL_DELETE = "tool:delete"
    ADMIN = "admin"

class Role(Enum):
    USER = [Permission.SESSION_CREATE, Permission.SESSION_READ]
    DEVELOPER = [Permission.SESSION_CREATE, Permission.SESSION_READ, 
                 Permission.TOOL_REGISTER]
    ADMIN = Permission.__all__
```

---

## 9. 可观测性

### 9.1 日志规范

```python
import structlog

# 结构化日志
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()
logger.info(
    "tool_executed",
    tool="web_search",
    duration_ms=123,
    user_id="user-123",
    session_id="sess-456"
)
```

### 9.2 指标规范

```python
from prometheus_client import Counter, Histogram, Gauge

# 计数器
llm_requests_total = Counter(
    "llm_requests_total",
    "Total LLM requests",
    ["provider", "model", "status"]
)

# 直方图
tool_duration_seconds = Histogram(
    "tool_duration_seconds",
    "Tool execution duration",
    ["tool_name"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

# 仪表
active_sessions = Gauge(
    "active_sessions",
    "Number of active sessions"
)
```

---

## 10. 部署架构

### 10.1 整体架构

```
                         ┌─────────────┐
                         │   Nginx     │
                         │  (Gateway)  │
                         └──────┬──────┘
                                │
               ┌────────────────┼────────────────┐
               │                │                │
         ┌─────▼─────┐    ┌─────▼─────┐    ┌─────▼─────┐
         │  API Pod  │    │  API Pod  │    │  API Pod  │
         │ (FastAPI) │    │ (FastAPI) │    │ (FastAPI) │
         └─────┬─────┘    └─────┬─────┘    └─────┬─────┘
               │                │                │
               └────────────────┼────────────────┘
                                │
    ┌───────────────────────────┼───────────────────────────┐
    │                           │                           │
┌───▼───┐               ┌──────▼──────┐            ┌──────▼──────┐
│ SQLite │               │   Qdrant   │            │   Neo4j    │
│(本地)  │               │  (向量存储) │            │  (知识图谱) │
└────────┘               └────────────┘            └─────────────┘

记忆系统数据流:
  User Input → WorkingMemory(内存) → EpisodicMemory(SQLite+Qdrant) → SemanticMemory(Neo4j+Qdrant)
```

### 10.2 记忆系统存储架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        AgentFrame Memory System                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ L0: WorkingMemory (工作记忆)                                    │    │
│  │     • 存储: 内存 (dict/Redis)                                   │    │
│  │     • 容量: 100条 (可配置)                                      │    │
│  │     • 清理: TTL 1小时自动过期                                    │    │
│  │     • 检索: TF-IDF向量化                                        │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                  │                                      │
│                         重要性 >= 0.7                                  │
│                                  ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ L1: EpisodicMemory (情景记忆)                                  │    │
│  │     • 存储: SQLite + Qdrant                                    │    │
│  │     • 清理: 时间+重要性双维度淘汰                                │    │
│  │     • 检索: 向量相似度 + 时间近因性                             │    │
│  │     • 评分: (向量×0.8 + 时间×0.2) × (0.8 + 重要性×0.4)        │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                  │                                      │
│                         重要性 >= 0.85 且 时间 >= 7天                    │
│                                  ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ L2: SemanticMemory (语义记忆)                                  │    │
│  │     • 存储: Neo4j + Qdrant                                    │    │
│  │     • 清理: 图关系稳定性判断                                    │    │
│  │     • 检索: 向量检索 + 图关系推理                               │    │
│  │     • 评分: (向量×0.7 + 图×0.3) × (0.8 + 重要性×0.4)          │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                  │                                      │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ L3: PerceptualMemory (感知记忆) ⚠️ 留白                        │    │
│  │     • 多模态支持待后续版本扩展                                  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 10.3 依赖服务

| 服务 | 用途 | 部署方式 | 必需 |
|------|------|---------|------|
| **Qdrant** | 向量存储/检索 | Docker | ✅ 必需 |
| **Neo4j** | 知识图谱存储 | Docker/云服务 | ✅ 必需 |
| **SQLite** | 情景记忆结构化存储 | 本地文件 | ✅ 必需 |
| PostgreSQL | 长期数据持久化 | Docker/云服务 | 可选 |

### 10.4 Docker Compose 配置

```yaml
version: '3.8'
services:
  agentframe-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=password
    depends_on:
      - qdrant
      - neo4j

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage

  neo4j:
    image: neo4j:5
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/password
    volumes:
      - neo4j_data:/data

volumes:
  qdrant_data:
  neo4j_data:
```

---

## 11. 版本对照表

| PRD章节 | SPEC对应章节 | TODO对应阶段 |
|---------|-------------|-------------|
| 5.1 LLM适配层 | 4.1, 6.1 | Phase 1 |
| 5.2 工具调用系统 | 4.2, 6.2 | Phase 1-2 |
| 5.3 记忆管理 | 4.3, 6.3 | Phase 2 |
| 5.3.1 WorkingMemory | 4.3.3 | Phase 2 |
| 5.3.2 EpisodicMemory | 4.3.4 | Phase 2 |
| 5.3.3 SemanticMemory | 4.3.5 | Phase 2 |
| 5.3.4 PerceptualMemory | 4.3.6 | Phase 4 |
| 5.4 RAG模块 | 4.4, 6.4 | Phase 2 |
| 5.5 Agent核心 | 4.5 | Phase 1 |
| 5.6 扩展机制 | 4.6 | Phase 3 |
| 6 非功能需求 | 7, 8, 9 | 全阶段 |
| 7 API接口 | 5 | Phase 1 |
| 13 验收标准 | 全文档 | 评审环节 |

---

*文档版本：V1.3*
*最后更新：2026-04-22*
