"""LLM Adapter Base Tests - LLM适配器基础测试

测试LLM适配器基类和通用功能
"""

import pytest
from agentframe.llm.base import (
    GenerationConfig,
    LLMAdapter,
    Message,
    MessageRole,
    ModelInfo,
    Response,
    ResponseChunk,
    ToolCall,
    ToolDefinition,
    ToolCallResult,
    UsageInfo,
)


class TestMessage:
    """测试消息类"""

    def test_message_creation(self):
        """测试消息创建"""
        message = Message(
            role=MessageRole.USER,
            content="Hello, world!",
        )
        assert message.role == MessageRole.USER
        assert message.content == "Hello, world!"
        assert message.name is None
        assert message.tool_calls is None

    def test_message_with_tool_calls(self):
        """测试带工具调用的消息"""
        tool_call = ToolCall(
            id="call_123",
            name="web_search",
            arguments={"query": "test"},
        )
        message = Message(
            role=MessageRole.ASSISTANT,
            content="Searching...",
            tool_calls=[tool_call],
        )
        assert len(message.tool_calls) == 1
        assert message.tool_calls[0].name == "web_search"

    def test_message_role_enum(self):
        """测试消息角色枚举"""
        assert MessageRole.SYSTEM.value == "system"
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
        assert MessageRole.TOOL.value == "tool"


class TestGenerationConfig:
    """测试生成配置类"""

    def test_default_config(self):
        """测试默认配置"""
        config = GenerationConfig()
        assert config.temperature == 0.7
        assert config.max_tokens == 4096
        assert config.top_p == 1.0
        assert config.top_k == 50
        assert config.tools is None
        assert config.stream is False

    def test_custom_config(self):
        """测试自定义配置"""
        config = GenerationConfig(
            temperature=0.9,
            max_tokens=2048,
            tools=[],
        )
        assert config.temperature == 0.9
        assert config.max_tokens == 2048
        assert config.tools == []


class TestToolDefinition:
    """测试工具定义类"""

    def test_tool_definition(self):
        """测试工具定义创建"""
        tool_def = ToolDefinition(
            name="calculator",
            description="Perform calculations",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression",
                    }
                },
                "required": ["expression"],
            },
        )
        assert tool_def.name == "calculator"
        assert "expression" in tool_def.parameters["properties"]


class TestModelInfo:
    """测试模型信息类"""

    def test_model_info(self):
        """测试模型信息创建"""
        info = ModelInfo(
            name="gpt-4",
            provider="openai",
            max_tokens=8192,
            supports_tools=True,
            supports_streaming=True,
        )
        assert info.name == "gpt-4"
        assert info.provider == "openai"
        assert info.supports_tools is True
        assert info.supports_streaming is True


class TestResponse:
    """测试响应类"""

    def test_response_without_tools(self):
        """测试不带工具调用的响应"""
        response = Response(
            content="Hello!",
            model="gpt-4",
        )
        assert response.content == "Hello!"
        assert response.tool_calls is None
        assert response.usage is None

    def test_response_with_tools(self):
        """测试带工具调用的响应"""
        tool_call = ToolCall(
            id="call_456",
            name="get_weather",
            arguments={"city": "Beijing"},
        )
        response = Response(
            content="Let me check the weather.",
            tool_calls=[tool_call],
        )
        assert response.tool_calls is not None
        assert len(response.tool_calls) == 1

    def test_response_with_usage(self):
        """测试带使用量信息的响应"""
        usage = UsageInfo(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )
        response = Response(
            content="Test response",
            usage=usage,
        )
        assert response.usage.total_tokens == 150


class TestToolCall:
    """测试工具调用类"""

    def test_tool_call_creation(self):
        """测试工具调用创建"""
        tool_call = ToolCall(
            id="call_789",
            name="search",
            arguments={"query": "AI agents"},
        )
        assert tool_call.id == "call_789"
        assert tool_call.name == "search"
        assert tool_call.arguments["query"] == "AI agents"


class TestToolCallResult:
    """测试工具调用结果类"""

    def test_successful_result(self):
        """测试成功结果"""
        result = ToolCallResult(
            tool_call_id="call_123",
            content="Search results here",
            is_error=False,
        )
        assert result.is_error is False

    def test_error_result(self):
        """测试错误结果"""
        result = ToolCallResult(
            tool_call_id="call_456",
            content="Error: Network timeout",
            is_error=True,
        )
        assert result.is_error is True


class TestResponseChunk:
    """测试流式响应块类"""

    def test_chunk_not_final(self):
        """测试非最终块"""
        chunk = ResponseChunk(
            content="Hello",
            is_final=False,
        )
        assert chunk.is_final is False

    def test_chunk_final(self):
        """测试最终块"""
        chunk = ResponseChunk(
            content="",
            is_final=True,
        )
        assert chunk.is_final is True


class TestLLMAdapterInterface:
    """测试LLMAdapter接口"""

    def test_adapter_is_abstract(self):
        """测试适配器是抽象类"""
        with pytest.raises(TypeError):
            LLMAdapter()

    def test_adapter_methods_are_abstract(self):
        """测试适配器方法是抽象的"""

        class MockAdapter(LLMAdapter):
            @property
            def provider(self) -> str:
                return "mock"

            @property
            def default_model(self) -> str:
                return "mock-model"

            async def generate(self, messages, config):
                pass

            async def stream(self, messages, config):
                yield

            def get_model_info(self, model=None):
                pass

            def count_tokens(self, text: str) -> int:
                return 0

        adapter = MockAdapter()
        assert adapter.provider == "mock"
        assert adapter.default_model == "mock-model"
