"""DeepSeek LLM Adapter - DeepSeek模型适配器

实现DeepSeek模型的适配器，支持DeepSeek API兼容格式。
"""

import os
from typing import Any, AsyncIterator, Dict, List, Optional

import tiktoken
import structlog

try:
    from openai import AsyncOpenAI, APIError, RateLimitError, Timeout
except ImportError:
    AsyncOpenAI = None
    APIError = Exception
    RateLimitError = Exception
    Timeout = Exception

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

logger = structlog.get_logger()


class DeepSeekAdapter(LLMAdapter):
    """DeepSeek模型适配器

    支持 DeepSeek-Chat, DeepSeek-Coder 等模型。
    使用 OpenAI 兼容的 API 格式。
    """

    SUPPORTED_MODELS = {
        "deepseek-chat": ModelInfo(
            name="deepseek-chat",
            provider="deepseek",
            max_tokens=64000,
            supports_tools=True,
            supports_streaming=True,
        ),
        "deepseek-coder": ModelInfo(
            name="deepseek-coder",
            provider="deepseek",
            max_tokens=64000,
            supports_tools=True,
            supports_streaming=True,
        ),
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        timeout: float = 60.0,
        max_retries: int = 3,
        default_temperature: float = 0.7,
        default_max_tokens: int = 4096,
    ):
        """初始化DeepSeek适配器

        Args:
            api_key: DeepSeek API密钥
            base_url: API基础URL
            model: 默认模型名称
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            default_temperature: 默认温度参数
            default_max_tokens: 默认最大token数
        """
        if AsyncOpenAI is None:
            raise ImportError("openai package is required for DeepSeek adapter")

        self._api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self._api_key:
            raise ValueError(
                "DeepSeek API key is required. "
                "Set DEEPSEEK_API_KEY environment variable or pass api_key parameter."
            )

        self._base_url = base_url
        self._model = model
        self._timeout = timeout
        self._max_retries = max_retries
        self._default_temperature = default_temperature
        self._default_max_tokens = default_max_tokens

        self._client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
            timeout=timeout,
            max_retries=max_retries,
        )

        self._tokenizer = tiktoken.encoding_for_model("gpt-4o-mini")

    @property
    def provider(self) -> str:
        return "deepseek"

    @property
    def default_model(self) -> str:
        return self._model

    def get_model_info(self, model: Optional[str] = None) -> ModelInfo:
        model_name = model or self._model
        if model_name not in self.SUPPORTED_MODELS:
            raise ValueError(
                f"Unsupported model: {model_name}. "
                f"Supported models: {list(self.SUPPORTED_MODELS.keys())}"
            )
        return self.SUPPORTED_MODELS[model_name]

    def list_models(self) -> List[ModelInfo]:
        return list(self.SUPPORTED_MODELS.values())

    def count_tokens(self, text: str) -> int:
        return len(self._tokenizer.encode(text))

    def count_messages_tokens(self, messages: List[Message]) -> int:
        total = 0
        for msg in messages:
            total += 3
            total += self.count_tokens(msg.content)
            if msg.name:
                total += self.count_tokens(msg.name)
        return total

    def _convert_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        converted = []
        for msg in messages:
            msg_dict = {"role": msg.role.value, "content": msg.content}
            if msg.name:
                msg_dict["name"] = msg.name
            converted.append(msg_dict)
        return converted

    def _convert_tools(self, tools: List[Any]) -> List[Dict[str, Any]]:
        result = []
        for tool in tools:
            if hasattr(tool, "to_openai_format"):
                result.append(tool.to_openai_format())
            elif isinstance(tool, dict):
                result.append(tool)
        return result

    async def generate(
        self,
        messages: List[Message],
        config: Optional[GenerationConfig] = None,
        tools: Optional[List[Any]] = None,
    ) -> Response:
        config = config or GenerationConfig()

        converted_messages = self._convert_messages(messages)
        converted_tools = self._convert_tools(tools) if tools else None

        logger.info(
            "deepseek_generate_start",
            message_count=len(messages),
            model=self._model,
        )

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=converted_messages,
                temperature=config.temperature or self._default_temperature,
                max_tokens=config.max_tokens or self._default_max_tokens,
                tools=converted_tools,
                stream=False,
            )

            choice = response.choices[0]
            message = choice.message

            tool_calls = None
            if message.tool_calls:
                tool_calls = [
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=tc.function.arguments,
                    )
                    for tc in message.tool_calls
                ]

            usage = UsageInfo(
                prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                completion_tokens=response.usage.completion_tokens if response.usage else 0,
                total_tokens=response.usage.total_tokens if response.usage else 0,
            )

            logger.info(
                "deepseek_generate_success",
                finish_reason=choice.finish_reason,
                usage=usage,
            )

            return Response(
                content=message.content or "",
                model=self._model,
                finish_reason=choice.finish_reason or "stop",
                tool_calls=tool_calls,
                usage=usage,
            )

        except Timeout:
            logger.error("deepseek_timeout", timeout=self._timeout)
            raise TimeoutError(f"Request timeout after {self._timeout}s")
        except RateLimitError:
            logger.error("deepseek_rate_limit")
            raise
        except APIError as e:
            logger.error("deepseek_api_error", error=str(e))
            raise

    async def stream(
        self,
        messages: List[Message],
        config: Optional[GenerationConfig] = None,
        tools: Optional[List[Any]] = None,
    ) -> AsyncIterator[ResponseChunk]:
        config = config or GenerationConfig()

        converted_messages = self._convert_messages(messages)
        converted_tools = self._convert_tools(tools) if tools else None

        logger.info(
            "deepseek_stream_start",
            message_count=len(messages),
            model=self._model,
        )

        try:
            stream = await self._client.chat.completions.create(
                model=self._model,
                messages=converted_messages,
                temperature=config.temperature or self._default_temperature,
                max_tokens=config.max_tokens or self._default_max_tokens,
                tools=converted_tools,
                stream=True,
            )

            full_content = ""
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_content += content
                    yield ResponseChunk(
                        content=content,
                        is_final=False,
                    )

            yield ResponseChunk(
                content="",
                is_final=True,
            )

            logger.info("deepseek_stream_complete", total_length=len(full_content))

        except Exception as e:
            logger.error("deepseek_stream_error", error=str(e))
            yield ResponseChunk(
                content=f"Error: {str(e)}",
                is_final=True,
            )
