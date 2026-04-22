"""MemoryManager - 统一记忆管理层

协调四层记忆，实现跨层检索和自动升级。
对应 SPEC 4.3.7
"""

from typing import Dict, List, Optional

from agentframe.memory.base import MemoryItem, MemoryType


class MemoryManager:
    """统一记忆管理层

    协调 WorkingMemory / EpisodicMemory / SemanticMemory 三层记忆。
    PerceptualMemory 为预留扩展。

    功能:
    - 统一add接口，自动分层
    - 跨层检索，评分合并
    - 记忆升级策略 (L0 → L1 → L2)
    - 统一清理接口
    """

    # 升级阈值
    WORKING_TO_EPISODIC_THRESHOLD = 0.7   # 重要性 >= 0.7 升级到情景记忆
    EPISODIC_TO_SEMANTIC_THRESHOLD = 0.85  # 重要性 >= 0.85 升级到语义记忆
    DAYS_TO_SEMANTIC = 7  # 7天后可升级到语义记忆

    def __init__(
        self,
        working_memory=None,
        episodic_memory=None,
        semantic_memory=None,
        auto_upgrade: bool = True
    ):
        self._working = working_memory
        self._episodic = episodic_memory
        self._semantic = semantic_memory
        self._auto_upgrade = auto_upgrade

    @property
    def working(self):
        """获取工作记忆"""
        return self._working

    @property
    def episodic(self):
        """获取情景记忆"""
        return self._episodic

    @property
    def semantic(self):
        """获取语义记忆"""
        return self._semantic

    async def add(
        self,
        content: str,
        importance: float = 0.5,
        memory_type: Optional[MemoryType] = None,
        metadata: Optional[Dict] = None
    ) -> MemoryItem:
        """添加记忆

        Args:
            content: 记忆内容
            importance: 重要性 (0-1)
            memory_type: 指定记忆类型，默认自动分层
            metadata: 附加元数据

        Returns:
            MemoryItem: 创建的记忆项
        """
        if memory_type == MemoryType.WORKING or memory_type is None:
            # 添加到工作记忆
            item = await self._working.add(content, importance, metadata)

            # 检查是否需要升级
            if self._auto_upgrade and importance >= self.WORKING_TO_EPISODIC_THRESHOLD:
                await self._upgrade_working_to_episodic(item)

            return item

        elif memory_type == MemoryType.EPISODIC:
            return await self._episodic.add(content, importance, metadata)

        elif memory_type == MemoryType.SEMANTIC:
            return await self._semantic.add(content, importance, metadata)

        else:
            raise ValueError(f"Unsupported memory type: {memory_type}")

    async def search_cross_layer(
        self,
        query: str,
        limit: int = 10,
        include_types: Optional[List[MemoryType]] = None
    ) -> List[MemoryItem]:
        """跨层检索

        从所有记忆层检索相关记忆，按评分合并排序。

        Args:
            query: 查询文本
            limit: 返回数量限制
            include_types: 指定检索的记忆类型，None表示全部

        Returns:
            List[MemoryItem]: 合并排序后的记忆列表
        """
        results: Dict[str, MemoryItem] = {}

        # 并行检索各层
        if include_types is None or MemoryType.WORKING in include_types:
            if self._working:
                items = await self._working.search(query, limit)
                for item in items:
                    if item.id not in results or item.score > results[item.id].score:
                        results[item.id] = item

        if include_types is None or MemoryType.EPISODIC in include_types:
            if self._episodic:
                items = await self._episodic.search(query, limit)
                for item in items:
                    if item.id not in results or item.score > results[item.id].score:
                        results[item.id] = item

        if include_types is None or MemoryType.SEMANTIC in include_types:
            if self._semantic:
                items = await self._semantic.search(query, limit)
                for item in items:
                    if item.id not in results or item.score > results[item.id].score:
                        results[item.id] = item

        # 按评分排序
        sorted_results = sorted(
            results.values(),
            key=lambda x: x.score,
            reverse=True
        )

        return sorted_results[:limit]

    async def get(self, item_id: str, memory_type: MemoryType) -> Optional[MemoryItem]:
        """从指定层获取记忆"""
        if memory_type == MemoryType.WORKING:
            return await self._working.get(item_id) if self._working else None
        elif memory_type == MemoryType.EPISODIC:
            return await self._episodic.get(item_id) if self._episodic else None
        elif memory_type == MemoryType.SEMANTIC:
            return await self._semantic.get(item_id) if self._semantic else None
        return None

    async def delete(self, item_id: str, memory_type: MemoryType) -> bool:
        """从指定层删除记忆"""
        if memory_type == MemoryType.WORKING:
            return await self._working.delete(item_id) if self._working else False
        elif memory_type == MemoryType.EPISODIC:
            return await self._episodic.delete(item_id) if self._episodic else False
        elif memory_type == MemoryType.SEMANTIC:
            return await self._semantic.delete(item_id) if self._semantic else False
        return False

    async def _upgrade_working_to_episodic(self, item: MemoryItem):
        """将工作记忆升级到情景记忆"""
        if not self._episodic:
            return

        # 在情景记忆中创建新的记忆项
        await self._episodic.add(
            content=item.content,
            importance=item.importance,
            metadata={**item.metadata, "upgraded_from": item.id}
        )

        # 从工作记忆删除原项
        await self._working.delete(item.id)

    async def _upgrade_episodic_to_semantic(self, item: MemoryItem):
        """将情景记忆升级到语义记忆"""
        if not self._semantic:
            return

        # 检查时间条件
        from datetime import datetime, timedelta
        days_elapsed = (datetime.now() - item.timestamp).days

        if days_elapsed < self.DAYS_TO_SEMANTIC:
            return  # 未达到时间阈值

        # 在语义记忆中创建新的记忆项
        await self._semantic.add(
            content=item.content,
            importance=item.importance,
            metadata={**item.metadata, "upgraded_from": item.id}
        )

        # 从情景记忆删除原项
        await self._episodic.delete(item.id)

    async def cleanup(self):
        """清理所有记忆层"""
        if self._working:
            await self._working.clear()
        if self._episodic:
            await self._episodic.clear()
        if self._semantic:
            await self._semantic.clear()

    def get_stats(self) -> Dict[str, int]:
        """获取各层记忆统计"""
        return {
            "working": self._working.get_count() if self._working else 0,
            "episodic": self._episodic.get_count() if self._episodic else 0,
            "semantic": self._semantic.get_count() if self._semantic else 0,
        }

    async def close(self):
        """关闭所有连接"""
        if hasattr(self._working, 'stop'):
            await self._working.stop()
        if hasattr(self._episodic, 'close'):
            self._episodic.close()
        if hasattr(self._semantic, 'close'):
            self._semantic.close()
