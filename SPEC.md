# AgentFrame 技术规格说明书 (SPEC)

| 属性 | 内容 |
|------|------|
| **文档版本** | V1.0 |
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
| **向量数据库** | ChromaDB | >= 0.4 | 内置向量存储 |
| **缓存** | Redis | >= 7.0 | 会话状态缓存 |
| **任务队列** | Celery | >= 5.3 | 异步任务处理 |

### 2.2 第三方依赖

| 依赖 | 用途 | 许可证 |
|------|------|--------|
| openai | OpenAI API调用 | Apache 2.0 |
| anthropic | Claude API调用 | Apache 2.0 |
| google-generativeai | Gemini API调用 | Apache 2.0 |
| tiktoken | Token计数 | MIT |
| chromadb | 向量存储 | Apache 2.0 |
| langchain-core | 核心抽象 | MIT |
| pydantic | 数据验证 | MIT |
| structlog | 结构化日志 | Apache 2.0 |
| prometheus-client | 性能监控 | Apache 2.0 |

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
│   ├── memory/                    # 记忆管理
│   │   ├── __init__.py
│   │   ├── base.py               # 记忆基类
│   │   ├── short_term.py         # 短期记忆
│   │   ├── long_term.py          # 长期记忆
│   │   ├── working.py            # 工作记忆
│   │   └── window.py             # 上下文窗口
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

```python
# agentframe/memory/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
import asyncio

class MemoryType(Enum):
    SESSION = "session"       # 会话记忆
    SHORT_TERM = "short_term" # 短期记忆
    LONG_TERM = "long_term"   # 长期记忆
    WORKING = "working"       # 工作记忆

@dataclass
class Memory:
    id: str
    content: str
    type: MemoryType
    embeddings: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    importance: float = 0.5  # 重要性 0-1

class MemoryManager(ABC):
    """记忆管理器基类"""
    
    @abstractmethod
    async def add(self, memory: Memory) -> str:
        """添加记忆"""
        pass
    
    @abstractmethod
    async def get(self, memory_id: str) -> Optional[Memory]:
        """获取记忆"""
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = 10,
        memory_type: Optional[MemoryType] = None
    ) -> List[Memory]:
        """检索记忆"""
        pass
    
    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        pass

# agentframe/memory/short_term.py

from agentframe.memory.base import Memory, MemoryManager, MemoryType
from collections import OrderedDict
import asyncio

class ShortTermMemory(MemoryManager):
    """短期记忆 - LRU缓存实现"""
    
    def __init__(self, max_size: int = 100, ttl: int = 3600):
        self._cache: OrderedDict[str, Memory] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl
    
    async def add(self, memory: Memory) -> str:
        memory.type = MemoryType.SHORT_TERM
        self._cache[memory.id] = memory
        self._cache.move_to_end(memory.id)
        
        # LRU淘汰
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)
        
        return memory.id
    
    async def get(self, memory_id: str) -> Optional[Memory]:
        if memory_id in self._cache:
            self._cache.move_to_end(memory_id)
            return self._cache[memory_id]
        return None
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        memory_type: Optional[MemoryType] = None
    ) -> List[Memory]:
        # 简单关键词匹配，后续可集成向量检索
        results = [
            m for m in self._cache.values()
            if query.lower() in m.content.lower()
            and (memory_type is None or m.type == memory_type)
        ]
        return results[:limit]
    
    async def delete(self, memory_id: str) -> bool:
        if memory_id in self._cache:
            del self._cache[memory_id]
            return True
        return False
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

```
                    ┌─────────────┐
                    │   Nginx     │
                    │  (Gateway)  │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐ ┌────▼────┐ ┌─────▼─────┐
        │  API Pod  │ │ API Pod │ │ API Pod   │
        │ (FastAPI) │ │         │ │           │
        └─────┬─────┘ └────┬────┘ └─────┬─────┘
              │            │            │
              └────────────┼────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
   ┌─────▼─────┐    ┌─────▼─────┐    ┌──────▼──────┐
   │   Redis   │    │ PostgreSQL│    │   ChromaDB   │
   │  (Cache)  │    │ (Primary) │    │  (Vector)   │
   └───────────┘    └───────────┘    └─────────────┘
```

---

## 11. 版本对照表

| PRD章节 | SPEC对应章节 | TODO对应阶段 |
|---------|-------------|-------------|
| 5.1 LLM适配层 | 4.1, 6.1 | Phase 1 |
| 5.2 工具调用系统 | 4.2, 6.2 | Phase 1-2 |
| 5.3 记忆管理 | 4.3, 6.3 | Phase 2 |
| 5.4 RAG模块 | 4.4, 6.4 | Phase 2 |
| 5.5 Agent核心 | 4.5 | Phase 1 |
| 5.6 扩展机制 | 4.6 | Phase 3 |
| 6 非功能需求 | 7, 8, 9 | 全阶段 |
| 7 API接口 | 5 | Phase 1 |
| 13 验收标准 | 全文档 | 评审环节 |

---

*文档版本：V1.0*
*最后更新：2026-04-22*
