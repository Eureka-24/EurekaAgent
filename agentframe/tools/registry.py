"""Tool Registry - 工具注册中心

实现工具的定义、注册、管理和执行功能。
对应 PRD 5.2.1, 5.2.2 和 SPEC 4.2.1, 4.2.2
"""

import asyncio
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

import structlog

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

logger = structlog.get_logger()


class ToolCategory(Enum):
    """工具分类枚举"""
    UTILITY = "utility"           # 实用工具
    MEMORY = "memory"             # 记忆工具
    RAG = "rag"                   # RAG工具
    WEB = "web"                   # 网络工具
    COMPUTATION = "computation"    # 计算工具
    CUSTOM = "custom"              # 自定义


@dataclass
class ToolMetadata:
    """工具元数据"""
    version: str = "1.0.0"
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    category: ToolCategory = ToolCategory.CUSTOM
    dependencies: List[str] = field(default_factory=list)
    description: str = ""
    timeout: float = 30.0  # 默认超时时间


@dataclass
class ToolDefinition:
    """工具定义

    对应 PRD 验收标准 13.2.1:
    - 兼容 OpenAI tool calling 格式
    - JSON Schema 定义正确
    """
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema 格式
    handler: Callable
    metadata: ToolMetadata = field(default_factory=ToolMetadata)
    
    def to_openai_format(self) -> Dict[str, Any]:
        """转换为 OpenAI tool calling 格式
        
        对应 PRD 5.2.1: 兼容 OpenAI tool calling 格式
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
    
    def validate_parameters(self, arguments: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """验证参数是否符合 Schema
        
        对应 PRD 验收标准 13.2.2:
        - JSON Schema 校验覆盖率100%
        
        Returns:
            tuple: (is_valid, error_message)
        """
        if not HAS_JSONSCHEMA:
            logger.warning("jsonschema not installed, skipping validation")
            return True, None
            
        try:
            jsonschema.validate(instance=arguments, schema=self.parameters)
            return True, None
        except jsonschema.ValidationError as e:
            return False, str(e.message)


@dataclass
class ToolCallResult:
    """工具调用结果
    
    对应 PRD 验收标准 13.2.2:
    - 工具异常不中断 Agent
    """
    tool_call_id: str = ""
    tool_name: str = ""
    content: str = ""
    is_error: bool = False
    error_message: Optional[str] = None
    execution_time: float = 0.0
    
    def to_message_dict(self) -> Dict[str, Any]:
        """转换为消息字典格式"""
        return {
            "role": "tool",
            "tool_call_id": self.tool_call_id,
            "name": self.tool_name,
            "content": self.content
        }


class ToolRegistry:
    """工具注册中心
    
    实现工具的动态注册、注销、查询和执行。
    对应 SPEC 4.2.1
    
    支持功能:
    - 动态注册/注销工具
    - 热更新不丢请求 (使用锁保护)
    - 异步执行
    - 参数验证
    """
    
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._lock = asyncio.Lock()
    
    @property
    def tools(self) -> Dict[str, ToolDefinition]:
        """获取所有已注册的工具"""
        return self._tools.copy()
    
    @property
    def tool_count(self) -> int:
        """获取工具数量"""
        return len(self._tools)
    
    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """获取指定工具"""
        return self._tools.get(name)
    
    def list_tools(self, category: Optional[ToolCategory] = None) -> List[ToolDefinition]:
        """列出工具
        
        Args:
            category: 可选的分类过滤器
            
        Returns:
            List[ToolDefinition]: 工具列表
        """
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t.metadata.category == category]
        return tools
    
    def register(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[ToolMetadata] = None
    ) -> Callable:
        """工具注册装饰器
        
        对应 PRD 验收标准 13.2.2:
        - 注册<50ms
        
        Usage:
            @registry.register(name="my_tool", description="Do something")
            async def my_tool(arg1: str, arg2: int) -> str:
                ...
        """
        def decorator(func: Callable) -> Callable:
            tool_name = name or func.__name__
            tool_description = description or (func.__doc__ or "").strip()
            
            # 提取函数参数生成 JSON Schema
            parameters = self._extract_parameters(func)
            
            tool_def = ToolDefinition(
                name=tool_name,
                description=tool_description,
                parameters=parameters,
                handler=func,
                metadata=metadata or ToolMetadata()
            )
            
            # 同步添加到注册表（装饰器在模块加载时执行）
            self._tools[tool_name] = tool_def
            logger.info("tool_registered", tool_name=tool_name)
            
            return func
        
        return decorator
    
    def register_tool(self, tool_def: ToolDefinition) -> None:
        """直接注册工具定义
        
        Args:
            tool_def: 工具定义对象
        """
        self._tools[tool_def.name] = tool_def
        logger.info("tool_registered_direct", tool_name=tool_def.name)
    
    async def unregister(self, name: str) -> bool:
        """注销工具
        
        对应 SPEC 4.2.1: 动态注册/注销
        
        Args:
            name: 工具名称
            
        Returns:
            bool: 是否成功注销
        """
        async with self._lock:
            if name in self._tools:
                del self._tools[name]
                logger.info("tool_unregistered", tool_name=name)
                return True
            return False
    
    async def execute(
        self,
        name: str,
        arguments: Dict[str, Any],
        tool_call_id: str = "",
        timeout: Optional[float] = None
    ) -> ToolCallResult:
        """执行工具
        
        对应 PRD 验收标准 13.2.2:
        - 工具异常不中断 Agent
        
        Args:
            name: 工具名称
            arguments: 工具参数
            tool_call_id: 工具调用ID
            timeout: 可选的超时时间
            
        Returns:
            ToolCallResult: 执行结果
        """
        import time
        start_time = time.time()
        
        # 检查工具是否存在
        if name not in self._tools:
            return ToolCallResult(
                tool_call_id=tool_call_id,
                tool_name=name,
                content=f"Tool not found: {name}",
                is_error=True,
                error_message=f"Tool '{name}' is not registered",
                execution_time=time.time() - start_time
            )
        
        tool = self._tools[name]
        actual_timeout = timeout or tool.metadata.timeout
        
        try:
            # 参数验证
            is_valid, error_msg = tool.validate_parameters(arguments)
            if not is_valid:
                return ToolCallResult(
                    tool_call_id=tool_call_id,
                    tool_name=name,
                    content=f"Invalid arguments: {error_msg}",
                    is_error=True,
                    error_message=error_msg,
                    execution_time=time.time() - start_time
                )
            
            # 执行工具
            if asyncio.iscoroutinefunction(tool.handler):
                result = await asyncio.wait_for(
                    tool.handler(**arguments),
                    timeout=actual_timeout
                )
            else:
                result = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: tool.handler(**arguments)
                )
            
            # 转换结果为字符串
            if result is not None:
                content = json.dumps(result, ensure_ascii=False) if isinstance(result, (dict, list)) else str(result)
            else:
                content = ""
            
            return ToolCallResult(
                tool_call_id=tool_call_id,
                tool_name=name,
                content=content,
                is_error=False,
                execution_time=time.time() - start_time
            )
            
        except asyncio.TimeoutError:
            error_msg = f"Tool execution timeout after {actual_timeout}s"
            logger.error("tool_timeout", tool_name=name, timeout=actual_timeout)
            return ToolCallResult(
                tool_call_id=tool_call_id,
                tool_name=name,
                content=error_msg,
                is_error=True,
                error_message=error_msg,
                execution_time=time.time() - start_time
            )
        except Exception as e:
            # 工具异常不中断Agent
            error_msg = str(e)
            logger.error("tool_execution_error", tool_name=name, error=error_msg)
            return ToolCallResult(
                tool_call_id=tool_call_id,
                tool_name=name,
                content=f"Error: {error_msg}",
                is_error=True,
                error_message=error_msg,
                execution_time=time.time() - start_time
            )
    
    def to_openai_tools_format(self) -> List[Dict[str, Any]]:
        """获取所有工具的 OpenAI 格式列表
        
        Returns:
            List[Dict]: OpenAI tool calling 格式的工具列表
        """
        return [tool.to_openai_format() for tool in self._tools.values()]
    
    def _extract_parameters(self, func: Callable) -> Dict[str, Any]:
        """从函数签名提取 JSON Schema 参数定义
        
        对应 SPEC 4.2.1: 参数提取
        """
        import inspect
        
        try:
            sig = inspect.signature(func)
        except (ValueError, TypeError):
            # 无法获取签名，返回空 schema
            return {
                "type": "object",
                "properties": {},
                "required": []
            }
        
        properties = {}
        required = []
        
        for param_name, param in sig.parameters.items():
            param_schema = {"type": "string"}  # 默认类型
            
            # 检查注解
            if param.annotation != inspect.Parameter.empty:
                annotation = param.annotation
                
                # 处理 Optional 类型
                origin = getattr(annotation, "__origin__", None)
                if origin is list:
                    param_schema = {"type": "array"}
                elif origin is dict:
                    param_schema = {"type": "object"}
                elif annotation in (int, float):
                    param_schema = {"type": "number"}
                elif annotation is bool:
                    param_schema = {"type": "boolean"}
                
                # 检查是否可空（Union with None）
                if origin is Union:
                    args = getattr(annotation, "__args__", ())
                    non_none_args = [a for a in args if a is not type(None)]
                    if len(non_none_args) == 1:
                        annotation = non_none_args[0]
                
                # 处理 List 类型
                if getattr(annotation, "__origin__", None) is list:
                    item_type = getattr(annotation, "__args__", (None,))[0]
                    if item_type in (int, float):
                        param_schema = {"type": "array", "items": {"type": "number"}}
                    elif item_type is str:
                        param_schema = {"type": "array", "items": {"type": "string"}}
                    elif item_type is bool:
                        param_schema = {"type": "array", "items": {"type": "boolean"}}
                    else:
                        param_schema = {"type": "array", "items": {"type": "string"}}
            
            # 检查默认值
            if param.default == inspect.Parameter.empty:
                required.append(param_name)
            
            properties[param_name] = param_schema
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }


# 全局默认工具注册中心实例
_default_registry = ToolRegistry()


# 装饰器函数，用于快速注册工具
def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    metadata: Optional[ToolMetadata] = None
) -> Callable:
    """工具注册装饰器
    
    对应 SPEC 4.2.1: @tool 装饰器
    
    Usage:
        @tool(name="web_search", description="Search the web")
        async def web_search(query: str) -> str:
            ...
    """
    return _default_registry.register(
        name=name,
        description=description,
        metadata=metadata
    )


# 导出便捷函数
def get_registry() -> ToolRegistry:
    """获取默认工具注册中心"""
    return _default_registry


def register_tool(
    name: str,
    description: str,
    handler: Callable,
    metadata: Optional[ToolMetadata] = None
) -> None:
    """便捷的工具注册函数
    
    Usage:
        async def my_handler(arg1: str) -> str:
            return f"Hello, {arg1}"
        
        register_tool(
            name="my_tool",
            description="A simple tool",
            handler=my_handler
        )
    """
    tool_def = ToolDefinition(
        name=name,
        description=description,
        parameters=_default_registry._extract_parameters(handler),
        handler=handler,
        metadata=metadata or ToolMetadata()
    )
    _default_registry.register_tool(tool_def)


def execute_tool(
    name: str,
    arguments: Dict[str, Any],
    tool_call_id: str = "",
    timeout: Optional[float] = None
) -> ToolCallResult:
    """便捷的工具执行函数"""
    return _default_registry.execute(name, arguments, tool_call_id, timeout)