"""Memory Base - 记忆基类

定义四层记忆系统的统一接口和评分公式。
对应 SPEC 4.3
"""

import math
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class MemoryType(Enum):
    """记忆类型枚举 - 四层架构"""
    WORKING = "working"           # L0: 工作记忆
    EPISODIC = "episodic"       # L1: 情景记忆
    SEMANTIC = "semantic"        # L2: 语义记忆
    PERCEPTUAL = "perceptual"    # L3: 感知记忆 (留白)


class MemoryLevel(Enum):
    """记忆层级枚举"""
    L0 = 0   # 工作记忆
    L1 = 1   # 情景记忆
    L2 = 2   # 语义记忆
    L3 = 3   # 感知记忆


@dataclass
class MemoryItem:
    """记忆项 - 统一数据结构"""
    id: str
    content: str
    memory_type: MemoryType
    importance: float = 1.0  # 重要性 0-1
    timestamp: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    access_count: int = 0
    score: float = 0.0  # 计算后的评分

    @staticmethod
    def new(content: str, memory_type: MemoryType, importance: float = 0.5, metadata: Optional[Dict] = None) -> 'MemoryItem':
        """创建新记忆项"""
        return MemoryItem(
            id=str(uuid.uuid4()),
            content=content,
            memory_type=memory_type,
            importance=importance,
            metadata=metadata or {}
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "importance": self.importance,
            "timestamp": self.timestamp.isoformat(),
            "accessed_at": self.accessed_at.isoformat(),
            "metadata": self.metadata,
            "access_count": self.access_count,
            "score": self.score
        }


@dataclass
class MemoryConfig:
    """记忆配置"""
    max_items: int = 100           # 最大记忆项数
    ttl_seconds: int = 3600        # TTL生存时间 (秒)
    importance_threshold: float = 0.5  # 重要性阈值
    # 评分公式参数
    lambda_decay: float = 0.1     # 时间衰减系数 (Working)
    lambda_recency: float = 0.05  # 近因系数 (Episodic)


# ===========================================
# 评分公式
# ===========================================

def calculate_working_score(item: MemoryItem, similarity: float = 1.0) -> float:
    """
    工作记忆评分: (相似度 × 时间衰减) × (0.8 + 重要性 × 0.4)
    
    时间衰减: e^(-λ × t), λ=0.1, t=距离上次访问的小时数
    """
    hours_elapsed = (datetime.now() - item.accessed_at).total_seconds() / 3600
    time_decay = math.exp(-0.1 * hours_elapsed)
    return (similarity * time_decay) * (0.8 + item.importance * 0.4)


def calculate_episodic_score(item: MemoryItem, vector_similarity: float = 1.0) -> float:
    """
    情景记忆评分: (向量相似度 × 0.8 + 时间近因性 × 0.2) × (0.8 + 重要性 × 0.4)
    
    时间近因性: e^(-β × Δt), β=0.05, Δt=距离创建的天数
    """
    days_elapsed = (datetime.now() - item.timestamp).total_seconds() / 86400
    recency = math.exp(-0.05 * days_elapsed)
    return (vector_similarity * 0.8 + recency * 0.2) * (0.8 + item.importance * 0.4)


def calculate_semantic_score(item: MemoryItem, vector_similarity: float = 1.0, graph_similarity: float = 1.0) -> float:
    """
    语义记忆评分: (向量相似度 × 0.7 + 图相似度 × 0.3) × (0.8 + 重要性 × 0.4)
    """
    return (vector_similarity * 0.7 + graph_similarity * 0.3) * (0.8 + item.importance * 0.4)


# ===========================================
# 记忆基类
# ===========================================

class Memory(ABC):
    """记忆基类 - 定义统一接口"""

    def __init__(self, config: Optional[MemoryConfig] = None):
        self.config = config or MemoryConfig()
        self._items: Dict[str, MemoryItem] = {}

    @property
    @abstractmethod
    def memory_type(self) -> MemoryType:
        """记忆类型"""
        pass

    @property
    @abstractmethod
    def memory_level(self) -> MemoryLevel:
        """记忆层级"""
        pass

    @abstractmethod
    async def add(
        self,
        content: str,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MemoryItem:
        """添加记忆"""
        pass

    @abstractmethod
    async def get(self, item_id: str) -> Optional[MemoryItem]:
        """获取记忆"""
        pass

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> List[MemoryItem]:
        """搜索记忆"""
        pass

    @abstractmethod
    async def delete(self, item_id: str) -> bool:
        """删除记忆"""
        pass

    @abstractmethod
    async def clear(self) -> int:
        """清空记忆"""
        pass

    @abstractmethod
    def calculate_score(self, item: MemoryItem, **kwargs) -> float:
        """计算记忆评分"""
        pass

    def get_count(self) -> int:
        """获取记忆数量"""
        return len(self._items)

    def list_all(self) -> List[MemoryItem]:
        """列出所有记忆"""
        return list(self._items.values())

    async def update_importance(self, item_id: str, importance: float) -> bool:
        """更新重要性"""
        item = self._items.get(item_id)
        if item:
            item.importance = max(0.0, min(1.0, importance))
            return True
        return False
