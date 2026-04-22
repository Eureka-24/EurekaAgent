"""Anthropic LLM Adapter - Anthropic模型适配器

实现Anthropic Claude系列模型的适配器，对应 PRD 5.1.1 和 SPEC 4.1.2
"""

import os
from typing import Any, AsyncIterator, Dict, List, Optional

import anthropic

from agentframe.llm.base import (
    GenerationConfig,
    LLMAdapter,
    Message,
    MessageRole,
    ModelInfo,
    Response,
    ResponseChunk,
    ToolCall,
    ToolCallResult,
    UsageInfo,
)

# 导入structlog
try:
    import structlog
    logger = structlog.get_logger()
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class AnthropicAdapter(LLMAdapter):
    """Anthropic Claude模型适配器

    支持 Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku 等模型。
    对应 PRD 验收标准 13.1.1 多模型支持
    """

    # 支持的模型列表
    SUPPORTED_MODELS = {
        "claude-3-5-sonnet-20240620": ModelInfo(
            name="claude-3-5-sonnet-20240620",
            provider="anthropic",
            max_tokens=8192,
            supports_tools=True,
            supports_streaming=True,
        ),
        "claude-3-opus-20240229": ModelInfo(
            name="claude-3-opus-20240229",
            provider="anthropic",
            max_tokens=4096,
            supports_tools=True,
            supports_streaming=True,
        ),
        "claude-3-haiku-20240307": ModelInfo(
            name="claude-3-haiku-20240307",
            provider="anthropic",
            max_tokens=4096,
            supports_tools=True,
            supports_streaming=True,
        ),
        "claude-sonnet-4-20250514": ModelInfo(
            name="claude-sonnet-4-20250514",
            provider="anthropic",
            max_tokens=8192,
            supports_tools=True,
            supports_streaming=True,
        ),
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20240620",
        timeout: float = 60.0,
        max_retries: int = 3,
        default_temperature: float = 0.7,
        default_max_tokens: int = 4096,
    ):
        """初始化Anthropic适配器

        Args:
            api_key: Anthropic API密钥，默认从环境变量ANTHROPIC_API_KEY读取
            model: 默认模型名称
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            default_temperature: 默认温度参数
            default_max_tokens: 默认最大token数
        """
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self._api_key:
            raise ValueError(
                "Anthropic API key is required. "
                "Set ANTHROPIC_API_KEY environment variable or pass api_key parameter."
            )

        self._model = model
        self._timeout = timeout
        self._max_retries = max_retries
        self._default_temperature = default_temperature
        self._default_max_tokens = default_max_tokens

        # 初始化Anthropic客户端
        self._client = anthropic.AsyncAnthropic(
            api_key=self._api_key,
            timeout=anthropic.Timeout(
                client_timeout=self._timeout,
            ),
            max_retries=max_retries,
        )

    @property
    def provider(self) -> str:
        """提供商名称"""
        return "anthropic"

    @property
    def default_model(self) -> str:
        """默认模型"""
        return self._model

    def get_model_info(self, model: Optional[str] = None) -> ModelInfo:
        """获取模型信息

        Args:
            model: 模型名称，如果为None则返回当前默认模型信息

        Returns:
            ModelInfo: 模型信息

        Raises:
            ValueError: 如果模型不支持
        """
        model = model or self._model
        if model not in self.SUPPORTED_MODELS:
            raise ValueError(
                f"Unsupported model: {model}. "
                f"Supported models: {list(self.SUPPORTED_MODELS.keys())}"
            )
        return self.SUPPORTED_MODELS[model]

    def list_models(self) -> List[ModelInfo]:
        """列出所有支持的模型"""
        return list(self.SUPPORTED_MODELS.values())

    async def generate(
        self,
        messages: List[Message],
        config: Optional[GenerationConfig] = None,
    ) -> Response:
        """同步生成

        Args:
            messages: 消息列表
            config: 生成配置

        Returns:
            Response: LLM响应
        """
        config = config or GenerationConfig(
            temperature=self._default_temperature,
            max_tokens=self._default_max_tokens,
        )

        # 提取system消息和对话消息
        system_message = ""
        conversation_messages = []
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_message = msg.content
            else:
                conversation_messages.append(msg)

        # 转换消息格式
        anthropic_messages = self._convert_messages(conversation_messages)

        # 转换工具格式
        tools = None
        if config.tools:
            tools = self._convert_tools(config.tools)

        try:
            logger.info(
                "anthropic_generate_start",
                model=self._model,
                message_count=len(messages),
            )

            response = await self._client.messages.create(
                model=self._model,
                system=system_message or None,
                messages=anthropic_messages,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                tools=tools,
                stream=False,
            )

            # 解析响应
            content_blocks = response.content
            text_content = ""
            tool_uses = []

            for block in content_blocks:
                if block.type == "text":
                    text_content += block.text
                elif block.type == "tool_use":
                    tool_uses.append(
                        ToolCall(
                            id=block.id,
                            name=block.name,
                            arguments=block.input,
                        )
                    )

            # 解析usage
            usage = UsageInfo(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            )

            logger.info(
                "anthropic_generate_success",
                model=self._model,
                content_length=len(text_content),
                tool_calls_count=len(tool_uses),
            )

            return Response(
                content=text_content,
                tool_calls=tool_uses if tool_uses else None,
                usage=usage,
                model=self._model,
                finish_reason=str(response.stop_reason) if response.stop_reason else None,
            )

        except Exception as e:
            logger.error("anthropic_generate_error", error=str(e))
            raise

    async def stream(
        self,
        messages: List[Message],
        config: Optional[GenerationConfig] = None,
    ) -> AsyncIterator[ResponseChunk]:
        """流式生成

        Args:
            messages: 消息列表
            config: 生成配置

        Yields:
            ResponseChunk: 流式响应块
        """
        config = config or GenerationConfig(
            temperature=self._default_temperature,
            max_tokens=self._default_max_tokens,
        )

        # 提取system消息
        system_message = ""
        conversation_messages = []
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_message = msg.content
            else:
                conversation_messages.append(msg)

        # 转换消息格式
        anthropic_messages = self._convert_messages(conversation_messages)

        try:
            logger.info(
                "anthropic_stream_start",
                model=self._model,
                message_count=len(messages),
            )

            with await self._client.messages.stream(
                model=self._model,
                system=system_message or None,
                messages=anthropic_messages,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                stream=True,
            ) as stream:
                async for text_event in stream.text_stream:
                    yield ResponseChunk(
                        content=text_event,
                        is_final=False,
                    )

            # 获取最终消息
            message = await stream.get_final_message()
            
            # 检查是否有工具调用
            tool_calls = []
            for block in message.content:
                if block.type == "tool_use":
                    tool_calls.append(
                        ToolCall(
                            id=block.id,
                            name=block.name,
                            arguments=block.input,
                        )
                    )

            logger.info(
                "anthropic_stream_complete",
                model=self._model,
                tool_calls_count=len(tool_calls),
            )

            # 最终chunk
            yield ResponseChunk(content="", is_final=True)

        except Exception as e:
            logger.error("anthropic_stream_error", error=str(e))
            raise

    def count_tokens(self, text: str) -> int:
        """Token计数 (估算)

        注意: Anthropic不提供公开的token计数API，这里使用估算
        实际使用中应使用官方token计数工具

        Args:
            text: 输入文本

        Returns:
            int: 估算的token数量
        """
        # 粗略估算: 每4个字符约等于1个token
        return len(text) // 4 + 1

    def _convert_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """转换消息格式为Anthropic格式"""
        result = []
        for msg in messages:
            role = "user" if msg.role == MessageRole.USER else "assistant"
            content = msg.content
            if msg.role == MessageRole.TOOL:
                # 工具结果需要特殊处理
                content = f"[{msg.name}] {msg.content}"
            result.append({"role": role, "content": content})
        return result

    def _convert_tools(self, tools: List) -> List[Dict[str, Any]]:
        """转换工具定义为Anthropic格式"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.parameters,
            }
            for tool in tools
        ]
