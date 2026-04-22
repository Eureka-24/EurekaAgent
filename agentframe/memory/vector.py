"""Vector Memory - 向量记忆

基于ChromaDB的向量存储实现，支持语义检索。
对应 SPEC 3.8.4
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from agentframe.memory.base import Memory, MemoryConfig, MemoryItem, MemoryType


class VectorMemory(Memory):
    """向量记忆实现
    
    特性:
    - 使用ChromaDB进行向量存储
    - 支持语义相似度搜索
    - 支持元数据过滤
    """

    def __init__(
        self,
        config: Optional[MemoryConfig] = None,
        persist_directory: Optional[str] = None,
        collection_name: str = "agentframe_memory"
    ):
        super().__init__(config)
        self._persist_directory = persist_directory
        self._collection_name = collection_name
        self._collection = None
        self._initialized = False

    async def initialize(self):
        """初始化向量存储"""
        if self._initialized:
            return
        
        try:
            import chromadb
            from chromadb.config import Settings
            
            client = chromadb.PersistentClient(
                path=self._persist_directory,
                settings=Settings(anonymized_telemetry=False)
            )
            
            self._collection = client.get_or_create_collection(
                name=self._collection_name,
                metadata={"description": "AgentFrame vector memory"}
            )
            
            self._initialized = True
        except ImportError:
            # 如果ChromaDB未安装，使用内存回退
            self._initialized = True
            self._collection = None

    async def add(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        embeddings: Optional[List[float]] = None
    ) -> MemoryItem:
        """添加记忆到向量存储"""
        await self.initialize()
        
        item_id = str(uuid.uuid4())
        
        item = MemoryItem(
            id=item_id,
            content=content,
            memory_type=MemoryType.VECTOR,
            timestamp=datetime.now(),
            metadata=metadata or {},
        )
        
        if self._collection is not None:
            # 添加到ChromaDB
            self._collection.add(
                ids=[item_id],
                documents=[content],
                metadatas=[item.metadata]
            )
        
        self._items[item_id] = item
        return item

    async def get(self, item_id: str) -> Optional[MemoryItem]:
        """获取记忆"""
        return self._items.get(item_id)

    async def search(
        self,
        query: str,
        limit: int = 10,
        where: Optional[Dict[str, Any]] = None,
        include: Optional[List[str]] = None
    ) -> List[MemoryItem]:
        """向量相似度搜索"""
        await self.initialize()
        
        if self._collection is None:
            # 回退到关键词搜索
            return self._keyword_search(query, limit)
        
        try:
            # 使用ChromaDB进行向量搜索
            results = self._collection.query(
                query_texts=[query],
                n_results=limit,
                where=where,
                include=include or ["documents", "metadatas"]
            )
            
            items = []
            if results and results.get("ids"):
                for i, doc_id in enumerate(results["ids"][0]):
                    if doc_id in self._items:
                        items.append(self._items[doc_id])
            
            return items[:limit]
        except Exception:
            return self._keyword_search(query, limit)

    def _keyword_search(self, query: str, limit: int = 10) -> List[MemoryItem]:
        """关键词搜索回退"""
        results = []
        query_lower = query.lower()
        
        for item in self._items.values():
            if query_lower in item.content.lower():
                results.append(item)
        
        return results[:limit]

    async def delete(self, item_id: str) -> bool:
        """删除记忆"""
        if self._collection and item_id in self._items:
            try:
                self._collection.delete(ids=[item_id])
            except Exception:
                pass
        
        if item_id in self._items:
            del self._items[item_id]
            return True
        return False

    async def clear(self) -> int:
        """清空所有记忆"""
        count = len(self._items)
        
        if self._collection:
            try:
                self._collection.delete(where={})
            except Exception:
                pass
        
        self._items.clear()
        return count

    async def get_by_metadata(
        self,
        filter_dict: Dict[str, Any],
        limit: int = 100
    ) -> List[MemoryItem]:
        """根据元数据过滤获取记忆"""
        if self._collection is None:
            return [
                item for item in self._items.values()
                if all(item.metadata.get(k) == v for k, v in filter_dict.items())
            ][:limit]
        
        try:
            results = self._collection.get(
                where=filter_dict,
                limit=limit
            )
            
            items = []
            if results and results.get("ids"):
                for doc_id in results["ids"]:
                    if doc_id in self._items:
                        items.append(self._items[doc_id])
            
            return items[:limit]
        except Exception:
            return []

    async def count(self) -> int:
        """获取记忆数量"""
        if self._collection:
            try:
                return self._collection.count()
            except Exception:
                pass
        return len(self._items)

    async def get_context(
        self,
        query: str,
        max_tokens: int = 4000,
        include_metadata: bool = True
    ) -> str:
        """获取检索上下文（用于RAG）"""
        items = await self.search(query, limit=10)
        
        context_parts = []
        total_tokens = 0
        
        for item in items:
            content = item.content
            # 简单估算token数
            tokens = len(content) // 4
            
            if total_tokens + tokens <= max_tokens:
                context_parts.append(content)
                total_tokens += tokens
            else:
                break
        
        if include_metadata:
            metadata_items = [
                f"[{item.metadata.get('source', 'unknown')}] {item.content[:100]}..."
                for item in items[:3]
            ]
            if metadata_items:
                context_parts.append("相关来源: " + "; ".join(metadata_items))
        
        return "\n\n".join(context_parts)
