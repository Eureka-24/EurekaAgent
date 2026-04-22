"""Tool Registry Tests - 工具注册中心测试

测试工具注册、注销、验证和执行功能。
对应 PRD 验收标准 13.2.1, 13.2.2

运行: pytest tests/unit/test_tool_registry.py -v
"""

import asyncio
from unittest.mock import MagicMock

import pytest

from agentframe.tools.registry import (
    ToolCategory,
    ToolDefinition,
    ToolMetadata,
    ToolRegistry,
    ToolCallResult,
    tool,
)


class TestToolDefinition:
    """测试工具定义"""

    def test_tool_definition_creation(self):
        """测试创建工具定义"""
        tool_def = ToolDefinition(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object"},
            handler=MagicMock()
        )
        
        assert tool_def.name == "test_tool"
        assert tool_def.description == "A test tool"
        assert tool_def.parameters["type"] == "object"

    def test_to_openai_format(self):
        """测试转换为OpenAI格式"""
        tool_def = ToolDefinition(
            name="my_tool",
            description="Tool description",
            parameters={
                "type": "object",
                "properties": {
                    "arg1": {"type": "string"}
                },
                "required": ["arg1"]
            },
            handler=MagicMock()
        )
        
        openai_format = tool_def.to_openai_format()
        
        assert openai_format["type"] == "function"
        assert openai_format["function"]["name"] == "my_tool"
        assert openai_format["function"]["description"] == "Tool description"
        assert "properties" in openai_format["function"]["parameters"]

    def test_validate_parameters_valid(self):
        """测试参数验证-有效参数"""
        tool_def = ToolDefinition(
            name="test",
            description="Test",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string"}
                },
                "required": ["name"]
            },
            handler=MagicMock()
        )
        
        is_valid, error = tool_def.validate_parameters({"name": "Alice"})
        assert is_valid is True
        assert error is None

    def test_validate_parameters_invalid(self):
        """测试参数验证-无效参数"""
        tool_def = ToolDefinition(
            name="test",
            description="Test",
            parameters={
                "type": "object",
                "properties": {
                    "age": {"type": "integer"}
                },
                "required": ["age"]
            },
            handler=MagicMock()
        )
        
        is_valid, error = tool_def.validate_parameters({"age": "not_an_int"})
        assert is_valid is False
        assert error is not None


class TestToolMetadata:
    """测试工具元数据"""

    def test_default_metadata(self):
        """测试默认元数据"""
        metadata = ToolMetadata()
        
        assert metadata.version == "1.0.0"
        assert metadata.category == ToolCategory.CUSTOM
        assert metadata.timeout == 30.0

    def test_custom_metadata(self):
        """测试自定义元数据"""
        metadata = ToolMetadata(
            version="2.0.0",
            author="Test Author",
            tags=["test", "demo"],
            category=ToolCategory.WEB,
            timeout=60.0
        )
        
        assert metadata.version == "2.0.0"
        assert metadata.author == "Test Author"
        assert metadata.category == ToolCategory.WEB
        assert "test" in metadata.tags


class TestToolCategory:
    """测试工具分类"""

    def test_category_values(self):
        """测试分类枚举值"""
        assert ToolCategory.UTILITY.value == "utility"
        assert ToolCategory.MEMORY.value == "memory"
        assert ToolCategory.RAG.value == "rag"
        assert ToolCategory.WEB.value == "web"
        assert ToolCategory.COMPUTATION.value == "computation"
        assert ToolCategory.CUSTOM.value == "custom"


class TestToolRegistry:
    """测试工具注册中心"""

    @pytest.fixture
    def registry(self):
        """创建空的工具注册中心"""
        return ToolRegistry()

    def test_empty_registry(self, registry):
        """测试空注册中心"""
        assert registry.tool_count == 0
        assert len(registry.tools) == 0

    def test_register_function(self, registry):
        """测试注册函数"""
        @registry.register(name="func_tool", description="A function tool")
        async def my_func(arg1: str) -> str:
            return f"Result: {arg1}"
        
        assert "func_tool" in registry.tools
        tool_def = registry.get_tool("func_tool")
        assert tool_def is not None
        assert tool_def.name == "func_tool"

    def test_register_with_decorator(self, registry):
        """测试使用装饰器注册"""
        @tool(name="decorator_tool", description="Decorated tool")
        def sync_func(x: int, y: int) -> int:
            return x + y
        
        # 注意：装饰器注册到全局注册表
        from agentframe.tools.registry import get_registry
        global_reg = get_registry()
        
        assert "decorator_tool" in global_reg.tools

    def test_register_direct(self, registry):
        """测试直接注册工具定义"""
        tool_def = ToolDefinition(
            name="direct_tool",
            description="Direct registration",
            parameters={"type": "object", "properties": {}},
            handler=MagicMock()
        )
        
        registry.register_tool(tool_def)
        
        assert "direct_tool" in registry.tools
        assert registry.tool_count == 1

    def test_unregister(self, registry):
        """测试注销工具"""
        @registry.register(name="temp_tool")
        async def temp_func():
            pass
        
        assert "temp_tool" in registry.tools
        
        async def test_unregister():
            result = await registry.unregister("temp_tool")
            return result
        
        result = asyncio.run(test_unregister())
        
        assert result is True
        assert "temp_tool" not in registry.tools

    def test_unregister_nonexistent(self, registry):
        """测试注销不存在的工具"""
        async def test_unregister():
            return await registry.unregister("nonexistent")
        
        result = asyncio.run(test_unregister())
        
        assert result is False

    def test_get_tool(self, registry):
        """测试获取工具"""
        @registry.register(name="get_test")
        async def func():
            pass
        
        tool_def = registry.get_tool("get_test")
        
        assert tool_def is not None
        assert tool_def.name == "get_test"

    def test_get_nonexistent_tool(self, registry):
        """测试获取不存在的工具"""
        tool_def = registry.get_tool("nonexistent")
        
        assert tool_def is None

    def test_list_tools(self, registry):
        """测试列出工具"""
        @registry.register(name="tool1")
        async def func1():
            pass
        
        @registry.register(name="tool2", metadata=ToolMetadata(category=ToolCategory.WEB))
        async def func2():
            pass
        
        # 列出所有工具
        all_tools = registry.list_tools()
        assert len(all_tools) == 2
        
        # 按分类筛选
        web_tools = registry.list_tools(category=ToolCategory.WEB)
        assert len(web_tools) == 1
        assert web_tools[0].name == "tool2"

    def test_to_openai_tools_format(self, registry):
        """测试转换为OpenAI工具格式"""
        @registry.register(name="openai_tool")
        async def func():
            pass
        
        tools = registry.to_openai_tools_format()
        
        assert len(tools) == 1
        assert tools[0]["type"] == "function"
        assert tools[0]["function"]["name"] == "openai_tool"


@pytest.mark.asyncio
class TestToolRegistryExecute:
    """测试工具执行"""

    @pytest.fixture
    def registry(self):
        """创建带工具的注册中心"""
        reg = ToolRegistry()
        
        @reg.register(name="add")
        async def add(a: int, b: int) -> int:
            return a + b
        
        @reg.register(name="greet")
        async def greet(name: str) -> str:
            return f"Hello, {name}!"
        
        @reg.register(name="echo")
        def echo(message: str) -> str:  # 同步函数
            return message
        
        return reg

    async def test_execute_simple(self, registry):
        """测试执行简单工具"""
        result = await registry.execute(
            name="add",
            arguments={"a": 5, "b": 3},
            tool_call_id="call_1"
        )
        
        assert result.is_error is False
        assert result.tool_call_id == "call_1"
        assert result.tool_name == "add"
        assert result.content == "8"

    async def test_execute_with_string_result(self, registry):
        """测试执行返回字符串的工具"""
        result = await registry.execute(
            name="greet",
            arguments={"name": "Alice"},
            tool_call_id="call_2"
        )
        
        assert result.is_error is False
        assert "Alice" in result.content

    async def test_execute_sync_function(self, registry):
        """测试执行同步函数"""
        result = await registry.execute(
            name="echo",
            arguments={"message": "Hello"}
        )
        
        assert result.is_error is False
        assert result.content == "Hello"

    async def test_execute_nonexistent_tool(self, registry):
        """测试执行不存在的工具"""
        result = await registry.execute(
            name="nonexistent_tool",
            arguments={}
        )
        
        assert result.is_error is True
        assert "not found" in result.content

    async def test_execute_invalid_arguments(self, registry):
        """测试执行时参数验证失败"""
        result = await registry.execute(
            name="add",
            arguments={"a": "not_an_int", "b": 3}
        )
        
        # 参数验证失败
        assert result.is_error is True

    async def test_execute_missing_required(self, registry):
        """测试执行时缺少必需参数"""
        result = await registry.execute(
            name="add",
            arguments={"a": 5}  # 缺少 b
        )
        
        assert result.is_error is True

    async def test_execute_result_to_message_dict(self, registry):
        """测试结果转换为消息字典"""
        result = await registry.execute(
            name="greet",
            arguments={"name": "Bob"},
            tool_call_id="call_3"
        )
        
        msg_dict = result.to_message_dict()
        
        assert msg_dict["role"] == "tool"
        assert msg_dict["tool_call_id"] == "call_3"
        assert msg_dict["name"] == "greet"


@pytest.mark.asyncio
class TestToolCallResult:
    """测试工具调用结果"""

    def test_successful_result(self):
        """测试成功结果"""
        result = ToolCallResult(
            tool_call_id="call_1",
            tool_name="test_tool",
            content="Success",
            is_error=False,
            execution_time=0.5
        )
        
        assert result.is_error is False
        assert result.content == "Success"
        assert result.execution_time == 0.5

    def test_error_result(self):
        """测试错误结果"""
        result = ToolCallResult(
            tool_call_id="call_2",
            tool_name="test_tool",
            content="Error occurred",
            is_error=True,
            error_message="Some error"
        )
        
        assert result.is_error is True
        assert result.error_message == "Some error"

    def test_to_message_dict(self):
        """测试转换为消息字典"""
        result = ToolCallResult(
            tool_call_id="call_123",
            tool_name="my_tool",
            content="Result content"
        )
        
        msg = result.to_message_dict()
        
        assert msg["role"] == "tool"
        assert msg["tool_call_id"] == "call_123"
        assert msg["name"] == "my_tool"
        assert msg["content"] == "Result content"


class TestParameterExtraction:
    """测试参数提取"""

    @pytest.fixture
    def registry(self):
        """创建工具注册中心"""
        return ToolRegistry()

    def test_extract_simple_params(self, registry):
        """测试提取简单参数"""
        async def func(name: str, age: int) -> str:
            return f"{name}: {age}"
        
        params = registry._extract_parameters(func)
        
        assert params["type"] == "object"
        assert "name" in params["properties"]
        assert "age" in params["properties"]
        assert params["properties"]["name"]["type"] == "string"
        assert params["properties"]["age"]["type"] == "number"
        assert "name" in params["required"]
        assert "age" in params["required"]

    def test_extract_with_defaults(self, registry):
        """测试提取带默认值的参数"""
        async def func(name: str, limit: int = 10) -> str:
            return name
        
        params = registry._extract_parameters(func)
        
        assert "name" in params["required"]
        assert "limit" not in params["required"]

    def test_extract_no_params(self, registry):
        """测试提取无参数函数"""
        async def func() -> None:
            pass
        
        params = registry._extract_parameters(func)
        
        assert params["type"] == "object"
        assert len(params["properties"]) == 0


class TestGlobalRegistry:
    """测试全局注册表"""

    def test_get_registry(self):
        """测试获取全局注册表"""
        from agentframe.tools.registry import get_registry
        
        registry = get_registry()
        
        assert isinstance(registry, ToolRegistry)

    def test_register_tool_function(self):
        """测试便捷注册函数"""
        from agentframe.tools.registry import register_tool
        
        async def my_handler(x: str) -> str:
            return x
        
        register_tool(
            name="quick_register",
            description="Quick registration",
            handler=my_handler
        )
        
        from agentframe.tools.registry import get_registry
        registry = get_registry()
        
        assert "quick_register" in registry.tools