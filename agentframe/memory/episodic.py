"""EpisodicMemory - 情景记忆 (L1)

SQLite + Qdrant混合存储。
对应 SPEC 4.3.4
"""

import asyncio
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from agentframe.memory.base import (
    Memory,
    MemoryConfig,
    MemoryItem,
    MemoryType,
    MemoryLevel,
    calculate_episodic_score,
)


class EpisodicMemory(Memory):
    """L1层情景记忆

    特性:
    - SQLite结构化存储
    - 内存向量缓存 (Qdrant可选)
    - 时间+重要性双维度淘汰

    评分公式: (向量相似度 × 0.8 + 时间近因性 × 0.2) × (0.8 + 重要性 × 0.4)
    """

    def __init__(
        self,
        config: Optional[MemoryConfig] = None,
        db_path: str = "episodic_memory.db",
        qdrant_client=None,
        lambda_recency: float = 0.05
    ):
        super().__init__(config)
        self._db_path = db_path
        self._qdrant = qdrant_client
        self._lambda_recency = lambda_recency
        self._db: Optional[sqlite3.Connection] = None
        self._vectors: Dict[str, List[float]] = {}  # 内存向量缓存
        self._init_db()

    def _init_db(self):
        """初始化SQLite数据库"""
        self._db = sqlite3.connect(self._db_path, check_same_thread=False)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                importance REAL DEFAULT 0.5,
                timestamp TEXT NOT NULL,
                accessed_at TEXT NOT NULL,
                access_count INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}'
            )
        """)
        self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON memories(timestamp)
        """)
        self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance)
        """)
        self._db.commit()

    @property
    def memory_type(self) -> MemoryType:
        return MemoryType.EPISODIC

    @property
    def memory_level(self) -> MemoryLevel:
        return MemoryLevel.L1

    def _embed(self, text: str) -> List[float]:
        """生成嵌入向量 (简化实现)"""
        import hashlib
        # 使用文本哈希生成伪嵌入向量
        h = hashlib.sha256(text.encode()).digest()
        # 将哈希转换为固定维度的向量
        return [b / 255.0 for b in h[:64]]

    def _vector_similarity(self, v1: List[float], v2: List[float]) -> float:
        """计算余弦相似度"""
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = sum(a * a for a in v1) ** 0.5
        norm2 = sum(b * b for b in v2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    async def add(
        self,
        content: str,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MemoryItem:
        """添加记忆"""
        item = MemoryItem.new(
            content=content,
            memory_type=MemoryType.EPISODIC,
            importance=importance,
            metadata=metadata
        )

        # 存入SQLite
        now = datetime.now().isoformat()
        self._db.execute(
            """INSERT INTO memories (id, content, importance, timestamp, accessed_at, access_count, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (item.id, content, importance, now, now, 0, '{}')
        )
        self._db.commit()

        # 生成并缓存向量
        vector = self._embed(content)
        self._vectors[item.id] = vector

        # 如果有Qdrant客户端，存入Qdrant
        if self._qdrant:
            try:
                self._qdrant.upsert(
                    collection_name="episodic",
                    points=[{"id": item.id, "vector": vector, "payload": {"content": content}}]
                )
            except Exception:
                pass  # Qdrant不可用时继续

        self._items[item.id] = item
        item.score = self.calculate_score(item, vector_similarity=1.0)

        return item

    async def get(self, item_id: str) -> Optional[MemoryItem]:
        """获取记忆"""
        cursor = self._db.execute(
            "SELECT * FROM memories WHERE id = ?", (item_id,)
        )
        row = cursor.fetchone()

        if not row:
            return None

        item = MemoryItem(
            id=row[0],
            content=row[1],
            memory_type=MemoryType.EPISODIC,
            importance=row[2],
            timestamp=datetime.fromisoformat(row[3]),
            accessed_at=datetime.fromisoformat(row[4]),
            access_count=row[5],
            metadata={}
        )

        # 更新访问时间
        self._db.execute(
            "UPDATE memories SET accessed_at = ?, access_count = ? WHERE id = ?",
            (datetime.now().isoformat(), item.access_count + 1, item_id)
        )
        self._db.commit()

        self._items[item.id] = item
        item.score = self.calculate_score(item)

        return item

    async def search(self, query: str, limit: int = 10) -> List[MemoryItem]:
        """向量检索 + 时间近因性"""
        query_vector = self._embed(query)
        results = []

        # 从SQLite获取所有记忆
        cursor = self._db.execute(
            "SELECT id, content, importance, timestamp, accessed_at, access_count FROM memories"
        )
        rows = cursor.fetchall()

        for row in rows:
            item_id = row[0]
            vector = self._vectors.get(item_id)

            if vector:
                similarity = self._vector_similarity(query_vector, vector)
                if similarity > 0.1:  # 阈值过滤
                    item = MemoryItem(
                        id=row[0],
                        content=row[1],
                        memory_type=MemoryType.EPISODIC,
                        importance=row[2],
                        timestamp=datetime.fromisoformat(row[3]),
                        accessed_at=datetime.fromisoformat(row[4]),
                        access_count=row[5],
                        metadata={}
                    )
                    item.score = self.calculate_score(item, vector_similarity=similarity)
                    results.append(item)
            else:
                # 关键词匹配回退
                if query.lower() in row[1].lower():
                    item = MemoryItem(
                        id=row[0],
                        content=row[1],
                        memory_type=MemoryType.EPISODIC,
                        importance=row[2],
                        timestamp=datetime.fromisoformat(row[3]),
                        accessed_at=datetime.fromisoformat(row[4]),
                        access_count=row[5],
                        metadata={}
                    )
                    item.score = self.calculate_score(item, vector_similarity=0.3)
                    results.append(item)

        # 按评分排序
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    async def delete(self, item_id: str) -> bool:
        """删除记忆"""
        self._db.execute("DELETE FROM memories WHERE id = ?", (item_id,))
        self._db.commit()

        if item_id in self._vectors:
            del self._vectors[item_id]

        if item_id in self._items:
            del self._items[item_id]

        if self._qdrant:
            try:
                self._qdrant.delete(collection_name="episodic", points_selector={"points": [item_id]})
            except Exception:
                pass

        return True

    async def clear(self) -> int:
        """清空所有记忆"""
        count = len(self._items)

        self._db.execute("DELETE FROM memories")
        self._db.commit()

        self._items.clear()
        self._vectors.clear()

        if self._qdrant:
            try:
                self._qdrant.delete(collection_name="episodic", points_selector={"filter": {}})
            except Exception:
                pass

        return count

    def calculate_score(self, item: MemoryItem, **kwargs) -> float:
        """计算情景记忆评分"""
        vector_similarity = kwargs.get("vector_similarity", 1.0)
        return calculate_episodic_score(item, vector_similarity)

    async def cleanup_low_score(self, threshold: float = 0.3) -> int:
        """清理低分记忆"""
        cursor = self._db.execute(
            "SELECT id FROM memories WHERE importance < ?", (threshold,)
        )
        to_delete = [row[0] for row in cursor.fetchall()]

        count = 0
        for item_id in to_delete:
            if await self.delete(item_id):
                count += 1

        return count

    def close(self):
        """关闭数据库连接"""
        if self._db:
            self._db.close()
