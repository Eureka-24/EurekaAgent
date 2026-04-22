"""SemanticMemory - 语义记忆 (L2)

Neo4j + Qdrant混合存储。
对应 SPEC 4.3.5
"""

import uuid
from typing import Any, Dict, List, Optional

from agentframe.memory.base import (
    Memory,
    MemoryConfig,
    MemoryItem,
    MemoryType,
    MemoryLevel,
    calculate_semantic_score,
)


class SemanticMemory(Memory):
    """L2层语义记忆

    特性:
    - Neo4j知识图谱存储
    - Qdrant向量存储
    - 图关系推理检索

    评分公式: (向量相似度 × 0.7 + 图相似度 × 0.3) × (0.8 + 重要性 × 0.4)

    注意: Neo4j连接为可选，在未配置时使用内存回退
    """

    def __init__(
        self,
        config: Optional[MemoryConfig] = None,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "password",
        qdrant_client=None,
        embedder=None
    ):
        super().__init__(config)
        self._neo4j_uri = neo4j_uri
        self._neo4j_user = neo4j_user
        self._neo4j_password = neo4j_password
        self._qdrant = qdrant_client
        self._embedder = embedder
        self._neo4j_driver = None
        self._vectors: Dict[str, List[float]] = {}
        self._graph: Dict[str, List[str]] = {}  # node_id -> connected_ids

        # 尝试初始化Neo4j
        self._init_neo4j()

    def _init_neo4j(self):
        """初始化Neo4j连接"""
        try:
            from neo4j import GraphDatabase
            self._neo4j_driver = GraphDatabase.driver(
                self._neo4j_uri,
                auth=(self._neo4j_user, self._neo4j_password)
            )
        except ImportError:
            # Neo4j驱动未安装
            self._neo4j_driver = None
        except Exception:
            # 连接失败
            self._neo4j_driver = None

    def _embed(self, text: str) -> List[float]:
        """生成嵌入向量"""
        if self._embedder:
            return self._embedder.embed(text)

        # 简化实现
        import hashlib
        h = hashlib.sha256(text.encode()).digest()
        return [b / 255.0 for b in h[:64]]

    def _vector_similarity(self, v1: List[float], v2: List[float]) -> float:
        """计算余弦相似度"""
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = sum(a * a for a in v1) ** 0.5
        norm2 = sum(b * b for b in v2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def _calculate_graph_similarity(self, item_id: str, query: str) -> float:
        """计算图相似度 - 基于共同邻居"""
        if item_id not in self._graph:
            return 0.5  # 默认相似度

        item_neighbors = set(self._graph.get(item_id, []))
        query_neighbors = set()

        # 简单实现：查找包含查询词的节点作为查询的邻居
        for nid, content in self._get_all_contents():
            if query.lower() in content.lower():
                query_neighbors.add(nid)

        if not item_neighbors or not query_neighbors:
            return 0.5

        intersection = item_neighbors & query_neighbors
        union = item_neighbors | query_neighbors

        if not union:
            return 0.5

        return len(intersection) / len(union) if union else 0.5

    def _get_all_contents(self) -> List[tuple]:
        """获取所有节点内容"""
        return [(k, v.content) for k, v in self._items.items()]

    @property
    def memory_type(self) -> MemoryType:
        return MemoryType.SEMANTIC

    @property
    def memory_level(self) -> MemoryLevel:
        return MemoryLevel.L2

    def _add_to_graph(self, item_id: str, content: str):
        """将节点添加到图结构"""
        neighbors = []

        # 查找内容相关的现有节点
        for existing_id, existing_content in self._get_all_contents():
            if existing_id == item_id:
                continue
            # 简单的关键词匹配
            if self._is_related(content, existing_content):
                neighbors.append(existing_id)
                # 双向添加邻居关系
                if existing_id in self._graph:
                    self._graph[existing_id].append(item_id)
                else:
                    self._graph[existing_id] = [item_id]

        self._graph[item_id] = neighbors

    def _is_related(self, content1: str, content2: str) -> bool:
        """判断两个内容是否相关"""
        # 简单的共同词检测
        import re
        words1 = set(re.findall(r'\w+', content1.lower()))
        words2 = set(re.findall(r'\w+', content2.lower()))

        # 移除停用词
        stopwords = {'的', '了', '是', '在', '和', '与', '或', '等', '这', '那'}
        words1 = words1 - stopwords
        words2 = words2 - stopwords

        if not words1 or not words2:
            return False

        # 计算Jaccard相似度
        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) > 0.2 if union else False

    async def add(
        self,
        content: str,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MemoryItem:
        """添加记忆到知识图谱"""
        item = MemoryItem.new(
            content=content,
            memory_type=MemoryType.SEMANTIC,
            importance=importance,
            metadata=metadata
        )

        # 生成向量
        vector = self._embed(content)
        self._vectors[item.id] = vector

        # 添加到图结构
        self._add_to_graph(item.id, content)

        # 存入Neo4j (如果可用)
        if self._neo4j_driver:
            try:
                with self._neo4j_driver.session() as session:
                    session.run(
                        "CREATE (m:SemanticMemory {id: $id, content: $content, importance: $importance})",
                        id=item.id, content=content, importance=importance
                    )

                    # 创建关系
                    neighbors = self._graph.get(item.id, [])
                    for neighbor_id in neighbors:
                        session.run(
                            """MATCH (a:SemanticMemory), (b:SemanticMemory)
                               WHERE a.id = $a_id AND b.id = $b_id
                               MERGE (a)-[:RELATED_TO]->(b)""",
                            a_id=item.id, b_id=neighbor_id
                        )
            except Exception:
                pass  # Neo4j不可用时继续

        # 存入Qdrant (如果可用)
        if self._qdrant:
            try:
                self._qdrant.upsert(
                    collection_name="semantic",
                    points=[{"id": item.id, "vector": vector, "payload": {"content": content}}]
                )
            except Exception:
                pass

        self._items[item.id] = item
        item.score = self.calculate_score(item, vector_similarity=1.0, graph_similarity=1.0)

        return item

    async def get(self, item_id: str) -> Optional[MemoryItem]:
        """获取记忆"""
        item = self._items.get(item_id)
        if item:
            item.score = self.calculate_score(item)
        return item

    async def search(self, query: str, limit: int = 10) -> List[MemoryItem]:
        """向量检索 + 图关系推理"""
        query_vector = self._embed(query)
        results = []

        for item_id, item in self._items.items():
            vector = self._vectors.get(item_id)

            if vector:
                vector_sim = self._vector_similarity(query_vector, vector)
                graph_sim = self._calculate_graph_similarity(item_id, query)

                if vector_sim > 0.1 or graph_sim > 0.2:
                    item.score = self.calculate_score(
                        item,
                        vector_similarity=vector_sim,
                        graph_similarity=graph_sim
                    )
                    results.append(item)
            else:
                # 关键词回退
                if query.lower() in item.content.lower():
                    item.score = self.calculate_score(
                        item,
                        vector_similarity=0.3,
                        graph_similarity=0.3
                    )
                    results.append(item)

        # 按评分排序
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    async def delete(self, item_id: str) -> bool:
        """删除记忆"""
        if item_id in self._vectors:
            del self._vectors[item_id]

        if item_id in self._graph:
            # 清理邻居关系
            for neighbor_id in self._graph[item_id]:
                if neighbor_id in self._graph:
                    if item_id in self._graph[neighbor_id]:
                        self._graph[neighbor_id].remove(item_id)
            del self._graph[item_id]

        # 从Neo4j删除
        if self._neo4j_driver:
            try:
                with self._neo4j_driver.session() as session:
                    session.run(
                        "MATCH (m:SemanticMemory {id: $id}) DELETE m",
                        id=item_id
                    )
            except Exception:
                pass

        # 从Qdrant删除
        if self._qdrant:
            try:
                self._qdrant.delete(collection_name="semantic", points_selector={"points": [item_id]})
            except Exception:
                pass

        if item_id in self._items:
            del self._items[item_id]

        return True

    async def clear(self) -> int:
        """清空所有记忆"""
        count = len(self._items)

        self._items.clear()
        self._vectors.clear()
        self._graph.clear()

        if self._neo4j_driver:
            try:
                with self._neo4j_driver.session() as session:
                    session.run("MATCH (m:SemanticMemory) DELETE m")
            except Exception:
                pass

        if self._qdrant:
            try:
                self._qdrant.delete(collection_name="semantic", points_selector={"filter": {}})
            except Exception:
                pass

        return count

    def calculate_score(self, item: MemoryItem, **kwargs) -> float:
        """计算语义记忆评分"""
        vector_sim = kwargs.get("vector_similarity", 1.0)
        graph_sim = kwargs.get("graph_similarity", 0.5)
        return calculate_semantic_score(item, vector_sim, graph_sim)

    def close(self):
        """关闭Neo4j连接"""
        if self._neo4j_driver:
            self._neo4j_driver.close()
