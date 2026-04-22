"""OpenAI Adapter Tests - OpenAI适配器测试

测试OpenAI适配器的功能，对应 PRD 验收标准 13.1.1

运行: pytest tests/unit/test_llm_openai.py -v
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentframe.llm.base import (
    GenerationConfig,
    Message,
    MessageRole,
    ToolDefinition,
)
from agentframe.llm.openai import OpenAIAdapter


class TestOpenAIAdapterInit:
    """测试OpenAI适配器初始化"""

    def test_init_without_api_key_raises(self):
        """测试没有API密钥时抛出异常"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="API key is required"):
                OpenAIAdapter(api_key=None)

    def test_init_with_env_variable(self):
        """测试从环境变量读取API密钥"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-123"}):
            with patch("agentframe.llm.openai.AsyncOpenAI"):
                adapter = OpenAIAdapter()
                assert adapter._api_key == "test-key-123"

    def test_init_with_custom_api_key(self):
        """测试使用自定义API密钥"""
        with patch("agentframe.llm.openai.AsyncOpenAI"):
            adapter = OpenAIAdapter(api_key="custom-key-456")
            assert adapter._api_key == "custom-key-456"

    def test_init_with_base_url(self):
        """测试使用自定义base_url"""
        with patch("agentframe.llm.openai.AsyncOpenAI") as mock_client:
            adapter = OpenAIAdapter(
                api_key="test-key",
                base_url="https://custom.proxy.com/v1",
            )
            mock_client.assert_called_once()
            call_kwargs = mock_client.call_args.kwargs
            assert call_kwargs["base_url"] == "https://custom.proxy.com/v1"

    def test_init_with_custom_model(self):
        """测试使用自定义模型"""
        with patch("agentframe.llm.openai.AsyncOpenAI"):
            adapter = OpenAIAdapter(
                api_key="test-key",
                model="gpt-3.5-turbo",
            )
            assert adapter._model == "gpt-3.5-turbo"

    def test_default_model_is_gpt_4o(self):
        """测试默认模型是gpt-4o"""
        with patch("agentframe.llm.openai.AsyncOpenAI"):
            adapter = OpenAIAdapter(api_key="test-key")
            assert adapter.default_model == "gpt-4o"

    def test_timeout_configuration(self):
        """测试超时配置"""
        with patch("agentframe.llm.openai.AsyncOpenAI") as mock_client:
            adapter = OpenAIAdapter(api_key="test-key", timeout=30.0)
            call_kwargs = mock_client.call_args.kwargs
            assert call_kwargs["timeout"] == 30.0

    def test_max_retries_configuration(self):
        """测试最大重试次数配置"""
        with patch("agentframe.llm.openai.AsyncOpenAI") as mock_client:
            adapter = OpenAIAdapter(api_key="test-key", max_retries=5)
            call_kwargs = mock_client.call_args.kwargs
            assert call_kwargs["max_retries"] == 5


class TestOpenAIAdapterProperties:
    """测试OpenAI适配器属性"""

    @pytest.fixture
    def adapter(self):
        """创建适配器fixture"""
        with patch("agentframe.llm.openai.AsyncOpenAI"):
            return OpenAIAdapter(api_key="test-key")

    def test_provider(self, adapter):
        """测试provider属性"""
        assert adapter.provider == "openai"

    def test_default_model_property(self, adapter):
        """测试default_model属性"""
        assert adapter.default_model == "gpt-4o"


class TestOpenAIAdapterModelInfo:
    """测试模型信息"""

    @pytest.fixture
    def adapter(self):
        """创建适配器fixture"""
        with patch("agentframe.llm.openai.AsyncOpenAI"):
            return OpenAIAdapter(api_key="test-key")

    def test_get_model_info_default(self, adapter):
        """测试获取默认模型信息"""
        info = adapter.get_model_info()
        assert info.name == "gpt-4o"
        assert info.provider == "openai"
        assert info.supports_tools is True
        assert info.supports_streaming is True

    def test_get_model_info_gpt_4(self, adapter):
        """测试获取GPT-4模型信息"""
        info = adapter.get_model_info("gpt-4")
        assert info.name == "gpt-4"
        assert info.max_tokens == 8192

    def test_get_model_info_gpt_35(self, adapter):
        """测试获取GPT-3.5模型信息"""
        info = adapter.get_model_info("gpt-3.5-turbo")
        assert info.name == "gpt-3.5-turbo"
        assert info.max_tokens == 16385

    def test_get_model_info_gpt_4o_mini(self, adapter):
        """测试获取GPT-4o-mini模型信息"""
        info = adapter.get_model_info("gpt-4o-mini")
        assert info.name == "gpt-4o-mini"
        assert info.supports_tools is True

    def test_get_model_info_unsupported(self, adapter):
        """测试获取不支持的模型抛出异常"""
        with pytest.raises(ValueError, match="Unsupported model"):
            adapter.get_model_info("gpt-999")

    def test_list_models(self, adapter):
        """测试列出所有支持的模型"""
        models = adapter.list_models()
        assert len(models) >= 5
        model_names = [m.name for m in models]
        assert "gpt-4o" in model_names
        assert "gpt-3.5-turbo" in model_names
        assert "gpt-4-turbo" in model_names


class TestOpenAIAdapterTokenCount:
    """测试Token计数"""

    @pytest.fixture
    def adapter(self):
        """创建适配器fixture"""
        with patch("agentframe.llm.openai.AsyncOpenAI"):
            return OpenAIAdapter(api_key="test-key")

    def test_count_tokens_simple(self, adapter):
        """测试简单文本token计数"""
        count = adapter.count_tokens("Hello, world!")
        assert count > 0

    def test_count_tokens_chinese(self, adapter):
        """测试中文token计数"""
        count = adapter.count_tokens("你好世界")
        assert count > 0

    def test_count_tokens_empty(self, adapter):
        """测试空字符串token计数"""
        count = adapter.count_tokens("")
        assert count == 0

    def test_count_tokens_long_text(self, adapter):
        """测试长文本token计数"""
        long_text = "Hello " * 1000
        count = adapter.count_tokens(long_text)
        assert count > 1000

    def test_count_tokens_special_chars(self, adapter):
        """测试特殊字符token计数"""
        special = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        count = adapter.count_tokens(special)
        assert count > 0

    def test_count_tokens_english(self, adapter):
        """测试英文文本token计数"""
        text = "The quick brown fox jumps over the lazy dog"
        count = adapter.count_tokens(text)
        assert count == 9  # 约9个token

    def test_count_messages_tokens_single(self, adapter):
        """测试单条消息token计数"""
        messages = [Message(role=MessageRole.USER, content="Hello")]
        count = adapter.count_messages_tokens(messages)
        assert count > 0

    def test_count_messages_tokens_multiple(self, adapter):
        """测试多条消息token计数"""
        messages = [
            Message(role=MessageRole.SYSTEM, content="You are helpful."),
            Message(role=MessageRole.USER, content="Hello!"),
            Message(role=MessageRole.ASSISTANT, content="Hi there!"),
        ]
        count = adapter.count_messages_tokens(messages)
        assert count > 0


class TestOpenAIAdapterMessageConversion:
    """测试消息格式转换"""

    @pytest.fixture
    def adapter(self):
        """创建适配器fixture"""
        with patch("agentframe.llm.openai.AsyncOpenAI"):
            return OpenAIAdapter(api_key="test-key")

    def test_convert_user_message(self, adapter):
        """测试转换用户消息"""
        messages = [Message(role=MessageRole.USER, content="Hello")]
        converted = adapter._convert_messages(messages)
        assert len(converted) == 1
        assert converted[0]["role"] == "user"
        assert converted[0]["content"] == "Hello"

    def test_convert_system_message(self, adapter):
        """测试转换系统消息"""
        messages = [Message(role=MessageRole.SYSTEM, content="You are helpful.")]
        converted = adapter._convert_messages(messages)
        assert converted[0]["role"] == "system"

    def test_convert_assistant_message(self, adapter):
        """测试转换助手消息"""
        messages = [Message(role=MessageRole.ASSISTANT, content="How can I help?")]
        converted = adapter._convert_messages(messages)
        assert converted[0]["role"] == "assistant"

    def test_convert_tool_message(self, adapter):
        """测试转换工具消息"""
        messages = [
            Message(
                role=MessageRole.TOOL,
                content="Tool result",
                name="calculator",
            )
        ]
        converted = adapter._convert_messages(messages)
        assert converted[0]["role"] == "tool"
        assert converted[0]["name"] == "calculator"

    def test_convert_multiple_messages(self, adapter):
        """测试转换多条消息"""
        messages = [
            Message(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
            Message(role=MessageRole.USER, content="Hello!"),
            Message(role=MessageRole.ASSISTANT, content="Hi there!"),
        ]
        converted = adapter._convert_messages(messages)
        assert len(converted) == 3
        assert converted[0]["role"] == "system"
        assert converted[1]["role"] == "user"
        assert converted[2]["role"] == "assistant"

    def test_convert_message_with_name(self, adapter):
        """测试转换带名称的消息"""
        messages = [
            Message(
                role=MessageRole.TOOL,
                content="Result",
                name="my_tool",
            )
        ]
        converted = adapter._convert_messages(messages)
        assert converted[0]["name"] == "my_tool"


class TestOpenAIAdapterToolConversion:
    """测试工具格式转换"""

    @pytest.fixture
    def adapter(self):
        """创建适配器fixture"""
        with patch("agentframe.llm.openai.AsyncOpenAI"):
            return OpenAIAdapter(api_key="test-key")

    def test_convert_single_tool(self, adapter):
        """测试转换单个工具"""
        tools = [
            ToolDefinition(
                name="web_search",
                description="Search the web",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    },
                    "required": ["query"],
                },
            )
        ]
        converted = adapter._convert_tools(tools)
        assert len(converted) == 1
        assert converted[0]["type"] == "function"
        assert converted[0]["function"]["name"] == "web_search"
        assert converted[0]["function"]["description"] == "Search the web"

    def test_convert_multiple_tools(self, adapter):
        """测试转换多个工具"""
        tools = [
            ToolDefinition(name="tool1", description="Desc 1", parameters={}),
            ToolDefinition(name="tool2", description="Desc 2", parameters={}),
        ]
        converted = adapter._convert_tools(tools)
        assert len(converted) == 2
        assert all(t["type"] == "function" for t in converted)

    def test_convert_empty_tools(self, adapter):
        """测试转换空工具列表"""
        converted = adapter._convert_tools([])
        assert converted == []

    def test_convert_tool_with_complex_parameters(self, adapter):
        """测试转换复杂参数的工兴"""
        tools = [
            ToolDefinition(
                name="calculator",
                description="Perform calculation",
                parameters={
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "Math expression"
                        },
                        "precision": {
                            "type": "integer",
                            "default": 2
                        }
                    },
                    "required": ["expression"],
                },
            )
        ]
        converted = adapter._convert_tools(tools)
        props = converted[0]["function"]["parameters"]["properties"]
        assert "expression" in props
        assert "precision" in props


@pytest.mark.asyncio
class TestOpenAIAdapterGenerate:
    """测试同步生成"""

    @pytest.fixture
    def adapter(self):
        """创建适配器fixture"""
        with patch("agentframe.llm.openai.AsyncOpenAI"):
            return OpenAIAdapter(api_key="test-key")

    async def test_generate_simple(self, adapter):
        """测试简单生成"""
        mock_message = MagicMock()
        mock_message.content = "Hello, world!"
        mock_message.tool_calls = None

        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = MagicMock(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        )
        mock_response.model = "gpt-4o"

        mock_create = AsyncMock(return_value=mock_response)
        adapter._client.chat.completions.create = mock_create

        messages = [Message(role=MessageRole.USER, content="Say hello")]
        response = await adapter.generate(messages)

        assert response.content == "Hello, world!"
        assert response.finish_reason == "stop"
        assert response.usage.total_tokens == 15
        assert response.model == "gpt-4o"

    async def test_generate_with_tool_call(self, adapter):
        """测试生成带工具调用"""
        mock_function = MagicMock()
        mock_function.name = "web_search"
        mock_function.arguments = '{"query": "test"}'

        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_123"
        mock_tool_call.function = mock_function

        mock_message = MagicMock()
        mock_message.content = "Searching..."
        mock_message.tool_calls = [mock_tool_call]

        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "tool_calls"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "gpt-4o"

        mock_create = AsyncMock(return_value=mock_response)
        adapter._client.chat.completions.create = mock_create

        messages = [Message(role=MessageRole.USER, content="Search for AI")]
        response = await adapter.generate(messages)

        assert response.content == "Searching..."
        assert response.tool_calls is not None
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].name == "web_search"
        assert response.tool_calls[0].id == "call_123"

    async def test_generate_with_config(self, adapter):
        """测试使用配置生成"""
        mock_message = MagicMock()
        mock_message.content = "Response"
        mock_message.tool_calls = None

        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = MagicMock(total_tokens=5)

        mock_create = AsyncMock(return_value=mock_response)
        adapter._client.chat.completions.create = mock_create

        config = GenerationConfig(temperature=0.9, max_tokens=100)
        messages = [Message(role=MessageRole.USER, content="Hello")]
        await adapter.generate(messages, config)

        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["temperature"] == 0.9
        assert call_kwargs["max_tokens"] == 100

    async def test_generate_with_system_message(self, adapter):
        """测试带系统消息的生成"""
        mock_message = MagicMock()
        mock_message.content = "Response"
        mock_message.tool_calls = None

        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = MagicMock(total_tokens=5)

        mock_create = AsyncMock(return_value=mock_response)
        adapter._client.chat.completions.create = mock_create

        messages = [
            Message(role=MessageRole.SYSTEM, content="You are helpful."),
            Message(role=MessageRole.USER, content="Hello"),
        ]
        await adapter.generate(messages)

        call_kwargs = mock_create.call_args.kwargs
        assert len(call_kwargs["messages"]) == 2

    async def test_generate_with_multiple_tools(self, adapter):
        """测试带多个工具调用的生成"""
        mock_function1 = MagicMock()
        mock_function1.name = "tool1"
        mock_function1.arguments = "{}"

        mock_tool_call1 = MagicMock()
        mock_tool_call1.id = "call_1"
        mock_tool_call1.function = mock_function1

        mock_function2 = MagicMock()
        mock_function2.name = "tool2"
        mock_function2.arguments = "{}"

        mock_tool_call2 = MagicMock()
        mock_tool_call2.id = "call_2"
        mock_tool_call2.function = mock_function2

        mock_message = MagicMock()
        mock_message.content = "Using tools..."
        mock_message.tool_calls = [mock_tool_call1, mock_tool_call2]

        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "tool_calls"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "gpt-4o"

        mock_create = AsyncMock(return_value=mock_response)
        adapter._client.chat.completions.create = mock_create

        messages = [Message(role=MessageRole.USER, content="Do something")]
        response = await adapter.generate(messages)

        assert len(response.tool_calls) == 2

    async def test_generate_empty_content(self, adapter):
        """测试空内容响应"""
        mock_message = MagicMock()
        mock_message.content = None
        mock_message.tool_calls = None

        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = MagicMock(total_tokens=0)

        mock_create = AsyncMock(return_value=mock_response)
        adapter._client.chat.completions.create = mock_create

        messages = [Message(role=MessageRole.USER, content="Hello")]
        response = await adapter.generate(messages)

        assert response.content == ""


@pytest.mark.asyncio
class TestOpenAIAdapterStream:
    """测试流式生成"""

    @pytest.fixture
    def adapter(self):
        """创建适配器fixture"""
        with patch("agentframe.llm.openai.AsyncOpenAI"):
            return OpenAIAdapter(api_key="test-key")

    async def test_stream_chunks(self, adapter):
        """测试流式响应块"""
        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [MagicMock(delta=MagicMock(content="H"))]

        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [MagicMock(delta=MagicMock(content="e"))]

        mock_chunk3 = MagicMock()
        mock_chunk3.choices = [MagicMock(delta=MagicMock(content="l"))]

        mock_chunk4 = MagicMock()
        mock_chunk4.choices = [MagicMock(delta=MagicMock(content="lo"))]

        async def mock_stream():
            yield mock_chunk1
            yield mock_chunk2
            yield mock_chunk3
            yield mock_chunk4

        mock_create = AsyncMock(return_value=mock_stream())
        adapter._client.chat.completions.create = mock_create

        messages = [Message(role=MessageRole.USER, content="Say hello")]
        chunks = [chunk async for chunk in adapter.stream(messages)]

        assert len(chunks) >= 4
        assert chunks[-1].is_final is True

    async def test_stream_with_config(self, adapter):
        """测试带配置的流式生成"""
        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock(delta=MagicMock(content="Hi"))]

        async def mock_stream():
            yield mock_chunk

        mock_create = AsyncMock(return_value=mock_stream())
        adapter._client.chat.completions.create = mock_create

        config = GenerationConfig(temperature=0.5)
        messages = [Message(role=MessageRole.USER, content="Hello")]

        chunks = [chunk async for chunk in adapter.stream(messages, config)]

        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["temperature"] == 0.5
        assert call_kwargs["stream"] is True

    async def test_stream_empty_chunks(self, adapter):
        """测试空流响应"""
        async def mock_stream():
            return
            yield  # Make it a generator

        mock_create = AsyncMock(return_value=mock_stream())
        adapter._client.chat.completions.create = mock_create

        messages = [Message(role=MessageRole.USER, content="Hello")]
        chunks = [chunk async for chunk in adapter.stream(messages)]

        # 应该只有最终的final chunk
        assert len(chunks) == 1
        assert chunks[0].is_final is True


class TestOpenAIAdapterIntegration:
    """测试集成场景"""

    @pytest.fixture
    def adapter(self):
        """创建适配器fixture"""
        with patch("agentframe.llm.openai.AsyncOpenAI"):
            return OpenAIAdapter(api_key="test-key")

    def test_conversation_flow(self, adapter):
        """测试对话流程的消息转换"""
        messages = [
            Message(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
            Message(role=MessageRole.USER, content="What is 2+2?"),
            Message(role=MessageRole.ASSISTANT, content="2+2 equals 4."),
            Message(role=MessageRole.USER, content="Thanks!"),
        ]

        converted = adapter._convert_messages(messages)
        assert len(converted) == 4
        assert converted[0]["role"] == "system"
        assert converted[1]["role"] == "user"
        assert converted[2]["role"] == "assistant"
        assert converted[3]["role"] == "user"

    def test_tool_registration_flow(self, adapter):
        """测试工具注册流程"""
        tools = [
            ToolDefinition(
                name="calculator",
                description="Perform calculations",
                parameters={
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string"}
                    },
                    "required": ["expression"],
                },
            ),
            ToolDefinition(
                name="web_search",
                description="Search the web",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "default": 5}
                    },
                    "required": ["query"],
                },
            ),
        ]

        converted = adapter._convert_tools(tools)
        assert len(converted) == 2
        assert all(t["type"] == "function" for t in converted)

    def test_model_registry_access(self, adapter):
        """测试模型注册表访问"""
        # 验证支持的模型数量
        assert len(adapter.SUPPORTED_MODELS) >= 5

        # 验证关键模型存在
        assert "gpt-4o" in adapter.SUPPORTED_MODELS
        assert "gpt-3.5-turbo" in adapter.SUPPORTED_MODELS

        # 验证模型信息完整
        for model_name, info in adapter.SUPPORTED_MODELS.items():
            assert info.max_tokens > 0
            assert info.supports_tools is True

    def test_token_encoding_integration(self, adapter):
        """测试token编码集成"""
        # 验证token编码器已初始化
        assert hasattr(adapter, '_tokenizer')
        assert adapter._tokenizer is not None

        # 验证不同类型文本的token计数
        texts = [
            ("Hello, world!", True),
            ("中文测试", True),
            ("", False),
            ("A" * 1000, True),
        ]

        for text, expected_positive in texts:
            count = adapter.count_tokens(text)
            if expected_positive:
                assert count > 0, f"Expected positive count for: {text}"
            else:
                assert count == 0, f"Expected zero count for: {text}"