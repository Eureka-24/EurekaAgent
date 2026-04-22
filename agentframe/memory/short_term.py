"""Short Term Memory - 短期记忆

基于会话的短期记忆实现，使用LRU缓存策略。
对应 SPEC 3.8.2
"""

import asyncio
import uuid
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import List, Optional

from agentframe.memory.base import Memory, MemoryConfig, MemoryItem, MemoryType


class ShortTermMemory(Memory):
    """短期记忆实现
    
    特性:
    - 基于LRU策略的内存缓存
    - TTL过期机制
    - 自动清理过期记忆
    """

    def __init__(self, config: Optional[MemoryConfig] = None):
        super().__init__(config)
        self._lru_order: OrderedDict[str, datetime] = OrderedDict()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._started = False

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
        cutoff = now - timedelta(seconds=self.config.ttl_seconds)
        
        expired_ids = [
            item_id for item_id, timestamp in self._lru_order.items()
            if timestamp < cutoff
        ]
        
        for item_id in expired_ids:
            if item_id in self._items:
                del self._items[item_id]
            if item_id in self._lru_order:
                del self._lru_order[item_id]

    async def _evict_if_needed(self):
        """LRU淘汰"""
        while len(self._items) >= self.config.max_items:
            if self._lru_order:
                oldest_id = next(iter(self._lru_order))
                await self.delete(oldest_id)

    async def add(self, content: str, metadata: Optional[dict] = None) -> MemoryItem:
        """添加记忆"""
        await self._evict_if_needed()
        
        item_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        item = MemoryItem(
            id=item_id,
            content=content,
            memory_type=MemoryType.SHORT_TERM,
            timestamp=timestamp,
            metadata=metadata or {},
        )
        
        self._items[item_id] = item
        self._lru_order[item_id] = timestamp
        
        return item

    async def get(self, item_id: str) -> Optional[MemoryItem]:
        """获取记忆并更新LRU"""
        item = self._items.get(item_id)
        if item:
            # 更新LRU顺序
            self._lru_order.move_to_end(item_id)
            item.access_count += 1
        return item

    async def search(self, query: str, limit: int = 10) -> List[MemoryItem]:
        """搜索记忆（简单关键词匹配）"""
        results = []
        query_lower = query.lower()
        
        for item in self._items.values():
            if query_lower in item.content.lower():
                results.append(item)
                if len(results) >= limit:
                    break
        
        return results[:limit]

    async def delete(self, item_id: str) -> bool:
        """删除记忆"""
        if item_id in self._items:
            del self._items[item_id]
        if item_id in self._lru_order:
            del self._lru_order[item_id]
        return item_id not in self._items

    async def clear(self) -> int:
        """清空所有记忆"""
        count = len(self._items)
        self._items.clear()
        self._lru_order.clear()
        return count

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

    async def update_importance(self, item_id: str, importance: float) -> bool:
        """更新记忆重要性"""
        item = self._items.get(item_id)
        if item:
            item.importance = max(0.0, min(1.0, importance))
            return True
        return False
