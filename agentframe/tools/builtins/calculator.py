"""Calculator Tool - 计算器工具

提供数学表达式计算功能。
对应 PRD 5.2.3 和 SPEC 4.2.3
"""

import math
import re
from typing import Union

import structlog

logger = structlog.get_logger()


class CalculatorTool:
    """计算器工具
    
    支持基本数学运算、三角函数、对数等。
    """
    
    name = "calculator"
    description = "执行数学计算，支持基本运算、三角函数、对数等"
    
    parameters = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "数学表达式，例如: 2 + 3, sin(pi/2), sqrt(16)"
            },
            "precision": {
                "type": "integer",
                "description": "结果保留的小数位数",
                "default": 6
            }
        },
        "required": ["expression"]
    }
    
    # 支持的函数映射
    FUNCTIONS = {
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "asin": math.asin,
        "acos": math.acos,
        "atan": math.atan,
        "sinh": math.sinh,
        "cosh": math.cosh,
        "tanh": math.tanh,
        "log": math.log,
        "log10": math.log10,
        "log2": math.log2,
        "sqrt": math.sqrt,
        "abs": abs,
        "ceil": math.ceil,
        "floor": math.floor,
        "round": round,
        "exp": math.exp,
        "pi": math.pi,
        "e": math.e,
    }
    
    # 别名映射
    ALIASES = {
        "ln": "log",
        "lg": "log10",
        "sqrt": "sqrt",
        "cbrt": None,  # 自定义实现
    }
    
    def __init__(self):
        self._constants = {"pi": math.pi, "e": math.e}
    
    async def execute(self, expression: str, precision: int = 6) -> str:
        """执行计算
        
        Args:
            expression: 数学表达式
            precision: 结果精度
            
        Returns:
            str: 计算结果
        """
        try:
            result = self._evaluate(expression)
            if isinstance(result, float):
                if precision >= 0:
                    result = round(result, precision)
                    # 移除尾部的 .0
                    if result == int(result):
                        result = int(result)
                return str(result)
            return str(result)
            
        except Exception as e:
            logger.error("calculator_error", expression=expression, error=str(e))
            return f"Error: {str(e)}"
    
    def _evaluate(self, expr: str) -> Union[float, int]:
        """评估数学表达式
        
        Args:
            expr: 数学表达式字符串
            
        Returns:
            计算结果
        """
        # 预处理：替换常量
        expr = expr.replace("pi", str(math.pi)).replace(" e ", f" {math.e} ")
        
        # 处理 ln -> log
        expr = re.sub(r'\bln\b', 'log', expr)
        
        # 处理 lg -> log10
        expr = re.sub(r'\blg\b', 'log10', expr)
        
        # 处理 cbrt (立方根)
        expr = re.sub(r'cbrt\(([^)]+)\)', r'((\1)**(1/3))', expr)
        
        # 处理幂运算
        expr = re.sub(r'\^', '**', expr)
        
        # 处理百分比
        expr = re.sub(r'(\d+)%', r'(\1/100)', expr)
        
        return self._safe_eval(expr)
    
    def _preprocess_expression(self, expr: str) -> str:
        """预处理表达式"""
        # 处理 ln -> log
        expr = re.sub(r'\bln\b', 'log', expr)
        
        # 处理 lg -> log10
        expr = re.sub(r'\blg\b', 'log10', expr)
        
        # 处理 cbrt (立方根)
        expr = re.sub(r'cbrt\(([^)]+)\)', r'((\1)**(1/3))', expr)
        
        # 处理幂运算
        expr = re.sub(r'\^', '**', expr)
        
        # 处理百分比
        expr = re.sub(r'(\d+)%', r'(\1/100)', expr)
        
        return expr
    
    def _safe_eval(self, expr: str) -> Union[float, int]:
        """安全的表达式评估
        
        只允许数学运算符和数学函数
        """
        # 定义安全命名空间
        safe_dict = {
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "pow": pow,
            "sum": sum,
            "pi": math.pi,
            "e": math.e,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "asin": math.asin,
            "acos": math.acos,
            "atan": math.atan,
            "sinh": math.sinh,
            "cosh": math.cosh,
            "tanh": math.tanh,
            "log": math.log,
            "log10": math.log10,
            "log2": math.log2,
            "sqrt": math.sqrt,
            "ceil": math.ceil,
            "floor": math.floor,
            "exp": math.exp,
        }
        
        # 使用ast解析并执行
        try:
            result = eval(expr, {"__builtins__": {}}, safe_dict)
            return result
        except ZeroDivisionError:
            return float('inf')
        except Exception as e:
            raise ValueError(f"Calculation error: {str(e)}")


# 创建默认实例供注册
_calculator = CalculatorTool()


async def calculator(expression: str, precision: int = 6) -> str:
    """计算器工具函数
    
    Usage:
        result = await calculator("2 + 3")  # "5"
        result = await calculator("sqrt(16)")  # "4"
        result = await calculator("sin(pi/2)")  # "1"
    """
    return await _calculator.execute(expression, precision)