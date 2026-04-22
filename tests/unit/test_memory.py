"""Memory Tests - 记忆系统测试

测试短期记忆、工作记忆和向量记忆功能。
"""

import asyncio
from datetime import datetime, timedelta

import pytest

from agentframe.memory.base import MemoryConfig, MemoryItem, MemoryType
from agentframe.memory.short_term import ShortTermMemory
from agentframe.memory.working import WorkingMemory
from agentframe.memory.vector import VectorMemory


class TestShortTermMemory:
    """测试短期记忆"""

    @pytest.fixture
    async def memory(self):
        """创建测试实例"""
        config = MemoryConfig(max_items=10, ttl_seconds=60)
        mem = ShortTermMemory(config)
        yield mem
        await mem.stop()

    @pytest.mark.asyncio
    async def test_add_and_get(self, memory):
        """测试添加和获取"""
        item = await memory.add("测试内容", {"key": "value"})
        
        assert item.id is not None
        assert item.content == "测试内容"
        assert item.memory_type == MemoryType.SHORT_TERM
        
        retrieved = await memory.get(item.id)
        assert retrieved is not None
        assert retrieved.content == "测试内容"

    @pytest.mark.asyncio
    async def test_search(self, memory):
        """测试搜索"""
        await memory.add("Python编程语言")
        await memory.add("JavaScript是前端语言")
        await memory.add("Go语言很高效")
        
        results = await memory.search("Python")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_lru_eviction(self, memory):
        """测试LRU淘汰"""
        for i in range(12):  # 超过max_items=10
            await memory.add(f"内容{i}")
        
        count = memory.get_count()
        assert count == 10

    @pytest.mark.asyncio
    async def test_delete(self, memory):
        """测试删除"""
        item = await memory.add("待删除内容")
        assert await memory.delete(item.id)
        assert await memory.get(item.id) is None

    @pytest.mark.asyncio
    async def test_clear(self, memory):
        """测试清空"""
        await memory.add("内容1")
        await memory.add("内容2")
        
        count = await memory.clear()
        assert count == 2
        assert memory.get_count() == 0

    @pytest.mark.asyncio
    async def test_get_recent(self, memory):
        """测试获取最近记忆"""
        for i in range(5):
            await memory.add(f"内容{i}")
        
        recent = await memory.get_recent(limit=3)
        assert len(recent) == 3

    @pytest.mark.asyncio
    async def test_update_importance(self, memory):
        """测试更新重要性"""
        item = await memory.add("高重要性内容")
        
        assert await memory.update_importance(item.id, 0.9)
        
        retrieved = await memory.get(item.id)
        assert retrieved.importance == 0.9


class TestWorkingMemory:
    """测试工作记忆"""

    @pytest.fixture
    def memory(self):
        return WorkingMemory()

    @pytest.mark.asyncio
    async def test_add(self, memory):
        """测试添加"""
        item = await memory.add("工作内容")
        assert item.memory_type == MemoryType.WORKING

    @pytest.mark.asyncio
    async def test_variables(self, memory):
        """测试变量存取"""
        await memory.set_var("counter", 0)
        await memory.set_var("name", "test")
        
        assert await memory.get_var("counter") == 0
        assert await memory.get_var("name") == "test"
        assert await memory.get_var("nonexistent", "default") == "default"

    @pytest.mark.asyncio
    async def test_delete_var(self, memory):
        """测试删除变量"""
        await memory.set_var("temp", "value")
        assert await memory.delete_var("temp")
        assert await memory.get_var("temp") is None

    @pytest.mark.asyncio
    async def test_thinking_history(self, memory):
        """测试思考历史"""
        await memory.add_thinking("让我思考这个问题", "reasoning")
        await memory.add_thinking("推理步骤1", "step")
        
        history = await memory.get_thinking_history()
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_tool_results(self, memory):
        """测试工具结果"""
        await memory.add_tool_result("calculator", "结果: 42", True)
        
        results = await memory.get_tool_results()
        assert len(results) == 1
        assert results[0].metadata["tool_name"] == "calculator"


class TestVectorMemory:
    """测试向量记忆"""

    @pytest.fixture
    async def memory(self):
        mem = VectorMemory(collection_name="test_memory")
        yield mem
        await mem.clear()

    @pytest.mark.asyncio
    async def test_add(self, memory):
        """测试添加"""
        item = await memory.add("向量内容", metadata={"source": "test"})
        assert item.memory_type == MemoryType.VECTOR

    @pytest.mark.asyncio
    async def test_search(self, memory):
        """测试搜索"""
        await memory.add("Python是一种高级编程语言", metadata={"source": "python"})
        await memory.add("JavaScript用于Web开发", metadata={"source": "js"})
        await memory.add("机器学习是AI的分支", metadata={"source": "ml"})
        
        results = await memory.search("编程", limit=2)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_delete(self, memory):
        """测试删除"""
        item = await memory.add("待删除内容", metadata={"source": "test"})
        assert await memory.delete(item.id)
        assert await memory.get(item.id) is None

    @pytest.mark.asyncio
    async def test_count(self, memory):
        """测试计数"""
        await memory.add("内容1", metadata={"source": "test1"})
        await memory.add("内容2", metadata={"source": "test2"})
        
        count = await memory.count()
        assert count == 2

    @pytest.mark.asyncio
    async def test_get_context(self, memory):
        """测试获取上下文"""
        await memory.add("Python是易学的语言", metadata={"source": "python"})
        await memory.add("Python有丰富的库", metadata={"source": "python"})
        await memory.add("JavaScript用于前端", metadata={"source": "js"})
        
        context = await memory.get_context("Python", max_tokens=1000)
        assert "Python" in context


class TestMemoryItem:
    """测试记忆项"""

    def test_to_dict(self):
        """测试转换为字典"""
        item = MemoryItem(
            id="test-id",
            content="测试内容",
            memory_type=MemoryType.SHORT_TERM,
            metadata={"key": "value"},
            importance=0.8
        )
        
        d = item.to_dict()
        assert d["id"] == "test-id"
        assert d["content"] == "测试内容"
        assert d["memory_type"] == "short_term"
        assert d["importance"] == 0.8


class TestMemoryIntegration:
    """测试记忆系统集成"""

    @pytest.mark.asyncio
    async def test_multi_memory_usage(self):
        """测试多记忆协同使用"""
        short_mem = ShortTermMemory()
        work_mem = WorkingMemory()
        vector_mem = VectorMemory()
        
        try:
            # 短期记忆存储会话内容
            short_item = await short_mem.add("用户说要学习Python")
            
            # 工作记忆记录当前状态
            await work_mem.set_var("current_topic", "Python")
            await work_mem.add_thinking("分析用户意图")
            
            # 向量记忆存储知识
            vector_item = await vector_mem.add("Python教程: 变量、数据类型、函数", metadata={"source": "tutorial"})
            
            assert short_mem.get_count() == 1
            assert work_mem.get_var("current_topic") == "Python"
            assert vector_mem.get_count() == 1
            
            # 跨记忆检索
            vector_results = await vector_mem.search("Python教程")
            assert len(vector_results) >= 1
            
        finally:
            await short_mem.clear()
            await work_mem.clear()
            await vector_mem.clear()
            await short_mem.stop()
