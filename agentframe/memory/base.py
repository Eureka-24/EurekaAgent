"""Memory Base - 记忆基类

定义记忆系统的抽象接口。
对应 SPEC 3.8.1
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class MemoryType(Enum):
    """记忆类型枚举"""
    SHORT_TERM = "short_term"      # 短期记忆
    WORKING = "working"            # 工作记忆
    LONG_TERM = "long_term"       # 长期记忆
    VECTOR = "vector"             # 向量记忆


@dataclass
class MemoryItem:
    """记忆项"""
    id: str
    content: str
    memory_type: MemoryType
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    importance: float = 1.0  # 重要性评分 0-1
    access_count: int = 0     # 访问次数

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "importance": self.importance,
            "access_count": self.access_count
        }


@dataclass
class MemoryConfig:
    """记忆配置"""
    max_items: int = 100           # 最大记忆项数
    ttl_seconds: int = 3600       # TTL生存时间
    importance_threshold: float = 0.5  # 重要性阈值
    auto_summarize: bool = True    # 自动摘要
    summary_threshold: int = 50     # 摘要触发阈值


class Memory(ABC):
    """记忆基类
    
    定义所有记忆类型的统一接口。
    """

    def __init__(self, config: Optional[MemoryConfig] = None):
        self.config = config or MemoryConfig()
        self._items: Dict[str, MemoryItem] = {}

    @abstractmethod
    async def add(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> MemoryItem:
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

    def get_count(self) -> int:
        """获取记忆数量"""
        return len(self._items)

    def list_all(self) -> List[MemoryItem]:
        """列出所有记忆"""
        return list(self._items.values())

    async def update_metadata(self, item_id: str, metadata: Dict[str, Any]) -> bool:
        """更新元数据"""
        item = self._items.get(item_id)
        if item:
            item.metadata.update(metadata)
            return True
        return False

    async def increment_access(self, item_id: str) -> bool:
        """增加访问计数"""
        item = self._items.get(item_id)
        if item:
            item.access_count += 1
            return True
        return False
