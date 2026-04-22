"""OpenAI LLM Adapter - OpenAI模型适配器

实现OpenAI GPT系列模型的适配器，对应 PRD 5.1.1 和 SPEC 4.1.2
"""

import os
from typing import Any, AsyncIterator, Dict, List, Optional

import tiktoken
from openai import AsyncOpenAI, APIError, RateLimitError, Timeout

from agentframe.llm.base import (
    GenerationConfig,
    LLMAdapter,
    Message,
    ModelInfo,
    Response,
    ResponseChunk,
    ToolCall,
    UsageInfo,
)

# 导入structlog
try:
    import structlog
    logger = structlog.get_logger()
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class OpenAIAdapter(LLMAdapter):
    """OpenAI模型适配器

    支持 GPT-4o, GPT-4 Turbo, GPT-3.5 Turbo 等模型。
    对应 PRD 验收标准 13.1.1 多模型支持
    """

    # 支持的模型列表
    SUPPORTED_MODELS = {
        "gpt-4o": ModelInfo(
            name="gpt-4o",
            provider="openai",
            max_tokens=128000,
            supports_tools=True,
            supports_streaming=True,
        ),
        "gpt-4o-mini": ModelInfo(
            name="gpt-4o-mini",
            provider="openai",
            max_tokens=128000,
            supports_tools=True,
            supports_streaming=True,
        ),
        "gpt-4-turbo": ModelInfo(
            name="gpt-4-turbo",
            provider="openai",
            max_tokens=128000,
            supports_tools=True,
            supports_streaming=True,
        ),
        "gpt-4": ModelInfo(
            name="gpt-4",
            provider="openai",
            max_tokens=8192,
            supports_tools=True,
            supports_streaming=True,
        ),
        "gpt-3.5-turbo": ModelInfo(
            name="gpt-3.5-turbo",
            provider="openai",
            max_tokens=16385,
            supports_tools=True,
            supports_streaming=True,
        ),
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-4o",
        timeout: float = 60.0,
        max_retries: int = 3,
        default_temperature: float = 0.7,
        default_max_tokens: int = 4096,
    ):
        """初始化OpenAI适配器

        Args:
            api_key: OpenAI API密钥，默认从环境变量OPENAI_API_KEY读取
            base_url: API基础URL，用于代理或兼容API
            model: 默认模型名称
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            default_temperature: 默认温度参数
            default_max_tokens: 默认最大token数
        """
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self._api_key:
            raise ValueError(
                "OpenAI API key is required. "
                "Set OPENAI_API_KEY environment variable or pass api_key parameter."
            )

        self._base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self._model = model
        self._timeout = timeout
        self._max_retries = max_retries
        self._default_temperature = default_temperature
        self._default_max_tokens = default_max_tokens

        # 初始化OpenAI客户端
        self._client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
            timeout=timeout,
            max_retries=max_retries,
        )

        # 初始化tokenizer
        self._tokenizer = tiktoken.encoding_for_model(self._model)

    @property
    def provider(self) -> str:
        """提供商名称"""
        return "openai"

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
            raise ValueError(f"Unsupported model: {model}. Supported models: {list(self.SUPPORTED_MODELS.keys())}")
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

        对应 PRD:
        - 5.1.3 同步调用
        - 验收标准: 同步调用<5s超时

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

        # 转换消息格式
        openai_messages = self._convert_messages(messages)

        # 转换工具格式
        tools = None
        if config.tools:
            tools = self._convert_tools(config.tools)

        try:
            logger.info(
                "openai_generate_start",
                model=self._model,
                message_count=len(messages),
            )

            response = await self._client.chat.completions.create(
                model=self._model,
                messages=openai_messages,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                top_p=config.top_p,
                stop=config.stop,
                tools=tools,
                stream=False,
            )

            # 解析响应
            choice = response.choices[0]
            content = choice.message.content or ""

            # 解析工具调用
            tool_calls = None
            if choice.message.tool_calls:
                tool_calls = [
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=tc.function.arguments,
                    )
                    for tc in choice.message.tool_calls
                ]

            # 解析usage
            usage = None
            if response.usage:
                usage = UsageInfo(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                )

            logger.info(
                "openai_generate_success",
                model=self._model,
                content_length=len(content),
                tool_calls_count=len(tool_calls) if tool_calls else 0,
            )

            return Response(
                content=content,
                tool_calls=tool_calls,
                usage=usage,
                model=self._model,
                finish_reason=choice.finish_reason,
            )

        except Timeout as e:
            logger.error("openai_timeout", error=str(e))
            raise TimeoutError(f"OpenAI API timeout: {e}") from e
        except RateLimitError as e:
            logger.warning("openai_rate_limit", error=str(e))
            raise e
        except APIError as e:
            logger.error("openai_api_error", error=str(e))
            raise e

    async def stream(
        self,
        messages: List[Message],
        config: Optional[GenerationConfig] = None,
    ) -> AsyncIterator[ResponseChunk]:
        """流式生成

        对应 PRD:
        - 5.1.3 流式响应
        - 验收标准: SSE延迟<100ms，支持断点续传

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

        # 转换消息格式
        openai_messages = self._convert_messages(messages)

        # 转换工具格式
        tools = None
        if config.tools:
            tools = self._convert_tools(config.tools)

        try:
            logger.info(
                "openai_stream_start",
                model=self._model,
                message_count=len(messages),
            )

            stream = await self._client.chat.completions.create(
                model=self._model,
                messages=openai_messages,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                top_p=config.top_p,
                stop=config.stop,
                tools=tools,
                stream=True,
            )

            accumulated_content = ""
            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    accumulated_content += delta.content
                    yield ResponseChunk(
                        content=delta.content,
                        is_final=False,
                    )

            # 最后一个chunk标记为final
            yield ResponseChunk(
                content="",
                is_final=True,
            )

            logger.info(
                "openai_stream_complete",
                model=self._model,
                total_length=len(accumulated_content),
            )

        except Exception as e:
            logger.error("openai_stream_error", error=str(e))
            raise

    def count_tokens(self, text: str) -> int:
        """Token计数

        对应 PRD:
        - 5.3.3 Token计数
        - 验收标准: tiktoken/CL100K兼容性，误差<1%

        Args:
            text: 输入文本

        Returns:
            int: token数量
        """
        return len(self._tokenizer.encode(text))

    def count_messages_tokens(self, messages: List[Message]) -> int:
        """计算消息列表的总token数

        Args:
            messages: 消息列表

        Returns:
            int: 总token数
        """
        total = 0
        for message in messages:
            # 角色token
            total += 4  # 每个消息的开销
            total += self.count_tokens(message.content)
            if message.name:
                total += self.count_tokens(message.name)
        # 最后一条消息开销
        total += 2
        return total

    def _convert_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """转换消息格式为OpenAI格式"""
        result = []
        for msg in messages:
            msg_dict: Dict[str, Any] = {
                "role": msg.role.value,
                "content": msg.content,
            }
            if msg.name:
                msg_dict["name"] = msg.name
            result.append(msg_dict)
        return result

    def _convert_tools(self, tools: List) -> List[Dict[str, Any]]:
        """转换工具定义为OpenAI格式"""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in tools
        ]


class AzureOpenAIAdapter(LLMAdapter):
    """Azure OpenAI适配器

    支持Azure OpenAI服务的模型。
    """

    def __init__(
        self,
        api_key: str,
        endpoint: str,
        api_version: str = "2024-02-01",
        deployment_name: str = "gpt-4o",
        timeout: float = 60.0,
    ):
        """初始化Azure OpenAI适配器

        Args:
            api_key: Azure API密钥
            endpoint: Azure端点URL
            api_version: API版本
            deployment_name: 部署名称
            timeout: 超时时间
        """
        from openai import AsyncAzureOpenAI

        self._client = AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
            timeout=timeout,
        )
        self._deployment_name = deployment_name
        self._tokenizer = tiktoken.encoding_for_model("gpt-4o")

    @property
    def provider(self) -> str:
        return "azure-openai"

    @property
    def default_model(self) -> str:
        return self._deployment_name

    async def generate(
        self,
        messages: List[Message],
        config: Optional[GenerationConfig] = None,
    ) -> Response:
        """同步生成"""
        config = config or GenerationConfig()

        # 转换消息格式
        openai_messages = [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
        ]

        response = await self._client.chat.completions.create(
            model=self._deployment_name,
            messages=openai_messages,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

        return Response(
            content=response.choices[0].message.content or "",
            model=self._deployment_name,
        )

    async def stream(
        self,
        messages: List[Message],
        config: Optional[GenerationConfig] = None,
    ) -> AsyncIterator[ResponseChunk]:
        """流式生成"""
        config = config or GenerationConfig()

        openai_messages = [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
        ]

        stream = await self._client.chat.completions.create(
            model=self._deployment_name,
            messages=openai_messages,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield ResponseChunk(content=delta.content, is_final=False)
        yield ResponseChunk(content="", is_final=True)

    def get_model_info(self, model: Optional[str] = None) -> ModelInfo:
        """获取模型信息"""
        return ModelInfo(
            name=self._deployment_name,
            provider="azure-openai",
            max_tokens=128000,
            supports_tools=True,
            supports_streaming=True,
        )

    def count_tokens(self, text: str) -> int:
        """Token计数"""
        return len(self._tokenizer.encode(text))
