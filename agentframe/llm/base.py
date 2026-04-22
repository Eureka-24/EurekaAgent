"""LLM Adapter Base - LLM适配器基类

定义统一的LLM接口规范，对应 PRD 5.1.3 和 SPEC 4.1.1
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional
from enum import Enum


class MessageRole(Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """对话消息"""
    role: MessageRole
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List["ToolCall"]] = None


@dataclass
class ToolCall:
    """工具调用请求"""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ToolCallResult:
    """工具调用结果"""
    tool_call_id: str
    content: str
    is_error: bool = False


@dataclass
class GenerationConfig:
    """生成配置"""
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 1.0
    top_k: int = 50
    stop: Optional[List[str]] = None
    tools: Optional[List["ToolDefinition"]] = None
    stream: bool = False


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema


@dataclass
class ModelInfo:
    """模型信息"""
    name: str
    provider: str
    max_tokens: int
    supports_tools: bool
    supports_streaming: bool


@dataclass
class Response:
    """LLM响应"""
    content: str
    tool_calls: Optional[List[ToolCall]] = None
    usage: Optional["UsageInfo"] = None
    model: Optional[str] = None
    finish_reason: Optional[str] = None


@dataclass
class ResponseChunk:
    """流式响应块"""
    content: str
    is_final: bool = False


@dataclass
class UsageInfo:
    """Token使用量"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class LLMAdapter(ABC):
    """LLM适配器基类

    定义统一的LLM接口，所有模型适配器需实现此接口。
    对应 PRD 验收标准 13.1.3 接口标准化
    """

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
        """同步生成

        对应 PRD:
        - 5.1.3 同步调用
        - 验收标准: 同步调用<5s超时
        """
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[Message],
        config: GenerationConfig
    ) -> AsyncIterator[ResponseChunk]:
        """流式生成

        对应 PRD:
        - 5.1.3 流式响应
        - 验收标准: SSE延迟<100ms，支持断点续传
        """
        pass

    @abstractmethod
    def get_model_info(self, model: Optional[str] = None) -> ModelInfo:
        """获取模型信息

        对应 PRD:
        - 5.1.1 多模型支持
        """
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Token计数

        对应 PRD:
        - 5.3.3 Token计数
        - 验收标准: tiktoken/CL100K兼容性，误差<1%
        """
        pass
