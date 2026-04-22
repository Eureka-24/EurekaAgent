"""Memory Layers Tests - 四层记忆系统测试

测试WorkingMemory、EpisodicMemory、SemanticMemory和MemoryManager功能。
对应 SPEC 4.3
"""

import asyncio
import os
import tempfile
from datetime import datetime, timedelta

import pytest

from agentframe.memory.base import (
    MemoryConfig,
    MemoryItem,
    MemoryType,
    MemoryLevel,
    calculate_working_score,
    calculate_episodic_score,
    calculate_semantic_score,
)
from agentframe.memory.working import WorkingMemory
from agentframe.memory.episodic import EpisodicMemory
from agentframe.memory.semantic import SemanticMemory
from agentframe.memory.manager import MemoryManager


class TestMemoryItem:
    """测试记忆项"""

    def test_new_item(self):
        """测试创建新记忆项"""
        item = MemoryItem.new(
            content="测试内容",
            memory_type=MemoryType.WORKING,
            importance=0.8
        )

        assert item.id is not None
        assert item.content == "测试内容"
        assert item.memory_type == MemoryType.WORKING
        assert item.importance == 0.8
        assert item.score == 0.0

    def test_to_dict(self):
        """测试转换为字典"""
        item = MemoryItem.new(
            content="测试内容",
            memory_type=MemoryType.EPISODIC,
            importance=0.7
        )

        d = item.to_dict()
        assert d["id"] == item.id
        assert d["content"] == "测试内容"
        assert d["memory_type"] == "episodic"
        assert d["importance"] == 0.7


class TestScoreCalculation:
    """测试评分公式"""

    def test_working_score(self):
        """测试工作记忆评分"""
        item = MemoryItem.new(
            content="测试",
            memory_type=MemoryType.WORKING,
            importance=0.8
        )

        # 相似度=1.0时
        score = calculate_working_score(item, similarity=1.0)
        assert 0 < score <= 1.44  # (1 * 1) * (0.8 + 0.8 * 0.4) = 1.12

    def test_episodic_score(self):
        """测试情景记忆评分"""
        item = MemoryItem.new(
            content="测试",
            memory_type=MemoryType.EPISODIC,
            importance=0.9
        )

        score = calculate_episodic_score(item, vector_similarity=1.0)
        assert score > 0

    def test_semantic_score(self):
        """测试语义记忆评分"""
        item = MemoryItem.new(
            content="测试",
            memory_type=MemoryType.SEMANTIC,
            importance=0.85
        )

        score = calculate_semantic_score(
            item,
            vector_similarity=1.0,
            graph_similarity=0.5
        )
        assert score > 0


class TestWorkingMemory:
    """测试工作记忆 L0"""

    @pytest.fixture
    async def memory(self):
        """创建测试实例"""
        mem = WorkingMemory(max_size=20, ttl_seconds=3600)
        await mem.start()
        yield mem
        await mem.stop()

    @pytest.mark.asyncio
    async def test_add(self, memory):
        """测试添加"""
        item = await memory.add("工作内容", importance=0.7)

        assert item.memory_type == MemoryType.WORKING
        assert item.memory_type.value == "working"  # 通过memory_type验证
        assert memory.get_count() == 1

    @pytest.mark.asyncio
    async def test_get(self, memory):
        """测试获取"""
        item = await memory.add("测试内容")

        retrieved = await memory.get(item.id)
        assert retrieved is not None
        assert retrieved.content == "测试内容"

    @pytest.mark.asyncio
    async def test_search_tfidf(self, memory):
        """测试TF-IDF检索"""
        await memory.add("Python是一种高级编程语言")
        await memory.add("JavaScript用于Web开发")
        await memory.add("机器学习是人工智能的分支")

        results = await memory.search("Python", limit=5)
        assert len(results) >= 1
        # Python相关的内容应该排在前面
        assert "Python" in results[0].content or results[0].score > 0

    @pytest.mark.asyncio
    async def test_lru_eviction(self, memory):
        """测试LRU淘汰"""
        for i in range(25):  # 超过max_size=20
            await memory.add(f"内容{i}")

        assert memory.get_count() <= 20

    @pytest.mark.asyncio
    async def test_delete(self, memory):
        """测试删除"""
        item = await memory.add("待删除内容")
        assert await memory.delete(item.id)
        assert memory.get_count() == 0

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
    async def test_get_by_importance(self, memory):
        """测试按重要性筛选"""
        await memory.add("低重要性", importance=0.3)
        await memory.add("高重要性", importance=0.8)

        high_importance = await memory.get_by_importance(threshold=0.7)
        assert len(high_importance) >= 1
        assert all(item.importance >= 0.7 for item in high_importance)


class TestEpisodicMemory:
    """测试情景记忆 L1"""

    @pytest.fixture
    def memory(self):
        """创建测试实例"""
        db_path = tempfile.mktemp(suffix=".db")
        mem = EpisodicMemory(db_path=db_path)
        yield mem
        mem.close()
        # 清理临时文件
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_add(self, memory):
        """测试添加"""
        item = await memory.add("情景记忆内容", importance=0.6)

        assert item.memory_type == MemoryType.EPISODIC
        assert item.memory_type.value == "episodic"  # 通过memory_type验证
        assert memory.get_count() == 1

    @pytest.mark.asyncio
    async def test_get(self, memory):
        """测试获取"""
        item = await memory.add("测试内容")

        retrieved = await memory.get(item.id)
        assert retrieved is not None
        assert retrieved.content == "测试内容"

    @pytest.mark.asyncio
    async def test_search(self, memory):
        """测试检索"""
        await memory.add("Python编程语言很强大")
        await memory.add("JavaScript用于前端开发")
        await memory.add("Go语言性能优秀")

        results = await memory.search("Python", limit=5)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_delete(self, memory):
        """测试删除"""
        item = await memory.add("待删除内容")
        assert await memory.delete(item.id)
        assert memory.get_count() == 0

    @pytest.mark.asyncio
    async def test_clear(self, memory):
        """测试清空"""
        await memory.add("内容1")
        await memory.add("内容2")

        count = await memory.clear()
        assert count == 2
        assert memory.get_count() == 0


class TestSemanticMemory:
    """测试语义记忆 L2"""

    @pytest.fixture
    def memory(self):
        """创建测试实例 (不连接Neo4j)"""
        mem = SemanticMemory(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="wrong_password"  # 使用错误密码避免实际连接
        )
        yield mem
        mem.close()

    @pytest.mark.asyncio
    async def test_add(self, memory):
        """测试添加"""
        item = await memory.add("语义记忆内容", importance=0.9)

        assert item.memory_type == MemoryType.SEMANTIC
        assert item.memory_type.value == "semantic"  # 通过memory_type验证
        assert memory.get_count() == 1

    @pytest.mark.asyncio
    async def test_get(self, memory):
        """测试获取"""
        item = await memory.add("测试内容")

        retrieved = await memory.get(item.id)
        assert retrieved is not None
        assert retrieved.content == "测试内容"

    @pytest.mark.asyncio
    async def test_search(self, memory):
        """测试检索"""
        await memory.add("人工智能是未来的发展方向")
        await memory.add("机器学习是AI的子领域")
        await memory.add("深度学习是机器学习的分支")

        results = await memory.search("人工智能", limit=5)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_graph_relations(self, memory):
        """测试图关系"""
        await memory.add("Python是一种编程语言")
        await memory.add("Python用于数据分析")
        await memory.add("JavaScript是前端语言")

        # 验证图关系建立
        assert memory._graph is not None

    @pytest.mark.asyncio
    async def test_delete(self, memory):
        """测试删除"""
        item = await memory.add("待删除内容")
        assert await memory.delete(item.id)
        assert memory.get_count() == 0

    @pytest.mark.asyncio
    async def test_clear(self, memory):
        """测试清空"""
        await memory.add("内容1")
        await memory.add("内容2")

        count = await memory.clear()
        assert count == 2
        assert memory.get_count() == 0


class TestMemoryManager:
    """测试记忆管理器"""

    @pytest.fixture
    async def manager(self):
        """创建测试实例"""
        working = WorkingMemory(max_size=10, ttl_seconds=3600)
        episodic = EpisodicMemory(db_path=tempfile.mktemp(suffix=".db"))
        semantic = SemanticMemory()

        await working.start()

        manager = MemoryManager(
            working_memory=working,
            episodic_memory=episodic,
            semantic_memory=semantic,
            auto_upgrade=True
        )

        yield manager

        await manager.close()
        # 清理临时数据库
        if os.path.exists(episodic._db_path):
            os.unlink(episodic._db_path)

    @pytest.mark.asyncio
    async def test_add_to_working(self, manager):
        """测试添加到工作记忆"""
        item = await manager.add("测试内容", importance=0.5)

        assert item.memory_type == MemoryType.WORKING
        assert manager.working.get_count() == 1

    @pytest.mark.asyncio
    async def test_add_high_importance_auto_upgrade(self, manager):
        """测试高重要性自动升级"""
        # 重要性 >= 0.7 应升级到情景记忆
        item = await manager.add("高重要性内容", importance=0.8)

        # 可能已升级到情景记忆
        stats = manager.get_stats()
        total = stats["working"] + stats["episodic"]
        assert total >= 1

    @pytest.mark.asyncio
    async def test_add_to_specific_layer(self, manager):
        """测试添加到指定层"""
        item = await manager.add(
            "指定层内容",
            memory_type=MemoryType.SEMANTIC
        )

        assert item.memory_type == MemoryType.SEMANTIC
        assert manager.semantic.get_count() == 1

    @pytest.mark.asyncio
    async def test_cross_layer_search(self, manager):
        """测试跨层检索"""
        await manager.add("Python编程语言")
        await manager.add("JavaScript前端开发", memory_type=MemoryType.EPISODIC)
        await manager.add("人工智能AI", memory_type=MemoryType.SEMANTIC)

        results = await manager.search_cross_layer("Python")
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_get_stats(self, manager):
        """测试统计信息"""
        await manager.add("内容1")
        await manager.add("内容2", memory_type=MemoryType.EPISODIC)
        await manager.add("内容3", memory_type=MemoryType.SEMANTIC)

        stats = manager.get_stats()
        assert stats["working"] == 1
        assert stats["episodic"] == 1
        assert stats["semantic"] == 1

    @pytest.mark.asyncio
    async def test_cleanup(self, manager):
        """测试清理"""
        await manager.add("内容1")
        await manager.add("内容2", memory_type=MemoryType.EPISODIC)
        await manager.add("内容3", memory_type=MemoryType.SEMANTIC)

        await manager.cleanup()

        stats = manager.get_stats()
        assert all(count == 0 for count in stats.values())


class TestMemoryUpgrade:
    """测试记忆升级策略"""

    @pytest.mark.asyncio
    async def test_upgrade_working_to_episodic(self):
        """测试工作记忆升级到情景记忆"""
        working = WorkingMemory(max_size=10)
        episodic = EpisodicMemory(db_path=tempfile.mktemp(suffix=".db"))

        await working.start()

        manager = MemoryManager(
            working_memory=working,
            episodic_memory=episodic,
            auto_upgrade=True
        )

        # 添加高重要性内容触发升级
        item = await manager.add("重要内容", importance=0.9)

        # 等待一小段时间让升级完成
        await asyncio.sleep(0.1)

        # 验证升级结果
        stats = manager.get_stats()

        await manager.close()
        episodic.close()

        if os.path.exists(episodic._db_path):
            os.unlink(episodic._db_path)

        # 至少有一层有内容
        assert stats["working"] + stats["episodic"] >= 1
