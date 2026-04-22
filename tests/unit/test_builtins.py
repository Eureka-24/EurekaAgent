"""Built-in Tools Tests - 内置工具测试

测试计算器、网络搜索、文件操作工具的功能。
对应 PRD 验收标准 13.2.3

运行: pytest tests/unit/test_builtins.py -v
"""

import asyncio
import json
import os

import pytest

from agentframe.tools.builtins.calculator import CalculatorTool, calculator
from agentframe.tools.builtins.web_search import WebSearchTool, web_search
from agentframe.tools.builtins.file_ops import FileOpsTool, file_ops


class TestCalculatorTool:
    """测试计算器工具"""

    @pytest.fixture
    def tool(self):
        """创建计算器工具实例"""
        return CalculatorTool()

    @pytest.mark.asyncio
    async def test_basic_addition(self, tool):
        """测试基本加法"""
        result = await tool.execute("2 + 3")
        assert result == "5"

    @pytest.mark.asyncio
    async def test_basic_subtraction(self, tool):
        """测试基本减法"""
        result = await tool.execute("10 - 4")
        assert result == "6"

    @pytest.mark.asyncio
    async def test_basic_multiplication(self, tool):
        """测试基本乘法"""
        result = await tool.execute("3 * 4")
        assert result == "12"

    @pytest.mark.asyncio
    async def test_basic_division(self, tool):
        """测试基本除法"""
        result = await tool.execute("10 / 2")
        assert result == "5"

    @pytest.mark.asyncio
    async def test_complex_expression(self, tool):
        """测试复杂表达式"""
        result = await tool.execute("(2 + 3) * 4")
        assert result == "20"

    @pytest.mark.asyncio
    async def test_power_operations(self, tool):
        """测试幂运算"""
        result = await tool.execute("2 ** 3")
        assert result == "8"

    @pytest.mark.asyncio
    async def test_sqrt(self, tool):
        """测试平方根"""
        result = await tool.execute("sqrt(16)")
        assert result == "4"

    @pytest.mark.asyncio
    async def test_trigonometric(self, tool):
        """测试三角函数"""
        result = await tool.execute("sin(0)")
        assert result == "0"

    @pytest.mark.asyncio
    async def test_pi_constant(self, tool):
        """测试pi常量"""
        result = await tool.execute("pi")
        assert "3.14159" in result

    @pytest.mark.asyncio
    async def test_logarithm(self, tool):
        """测试对数"""
        result = await tool.execute("log(e)")
        assert "1" in result

    @pytest.mark.asyncio
    async def test_precision(self, tool):
        """测试精度控制"""
        result = await tool.execute("10 / 3", precision=4)
        assert result == "3.3333"

    @pytest.mark.asyncio
    async def test_invalid_expression(self, tool):
        """测试无效表达式"""
        result = await tool.execute("invalid ++ expression")
        assert "Error" in result


class TestCalculatorFunction:
    """测试计算器便捷函数"""

    async def test_calculator_function_add(self):
        """测试计算器函数加法"""
        result = await calculator("5 + 3")
        assert result == "8"

    async def test_calculator_function_sqrt(self):
        """测试计算器函数平方根"""
        result = await calculator("sqrt(25)")
        assert result == "5"


class TestWebSearchTool:
    """测试网络搜索工具"""

    @pytest.fixture
    def tool(self):
        """创建搜索工具实例"""
        return WebSearchTool(api_key=None)  # 使用模拟数据

    @pytest.mark.asyncio
    async def test_search_baidu(self, tool):
        """测试百度搜索"""
        result = await tool.execute("Python教程")
        
        data = json.loads(result)
        assert data["engine"] == "baidu"
        assert "query" in data
        assert "results" in data

    @pytest.mark.asyncio
    async def test_search_bing(self, tool):
        """测试Bing搜索"""
        result = await tool.execute("AI news", engine="bing")
        
        data = json.loads(result)
        assert data["engine"] == "bing"

    @pytest.mark.asyncio
    async def test_search_google(self, tool):
        """测试Google搜索"""
        result = await tool.execute("machine learning", engine="google")
        
        data = json.loads(result)
        assert data["engine"] == "google"

    @pytest.mark.asyncio
    async def test_search_with_limit(self, tool):
        """测试限制结果数量"""
        result = await tool.execute("test", limit=3)
        
        data = json.loads(result)
        assert "results" in data

    @pytest.mark.asyncio
    async def test_unknown_engine(self, tool):
        """测试未知搜索引擎"""
        result = await tool.execute("test", engine="unknown")
        
        data = json.loads(result)
        assert "error" in data


class TestWebSearchFunction:
    """测试搜索便捷函数"""

    async def test_web_search_function(self):
        """测试搜索便捷函数"""
        result = await web_search("hello world")
        
        data = json.loads(result)
        assert "results" in data or "error" in data


class TestFileOpsTool:
    """测试文件操作工具"""

    @pytest.fixture
    def tool(self):
        """创建文件操作工具实例"""
        return FileOpsTool()

    @pytest.fixture
    def test_file_path(self, tmp_path):
        """创建测试文件路径"""
        return str(tmp_path / "test_file.txt")

    @pytest.mark.asyncio
    async def test_write_file(self, tool, test_file_path):
        """测试写入文件"""
        result = await tool.execute(
            operation="write",
            path=test_file_path,
            content="Hello, World!"
        )
        
        data = json.loads(result)
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_read_file(self, tool, test_file_path):
        """测试读取文件"""
        # 先写入
        await tool.execute(
            operation="write",
            path=test_file_path,
            content="Test content"
        )
        
        # 再读取
        result = await tool.execute(operation="read", path=test_file_path)
        
        data = json.loads(result)
        assert data["success"] is True
        assert data["content"] == "Test content"

    @pytest.mark.asyncio
    async def test_file_exists(self, tool, test_file_path):
        """测试文件存在检查"""
        # 文件不存在
        result = await tool.execute(operation="exists", path=test_file_path)
        
        data = json.loads(result)
        assert data["exists"] is False
        
        # 创建文件
        await tool.execute(
            operation="write",
            path=test_file_path,
            content="data"
        )
        
        # 再次检查
        result = await tool.execute(operation="exists", path=test_file_path)
        
        data = json.loads(result)
        assert data["exists"] is True

    @pytest.mark.asyncio
    async def test_file_info(self, tool, test_file_path):
        """测试获取文件信息"""
        # 创建文件
        await tool.execute(
            operation="write",
            path=test_file_path,
            content="Info test"
        )
        
        result = await tool.execute(operation="info", path=test_file_path)
        
        data = json.loads(result)
        assert data["type"] == "file"
        assert data["name"] == "test_file.txt"
        assert data["size"] > 0

    @pytest.mark.asyncio
    async def test_create_directory(self, tool, tmp_path):
        """测试创建目录"""
        dir_path = str(tmp_path / "new_dir")
        
        result = await tool.execute(operation="create_dir", path=dir_path)
        
        data = json.loads(result)
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_list_directory(self, tool, tmp_path):
        """测试列出目录"""
        # 创建测试文件
        await tool.execute(
            operation="write",
            path=str(tmp_path / "file1.txt"),
            content="content1"
        )
        await tool.execute(
            operation="write",
            path=str(tmp_path / "file2.txt"),
            content="content2"
        )
        
        result = await tool.execute(operation="list", path=str(tmp_path))
        
        data = json.loads(result)
        assert data["total"] >= 2
        assert any(e["name"] == "file1.txt" for e in data["entries"])

    @pytest.mark.asyncio
    async def test_delete_file(self, tool, test_file_path):
        """测试删除文件"""
        # 创建文件
        await tool.execute(
            operation="write",
            path=test_file_path,
            content="To be deleted"
        )
        
        # 删除
        result = await tool.execute(operation="delete", path=test_file_path)
        
        data = json.loads(result)
        assert data["success"] is True
        
        # 确认删除
        result = await tool.execute(operation="exists", path=test_file_path)
        data = json.loads(result)
        assert data["exists"] is False

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, tool):
        """测试读取不存在的文件"""
        result = await tool.execute(
            operation="read",
            path="/nonexistent/path/file.txt"
        )
        
        data = json.loads(result)
        assert "error" in data


class TestFileOpsFunction:
    """测试文件操作便捷函数"""

    @pytest.fixture
    def test_dir(self, tmp_path):
        """创建测试目录"""
        return str(tmp_path)

    async def test_file_ops_write_read(self, test_dir):
        """测试写入和读取"""
        file_path = os.path.join(test_dir, "test.txt")
        
        # 写入
        await file_ops("write", file_path, content="Test data")
        
        # 读取
        result = await file_ops("read", file_path)
        
        data = json.loads(result)
        assert data["success"] is True
        assert data["content"] == "Test data"


class TestToolIntegration:
    """测试工具集成"""

    @pytest.mark.asyncio
    async def test_multiple_tools(self):
        """测试多个工具协作"""
        # 计算器
        calc_result = await calculator("2 + 3")
        assert calc_result == "5"
        
        # 文件操作
        file_result = await file_ops("exists", "/tmp/test.txt")
        data = json.loads(file_result)
        assert "exists" in data

    @pytest.mark.asyncio
    async def test_calculator_in_pipeline(self):
        """测试计算器在管道中使用"""
        # 计算表达式
        result = await calculator("10 * 2 + 5")
        assert result == "25"