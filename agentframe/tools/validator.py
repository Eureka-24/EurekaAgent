"""Tool Validator - 工具参数验证器

实现 JSON Schema 参数验证功能。
对应 PRD 验收标准 13.2.2 和 SPEC 4.2.1
"""

from typing import Any, Dict, List, Optional, Tuple

import structlog

try:
    import jsonschema
    from jsonschema import Draft7Validator, validators
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

logger = structlog.get_logger()


class ValidationError(Exception):
    """验证错误异常"""
    
    def __init__(self, message: str, path: Optional[List[str]] = None):
        super().__init__(message)
        self.message = message
        self.path = path or []
    
    def __str__(self) -> str:
        if self.path:
            return f"{'.'.join(self.path)}: {self.message}"
        return self.message


class ToolParameterValidator:
    """工具参数验证器
    
    实现 JSON Schema 参数验证，支持：
    - 标准 JSON Schema 校验
    - 自定义验证规则
    - 嵌套对象验证
    - 数组项验证
    
    对应 PRD 验收标准 13.2.2:
    - JSON Schema 校验覆盖率100%
    """
    
    def __init__(self, schema: Dict[str, Any]):
        """初始化验证器
        
        Args:
            schema: JSON Schema 定义
        """
        self.schema = schema
        self._errors: List[ValidationError] = []
    
    def validate(self, arguments: Dict[str, Any]) -> Tuple[bool, List[ValidationError]]:
        """验证参数
        
        Args:
            arguments: 待验证的参数
            
        Returns:
            Tuple[bool, List[ValidationError]]: (是否有效, 错误列表)
        """
        self._errors = []
        
        if not HAS_JSONSCHEMA:
            logger.warning("jsonschema not installed, validation skipped")
            return True, []
        
        try:
            # 创建验证器并验证
            validator = Draft7Validator(self.schema)
            
            for error in validator.iter_errors(arguments):
                path = list(error.path) if error.path else []
                error_msg = error.message
                
                # 优化错误消息
                if path:
                    self._errors.append(ValidationError(error_msg, path))
                else:
                    self._errors.append(ValidationError(error_msg))
            
            return len(self._errors) == 0, self._errors
            
        except Exception as e:
            logger.error("validation_error", error=str(e))
            self._errors.append(ValidationError(f"Validation error: {str(e)}"))
            return False, self._errors
    
    def is_valid(self, arguments: Dict[str, Any]) -> bool:
        """快速检查参数是否有效
        
        Args:
            arguments: 待验证的参数
            
        Returns:
            bool: 是否有效
        """
        is_valid, _ = self.validate(arguments)
        return is_valid
    
    def get_errors(self) -> List[ValidationError]:
        """获取验证错误列表"""
        return self._errors
    
    def format_errors(self) -> str:
        """格式化错误消息"""
        if not self._errors:
            return ""
        
        lines = []
        for error in self._errors:
            path_str = ".".join(str(p) for p in error.path) if error.path else "root"
            lines.append(f"  - [{path_str}] {error.message}")
        
        return "\n".join(lines)


def validate_tool_arguments(
    schema: Dict[str, Any],
    arguments: Dict[str, Any]
) -> Tuple[bool, Optional[str]]:
    """验证工具参数的便捷函数
    
    Args:
        schema: JSON Schema 定义
        arguments: 工具参数
        
    Returns:
        Tuple[bool, Optional[str]]: (是否有效, 错误消息)
    """
    validator = ToolParameterValidator(schema)
    is_valid, errors = validator.validate(arguments)
    
    if is_valid:
        return True, None
    else:
        return False, validator.format_errors()


def extend_with_default(
    validator_class,
    property_value,
    schema,
    resolver
):
    """JSON Schema 扩展：支持 default 值
    
    使验证器在缺少可选字段时使用默认值填充
    """
    validate = validator_class(schema, resolver)
    
    def set_defaults(validator, properties, instance, schema):
        for name, subschema in properties.items():
            if "default" in subschema:
                instance.setdefault(name, subschema["default"])
        
        for error in validate.iter_errors(instance, schema):
            yield error
    
    return validators.extend(
        validator_class,
        {"properties": set_defaults}
    )


class SchemaBuilder:
    """Schema 构建器
    
    提供便捷的 JSON Schema 构建方法
    """
    
    @staticmethod
    def string(
        description: str = "",
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        pattern: Optional[str] = None,
        enum: Optional[List[str]] = None,
        default: Optional[str] = None
    ) -> Dict[str, Any]:
        """构建字符串类型 schema"""
        schema = {"type": "string"}
        
        if description:
            schema["description"] = description
        if min_length is not None:
            schema["minLength"] = min_length
        if max_length is not None:
            schema["maxLength"] = max_length
        if pattern:
            schema["pattern"] = pattern
        if enum:
            schema["enum"] = enum
        if default is not None:
            schema["default"] = default
        
        return schema
    
    @staticmethod
    def number(
        description: str = "",
        minimum: Optional[float] = None,
        maximum: Optional[float] = None,
        default: Optional[float] = None
    ) -> Dict[str, Any]:
        """构建数字类型 schema"""
        schema = {"type": "number"}
        
        if description:
            schema["description"] = description
        if minimum is not None:
            schema["minimum"] = minimum
        if maximum is not None:
            schema["maximum"] = maximum
        if default is not None:
            schema["default"] = default
        
        return schema
    
    @staticmethod
    def integer(
        description: str = "",
        minimum: Optional[int] = None,
        maximum: Optional[int] = None,
        default: Optional[int] = None
    ) -> Dict[str, Any]:
        """构建整数类型 schema"""
        schema = {"type": "integer"}
        
        if description:
            schema["description"] = description
        if minimum is not None:
            schema["minimum"] = minimum
        if maximum is not None:
            schema["maximum"] = maximum
        if default is not None:
            schema["default"] = default
        
        return schema
    
    @staticmethod
    def boolean(
        description: str = "",
        default: Optional[bool] = None
    ) -> Dict[str, Any]:
        """构建布尔类型 schema"""
        schema = {"type": "boolean"}
        
        if description:
            schema["description"] = description
        if default is not None:
            schema["default"] = default
        
        return schema
    
    @staticmethod
    def array(
        items: Dict[str, Any],
        description: str = "",
        min_items: Optional[int] = None,
        max_items: Optional[int] = None,
        default: Optional[List] = None
    ) -> Dict[str, Any]:
        """构建数组类型 schema"""
        schema = {
            "type": "array",
            "items": items
        }
        
        if description:
            schema["description"] = description
        if min_items is not None:
            schema["minItems"] = min_items
        if max_items is not None:
            schema["maxItems"] = max_items
        if default is not None:
            schema["default"] = default
        
        return schema
    
    @staticmethod
    def object(
        properties: Dict[str, Dict[str, Any]],
        required: Optional[List[str]] = None,
        description: str = ""
    ) -> Dict[str, Any]:
        """构建对象类型 schema"""
        schema = {
            "type": "object",
            "properties": properties
        }
        
        if required:
            schema["required"] = required
        if description:
            schema["description"] = description
        
        return schema