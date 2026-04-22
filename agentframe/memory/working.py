"""WorkingMemory - 工作记忆 (L0)

TTL自动清理 + TF-IDF向量化检索。
对应 SPEC 4.3.3
"""

import asyncio
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from agentframe.memory.base import (
    Memory,
    MemoryConfig,
    MemoryItem,
    MemoryType,
    MemoryLevel,
    calculate_working_score,
)


class WorkingMemory(Memory):
    """L0层工作记忆

    特性:
    - 纯内存存储，TTL自动过期
    - LRU淘汰策略
    - TF-IDF向量化检索

    评分公式: (相似度 × e^(-0.1×t)) × (0.8 + 重要性×0.4)
    """

    def __init__(
        self,
        config: Optional[MemoryConfig] = None,
        max_size: int = 100,
        ttl_seconds: int = 3600
    ):
        super().__init__(config)
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._lru_order: OrderedDict[str, datetime] = OrderedDict()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._started = False
        # TF-IDF 简化实现
        self._tfidf: Dict[str, Dict[str, int]] = {}  # item_id -> {word: count}
        self._word_docs: Dict[str, int] = {}  # word -> doc_count
        self._total_docs: int = 0

    @property
    def memory_type(self) -> MemoryType:
        return MemoryType.WORKING

    @property
    def memory_level(self) -> MemoryLevel:
        return MemoryLevel.L0

    async def start(self):
        """启动清理任务"""
        if not self._started:
            self._started = True
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self):
        """停止清理任务"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def _cleanup_loop(self):
        """定期清理过期记忆"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟检查一次
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break

    async def _cleanup_expired(self):
        """清理过期记忆"""
        now = datetime.now()
        cutoff = now - timedelta(seconds=self._ttl_seconds)

        expired_ids = [
            item_id for item_id, timestamp in self._lru_order.items()
            if timestamp < cutoff
        ]

        for item_id in expired_ids:
            if item_id in self._items:
                await self._remove_from_tfidf(item_id)
                del self._items[item_id]
            if item_id in self._lru_order:
                del self._lru_order[item_id]

    async def _evict_if_needed(self):
        """LRU淘汰超出容量的记忆"""
        while len(self._items) >= self._max_size:
            if self._lru_order:
                oldest_id = next(iter(self._lru_order))
                await self.delete(oldest_id)

    def _tokenize(self, text: str) -> List[str]:
        """简单分词"""
        import re
        words = re.findall(r'\w+', text.lower())
        return [w for w in words if len(w) > 1]

    def _update_tfidf(self, item_id: str, content: str):
        """更新TF-IDF索引"""
        tokens = self._tokenize(content)
        word_counts: Dict[str, int] = {}

        for token in tokens:
            word_counts[token] = word_counts.get(token, 0) + 1
            if self._word_docs.get(token, 0) == 0:
                self._word_docs[token] = 1
            else:
                # 已在其他文档中
                pass

        self._tfidf[item_id] = word_counts
        self._total_docs += 1

        # 更新词频
        for word in word_counts:
            self._word_docs[word] = self._word_docs.get(word, 0) + 1

    async def _remove_from_tfidf(self, item_id: str):
        """从TF-IDF移除"""
        if item_id in self._tfidf:
            del self._tfidf[item_id]

    def _calculate_tfidf_similarity(self, query: str, item_id: str) -> float:
        """计算TF-IDF相似度"""
        if item_id not in self._tfidf:
            return 0.0

        query_tokens = self._tokenize(query)
        item_words = self._tfidf[item_id]

        if not query_tokens or not item_words:
            return 0.0

        # 简单余弦相似度
        query_set = set(query_tokens)
        item_set = set(item_words.keys())

        intersection = query_set & item_set
        if not intersection:
            return 0.0

        # 简化的相似度计算
        return len(intersection) / len(query_set)

    async def add(
        self,
        content: str,
        importance: float = 0.5,
        metadata: Optional[Dict] = None
    ) -> MemoryItem:
        """添加记忆"""
        await self._evict_if_needed()

        item = MemoryItem.new(
            content=content,
            memory_type=MemoryType.WORKING,
            importance=importance,
            metadata=metadata
        )

        self._items[item.id] = item
        self._lru_order[item.id] = datetime.now()
        self._update_tfidf(item.id, content)

        # 计算初始评分
        item.score = self.calculate_score(item, similarity=1.0)

        return item

    async def get(self, item_id: str) -> Optional[MemoryItem]:
        """获取记忆并更新LRU"""
        item = self._items.get(item_id)
        if item:
            # 更新LRU顺序
            self._lru_order.move_to_end(item_id)
            item.accessed_at = datetime.now()
            item.access_count += 1
            # 重新计算评分
            item.score = self.calculate_score(item)
        return item

    async def search(self, query: str, limit: int = 10) -> List[MemoryItem]:
        """TF-IDF向量化检索"""
        results = []
        query_lower = query.lower()

        for item_id, item in self._items.items():
            # TF-IDF相似度
            similarity = self._calculate_tfidf_similarity(query, item_id)

            # 关键词回退匹配
            if similarity == 0:
                if query_lower in item.content.lower():
                    similarity = 0.5

            if similarity > 0:
                item.score = self.calculate_score(item, similarity=similarity)
                results.append(item)

        # 按评分排序
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    async def delete(self, item_id: str) -> bool:
        """删除记忆"""
        if item_id in self._items:
            await self._remove_from_tfidf(item_id)
            del self._items[item_id]
        if item_id in self._lru_order:
            del self._lru_order[item_id]
        return item_id not in self._items

    async def clear(self) -> int:
        """清空所有记忆"""
        count = len(self._items)
        self._items.clear()
        self._lru_order.clear()
        self._tfidf.clear()
        self._word_docs.clear()
        self._total_docs = 0
        return count

    def calculate_score(self, item: MemoryItem, **kwargs) -> float:
        """计算工作记忆评分"""
        similarity = kwargs.get("similarity", 1.0)
        return calculate_working_score(item, similarity)

    async def get_recent(self, limit: int = 10) -> List[MemoryItem]:
        """获取最近的记忆"""
        items = sorted(
            self._items.values(),
            key=lambda x: x.timestamp,
            reverse=True
        )
        return items[:limit]

    async def get_by_importance(self, threshold: float = 0.5) -> List[MemoryItem]:
        """获取重要性高于阈值的所有记忆"""
        return [
            item for item in self._items.values()
            if item.importance >= threshold
        ]
